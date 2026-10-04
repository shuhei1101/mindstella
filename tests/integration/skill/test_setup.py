"""スキル setup（/mindstella:setup）のファイルの形の結合テスト。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .skill_files import (
    SERVER_TOOL_NAMES,
    allowed_mcp_tools,
    mentions_old_mode,
    missing_plugin_paths,
    read_skill,
    skill_markdown_texts,
    step_files_in,
    steps_referenced_by,
    tools_listed_in,
)

if TYPE_CHECKING:
    from pathlib import Path

    from conftest import RunClaude

# front matter の allowed-tools の値
SETUP_ALLOWED_TOOLS = (
    "Read, mcp__mindstella__init, mcp__mindstella__status, mcp__mindstella__migrate"
)

# 版を比べる呼び方
PLAN_CALL = "`plan: true`"

# スキル setup の steps/ のファイル
SETUP_STEP_FILES = ["新しいワークスペース.md", "既存のワークスペース.md"]


def test_normal(run_claude: RunClaude, repo_root: Path) -> None:
    """スキル setup のファイルが制約どおりの形で、プラグインの検証を通る（正常系）。"""
    # 実行
    front_matter, body = read_skill("setup")
    texts = skill_markdown_texts("setup")
    validate = run_claude("plugin", "validate", str(repo_root))
    # 検証
    # front matter の name が setup、allowed-tools が制約の値と一致する
    assert front_matter["name"] == "setup"
    assert front_matter["allowed-tools"] == SETUP_ALLOWED_TOOLS
    assert front_matter["description"]
    # 本文の ${CLAUDE_PLUGIN_ROOT}/ で始まるパスが全てリポジトリの中にある
    assert missing_plugin_paths(texts) == []
    # 本文が指す steps/ のファイルが全てある
    assert steps_referenced_by(body) == SETUP_STEP_FILES
    assert step_files_in("setup") == SETUP_STEP_FILES
    # 本文が呼ぶツールが全て allowed-tools にあり、サーバーのツールの一覧にある
    called = tools_listed_in(texts)
    assert called != []
    assert set(called) <= set(allowed_mcp_tools(front_matter))
    assert set(allowed_mcp_tools(front_matter)) <= set(SERVER_TOOL_NAMES)
    # 本文が mindmap.py・build・check-env を指さない
    assert mentions_old_mode(texts) == []
    # 本文が migrate を plan: true で呼ぶ
    assert any("`migrate`" in text and PLAN_CALL in text for text in texts)
    # 本文に、MCP のツールが無いとき起動スクリプトを案内して止まる分岐がある
    assert any("bin/mindstella" in text and "止まる" in text for text in texts)
    # claude plugin validate が終了コード 0（失敗すれば run_claude が例外にする）
    assert validate.returncode == 0
