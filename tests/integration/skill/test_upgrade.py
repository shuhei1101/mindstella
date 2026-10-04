"""スキル upgrade（/mindstella:upgrade）のファイルの形の結合テスト。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .skill_files import (
    SERVER_TOOL_NAMES,
    SKILLS_DIR,
    allowed_mcp_tools,
    mentions_old_mode,
    missing_plugin_paths,
    read_skill,
    skill_markdown_texts,
    texts_with_forbidden_name,
    tools_listed_in,
)

if TYPE_CHECKING:
    from pathlib import Path

    from conftest import RunClaude

# front matter の allowed-tools の値
UPGRADE_ALLOWED_TOOLS = "Read, mcp__mindstella__migrate, mcp__mindstella__check"

# 本文のツールの表に並ぶ migrate の呼び方（版を比べる・手順を当てる・値を入れる・版を書き換える）
MIGRATE_CALLS = ["plan: true", "values", "record: true"]


def test_normal(run_claude: RunClaude, repo_root: Path) -> None:
    """スキル upgrade のファイルが制約どおりの形で、プラグインの検証を通る（正常系）。"""
    # 実行
    front_matter, body = read_skill("upgrade")
    texts = skill_markdown_texts("upgrade")
    validate = run_claude("plugin", "validate", str(repo_root))
    # 検証
    # front matter の name が upgrade、allowed-tools が制約の値と一致する
    assert front_matter["name"] == "upgrade"
    assert front_matter["allowed-tools"] == UPGRADE_ALLOWED_TOOLS
    assert front_matter["description"]
    # ファイルは SKILL.md だけ
    assert [path.name for path in (SKILLS_DIR / "upgrade").iterdir()] == ["SKILL.md"]
    # 本文の ${CLAUDE_PLUGIN_ROOT}/ で始まるパスが全てリポジトリの中にある
    assert missing_plugin_paths(texts) == []
    # 本文が呼ぶツールが全て allowed-tools にあり、サーバーのツールの一覧にある
    assert tools_listed_in(texts) == ["migrate", "check"]
    assert set(allowed_mcp_tools(front_matter)) <= set(SERVER_TOOL_NAMES)
    # 本文のツールの一覧に migrate（plan・手順を当てる・values・record）と check がある
    assert [call for call in MIGRATE_CALLS if f"`{call}`" not in body] == []
    assert "| `migrate`（手順を当てる） | `workspace` |" in body
    # 本文が mindmap.py・build・check-env を指さない
    assert mentions_old_mode(texts) == []
    # 本文に、MCP のツールが無いとき起動スクリプトを案内して止まる分岐がある
    assert "bin/mindstella" in body
    assert "止まる" in body
    # スキルの Markdown に特定の開発基盤の名前が無い
    assert texts_with_forbidden_name() == []
    # claude plugin validate が終了コード 0（失敗すれば run_claude が例外にする）
    assert validate.returncode == 0
