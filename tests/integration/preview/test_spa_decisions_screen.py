"""画面設計『検討事項.tsx』の結合テスト。"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, ViewportSize, expect
from preview_edit_helpers import edit_edits, edit_items
from preview_fixture_types import WriteReviewPreview, WriteSamplePreview
from preview_spa_helpers import AXE_SCRIPT, open_spa
from workspace_fixtures import MakeEdit, MakeItem

# 押せる範囲と h1 の axe の規則を当て、違反を返す
AXE_RULES_JS = """async () => {
  const result = await axe.run(document, { runOnly: ["target-size", "page-has-heading-one"] });
  return result.violations.flatMap((rule) => rule.nodes.map((node) => `${rule.id}: ${node.target.join(" ")}`));
}"""


def test_board_is_default(page: Page, spa_preview: str) -> None:
    """既定はボードで、状態の列にカードを並べる（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions")
    expect(page.get_by_role("button", name="ボード", exact=True)).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_role("region", name="未決定")).to_contain_text("記録の形")


def test_table_sort(page: Page, spa_preview: str) -> None:
    """表の見出しを押すと昇順に並べ、URL に残す（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions")
    page.get_by_role("button", name="表", exact=True).click()
    expect(page.get_by_role("cell", name="記録の形")).to_be_visible()
    page.get_by_role("button", name="タイトルで並べ替え").click()
    expect(page.get_by_role("columnheader", name="タイトル")).to_have_attribute("aria-sort", "ascending")
    expect(page).to_have_url(re.compile("sort=title"))


def test_filter_drawer(page: Page, spa_preview: str) -> None:
    """ドロワーの条件で絞り、チップで解除する（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&view=table&f.status=%E4%BF%9D%E7%95%99")
    expect(page.get_by_role("cell", name="画面の幅")).to_be_visible()
    expect(page.get_by_role("cell", name="記録の形")).to_be_hidden()
    page.get_by_role("button", name="状態: 保留 の条件を解除").click()
    expect(page.get_by_role("cell", name="記録の形")).to_be_visible()


@pytest.mark.parametrize("search", ["?tab=decisions&view=table", "?tab=decisions", "?tab=tasks", "?tab=docs", "?tab=research"])
@pytest.mark.parametrize("viewport", [{"width": 1280, "height": 800}, {"width": 390, "height": 844}])
def test_list_screens_pass_axe_rules(page: Page, spa_preview: str, search: str, viewport: ViewportSize) -> None:
    """一覧の画面に見出しの h1 があり、表の見出しのボタンが押せる範囲を持つ（正常系）。"""
    page.set_viewport_size(viewport)
    open_spa(page, spa_preview, search)
    page.add_script_tag(path=str(AXE_SCRIPT))
    assert page.evaluate(AXE_RULES_JS) == []


# ─── 画面設計の要素の確認項目 ───

NARROW = {"width": 900, "height": 800}


def test_topbar_visible(page: Page, spa_preview: str) -> None:
    """トップバーを常に出し、検討事項のタブを開いている（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions")
    # 検証
    expect(page.get_by_role("link", name="検討事項")).to_have_attribute("aria-current", "page")


def test_view_switch_visible(page: Page, spa_preview: str) -> None:
    """表示形式の切り替えを常に出し、ボード・表を並べ、既定はボード（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions")
    group = page.get_by_role("group", name="表示形式")
    # 検証
    expect(group.get_by_role("button")).to_have_text(["ボード", "表"])
    expect(group.get_by_role("button", name="ボード")).to_have_attribute("aria-pressed", "true")


def test_chips_visible(page: Page, spa_preview: str) -> None:
    """条件のチップは、ボードで値を選んだ条件があるときに出す（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions&view=board&f.status=保留")
    # 検証
    expect(page.get_by_role("button", name="状態: 保留 の条件を解除")).to_be_visible()


def test_board_visible(page: Page, spa_preview: str) -> None:
    """表示形式がボードのときは状態の列のボードを出す（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions&view=board")
    # 検証
    expect(page.get_by_role("region", name="未決定")).to_contain_text("記録の形")
    expect(page.get_by_role("table")).to_have_count(0)


def test_table_visible(page: Page, spa_preview: str) -> None:
    """表示形式が表のときは表を出す（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions&view=table")
    # 検証
    expect(page.get_by_role("table")).to_be_visible()
    expect(page.locator("tr[data-id='D-1']")).to_be_visible()


def test_diff_mark_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """差分の表示の間、選んだ時点で足した検討事項のボードに新規の印を出し、差分の表示でないときは出さない（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions&view=board&f.status=決定済み|未決定")
    expect(page.locator("[data-id='D-2'] [title=新規]")).to_have_count(0)
    # 実行
    open_spa(page, url, "?tab=decisions&view=board&f.status=決定済み|未決定&diff=V-1")
    # 検証
    expect(page.locator("[data-id='D-2'] [title=新規]").first).to_be_visible()


def test_drawer_visible(page: Page, spa_preview: str) -> None:
    """絞り込みのドロワーはトップバーの絞り込みのボタンを押したときに出す（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=decisions")
    expect(page.get_by_role("dialog", name="絞り込み")).to_have_count(0)
    # 実行
    page.get_by_role("button", name="絞り込み").click()
    # 検証
    expect(page.get_by_role("dialog", name="絞り込み")).to_be_visible()


def test_drawer_initial_value(page: Page, write_sample_preview: WriteSamplePreview) -> None:
    """絞り込みのドロワーは、状態で要見直し・未決定・未整理・保留を選んだ状態で開く（記録に無い未整理は並べない）（正常系）。"""
    # 準備
    open_spa(page, write_sample_preview(), "?tab=decisions")
    # 実行
    page.get_by_role("button", name="絞り込み").click()
    dialog = page.get_by_role("dialog", name="絞り込み")
    # 検証
    expect(dialog.get_by_role("checkbox", name=re.compile("^要見直し"))).to_be_checked()
    expect(dialog.get_by_role("checkbox", name=re.compile("^未決定"))).to_be_checked()
    expect(dialog.get_by_role("checkbox", name=re.compile("^保留"))).to_be_checked()
    expect(dialog.get_by_role("checkbox", name=re.compile("^決定済み"))).not_to_be_checked()


def test_region_visible(page: Page, spa_preview: str) -> None:
    """画面の領域を常に出し、見出しを「検討事項」にする（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions")
    # 検証
    expect(page.get_by_role("main").get_by_role("heading", level=1)).to_have_text("検討事項")


def test_comment_mark_visible(page: Page, write_commented_preview: WriteReviewPreview) -> None:
    """レビュー中のコメントがある検討事項のボードにだけ、コメントの印を出す（正常系）。"""
    # 準備・実行
    url, _ = write_commented_preview()
    open_spa(page, url, "?tab=decisions&view=board")
    # 検証
    expect(page.locator("[data-id='D-2'] [title='コメント 2 件']").first).to_be_visible()
    expect(page.locator("[data-id='D-4'] [title^='コメント']")).to_have_count(0)


SHAKE_EARLY_MS = 120


def test_removed_band_visible(page: Page, write_removed_preview: WriteReviewPreview) -> None:
    """選んだ時点で検討事項を消したときだけ消した項目の帯を出す（正常系）。"""
    # 準備
    url, _ = write_removed_preview()
    open_spa(page, url, "?tab=decisions&diff=V-1")
    expect(page.get_by_role("region", name="この時点で消した項目")).to_have_count(0)
    # 実行
    open_spa(page, url, "?tab=decisions&diff=V-2")
    # 検証
    expect(page.get_by_role("region", name="この時点で消した項目").get_by_role("listitem")).to_contain_text(["D-3", "D-4"])


def test_add_button_label(page: Page, spa_preview: str) -> None:
    """項目を追加のボタンの文言は「項目を追加」（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions")
    # 検証
    expect(page.get_by_role("button", name="検討事項の項目を追加")).to_have_text("項目を追加")


def test_add_button_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """項目を追加は差分の表示をしていないときだけ出す（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions")
    expect(page.get_by_role("button", name="検討事項の項目を追加")).to_be_visible()
    # 実行
    open_spa(page, url, "?tab=decisions&diff=V-1")
    # 検証
    expect(page.get_by_role("button", name="検討事項の項目を追加")).to_have_count(0)


@pytest.mark.parametrize("view", ["board", "table"])
def test_pending_mark_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit, view: str) -> None:
    """保存待ちの編集がある検討事項にだけ、一覧の保存待ちの印を出す（正常系）。"""
    # 準備・実行
    url, _ = write_edit_preview(*edit_items(make_item, "D"), make_item("D-4", title="触らない項目"), edits=edit_edits(make_edit, "D"))
    open_spa(page, url, f"?tab=decisions&view={view}")
    # 検証
    expect(page.locator("[data-id='D-1'] :text('保存待ち')").first).to_be_visible()
    expect(page.locator("[data-id='D-4'] :text('保存')")).to_have_count(0)


def test_added_items_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """検討事項の `item-add` が保存待ちにあるときは、追加する項目を出す（正常系）。"""
    # 準備・実行
    url, _ = write_edit_preview(
        make_item("D-1", status="未決定"),
        edits=(make_edit("E-1", target="new-1", op="item-add", key="decisions", value={"title": "足す問い", "status": "未決定"}, before=None, base=None),),
    )
    open_spa(page, url, "?tab=decisions&view=board")
    # 検証
    expect(page.locator("[data-new-id]")).to_contain_text("足す問い")
