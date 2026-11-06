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


def test_map_nodes(page: Page, spa_preview: str) -> None:
    """マップは elkjs で配置した節を描く（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&view=map")
    expect(page.locator('[data-node="D-1"]')).to_be_visible()


def test_map_lock(page: Page, spa_preview: str) -> None:
    """開いている節をもう一度押すとロックし、ロック中に余白を押しても選択を解除しない（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&view=map&id=D-1")
    page.locator('[data-node="D-1"]').wait_for()
    page.wait_for_timeout(500)
    page.locator('[data-node="D-1"]').click()
    expect(page.locator("[data-locked-key]")).to_be_visible()
    page.wait_for_timeout(500)
    page.locator("#decision-map").click(position={"x": 2, "y": 2})
    expect(page).to_have_url(re.compile("id=D-1"))


@pytest.mark.parametrize("search", ["?tab=decisions&view=table", "?tab=decisions", "?tab=tasks", "?tab=docs", "?tab=research"])
@pytest.mark.parametrize("viewport", [{"width": 1280, "height": 800}, {"width": 390, "height": 844}])
def test_list_screens_pass_axe_rules(page: Page, spa_preview: str, search: str, viewport: ViewportSize) -> None:
    """一覧の画面に見出しの h1 があり、表の見出しのボタンが押せる範囲を持つ（正常系）。"""
    page.set_viewport_size(viewport)
    open_spa(page, spa_preview, search)
    page.add_script_tag(path=str(AXE_SCRIPT))
    assert page.evaluate(AXE_RULES_JS) == []


# ─── 画面設計の要素の確認項目 ───

# マップを出す幅と、字下げの一覧にする幅
WIDE = {"width": 1280, "height": 800}
NARROW = {"width": 900, "height": 800}

# マップの倍率（transform の scale）を返す
_MAP_SCALE_JS = """() => {
    const match = document.querySelector('#decision-map').style.transform.match(/scale\\(([\\d.]+)\\)/);
    return match === null ? null : Number(match[1]);
}"""


def _map(page: Page, url: str, search: str = "") -> Page:
    """検討事項のマップを開き、節を描き終えるまで待つ。"""
    open_spa(page, url, f"?tab=decisions&view=map{search}")
    page.locator("#decision-map [data-node]").first.wait_for(state="attached")
    return page


def test_topbar_visible(page: Page, spa_preview: str) -> None:
    """トップバーを常に出し、検討事項のタブを開いている（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions")
    # 検証
    expect(page.get_by_role("link", name="検討事項")).to_have_attribute("aria-current", "page")


def test_view_switch_visible(page: Page, spa_preview: str) -> None:
    """表示形式の切り替えを常に出し、ボード・マップ・表を並べ、既定はボード（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions")
    group = page.get_by_role("group", name="表示形式")
    # 検証
    expect(group.get_by_role("button")).to_have_text(["ボード", "マップ", "表"])
    expect(group.get_by_role("button", name="ボード")).to_have_attribute("aria-pressed", "true")


def test_keyword_placeholder(page: Page, spa_preview: str) -> None:
    """キーワードの欄のプレースホルダは「タイトルで強調」（正常系）。"""
    # 準備・実行
    _map(page, spa_preview)
    # 検証
    expect(page.get_by_role("searchbox", name="タイトルで強調するキーワード")).to_have_attribute("placeholder", "タイトルで強調")


def test_keyword_visible(page: Page, spa_preview: str) -> None:
    """キーワードの欄は表示形式がマップのときだけ出す（正常系）。"""
    # 準備
    _map(page, spa_preview)
    expect(page.get_by_role("searchbox", name="タイトルで強調するキーワード")).to_be_visible()
    # 実行
    open_spa(page, spa_preview, "?tab=decisions&view=board")
    # 検証
    expect(page.get_by_role("searchbox", name="タイトルで強調するキーワード")).to_have_count(0)


def test_keyword_initial_value(page: Page, spa_preview: str) -> None:
    """キーワードの欄は空で開き、どの節も強調しない（正常系）。"""
    # 準備・実行
    _map(page, spa_preview)
    # 検証
    expect(page.get_by_role("searchbox", name="タイトルで強調するキーワード")).to_have_value("")
    expect(page.locator("#decision-map [data-node].bg-hit")).to_have_count(0)


@pytest.mark.parametrize("view", ["map", "board"])
def test_chips_visible(page: Page, spa_preview: str, view: str) -> None:
    """条件のチップは、マップ・ボードで値を選んだ条件があるときに出す（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, f"?tab=decisions&view={view}&f.status=保留")
    # 検証
    expect(page.get_by_role("button", name="状態: 保留 の条件を解除")).to_be_visible()


def test_map_visible(page: Page, spa_preview: str) -> None:
    """マップは表示形式がマップで幅 901px 以上のときに出し、幅 900px 以下では出さない（正常系）。"""
    # 準備
    page.set_viewport_size(WIDE)
    _map(page, spa_preview)
    expect(page.get_by_role("group", name="検討事項のマップ")).to_be_visible()
    # 実行
    page.set_viewport_size(NARROW)
    # 検証
    expect(page.get_by_role("group", name="検討事項のマップ")).to_be_hidden()


def test_map_action(page: Page, spa_preview: str) -> None:
    """マップの余白を押すと、選んでいる項目の詳細パネルを閉じ、URL から項目の ID を外す（正常系）。"""
    # 準備
    _map(page, spa_preview, "&id=D-1")
    expect(page.get_by_role("complementary", name="詳細")).to_be_visible()
    page.wait_for_timeout(500)
    # 実行
    page.locator("#decision-map").click(position={"x": 2, "y": 2})
    # 検証
    expect(page.get_by_role("complementary", name="詳細")).to_have_count(0)
    expect(page).not_to_have_url(re.compile("id=D-1"))


def test_zoom_buttons_visible(page: Page, spa_preview: str) -> None:
    """拡大・縮小・全体を表示は、マップで幅 901px 以上のときだけ出す（正常系）。"""
    # 準備
    page.set_viewport_size(WIDE)
    _map(page, spa_preview)
    zoom = page.get_by_role("group", name="拡大率")
    expect(zoom.get_by_role("button")).to_have_text(["−", "全体を表示", "＋"])
    # 実行
    page.set_viewport_size(NARROW)
    # 検証
    expect(zoom).to_be_hidden()


def test_outline_visible(page: Page, spa_preview: str) -> None:
    """字下げの一覧は、マップで幅 900px 以下のときだけ出す（正常系）。"""
    # 準備
    page.set_viewport_size(WIDE)
    _map(page, spa_preview)
    outline = page.get_by_role("navigation", name="検討事項の一覧")
    expect(outline).to_be_hidden()
    # 実行
    page.set_viewport_size(NARROW)
    # 検証
    expect(outline).to_be_visible()
    expect(outline.locator("button[data-id='D-1']")).to_contain_text("記録の形")


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


def test_no_match_label(page: Page, spa_preview: str) -> None:
    """マップで条件に合う検討事項が無いときは「表示する検討事項はありません。」と出す（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions&view=map&f.status=取り下げ")
    # 検証
    expect(page.get_by_text("表示する検討事項はありません。").first).to_be_visible()


def test_no_match_visible(page: Page, spa_preview: str) -> None:
    """条件に合う検討事項があるときは、条件に合う検討事項が無い旨を出さない（正常系）。"""
    # 準備・実行
    _map(page, spa_preview)
    # 検証
    expect(page.get_by_text("表示する検討事項はありません。")).to_have_count(0)


@pytest.mark.parametrize("view", ["map", "board"])
def test_diff_mark_visible(page: Page, write_history_preview: WriteReviewPreview, view: str) -> None:
    """差分の表示の間、選んだ時点で足した検討事項のマップ・ボードに新規の印を出し、差分の表示でないときは出さない（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, f"?tab=decisions&view={view}&f.status=決定済み|未決定")
    expect(page.locator("[data-node='D-2'] [title=新規], [data-id='D-2'] [title=新規]")).to_have_count(0)
    # 実行
    open_spa(page, url, f"?tab=decisions&view={view}&f.status=決定済み|未決定&diff=V-1")
    # 検証
    expect(page.locator("[data-node='D-2'] [title=新規], [data-id='D-2'] [title=新規]").first).to_be_visible()


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


def test_wheel_zoom_visible(page: Page, spa_preview: str) -> None:
    """マップでホイールを奥へ回すと倍率を 1.12 倍にし、「全体を表示」を外す（正常系）。"""
    # 準備
    page.set_viewport_size(WIDE)
    _map(page, spa_preview)
    before = page.evaluate(_MAP_SCALE_JS)
    box = page.get_by_role("group", name="検討事項のマップ").bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + 20, box["y"] + 20)
    # 実行
    page.mouse.wheel(0, -100)
    page.wait_for_function(f"document.querySelector('#decision-map').style.transform !== 'scale({before})'")
    # 検証
    assert abs(page.evaluate(_MAP_SCALE_JS) - min(1.5, before * 1.12)) < 0.01
    expect(page.get_by_role("button", name="全体を表示")).to_have_attribute("aria-pressed", "false")


def test_wheel_zoom_action(page: Page, spa_preview: str) -> None:
    """横にだけ回したホイール（`deltaY` が 0）では倍率を変えない（正常系）。"""
    # 準備
    page.set_viewport_size(WIDE)
    _map(page, spa_preview)
    before = page.evaluate(_MAP_SCALE_JS)
    box = page.get_by_role("group", name="検討事項のマップ").bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + 20, box["y"] + 20)
    # 実行
    page.mouse.wheel(100, 0)
    page.wait_for_timeout(300)
    # 検証
    assert page.evaluate(_MAP_SCALE_JS) == before
    expect(page.get_by_role("button", name="全体を表示")).to_have_attribute("aria-pressed", "true")


def test_region_visible(page: Page, spa_preview: str) -> None:
    """画面の領域を常に出し、見出しを「検討事項」にする（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions")
    # 検証
    expect(page.get_by_role("main").get_by_role("heading", level=1)).to_have_text("検討事項")


def test_layer_labels_visible(page: Page, write_sample_preview: WriteSamplePreview) -> None:
    """マップの幅 901px 以上では、対象・カテゴリー・フェーズの中間の層のラベルを節として出す（正常系）。"""
    # 準備・実行
    page.set_viewport_size(WIDE)
    _map(page, write_sample_preview())
    # 検証
    expect(page.locator("#decision-map div[data-node]").filter(has_text="データ構造")).to_have_count(1)
    expect(page.locator("#decision-map div[data-node]").filter(has_text="画面")).to_have_count(1)


@pytest.mark.parametrize("view", ["map", "board"])
def test_comment_mark_visible(page: Page, write_commented_preview: WriteReviewPreview, view: str) -> None:
    """レビュー中のコメントがある検討事項のマップ・ボードにだけ、コメントの印を出す（正常系）。"""
    # 準備・実行
    url, _ = write_commented_preview()
    open_spa(page, url, f"?tab=decisions&view={view}")
    # 検証
    expect(page.locator("[data-node='D-2'] [title='コメント 2 件'], [data-id='D-2'] [title='コメント 2 件']").first).to_be_visible()
    expect(page.locator("[data-node='D-4'] [title^='コメント'], [data-id='D-4'] [title^='コメント']")).to_have_count(0)


def test_lock_key_visible(page: Page, spa_preview: str) -> None:
    """開いた鍵はロックしていないとき詳細を開いている節にカーソルを乗せたときだけ出し、ロックすると閉じた鍵を残す（正常系）。"""
    # 準備
    page.set_viewport_size(WIDE)
    _map(page, spa_preview, "&id=D-1")
    node = page.locator('#decision-map [data-node="D-1"]')
    expect(page.locator("[data-locked-key]")).to_have_count(0)
    page.wait_for_timeout(500)
    # 実行
    node.click()
    # 検証
    expect(node.locator("[data-locked-key]")).to_be_visible()
    page.get_by_role("complementary", name="詳細").get_by_role("button", name="詳細を閉じる").click()
    expect(node.locator("[data-locked-key]")).to_be_visible()


def test_lock_gesture_visible(page: Page, spa_preview: str) -> None:
    """幅 900px 以下の字下げの一覧では、詳細を開いている項目を押し直してもロックしない（正常系）。"""
    # 準備
    page.set_viewport_size(NARROW)
    _map(page, spa_preview)
    outline = page.get_by_role("navigation", name="検討事項の一覧")
    detail = page.get_by_role("complementary", name="詳細")
    # 実行
    outline.locator("button[data-id='D-1']").click()
    expect(detail).to_be_visible()
    detail.get_by_role("button", name="詳細を閉じる").click()
    outline.locator("button[data-id='D-1']").click()
    # 検証
    expect(detail).to_be_visible()
    expect(page.locator("[data-locked-key]")).to_have_count(0)


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


@pytest.mark.parametrize("view", ["board", "table", "map"])
def test_pending_mark_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit, view: str) -> None:
    """保存待ちの編集がある検討事項にだけ、一覧の保存待ちの印を出す（正常系）。"""
    # 準備・実行
    url, _ = write_edit_preview(*edit_items(make_item, "D"), make_item("D-4", title="触らない項目"), edits=edit_edits(make_edit, "D"))
    open_spa(page, url, f"?tab=decisions&view={view}")
    # 検証
    expect(page.locator(f"[data-{'node' if view == 'map' else 'id'}='D-1'] [title=保存待ち], [data-id='D-1'] :text('保存待ち')").first).to_be_visible()
    expect(page.locator("[data-node='D-4'] [title^=保存], [data-id='D-4'] :text('保存')")).to_have_count(0)


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
