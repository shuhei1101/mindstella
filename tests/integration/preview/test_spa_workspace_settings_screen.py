"""画面設計『設定の画面.tsx』の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page, expect
from preview_spa_helpers import open_spa


def test_title_is_stored(page: Page, spa_preview: str) -> None:
    """題名を書き換えると保存待ちに溜まる（正常系）。"""
    open_spa(page, spa_preview, "?tab=settings")
    title = page.get_by_role("textbox", name="題名")
    title.fill("画面の編集")
    title.blur()
    page.get_by_role("button", name="保存待ち").first.click()
    expect(page.get_by_role("complementary", name="保存待ちの編集")).to_contain_text("画面の編集")


def test_close_returns_to_overview(page: Page, spa_preview: str) -> None:
    """閉じると概要へ戻る（正常系）。"""
    open_spa(page, spa_preview, "?tab=settings")
    page.get_by_role("button", name="閉じる").click()
    expect(page.locator("#tile-next")).to_be_visible()
