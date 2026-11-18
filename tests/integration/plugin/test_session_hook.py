"""MindStella のセッションのフック（session_hook.py）の結合テスト。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from session_fixtures import HOOK_SCRIPT, SYSTEM_PATH
from workspace_fixtures import LISTEN_HOST, free_port

# フック 1 回を待つ上限秒数
HOOK_TIMEOUT_SEC = 30

# MindStella のセッションの ID と進め方の文書
SESSION_ID = "S-0123456789ab"
FLOW = "aituber#flow-script"


# `/resume` の既定の応答（起動の注入文の見本と、通し番号 0）
STARTUP_RESUME = {"context": "起動しました。次は mindstella/startup を参照して先に進めます。", "until_seq": 0, "changed_more": 0, "removed_more": 0}

# 再開の `/resume` の応答（取り込み待ち 1 件・変わった D-1・要見直し D-1・進行中 T-1）
RESUMED_RESUME = {
    "trigger": "resume",
    "awaiting_threads": 1,
    "changed": [{"id": "D-1", "kind": "decision", "title": "問い", "updated_by": "user"}],
    "changed_more": 0,
    "removed": [],
    "removed_more": 0,
    "needs_review": [{"id": "D-1", "title": "問い"}],
    "in_progress": [{"id": "T-1", "title": "作業"}],
    "context": "再開しました。取り込み待ちのコメントのスレッドは 1 件です。\n- D-1 問い\n- T-1 作業",
    "until_seq": 7,
}

# 注入に収まらない変更を持つ `/resume` の応答
OVERFLOW_RESUME = {
    "trigger": "resume",
    "changed": [{"id": f"D-{number}", "kind": "decision", "title": "問い", "updated_by": "ai"} for number in range(1, 21)],
    "changed_more": 5,
    "removed": [],
    "removed_more": 0,
    "context": "ほかに、変えた項目が 5 件あります。残りと前の値は changes_since_read で取得できます。",
    "until_seq": 30,
}


class _Recorder:
    """受けた要求を記録し、`/resume` には決めた応答を、ほかには 200 を返す、常駐サーバーの代わりの HTTP のサーバー。"""

    def __init__(self) -> None:
        """空きポートで待ち受ける。"""
        self.received: list[tuple[str, Any]] = []
        self.resume_status = 200
        self.resume_body: dict[str, Any] = STARTUP_RESUME
        recorder = self

        class Handler(BaseHTTPRequestHandler):
            """経路と本文を記録する。"""

            def do_POST(self) -> None:
                """記録して応答する。"""
                length = int(self.headers.get("Content-Length") or 0)
                recorder.received.append((self.path, json.loads(self.rfile.read(length))))
                # 再開の状況: 決めた応答
                if self.path.endswith("/resume"):
                    status, payload = recorder.resume_status, recorder.resume_body
                else:
                    status, payload = 200, {}
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args: object) -> None:
                """記録を出さない。"""

        self.server = ThreadingHTTPServer((LISTEN_HOST, 0), Handler)
        self.port = int(self.server.server_address[1])
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def paths(self) -> list[str]:
        """受けた要求の経路の最後の部分を、受けた順に返す。"""
        return [path.rsplit("/", 1)[-1] for path, _body in self.received]

    def body_of(self, last: str) -> Any:
        """経路の最後の部分が last の要求の本文を返す。"""
        return next(body for path, body in self.received if path.endswith(f"/{last}"))


@pytest.fixture
def recorder() -> Iterator[_Recorder]:
    """常駐サーバーの代わりを立て、テストの後で止める。"""
    started = _Recorder()
    yield started
    started.server.shutdown()
    started.server.server_close()


def _run(
    event: str,
    port: int,
    *,
    with_session: bool = True,
    source: str = "startup",
    flow: bool = True,
    home: str | None = None,
    config_dir: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """システムの python3 でフックを呼ぶ。"""
    python = shutil.which("python3", path=SYSTEM_PATH)
    assert python is not None
    env = {
        "PATH": SYSTEM_PATH,
        "HOME": home or os.environ.get("HOME", "/tmp"),
        "MINDSTELLA_PORT": str(port),
        "TMUX_PANE": "%3",
    }
    # 起動したアカウントの設定のフォルダを渡すとき
    if config_dir is not None:
        env["CLAUDE_CONFIG_DIR"] = config_dir
    # MindStella のセッション: ID と、渡すときは進め方の文書の場所
    if with_session:
        env["MINDSTELLA_SESSION"] = SESSION_ID
        if flow:
            env["MINDSTELLA_FLOW"] = FLOW
    return subprocess.run(
        [python, str(HOOK_SCRIPT), event],
        input=json.dumps({"session_id": "c-1", "source": source}),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=HOOK_TIMEOUT_SEC,
        check=False,
    )


def _context(completed: subprocess.CompletedProcess[str]) -> str:
    """標準出力の注入文を返す。"""
    return json.loads(completed.stdout)["hookSpecificOutput"]["additionalContext"]


def test_normal(recorder: _Recorder, tmp_path: Path) -> None:
    """SessionStart で出来事を設定のフォルダとともに送り、『再開の状況』の注入文を注入する（正常系）。"""
    # 実行
    completed = _run(
        "session-start", recorder.port, home=str(tmp_path), config_dir="~/claude-sub1"
    )
    # 検証
    assert completed.returncode == 0, completed.stderr
    path, body = recorder.received[0]
    assert path == f"/_admin/sessions/{SESSION_ID}/events"
    assert (body["event"], body["claude_session_id"], body["pane"], body["source"]) == (
        "session_start",
        "c-1",
        "%3",
        "startup",
    )
    assert body["claude_config_dir"] == f"{tmp_path}/claude-sub1"
    assert _context(completed) == STARTUP_RESUME["context"]
    assert recorder.paths() == ["events", "resume", "read_point"]
    assert recorder.body_of("resume") == {"source": "startup"}
    assert recorder.body_of("read_point") == {"until_seq": 0}


def test_normal_when_config_dir_not_set(recorder: _Recorder, tmp_path: Path) -> None:
    """CLAUDE_CONFIG_DIR が無ければ ~/.claude の絶対パスを送る（正常系）。"""
    # 実行
    completed = _run("session-start", recorder.port, home=str(tmp_path))
    # 検証
    assert completed.returncode == 0, completed.stderr
    assert recorder.received[0][1]["claude_config_dir"] == f"{tmp_path}/.claude"


def test_normal_when_ordinary_session(recorder: _Recorder) -> None:
    """MINDSTELLA_SESSION が無ければ何もしない（正常系）。"""
    # 実行
    completed = _run("session-start", recorder.port, with_session=False)
    # 検証
    assert (completed.returncode, completed.stdout) == (0, "")
    assert recorder.received == []


def test_error_when_server_down() -> None:
    """常駐サーバーへつながらなければ、標準エラーに 1 行書いて終了コード 0（異常系）。"""
    # 実行
    completed = _run("stop", free_port())
    # 検証
    assert completed.returncode == 0
    assert "[mindstella]" in completed.stderr


def test_normal_when_resumed(recorder: _Recorder) -> None:
    """SessionStart の compact で、再開の状況を注入し、注入文を書いた後に前回参照した時点を進める（正常系）。"""
    # 準備
    recorder.resume_body = RESUMED_RESUME
    # 実行
    completed = _run("session-start", recorder.port, source="compact", flow=False)
    # 検証
    assert completed.returncode == 0, completed.stderr
    assert recorder.paths() == ["events", "resume", "read_point"]
    assert recorder.body_of("resume") == {"source": "compact"}
    assert recorder.body_of("read_point") == {"until_seq": 7}
    assert _context(completed) == RESUMED_RESUME["context"]


def test_normal_when_resume_unavailable(recorder: _Recorder) -> None:
    """再開の状況が 200 でないと、状況を持たずに注入し、前回参照した時点を進めない（正常系）。"""
    # 準備
    recorder.resume_status = 500
    recorder.resume_body = {"detail": "描けません"}
    # 実行
    completed = _run("session-start", recorder.port, source="compact")
    # 検証
    assert completed.returncode == 0
    context = _context(completed)
    assert "再開" in context
    assert FLOW.split("#")[0] in context
    assert FLOW.split("#")[1] in context
    assert "mindstella/startup" in context
    assert "取り込み待ち" not in context
    assert "read_point" not in recorder.paths()
    assert "[mindstella]" in completed.stderr


def test_normal_when_changes_overflow(recorder: _Recorder) -> None:
    """再開の状況に超えた分があると、注入文を注入し、前回参照した時点を進めない（正常系）。"""
    # 準備
    recorder.resume_body = OVERFLOW_RESUME
    # 実行
    completed = _run("session-start", recorder.port, source="compact")
    # 検証
    assert completed.returncode == 0, completed.stderr
    assert _context(completed) == OVERFLOW_RESUME["context"]
    assert "read_point" not in recorder.paths()
