"""画面の領域（窓の高さに収め、帯の下の領域の中でスクロールする作り）の結合テストが共有する操作と値。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

__all__ = [
    "BOUNDARY_HEIGHT",
    "MAP_BOUNDARY_WIDTHS",
    "NARROW_VIEWPORT",
    "TABLE_BOARD_BOUNDARY_WIDTHS",
    "WIDE_VIEWPORT",
    "assert_bands_stay",
    "assert_page_does_not_scroll",
    "assert_region_mode",
    "region_metrics",
]

# 表・ボード・マップを領域の高さいっぱいに広げる幅（721px 以上・901px 以上）の窓と、それより狭い窓
WIDE_VIEWPORT = {"width": 1280, "height": 720}
NARROW_VIEWPORT = {"width": 600, "height": 720}

# 窓・本文の領域・指した要素のスクロールの大きさと位置を読む（`selector` が無ければ null）
_REGION_SCRIPT = """(selector) => {
    const content = document.querySelector('.content');
    const target = selector === null ? null : document.querySelector(selector);
    const rect = (element) => {
        if (element === null) return null;
        const box = element.getBoundingClientRect();
        return {top: box.top, bottom: box.bottom};
    };
    return {
        pageScrollHeight: document.documentElement.scrollHeight,
        pageScrollWidth: document.documentElement.scrollWidth,
        innerHeight,
        innerWidth,
        scrollY,
        content: {
            clientHeight: content.clientHeight,
            scrollHeight: content.scrollHeight,
            ...rect(content),
        },
        target: target === null ? null : {
            clientHeight: target.clientHeight,
            scrollHeight: target.scrollHeight,
            clientWidth: target.clientWidth,
            scrollWidth: target.scrollWidth,
            ...rect(target),
        },
    };
}"""

# 表・ボードを領域の高さいっぱいに広げる境（721px 以上）と、マップの境（901px 以上）の前後の幅（px）と、広げるか
TABLE_BOARD_BOUNDARY_WIDTHS = [(720, False), (721, True)]
MAP_BOUNDARY_WIDTHS = [(900, False), (901, True)]

# 窓の高さ（px）。項目を多く並べた画面が収まらない高さにする
BOUNDARY_HEIGHT = 720

# 本文の領域を一番下まで送った後の、トップバーとタブの帯の位置を読む
_BANDS_SCRIPT = """() => {
    const content = document.querySelector('.content');
    content.scrollTop = content.scrollHeight;
    const top = document.querySelector('.topbar').getBoundingClientRect();
    const tabs = document.querySelector('.tabbar').getBoundingClientRect();
    return {topbarTop: top.top, topbarBottom: top.bottom, tabbarTop: tabs.top, tabbarBottom: tabs.bottom};
}"""


def region_metrics(page: Page, selector: str | None = None) -> dict[str, Any]:
    """窓・本文の領域・`selector` が指す要素のスクロールの大きさと位置を返す。"""
    return page.evaluate(_REGION_SCRIPT, selector)


def assert_page_does_not_scroll(page: Page) -> None:
    """ページ全体は縦にも横にもスクロールしない（本文の領域の外へ溢れない）ことを確かめる。"""
    metrics = region_metrics(page)
    assert metrics["pageScrollHeight"] <= metrics["innerHeight"]
    assert metrics["pageScrollWidth"] <= metrics["innerWidth"]
    assert metrics["scrollY"] == 0


def assert_bands_stay(page: Page) -> None:
    """本文の領域を一番下まで送っても、トップバーとタブの帯が窓の上端に見えたままであることを確かめる。"""
    bands = page.evaluate(_BANDS_SCRIPT)
    assert bands["topbarTop"] == 0
    assert bands["tabbarTop"] == bands["topbarBottom"]
    assert bands["tabbarBottom"] > bands["tabbarTop"]


def assert_region_mode(page: Page, selector: str, *, filled: bool) -> None:
    """`selector` の枠が、領域の高さいっぱいに広がって中でスクロールする（`filled`）か、領域ごと縦にスクロールする（そうでない）かを確かめる。"""
    metrics = region_metrics(page, selector)
    assert_page_does_not_scroll(page)
    if filled:
        # 領域そのものはスクロールせず、枠が領域の底まで広がって中で縦にスクロールする
        assert metrics["content"]["scrollHeight"] <= metrics["content"]["clientHeight"]
        assert metrics["target"]["scrollHeight"] > metrics["target"]["clientHeight"]
    else:
        # 枠の中ではスクロールせず、領域ごと縦にスクロールする
        assert metrics["content"]["scrollHeight"] > metrics["content"]["clientHeight"]
        assert metrics["target"]["scrollHeight"] <= metrics["target"]["clientHeight"] + 1
    assert_bands_stay(page)
