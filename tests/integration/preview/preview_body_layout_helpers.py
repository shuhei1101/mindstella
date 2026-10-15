"""本文の差分の並べ方の結合テストが共有する、ワークスペースの作り方と値、操作・読み取りの関数。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from playwright.sync_api import Page
from preview_head_title_helpers import ANIMATIONS_FINISHED_JS
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace

__all__ = [
    "HTML_BODY_AFTER",
    "HTML_BODY_BEFORE",
    "INLINE_NAME",
    "LAYOUT_GROUP_NAME",
    "LAYOUT_SWITCH",
    "LINKED_V1_BODY",
    "LINKED_V2_BODY",
    "MARKDOWN_A1_AFTER",
    "MARKDOWN_A1_BEFORE",
    "MARKDOWN_D1_AFTER",
    "MARKDOWN_D1_BEFORE",
    "SIDE_HASH",
    "SIDE_NAME",
    "SIDE_VIEWPORT",
    "build_body_layout_workspace",
    "build_html_body_layout_workspace",
    "build_linked_body_layout_workspace",
    "layout_buttons",
    "open_side_by_side",
    "rows_of_columns",
    "seed_side_layout",
]

# 切り替えのボタンの組と、その読み上げの名前、押すボタンの名前
LAYOUT_SWITCH = ".sbs-switch"
LAYOUT_GROUP_NAME = "本文の差分の並べ方"
INLINE_NAME = "インライン"
SIDE_NAME = "左右に並べる"

# 差分の表示で資料 A-1 を開く URL のハッシュ（まとまり V-2）
SIDE_HASH = "#tab=docs&id=A-1&diff=V-2"

# 開く画面の幅と高さ（資料の詳細パネルの本文の幅が 560px 以上になる）
SIDE_VIEWPORT = {"width": 1280, "height": 800}

# 左右に並べた本文が置かれるまで待つ上限ミリ秒
SIDE_TIMEOUT_MS = 15_000

# 資料 A-1 の書き換える前と後の本文（1 つ目の段落を消して、末尾に段落を足す）
MARKDOWN_A1_BEFORE = "1 つ目の段落です。\n\n2 つ目の段落です。\n\n3 つ目の段落です。\n"
MARKDOWN_A1_AFTER = "2 つ目の段落です。\n\n3 つ目の段落です。\n\n4 つ目の段落です。\n"

# 検討事項 D-1 の書き換える前と後の本文（2 つ目の段落を書き換える）
MARKDOWN_D1_BEFORE = "1 つ目の段落です。\n\n2 つ目の段落は、来週に決めます。\n\n3 つ目の段落です。\n"
MARKDOWN_D1_AFTER = "1 つ目の段落です。\n\n2 つ目の段落は、今週に決めます。\n\n3 つ目の段落です。\n"

# 段落 3 つを 1 行ずつ持つ HTML の本文と、2 つ目の段落を書き換えた本文
HTML_BODY_BEFORE = "<p>1 つ目の段落</p>\n<p>2 つ目の段落</p>\n<p>3 つ目の段落</p>\n"
HTML_BODY_AFTER = "<p>1 つ目の段落</p>\n<p>書き直した 2 つ目の段落</p>\n<p>3 つ目の段落</p>\n"

# 見出し・用語・項目の ID・図を持つ A-1 の本文の書き換える前と後（段落を書き換え、図の記法を変える）
LINKED_V1_BODY = (
    "## 保存先\n\n保存先と D-1 の話です。\n\n消す段落です。\n\n"
    "```mermaid\nflowchart LR\n  A[一覧] --> B[詳細]\n```\n"
)
LINKED_V2_BODY = (
    "## 保存先\n\n保存先と D-1 の話です。\n\n足す段落です。\n\n"
    "```mermaid\nflowchart LR\n  A[一覧] --> B[詳細パネル]\n  B --> C[全画面]\n```\n"
)

# 切り替えのボタンの押し状態を返す
_BUTTONS_JS = """(scope) => [...document.querySelectorAll(`${scope} .sbs-switch button`)].map((button) => ({
    name: button.textContent.trim(),
    layout: button.getAttribute('data-layout'),
    pressed: button.getAttribute('aria-pressed'),
}))"""

# 左右の列ごとに、直下の行の位置・高さ・変えた行か・向かいの空きか・文字を返す
_ROWS_JS = """(scope) => [...document.querySelectorAll(`${scope} .sbs .sbs-col`)].map((column) =>
    [...column.querySelectorAll(':scope > .sbs-row')].map((row) => {
        const rect = row.getBoundingClientRect();
        return {
            top: rect.top,
            height: rect.height,
            changed: row.classList.contains('sbs-chg'),
            gap: row.classList.contains('sbs-gap'),
            text: row.textContent.trim(),
        };
    })
)"""


def _call(call_tool: CallTool, name: str, **arguments: Any) -> None:
    """ツールを呼び、エラーでないことを確かめる。"""
    result = call_tool(name, **arguments)
    assert result.is_error is False, result.text


def build_body_layout_workspace(make_workspace: MakeWorkspace, call_tool: CallTool) -> Path:
    """段落 3 つの Markdown の本文を持つ資料 A-1 と検討事項 D-1 を足して `commit`（V-1）し、A-1 の 1 つ目の段落を消して末尾に段落を足し、D-1 の 2 つ目の段落を書き換えて `commit`（V-2）したワークスペースを作る。"""
    root = make_workspace()
    workspace = str(root)
    decision = {
        "title": "いつ決めるか",
        "status": "未決定",
        "options": [
            {"key": "A", "content": "今週に決める"},
            {"key": "B", "content": "来週に決める"},
        ],
        "weight": "大",
        "category": "データ構造",
        "phase": "要件",
        "target": "mindmap",
    }
    doc = {"title": "工程の資料", "kind": "図", "deliverable": False, "status": "下書き"}
    _call(call_tool, "add", workspace=workspace, kind="doc", item={**doc, "body_markdown": MARKDOWN_A1_BEFORE})
    _call(
        call_tool, "add", workspace=workspace, kind="decision", item={**decision, "body_markdown": MARKDOWN_D1_BEFORE}
    )
    _call(call_tool, "commit", workspace=workspace, summary="足す")
    _call(call_tool, "update", workspace=workspace, id="A-1", item={"body_markdown": MARKDOWN_A1_AFTER})
    _call(call_tool, "update", workspace=workspace, id="D-1", item={"body_markdown": MARKDOWN_D1_AFTER})
    _call(call_tool, "commit", workspace=workspace, summary="直す")
    return root


def build_html_body_layout_workspace(make_workspace: MakeWorkspace, call_tool: CallTool) -> Path:
    """段落 3 つを 1 行ずつ持つ HTML の本文の資料 A-1 を足して `commit`（V-1）し、2 つ目の段落を書き換えて `commit`（V-2）したワークスペースを作る。"""
    root = make_workspace()
    workspace = str(root)
    doc = {"title": "画面のモック", "kind": "モック", "status": "下書き", "deliverable": False}
    _call(call_tool, "add", workspace=workspace, kind="doc", item={**doc, "body_html": HTML_BODY_BEFORE})
    _call(call_tool, "commit", workspace=workspace, summary="足す")
    _call(call_tool, "update", workspace=workspace, id="A-1", item={"body_html": HTML_BODY_AFTER})
    _call(call_tool, "commit", workspace=workspace, summary="直す")
    return root


def build_linked_body_layout_workspace(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> Path:
    """見出し・用語 G-1・項目の ID D-1・図を持つ資料 A-1 の本文を書き換えて `commit`（V-1）したワークスペースを作る。"""
    root = make_workspace(
        make_item("A-1"),
        make_item("D-1"),
        make_item("G-1", title="保存先", meaning="記録を置く場所"),
        bodies={"A-1.md": LINKED_V1_BODY},
    )
    workspace = str(root)
    _call(call_tool, "update", workspace=workspace, id="A-1", item={"body_markdown": LINKED_V2_BODY})
    _call(call_tool, "commit", workspace=workspace, summary="段落と図を直す")
    return root


def seed_side_layout(page: Page, sel: str | None = None) -> None:
    """ページを開く前に、端末の保存領域へ本文の差分を左右に並べる上書き（と、あれば選んだ時点）を入れる。"""
    value = json.dumps({"bodyLayout": "side", "diffSel": sel})
    page.add_init_script(
        "try { if (!sessionStorage.getItem('mindmap-seeded')) {"
        f" localStorage.setItem('mindmap-preview', {json.dumps(value)});"
        " sessionStorage.setItem('mindmap-seeded', '1'); } } catch (e) {}"
    )


def layout_buttons(page: Page, scope: str) -> list[dict[str, str | None]]:
    """切り替えのボタンを並びのまま、文言・並べ方・押している状態で返す（切り替えが無ければ空）。"""
    return page.evaluate(_BUTTONS_JS, scope)


def rows_of_columns(page: Page, scope: str) -> list[list[dict[str, Any]]]:
    """左右に並べた本文の左右の列ごとに、行の位置・高さ・変えた行か・向かいの空きか・文字を返す。"""
    return page.evaluate(_ROWS_JS, scope)


def open_side_by_side(page: Page, scope: str) -> None:
    """左右に並べた本文が置かれ、パネルの動きが終わるまで待つ。"""
    page.wait_for_selector(f"{scope} .sbs", timeout=SIDE_TIMEOUT_MS)
    page.evaluate(ANIMATIONS_FINISHED_JS)
