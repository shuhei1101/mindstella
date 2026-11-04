"""左のパネル（絞り込みのドロワー・コメントの一覧・表示の設定・保存待ち）のグレーアウトの結合テストが共有する操作と値。"""

from __future__ import annotations

from playwright.sync_api import Page

__all__ = [
    "SCRIM",
    "SCRIM_ON",
    "click_scrim",
    "detail_above_scrim",
    "main_inert",
    "scrim_visible",
]

# 左のパネル以外を覆うグレーアウト
SCRIM = "div.left-scrim"
SCRIM_ON = f"{SCRIM}.on"

# 本文の右寄り（左のパネルにも詳細パネルの右端にも重ならない、本文の上の点）の位置を窓の幅と高さに対する割合で持つ
_PRESS_X_RATIO = 0.55
_PRESS_Y_RATIO = 0.6


def scrim_visible(page: Page) -> bool:
    """グレーアウトが出ていて、押せる（`visibility` が `visible`）かを返す。"""
    return page.evaluate(
        """selector => {
            const scrim = document.querySelector(selector);
            return scrim !== null && scrim.classList.contains("on") && getComputedStyle(scrim).visibility === "visible";
        }""",
        SCRIM,
    )


def main_inert(page: Page) -> bool:
    """本文（`main`）が、それ自体か中の要素ごと止まっているか（`main` か `main` の中に `inert` があるか）を返す。"""
    return page.evaluate("document.querySelectorAll('main[inert], main [inert]').length > 0")


def click_scrim(page: Page) -> None:
    """本文の右寄りの点を押す（グレーアウトが出ていればグレーアウトを押す）。"""
    size = page.viewport_size
    assert size is not None
    page.mouse.click(size["width"] * _PRESS_X_RATIO, size["height"] * _PRESS_Y_RATIO)


def detail_above_scrim(page: Page) -> bool:
    """詳細パネルをグレーアウトの上に出す印（`body` の `detail-above-scrim`）があるかを返す。"""
    return page.evaluate("document.body.classList.contains('detail-above-scrim')")
