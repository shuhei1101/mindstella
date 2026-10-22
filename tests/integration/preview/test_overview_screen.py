"""画面設計『概要』（タイルの項目 ID で要素を引く）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page
from preview_edit_helpers import (
    PENDING_BUTTON,
    assert_topbar_pending,
    edit_edits,
    edit_items,
)
from preview_fit_helpers import assert_fits_smallest, set_smallest
from preview_fixture_types import OpenPreview, WritePreview, WriteReviewPreview, WriteSamplePreview
from preview_history_helpers import assert_topbar_history, preselect_diff
from preview_layout_helpers import assert_bands_stay, assert_page_does_not_scroll, region_metrics
from preview_removed_helpers import REMOVED_IN_V2_BY_TAB
from workspace_fixtures import ADOPTED_OPTIONS, CallTool, MakeEdit, MakeItem, MakeWorkspace

# 概要のタイルの項目 ID
TILE_IDS = (
    "tile-next",
    "tile-goal",
    "tile-review",
    "tile-hold",
    "tile-running",
    "tile-progress",
)


def _chips(page: Page) -> list[str]:
    """表の上に並んでいる条件のチップの文字を返す。"""
    return page.eval_on_selector_all(".chips .chip", "chips => chips.map(c => c.textContent)")


def _row_ids(page: Page) -> list[str]:
    """表に並んでいる行の ID を上から返す。"""
    return page.eval_on_selector_all("table.grid tbody tr", "rows => rows.map(r => r.dataset.id)")


def test_tiles_are_laid_out(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """6 つのタイルが項目 ID で引け、概要の題名が h1 になる（正常系）。"""
    # 準備
    url = write_sample_preview()
    # 実行
    page = open_preview(url)
    # 検証
    for tile_id in TILE_IDS:
        assert page.locator(f"#{tile_id}").count() == 1
    assert page.inner_text("main h1") == "要件出しのスキル mindmap を設計する"


def test_next_tile(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """次に検討する項目を build が埋め込んだ順に並べ、押すと詳細パネルを開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    # 実行
    ids = page.eval_on_selector_all("#tile-next button[data-id]", "b => b.map(x => x.dataset.id)")
    impact = page.inner_text('#tile-next button[data-id="D-2"] .impact')
    page.click('#tile-next button[data-id="D-2"]')
    # 検証
    assert ids == ["D-2", "D-5"]
    # 影響度の目盛りの横には、軸の名前を添える
    assert impact == "影響度 大"
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-2の題"


def test_next_tile_show_all(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """すべて表示で、検討事項の表を 未決定 × 着手可否 = 着手可能 で絞って開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    # 実行
    page.click("#tile-next .t-link")
    page.wait_for_selector("table.grid")
    # 検証
    assert _chips(page) == ["状態: 未決定", "着手可否: 着手可能"]
    assert _row_ids(page) == ["D-2", "D-5"]


def test_next_tile_when_nothing_to_discuss(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """次に検討する項目が無いときは、その旨を出して「すべて表示」を置かない（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1", status="決定済み", options=ADOPTED_OPTIONS))
    # 実行
    page = open_preview(url)
    # 検証
    assert "次に検討する項目はありません。" in page.inner_text("#tile-next")
    assert page.locator("#tile-next .t-link").count() == 0


def test_goal_tile(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ゴールのフェーズまでの決定済みの数・フェーズごとの棒・納品物のチェックリストを出す（正常系）。"""
    # 準備
    url = write_sample_preview()
    # 実行
    page = open_preview(url)
    # 検証
    assert page.inner_text("#tile-goal .big").replace("\n", "").replace(" ", "") == "1/3"
    stages = page.eval_on_selector_all(
        "#tile-goal .stage-rows li", "rows => rows.map(r => r.textContent)"
    )
    assert stages == ["目的1/1", "要件0/2"]
    assert page.locator("#tile-goal .checklist li.done").count() == 1
    assert "1/1" in page.inner_text("#tile-goal .deliv-head")
    # 納品物を押すと、その資料の詳細パネルを開く
    page.click("#tile-goal .checklist button")
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "A-1の題\n納品物"


def test_goal_tile_when_no_goal(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """ゴールが無いときは、見出しを「フェーズ別の進捗」にし、ゴールが無いことと全フェーズの棒だけを出す（正常系）。"""
    # 準備
    settings = {
        **{key: value for key, value in valid_settings.items() if key != "goal"},
        "phases": ["目的", "要件"],
    }
    url = write_preview(
        make_item("D-1", phase="目的", status="決定済み", options=ADOPTED_OPTIONS),
        make_item("D-2", phase="要件", status="未決定"),
        settings=settings,
    )
    # 実行
    page = open_preview(url)
    # 検証
    assert page.inner_text("#tile-goal h2") == "フェーズ別の進捗"
    assert page.inner_text("#tile-goal .goal-none") == "ゴールは決まっていません"
    assert page.inner_text("#tile-goal .big").replace("\n", "").replace(" ", "") == "1/2"
    stages = page.eval_on_selector_all(
        "#tile-goal .stage-rows li", "rows => rows.map(r => r.textContent)"
    )
    assert stages == ["目的1/1", "要件0/1"]
    # 納品物は出さない
    assert page.locator("#tile-goal .deliv").count() == 0


def test_description(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """設定の話し合いの概要を題名の上に出し、プレイブックの名前は出さない（正常系）。"""
    # 準備
    description = "スキル mindmap の記録の形とプレビューの画面を、作り始められるところまで決める話し合い。"
    url = write_preview(make_item("D-1"), settings={**valid_settings, "description": description})
    # 実行
    page = open_preview(url)
    # 検証
    assert page.inner_text("#overview-description") == description
    rows = page.eval_on_selector_all("main .hero > *", "els => els.map(e => e.textContent)")
    assert rows == [description, "要件出しのスキル mindmap を設計する"]
    assert "システム開発" not in page.inner_text("main .hero")


def test_description_when_missing(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """話し合いの概要が無い設定では、行を出さず題名がそのまま上に来る（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1"))
    # 実行
    page = open_preview(url)
    # 検証
    assert page.locator("#overview-description").count() == 0
    assert page.inner_text("main .hero") == "要件出しのスキル mindmap を設計する"


def test_small_tiles(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """要見直し・保留・進行中のタスクの件数と名前を出し、押すと詳細パネルを開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    # 実行
    counts = {
        tile_id: page.inner_text(f"#{tile_id} .num")
        for tile_id in ("tile-review", "tile-hold", "tile-running")
    }
    page.click('#tile-hold button[data-id="D-4"]')
    # 検証
    assert counts == {"tile-review": "1", "tile-hold": "1", "tile-running": "1"}
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-4の題"


def test_small_tiles_show_all(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """要見直しのすべて表示で、検討事項の表を 状態 = 要見直し で絞って開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    # 実行
    page.click("#tile-review .t-link")
    page.wait_for_selector("table.grid")
    # 検証
    assert _chips(page) == ["状態: 要見直し"]
    assert _row_ids(page) == ["D-3"]


def test_small_tiles_when_empty(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """該当する項目が無いタイルは 0 件と、種類の名前で「〇〇はありません。」を出す（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1", status="決定済み", options=ADOPTED_OPTIONS))
    # 実行
    page = open_preview(url)
    # 検証
    empty_texts = {
        "tile-review": "要見直しの検討事項はありません。",
        "tile-hold": "保留の検討事項はありません。",
        "tile-running": "進行中のタスクはありません。",
    }
    for tile_id, text in empty_texts.items():
        assert page.inner_text(f"#{tile_id} .num") == "0"
        assert page.inner_text(f"#{tile_id} .empty") == text


def test_progress_tile(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """カテゴリー別の進み具合をカテゴリー × フェーズで出し、セルとカテゴリー名で表を絞る（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    # 実行・検証
    totals = page.eval_on_selector_all(
        "#tile-progress td.tot", "cells => cells.map(c => c.textContent)"
    )
    assert totals == ["1/2", "0/3"]
    # 項目の無いセルは押せない
    assert page.locator("#tile-progress td >> text=—").count() == 2
    # セルを押すと、そのカテゴリーとフェーズで絞った表を開く
    page.click('#tile-progress button.cell[aria-label^="画面 の 構成"]')
    page.wait_for_selector("table.grid")
    assert _chips(page) == ["カテゴリー: 画面", "フェーズ: 構成"]
    assert _row_ids(page) == ["D-4", "D-5"]


def test_progress_tile_category_link(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """行の見出しを押すと、カテゴリーだけで絞った表を開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    # 実行
    page.click("#tile-progress button.cat-link >> text=データ構造")
    page.wait_for_selector("table.grid")
    # 検証
    assert _chips(page) == ["カテゴリー: データ構造"]
    assert _row_ids(page) == ["D-1", "D-2"]


def test_diff_marks(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """差分の表示の間、タイルの項目のタイトルの横に印を文言なしで置く。トップバーに選んだ時点の札を出す（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    preselect_diff(page, "since")
    open_preview(url, "#tab=overview")
    page.wait_for_selector("#tile-next button[data-id]")
    # 検証
    next_mark = page.locator('#tile-next button[data-id="D-2"] .df-mark')
    assert next_mark.get_attribute("class") == "df-mark df-chg"
    assert next_mark.inner_text() == "変更"
    running_mark = page.locator('#tile-running button[data-id="T-1"] .df-mark')
    assert running_mark.get_attribute("title") == "変更"
    assert page.locator("#tile-next .df-badge, #tile-running .df-badge").count() == 0
    assert_topbar_history(page)


def test_diff_marks_when_removed(
    write_removed_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """差分の表示の間、消した項目を持つ種類のタブに点を付ける。消した項目はタイルに並べない（正常系）。"""
    # 準備・実行
    url, _ = write_removed_preview()
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=overview")
    page.wait_for_selector("#tile-next")
    # 検証
    dotted = page.eval_on_selector_all(
        "nav.tabbar a.tab:has(.df-dot)", "tabs => tabs.map(t => t.dataset.tab)"
    )
    assert dotted == list(REMOVED_IN_V2_BY_TAB)
    assert page.locator('main#main [data-id="D-3"], main#main [data-id="D-4"]').count() == 0
    assert_topbar_history(page)



# 検討事項・タスク・資料を表示しない種類の既定
KINDS_WITHOUT_DECISIONS_TASKS_DOCS = ["research", "terms", "notes", "logs"]


def test_hidden_kinds_keep_tiles(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    sample_items: list[dict[str, Any]],
    sample_settings: dict[str, Any],
    sample_bodies: dict[str, str],
) -> None:
    """表示しない種類のタイルは残し、その種類の画面へ移る「すべて表示」と進捗のセルのリンクだけを外す（正常系）。"""
    # 準備
    settings = {
        **sample_settings,
        "display": {"visible_kinds": KINDS_WITHOUT_DECISIONS_TASKS_DOCS},
    }
    url = write_preview(*sample_items, settings=settings, bodies=sample_bodies)
    # 実行
    page = open_preview(url)
    # 検証
    # タイルと中の項目は残る
    assert page.inner_text("#tile-review .num") == "1"
    assert page.locator('#tile-review button[data-id="D-3"]').count() == 1
    assert page.locator('#tile-running button[data-id="T-1"]').count() == 1
    assert page.locator("#tile-goal .checklist li").count() == 1
    # その種類の画面へ移るリンクだけが無い
    for tile_id in ("tile-next", "tile-review", "tile-hold", "tile-running"):
        assert page.locator(f"#{tile_id} .t-link").count() == 0
    assert page.locator("#tile-progress button").count() == 0
    # 進捗の数と棒は残る
    assert page.eval_on_selector_all(
        "#tile-progress td.tot", "cells => cells.map(c => c.textContent)"
    ) == ["1/2", "0/3"]
    assert page.locator("#tile-progress .cell").count() > 0
    # タブの帯にもその種類が無い
    assert page.locator('nav.tabbar a[data-tab="decisions"]').count() == 0


def test_visible_kinds_keep_links(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    sample_items: list[dict[str, Any]],
    sample_settings: dict[str, Any],
    sample_bodies: dict[str, str],
) -> None:
    """表示する種類の既定が全ての種類のときは、「すべて表示」と進捗のセルのリンクを出す（正常系）。"""
    # 準備
    settings = {**sample_settings, "display": {"network_look": "deep"}}
    url = write_preview(*sample_items, settings=settings, bodies=sample_bodies)
    # 実行
    page = open_preview(url)
    # 検証
    assert page.locator("#tile-review .t-link").count() == 1
    assert page.locator("#tile-progress button.cell").count() > 0


def test_region(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ページ全体はスクロールせず、タイルは領域の中で縦にスクロールし、帯は見えたまま（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    page.set_viewport_size({"width": 1280, "height": 520})
    page.wait_for_selector("#tile-next")
    # 実行
    metrics = region_metrics(page)
    # 検証
    assert_page_does_not_scroll(page)
    assert metrics["content"]["scrollHeight"] > metrics["content"]["clientHeight"]
    assert_bands_stay(page)


# 次に検討する項目のタイルの見出しと「すべて表示」が、それぞれ何行に折り返しているかと、「すべて表示」が見出しの下の行にあるかを読む
HEAD_ROWS_JS = """() => {
    // 行の数は、文字の枠の縦の中心が半分の高さより離れるたびに 1 行と数える（印のアイコンと文字は高さが違うので、上端では数えない）
    const rows = (element) => {
        const range = document.createRange();
        range.selectNodeContents(element);
        const rects = [...range.getClientRects()].sort((a, b) => a.top + a.height / 2 - (b.top + b.height / 2));
        return rects.reduce((count, rect, index) => {
            const previous = rects[index - 1];
            const apart = previous === undefined || rect.top + rect.height / 2 - (previous.top + previous.height / 2) > rect.height / 2;
            return apart ? count + 1 : count;
        }, 0);
    };
    const heading = document.querySelector('#tile-next .t-head h2');
    const link = document.querySelector('#tile-next .t-head .t-link');
    return {
        headingRows: rows(heading),
        linkRows: rows(link),
        linkBelow: link.getBoundingClientRect().top >= heading.getBoundingClientRect().bottom - 1,
    };
}"""


@pytest.mark.parametrize(
    ("width", "link_below"),
    [
        pytest.param(320, True, id="narrowest"),
        pytest.param(389, False, id="narrow_edge"),
        pytest.param(390, False, id="wide_edge"),
    ],
)
def test_next_tile_head_when_narrow(
    write_sample_preview: WriteSamplePreview,
    open_preview: OpenPreview,
    width: int,
    link_below: bool,
) -> None:
    """幅 389px 以下でも見出しと「すべて表示」はそれぞれ 1 行で、収まらない幅 320px では「すべて表示」が見出しの下の行に回る。収まる幅では見出しと同じ行に並ぶ（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    # 実行
    page.set_viewport_size({"width": width, "height": 568})
    page.wait_for_selector("#tile-next .t-link")
    result = page.evaluate(HEAD_ROWS_JS)
    # 検証
    assert result == {"headingRows": 1, "linkRows": 1, "linkBelow": link_below}


def test_fit_smallest(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """概要は、幅 320px でページが横にスクロールせず、表のほかに横にあふれる区画が無く、「すべて表示」が表示幅の中にある（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=overview")
    # 実行
    set_smallest(page)
    # 検証
    assert_fits_smallest(page, ("#tile-next .t-link",))


# ===== 編集（トップバーの保存待ち） =====


def test_topbar_pending(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """トップバーに保存待ちのボタンを出し、溜めた件数・開いているか・書き込めない編集の有無を見せる（正常系）。"""
    # 準備
    url, _ = write_edit_preview(*edit_items(make_item, "D"), edits=edit_edits(make_edit, "D"))
    # 実行
    page = open_preview(url)
    page.wait_for_selector(PENDING_BUTTON)
    # 検証
    assert_topbar_pending(page)


def test_topbar_pending_hidden_when_nothing(
    write_edit_preview: WriteReviewPreview, make_item: MakeItem, open_preview: OpenPreview
) -> None:
    """保存待ちの編集が 0 件のときは、保存待ちのボタンを出さない（正常系）。"""
    # 準備
    url, _ = write_edit_preview(make_item("D-1"))
    # 実行
    page = open_preview(url)
    page.wait_for_selector("#tile-next")
    # 検証
    assert page.locator(PENDING_BUTTON).count() == 0


def test_topbar_pending_hidden_when_exported(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    tmp_path: Path,
) -> None:
    """配る書き出しでは、保存待ちのボタンを出さない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    out = tmp_path / "配る.html"
    result = call_tool("export", workspace=str(root), out=str(out))
    assert result.is_error is False, result.text
    # 実行
    page = open_preview(out.as_uri())
    page.wait_for_selector("#tile-next")
    # 検証
    assert page.locator(PENDING_BUTTON).count() == 0
