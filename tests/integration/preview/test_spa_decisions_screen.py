"""画面設計『検討事項.tsx』の結合テスト。"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, ViewportSize, expect
from preview_edit_helpers import edit_edits, edit_items
from preview_fixture_types import WritePreview, WriteReviewPreview, WriteSamplePreview
from preview_spa_helpers import AXE_SCRIPT, assert_below_topbar, open_spa
from preview_favorites_helpers import assert_card_star_toggles, assert_favorites_only_chip, assert_star_column, seed_prefs
from workspace_fixtures import MakeEdit, MakeItem
from preview_record_id_helpers import LINKED_TITLE, TARGET_TITLE, assert_described, assert_tip

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
    expect(page.get_by_role("cell", name="記録の形", exact=True)).to_be_visible()
    page.get_by_role("button", name="タイトルで並べ替え").click()
    expect(page.get_by_role("columnheader", name="タイトル")).to_have_attribute("aria-sort", "ascending")
    expect(page).to_have_url(re.compile("sort=title"))


def test_filter_drawer(page: Page, spa_preview: str) -> None:
    """ドロワーの条件で絞り、チップで解除する（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&view=table&f.status=%E4%BF%9D%E7%95%99")
    expect(page.get_by_role("cell", name="画面の幅", exact=True)).to_be_visible()
    expect(page.get_by_role("cell", name="記録の形", exact=True)).to_be_hidden()
    page.get_by_role("button", name="状態: 保留 の条件を解除").click()
    expect(page.get_by_role("cell", name="記録の形", exact=True)).to_be_visible()


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
    expect(page.locator("[data-card='D-2'] [title=新規]")).to_have_count(0)
    # 実行
    open_spa(page, url, "?tab=decisions&view=board&f.status=決定済み|未決定&diff=V-1")
    # 検証
    expect(page.locator("[data-card='D-2'] [title=新規]").first).to_be_visible()


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
    expect(page.locator("[data-card='D-2'] [title='コメント 2 件']").first).to_be_visible()
    expect(page.locator("[data-card='D-4'] [title^='コメント']")).to_have_count(0)


SHAKE_EARLY_MS = 120


def test_removed_band_visible(page: Page, write_removed_preview: WriteReviewPreview) -> None:
    """選んだ時点で検討事項を消したときだけ削除した項目の帯を出す（正常系）。"""
    # 準備
    url, _ = write_removed_preview()
    open_spa(page, url, "?tab=decisions&diff=V-1")
    expect(page.get_by_role("region", name="この時点で削除した項目")).to_have_count(0)
    # 実行
    open_spa(page, url, "?tab=decisions&diff=V-2")
    # 検証
    expect(page.get_by_role("region", name="この時点で削除した項目").get_by_role("listitem")).to_contain_text(["D-3", "D-4"])


def test_add_button_label(page: Page, spa_preview: str) -> None:
    """項目を追加のボタンの文言は「項目を追加」（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions")
    # 検証
    expect(page.get_by_role("button", name="検討事項の項目を追加")).to_have_text("項目追加")


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
    expect(page.locator("[data-card='D-1'] :text('保存待ち'), tr[data-id='D-1'] :text('保存待ち')").first).to_be_visible()
    expect(page.locator("[data-card='D-4'] :text('保存'), tr[data-id='D-4'] :text('保存')")).to_have_count(0)


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


def _tags(*names: str) -> list[dict[str, str]]:
    """タグの名前の並びを項目の `tags` にする。"""
    return [{"name": name} for name in names]


def test_board_tag_press(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """ボードのカードのタグを押すと詳細を開かずに f.tags に加える（正常系）。"""
    # 準備
    url = write_preview(
        make_item("D-1", title="記録の形", status="未決定", tags=_tags("画面")),
        make_item("D-2", title="画面の幅", status="未決定", tags=_tags("保存")),
    )
    open_spa(page, url, "?tab=decisions&view=board")
    # 実行
    page.locator("[data-card='D-1']").get_by_role("button", name="タグ「画面」で絞り込む").click()
    # 検証
    expect(page).to_have_url(re.compile(r"f\.tags=%E7%94%BB%E9%9D%A2"))
    expect(page.locator("[data-card='D-2']")).to_have_count(0)
    expect(page.get_by_role("complementary", name="詳細")).to_have_count(0)

# ─── 絞り込みのドロワーの上端（トップバーの下） ───


@pytest.mark.parametrize(
    "size",
    [pytest.param({"width": 1280, "height": 800}, id="wide"), pytest.param({"width": 390, "height": 844}, id="phone")],
)
def test_drawer_below_topbar(page: Page, spa_preview: str, size: dict[str, int]) -> None:
    """絞り込みのドロワーはトップバーとタブを覆わず、その下端から画面の下端まで出す（正常系）。"""
    # 準備
    page.set_viewport_size(size)
    open_spa(page, spa_preview, "?tab=decisions")
    # 実行
    page.get_by_role("button", name="絞り込み").click()
    # 検証
    assert_below_topbar(page, page.get_by_role("dialog", name="絞り込み"))


# ─── 作成日時・更新日時と並べ替え（#186・#364） ───


def _dated_items(make_item: MakeItem) -> tuple[dict[str, object], ...]:
    """更新日時が D-1 < D-3 < D-2 の同じ状態の 3 件を返す。"""
    return (
        make_item("D-1", title="一つ目", created="2026-11-01T00:00:00+00:00", updated="2026-11-02T00:00:00+00:00"),
        make_item("D-2", title="二つ目", created="2026-11-03T00:00:00+00:00", updated="2026-11-20T00:00:00+00:00"),
        make_item("D-3", title="三つ目", created="2026-11-02T00:00:00+00:00", updated="2026-11-10T00:00:00+00:00"),
    )


def _column_ids(page: Page) -> list[str]:
    """「未決定」の列のカードの ID を並び順に返す。"""
    return page.get_by_role("region", name="未決定").locator("[data-card]").evaluate_all("cards => cards.map((card) => card.dataset.card)")


def test_board_card_sort_default(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """ボードは開いた直後は連番の順で、「並べ替え」の「連番」が押された見た目になる。カードに作成日時・更新日時を出す（正常系）。"""
    # 準備・実行
    open_spa(page, write_preview(*_dated_items(make_item)), "?tab=decisions")
    # 検証
    expect(page.get_by_role("group", name="並べ替え").get_by_role("button", name="連番")).to_have_attribute("aria-pressed", "true")
    assert _column_ids(page) == ["D-1", "D-2", "D-3"]
    expect(page.locator("[data-card='D-2'] [data-part='item-dates'] > span")).to_have_text(["作成 11/03 09:00", "更新 11/20 09:00"])


def test_board_card_sort_updated(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """「更新日時」を押すと列の中が更新日時の新しい順になり、URL に `sort=-updated` が入る（正常系）。"""
    # 準備
    open_spa(page, write_preview(*_dated_items(make_item)), "?tab=decisions")
    # 実行
    page.get_by_role("group", name="並べ替え").get_by_role("button", name="更新日時").click()
    # 検証
    expect(page).to_have_url(re.compile(r"sort=-updated"))
    expect(page.locator("[data-card]").first).to_have_attribute("data-card", "D-2")
    assert _column_ids(page) == ["D-2", "D-3", "D-1"]


def test_table_date_columns(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """表に作成日時・更新日時の列があり、セルは `time` で JST の日時を出す（正常系）。"""
    # 準備・実行
    open_spa(page, write_preview(*_dated_items(make_item)), "?tab=decisions&view=table")
    row = page.get_by_role("row").filter(has_text="二つ目")
    # 検証
    expect(page.get_by_role("columnheader", name=re.compile("更新日時"))).to_be_visible()
    expect(row.locator("time[datetime='2026-11-20T00:00:00+00:00']")).to_have_text("11/20 09:00")


def test_card_title_id_markers(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """カードのタイトルの中の記録にある D-1 をマーカーにし、乗せると D-1 のツールチップを出し、押すとカードの詳細を開く（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1", title=TARGET_TITLE, status="未決定"), make_item("D-2", title=LINKED_TITLE, status="未決定"))
    open_spa(page, url, "?tab=decisions&view=board")
    card = page.locator("[data-card='D-2']")
    marker = card.locator("button[data-id] [data-record-id='D-1']")
    # 実行
    marker.hover()
    # 検証
    expect(card.locator("[data-record-id='D-99'], a")).to_have_count(0)
    assert_tip(page)
    assert_described(page, card.locator("button[data-id]"))
    marker.click()
    expect(page).to_have_url(re.compile(r"id=D-2"))


# ─── お気に入り ───


def test_favorite_star_on_board(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """ボードのカードの右上の星を押すと登録・解除し、カードは開かない（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1", title="星の項目"))
    open_spa(page, url, "?tab=decisions&view=board")
    # 実行・検証
    assert_card_star_toggles(page, "D-1", "星の項目")


def test_favorite_column_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """表の一番左に「お気に入り」の列を出し、見出しで並べ替える（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1"), make_item("D-2"), make_item("D-3"))
    seed_prefs(page, {"favorites": ["D-2"]})
    open_spa(page, url, "?tab=decisions&view=table")
    # 実行・検証
    assert_star_column(page, "D-2")


def test_favorites_only_chip_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """「お気に入りだけを表示する」の間はボードに「お気に入りのみ」のチップを出し、× で解除する（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1"), make_item("D-2"))
    seed_prefs(page, {"favorites": ["D-1"], "favoritesOnly": True})
    open_spa(page, url, "?tab=decisions&view=board")
    # 実行・検証
    assert_favorites_only_chip(page, "D-1", "D-2")
