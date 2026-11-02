"""プラグインの読み込み（plugins/mindstella/ の .claude-plugin/plugin.json・.mcp.json・hooks/・skills/・LICENSE）の結合テスト。"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from workspace_fixtures import PORT_ENV, free_port

if TYPE_CHECKING:
    from conftest import RunClaude

PLUGIN_ID = "mindstella@mindstella"

# 取り込まれたプラグインのフォルダに無いこと（リポジトリの開発用のファイル）
OUTSIDE_PLUGIN_NAMES = ["dev", "docs", "tests", ".storybook", "package.json"]

# 常駐サーバーへつなぐ MCP サーバーの設定
MCP_SERVER_CONFIG = {"type": "http", "url": "http://127.0.0.1:${MINDSTELLA_PORT:-8784}/mcp"}

# フックが呼ぶコマンド
RESET_UNREAD_COMMAND = (
    '"${MINDSTELLA_VENV:-$HOME/.mindmap/venv}/bin/python" '
    '"${CLAUDE_PLUGIN_ROOT}/skills/mindmap/scripts/reset_unread.py"'
)
ENSURE_SERVER_COMMAND = 'python3 "${CLAUDE_PLUGIN_ROOT}/skills/mindmap/scripts/ensure_server.py" --hook'
INJECT_SESSION_COMMAND = 'python3 "${CLAUDE_PLUGIN_ROOT}/skills/mindmap/scripts/inject_session.py"'

# PreToolUse のフックを当てるツールの名前
INJECT_MATCHER = "mcp__plugin_mindstella_mindstella__.*"


def _find_installed_plugin(list_json: str) -> dict[str, object]:
    """claude plugin list --json の出力から mindstella@mindstella の行を取り出す。"""
    return next(plugin for plugin in json.loads(list_json) if plugin["id"] == PLUGIN_ID)


def _hook_events(details: str) -> list[str]:
    """claude plugin details の出力の部品の一覧から、hooks のイベントの名前を取り出す。"""
    match = re.search(r"Hooks \(\d+\)\s+([A-Za-z, ]+?)\s+\(", details)
    if match is None:
        raise ValueError(f"部品の一覧に hooks の行が無い: {details}")
    return [name.strip() for name in match.group(1).split(",")]


def test_normal(run_claude: RunClaude, repo_root: Path) -> None:
    """プラグイン mindstella が、スキルのフォルダと常駐サーバーへの接続の設定と 3 つのフックを持って読み込まれる（正常系）。"""
    # 準備
    run_claude("plugin", "marketplace", "add", str(repo_root))

    # 実行
    run_claude("plugin", "install", PLUGIN_ID)
    plugin_list = run_claude("plugin", "list", "--json")
    details = run_claude("plugin", "details", PLUGIN_ID)

    # 検証
    installed = _find_installed_plugin(plugin_list.stdout)
    install_path = Path(str(installed["installPath"]))
    # claude plugin list で mindstella@mindstella が有効である
    assert installed["enabled"] is True
    # 取り込まれたプラグインのフォルダに 2 つのスキルの SKILL.md と、共通の置き場所の 4 つのフォルダがある
    assert (install_path / "skills" / "setup" / "SKILL.md").is_file()
    assert (install_path / "skills" / "session" / "SKILL.md").is_file()
    shared = install_path / "skills" / "mindmap"
    assert (shared / "references").is_dir()
    assert (shared / "playbooks").is_dir()
    assert (shared / "schemas").is_dir()
    assert (shared / "scripts").is_dir()
    # 取り込まれたプラグインのフォルダに、実行の権限を持つ bin/mindstella がある
    assert os.access(install_path / "bin" / "mindstella", os.X_OK)
    # 取り込まれたプラグインのフォルダの直下に LICENSE があり、本文がリポジトリの直下の LICENSE と一致する
    assert (install_path / "LICENSE").is_file()
    assert (install_path / "LICENSE").read_bytes() == (repo_root / "LICENSE").read_bytes()
    # 取り込まれたプラグインのフォルダに .claude-plugin/plugin.json があり、リポジトリの開発用のファイルが無い
    assert (install_path / ".claude-plugin" / "plugin.json").is_file()
    assert [name for name in OUTSIDE_PLUGIN_NAMES if (install_path / name).exists()] == []
    # plugin.json が mcpServers を持たない
    manifest = json.loads(
        (install_path / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert "mcpServers" not in manifest
    # 直下の .mcp.json が、常駐サーバーへ HTTP でつなぐ mindstella だけを持つ
    mcp = json.loads((install_path / ".mcp.json").read_text(encoding="utf-8"))
    assert mcp == {"mcpServers": {"mindstella": MCP_SERVER_CONFIG}}
    # hooks/hooks.json が SessionStart の 2 つのコマンドと、mindstella のツールの PreToolUse の 1 つを持つ
    hooks = json.loads((install_path / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    assert {
        event: [
            (group.get("matcher"), [hook["command"] for hook in group["hooks"]]) for group in groups
        ]
        for event, groups in hooks.items()
    } == {
        "SessionStart": [(None, [RESET_UNREAD_COMMAND, ENSURE_SERVER_COMMAND])],
        "PreToolUse": [(INJECT_MATCHER, [INJECT_SESSION_COMMAND])],
    }
    assert _hook_events(details.stdout) == ["SessionStart", "PreToolUse"]
    # 待ち受けているプロセスの無いポートでは、claude mcp list の mindstella がつながらない
    port = free_port()
    listed = run_claude("mcp", "list", extra_env={PORT_ENV: str(port)}).stdout
    assert f"plugin:mindstella:mindstella: http://127.0.0.1:{port}/mcp (HTTP) - ✘" in listed
