"""差分のミニマップの E2E テストが共有する値と、ワークスペースの作り方、画面の読み取りの関数。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import Page
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace

__all__ = [
    "FULL_SCOPE",
    "MINIMAP_COMMIT_SUMMARY",
    "MINIMAP_TIMEOUT_MS",
    "MINIMAP_VIEWPORT_WIDTH",
    "PANEL_SCOPE",
    "added_paragraph_in_view",
    "block_kinds",
    "build_minimap_workspace",
    "mark_shapes",
    "wait_added_paragraph_in_view",
]

# 詳細パネルと詳細の全画面（本文のスクロール領域とミニマップを持つ外側）
PANEL_SCOPE = "aside.panel"
FULL_SCOPE = "dialog.full"

# ミニマップの印が置かれる・足した段落が見える範囲に入るまで待つ上限ミリ秒
MINIMAP_TIMEOUT_MS = 15_000

# 画面の幅（詳細パネルが本文の右に開く幅）
MINIMAP_VIEWPORT_WIDTH = 1280

# 書き換えのまとまりの説明
MINIMAP_COMMIT_SUMMARY = "段落を消して足す"

# 書き換える前の A-1 の本文（本文のスクロール領域の高さを超える 40 個の段落）
BODY_BEFORE = (
    "\n\n".join(
        f"{number} 番目の段落です。本文を縦に長くするための文です。" for number in range(1, 41)
    )
    + "\n"
)

# 足した段落
ADDED_PARAGRAPH = "足した段落です。"

# 書き換えた後の A-1 の本文（1 つ目の段落を消し、末尾に段落を 1 つ足す）
BODY_AFTER = (
    "\n\n".join(
        [f"{number} 番目の段落です。本文を縦に長くするための文です。" for number in range(2, 41)]
        + [ADDED_PARAGRAPH]
    )
    + "\n"
)

# 書き換えない A-2 の本文
UNCHANGED_BODY = "変わらない本文です。\n"

# 印ごとに、種類のクラス・形（枠の太さ・塗り）・位置を上から返す
_SHAPES_JS = """(scope) => [...document.querySelectorAll(`${scope} .df-map .df-map-m`)].map((mark) => {
    const shape = getComputedStyle(mark.querySelector('i'));
    return {
        kind: [...mark.classList].find((name) => /^df-(add|del|chg)$/.test(name)) ?? null,
        border: shape.borderTopWidth,
        fill: shape.backgroundColor,
        top: mark.getBoundingClientRect().top,
    };
})"""

# 本文の差分の印（消した・足した段落）を、本文の中の上から種類（del・ins）で返す
_BLOCKS_JS = """(scope) => [...document.querySelectorAll(`${scope} .panel-body .df-blk`)].map(
    (block) => block.tagName.toLowerCase()
)"""

# 足した段落が、本文のスクロール領域の見える範囲に入っているか
_ADDED_IN_VIEW_JS = """([scope, text]) => {
    const body = document.querySelector(`${scope} .panel-body`);
    const added = [...body.querySelectorAll('ins.df-blk')].find((block) => block.textContent.includes(text));
    const bodyRect = body.getBoundingClientRect();
    const addedRect = added.getBoundingClientRect();
    return addedRect.top >= bodyRect.top && addedRect.bottom <= bodyRect.bottom;
}"""


def build_minimap_workspace(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> Path:
    """本文に段落を 40 個持つ資料 A-1 の 1 つ目の段落を消し、末尾に段落を足して `commit` した、A-2 を持つワークスペースを作る。"""
    root = make_workspace(
        make_item("A-1"),
        make_item("A-2"),
        bodies={"A-1.md": BODY_BEFORE, "A-2.md": UNCHANGED_BODY},
    )
    workspace = str(root)
    updated = call_tool("update", workspace=workspace, id="A-1", item={"body_markdown": BODY_AFTER})
    assert updated.is_error is False, updated.text
    committed = call_tool("commit", workspace=workspace, summary=MINIMAP_COMMIT_SUMMARY)
    assert committed.is_error is False, committed.text
    return root


def mark_shapes(page: Page, scope: str) -> list[dict[str, Any]]:
    """帯の印を上から、種類・形・位置で返す。"""
    return page.evaluate(_SHAPES_JS, scope)


def block_kinds(page: Page, scope: str) -> list[str]:
    """本文の差分の印を、本文の中の上から種類（del・ins）で返す。"""
    return page.evaluate(_BLOCKS_JS, scope)


def added_paragraph_in_view(page: Page, scope: str) -> bool:
    """足した段落が、本文のスクロール領域の見える範囲に入っているかを返す。"""
    return page.evaluate(_ADDED_IN_VIEW_JS, [scope, ADDED_PARAGRAPH])


def wait_added_paragraph_in_view(page: Page, scope: str) -> None:
    """足した段落が、本文のスクロール領域の見える範囲に入るまで待つ。"""
    page.wait_for_function(
        _ADDED_IN_VIEW_JS, arg=[scope, ADDED_PARAGRAPH], timeout=MINIMAP_TIMEOUT_MS
    )
