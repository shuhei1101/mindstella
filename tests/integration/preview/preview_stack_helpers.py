"""幅 900px 以下の、詳細パネルと左のパネル（表示の設定・コメントの一覧・絞り込みのドロワー）の重なりの結合テストが共有する操作と値。"""

from __future__ import annotations

from playwright.sync_api import Page

__all__ = [
    "DETAIL_HASH",
    "NARROW_VIEWPORT",
    "WIDE_VIEWPORT",
    "has_left_front",
    "is_inert",
    "open_narrow",
    "wait_front",
]

# 詳細パネルと左のパネルが、どちらも画面の幅いっぱいに出る幅（スマホの幅）と、どちらも画面の幅いっぱいに出ない幅
NARROW_VIEWPORT = {"width": 390, "height": 844}
WIDE_VIEWPORT = {"width": 1200, "height": 800}

# 検討事項の表で D-1 の詳細パネルを開く URL のハッシュ
DETAIL_HASH = "#tab=decisions&view=table&id=D-1"

# 重なりを調べる名前と、そのパネルの選択子
_PANELS = {
    "detail": "aside.panel",
    "settings": "aside.settings-drawer",
    "comments": "aside.comments-panel",
    "drawer": "dialog.drawer",
}

# 画面の真ん中の点（トップバーの下で、全てのパネルが広がる）にある一番前のパネルの名前を返す関数
_FRONT_PANEL_FN = """panels => {
    const hit = document.elementFromPoint(window.innerWidth / 2, window.innerHeight * 0.6);
    const found = Object.entries(panels).find(([, selector]) => hit?.closest(selector));
    return found === undefined ? null : found[0];
}"""


def open_narrow(page: Page) -> None:
    """幅を 390px にし、詳細パネルが開くのを待つ。"""
    page.set_viewport_size(NARROW_VIEWPORT)
    page.wait_for_selector("aside.panel.open")


def wait_front(page: Page, name: str) -> None:
    """一番前に見えているパネルが name になるのを、開く動きが終わるまで待つ。"""
    page.wait_for_function(f"([panels, expected]) => ({_FRONT_PANEL_FN})(panels) === expected", arg=[_PANELS, name])


def is_inert(page: Page, name: str) -> bool:
    """名前のパネルが `inert`（後ろになって操作できない）かを返す。"""
    return page.evaluate("selector => document.querySelector(selector).inert", _PANELS[name])


def has_left_front(page: Page) -> bool:
    """左のパネルを前に出している印（`body` の `left-front`）があるかを返す。"""
    return page.evaluate("document.body.classList.contains('left-front')")
