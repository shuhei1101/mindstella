"""画面設計『タスク.tsx』の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page, expect
from preview_spa_helpers import open_spa


def test_board_columns(page: Page, spa_preview: str) -> None:
    """既定はボードで、タスクを状態の列に並べる（正常系）。"""
    open_spa(page, spa_preview, "?tab=tasks")
    expect(page.get_by_role("region", name="進行中")).to_contain_text("画面を作る")


def test_item_add_flow(page: Page, spa_preview: str) -> None:
    """項目を追加すると詳細の場所の入力で溜まり、ボードの先頭に出て、押すと入力を開き直す（正常系）。"""
    open_spa(page, spa_preview, "?tab=tasks")
    page.get_by_role("button", name="タスクの項目を追加").click()
    panel = page.get_by_role("complementary", name="タスクを追加")
    title = panel.get_by_role("textbox", name="タイトル")
    title.fill("足すタスク")
    title.blur()
    card = page.locator("[data-new-id]")
    expect(card).to_contain_text("足すタスク")
    expect(card).to_contain_text("ID は保存で決まる")
    panel.get_by_role("button", name="追加の入力を閉じる").click()
    expect(panel).to_be_hidden()
    card.click()
    expect(page.get_by_role("complementary", name="タスクを追加").get_by_role("textbox", name="タイトル")).to_have_value("足すタスク")


def test_item_add_keeps_empty_title_unsaved(page: Page, spa_preview: str) -> None:
    """タイトルを空のまま離れると溜めず、誤りを出す（異常系）。"""
    open_spa(page, spa_preview, "?tab=tasks")
    page.get_by_role("button", name="タスクの項目を追加").click()
    title = page.get_by_role("complementary", name="タスクを追加").get_by_role("textbox", name="タイトル")
    title.fill("  ")
    title.blur()
    expect(page.get_by_text("タイトルを書いてください。")).to_be_visible()
    expect(page.locator("[data-new-id]")).to_have_count(0)
