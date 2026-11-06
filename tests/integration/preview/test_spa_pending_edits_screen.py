"""画面設計『保存待ちのパネル.tsx』の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page, Route, expect
from preview_edit_helpers import edit_edits, edit_items
from preview_fixture_types import WriteReviewPreview
from preview_spa_helpers import open_spa
from workspace_fixtures import MakeEdit, MakeItem

# まとめて保存を断る応答の本文
BLOCKED_BODY = '{"type":"about:blank","title":"Conflict","status":409,"detail":"書き込めません","blocked":[{"id":"%s","reason":"invalid","detail":"書き込めない理由","refs":[]}]}'


def _open(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """保存待ちの編集を持つ画面でパネルを開く。"""
    url, _ = write_edit_preview(*edit_items(make_item, "D"), edits=edit_edits(make_edit, "D"))
    open_spa(page, url, "?tab=decisions&panel=pending")


def test_undo_row(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """行の取り消すで 1 件を外す（正常系）。"""
    _open(page, write_edit_preview, make_item, make_edit)
    panel = page.get_by_role("complementary", name="保存待ちの編集")
    rows = panel.get_by_role("listitem")
    before = rows.count()
    panel.get_by_role("button", name="取り消す").first.click()
    expect(rows).to_have_count(before - 1)


def test_blocked_list_moves_focus(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """書き込めない編集の知らせへフォーカスを移し、一覧から行の取り消すボタンへ移る（異常系）。"""
    _open(page, write_edit_preview, make_item, make_edit)
    panel = page.get_by_role("complementary", name="保存待ちの編集")
    edit_id = panel.locator("li[id^='pe-row-']").first.get_attribute("id")
    assert edit_id is not None

    def _refuse(route: Route) -> None:
        """まとめて保存を 409 で断る。"""
        route.fulfill(status=409, content_type="application/problem+json", body=BLOCKED_BODY % edit_id.removeprefix("pe-row-"))

    page.route("**/api/edits/save", _refuse)
    panel.get_by_role("button", name="まとめて保存する").click()
    alert = panel.get_by_role("alert")
    expect(alert).to_be_focused()
    expect(alert).to_contain_text("何も保存していません")
    alert.get_by_role("listitem").first.get_by_role("button").click()
    expect(panel.locator(f"#{edit_id} button")).to_be_focused()
    expect(panel).to_contain_text("書き込めない理由")
