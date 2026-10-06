"""画面設計『資料』（カード・ボード・表）の結合テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page
from preview_fixture_types import OpenPreview, WritePreview, WriteReviewPreview, WriteSamplePreview
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
    open_drawer,
    remove_chip,
)
from preview_history_helpers import assert_topbar_history, preselect_diff
from preview_mark_helpers import SCREEN_MARKS, marks_of
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
from workspace_fixtures import MakeItem


def _card_ids(page) -> list[str]:
    """資料のカードの ID を並びのまま返す。"""
    return page.eval_on_selector_all(".doc-card", "cards => cards.map(c => c.dataset.id)")


def test_cards(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """納品物を先頭に印付きで並べ、資料の状態を出し、押すと詳細を開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=docs")
    # 実行
    ids = _card_ids(page)
    badge_cards = page.eval_on_selector_all(
        ".doc-card:has(.deliv-badge)", "cards => cards.map(c => c.dataset.id)"
    )
    statuses = page.eval_on_selector_all(".doc-card .st", "marks => marks.map(m => m.dataset.st)")
    page.click('.doc-card[data-id="A-2"]')
    # 検証
    assert ids == ["A-1", "A-2"]
    assert badge_cards == ["A-1"]
    assert statuses == ["完成", "下書き"]
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "A-2の題"


def test_view_switch(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """表示形式の切り替えは カード・ボード・表 の 3 つで、既定はカード。表に切り替えると行を並べる（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=docs")
    views = page.eval_on_selector_all(
        ".segment button", "b => b.map(x => [x.dataset.view, x.getAttribute('aria-pressed')])"
    )
    # 実行
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector("table.grid")
    # 検証
    assert views == [["cards", "true"], ["board", "false"], ["table", "false"]]
    rows = page.eval_on_selector_all("table.grid tbody tr", "rows => rows.map(r => r.dataset.id)")
    assert rows == ["A-1", "A-2"]
    assert page.inner_text("main h1") == "資料"


def test_card_filter(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ドロワーで値を選ぶとカードが絞られてバッジとチップが付き、条件の「解除」で戻る。ツールバーに絞り込みのボタンを出さない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=docs")
    toolbar_buttons = page.locator('.toolbar [aria-label="絞り込み"]').count()
    # 実行
    open_drawer(page)
    click_value(page, "deliverable", "納品物以外")
    page.wait_for_function("document.querySelectorAll('.doc-card').length === 1")
    selected = (_card_ids(page), badge_text(page), chip_texts(page))
    page.click(f"{DRAWER} button[aria-label='納品物の条件を解除']")
    page.wait_for_function("document.querySelectorAll('.doc-card').length === 2")
    # 検証
    assert toolbar_buttons == 0
    assert selected == (["A-2"], "1", ["納品物: 納品物以外"])
    assert _card_ids(page) == ["A-1", "A-2"]
    assert page.locator(".chips .chip").count() == 0
    assert page.locator(".pop").count() == 0


def test_card_filter_clear_all(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """条件が 2 つあるとき、ドロワーの「すべて解除」で全ての条件を解除し、バッジを外す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=docs&f.deliverable=納品物&f.status=完成")
    assert _card_ids(page) == ["A-1"]
    assert badge_text(page) == "2"
    # 実行
    open_drawer(page)
    page.click(f"{DRAWER} .fd-foot button:has-text('すべて解除')")
    # 検証
    page.wait_for_function("document.querySelectorAll('.doc-card').length === 2")
    assert badge_text(page) is None


def test_drawer(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ドロワーは、種類・状態・納品物（納品物 → 納品物以外の順）を並べ、何も選んでいない状態で開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=docs")
    # 実行
    open_drawer(page)
    groups = {group["label"]: group for group in drawer_groups(page)}
    # 検証
    assert list(groups) == ["種類", "状態", "納品物"]
    assert groups["状態"]["values"] == [["下書き", 1, False], ["完成", 1, False]]
    assert groups["納品物"]["values"] == [["納品物", 1, False], ["納品物以外", 1, False]]
    assert badge_text(page) is None
    assert page.is_visible(FILTER_BUTTON)


def _board_columns(page) -> list[list[Any]]:
    """ボードの列を、状態・件数・カードの ID の並びで返す。"""
    return page.eval_on_selector_all(
        ".board section.board-col",
        """cols => cols.map(c => [
            c.getAttribute('aria-label'),
            c.querySelector('h3 .n').textContent,
            [...c.querySelectorAll('.card')].map(k => k.dataset.id),
        ])""",
    )


def test_view_switch_to_board(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ボードに切り替えると状態の列を並べ、押されている形式がボードになる（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=docs")
    # 実行
    page.click('.segment button[data-view="board"]')
    page.wait_for_selector(".board")
    # 検証
    pressed = page.eval_on_selector_all(
        ".segment button", "b => b.map(x => [x.dataset.view, x.getAttribute('aria-pressed')])"
    )
    assert pressed == [["cards", "false"], ["board", "true"], ["table", "false"]]
    assert page.locator(".doc-grid").count() == 0


def test_board(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """下書き・確認中・完成の 3 列に資料を並べ、0 件の列も出し、カードに状態の印を出さない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=docs&view=board")
    # 実行
    columns = _board_columns(page)
    marks = page.locator(".board .doc-card .st").count()
    badge_cards = page.eval_on_selector_all(
        ".board .doc-card:has(.deliv-badge)", "cards => cards.map(c => c.dataset.id)"
    )
    # 検証
    assert columns == [["下書き", "1", ["A-2"]], ["確認中", "0", []], ["完成", "1", ["A-1"]]]
    assert (
        page.locator(".board section.board-col").nth(1).inner_text().endswith("資料はありません。")
    )
    assert marks == 0
    assert badge_cards == ["A-1"]


def test_board_order(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    sample_settings: dict[str, Any],
) -> None:
    """列の中は納品物を先頭に連番の順に並べる（正常系）。"""
    # 準備
    url = write_preview(
        make_item("A-1", deliverable=False, status="完成", kind="文書"),
        make_item("A-2", deliverable=False, status="完成", kind="文書"),
        make_item("A-3", deliverable=True, status="完成", kind="文書"),
        make_item("A-4", deliverable=True, status="下書き", kind="文書"),
        make_item("A-5", deliverable=False, status="下書き", kind="文書"),
        settings=sample_settings,
    )
    page = open_preview(url, "#tab=docs&view=board")
    # 実行
    columns = _board_columns(page)
    # 検証
    assert columns == [
        ["下書き", "2", ["A-4", "A-5"]],
        ["確認中", "0", []],
        ["完成", "3", ["A-3", "A-1", "A-2"]],
    ]


def test_board_open_detail(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """カードを押すと詳細を開き、開いているカードに selected が付く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=docs&view=board")
    # 実行
    page.click('.board .doc-card[data-id="A-2"]')
    # 検証
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "A-2の題"
    selected = page.eval_on_selector_all(
        ".board .doc-card.selected", "cards => cards.map(c => c.dataset.id)"
    )
    assert selected == ["A-2"]


def test_board_filter(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ボードでもドロワーで値を選ぶと列のカードが絞られてチップが付き、条件の「解除」で戻る（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=docs&view=board")
    # 実行
    open_drawer(page)
    click_value(page, "deliverable", "納品物以外")
    page.wait_for_function("document.querySelectorAll('.board .doc-card').length === 1")
    # 検証
    assert _board_columns(page) == [
        ["下書き", "1", ["A-2"]],
        ["確認中", "0", []],
        ["完成", "0", []],
    ]
    assert chip_texts(page) == ["納品物: 納品物以外"]
    # 条件の「解除」で全ての列のカードが戻る
    page.click(f"{DRAWER} button[aria-label='納品物の条件を解除']")
    page.wait_for_function("document.querySelectorAll('.board .doc-card').length === 2")
    assert _board_columns(page) == [
        ["下書き", "1", ["A-2"]],
        ["確認中", "0", []],
        ["完成", "1", ["A-1"]],
    ]


def test_board_filter_from_url(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """URL の条件でボードを開くと、カードと同じ条件で絞られ、状態の条件から外した列は列を残して外した旨を出す（正常系）。"""
    # 準備・実行
    url = write_sample_preview()
    page = open_preview(url, "#tab=docs&view=board&f.status=完成")
    excluded = [
        page.inner_text(f'.board section.board-col[aria-label="{status}"] .empty')
        for status in ("下書き", "確認中")
    ]
    open_drawer(page)
    # 検証
    assert _board_columns(page) == [
        ["下書き", "0", []],
        ["確認中", "0", []],
        ["完成", "1", ["A-1"]],
    ]
    assert excluded == ["状態の条件で外しています。", "状態の条件で外しています。"]
    assert badge_text(page) == "1"
    assert checked_values(page, "status") == ["完成"]


def test_board_edge_gap(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """資料のボードは、カードの左端をボードの左端から余白を空けて置き、ツールバーの左端に揃える（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=docs&view=board")
    # 実行
    edges = board_edges(page)
    # 検証
    assert edges["cardLeft"] - edges["boardLeft"] >= BOARD_EDGE_GAP_PX
    assert edges["cardLeft"] == pytest.approx(edges["toolbarLeft"], abs=1)


def test_board_columns_when_narrow(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """資料のボードは、幅 390px で列を縦に 1 列に積み、列の右端を画面の幅に収め、背景をつかめることを示さない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=docs&view=board")
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
    """資料のボードは、幅 1280px で 290px の列を横に並べ、背景をつかめることを示す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=docs&view=board")
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
    """資料の表のセルは静止時に面の色を持たず、面の色は表の枠と固定した列が持つ（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=docs&view=table")
    pin_id_column(page)
    # 実行
    backgrounds = table_cell_backgrounds(page)
    # 検証
    assert backgrounds["wrap"] != TRANSPARENT
    assert backgrounds["plain"] == [TRANSPARENT]
    assert len(backgrounds["pinned"]) > 0
    assert TRANSPARENT not in backgrounds["pinned"]


def test_diff_marks_when_cards_and_board(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """資料のカードとボードのカードのタイトルの横に、文言なしの印を置く。トップバーに札を出す（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=docs&view=cards")
    page.wait_for_selector(".doc-card")
    # 検証（カード）
    mark = page.locator('.doc-card[data-id="A-1"] .df-mark')
    assert mark.get_attribute("class") == "df-mark df-chg"
    assert mark.inner_text() == "変更"
    assert page.locator(".doc-card .df-badge").count() == 0
    assert_topbar_history(page)
    # 検証（ボード）
    page.click('.segment button[data-view="board"]')
    page.wait_for_selector(".board .doc-card")
    assert page.locator('.board .doc-card[data-id="A-1"] .df-mark.df-chg').count() == 1


def test_diff_marks_when_table(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """表の行のタイトルの右に印を置く（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=docs&view=table")
    page.wait_for_selector("table.grid tbody tr")
    # 検証
    assert page.locator('table.grid tbody tr[data-id="A-1"] .row-open + .df-mark.df-chg').count() == 1


@pytest.mark.parametrize("view", ["cards", "board"])
def test_chips(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, view: str
) -> None:
    """カード・ボードのツールバーの下に条件のチップの行を置き、× で 1 つ解除し、「すべて解除」で全ての条件を外す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, f"#tab=docs&view={view}")
    open_drawer(page)
    click_value(page, "deliverable", "納品物以外")
    click_value(page, "status", "下書き")
    close_drawer(page)
    # 実行
    chips = chip_texts(page)
    below_toolbar = page.evaluate(
        "document.querySelector('.screen.docs .toolbar').nextElementSibling.classList.contains('chips')"
    )
    remove_chip(page, "納品物: 納品物以外")
    page.wait_for_function("document.querySelectorAll('.chips .chip').length === 1")
    after_remove = (chip_texts(page), badge_text(page), len(_card_ids(page)))
    clear_all_chips(page)
    page.wait_for_function("document.querySelectorAll('.chips .chip').length === 0")
    page.wait_for_function("document.querySelectorAll('.doc-card').length === 2")
    # 検証
    assert chips == ["納品物: 納品物以外", "状態: 下書き"]
    assert below_toolbar is True
    assert after_remove == (["状態: 下書き"], "1", 1)
    assert badge_text(page) is None
    # チップを外すとドロワーの選びも外れる
    open_drawer(page)
    assert checked_values(page, "deliverable") == []
    assert checked_values(page, "status") == []


@pytest.mark.parametrize(
    "view",
    [
        pytest.param("cards", id="cards"),
        pytest.param("board", id="board"),
    ],
)
def test_comment_marks_when_cards(
    write_commented_preview: WriteReviewPreview, open_preview: OpenPreview, view: str
) -> None:
    """資料のカードとボードのカードのメタ情報の右端に、コメントの件数の印を出す。件数 0 の資料には出さない（正常系）。"""
    # 準備・実行
    url, _ = write_commented_preview()
    page = open_preview(url, f"#tab=docs&view={view}")
    page.wait_for_selector("button.card")
    # 検証
    assert marks_of(page) == SCREEN_MARKS["docs"]
    assert page.locator("button.card .c-meta .cmk").count() == 2
    assert page.inner_text('button.card[data-id="A-1"] .cmk .sr-only') == "コメント 1 件"


def test_comment_marks_when_table(
    write_commented_preview: WriteReviewPreview, open_preview: OpenPreview
) -> None:
    """表の行のタイトルの右に印を出す（正常系）。"""
    # 準備・実行
    url, _ = write_commented_preview()
    page = open_preview(url, "#tab=docs&view=table")
    page.wait_for_selector("table.grid tbody tr")
    # 検証
    assert marks_of(page) == SCREEN_MARKS["docs"]
    assert page.locator("table.grid tbody tr:has(.row-open ~ .cmk-place .cmk)").count() == 2
