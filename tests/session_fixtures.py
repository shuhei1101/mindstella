"""MindStella の API の結合テストの共通の fixture（project-index の Mock・偽の claude と claude-balancer・専用の tmux・常駐サーバー）。

常駐サーバーは子プロセスで起動し、`PATH` の先頭に偽の `claude`・`claude-balancer` と、
`TMUX_TMPDIR` をテストごとの一時フォルダにした tmux のラッパーを置く（利用者の tmux のサーバーに触れない）。
状態のフォルダ（`XDG_STATE_HOME`）もテストごとの一時フォルダにする。fixture は `tests/conftest.py` が読み込む。
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
import yaml
from workspace_fixtures import LISTEN_HOST, PORT_ENV, REPO_ROOT, McpServer, free_port

# 常駐サーバーのスクリプトのフォルダ
SCRIPTS_DIR = REPO_ROOT / "plugins" / "mindstella" / "skills" / "mindmap" / "scripts"

# MindStella のセッションのフック
HOOK_SCRIPT = SCRIPTS_DIR / "session_hook.py"

# 偽のコマンドのほかに常駐サーバーへ見せる PATH（利用者の `~/.local/bin` の claude・claude-balancer を見せない）
SYSTEM_PATH = "/usr/local/bin:/usr/bin:/bin"

# 待つ上限秒数と確かめる間隔
WAIT_SEC = 30.0
POLL_SEC = 0.1

# HTTP の 1 回を打ち切る秒数（MindStella のセッションの準備を待つ上限より長く）
HTTP_TIMEOUT_SEC = 60.0

# 偽の Claude Code（引数と環境変数を記録し、モードに応じて MindStella のセッションのフックを叩いて入力を待つ）
FAKE_CLAUDE = """#!{python}
import json, os, subprocess, sys, threading, time
record = {record!r}
hook = {hook!r}
pid = os.getpid()
mode_file = os.path.join(record, "claude-mode")
mode = open(mode_file).read().strip() if os.path.exists(mode_file) else "normal"
names = [name for name in os.environ if name.startswith("MINDSTELLA_") or name == "CLAUDE_CONFIG_DIR"]
with open(os.path.join(record, "claude-%d.json" % pid), "w") as stream:
    json.dump({{"args": sys.argv[1:], "env": {{name: os.environ[name] for name in names}}, "pid": pid}}, stream)

def send(event, **extra):
    body = {{"session_id": "c-%d" % pid}}
    body.update(extra)
    subprocess.run([sys.executable, hook, event], input=json.dumps(body), text=True, check=False)

def note(name):
    with open(os.path.join(record, "%s-%d" % (name, pid)), "w") as stream:
        stream.write(str(time.time()))

if mode.startswith("exit:"):
    sys.exit(int(mode.split(":", 1)[1]))
if mode != "no_hook":
    send("session-start", source="startup")
if mode.startswith("responding"):
    send("prompt-submit")
    seconds = mode.split(":", 1)[1] if ":" in mode else ""
    if seconds:
        def finish():
            time.sleep(float(seconds))
            note("stop")
            send("stop")
        threading.Thread(target=finish, daemon=True).start()
for line in sys.stdin:
    with open(os.path.join(record, "input-%d.log" % pid), "a") as stream:
        stream.write("%r %s\\n" % (time.time(), line.rstrip("\\n")))
    if line.strip() == "/exit":
        note("exit")
        send("session-end", reason="prompt_input_exit")
        sys.exit(0)
"""

# 偽の claude-balancer（受けた引数を記録し、`claude-balancer-exit` があれば理由を書いてその終了コードで終わる）
FAKE_BALANCER = """#!{python}
import json, os, sys
record = {record!r}
with open(os.path.join(record, "balancer.jsonl"), "a") as stream:
    stream.write(json.dumps(sys.argv[1:]) + "\\n")
exit_file = os.path.join(record, "claude-balancer-exit")
if os.path.exists(exit_file):
    sys.stderr.write("claude-balancer: 借りられるアカウントがありません\\n")
    sys.exit(int(open(exit_file).read().strip()))
rest = sys.argv[sys.argv.index("--") + 1:]
os.execvp(rest[0], rest)
"""

# 本物の tmux を、呼び出し元の `TMUX` を外して呼ぶラッパー（ソケットは `TMUX_TMPDIR` の下の既定の名前）
TMUX_WRAPPER = """#!/bin/sh
unset TMUX TMUX_PANE
exec {tmux} -u "$@"
"""


class FakeProjectIndex:
    """project-index の端末の設定の API と読み取り API の Mock。受けた要求を記録する。"""

    def __init__(self, root: Path, allowed: list[Path]) -> None:
        """許可するフォルダを書いた端末の設定のファイルを作り、空きポートで待ち受ける。"""
        self.settings_path = root / "pi-settings.yaml"
        self.settings_path.write_text(
            yaml.safe_dump(
                {"mindstella": {"allowed_dirs": [str(path) for path in allowed]}, "sources": []}
            ),
            encoding="utf-8",
        )
        self.rows: dict[str, dict[str, Any]] = {}
        self.docs: dict[str, list[dict[str, str]]] = {}
        self.version = 1
        self.requests: list[tuple[str, str, Any]] = []
        self.post_status: int | None = None
        self.patch_delay_sec = 0.0
        self._lock = threading.Lock()
        fake = self

        class Handler(BaseHTTPRequestHandler):
            """要求を記録して答える。"""

            def _body(self) -> Any:
                """JSON の本文を読む。"""
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                return json.loads(raw) if raw else None

            def _send(self, status: int, payload: Any) -> None:
                """JSON を返す。"""
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:
                """端末の設定・文書の一覧・文書を返す。"""
                fake.requests.append(("GET", self.path, None))
                status, payload = fake.get(self.path)
                self._send(status, payload)

            def do_POST(self) -> None:
                """配信元の行を足す。"""
                body = self._body()
                fake.requests.append(("POST", self.path, body))
                status, payload = fake.post(body)
                self._send(status, payload)

            def do_PATCH(self) -> None:
                """配信元の行を変える。"""
                body = self._body()
                fake.requests.append(("PATCH", self.path, body))
                status, payload = fake.patch(self.path, body)
                self._send(status, payload)

            def log_message(self, *args: object) -> None:
                """記録を出さない。"""

        self.server = ThreadingHTTPServer((LISTEN_HOST, 0), Handler)
        self.port = int(self.server.server_address[1])
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def get(self, path: str) -> tuple[int, Any]:
        """GET の応答を作る。"""
        parsed = urllib.parse.urlsplit(path)
        parts = [urllib.parse.unquote(part) for part in parsed.path.strip("/").split("/")]
        with self._lock:
            if parsed.path == "/settings/sources":
                return 200, {
                    "settingsPath": str(self.settings_path),
                    "sources": [dict(row) for row in self.rows.values()],
                    "version": str(self.version),
                    "warnings": [],
                }
            # /sources/{source}/docs と /sources/{source}/docs/{path}?id=
            if parts[:1] == ["sources"] and len(parts) >= 3 and parts[2] == "docs":
                docs = self.docs.get(parts[1])
                if docs is None:
                    return 404, {"missing": "source"}
                if len(parts) == 3:
                    return 200, {"ref": "develop", "documents": docs}
                doc_path = "/".join(parts[3:])
                doc_id = urllib.parse.parse_qs(parsed.query).get("id", [""])[0]
                found = any(doc["path"] == doc_path and doc["id"] == doc_id for doc in docs)
                return (200, {"id": doc_id}) if found else (404, {"missing": "doc"})
        return 404, {}

    def post(self, body: Any) -> tuple[int, Any]:
        """行を足す。`post_status` があればその応答だけを返す。"""
        if self.post_status is not None:
            return self.post_status, {"detail": "Mock の失敗"}
        row = body["source"]
        with self._lock:
            if row["id"] in self.rows:
                stored = self.rows[row["id"]]
                same = stored["config"] == [row["config"]] and stored["scope"] == row["scope"]
                return 409, {"result": "exists", "same": same}
            self.rows[row["id"]] = {
                "id": row["id"],
                "config": [row["config"]],
                "scope": row["scope"],
                "outsideRead": row.get("outside_read", True),
                "status": "not_served",
            }
            self.version += 1
        return 201, {"result": "added"}

    def patch(self, path: str, body: Any) -> tuple[int, Any]:
        """行のキーを変える。版が古ければ 409。"""
        if self.patch_delay_sec:
            time.sleep(self.patch_delay_sec)
        source_id = urllib.parse.unquote(path.rsplit("/", 1)[1])
        with self._lock:
            if body.get("expectedVersion") != str(self.version):
                return 409, {"current": str(self.version)}
            row = self.rows.get(source_id)
            if row is None:
                return 404, {}
            if "outside_read" in body["source"]:
                row["outsideRead"] = body["source"]["outside_read"]
            self.version += 1
        return 200, {"version": str(self.version)}

    def changes(self) -> list[tuple[str, str, Any]]:
        """行を変える要求（POST・PATCH）だけを返す。"""
        return [request for request in self.requests if request[0] in ("POST", "PATCH")]

    def close(self) -> None:
        """待ち受けを閉じる。"""
        self.server.shutdown()
        self.server.server_close()


@dataclass
class SessionWorld:
    """MindStella の API の結合テストの環境。"""

    root: Path
    allowed: Path
    tools_dir: Path
    record_dir: Path
    tmux_tmpdir: Path
    state_root: Path
    real_tmux: str
    pi: FakeProjectIndex
    servers: list[McpServer] = field(default_factory=list)
    port: int = 0

    def server_env(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """常駐サーバーに渡す環境変数（呼び出し元の `TMUX` を渡さない）。"""
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in ("TMUX", "TMUX_PANE", "PATH") and not key.startswith("MINDSTELLA_")
        }
        env.update(
            {
                "PATH": f"{self.tools_dir}:{SYSTEM_PATH}",
                "PYTHONUTF8": "1",
                "TMUX_TMPDIR": str(self.tmux_tmpdir),
                "XDG_STATE_HOME": str(self.state_root.parent),
                "PROJECT_INDEX_PORT": str(self.pi.port),
            }
        )
        return {**env, **(extra or {})}

    def start(self, extra_env: dict[str, str] | None = None) -> McpServer:
        """常駐サーバーを子プロセスで起動する。"""
        env = self.server_env(extra_env)
        env[PORT_ENV] = str(free_port())
        server = McpServer(python=sys.executable, env=env, cwd=self.root)
        self.servers.append(server)
        self.port = server.port
        return server

    def api(
        self,
        method: str,
        path: str,
        body: Any = None,
        *,
        host: str | None = None,
        origin: str | None = None,
    ) -> tuple[int, dict[str, Any]]:
        """MindStella の API を呼び、ステータスと JSON の本文を返す。"""
        headers = {"Content-Type": "application/json", "Host": host or f"127.0.0.1:{self.port}"}
        if origin is not None:
            headers["Origin"] = origin
        request = urllib.request.Request(
            f"http://{LISTEN_HOST}:{self.port}{urllib.parse.quote(path, safe='/?=&')}",
            data=None if body is None else json.dumps(body).encode("utf-8"),
            method=method,
            headers=headers,
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(request, timeout=HTTP_TIMEOUT_SEC) as response:
                return response.status, json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"{}")

    def folder(self, name: str = "家計簿") -> Path:
        """許可するフォルダの下のフォルダの絶対パス（作らない）。"""
        return self.allowed / name

    def create_workspace(self, name: str = "家計簿", **body: Any) -> dict[str, Any]:
        """ワークスペースを作り、応答を返す。"""
        status, payload = self.api(
            "POST", "/workspaces", {"folder": str(self.folder(name)), **body}
        )
        assert status in (200, 201), payload
        return payload

    def create_session(self, workspace_id: str, **body: Any) -> tuple[int, dict[str, Any]]:
        """MindStella のセッションを作る。"""
        return self.api("POST", f"/workspaces/{workspace_id}/sessions", body or None)

    def tmux(self, *args: str) -> subprocess.CompletedProcess[str]:
        """テストの tmux のサーバーを呼ぶ。"""
        return subprocess.run(
            [str(self.tools_dir / "tmux"), *args],
            env={"TMUX_TMPDIR": str(self.tmux_tmpdir), "PATH": SYSTEM_PATH, "HOME": str(self.root)},
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def sessions(self) -> list[str]:
        """tmux のセッションの名前の一覧（サーバーが無ければ空）。"""
        listed = self.tmux("list-sessions", "-F", "#{session_name}")
        return listed.stdout.split() if listed.returncode == 0 else []

    def pane_text(self, workspace_id: str) -> str:
        """ペインの表示を返す。"""
        return self.tmux("capture-pane", "-p", "-t", f"={workspace_id}").stdout

    def session_file(self, workspace_id: str) -> Path:
        """状態のフォルダの session.json のパス。"""
        return self.state_root / "workspaces" / workspace_id / "session.json"

    def read_session(self, workspace_id: str) -> dict[str, Any] | None:
        """session.json を読む。"""
        path = self.session_file(workspace_id)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def write_session(self, workspace_id: str, **values: Any) -> dict[str, Any]:
        """session.json を書く。"""
        data = {
            "session": "S-0123456789ab",
            "status": "running",
            "started_at": "2026-11-15T00:00:00+00:00",
            "claude_session_id": "c-1",
            "pane": f"{workspace_id}:0.0",
            "socket": None,
            "pid": None,
            "pid_started_at": None,
            "responding": False,
            "pending_write": False,
            "close_pending": False,
            "last_error": None,
        }
        data.update(values)
        path = self.session_file(workspace_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return data

    def set_claude_mode(self, mode: str) -> None:
        """偽の Claude Code の動き（normal・no_hook・exit:{N}・responding・responding:{秒}）を決める。"""
        (self.record_dir / "claude-mode").write_text(mode, encoding="utf-8")

    def set_balancer_exit(self, code: int) -> None:
        """偽の claude-balancer を、借りられないときと同じく終わらせる。"""
        (self.record_dir / "claude-balancer-exit").write_text(str(code), encoding="utf-8")

    def remove_balancer(self) -> None:
        """`PATH` から claude-balancer を外す。"""
        (self.tools_dir / "claude-balancer").unlink()

    def claude_records(self) -> list[dict[str, Any]]:
        """偽の Claude Code が記録した起動の引数と環境変数。"""
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(self.record_dir.glob("claude-*.json"))
        ]

    def balancer_calls(self) -> list[list[str]]:
        """偽の claude-balancer が受けた引数。"""
        path = self.record_dir / "balancer.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def inputs(self) -> list[str]:
        """偽の Claude Code が受けた入力の行。"""
        lines: list[str] = []
        for path in sorted(self.record_dir.glob("input-*.log")):
            lines += [
                line.split(" ", 1)[1] for line in path.read_text(encoding="utf-8").splitlines()
            ]
        return lines

    def noted(self, name: str) -> float | None:
        """偽の Claude Code が記録した時刻（stop・exit）。"""
        found = sorted(self.record_dir.glob(f"{name}-*"))
        return float(found[0].read_text(encoding="utf-8")) if found else None

    def alive_claude_pids(self) -> list[int]:
        """記録した偽の Claude Code のうち、動いているプロセスの PID。"""
        pids = [int(record["pid"]) for record in self.claude_records()]
        return [pid for pid in pids if Path(f"/proc/{pid}").exists()]

    def cleanup(self) -> None:
        """常駐サーバー・tmux のセッション・偽の Claude Code を止める。"""
        for server in self.servers:
            server.stop()
        # tmux のセッションを名前で 1 つずつ落とす（最後のセッションが落ちるとテストの tmux のサーバーも終わる）
        for name in self.sessions():
            self.tmux("kill-session", "-t", f"={name}")
        for pid in self.alive_claude_pids():
            os.kill(pid, signal.SIGTERM)
        self.pi.close()
        shutil.rmtree(self.tmux_tmpdir, ignore_errors=True)


def wait_until(condition: Callable[[], Any], timeout: float = WAIT_SEC) -> Any:
    """condition が真の値を返すまで待ち、その値を返す。上限を過ぎたらテストを止める。"""
    deadline = time.monotonic() + timeout
    while True:
        value = condition()
        if value:
            return value
        assert time.monotonic() < deadline, "待っている状態になりません"
        time.sleep(POLL_SEC)


def _write_script(path: Path, text: str) -> None:
    """実行できるスクリプトを書く。"""
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


@pytest.fixture
def session_world(tmp_path: Path) -> Iterator[SessionWorld]:
    """project-index の Mock・偽の claude と claude-balancer・専用の tmux を用意し、テストの後で全て止める。"""
    real_tmux = shutil.which("tmux")
    if real_tmux is None:
        pytest.skip("tmux が無い")
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    record_dir = tmp_path / "records"
    record_dir.mkdir()
    state_home = tmp_path / "state"
    # ソケットのパスが長いとつながらないため、短い一時フォルダに置く
    tmux_tmpdir = Path(tempfile.mkdtemp(prefix="mss", dir="/tmp"))
    python = shutil.which("python3", path=SYSTEM_PATH) or sys.executable
    _write_script(
        tools_dir / "claude",
        FAKE_CLAUDE.format(python=python, record=str(record_dir), hook=str(HOOK_SCRIPT)),
    )
    _write_script(
        tools_dir / "claude-balancer", FAKE_BALANCER.format(python=python, record=str(record_dir))
    )
    _write_script(tools_dir / "tmux", TMUX_WRAPPER.format(tmux=real_tmux))
    world = SessionWorld(
        root=tmp_path,
        allowed=allowed,
        tools_dir=tools_dir,
        record_dir=record_dir,
        tmux_tmpdir=tmux_tmpdir,
        state_root=state_home / "mindstella",
        real_tmux=real_tmux,
        pi=FakeProjectIndex(tmp_path, [allowed]),
    )
    yield world
    world.cleanup()


# systemctl の Mock（`--user` の引数を記録し、ユニットのファイルの ExecStart・Environment= で常駐サーバーを起動・停止する）
FAKE_SYSTEMCTL = """#!{python}
import json, os, shlex, signal, subprocess, sys, time
record = {record!r}
args = sys.argv[1:]
if args[:1] == ["--user"]:
    args = args[1:]
with open(os.path.join(record, "systemctl.jsonl"), "a") as stream:
    stream.write(json.dumps(args) + "\\n")
pid_file = os.path.join(record, "unit.pid")

def unit_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.environ["HOME"], ".config")
    return os.path.join(base, "systemd", "user", "mindstella.service")

def read_pid():
    return int(open(pid_file).read()) if os.path.exists(pid_file) else None

def alive():
    pid = read_pid()
    return pid is not None and os.path.exists("/proc/%d" % pid) and "zombie" not in open("/proc/%d/status" % pid).read()

def stop():
    pid = read_pid()
    if pid is not None and alive():
        os.kill(pid, signal.SIGTERM)
        deadline = time.time() + 10
        while alive() and time.time() < deadline:
            time.sleep(0.1)

def start():
    command, env, log = None, {{}}, None
    for line in open(unit_path()).read().splitlines():
        key, _, value = line.partition("=")
        if key == "ExecStart":
            command = shlex.split(value)
        elif key == "Environment":
            name, _, item = shlex.split(value)[0].partition("=")
            env[name] = item
        elif key == "StandardOutput":
            log = value.split(":", 1)[1]
    env.setdefault("PATH", "/usr/bin:/bin")
    env["HOME"] = os.environ["HOME"]
    os.makedirs(os.path.dirname(log), exist_ok=True)
    process = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL, stdout=open(log, "ab"), stderr=subprocess.STDOUT, start_new_session=True, cwd=os.environ["HOME"])
    open(pid_file, "w").write(str(process.pid))

name = args[0] if args else ""
if name == "show-environment":
    sys.exit(0)
if name == "daemon-reload":
    sys.exit(0)
if name == "start":
    if not alive():
        start()
    sys.exit(0)
if name == "restart":
    stop()
    start()
    sys.exit(0)
if name == "stop":
    stop()
    sys.exit(0)
if name == "is-active":
    print("active" if alive() else ("failed" if read_pid() is not None else "inactive"))
    sys.exit(0 if alive() else 3)
sys.exit(1)
"""


@dataclass
class FakeSystemctl:
    """systemctl の Mock を置いたフォルダと、受けた引数・起動したプロセス。"""

    bin_dir: Path
    record_dir: Path

    def calls(self) -> list[list[str]]:
        """受けた引数（`--user` を除く）。"""
        path = self.record_dir / "systemctl.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def pid(self) -> int | None:
        """最後に起動した常駐サーバーの PID。"""
        path = self.record_dir / "unit.pid"
        return int(path.read_text(encoding="utf-8")) if path.exists() else None

    def stop(self) -> None:
        """起動した常駐サーバーが動いていれば止める。"""
        pid = self.pid()
        if pid is not None and Path(f"/proc/{pid}").exists():
            os.kill(pid, signal.SIGTERM)


@pytest.fixture
def fake_systemctl(tmp_path: Path) -> Iterator[FakeSystemctl]:
    """systemctl の Mock を置いたフォルダを返し、テストの後で起動した常駐サーバーを止める。"""
    bin_dir = tmp_path / "systemctl-bin"
    bin_dir.mkdir()
    record_dir = tmp_path / "systemctl-records"
    record_dir.mkdir()
    python = shutil.which("python3", path=SYSTEM_PATH) or sys.executable
    _write_script(
        bin_dir / "systemctl", FAKE_SYSTEMCTL.format(python=python, record=str(record_dir))
    )
    fake = FakeSystemctl(bin_dir=bin_dir, record_dir=record_dir)
    yield fake
    fake.stop()
