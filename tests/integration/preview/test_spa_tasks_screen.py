"""画面設計『タスク.tsx』の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page, expect
from preview_edit_helpers import edit_edits, edit_items
from preview_fixture_types import WriteReviewPreview
from preview_spa_helpers import open_spa
from workspace_fixtures import MakeEdit, MakeItem


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


# ─── 画面設計の要素の確認項目 ───


def test_topbar_visible(page: Page, spa_preview: str) -> None:
    """トップバーを常に出し、タスクのタブを開いている（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=tasks")
    # 検証
    expect(page.get_by_role("link", name="タスク")).to_have_attribute("aria-current", "page")


def test_view_switch_visible(page: Page, spa_preview: str) -> None:
    """表示形式の切り替えを常に出し、ボード・表の順に並べる（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=tasks")
    group = page.get_by_role("group", name="表示形式")
    # 検証
    expect(group.get_by_role("button")).to_have_text(["ボード", "表"])
    expect(group.get_by_role("button", name="ボード")).to_have_attribute("aria-pressed", "true")


def test_chips_visible_on_board(page: Page, spa_preview: str) -> None:
    """条件のチップは、ボードで値を選んだ条件があるときだけ出し、表では表の上のチップにまかせる（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=tasks&view=board")
    expect(page.get_by_role("button", name="すべて解除")).to_have_count(0)
    open_spa(page, spa_preview, "?tab=tasks&view=board&f.status=進行中")
    # 検証
    expect(page.get_by_text("状態: 進行中")).to_have_count(1)
    expect(page.get_by_role("button", name="状態: 進行中 の条件を解除")).to_be_visible()


def test_board_visible(page: Page, spa_preview: str) -> None:
    """表示形式がボードのときはボードを出し、表を出さない（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=tasks&view=board")
    # 検証
    expect(page.get_by_role("region", name="進行中")).to_be_visible()
    expect(page.get_by_role("table")).to_have_count(0)


def test_table_visible(page: Page, spa_preview: str) -> None:
    """表示形式が表のときは表を出し、ボードを出さない（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=tasks&view=table")
    # 検証
    expect(page.get_by_role("table")).to_be_visible()
    expect(page.get_by_role("region", name="進行中")).to_have_count(0)
    expect(page.get_by_role("button", name="画面を作る")).to_be_visible()


def test_board_diff_mark_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """差分の表示の間、選んだ時点で足したタスクのボードのカードに新規の印を出し、差分の表示でないときは出さない（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=tasks&view=board")
    expect(page.locator("[data-id='T-1'] [title=新規]")).to_have_count(0)
    # 実行
    open_spa(page, url, "?tab=tasks&view=board&diff=V-1")
    # 検証
    expect(page.locator("[data-id='T-1'] [title=新規]")).to_have_count(1)


def test_drawer_visible(page: Page, spa_preview: str) -> None:
    """絞り込みのドロワーはトップバーの絞り込みのボタンを押したときに出す（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=tasks")
    expect(page.get_by_role("dialog", name="絞り込み")).to_have_count(0)
    # 実行
    page.get_by_role("button", name="絞り込み").click()
    # 検証
    expect(page.get_by_role("dialog", name="絞り込み")).to_be_visible()


def test_drawer_initial_value(page: Page, spa_preview: str) -> None:
    """絞り込みのドロワーは、URL の `f.{列}` の条件を選んだ状態で開き、無ければどの値も選ばない（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=tasks")
    page.get_by_role("button", name="絞り込み").click()
    assert page.get_by_role("dialog", name="絞り込み").get_by_role("checkbox", checked=True).count() == 0
    # 実行
    open_spa(page, spa_preview, "?tab=tasks&f.status=進行中")
    page.get_by_role("button", name="絞り込み").click()
    dialog = page.get_by_role("dialog", name="絞り込み")
    # 検証
    expect(dialog.get_by_role("checkbox", name="進行中")).to_be_checked()
    expect(dialog.get_by_role("checkbox", checked=True)).to_have_count(1)


def test_region_visible(page: Page, spa_preview: str) -> None:
    """画面の領域を常に出し、見出しを「タスク」にする（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=tasks")
    main = page.get_by_role("main")
    # 検証
    expect(main).to_be_visible()
    expect(main.get_by_role("heading", level=1)).to_have_text("タスク")


def test_board_comment_mark_visible(page: Page, write_commented_preview: WriteReviewPreview) -> None:
    """レビュー中のコメントがあるタスクのボードのカードにだけ、コメントの印を出す（正常系）。"""
    # 準備・実行
    url, _ = write_commented_preview()
    open_spa(page, url, "?tab=tasks&view=board")
    # 検証
    expect(page.locator("[data-id='T-1'] [title='コメント 1 件']")).to_have_count(1)
    expect(page.locator("[data-id='T-2'] [title^='コメント']")).to_have_count(0)


def test_removed_band_visible(page: Page, write_removed_preview: WriteReviewPreview) -> None:
    """選んだ時点でタスクを消したときだけ消した項目の帯を出す（正常系）。"""
    # 準備
    url, _ = write_removed_preview()
    open_spa(page, url, "?tab=tasks&diff=V-2")
    expect(page.get_by_role("region", name="この時点で消した項目")).to_have_count(0)
    # 実行
    open_spa(page, url, "?tab=tasks&diff=pending")
    band = page.get_by_role("region", name="この時点で消した項目")
    # 検証
    expect(band).to_be_visible()
    expect(band.get_by_role("listitem")).to_contain_text(["T-2"])


def test_add_button_label(page: Page, spa_preview: str) -> None:
    """項目を追加のボタンの文言は「項目を追加」（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=tasks")
    # 検証
    expect(page.get_by_role("button", name="タスクの項目を追加")).to_have_text("項目を追加")


def test_add_button_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """項目を追加は差分の表示をしていないときだけ出す（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=tasks")
    expect(page.get_by_role("button", name="タスクの項目を追加")).to_be_visible()
    # 実行
    open_spa(page, url, "?tab=tasks&diff=V-1")
    # 検証
    expect(page.get_by_role("button", name="タスクの項目を追加")).to_have_count(0)


def test_pending_mark_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """保存待ちの編集があるタスクにだけ、一覧の保存待ちの印を出す（正常系）。"""
    # 準備・実行
    url, _ = write_edit_preview(*edit_items(make_item, "T"), make_item("T-4", title="触らない項目"), edits=edit_edits(make_edit, "T"))
    open_spa(page, url, "?tab=tasks&view=table")
    # 検証
    expect(page.locator("tr[data-id='T-1']")).to_contain_text("保存待ち")
    expect(page.locator("tr[data-id='T-2']")).to_contain_text("保存で削除")
    expect(page.locator("tr[data-id='T-4']")).not_to_contain_text("保存")


def test_added_items_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """タスクの `item-add` が保存待ちにあるときは追加する項目を出し、差分の表示の間は出さない（正常系）。"""
    # 準備
    url, _ = write_edit_preview(
        make_item("T-1", title="今ある項目", status="進行中"),
        edits=(make_edit("E-1", target="new-1", op="item-add", key="tasks", value={"title": "足す項目", "kind": "作業", "status": "進行中"}, before=None, base=None),),
    )
    # 実行
    open_spa(page, url, "?tab=tasks&view=board")
    # 検証
    expect(page.locator("[data-new-id]")).to_contain_text("足す項目")
