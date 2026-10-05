"""スキル session（/mindstella:session）と共通の置き場所のファイルの形の結合テスト。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .skill_files import (
    PLAYBOOK_NAMES,
    SECTION_PATTERN,
    SERVER_TOOL_NAMES,
    SKILLS_DIR,
    allowed_mcp_tools,
    edits_settings_directly,
    mentions_old_mode,
    missing_plugin_paths,
    playbook_names,
    playbooks_with_wrong_sections,
    playbooks_without_single_default,
    read_skill,
    skill_markdown_texts,
    step_files_in,
    steps_referenced_by,
    texts_with_forbidden_name,
    tools_listed_in,
)

if TYPE_CHECKING:
    from pathlib import Path

    from conftest import RunClaude

# front matter の allowed-tools の値（`init` を除く mindstella の MCP のツールを並べる）
SESSION_ALLOWED_TOOLS = "Read, Agent, WebSearch, WebFetch, " + ", ".join(
    f"mcp__mindstella__{name}"
    for name in (
        "add",
        "update",
        "update_settings",
        "adopt",
        "edit_option",
        "batch",
        "changes_since_read",
        "commit",
        "pending",
        "status",
        "next",
        "impact",
        "find",
        "show",
        "attrs",
        "check",
        "goal",
        "migrate",
        "clear_release",
        "export",
        "preview_url",
        "submissions",
        "take_submission",
    )
)

# 版を比べる呼び方
PLAN_CALL = "`plan: true`"

# SKILL.md が持つ、記録の書き方の節の見出し（`## ` を除く）
RECORD_SECTION = "記録の書き方"

# 記録を書き換え終えたら `commit` を呼ぶステップのファイル
COMMIT_STEP_FILES = ["取り込み.md", "ヒアリング.md", "リサーチ.md", "方針転換.md"]

# スキル session の steps/ のファイル
SESSION_STEP_FILES = [
    "ゴール判定.md",
    "ヒアリング.md",
    "プレビュー.md",
    "リサーチ.md",
    "取り込み.md",
    "方針転換.md",
    "範囲の見直し.md",
]


def test_normal(run_claude: RunClaude, repo_root: Path) -> None:
    """スキル session と共通の置き場所のファイルが制約どおりの形で、プラグインの検証を通る（正常系）。"""
    # 実行
    front_matter, body = read_skill("session")
    texts = skill_markdown_texts("session")
    validate = run_claude("plugin", "validate", str(repo_root))
    # 検証
    # front matter の name が session、allowed-tools が制約の値と一致する
    assert front_matter["name"] == "session"
    assert front_matter["allowed-tools"] == SESSION_ALLOWED_TOOLS
    assert front_matter["description"]
    # steps/ に 7 つのステップのファイルがあり、SKILL.md のステップの表がその全てを指す
    assert step_files_in("session") == SESSION_STEP_FILES
    assert steps_referenced_by(body) == SESSION_STEP_FILES
    # SKILL.md が `## 記録の書き方` の節を持つ
    assert RECORD_SECTION in SECTION_PATTERN.findall(body)
    # SKILL.md と steps/ の本文の ${CLAUDE_PLUGIN_ROOT}/ で始まるパスが全てリポジトリの中にある
    assert missing_plugin_paths(texts) == []
    # 本文が呼ぶツールが全て allowed-tools にあり、サーバーのツールの一覧にある
    called = tools_listed_in(texts)
    assert called != []
    assert set(called) <= set(allowed_mcp_tools(front_matter))
    assert set(allowed_mcp_tools(front_matter)) <= set(SERVER_TOOL_NAMES)
    # 本文が mindmap.py・build・preview.html を指さない
    assert mentions_old_mode(texts) == []
    # 本文が mindmap.yaml を Edit ツールで直す手順を持たない
    assert edits_settings_directly(texts) == []
    # 本文が migrate を plan: true で呼び、その後に submissions を呼ぶ
    preparation = next(line for line in body.splitlines() if line.startswith("| 準備 |"))
    assert "`migrate`" in preparation
    assert PLAN_CALL in preparation
    assert preparation.index("`migrate`") < preparation.index("`submissions`")
    # 準備が changes_since_read を submissions より前に呼ぶ
    assert "`changes_since_read`" in preparation
    assert preparation.index("`changes_since_read`") < preparation.index("`submissions`")
    # 本文に、MCP のツールが無いとき起動スクリプトを案内して止まる分岐がある
    assert "bin/mindstella" in preparation
    assert "止まる" in preparation
    # steps/プレビュー.md が preview_url を呼ぶ
    preview_step = (SKILLS_DIR / "session" / "steps" / "プレビュー.md").read_text(encoding="utf-8")
    assert "`preview_url`" in preview_step
    # steps/範囲の見直し.md が update_settings を呼ぶ
    scope_step = (SKILLS_DIR / "session" / "steps" / "範囲の見直し.md").read_text(encoding="utf-8")
    assert "`update_settings`" in scope_step
    # steps/取り込み.md が batch を呼ぶ
    capture_step = (SKILLS_DIR / "session" / "steps" / "取り込み.md").read_text(encoding="utf-8")
    assert "`batch`" in capture_step
    # 取り込み・ヒアリング・リサーチ・方針転換のステップが commit を呼ぶ
    for step_file in COMMIT_STEP_FILES:
        step = (SKILLS_DIR / "session" / "steps" / step_file).read_text(encoding="utf-8")
        assert "`commit`" in step
    # skills/mindmap/ に SKILL.md が無く、references/・playbooks/ がある
    assert not (SKILLS_DIR / "mindmap" / "SKILL.md").exists()
    assert (SKILLS_DIR / "mindmap" / "references").is_dir()
    assert (SKILLS_DIR / "mindmap" / "playbooks").is_dir()
    # playbooks/ に システム開発・調査・資料作り・壁打ち の 4 つのガイドがある
    assert playbook_names() == PLAYBOOK_NAMES
    # どのガイドも 6 つの節をその並びで持つ
    assert playbooks_with_wrong_sections() == []
    # どのガイドも `## ゴールの候補` に（既定）の行を 1 つだけ持つ
    assert playbooks_without_single_default() == []
    # スキルの全ての Markdown に特定の開発基盤の名前が無い
    assert texts_with_forbidden_name() == []
    # claude plugin validate が終了コード 0（失敗すれば run_claude が例外にする）
    assert validate.returncode == 0
