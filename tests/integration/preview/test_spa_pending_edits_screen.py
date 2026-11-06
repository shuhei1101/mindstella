"""画面設計『保存待ちのパネル.tsx』の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, Route, expect
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


# ─── 画面設計の要素の確認項目 ───

# 保存した知らせを出しておく秒数の前後（ミリ秒）
SAVED_SHOWN_MS = 4_500
SAVED_GONE_MS = 1_500


def _open_emptied(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """1 件の編集を溜めたパネルを開き、その編集を取り消して保存待ちを 0 件にする。"""
    url, _ = write_edit_preview(make_item("D-1"), edits=(make_edit("E-1", target="D-1", key="title", value="新しい題", before="D-1の題"),))
    open_spa(page, url, "?tab=decisions&panel=pending")
    _panel(page).get_by_role("button", name="D-1 のタイトルの編集を取り消す").click()


def _panel(page: Page) -> Locator:
    """保存待ちのパネルを返す。"""
    return page.get_by_role("complementary", name="保存待ちの編集")


def test_heading_label(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """パネルの見出しは「保存待ち」と件数で、開いたときに見出しへフォーカスを移す（正常系）。"""
    # 準備・実行
    _open(page, write_edit_preview, make_item, make_edit)
    heading = _panel(page).get_by_role("heading", level=2)
    # 検証
    expect(heading).to_have_text("保存待ち")
    expect(_panel(page)).to_contain_text("3 件")
    expect(heading).to_be_focused()


def test_blocked_notice_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """書き込めない編集の知らせは、直前の保存が 409 で書き込めない編集が残っているときだけ出す（異常系）。"""
    # 準備
    _open(page, write_edit_preview, make_item, make_edit)
    panel = _panel(page)
    expect(panel.get_by_role("alert")).to_have_count(0)
    edit_id = panel.locator("li[id^='pe-row-']").first.get_attribute("id")
    assert edit_id is not None
    page.route("**/api/edits/save", lambda route: route.fulfill(status=409, content_type="application/problem+json", body=BLOCKED_BODY % edit_id.removeprefix("pe-row-")))
    # 実行
    panel.get_by_role("button", name="まとめて保存する").click()
    # 検証
    expect(panel.get_by_role("alert")).to_contain_text("1 件の編集を書き込めないため、何も保存していません。")
    expect(panel.get_by_role("alert")).to_contain_text("書き込めない編集を取り消してから、もう一度保存してください。")


def test_unreachable_notice_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """つながらない知らせは、直前の保存がサーバーに届かなかったときだけ出し、保存待ちの編集は残す（異常系）。"""
    # 準備
    _open(page, write_edit_preview, make_item, make_edit)
    panel = _panel(page)
    page.route("**/api/edits/save", lambda route: route.abort())
    # 実行
    panel.get_by_role("button", name="まとめて保存する").click()
    alert = panel.get_by_role("alert")
    # 検証
    expect(alert).to_contain_text("サーバーにつながらないため、保存できませんでした。")
    expect(alert).to_contain_text("保存待ちの編集は残っています。サーバーを立ち上げ直してから、もう一度保存してください。")
    expect(panel.locator("li[id^='pe-row-']")).to_have_count(3)


def test_undo_label(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """取り消すの文言は「取り消す」で、読み上げの名前は「{ID} の{何を}の編集を取り消す」（正常系）。"""
    # 準備・実行
    _open(page, write_edit_preview, make_item, make_edit)
    undo = _panel(page).get_by_role("button", name="D-1 のタイトルの編集を取り消す")
    # 検証
    expect(undo).to_have_text("取り消す")


def test_empty_label(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """保存待ちの編集が 0 件のときは「保存待ちの編集はありません。」と出す（正常系）。"""
    # 準備・実行（1 件を溜めたパネルを開き、取り消して 0 件にする）
    _open_emptied(page, write_edit_preview, make_item, make_edit)
    # 検証
    expect(_panel(page).get_by_text("保存待ちの編集はありません。")).to_be_visible()


def test_empty_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """保存待ちの編集が 1 件以上あるときは空の状態を出さない（正常系）。"""
    # 準備・実行
    _open(page, write_edit_preview, make_item, make_edit)
    # 検証
    expect(_panel(page).get_by_text("保存待ちの編集はありません。")).to_have_count(0)


def test_count_label(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """保存する件数は「{n} 件（うち削除 {m} 件）をワークスペースに書きます」（正常系）。"""
    # 準備・実行
    _open(page, write_edit_preview, make_item, make_edit)
    # 検証
    expect(_panel(page).get_by_text("3 件（うち削除 1 件）をワークスペースに書きます")).to_be_visible()


def test_count_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """保存待ちの編集が 0 件のときは保存する件数を出さない（正常系）。"""
    # 準備・実行（1 件を溜めたパネルを開き、取り消して 0 件にする）
    _open_emptied(page, write_edit_preview, make_item, make_edit)
    # 検証
    expect(_panel(page).get_by_text("をワークスペースに書きます")).to_have_count(0)


def test_save_label(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """削除を含むときは「まとめて保存する（{m} 件を削除）」、含まないときは「まとめて保存する」（正常系）。"""
    # 準備
    _open(page, write_edit_preview, make_item, make_edit)
    expect(_panel(page).get_by_role("button", name="まとめて保存する")).to_have_text("まとめて保存する（1 件を削除）")
    # 実行
    _panel(page).get_by_role("button", name="D-2 の項目を削除の編集を取り消す").click()
    # 検証
    expect(_panel(page).get_by_role("button", name="まとめて保存する")).to_have_text("まとめて保存する")


def test_save_enabled(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """まとめて保存するは、保存待ちの編集が 0 件のときは押せない（正常系）。"""
    # 準備・実行（1 件を溜めたパネルを開き、取り消して 0 件にする）
    _open_emptied(page, write_edit_preview, make_item, make_edit)
    # 検証
    expect(_panel(page).get_by_role("button", name="まとめて保存する")).to_be_disabled()


def test_save_disabled_while_sending(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """送信中は「保存しています…」にして押せなくし、`aria-busy` を付ける（正常系）。"""
    # 準備
    _open(page, write_edit_preview, make_item, make_edit)
    panel = _panel(page)
    page.route("**/api/edits/save", lambda route: None)
    # 実行
    panel.get_by_role("button", name="まとめて保存する").click()
    sending = panel.get_by_role("button", name="保存しています…")
    # 検証
    expect(sending).to_be_disabled()
    expect(sending).to_have_attribute("aria-busy", "true")


def test_saved_notice_label(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """全て書けたら「{n} 件を保存しました。」を status で出し、パネルを閉じる（正常系）。"""
    # 準備
    url, _ = write_edit_preview(make_item("D-1"), make_item("D-2"), edits=(make_edit("E-1", target="D-1", key="title", value="D-1の新しい題", before="D-1の題"), make_edit("E-2", target="D-2", key="title", value="D-2の新しい題", before="D-2の題")))
    open_spa(page, url, "?tab=decisions&panel=pending")
    # 実行
    _panel(page).get_by_role("button", name="まとめて保存する").click()
    # 検証
    expect(page.get_by_role("status").filter(has_text="件を保存しました。")).to_have_text("2 件を保存しました。")
    expect(_panel(page)).to_have_count(0)


def test_saved_notice_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """保存した知らせは全て書けてから 5 秒の間だけ出す（正常系）。"""
    # 準備
    url, _ = write_edit_preview(make_item("D-1"), edits=(make_edit("E-1", target="D-1", key="title", value="D-1の新しい題", before="D-1の題"),))
    open_spa(page, url, "?tab=decisions&panel=pending")
    notice = page.get_by_role("status").filter(has_text="件を保存しました。")
    # 実行
    _panel(page).get_by_role("button", name="まとめて保存する").click()
    expect(notice).to_be_visible()
    page.wait_for_timeout(SAVED_SHOWN_MS)
    shown = notice.count()
    page.wait_for_timeout(SAVED_GONE_MS)
    # 検証
    assert shown == 1
    expect(notice).to_have_count(0)


def test_scrim_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """グレーアウトは幅 901px 以上で出し、押すとパネルを閉じる。幅 900px 以下では出さない（正常系）。"""
    # 準備
    page.set_viewport_size({"width": 900, "height": 800})
    _open(page, write_edit_preview, make_item, make_edit)
    scrim = page.locator("[data-scrim]")
    expect(scrim).to_be_hidden()
    # 実行
    page.set_viewport_size({"width": 1280, "height": 800})
    expect(scrim).to_be_visible()
    scrim.click(position={"x": 1000, "y": 400})
    # 検証
    expect(_panel(page)).to_have_count(0)


def test_close_by_escape(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """パネルの中で Esc を押すと閉じ、保存待ちの編集は残る（正常系）。"""
    # 準備
    _open(page, write_edit_preview, make_item, make_edit)
    # 実行
    page.keyboard.press("Escape")
    # 検証
    expect(_panel(page)).to_have_count(0)
    expect(page.get_by_role("button", name="保存待ち").first).to_contain_text("3")
