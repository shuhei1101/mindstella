"""bin/mindstella（起動スクリプト）の結合テスト。

隔離した環境（偽の `claude`・専用のソケットの `tmux`）は `tests/launch_fixtures.py`。
MCP の設定どおりのサーバーは、本物の MCP サーバーとして立てて確かめる。
"""

from __future__ import annotations

import os
from pathlib import Path

from launch_fixtures import PLUGIN_DIR, LaunchSandbox, copy_plugin, read_mcp_config, session_name
from workspace_fixtures import McpServer

from .fixture_types import MakeVenv


def test_normal(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """依存がそろっていれば、今の版のサーバーを渡した Claude Code を tmux のセッションで立てる（正常系）。"""
    # 準備
    folder = sandbox.root / "家計簿アプリ"
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 0, result.stderr
    assert folder.is_dir()
    name = session_name(folder)
    assert sandbox.sessions() == [name]
    assert sandbox.session_path(name) == folder.resolve()
    started = sandbox.wait_started()
    assert len(started) == 1
    config = read_mcp_config(started[0])
    mindstella = config["mcpServers"]["mindstella"]
    assert mindstella["command"] == str(ready_venv / "bin" / "python")
    assert mindstella["args"] == [str(PLUGIN_DIR / "skills" / "mindmap" / "scripts" / "server.py")]
    assert started[0].with_suffix(".config").read_text(encoding="utf-8") == str(sandbox.config_dir)
    # その MCP の設定どおりにサーバーを立ててつなぐと、ツールの一覧が返る
    server = McpServer(
        python=mindstella["command"],
        env={**os.environ, "PYTHONUTF8": "1"},
        cwd=folder,
        script=Path(mindstella["args"][0]),
    )
    try:
        assert len(server.list_tools()) == 26
    finally:
        server.stop()
    assert f"tmux attach-session -t ={name}" in result.stdout


def test_normal_when_external_settings(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """設定されている外から見る環境変数だけを MCP の設定の env に書く（正常系）。"""
    # 準備
    external = {
        "MINDSTELLA_ALLOWED_HOSTS": "preview.example.test",
        "MINDSTELLA_PREVIEW_START_HOOK": "pub add",
    }
    # 実行
    with_env = sandbox.launch("家計簿アプリ", venv=ready_venv, extra_env=external)
    without_env = sandbox.launch("別の話し合い", venv=ready_venv)
    # 検証
    assert with_env.returncode == 0, with_env.stderr
    assert without_env.returncode == 0, without_env.stderr
    started = sandbox.wait_started(2)
    assert len(started) == 2
    configs = {
        path: read_mcp_config(path)["mcpServers"]["mindstella"] for path in started
    }
    with_config = [config for config in configs.values() if "env" in config]
    without_config = [config for config in configs.values() if "env" not in config]
    assert [config["env"] for config in with_config] == [external]
    assert len(without_config) == 1


def test_normal_when_plugin_upgraded(
    sandbox: LaunchSandbox, ready_venv: Path, tmp_path: Path
) -> None:
    """古い版のフォルダのスクリプトを叩いても、新しい版のサーバーを指す（正常系）。"""
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
    config = read_mcp_config(started[0])
    assert config["mcpServers"]["mindstella"]["args"] == [
        str(new_dir / "skills" / "mindmap" / "scripts" / "server.py")
    ]


def test_normal_when_session_exists(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """既にあるセッションには新しく立てず、つなぐコマンドを返す（正常系）。"""
    # 準備
    first = sandbox.launch("家計簿アプリ", venv=ready_venv)
    assert first.returncode == 0, first.stderr
    sandbox.wait_started()
    sessions_before = sandbox.sessions()
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 0, result.stderr
    assert sandbox.sessions() == sessions_before
    assert len(sandbox.started()) == 1
    assert "既にある" in result.stderr
    assert f"tmux attach-session -t ={sessions_before[0]}" in result.stdout


def test_error_when_dependency_missing(sandbox: LaunchSandbox, make_venv: MakeVenv) -> None:
    """ライブラリを入れていない仮想環境では、そろえるコマンドを示して何も立てない（異常系）。"""
    # 準備
    bare_venv = make_venv("bare-venv", with_libraries=False)
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=bare_venv)
    # 検証
    assert result.returncode == 1
    for package in ("PyYAML", "jsonschema", "mcp"):
        assert package in result.stderr
    assert "-m pip install" in result.stderr
    assert sandbox.sessions() == []
    assert sandbox.started() == []


def test_error_when_tmux_missing(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """tmux が無ければ、入れるよう示して Claude Code を立てない（異常系）。"""
    # 準備
    sandbox.remove_tool("tmux")
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 1
    assert "tmux" in result.stderr
    assert sandbox.started() == []


def test_error_when_claude_missing(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """claude が無ければ、入れるよう示して止まる（異常系）。"""
    # 準備
    sandbox.remove_tool("claude")
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 1
    assert "claude" in result.stderr
    assert sandbox.sessions() == []


def test_error_when_plugin_not_installed(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """プラグインの一覧に mindstella が無ければ、インストールを案内して止まる（異常系）。"""
    # 準備
    sandbox.write_claude([])
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 1
    assert "mindstella@mindstella" in result.stderr
    assert "インストール" in result.stderr
    assert sandbox.sessions() == []


def test_error_when_folder_missing(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """引数が無ければ、使い方を出して止まる（異常系）。"""
    # 実行
    result = sandbox.launch(venv=ready_venv)
    # 検証
    assert result.returncode == 2
    assert "使い方" in result.stderr
    assert sandbox.started() == []


def test_normal_when_same_folder_name_elsewhere(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """名前が同じでも場所が違うフォルダは、別のセッションを立てる（正常系）。"""
    # 準備
    first = sandbox.launch("仕事/家計簿アプリ", venv=ready_venv)
    assert first.returncode == 0, first.stderr
    sandbox.wait_started()
    work_folder = sandbox.root / "仕事" / "家計簿アプリ"
    personal_folder = sandbox.root / "個人" / "家計簿アプリ"
    # 実行
    result = sandbox.launch("個人/家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 0, result.stderr
    assert sorted(sandbox.sessions()) == sorted(
        [session_name(work_folder), session_name(personal_folder)]
    )
    assert sandbox.session_path(session_name(work_folder)) == work_folder.resolve()
    assert sandbox.session_path(session_name(personal_folder)) == personal_folder.resolve()
    assert f"tmux attach-session -t ={session_name(personal_folder)}" in result.stdout
    assert "既にある" not in result.stderr
