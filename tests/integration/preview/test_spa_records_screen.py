"""画面設計『記録の表.tsx』の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect
from preview_edit_helpers import edit_edits, edit_items
from preview_fixture_types import WritePreview, WriteReviewPreview
from preview_spa_helpers import open_spa
from workspace_fixtures import MakeEdit, MakeItem


@pytest.mark.parametrize(
    ("tab", "item", "column"),
    [("research", "R-1", "問い"), ("terms", "G-1", "意味"), ("notes", "N-1", "内容"), ("logs", "L-1", "日付")],
)
def test_table_columns(page: Page, write_preview: WritePreview, make_item: MakeItem, tab: str, item: str, column: str) -> None:
    """種類ごとの列を持つ表だけを出す（正常系）。"""
    url = write_preview(make_item(item, title="記録の題"))
    open_spa(page, url, f"?tab={tab}")
    expect(page.get_by_role("columnheader", name=column)).to_be_visible()
    expect(page.get_by_role("group", name="表示形式")).to_have_count(0)
    page.get_by_role("button", name="記録の題").click()
    expect(page.get_by_role("complementary", name="詳細")).to_contain_text("記録の題")


# ─── 画面設計の要素の確認項目 ───

# 記録の表の種類と、その画面のタブの名前・項目の ID
RECORD_TABS = [
    pytest.param("research", "調査", "R", id="research"),
    pytest.param("terms", "用語集", "G", id="terms"),
    pytest.param("notes", "メモ", "N", id="notes"),
    pytest.param("logs", "会話ログ", "L", id="logs"),
]


@pytest.mark.parametrize(("tab", "label", "prefix"), RECORD_TABS)
def test_topbar_visible(page: Page, write_preview: WritePreview, make_item: MakeItem, tab: str, label: str, prefix: str) -> None:
    """トップバーを常に出し、開いている種類のタブを選んでいる（正常系）。"""
    # 準備・実行
    open_spa(page, write_preview(make_item(f"{prefix}-1")), f"?tab={tab}")
    # 検証
    expect(page.get_by_role("link", name=label)).to_have_attribute("aria-current", "page")


@pytest.mark.parametrize(("tab", "label", "prefix"), RECORD_TABS)
def test_table_visible(page: Page, write_preview: WritePreview, make_item: MakeItem, tab: str, label: str, prefix: str) -> None:
    """表を常に出し、表示形式の切り替えを持たない（正常系）。"""
    # 準備・実行
    open_spa(page, write_preview(make_item(f"{prefix}-1")), f"?tab={tab}")
    # 検証
    expect(page.get_by_role("table")).to_be_visible()
    expect(page.locator(f"tr[data-id='{prefix}-1']")).to_be_visible()
    expect(page.get_by_role("group", name="表示形式")).to_have_count(0)


def test_drawer_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """絞り込みのドロワーはトップバーの絞り込みのボタンを押したときに出す（正常系）。"""
    # 準備
    open_spa(page, write_preview(make_item("R-1")), "?tab=research")
    expect(page.get_by_role("dialog", name="絞り込み")).to_have_count(0)
    # 実行
    page.get_by_role("button", name="絞り込み").click()
    # 検証
    expect(page.get_by_role("dialog", name="絞り込み")).to_be_visible()


def test_drawer_initial_value(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """絞り込みのドロワーは、URL の `f.{列}` の条件を選んだ状態で開く（正常系）。"""
    # 準備
    url = write_preview(make_item("R-1", confidence="高"), make_item("R-2", confidence="低"))
    open_spa(page, url, "?tab=research&f.confidence=高")
    # 実行
    page.get_by_role("button", name="絞り込み").click()
    dialog = page.get_by_role("dialog", name="絞り込み")
    # 検証
    expect(dialog.get_by_role("checkbox", name="高")).to_be_checked()
    expect(dialog.get_by_role("checkbox", checked=True)).to_have_count(1)
    expect(page.locator("tr[data-id='R-2']")).to_have_count(0)


@pytest.mark.parametrize(("tab", "label", "prefix"), RECORD_TABS)
def test_region_visible(page: Page, write_preview: WritePreview, make_item: MakeItem, tab: str, label: str, prefix: str) -> None:
    """画面の領域を常に出し、見出しを開いている種類の名前にする（正常系）。"""
    # 準備・実行
    open_spa(page, write_preview(make_item(f"{prefix}-1")), f"?tab={tab}")
    # 検証
    expect(page.get_by_role("main").get_by_role("heading", level=1)).to_have_text(label)


@pytest.mark.parametrize(("tab", "label", "prefix"), RECORD_TABS)
def test_removed_band_visible(page: Page, write_removed_preview: WriteReviewPreview, tab: str, label: str, prefix: str) -> None:
    """選んだ時点でその種類の項目を消したときだけ消した項目の帯を出す（正常系）。"""
    # 準備
    url, _ = write_removed_preview()
    open_spa(page, url, f"?tab={tab}&diff=V-1")
    expect(page.get_by_role("region", name="この時点で消した項目")).to_have_count(0)
    # 実行
    open_spa(page, url, f"?tab={tab}&diff=V-2")
    # 検証
    expect(page.get_by_role("region", name="この時点で消した項目").get_by_role("listitem")).to_contain_text([f"{prefix}-3"])


def test_add_button_label(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """項目を追加のボタンの文言は「項目を追加」（正常系）。"""
    # 準備・実行
    open_spa(page, write_preview(make_item("G-1")), "?tab=terms")
    # 検証
    expect(page.get_by_role("button", name="用語集の項目を追加")).to_have_text("項目を追加")


def test_add_button_visible(page: Page, write_removed_preview: WriteReviewPreview) -> None:
    """項目を追加は差分の表示をしていないときだけ出す（正常系）。"""
    # 準備
    url, _ = write_removed_preview()
    open_spa(page, url, "?tab=notes")
    expect(page.get_by_role("button", name="メモの項目を追加")).to_be_visible()
    # 実行
    open_spa(page, url, "?tab=notes&diff=V-1")
    # 検証
    expect(page.get_by_role("button", name="メモの項目を追加")).to_have_count(0)


def test_pending_mark_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """保存待ちの編集がある記録にだけ、一覧の保存待ちの印を出す（正常系）。"""
    # 準備・実行
    url, _ = write_edit_preview(*edit_items(make_item, "N"), make_item("N-4", title="触らないメモ"), edits=edit_edits(make_edit, "N"))
    open_spa(page, url, "?tab=notes")
    # 検証
    expect(page.locator("tr[data-id='N-1']")).to_contain_text("保存待ち")
    expect(page.locator("tr[data-id='N-2']")).to_contain_text("保存で削除")
    expect(page.locator("tr[data-id='N-4']")).not_to_contain_text("保存")


def test_added_items_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """開いている種類の `item-add` が保存待ちにあるときは、表の先頭に追加する項目を出す（正常系）。"""
    # 準備・実行
    url, _ = write_edit_preview(
        make_item("G-1"),
        edits=(make_edit("E-1", target="new-1", op="item-add", key="terms", value={"title": "足す用語", "meaning": "意味"}, before=None, base=None),),
    )
    open_spa(page, url, "?tab=terms")
    # 検証
    expect(page.locator("tr[data-new-id]")).to_contain_text("足す用語")
    expect(page.locator("tbody tr").first).to_have_attribute("data-new-id", "new-1")
