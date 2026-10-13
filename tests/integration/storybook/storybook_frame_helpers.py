"""HTML の本文の枠を描く部品のストーリーの結合テストが共有する、枠の中を読む関数。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict

from playwright.sync_api import Frame, Page

__all__ = [
    "EXTERNAL_PAGE_TITLE",
    "FRAME_SELECTOR",
    "FRAME_SETTLE_MS",
    "WINDOW_OPEN_RECORDER_JS",
    "FrameFit",
    "new_tab_after",
    "opened_tabs",
    "serve_external_pages",
    "frame_fit",
    "frame_of",
    "wait_frame_rendered",
]

# 部品が描く枠
FRAME_SELECTOR = "iframe.html-frame"

# 枠の描き終わり・高さ合わせが済むまで待つミリ秒
FRAME_SETTLE_MS = 400

# 枠を描き終えるまで待つ上限ミリ秒
FRAME_RENDER_TIMEOUT_MS = 15_000

# 枠の高さが伸び続けないかを確かめるために、置く間隔のミリ秒
FRAME_LATER_MS = 1_500

# 外のページへのリンクの先として返すページの題
EXTERNAL_PAGE_TITLE = "外のページ"

# 外のページへの要求を、テストが返すページで受ける条件
EXTERNAL_PAGE_PATTERN = "https://example.com/**"

# 新しいタブが開くまで待つ上限ミリ秒
NEW_TAB_TIMEOUT_MS = 10_000

# 親の画面の `window.open` を、呼び出しを記録するものに差し替える
WINDOW_OPEN_RECORDER_JS = """() => {
    window.__opens = [];
    window.open = (...args) => { window.__opens.push(args.map(String)); return null; };
}"""

# 枠の高さと、枠の中の最後の要素の下端（px）を返す
FRAME_METRICS_SCRIPT = """(selector) => {
    const frame = document.querySelector(selector);
    const bottoms = [...frame.contentDocument.body.querySelectorAll('*')].map(
        (element) => element.getBoundingClientRect().bottom
    );
    return { height: frame.clientHeight, bottom: Math.max(...bottoms) };
}"""


class FrameFit(TypedDict):
    """枠の高さと中身の下端（px）、時間を置いた後の枠の高さ。"""

    height: float
    bottom: float
    later_height: float


def serve_external_pages(page: Page) -> None:
    """`https://example.com/` への要求を、外へ通信せず、題だけを持つページで答えるようにする（新しいタブにも効く）。"""
    page.context.route(
        EXTERNAL_PAGE_PATTERN,
        lambda route: route.fulfill(
            status=200,
            content_type="text/html; charset=utf-8",
            body=f"<!doctype html><title>{EXTERNAL_PAGE_TITLE}</title>",
        ),
    )


def opened_tabs(page: Page) -> int:
    """ブラウザの文脈に開いているタブの数を返す。"""
    return len(page.context.pages)


def new_tab_after(page: Page, action: Callable[[], object]) -> Page:
    """`action` を実行して開いた新しいタブを、読み込み終わりまで待って返す。"""
    with page.context.expect_page(timeout=NEW_TAB_TIMEOUT_MS) as info:
        action()
    tab = info.value
    tab.wait_for_load_state()
    return tab


def wait_frame_rendered(page: Page, selector: str = FRAME_SELECTOR) -> None:
    """枠が描き終わり（`data-rendered`）、高さ合わせが済むまで待つ。"""
    page.wait_for_selector(f"{selector}[data-rendered]", state="attached", timeout=FRAME_RENDER_TIMEOUT_MS)
    page.wait_for_timeout(FRAME_SETTLE_MS)


def frame_of(page: Page, selector: str = FRAME_SELECTOR) -> Frame:
    """枠（iframe）の中の文書の Frame を返す。"""
    handle = page.locator(selector).first.element_handle()
    frame = handle.content_frame()
    assert frame is not None, f"{selector} の中の文書がありません"
    return frame


def frame_fit(page: Page, selector: str = FRAME_SELECTOR) -> FrameFit:
    """枠の高さと枠の中の最後の要素の下端を測り、時間を置いて枠の高さを測り直して返す。"""
    metrics = page.evaluate(FRAME_METRICS_SCRIPT, selector)
    page.wait_for_timeout(FRAME_LATER_MS)
    later = page.evaluate(FRAME_METRICS_SCRIPT, selector)
    return {"height": metrics["height"], "bottom": metrics["bottom"], "later_height": later["height"]}
