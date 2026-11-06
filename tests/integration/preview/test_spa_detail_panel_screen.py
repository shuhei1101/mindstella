"""画面設計『詳細パネル.tsx』の結合テスト。"""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from preview_fixture_types import WritePreview
from preview_spa_helpers import open_spa
from workspace_fixtures import MakeItem

# 送る本文のスクロールの位置（px）
SCROLLED_TOP = 600

# 本文の高さの変化でブラウザが補正する位置のずれ（px）
SCROLL_TOLERANCE = 10


def test_draws_body_with_mdmark(page: Page, spa_preview: str) -> None:
    """mdmark で本文を描き、見出しと表と案を出す（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    panel = page.get_by_role("complementary", name="詳細")
    expect(panel.get_by_role("heading", name="決め方")).to_be_visible()
    expect(panel.get_by_role("cell", name="表の行")).to_be_visible()
    expect(panel).to_contain_text("案 A")


def test_edit_stores_pending(page: Page, spa_preview: str) -> None:
    """タイトルを書き換えると保存待ちに溜まる（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    page.get_by_role("button", name="編集する").click()
    title = page.get_by_role("textbox", name="タイトル")
    title.fill("書き換えた題")
    title.blur()
    page.get_by_role("button", name="保存待ち").first.click()
    expect(page.get_by_role("complementary", name="保存待ちの編集")).to_contain_text("書き換えた題")


def test_remove_can_be_cancelled(page: Page, spa_preview: str) -> None:
    """項目の削除を溜め、取り消せる（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&id=D-2")
    page.get_by_role("button", name="編集する").click()
    page.get_by_role("button", name="項目を削除").click()
    cancel = page.get_by_role("button", name="削除を取り消す")
    expect(cancel).to_be_visible()
    cancel.click()
    expect(page.get_by_role("button", name="項目を削除")).to_be_visible()


def test_back_keeps_trail_over_reload(page: Page, spa_preview: str) -> None:
    """見てきた項目の位置は履歴に持つので、再読み込みしても戻る・進むを押せる（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    panel = page.get_by_role("complementary", name="詳細")
    back = panel.get_by_role("button", name="前の項目へ戻る")
    forward = panel.get_by_role("button", name="次の項目へ進む")
    expect(back).to_be_disabled()
    panel.get_by_role("button", name="D-2").click()
    expect(back).to_be_enabled()
    page.reload()
    expect(back).to_be_enabled()
    back.click()
    expect(page).to_have_url(re.compile("id=D-1"))
    expect(back).to_be_disabled()
    expect(forward).to_be_enabled()


def test_back_keeps_trail_over_filter(page: Page, spa_preview: str) -> None:
    """絞り込みを変えても、見てきた項目の位置を保つ（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&view=table&id=D-1")
    panel = page.get_by_role("complementary", name="詳細")
    panel.get_by_role("button", name="D-2").click()
    expect(page).to_have_url(re.compile("id=D-2"))
    page.get_by_role("button", name="状態: 保留 の条件を解除").click()
    expect(panel.get_by_role("button", name="前の項目へ戻る")).to_be_enabled()


def test_restores_body_scroll(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """本文を送った項目を開き直すと、その位置へ戻る（正常系）。"""
    long_body = "\n\n".join(f"段落 {number}" for number in range(200))
    url = write_preview(make_item("D-1", title="長い本文", status="未決定", body="D-1.md"), make_item("D-2", title="別の項目", status="未決定"), bodies={"D-1.md": long_body})
    open_spa(page, url, "?tab=decisions&id=D-1")
    page.get_by_text("段落 199").wait_for()
    page.locator("aside .panel-body").evaluate(f"(element) => {{ element.scrollTop = {SCROLLED_TOP}; }}")
    page.wait_for_function("sessionStorage.getItem('mindmap-body-scroll') !== null")
    page.goto(page.url.replace("id=D-1", "id=D-2"))
    page.get_by_role("complementary", name="詳細").wait_for()
    page.goto(page.url.replace("id=D-2", "id=D-1"))
    page.get_by_text("段落 199").wait_for()
    page.wait_for_function(f"Math.abs(document.querySelector('aside .panel-body').scrollTop - {SCROLLED_TOP}) < {SCROLL_TOLERANCE}")
