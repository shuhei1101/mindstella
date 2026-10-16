"""幅 320px で、トップバー以外の画面が横にスクロールせず見切れないことを確かめる結合テストが共有する操作と値。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

__all__ = [
    "FIT_EXEMPT",
    "SMALLEST_VIEWPORT",
    "assert_fits_smallest",
    "fit_report",
    "set_smallest",
]

# 動作環境の最も狭い画面（幅 320px 以上）
SMALLEST_VIEWPORT = {"width": 320, "height": 568}

# 区画の中でだけ横に送る要素（表・カテゴリー別の進捗・マップ・ネットワーク・図・コードブロック）と、読み上げにだけ残す要素、
# ボード（右端が表示幅に収まることは各ボードのテストが見る）、対象外の帯（トップバーとタブの帯）。これらとその中身は、はみ出しを数えない
FIT_EXEMPT = ", ".join(
    [
        ".topbar",
        ".tabbar",
        ".table-wrap",
        ".md-table-wrap",
        ".cat-wrap",
        ".board",
        ".sr-only",
        "#decision-map",
        "#graph-canvas",
        ".mermaid",
        ".v-canvas",
        "pre",
        "svg",
        "canvas",
    ]
)

# ページ全体の横のはみ出しと、中身を切る・自分の中で送る区画のはみ出しを読む
_FIT_REPORT_SCRIPT = """([exempt, scope]) => {
    const root = document.documentElement;
    const describe = (element) => {
        const id = element.id ? `#${element.id}` : "";
        const classes = [...element.classList].map((name) => `.${name}`).join("");
        return `${element.tagName.toLowerCase()}${id}${classes}`;
    };
    // 中身を省略記号で切る要素は、切ること自体が作りなので数えない
    const clipsOnPurpose = (element) => {
        const style = getComputedStyle(element);
        return style.textOverflow === "ellipsis" || style.webkitLineClamp !== "none";
    };
    // 対象外の子孫だけが外へはみ出しているなら、その要素のはみ出しではない
    const spillsOutside = (element) => {
        const right = element.getBoundingClientRect().left + element.clientWidth;
        return [...element.querySelectorAll("*")]
            .filter((child) => child.closest(exempt) === null)
            .some((child) => child.getBoundingClientRect().right > right + 0.5);
    };
    // 読み上げにだけ残す要素（見た目の幅が 1px 以下に切られたもの）は、見える区画ではない
    const visuallyHidden = (element) => element.getBoundingClientRect().width <= 1;
    // 中身を切る・自分の中で送る区画だけを数える（切らない要素のはみ出しは、切る祖先かページ全体のはみ出しに現れる）
    const clipsContent = (element) => getComputedStyle(element).overflowX !== "visible";
    const overflowing = [...document.querySelector(scope).querySelectorAll("*")]
        .filter((element) => element.closest(exempt) === null)
        .filter(clipsContent)
        .filter((element) => !visuallyHidden(element))
        .filter((element) => element.clientWidth > 0 && element.scrollWidth > element.clientWidth)
        .filter((element) => !clipsOnPurpose(element))
        .filter((element) => element.querySelector(exempt) === null || spillsOutside(element) || element.children.length === 0)
        .map(describe);
    return {
        pageOverflow: root.scrollWidth - root.clientWidth,
        overflowing,
    };
}"""


def set_smallest(page: Page) -> None:
    """表示幅を 320 x 568 にし、画面が描き直るのを待つ。"""
    page.set_viewport_size(SMALLEST_VIEWPORT)
    page.evaluate("new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))")


# 動いている途中の動き（パネルの出入り）が終わるのを待つ
_ANIMATIONS_FINISHED_SCRIPT = "Promise.all(document.getAnimations().map((animation) => animation.finished))"


def _outside(page: Page, controls: tuple[str, ...]) -> list[str]:
    """`controls`（Playwright の選択子）のうち、見つからないもの・表示幅の外に出ているものを返す。"""
    problems: list[str] = []
    width = page.evaluate("document.documentElement.clientWidth")
    for selector in controls:
        boxes = page.locator(selector).evaluate_all(
            "elements => elements.map((element) => element.getBoundingClientRect().toJSON())"
        )
        if not boxes:
            problems.append(f"{selector}: 見つからない")
        problems.extend(f"{selector}: 表示幅の外" for box in boxes if box["left"] < 0 or box["right"] > width)
    return problems


def fit_report(page: Page, controls: tuple[str, ...] = (), scope: str = "body") -> dict[str, Any]:
    """ページ全体の横のはみ出し（px）、`scope` の中のはみ出す区画、表示幅の外にある操作の要素を返す。"""
    page.evaluate(_ANIMATIONS_FINISHED_SCRIPT)
    report: dict[str, Any] = page.evaluate(_FIT_REPORT_SCRIPT, [FIT_EXEMPT, scope])
    report["outside"] = _outside(page, controls)
    return report


def assert_fits_smallest(page: Page, controls: tuple[str, ...] = (), scope: str = "body") -> None:
    """ページが横にスクロールせず、`scope` の中の区画がはみ出さず、操作の要素が表示幅の中にあることを確かめる。"""
    report = fit_report(page, controls, scope)
    assert report["pageOverflow"] == 0, f"ページが横に {report['pageOverflow']}px あふれる"
    assert report["overflowing"] == [], f"横にあふれる区画: {report['overflowing']}"
    assert report["outside"] == [], f"表示幅の外にある操作: {report['outside']}"
