"""起動スクリプトで立ち上げる（依存を確かめ、tmux の中で MCP サーバーを渡した Claude Code を立ち上げる）の E2E テスト。

本物の Claude Code は立ち上げず、偽の `claude` が受け取った MCP の設定と環境変数を確かめる。
隔離した環境（偽の `claude`・専用のソケットの `tmux`）は `tests/launch_fixtures.py`。
"""

from __future__ import annotations

import os
from pathlib import Path

from launch_fixtures import (
    PLUGIN_DIR,
    LaunchSandbox,
    copy_plugin,
    read_mcp_config,
    read_tool_names,
    session_name,
)
from workspace_fixtures import MakeVenv, McpServer


def test_normal(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """依存が揃っていれば、tmux のセッションの中で mindstella の MCP サーバーを渡した Claude Code を立てる（正常系）。"""
    # 準備
    folder = sandbox.root / "家計簿アプリ"
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 0, result.stderr
    # tmux に、ワークスペースのフォルダを開いたセッションがある
    name = session_name(folder)
    assert sandbox.sessions() == [name]
    assert sandbox.session_path(name) == folder.resolve()
    # Claude Code に MCP の設定が渡り、起動コマンドが installPath の版のフォルダのサーバーを指す
    started = sandbox.wait_started()
    assert len(started) == 1
    mindstella = read_mcp_config(started[0])["mcpServers"]["mindstella"]
    assert mindstella["command"] == str(ready_venv / "bin" / "python")
    assert mindstella["args"] == [str(PLUGIN_DIR / "skills" / "mindmap" / "scripts" / "server.py")]
    # その設定どおりに MCP サーバーを立てると、そのサーバーが登録する mindstella のツールの一覧が返る
    server_script = Path(mindstella["args"][0])
    server = McpServer(
        python=mindstella["command"],
        env={**os.environ, "PYTHONUTF8": "1"},
        cwd=folder,
        script=server_script,
    )
    try:
        assert [tool["name"] for tool in server.list_tools()] == read_tool_names(server_script)
    finally:
        server.stop()
    # Claude Code に設定のフォルダの CLAUDE_CONFIG_DIR が渡る
    assert started[0].with_suffix(".config").read_text(encoding="utf-8") == str(sandbox.config_dir)


def test_normal_when_plugin_upgraded(
    sandbox: LaunchSandbox, ready_venv: Path, tmp_path: Path
) -> None:
    """古い版のフォルダの起動スクリプトを叩いても、新しい版のフォルダのサーバーを指す（正常系）。"""
    # 準備
    old_dir = copy_plugin(tmp_path / "plugin-old")
    new_dir = copy_plugin(tmp_path / "plugin-new")
    sandbox.write_claude([{"id": "mindstella@mindstella", "installPath": str(new_dir)}])
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv, script=old_dir / "bin" / "mindstella")
    # 検証
    assert result.returncode == 0, result.stderr
    started = sandbox.wait_started()
    assert len(started) == 1
    mindstella = read_mcp_config(started[0])["mcpServers"]["mindstella"]
    assert mindstella["args"] == [str(new_dir / "skills" / "mindmap" / "scripts" / "server.py")]


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
