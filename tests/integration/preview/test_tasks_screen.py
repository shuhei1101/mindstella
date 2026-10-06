"""画面設計『タスク』（ボード・表）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page
from preview_drawer_helpers import (
    DRAWER,
    FILTER_BUTTON,
    badge_text,
    checked_values,
    chip_texts,
    clear_all_chips,
    click_value,
    close_drawer,
    drawer_groups,
    drawer_head,
    open_drawer,
    remove_chip,
)
from preview_fixture_types import (
    ID_BUTTON_MIN_SIZE_PX,
    ID_BUTTON_SIZE_JS,
    OpenPreview,
    WriteReviewPreview,
    WriteSamplePreview,
)
from preview_history_helpers import assert_topbar_history, preselect_diff
from preview_style_checks import (
    BOARD_COLUMN_WIDTH_PX,
    BOARD_EDGE_GAP_PX,
    DESKTOP_VIEWPORT,
    PHONE_VIEWPORT,
    TRANSPARENT,
    board_edges,
    board_layout,
    pin_id_column,
    table_cell_backgrounds,
)


def test_board(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """状態ごとの列にカードを並べ、進める検討事項を出し、押すと詳細を開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=tasks")
    # 実行
    columns = page.eval_on_selector_all(
        ".board section.board-col",
        "cols => cols.map(c => [c.getAttribute('aria-label'), [...c.querySelectorAll('.card')].map(k => k.dataset.id)])",
    )
    running_for = page.inner_text('.board button.card[data-id="T-1"] .c-for')
    page.click('.board button.card[data-id="T-1"]')
    # 検証
    assert columns == [
        ["未着手", ["T-2"]],
        ["進行中", ["T-1"]],
        ["保留", []],
        ["完了", ["T-3"]],
        ["中止", []],
    ]
    assert "D-2の題" in running_for
    # 0 件の列には、種類の名前で空の旨を出す
    assert (
        page.inner_text('.board section.board-col[aria-label="保留"] .empty')
        == "タスクはありません。"
    )
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "T-1の題"


def test_view_switch(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """表示形式の切り替えは ボード・表 の 2 つで、既定はボード。表に切り替えると行を並べる（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=tasks")
    views = page.eval_on_selector_all(
        ".segment button", "b => b.map(x => [x.dataset.view, x.getAttribute('aria-pressed')])"
    )
    # 実行
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector("table.grid")
    # 検証
    assert views == [["board", "true"], ["table", "false"]]
    rows = page.eval_on_selector_all("table.grid tbody tr", "rows => rows.map(r => r.dataset.id)")
    assert rows == ["T-1", "T-2", "T-3"]
    assert page.inner_text("main h1") == "タスク"


def test_table(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """表の「進める検討事項」の列から、その検討事項の詳細を開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=tasks&view=table")
    # 実行
    page.click('table.grid tr[data-id="T-1"] button.idlink')
    # 検証
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-2の題"


def test_board_edge_gap(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """タスクのボードは、カードの左端をボードの左端から余白を空けて置き、ツールバーの左端に揃える（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=tasks")
    # 実行
    edges = board_edges(page)
    # 検証
    assert edges["cardLeft"] - edges["boardLeft"] >= BOARD_EDGE_GAP_PX
    assert edges["cardLeft"] == pytest.approx(edges["toolbarLeft"], abs=1)


def test_board_columns_when_narrow(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """タスクのボードは、幅 390px で列を縦に 1 列に積み、列の右端を画面の幅に収め、背景をつかめることを示さない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=tasks&view=board")
    page.set_viewport_size(PHONE_VIEWPORT)
    # 実行
    layout = board_layout(page)
    # 検証
    assert layout["columnCount"] > 1
    assert layout["leftSpread"] == pytest.approx(0, abs=1)
    assert layout["rightmost"] <= layout["viewportWidth"]
    assert not layout["pageScrolls"]
    assert layout["cursor"] != "grab"


def test_board_columns_when_wide(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """タスクのボードは、幅 1280px で 290px の列を横に並べ、背景をつかめることを示す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=tasks&view=board")
    page.set_viewport_size(DESKTOP_VIEWPORT)
    # 実行
    layout = board_layout(page)
    # 検証
    assert layout["columnCount"] > 1
    assert layout["topSpread"] == pytest.approx(0, abs=1)
    assert layout["narrowest"] == pytest.approx(BOARD_COLUMN_WIDTH_PX, abs=1)
    assert layout["widest"] == pytest.approx(BOARD_COLUMN_WIDTH_PX, abs=1)
    assert layout["cursor"] == "grab"


def test_table_cell_surface(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """タスクの表のセルは静止時に面の色を持たず、面の色は表の枠と固定した列が持つ（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=tasks&view=table")
    pin_id_column(page)
    # 実行
    backgrounds = table_cell_backgrounds(page)
    # 検証
    assert backgrounds["wrap"] != TRANSPARENT
    assert backgrounds["plain"] == [TRANSPARENT]
    assert len(backgrounds["pinned"]) > 0
    assert TRANSPARENT not in backgrounds["pinned"]


def test_table_id_button_size(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """表の「進める検討事項」の列の ID のボタンは、見えている枠が縦横 24px 以上である（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=tasks&view=table")
    # 実行
    sizes = page.eval_on_selector_all("table.grid td button.idlink", ID_BUTTON_SIZE_JS)
    # 検証
    assert sizes["count"] > 0
    assert sizes["smallest"] >= ID_BUTTON_MIN_SIZE_PX


def test_diff_marks_when_board(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """ボードのカードのタイトルの横に、文言なしの印を置く。トップバーに札を出す（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    preselect_diff(page, "since")
    open_preview(url, "#tab=tasks")
    page.wait_for_selector(".board button.card")
    # 検証
    mark = page.locator('.board button.card[data-id="T-1"] .df-mark')
    assert mark.get_attribute("class") == "df-mark df-chg"
    assert mark.get_attribute("title") == "変更"
    assert page.locator(".board .df-badge").count() == 0
    assert_topbar_history(page)


def test_diff_marks_when_table(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """表の行のタイトルの右に印を置き、印の無い行は変えない（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    preselect_diff(page, "V-1")
    open_preview(url, "#tab=tasks&view=table")
    page.wait_for_selector("table.grid tbody tr")
    # 検証
    assert page.locator('table.grid tbody tr[data-id="T-1"] .row-open + .df-mark.df-new').count() == 1
    # 印の無い時点では付かない
    page.evaluate("localStorage.setItem('mindmap-preview', JSON.stringify({diffSel: null}))")
    page.reload()
    page.wait_for_selector("table.grid tbody tr")
    assert page.locator("table.grid .df-mark").count() == 0


def _board_columns(page: Page) -> list[list[object]]:
    """ボードの列を、状態・カードの ID の並び・0 件の列に出した文で返す。"""
    return page.eval_on_selector_all(
        ".board section.board-col",
        """cols => cols.map(c => [
            c.getAttribute('aria-label'),
            [...c.querySelectorAll('.card')].map(k => k.dataset.id),
            c.querySelector('.empty')?.textContent ?? null,
        ])""",
    )


def test_drawer(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ドロワーは、種類・状態を並べ（記録に値の無い条件は並べない）、何も選んでいない状態で開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=tasks")
    # 実行
    open_drawer(page)
    groups = {group["label"]: group for group in drawer_groups(page)}
    # 検証
    assert list(groups) == ["種類", "状態"]
    assert groups["種類"]["values"] == [["作業", 3, False]]
    assert groups["状態"]["values"] == [["未着手", 1, False], ["進行中", 1, False], ["完了", 1, False]]
    assert badge_text(page) is None
    assert drawer_head(page) == {"count": "3 件", "foot": ["3 件を表示"]}
    assert page.is_visible(FILTER_BUTTON)


def test_board_filter(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ボードはドロワーの条件に合うタスクだけを並べ、状態の条件から外した列は列を残して外した旨を出す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=tasks&view=board")
    open_drawer(page)
    # 実行
    click_value(page, "status", "進行中")
    page.wait_for_function("document.querySelectorAll('.board .card').length === 1")
    # 検証
    assert _board_columns(page) == [
        ["未着手", [], "状態の条件で外しています。"],
        ["進行中", ["T-1"], None],
        ["保留", [], "状態の条件で外しています。"],
        ["完了", [], "状態の条件で外しています。"],
        ["中止", [], "状態の条件で外しています。"],
    ]
    assert badge_text(page) == "1"
    assert chip_texts(page) == ["状態: 進行中"]


def test_board_filter_when_nothing_selected(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """状態を選んでいない間は、0 件の列に「タスクはありません。」を出す（正常系）。"""
    # 準備・実行
    url = write_sample_preview()
    page = open_preview(url, "#tab=tasks&view=board")
    # 検証
    assert [column[2] for column in _board_columns(page)] == [
        None,
        None,
        "タスクはありません。",
        None,
        "タスクはありません。",
    ]


def test_table_filter(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """表もドロワーの条件に合うタスクだけを並べ、表の上のチップで解除できる。ボードと条件を共有する（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=tasks&view=board")
    open_drawer(page)
    click_value(page, "status", "完了")
    page.wait_for_function("document.querySelectorAll('.board .card').length === 1")
    page.click(f"{DRAWER} .fd-foot .btn.primary")
    page.wait_for_selector(DRAWER, state="detached")
    # 実行（表へ切り替える）
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector("table.grid")
    rows = page.eval_on_selector_all(
        "table.grid tbody tr[data-id]", "rows => rows.map(r => r.dataset.id)"
    )
    chips = page.eval_on_selector_all(".table-block .chip", "chips => chips.map(c => c.textContent)")
    page.click(".table-block .chip button[aria-label='状態: 完了 の条件を解除']")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr[data-id]').length === 3")
    # 検証
    assert rows == ["T-3"]
    assert chips == ["状態: 完了"]
    assert badge_text(page) is None
    open_drawer(page)
    assert checked_values(page, "status") == []


def test_board_chips(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ボードのツールバーの下に条件のチップの行を置き、× で 1 つ解除し、「すべて解除」で全ての条件を外す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=tasks&view=board")
    open_drawer(page)
    click_value(page, "status", "進行中")
    click_value(page, "status", "完了")
    close_drawer(page)
    # 実行
    chips = chip_texts(page)
    below_toolbar = page.evaluate(
        "document.querySelector('.screen.tasks .toolbar').nextElementSibling.classList.contains('chips')"
    )
    remove_chip(page, "状態: 完了")
    page.wait_for_function("document.querySelectorAll('.chips .chip').length === 1")
    after_remove = (chip_texts(page), badge_text(page), page.locator(".board .card").count())
    clear_all_chips(page)
    page.wait_for_function("document.querySelectorAll('.chips .chip').length === 0")
    # 検証
    assert chips == ["状態: 進行中", "状態: 完了"]
    assert below_toolbar is True
    assert after_remove == (["状態: 進行中"], "1", 1)
    assert badge_text(page) is None
    assert page.locator(".board .card").count() == 3
