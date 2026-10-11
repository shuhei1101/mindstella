"""HTML の本文の枠を描く部品のストーリーの結合テストが共有する、枠の中を読む関数。"""

from __future__ import annotations

from playwright.sync_api import Frame, Page

__all__ = ["FRAME_SELECTOR", "FRAME_SETTLE_MS", "frame_of", "wait_frame_rendered"]

# 部品が描く枠
FRAME_SELECTOR = "iframe.html-frame"

# 枠の描き終わり・高さ合わせが済むまで待つミリ秒
FRAME_SETTLE_MS = 400

# 枠を描き終えるまで待つ上限ミリ秒
FRAME_RENDER_TIMEOUT_MS = 15_000


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
