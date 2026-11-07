"""起動スクリプトで立ち上げる（依存を確かめ、常駐の MCP サーバーが落ちていれば起動してから、tmux の中で Claude Code を立ち上げる）の E2E テスト。

本物の Claude Code は立ち上げず、偽の `claude` が受け取った引数と環境変数と、常駐サーバーの待ち受けを確かめる。
隔離した環境（偽の `claude`・専用のソケットの `tmux`・空きポート）は `tests/launch_fixtures.py`。
"""

from __future__ import annotations

import os
import socket
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from launch_fixtures import (
    PLUGIN_DIR,
    LaunchSandbox,
    copy_plugin,
    read_tool_names,
    session_name,
)
from workspace_fixtures import (
    LISTEN_HOST,
    MCP_PATH,
    PORT_ENV,
    MakeVenv,
    MakeWorkspace,
    McpClient,
    McpServer,
    is_listening,
    plugin_version,
    read_server_status,
)

# 常駐サーバーの入口の、プラグインのフォルダからの場所
SERVER_ENTRY = Path("skills") / "mindmap" / "scripts" / "server.py"

# 古い版のフォルダが名乗るバージョン
OLD_VERSION = "v0.0.1"


@pytest.fixture
def occupied_port(sandbox: LaunchSandbox) -> Iterator[socket.socket]:
    """常駐サーバーに渡すポートを、テストが先に `127.0.0.1` で待ち受けて塞ぎ、テストの後で閉じる。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind((LISTEN_HOST, sandbox.port))
        listener.listen()
        yield listener


@pytest.fixture
def old_server(sandbox: LaunchSandbox, ready_venv: Path, tmp_path: Path) -> Iterator[McpServer]:
    """古い版のフォルダのサーバーを MINDSTELLA_PORT のポートで常駐させ、偽の claude の installPath を新しい版のフォルダにする。"""
    old_dir = copy_plugin(tmp_path / "plugin-old")
    (old_dir / "version.ini").write_text(f"{OLD_VERSION}\n", encoding="utf-8")
    new_dir = copy_plugin(tmp_path / "plugin-new")
    sandbox.write_claude([{"id": "mindstella@mindstella", "installPath": str(new_dir)}])
    server = McpServer(
        python=str(ready_venv / "bin" / "python"),
        env={**os.environ, "PYTHONUTF8": "1", PORT_ENV: str(sandbox.port)},
        cwd=tmp_path,
        script=old_dir / SERVER_ENTRY,
    )
    yield server
    server.stop()


@pytest.fixture
def old_preview_port(old_server: McpServer, make_workspace: MakeWorkspace) -> int:
    """古い版の常駐サーバーで別のワークスペースのプレビューを配信し、配信のポートを返す。"""
    other = make_workspace(name="別の話し合い")
    served = old_server.call("preview_url", workspace=str(other))
    assert served.data is not None
    port = urlsplit(str(served.data["url"])).port
    assert port is not None
    return port


def test_normal(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """依存が揃っていれば、落ちている常駐サーバーを起動してから、tmux のセッションの中で Claude Code を立てる（正常系）。"""
    # 準備
    folder = sandbox.root / "家計簿アプリ"
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 0, result.stderr
    # tmux に、ワークスペースのフォルダを開いたセッションがある
    name = session_name(folder, sandbox.config_dir)
    assert sandbox.sessions() == [name]
    assert sandbox.session_path(name) == folder.resolve()
    # 常駐サーバーが、installPath の版のフォルダのサーバーで、MINDSTELLA_PORT のポートで待ち受けている
    status = read_server_status(sandbox.port)
    assert status is not None
    assert (status["plugin_root"], status["port"]) == (str(PLUGIN_DIR), sandbox.port)
    # MCP のクライアントで常駐サーバーにつなぐと、mindstella のツールの一覧が返る
    client = McpClient(f"http://{LISTEN_HOST}:{sandbox.port}{MCP_PATH}")
    try:
        tools = [tool["name"] for tool in client.list_tools()]
    finally:
        client.close()
    assert tools == read_tool_names(PLUGIN_DIR / SERVER_ENTRY)
    # Claude Code が --mcp-config を受け取っておらず、設定のフォルダの CLAUDE_CONFIG_DIR が渡る
    started = sandbox.wait_started()
    assert len(started) == 1
    assert "--mcp-config" not in started[0].read_text(encoding="utf-8").splitlines()
    assert started[0].with_suffix(".config").read_text(encoding="utf-8") == str(sandbox.config_dir)
    # Claude Code が --append-system-prompt を受け取り、その値が installPath の版のフォルダの起動時の指示の中身である
    prompt = (PLUGIN_DIR / "skills" / "mindmap" / "references" / "起動時の指示.md").read_text(encoding="utf-8")
    assert started[0].read_text(encoding="utf-8") == f"--append-system-prompt\n{prompt.rstrip(chr(10))}\n"


def test_normal_when_plugin_upgraded(
    sandbox: LaunchSandbox, ready_venv: Path, tmp_path: Path
) -> None:
    """古い版のフォルダの起動スクリプトを叩いても、新しい版のフォルダのサーバーで常駐サーバーを起動する（正常系）。"""
    # 準備
    old_dir = copy_plugin(tmp_path / "plugin-old")
    new_dir = copy_plugin(tmp_path / "plugin-new")
    sandbox.write_claude([{"id": "mindstella@mindstella", "installPath": str(new_dir)}])
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv, script=old_dir / "bin" / "mindstella")
    # 検証
    assert result.returncode == 0, result.stderr
    status = read_server_status(sandbox.port)
    assert status is not None
    assert status["plugin_root"] == str(new_dir)


def test_normal_when_old_server_running(
    sandbox: LaunchSandbox, ready_venv: Path, old_server: McpServer, old_preview_port: int
) -> None:
    """古い版の常駐サーバーが待ち受けていれば、立ち上げ直さずに版の違いと立ち上げ直す手順を示し、tmux のセッションを立てる（正常系）。"""
    # 準備
    folder = sandbox.root / "家計簿アプリ"
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 0, result.stderr
    # 出力に、待ち受けている常駐サーバーの版とインストールした今の版と、立ち上げ直す手順がある
    assert (
        f"常駐サーバーのバージョン {OLD_VERSION} と、インストールしたプラグインのバージョン {plugin_version()} が違います"
        in result.stderr
    )
    assert "server_stop で常駐サーバーを止めてから、Claude Code を立ち上げ直してください" in result.stderr
    # 古い版の常駐サーバーが立ち上げ直されず、別のワークスペースのプレビューの配信が止まっていない
    status = read_server_status(sandbox.port)
    assert status is not None
    assert (status["version"], status["pid"]) == (OLD_VERSION, old_server.process.pid)
    assert is_listening(old_preview_port) is True
    # tmux に、ワークスペースのフォルダを開いたセッションがある
    assert sandbox.sessions() == [session_name(folder, sandbox.config_dir)]


def test_error_when_dependency_missing(sandbox: LaunchSandbox, make_venv: MakeVenv) -> None:
    """依存が足りないと、足りないライブラリとそろえるコマンドを示して、何も立ち上げない（異常系）。"""
    # 準備
    bare_venv = make_venv("bare-venv", with_libraries=False)
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=bare_venv)
    # 検証
    assert result.returncode != 0
    for package in ("PyYAML", "jsonschema", "mcp"):
        assert package in result.stderr
    assert "-m pip install" in result.stderr
    assert sandbox.sessions() == []
    assert sandbox.started() == []
    assert is_listening(sandbox.port) is False


@pytest.mark.usefixtures("occupied_port")
def test_error_when_server_not_started(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """常駐サーバーのポートが使われていて起動できなければ、使われているポートと変える手順を示し、何も立ち上げない（異常系）。"""
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode != 0
    assert f"ポート {sandbox.port} は別のプロセスが使っています" in result.stderr
    assert "MINDSTELLA_PORT" in result.stderr
    assert sandbox.sessions() == []
    assert sandbox.started() == []


def test_error_when_tmux_missing(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """tmux が無ければ、tmux が無い旨を示して Claude Code を立ち上げない（異常系）。"""
    # 準備
    sandbox.remove_tool("tmux")
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode != 0
    assert "tmux" in result.stderr
    assert sandbox.started() == []


def test_normal_when_another_account(
    sandbox: LaunchSandbox, ready_venv: Path, tmp_path: Path
) -> None:
    """同じフォルダでも別のアカウント（`CLAUDE_CONFIG_DIR`）で開けば、別の名前のセッションを立て、先にあったセッションは立ち上げ直さない（正常系）。"""
    # 準備
    folder = sandbox.root / "家計簿アプリ"
    sub1 = tmp_path / "claude-sub1"
    sub1.mkdir()
    # `CLAUDE_CONFIG_DIR` を渡さずに立てたセッションが 1 つある
    first = sandbox.launch("家計簿アプリ", venv=ready_venv, with_config=False)
    assert first.returncode == 0, first.stderr
    before = sandbox.wait_started()
    assert len(before) == 1
    # 実行
    result = sandbox.launch(
        "家計簿アプリ", venv=ready_venv, extra_env={"CLAUDE_CONFIG_DIR": str(sub1)}
    )
    # 検証
    assert result.returncode == 0, result.stderr
    # tmux に、同じフォルダを開いたセッションが 2 つあり、名前が違う
    first_name = session_name(folder)
    sub1_name = session_name(folder, sub1)
    assert first_name != sub1_name
    assert sorted(sandbox.sessions()) == sorted([first_name, sub1_name])
    assert sandbox.session_path(first_name) == folder.resolve()
    assert sandbox.session_path(sub1_name) == folder.resolve()
    # 新しいセッションの Claude Code に別のアカウントの設定のフォルダが渡る
    started = sandbox.wait_started(2)
    assert len(started) == 2
    added = [path for path in started if path not in before]
    assert len(added) == 1
    assert added[0].with_suffix(".config").read_text(encoding="utf-8") == str(sub1)
    # 先にあったセッションは立ち上げ直されていない
    assert before[0] in started
    assert before[0].with_suffix(".config").read_text(encoding="utf-8") == ""
