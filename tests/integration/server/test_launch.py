"""bin/mindstella（起動のコマンド）の結合テスト。

隔離した環境（偽の `claude`・tmux のラッパー・空きポート）は `tests/launch_fixtures.py`、
project-index の Mock・偽の `claude-balancer`・偽の `systemctl` は `tests/session_fixtures.py`。
起動のコマンドが起動した常駐サーバーと状態のフォルダを読んで確かめる。
"""

from __future__ import annotations

import json
import shutil
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
import yaml
from launch_fixtures import PLUGIN_DIR, LaunchSandbox, ServeFakeStatus, copy_plugin
from session_fixtures import (
    FAKE_BALANCER,
    FAKE_CLAUDE,
    HOOK_SCRIPT,
    SYSTEM_PATH,
    FakeProjectIndex,
    FakeSystemctl,
)
from workspace_fixtures import LISTEN_HOST, plugin_version, read_server_status

from .fixture_types import MakeVenv

# 古いバージョンの常駐サーバーの代わりが返す状態
OUTDATED_STATUS = {"name": "mindstella", "version": "0.0.1"}

# 外から見る設定の環境変数とその値
ALLOWED_HOSTS_ENV = "MINDSTELLA_ALLOWED_HOSTS"
ALLOWED_HOST = "preview.example.test"

# 常駐サーバーと偽のコマンドが使う外部コマンド（起動のコマンドの PATH のフォルダにリンクを置く）
EXTRA_COMMANDS = ("ps", "sh", "cat", "env")

# 許可するフォルダの名前（起動のコマンドの作業フォルダからの相対パス）
ALLOWED = "allowed"

# ワークスペースのフォルダ
FOLDER = f"{ALLOWED}/家計簿アプリ"


@dataclass
class LaunchWorld:
    """起動のコマンドを、MindStella の API まで通して動かす環境。"""

    sandbox: LaunchSandbox
    pi: FakeProjectIndex
    systemctl: FakeSystemctl
    venv: Path
    state_home: Path

    def write_claude(self, listing: list[dict[str, Any]]) -> None:
        """`plugin list --json` に listing を返し、ほかは MindStella のセッションの偽の Claude Code として動く claude を置く。"""
        python = shutil.which("python3", path=SYSTEM_PATH)
        script = FAKE_CLAUDE.format(
            python=python, record=str(self.sandbox.record_dir), hook=str(HOOK_SCRIPT)
        )
        branch = f"if sys.argv[1:3] == ['plugin', 'list']:\n    print({json.dumps(listing)!r})\n    sys.exit(0)\n"
        script = script.replace(
            "import json, os, subprocess, sys, threading, time\n",
            "import json, os, subprocess, sys, threading, time\n" + branch,
            1,
        )
        path = self.sandbox.tools_dir / "claude"
        path.write_text(script, encoding="utf-8")
        path.chmod(0o755)

    def launch(self, *args: str, extra_env: dict[str, str] | None = None, **kwargs: Any) -> Any:
        """起動のコマンドを叩く。"""
        env = {
            "PROJECT_INDEX_PORT": str(self.pi.port),
            "XDG_STATE_HOME": str(self.state_home),
            "XDG_CONFIG_HOME": str(self.sandbox.root / ".config"),
            **(extra_env or {}),
        }
        return self.sandbox.launch(
            *args, venv=kwargs.pop("venv", self.venv), extra_env=env, **kwargs
        )

    def ids(self) -> list[str]:
        """状態のフォルダの ID の一覧。"""
        path = self.state_home / "mindstella" / "workspaces.yaml"
        return (
            list(yaml.safe_load(path.read_text(encoding="utf-8"))["ids"]) if path.exists() else []
        )

    def session(self, workspace_id: str) -> dict[str, Any] | None:
        """状態のフォルダの session.json。"""
        path = self.state_home / "mindstella" / "workspaces" / workspace_id / "session.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def workspace_id(self) -> str:
        """作ったワークスペースの ID（記録の設定の id）。"""
        config = self.sandbox.root / FOLDER / ".mindstella" / "config.yaml"
        return str(yaml.safe_load(config.read_text(encoding="utf-8"))["id"])

    def claude_records(self) -> list[dict[str, Any]]:
        """偽の Claude Code が記録した起動の引数と環境変数。"""
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(self.sandbox.record_dir.glob("claude-*.json"))
        ]

    def balancer_calls(self) -> list[list[str]]:
        """偽の claude-balancer が受けた引数。"""
        path = self.sandbox.record_dir / "balancer.jsonl"
        return (
            [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            if path.exists()
            else []
        )

    def unit_text(self) -> str:
        """ユニットのファイルの中身。"""
        return (
            self.sandbox.root / ".config" / "systemd" / "user" / "mindstella.service"
        ).read_text(encoding="utf-8")


@pytest.fixture
def world(
    sandbox: LaunchSandbox, ready_venv: Path, fake_systemctl: FakeSystemctl
) -> Iterator[LaunchWorld]:
    """起動のコマンドの PATH に偽の systemctl・claude-balancer と外部コマンドを置き、project-index の Mock を立てる。"""
    for name in EXTRA_COMMANDS:
        found = shutil.which(name, path=SYSTEM_PATH)
        assert found is not None, name
        (sandbox.tools_dir / name).symlink_to(found)
    (sandbox.tools_dir / "systemctl").symlink_to(fake_systemctl.bin_dir / "systemctl")
    balancer = sandbox.tools_dir / "claude-balancer"
    python = shutil.which("python3", path=SYSTEM_PATH)
    balancer.write_text(
        FAKE_BALANCER.format(python=python, record=str(sandbox.record_dir)), encoding="utf-8"
    )
    balancer.chmod(0o755)
    (sandbox.root / ALLOWED).mkdir()
    pi = FakeProjectIndex(sandbox.root, [sandbox.root / ALLOWED])
    created = LaunchWorld(
        sandbox=sandbox,
        pi=pi,
        systemctl=fake_systemctl,
        venv=ready_venv,
        state_home=sandbox.root / "state",
    )
    created.write_claude([{"id": "mindstella@mindstella", "installPath": str(PLUGIN_DIR)}])
    yield created
    # tmux のセッションを名前で 1 つずつ落とす（tmux を外したテストでは立っていない）
    if (sandbox.tools_dir / "tmux").exists():
        for name in sandbox.sessions():
            sandbox.tmux("kill-session", "-t", f"={name}")
    pi.close()


def _process_env(pid: int) -> dict[str, str]:
    """プロセスの環境変数を読む（Linux の /proc）。"""
    raw = Path(f"/proc/{pid}/environ").read_bytes().decode("utf-8")
    return dict(entry.split("=", 1) for entry in raw.split("\0") if "=" in entry)


def test_normal(world: LaunchWorld) -> None:
    """常駐サーバーが落ちていれば起動し、ワークスペースと MindStella のセッションを作ってつなぐコマンドを出す（正常系）。"""
    # 実行
    result = world.launch(FOLDER)
    # 検証
    assert result.returncode == 0, result.stderr
    workspace_id = world.workspace_id()
    assert workspace_id in world.ids()
    session = world.session(workspace_id)
    assert session is not None
    assert session["status"] == "running"
    assert workspace_id in world.sandbox.sessions()
    status = read_server_status(world.sandbox.port)
    assert status is not None
    assert status["plugin_root"] == str(PLUGIN_DIR)
    lines = result.stdout.splitlines()
    assert lines[0].startswith("http://")
    assert f"tmux attach-session -t ={workspace_id}" in lines


def test_normal_when_plugin_upgraded(world: LaunchWorld, tmp_path: Path) -> None:
    """古い版の起動のコマンドを叩いても、インストールした今の版の常駐サーバーを起動する（正常系）。"""
    # 準備
    old_dir = copy_plugin(tmp_path / "plugin-old")
    new_dir = copy_plugin(tmp_path / "plugin-new")
    world.write_claude([{"id": "mindstella@mindstella", "installPath": str(new_dir)}])
    # 実行
    result = world.launch(FOLDER, script=old_dir / "bin" / "mindstella")
    # 検証
    assert result.returncode == 0, result.stderr
    status = read_server_status(world.sandbox.port)
    assert status is not None
    assert status["plugin_root"] == str(new_dir)


def test_normal_when_session_exists(world: LaunchWorld) -> None:
    """同じフォルダの MindStella のセッションが動いていれば、立てずにそのペインへつなぐ（正常系）。"""
    # 準備
    first = world.launch(FOLDER)
    assert first.returncode == 0, first.stderr
    before = world.sandbox.sessions()
    # 実行
    result = world.launch(FOLDER)
    # 検証
    assert result.returncode == 0, result.stderr
    assert world.sandbox.sessions() == before
    assert len(world.balancer_calls()) == 1
    assert "既にある MindStella のセッション" in result.stderr


def test_normal_when_options_given(world: LaunchWorld) -> None:
    """進め方の文書・追加の MCP・プラグインを『ワークスペースの作成』へ渡す（正常系）。"""
    # 準備
    root = world.sandbox.root
    world.pi.rows["aituber"] = {
        "id": "aituber",
        "config": ["/repo/aituber/project-index.yaml"],
        "scope": {"read": [f"{root / ALLOWED}/**"]},
        "outsideRead": True,
    }
    world.pi.docs["aituber"] = [{"id": "flow-1", "path": "docs/flow-1.yaml"}]
    mcp_config = {"mcpServers": {"aituber": {"command": "aituber-mcp"}}}
    (root / "mcp.json").write_text(json.dumps(mcp_config), encoding="utf-8")
    plugins = []
    for name in ("p1", "p2"):
        (root / name / ".claude-plugin").mkdir(parents=True)
        (root / name / ".claude-plugin" / "plugin.json").write_text(
            '{"name": "x"}', encoding="utf-8"
        )
        plugins.append(str(root / name))
    # 実行
    result = world.launch(
        FOLDER,
        "--flow",
        "aituber#flow-1",
        "--mcp-config",
        "mcp.json",
        "--plugin-dir",
        "p1",
        "--plugin-dir",
        "p2",
    )
    # 検証
    assert result.returncode == 0, result.stderr
    workspace_id = world.workspace_id()
    config = yaml.safe_load(
        (root / FOLDER / ".mindstella" / "config.yaml").read_text(encoding="utf-8")
    )
    assert config["flow"] == {"source": "aituber", "doc": "flow-1"}
    launch = json.loads(
        (world.state_home / "mindstella" / "workspaces" / workspace_id / "launch.json").read_text(
            encoding="utf-8"
        )
    )
    assert launch == {"mcp_config": mcp_config, "plugin_dirs": plugins}


def test_normal_when_server_status(world: LaunchWorld) -> None:
    """server status で常駐サーバーの状態を出す（正常系）。"""
    # 準備
    assert world.launch(FOLDER).returncode == 0
    # 実行
    result = world.launch("server", "status")
    # 検証
    assert result.returncode == 0, result.stderr
    status = read_server_status(world.sandbox.port)
    assert status is not None
    assert str(world.sandbox.port) in result.stdout
    assert plugin_version() in result.stdout
    assert str(PLUGIN_DIR) in result.stdout
    assert all(str(preview["port"]) in result.stdout for preview in status["previews"])


def test_normal_when_server_restart(world: LaunchWorld) -> None:
    """server restart でユニットを書き直して起動し直し、server stop で止める（正常系）。"""
    # 準備
    assert world.launch(FOLDER).returncode == 0
    # 実行
    restarted = world.launch("server", "restart")
    stopped = world.launch("server", "stop")
    # 検証
    assert restarted.returncode == 0, restarted.stderr
    assert (
        f"ExecStart={world.venv}/bin/python {PLUGIN_DIR}/skills/mindmap/scripts/server.py"
        in world.unit_text()
    )
    calls = [call for call in world.systemctl.calls() if call[:1] != ["is-active"]]
    assert ["restart", "mindstella.service"] in calls
    assert calls.index(["restart", "mindstella.service"]) == len(calls) - 2
    assert calls[-3] == ["daemon-reload"]
    assert stopped.returncode == 0, stopped.stderr
    assert calls[-1] == ["stop", "mindstella.service"]


def test_error_when_dependency_missing(world: LaunchWorld, make_venv: MakeVenv) -> None:
    """依存が足りなければ、そろえるコマンドを出して何も起動しない（異常系）。"""
    # 準備
    bare_venv = make_venv("bare-venv", with_libraries=False)
    # 実行
    result = world.launch(FOLDER, venv=bare_venv)
    # 検証
    assert result.returncode == 1
    assert all(package in result.stderr for package in ("PyYAML", "jsonschema", "mcp"))
    assert "-m pip install" in result.stderr
    assert world.sandbox.sessions() == []
    assert world.claude_records() == []


def test_error_when_tmux_missing(world: LaunchWorld) -> None:
    """tmux が無ければ 1（異常系）。"""
    # 準備
    world.sandbox.remove_tool("tmux")
    # 実行
    result = world.launch(FOLDER)
    # 検証
    assert result.returncode == 1
    assert "tmux" in result.stderr
    assert world.claude_records() == []


def test_error_when_claude_missing(world: LaunchWorld) -> None:
    """claude が無ければ 1（異常系）。"""
    # 準備
    world.sandbox.remove_tool("claude")
    # 実行
    result = world.launch(FOLDER)
    # 検証
    assert result.returncode == 1
    assert "claude" in result.stderr
    assert world.sandbox.sessions() == []


def test_error_when_plugin_not_installed(world: LaunchWorld) -> None:
    """プラグインがインストールされていなければ、インストールの案内を出して 1（異常系）。"""
    # 準備
    world.write_claude([])
    # 実行
    result = world.launch(FOLDER)
    # 検証
    assert result.returncode == 1
    assert "mindstella@mindstella" in result.stderr
    assert "claude plugin install" in result.stderr
    assert world.sandbox.sessions() == []


def test_error_when_folder_missing(world: LaunchWorld) -> None:
    """フォルダを渡さなければ使い方を出して 2（異常系）。"""
    # 実行
    result = world.launch()
    # 検証
    assert result.returncode == 2
    assert "使い方" in result.stderr
    assert world.claude_records() == []


def test_normal_when_external_settings(world: LaunchWorld) -> None:
    """外から見る設定は常駐サーバーへ渡し、MindStella のセッションの claude には足さない（正常系）。"""
    # 実行
    result = world.launch(FOLDER, extra_env={ALLOWED_HOSTS_ENV: ALLOWED_HOST})
    # 検証
    assert result.returncode == 0, result.stderr
    status = read_server_status(world.sandbox.port)
    assert status is not None
    assert _process_env(int(status["pid"]))[ALLOWED_HOSTS_ENV] == ALLOWED_HOST
    assert f"Environment={ALLOWED_HOSTS_ENV}={ALLOWED_HOST}" in world.unit_text()
    assert ALLOWED_HOSTS_ENV not in world.claude_records()[0]["env"]


class _OutdatedServer:
    """古いコードの常駐サーバーの代わり（状態の GET に古い版を返し、作成の POST を記録して成功を返す）。"""

    def __init__(self, port: int) -> None:
        """そのポートで待ち受ける。"""
        self.posts: list[str] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            """決めた応答を返す。"""

            def _send(self, status: int, body: dict[str, Any]) -> None:
                """JSON を返す。"""
                data = json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:
                """古い版の状態を返す。"""
                self._send(200, OUTDATED_STATUS)

            def do_POST(self) -> None:
                """作成の依頼を記録して成功を返す。"""
                self.rfile.read(int(self.headers.get("Content-Length") or 0))
                outer.posts.append(self.path)
                if self.path == "/workspaces":
                    self._send(
                        201,
                        {
                            "id": "mindstella-家計簿アプリ-000000",
                            "url": "http://127.0.0.1:1/mindstella.html",
                        },
                    )
                else:
                    self._send(
                        201, {"session": "S-1", "pane": "mindstella-家計簿アプリ-000000:0.0"}
                    )

            def log_message(self, *args: object) -> None:
                """記録を出さない。"""

        self.server = ThreadingHTTPServer((LISTEN_HOST, port), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        """待ち受けを閉じる。"""
        self.server.shutdown()
        self.server.server_close()


def test_normal_when_server_outdated(world: LaunchWorld) -> None:
    """古いコードの常駐サーバーが待ち受けていれば、起動し直さずに違いと手順を出し、作成へ進む（正常系）。"""
    # 準備
    outdated = _OutdatedServer(world.sandbox.port)
    try:
        # 実行
        result = world.launch(FOLDER)
        # 検証
        assert result.returncode == 0, result.stderr
        assert "0.0.1" in result.stderr
        assert plugin_version() in result.stderr
        assert "mindstella server restart" in result.stderr
        assert "/workspaces" in outdated.posts
        assert read_server_status(world.sandbox.port) == OUTDATED_STATUS
    finally:
        outdated.close()


def test_error_when_server_start_fails(
    world: LaunchWorld, serve_fake_status: ServeFakeStatus
) -> None:
    """ポートを別のプロセスが使っていれば、起動せずに案内を出して 1（異常系）。"""
    # 準備
    serve_fake_status(world.sandbox.port, 404, None)
    # 実行
    result = world.launch(FOLDER)
    # 検証
    assert result.returncode == 1
    assert str(world.sandbox.port) in result.stderr
    assert "MINDSTELLA_PORT" in result.stderr
    assert not any(call[:1] == ["start"] for call in world.systemctl.calls())
    assert not (world.sandbox.root / FOLDER / ".mindstella").exists()
    assert world.sandbox.sessions() == []


def test_normal_when_another_account(world: LaunchWorld) -> None:
    """claude-balancer が無ければ、CLAUDE_CONFIG_DIR のアカウントで MindStella のセッションを起動する（正常系）。"""
    # 準備
    world.sandbox.remove_tool("claude-balancer")
    config_dir = world.sandbox.root / ".claude-sub1"
    config_dir.mkdir()
    # 実行
    result = world.launch(FOLDER, extra_env={"CLAUDE_CONFIG_DIR": str(config_dir)})
    # 検証
    assert result.returncode == 0, result.stderr
    assert world.claude_records()[0]["env"]["CLAUDE_CONFIG_DIR"] == str(config_dir)


def test_error_when_workspace_rejected(world: LaunchWorld) -> None:
    """ワークスペースを作れなければ、detail を出して 1 を返し、MindStella のセッションを作らない（異常系）。"""
    # 実行
    result = world.launch("outside/家計簿アプリ")
    # 検証
    assert result.returncode == 1
    assert "許可するフォルダの外です" in result.stderr
    assert world.sandbox.sessions() == []
    assert world.claude_records() == []


def test_error_when_session_not_created(world: LaunchWorld) -> None:
    """MindStella のセッションを作れなければ、detail と画面の URL を出して 1（異常系）。"""
    # 準備
    (world.sandbox.record_dir / "claude-balancer-exit").write_text("125", encoding="utf-8")
    # 実行
    result = world.launch(FOLDER)
    # 検証
    assert result.returncode == 1
    assert "借りられるアカウントがありません" in result.stderr
    assert "画面: http://" in result.stderr
    assert world.sandbox.sessions() == []
