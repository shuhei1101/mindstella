"""画面設計『資料.tsx』の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect
from preview_edit_helpers import edit_edits, edit_items
from preview_fixture_types import WritePreview, WriteReviewPreview
from preview_spa_helpers import open_spa
from workspace_fixtures import MakeEdit, MakeItem


def test_cards_put_deliverable_first(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """既定はカードで、納品物を先頭に並べる（正常系）。"""
    url = write_preview(make_item("A-1", title="普通の資料"), make_item("A-2", title="納品物の資料", deliverable=True))
    open_spa(page, url, "?tab=docs")
    expect(page.get_by_role("heading", level=3).first).to_have_text("納品物の資料")


def test_board_and_table(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """ボードは状態の列、表は形式の列を持つ（正常系）。"""
    url = write_preview(make_item("A-1", title="普通の資料", body="A-1.md"), bodies={"A-1.md": "本文"})
    open_spa(page, url, "?tab=docs&view=board")
    expect(page.locator("[data-id='A-1']")).to_be_visible()
    open_spa(page, url, "?tab=docs&view=table")
    expect(page.get_by_role("cell", name="MD", exact=True)).to_be_visible()


# ─── 画面設計の要素の確認項目 ───


def test_topbar_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """トップバーを常に出し、資料のタブを開いている（正常系）。"""
    # 準備・実行
    open_spa(page, write_preview(make_item("A-1")), "?tab=docs")
    # 検証
    expect(page.get_by_role("link", name="資料")).to_have_attribute("aria-current", "page")


def test_view_switch_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """表示形式の切り替えを常に出し、カード・ボード・表の順に並べ、既定はカード（正常系）。"""
    # 準備・実行
    open_spa(page, write_preview(make_item("A-1")), "?tab=docs")
    group = page.get_by_role("group", name="表示形式")
    # 検証
    expect(group.get_by_role("button")).to_have_text(["カード", "ボード", "表"])
    expect(group.get_by_role("button", name="カード")).to_have_attribute("aria-pressed", "true")


@pytest.mark.parametrize("view", ["cards", "board"])
def test_chips_visible(page: Page, write_preview: WritePreview, make_item: MakeItem, view: str) -> None:
    """条件のチップは、カード・ボードで値を選んだ条件があるときに出す（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1", status="完成"), make_item("A-2", status="下書き"))
    open_spa(page, url, f"?tab=docs&view={view}")
    expect(page.get_by_role("button", name="すべて解除")).to_have_count(0)
    # 実行
    open_spa(page, url, f"?tab=docs&view={view}&f.status=完成")
    # 検証
    expect(page.get_by_role("button", name="状態: 完成 の条件を解除")).to_be_visible()


def test_cards_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """表示形式がカードのときは資料のカードを出し、表とボードを出さない（正常系）。"""
    # 準備・実行
    open_spa(page, write_preview(make_item("A-1", title="カードの資料")), "?tab=docs&view=cards")
    # 検証
    expect(page.locator("button[data-id='A-1']")).to_contain_text("カードの資料")
    expect(page.get_by_role("table")).to_have_count(0)
    expect(page.get_by_role("region", name="下書き")).to_have_count(0)


def test_table_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """表示形式が表のときは表を出す（正常系）。"""
    # 準備・実行
    open_spa(page, write_preview(make_item("A-1", title="表の資料")), "?tab=docs&view=table")
    # 検証
    expect(page.get_by_role("table")).to_be_visible()
    expect(page.locator("tr[data-id='A-1']")).to_contain_text("表の資料")


def test_board_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """表示形式がボードのときは状態の列のボードを出し、表を出さない（正常系）。"""
    # 準備・実行
    open_spa(page, write_preview(make_item("A-1", status="下書き")), "?tab=docs&view=board")
    # 検証
    expect(page.get_by_role("region", name="下書き")).to_contain_text("A-1の題")
    expect(page.get_by_role("table")).to_have_count(0)


@pytest.mark.parametrize("view", ["cards", "board"])
def test_diff_mark_visible(page: Page, write_history_preview: WriteReviewPreview, view: str) -> None:
    """差分の表示の間、選んだ時点で足した資料のカード・ボードに新規の印を出し、差分の表示でないときは出さない（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, f"?tab=docs&view={view}")
    expect(page.locator("[data-id='A-1'] [title=新規]")).to_have_count(0)
    # 実行
    open_spa(page, url, f"?tab=docs&view={view}&diff=V-1")
    # 検証
    expect(page.locator("[data-id='A-1'] [title=新規]")).to_have_count(1)


def test_drawer_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """絞り込みのドロワーはトップバーの絞り込みのボタンを押したときに出す（正常系）。"""
    # 準備
    open_spa(page, write_preview(make_item("A-1")), "?tab=docs")
    expect(page.get_by_role("dialog", name="絞り込み")).to_have_count(0)
    # 実行
    page.get_by_role("button", name="絞り込み").click()
    # 検証
    expect(page.get_by_role("dialog", name="絞り込み")).to_be_visible()


def test_drawer_initial_value(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """絞り込みのドロワーは、URL の `f.{列}` の条件を選んだ状態で開く（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1", status="完成"), make_item("A-2", status="下書き"))
    open_spa(page, url, "?tab=docs&f.status=完成")
    # 実行
    page.get_by_role("button", name="絞り込み").click()
    dialog = page.get_by_role("dialog", name="絞り込み")
    # 検証
    expect(dialog.get_by_role("checkbox", name="完成")).to_be_checked()
    expect(dialog.get_by_role("checkbox", checked=True)).to_have_count(1)


def test_region_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """画面の領域を常に出し、見出しを「資料」にする（正常系）。"""
    # 準備・実行
    open_spa(page, write_preview(make_item("A-1")), "?tab=docs")
    # 検証
    expect(page.get_by_role("main").get_by_role("heading", level=1)).to_have_text("資料")


@pytest.mark.parametrize("view", ["cards", "board"])
def test_comment_mark_visible(page: Page, write_commented_preview: WriteReviewPreview, view: str) -> None:
    """レビュー中のコメントがある資料のカード・ボードにだけ、コメントの印を出す（正常系）。"""
    # 準備・実行
    url, _ = write_commented_preview()
    open_spa(page, url, f"?tab=docs&view={view}")
    # 検証
    expect(page.locator("[data-id='A-1'] [title='コメント 1 件']")).to_have_count(1)
    expect(page.locator("[data-id='A-2'] [title='コメント 1 件']")).to_have_count(1)


def test_removed_band_visible(page: Page, write_removed_preview: WriteReviewPreview) -> None:
    """選んだ時点で資料を消したときだけ消した項目の帯を出す（正常系）。"""
    # 準備
    url, _ = write_removed_preview()
    open_spa(page, url, "?tab=docs&diff=V-1")
    expect(page.get_by_role("region", name="この時点で消した項目")).to_have_count(0)
    # 実行
    open_spa(page, url, "?tab=docs&diff=V-2")
    # 検証
    expect(page.get_by_role("region", name="この時点で消した項目").get_by_role("listitem")).to_contain_text(["A-3"])


@pytest.mark.parametrize("view", ["cards", "board"])
def test_withdrawn_badge_visible(page: Page, write_removed_preview: WriteReviewPreview, view: str) -> None:
    """取り下げた資料のカード・ボードにだけ、差分の表示によらず取り下げの札を出す（正常系）。"""
    # 準備・実行
    url, _ = write_removed_preview()
    open_spa(page, url, f"?tab=docs&view={view}")
    # 検証
    expect(page.locator("[data-id='A-2']")).to_contain_text("取り下げ")
    expect(page.locator("[data-id='A-1']")).not_to_contain_text("取り下げ")


@pytest.mark.parametrize(("view", "body", "badge"), [("cards", "A-1.md", "MD"), ("cards", "A-1.html", "HTML"), ("board", "A-1.md", "MD")])
def test_format_badge_visible(page: Page, write_preview: WritePreview, make_item: MakeItem, view: str, body: str, badge: str) -> None:
    """本文を持つ資料のカード・ボードに、本文の形式の札（`MD` / `HTML`）を出す（正常系）。"""
    # 準備・実行
    url = write_preview(make_item("A-1", body=body), bodies={body: "本文"})
    open_spa(page, url, f"?tab=docs&view={view}")
    # 検証
    expect(page.locator("[data-id='A-1']").get_by_text(badge, exact=True)).to_be_visible()


def test_add_button_label(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """項目を追加のボタンの文言は「項目を追加」（正常系）。"""
    # 準備・実行
    open_spa(page, write_preview(make_item("A-1")), "?tab=docs")
    # 検証
    expect(page.get_by_role("button", name="資料の項目を追加")).to_have_text("項目を追加")


def test_add_button_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """項目を追加は差分の表示をしていないときだけ出す（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=docs")
    expect(page.get_by_role("button", name="資料の項目を追加")).to_be_visible()
    # 実行
    open_spa(page, url, "?tab=docs&diff=V-1")
    # 検証
    expect(page.get_by_role("button", name="資料の項目を追加")).to_have_count(0)


def test_pending_mark_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """保存待ちの編集がある資料にだけ、一覧の保存待ちの印を出す（正常系）。"""
    # 準備・実行
    url, _ = write_edit_preview(*edit_items(make_item, "A"), make_item("A-4", title="触らない資料"), edits=edit_edits(make_edit, "A"))
    open_spa(page, url, "?tab=docs&view=cards")
    # 検証
    expect(page.locator("[data-id='A-1']")).to_contain_text("保存待ち")
    expect(page.locator("[data-id='A-2']")).to_contain_text("保存で削除")
    expect(page.locator("[data-id='A-4']")).not_to_contain_text("保存")


def test_added_items_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """資料の `item-add` が保存待ちにあるときは、追加する項目を出す（正常系）。"""
    # 準備・実行
    url, _ = write_edit_preview(
        make_item("A-1"),
        edits=(make_edit("E-1", target="new-1", op="item-add", key="docs", value={"title": "足す資料", "kind": "文書", "status": "下書き", "deliverable": False}, before=None, base=None),),
    )
    open_spa(page, url, "?tab=docs&view=cards")
    # 検証
    expect(page.locator("[data-new-id]")).to_contain_text("足す資料")


def test_card_tags_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """タグを持つ資料のカードにだけタグの並びを出す（正常系）。"""
    # 準備・実行
    url = write_preview(make_item("A-1", tags=[{"name": "画面", "main": True}]), make_item("A-2", tags=[]))
    open_spa(page, url, "?tab=docs&view=cards")
    # 検証
    expect(page.locator("[data-id='A-1'] [title=主題]")).to_contain_text("画面")
    expect(page.locator("[data-id='A-2'] [title=主題]")).to_have_count(0)
