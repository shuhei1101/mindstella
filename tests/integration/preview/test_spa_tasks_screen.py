"""画面設計『タスク.tsx』の結合テスト。"""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect
from preview_edit_helpers import edit_edits, edit_items
from preview_fixture_types import WritePreview, WriteReviewPreview
from preview_spa_helpers import open_spa
from workspace_fixtures import MakeEdit, MakeItem

# スクロールできるだけの数のタスク
MANY_TASKS = 60

# 表のスクロール領域
TABLE_SCROLL_SELECTOR = "[data-kind='tasks'] .overflow-auto"

# スクロールの位置が保存領域に書かれるまで待つミリ秒
SCROLL_SAVE_WAIT_MS = 200


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
    expect(card).to_contain_text("ID は保存時に決定")
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
    expect(page.locator("[data-card='T-1'] [title=新規]")).to_have_count(0)
    # 実行
    open_spa(page, url, "?tab=tasks&view=board&diff=V-1")
    # 検証
    expect(page.locator("[data-card='T-1'] [title=新規]")).to_have_count(1)


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
    expect(page.locator("[data-card='T-1'] [title='コメント 1 件']")).to_have_count(1)
    expect(page.locator("[data-card='T-2'] [title^='コメント']")).to_have_count(0)


def test_removed_band_visible(page: Page, write_removed_preview: WriteReviewPreview) -> None:
    """選んだ時点でタスクを消したときだけ削除した項目の帯を出す（正常系）。"""
    # 準備
    url, _ = write_removed_preview()
    open_spa(page, url, "?tab=tasks&diff=V-2")
    expect(page.get_by_role("region", name="この時点で削除した項目")).to_have_count(0)
    # 実行
    open_spa(page, url, "?tab=tasks&diff=pending")
    band = page.get_by_role("region", name="この時点で削除した項目")
    # 検証
    expect(band).to_be_visible()
    expect(band.get_by_role("listitem")).to_contain_text(["T-2"])


def test_add_button_label(page: Page, spa_preview: str) -> None:
    """項目を追加のボタンの文言は「項目を追加」（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=tasks")
    # 検証
    expect(page.get_by_role("button", name="タスクの項目を追加")).to_have_text("項目追加")


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


# ─── タグの絞り込み・組み合わせ方・状態の保持 ───


def _tags(*names: str) -> list[dict[str, str]]:
    """タグの名前の並びを項目の `tags` にする。"""
    return [{"name": name} for name in names]


def test_board_tag_press(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """カードのタグを押すと詳細を開かずに f.tags に加え、履歴に 1 つ積む（正常系）。"""
    # 準備
    url = write_preview(
        make_item("T-1", title="画面を作る", status="進行中", tags=_tags("画面")),
        make_item("T-2", title="保存を作る", status="進行中", tags=_tags("保存")),
    )
    open_spa(page, url, "?tab=tasks")
    # 実行
    page.locator("[data-card='T-1']").get_by_role("button", name="タグ「画面」で絞り込む").click()
    # 検証
    expect(page).to_have_url(re.compile(r"f\.tags=%E7%94%BB%E9%9D%A2"))
    expect(page.locator("[data-card='T-2']")).to_have_count(0)
    expect(page.get_by_role("complementary", name=re.compile("T-1"))).to_have_count(0)
    page.go_back()
    expect(page.locator("[data-card='T-2']")).to_be_visible()


def test_drawer_tag_match(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """既定は選んだタグを全て持つタスクだけを出し、「どれかを含む」でどれかを持つタスクを出す（正常系）。"""
    # 準備
    url = write_preview(
        make_item("T-1", title="画面を作る", status="進行中", tags=_tags("画面")),
        make_item("T-2", title="保存を作る", status="進行中", tags=_tags("保存")),
        make_item("T-3", title="両方を作る", status="進行中", tags=_tags("画面", "保存")),
    )
    open_spa(page, url, "?tab=tasks&f.tags=%E7%94%BB%E9%9D%A2|%E4%BF%9D%E5%AD%98")
    expect(page.locator("[data-card]")).to_have_count(1)
    # 実行
    page.get_by_role("button", name="絞り込み").click()
    page.get_by_role("dialog", name="絞り込み").get_by_role("group", name="タグの組み合わせ方").get_by_text("どれかを含む").click()
    # 検証
    expect(page).to_have_url(re.compile(r"tagmatch=any"))
    expect(page.locator("[data-card]")).to_have_count(3)
    expect(page.get_by_text("タグ（どれかを含む）: 画面", exact=True)).to_be_visible()


def test_filters_kept_in_tab(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """ほかの画面から戻ると、そのタブに残した絞り込みの条件で開き、端末の保存領域には残さない（正常系）。"""
    # 準備
    url = write_preview(
        make_item("T-1", title="画面を作る", status="進行中"),
        make_item("T-2", title="保存を作る", status="未着手"),
    )
    open_spa(page, url, "?tab=tasks&f.status=%E9%80%B2%E8%A1%8C%E4%B8%AD")
    expect(page.locator("[data-card]")).to_have_count(1)
    # 実行
    page.get_by_role("link", name="検討事項").click()
    page.get_by_role("link", name="タスク").click()
    # 検証
    expect(page).to_have_url(re.compile(r"f\.status=%E9%80%B2%E8%A1%8C%E4%B8%AD"))
    expect(page.locator("[data-card]")).to_have_count(1)
    assert "filters" not in (page.evaluate("JSON.stringify(localStorage)") or "")


def test_table_scroll_restored(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """表をスクロールしてほかの画面へ移り、戻ると離れたときの位置へ戻す（正常系）。"""
    # 準備
    url = write_preview(*(make_item(f"T-{number}", title=f"タスク {number}", status="未着手") for number in range(1, MANY_TASKS + 1)))
    page.set_viewport_size({"width": 1280, "height": 600})
    open_spa(page, url, "?tab=tasks&view=table")
    area = page.locator(TABLE_SCROLL_SELECTOR)
    before = area.evaluate("(node) => { node.scrollTop = 300; node.dispatchEvent(new Event('scroll')); return node.scrollTop; }")
    page.wait_for_timeout(SCROLL_SAVE_WAIT_MS)
    # 実行
    page.get_by_role("link", name="検討事項").click()
    page.go_back()
    # 検証
    assert before > 0
    expect(page.locator("tbody tr[data-id='T-1']")).to_be_attached()
    page.wait_for_function(
        "([selector, top]) => document.querySelector(selector)?.scrollTop === top", arg=[TABLE_SCROLL_SELECTOR, before]
    )
