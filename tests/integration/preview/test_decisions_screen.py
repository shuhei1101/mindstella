"""画面設計『検討事項』（ボード・表）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from playwright.sync_api import Page, Route, expect
from preview_edit_helpers import (
    ADD_BUTTON,
    ADD_PANEL,
    ADD_TITLE_INPUT,
    ADDED_ITEM,
    PENDING_BUTTON,
    SETTLE_MS,
    assert_topbar_pending,
    block_by_saving,
    edit_edits,
    edit_items,
    item_marks,
    read_edits_file,
    start_add,
    wait_edits_match,
)
from preview_fit_helpers import assert_fits_smallest, set_smallest
from preview_scrim_helpers import SCRIM_ON, click_scrim, main_inert, scrim_visible
from preview_fixture_types import (
    ID_BUTTON_MIN_SIZE_PX,
    ID_BUTTON_SIZE_JS,
    OpenPreview,
    WritePreview,
    WriteReviewPreview,
    WriteSamplePreview,
)
from preview_drawer_helpers import (
    ALL_DECISION_STATUSES_HASH,
    DEFAULT_DECISION_STATUSES,
    DRAWER,
    DRAWER_OPEN,
    FILTER_BUTTON,
    badge_text,
    checked_values,
    chip_texts,
    clear_all_chips,
    click_value,
    close_drawer,
    drawer_groups,
    drawer_head,
    drawer_text_fields,
    open_drawer,
    remove_chip,
    value_selector,
)
from preview_history_helpers import assert_topbar_history, preselect_diff
from preview_layout_helpers import (
    BOUNDARY_HEIGHT,
    NARROW_VIEWPORT,
    TABLE_BOARD_BOUNDARY_WIDTHS,
    WIDE_VIEWPORT,
    assert_bands_stay,
    assert_page_does_not_scroll,
    assert_region_mode,
    region_metrics,
)
from preview_mark_helpers import SCREEN_MARKS, marks_of
from preview_removed_helpers import (
    BAND,
    REMOVED_IN_V2_BY_TAB,
    assert_band_above,
    assert_removed_band,
)
from preview_saved_filter_helpers import (
    read_saved_filters,
    reload_preview,
    reopen_preview,
    seed_saved_filters,
)
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
from preview_stack_helpers import DETAIL_HASH, has_left_front, is_inert, open_narrow, wait_front
from workspace_fixtures import CallTool, MakeEdit, MakeItem, MakeWorkspace, WriteEdits


# 狭い幅の画面の高さ
NARROW_HEIGHT = 700

MAP_NODE_HEIGHT = 48

# 状態の順（ボードの列の並び）
DECISION_STATUSES = ["要見直し", "未決定", "保留", "未整理", "決定済み", "対象外", "取り下げ"]

# サンプルの記録が持つ状態（ドロワーの状態の値の並びの順）
SAMPLE_STATUSES = ["要見直し", "未決定", "保留", "決定済み"]

# 絞り込みの条件に合う検討事項が無いときに出す文
NO_MATCH_TEXT = "表示する検討事項はありません。"

# 状態の条件から外した状態の列に出す文と、0 件の列に出す文
EXCLUDED_COLUMN_TEXT = "状態の条件で外しています。"
EMPTY_COLUMN_TEXT = "検討事項はありません。"

# 幅 900px 以下の画面の大きさ（絞り込みのドロワーが画面の幅いっぱいに出る）
DRAWER_NARROW_VIEWPORT = {"width": 390, "height": 844}


# 余白を押してから、描き直しなどで変わるものが落ち着くまで待つ時間（ms。変わらないことを確かめる前に置く）
PRESS_SETTLE_MS = 400

# 押したとみなす移動の上限（`PRESS_SLOP_PX`）と、それを超える移動（px）
PRESS_SLOP_PX = 5
DRAG_OVER_SLOP_PX = PRESS_SLOP_PX + 1

BLANK_SCAN_STEP_PX = 20

# 拡大・縮小で倍率を決めるための「拡大」を押す回数（上限の倍率になる）と、スクロールさせる位置（px）
ZOOM_IN_CLICKS = 6
SCROLL_LEFT_PX = 150
SCROLL_TOP_PX = 40


WHEEL_OUT_DELTA = 100
WHEEL_ZOOM_MAX = 1.5
WHEEL_ZOOM_MIN = 0.4
WHEEL_FACTOR = 1.12
WHEEL_MAX_TURNS = 30

# 回す前にマウスの下にあった節の中心が、回した後に動いてよい距離（px。スクロールの位置の丸めの分）
WHEEL_POINT_TOLERANCE_PX = 2

# 余白の大きさが、土台の幅（整数に丸められる）から求めた値と違ってよい距離（px）
MARGIN_TOLERANCE_PX = 1

# 回した後、倍率と余白が当たるまで待つ時間（ms）
WHEEL_SETTLE_MS = 200


SHAKE_EARLY_MS = 120

# 素早い 2 回押しにする、続けて押す間隔（ms。450ms 未満）
QUICK_PRESS_GAP_MS = 80


def _view_pressed(page: Page, view: str) -> str | None:
    """表示形式の切り替えで、その形式のボタンが押されているかを返す。"""
    return page.get_attribute(f'.segment button[data-view="{view}"]', "aria-pressed")


def test_view_switch(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """表示形式の切り替えは、view の無いハッシュでボードが押された状態で開き、ボード・表の順に並び、行き来するとハッシュの view を置き換える（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions")
    history_length = page.evaluate("history.length")
    assert _view_pressed(page, "board") == "true"
    assert page.eval_on_selector_all(
        ".segment button", "buttons => buttons.map(b => b.dataset.view)"
    ) == ["board", "table"]
    # 実行・検証
    for view in ("table", "board"):
        page.click(f'.segment button[data-view="{view}"]')
        page.wait_for_function(
            f"document.querySelector('.segment button[data-view=\"{view}\"]').getAttribute('aria-pressed') === 'true'"
        )
        assert _view_pressed(page, view) == "true"
    # 表示形式の切り替えは履歴に積まない
    assert page.evaluate("history.length") == history_length
    # 画面の名前が h1
    assert page.inner_text("main h1") == "検討事項"


def test_board_heading_level(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ボードの列の見出しは、画面の見出し h1 の 1 段下の h2 で、h3 の列の見出しは残らない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions")
    # 実行
    heading_tags = page.eval_on_selector_all(
        "main h1, main .board-col h2",
        "heads => heads.map(h => [h.tagName, h.closest('.board-col')?.getAttribute('aria-label') ?? null])",
    )
    labels = page.eval_on_selector_all(
        ".board section.board-col", "cols => cols.map(c => c.getAttribute('aria-label'))"
    )
    h3_count = page.eval_on_selector_all("main .board-col h3", "heads => heads.length")
    # 検証
    assert page.inner_text("main h1") == "検討事項"
    assert heading_tags == [["H1", None]] + [["H2", label] for label in labels]
    assert h3_count == 0


def _press_at(page: Page, point: dict[str, float]) -> None:
    """動かさずに左ボタンを押して離す。"""
    page.mouse.move(point["x"], point["y"])
    page.mouse.down()
    page.mouse.up()


def _box_center(page: Page, selector: str) -> dict[str, float]:
    """要素の中心の画面上の座標を返す。"""
    box = page.locator(selector).first.bounding_box()
    assert box is not None
    return {"x": box["x"] + box["width"] / 2, "y": box["y"] + box["height"] / 2}


def test_board(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ドロワーの条件に合う検討事項を状態ごとの列に並べ、条件から外した状態の列も残し、カードを押すと詳細を開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=board")
    # 実行
    columns = page.eval_on_selector_all(
        ".board section.board-col",
        "cols => cols.map(c => [c.getAttribute('aria-label'), [...c.querySelectorAll('.card')].map(k => k.dataset.id)])",
    )
    page.click('.board button.card[data-id="D-5"]')
    # 検証
    assert columns == [
        ["要見直し", ["D-3"]],
        ["未決定", ["D-2", "D-5"]],
        ["保留", ["D-4"]],
        ["未整理", []],
        ["決定済み", []],
        ["対象外", []],
        ["取り下げ", []],
    ]
    # 状態の条件に含む 0 件の列には、種類の名前で空の旨を出し、条件から外した列には外した旨を出す
    assert (
        page.inner_text('.board section.board-col[aria-label="未整理"] .empty') == EMPTY_COLUMN_TEXT
    )
    for status in ("決定済み", "対象外", "取り下げ"):
        assert (
            page.inner_text(f'.board section.board-col[aria-label="{status}"] .empty')
            == EXCLUDED_COLUMN_TEXT
        )
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-5の題"


def test_table_ready_column_when_waiting(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """前提が決着していない未決定は、着手可否を「前提待ち」にする（正常系）。"""
    # 準備
    url = write_preview(
        make_item("D-1", status="未決定"),
        make_item("D-2", status="未決定", related=[{"to": "D-1", "type": "depends_on"}]),
    )
    page = open_preview(url, "#tab=decisions&view=table")
    # 実行
    ready = page.eval_on_selector_all(
        "table.grid tbody tr",
        "rows => rows.map(r => [r.dataset.id, r.querySelector('td[data-col=\"3\"]').textContent])",
    )
    # 検証
    assert ready == [["D-1", "着手可能"], ["D-2", "前提待ち"]]


def test_table_ready_column(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """表の「着手可否」は、build が埋め込んだ次の候補にある未決定を「着手可能」、未決定以外を「なし」にする（正常系）。"""
    # 準備（決定済みの D-1 も出すため、全ての状態を選んで開く）
    url = write_sample_preview()
    page = open_preview(url, f"#tab=decisions&view=table{ALL_DECISION_STATUSES_HASH}")
    # 実行
    ready = page.eval_on_selector_all(
        "table.grid tbody tr",
        "rows => rows.map(r => [r.dataset.id, r.querySelector('td[data-col=\"3\"]').textContent])",
    )
    # 検証
    assert ready == [
        ["D-1", "なし"],
        ["D-2", "着手可能"],
        ["D-3", "なし"],
        ["D-4", "なし"],
        ["D-5", "着手可能"],
    ]
    assert page.inner_text('table.grid thead th[data-col="3"]').strip().startswith("着手可否")
    # 行のタイトルを押すと詳細を開く
    page.click('table.grid button.row-open[data-id="D-4"]')
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-4の題"


def test_board_edge_gap(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """検討事項のボードは、カードの左端をボードの左端から余白を空けて置き、ツールバーの左端に揃える（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=board")
    # 実行
    edges = board_edges(page)
    # 検証
    assert edges["cardLeft"] - edges["boardLeft"] >= BOARD_EDGE_GAP_PX
    assert edges["cardLeft"] == pytest.approx(edges["toolbarLeft"], abs=1)


def test_board_columns_when_narrow(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """検討事項のボードは、幅 390px で列を縦に 1 列に積み、列の右端を画面の幅に収め、背景をつかめることを示さない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=board")
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
    """検討事項のボードは、幅 1280px で 290px の列を横に並べ、背景をつかめることを示す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=board")
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
    """検討事項の表のセルは静止時に面の色を持たず、面の色は表の枠と固定した列が持つ（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
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
    """表の「前提」の列の ID のボタンは、見えている枠が縦横 24px 以上である（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    # 実行
    sizes = page.eval_on_selector_all("table.grid td button.idlink", ID_BUTTON_SIZE_JS)
    # 検証
    assert sizes["count"] > 0
    assert sizes["smallest"] >= ID_BUTTON_MIN_SIZE_PX


def test_diff_marks_when_table(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """表の行のタイトルの右に印を置く。変えた行は ●、足した行は + で、トップバーに札を出し、タブに点を付ける（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    preselect_diff(page, "V-1")
    open_preview(url, f"#tab=decisions&view=table{ALL_DECISION_STATUSES_HASH}")
    page.wait_for_selector("table.grid tbody tr")
    # 検証
    new_rows = page.eval_on_selector_all(
        "table.grid tbody tr:has(.row-open + .df-mark.df-new)", "rows => rows.map(r => r.dataset.id)"
    )
    assert new_rows == ["D-1", "D-2"]
    assert page.locator("table.grid .df-mark.df-chg").count() == 0
    assert page.locator('nav.tabbar a[data-tab="decisions"] .df-dot').count() == 1
    assert_topbar_history(page)


def test_diff_marks_when_board(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """ボードのカードのタイトルの横に、文言なしの印を置く（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    preselect_diff(page, "V-2")
    open_preview(url, f"#tab=decisions&view=board{ALL_DECISION_STATUSES_HASH}")
    page.wait_for_selector(".board button.card")
    # 検証
    marked = page.eval_on_selector_all(
        ".board button.card:has(.df-mark.df-chg)", "cards => cards.map(c => c.dataset.id)"
    )
    assert sorted(marked) == ["D-1", "D-2"]
    assert page.locator(".board .df-badge").count() == 0


@pytest.mark.parametrize(
    ("view", "below"),
    [
        pytest.param("table", "table.grid", id="table"),
        pytest.param("board", ".board", id="board"),
    ],
)
def test_removed_band(
    write_removed_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    page: Page,
    view: str,
    below: str,
) -> None:
    """差分の表示の間、選んだ時点で消した検討事項を、表示形式によらず一覧の上の帯に ID の順で並べる。押せない（正常系）。"""
    # 準備・実行
    url, _ = write_removed_preview()
    preselect_diff(page, "V-2")
    open_preview(url, f"#tab=decisions&view={view}")
    page.wait_for_selector(below)
    # 検証
    assert_removed_band(page, REMOVED_IN_V2_BY_TAB["decisions"])
    assert_band_above(page, below)
    # 消した検討事項は、ボードのカード・表の行にしない
    assert page.locator('[data-id="D-3"], [data-id="D-4"]').count() == 0


def test_removed_band_when_filtered(
    write_removed_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """絞り込みの条件で一覧の行が 0 件になっても、削除した項目は絞り込まず全て帯に出す（正常系）。"""
    # 準備・実行
    url, _ = write_removed_preview()
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=decisions&view=table&f.status=対象外")
    page.wait_for_selector("table.grid")
    # 検証
    assert page.locator("table.grid tbody tr[data-id]").count() == 0
    assert_removed_band(page, REMOVED_IN_V2_BY_TAB["decisions"])


@pytest.mark.parametrize(
    "sel",
    [
        pytest.param(None, id="diff_off"),
        pytest.param("V-1", id="nothing_removed"),
        pytest.param("pending", id="removed_other_kind"),
    ],
)
def test_removed_band_when_nothing_to_show(
    write_removed_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    page: Page,
    sel: str | None,
) -> None:
    """差分を出していないとき、選んだ時点で検討事項を消していないとき（消したのがほかの種類だけのときも）は、帯を置かない（正常系）。"""
    # 準備・実行
    url, _ = write_removed_preview()
    preselect_diff(page, sel)
    open_preview(url, "#tab=decisions&view=table")
    page.wait_for_selector("table.grid")
    # 検証
    assert page.locator(BAND).count() == 0


def _table_row_ids(page: Page) -> list[str]:
    """表に並んでいる行の ID を並びのまま返す。"""
    return page.eval_on_selector_all(
        "table.grid tbody tr[data-id]", "rows => rows.map(r => r.dataset.id)"
    )


def test_filter_button(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """トップバーの絞り込みのボタンをコメントのボタンの左に置き、値を選んでいる条件の数をバッジに出し、押すとドロワーを開閉する（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions")
    # 実行
    order = page.eval_on_selector_all(
        "header.topbar > button", "buttons => buttons.map(b => b.dataset.act ?? null)"
    )
    closed = page.eval_on_selector(
        FILTER_BUTTON,
        "b => [b.getAttribute('aria-label'), b.getAttribute('aria-expanded'), b.getAttribute('aria-controls')]",
    )
    open_drawer(page)
    opened = page.eval_on_selector(
        FILTER_BUTTON,
        "b => [b.getAttribute('aria-expanded'), b.getAttribute('aria-controls'), b.classList.contains('open')]",
    )
    page.click(FILTER_BUTTON)
    page.wait_for_selector(DRAWER, state="detached")
    # 検証
    # 右端はライト / ダークのボタン（`data-act` を持たない）
    assert order[-3:] == ["filter", "comments", None]
    # 開いたときの条件（状態）の 1 つだけにバッジが付く
    assert badge_text(page) == "1"
    assert closed == ["絞り込み（1 つの条件で絞り込み中）", "false", None]
    assert opened == ["true", "drawer", True]
    assert page.get_attribute(FILTER_BUTTON, "aria-expanded") == "false"


def test_drawer_default(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ドロワーは、状態で要見直し・未決定・未整理・保留を選んだ状態で開き、見出しの右に件数、下端に「すべて解除」と「{件数} 件を表示」を出す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    # 実行
    open_drawer(page)
    groups = drawer_groups(page)
    head = drawer_head(page)
    # 検証
    assert [group["label"] for group in groups] == ["状態", "着手可否"]
    status = groups[0]
    # 並ぶ値のうち選んでいるものだけを数える（記録に無い「未整理」は数えない）
    assert status["values"] == [
        ["要見直し", 1, True],
        ["未決定", 2, True],
        ["保留", 1, True],
        ["決定済み", 1, False],
    ]
    assert status["sel"] == "3 件を選択"
    assert status["clear"] is True
    assert all(group["sel"] is None and group["clear"] is False for group in groups[1:])
    assert head == {"count": "5 件中 4 件", "foot": ["すべて解除", "4 件を表示"]}
    assert page.get_attribute(DRAWER, "aria-labelledby") == "drawer-title"
    assert page.inner_text("#drawer-title") == "絞り込み"


def test_drawer_keeps_when_view_switched(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ボード・表を切り替えても、ドロワーで選んだ条件を保つ（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    page.wait_for_selector("table.grid")
    open_drawer(page)
    click_value(page, "status", "決定済み")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr[data-id]').length === 5")
    page.click(f"{DRAWER} .fd-foot .btn.primary")
    page.wait_for_selector(DRAWER, state="detached")
    # 実行（ボード）
    page.click('.segment button[data-view="board"]')
    page.wait_for_selector(".board")
    board_done = page.eval_on_selector_all(
        '.board section.board-col[aria-label="決定済み"] .card', "cards => cards.map(c => c.dataset.id)"
    )
    # 実行（表）
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector("table.grid")
    rows = _table_row_ids(page)
    # 検証
    assert board_done == ["D-1"]
    assert rows == ["D-1", "D-2", "D-3", "D-4", "D-5"]
    assert badge_text(page) == "1"
    open_drawer(page)
    assert checked_values(page, "status") == ["要見直し", "未決定", "保留", "決定済み"]


def test_drawer_close(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """見出しの ×・下端の「{件数} 件を表示」・ドロワーの中の Esc・絞り込みのボタン・グレーアウトした所で閉じ、閉じたら絞り込みのボタンへフォーカスを戻す。開いている間はトップバーとタブの帯とドロワー以外をグレーアウトして止める（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    focused: list[str | None] = []
    # 実行（開いている間のグレーアウト）
    open_drawer(page)
    page.wait_for_selector(SCRIM_ON)
    covered = (scrim_visible(page), main_inert(page))
    # 実行（×・下端のボタン・Esc・グレーアウトで閉じる）
    for close in (
        lambda: page.click(f"{DRAWER} button[aria-label='絞り込みを閉じる']"),
        lambda: page.click(f"{DRAWER} .fd-foot .btn.primary"),
        lambda: page.keyboard.press("Escape"),
        lambda: click_scrim(page),
    ):
        if page.locator(DRAWER_OPEN).count() == 0:
            open_drawer(page)
        close()
        page.wait_for_selector(DRAWER, state="detached")
        focused.append(page.evaluate("document.activeElement?.dataset.act ?? null"))
    # 実行（絞り込みのボタンで閉じる）
    open_drawer(page)
    page.click(FILTER_BUTTON)
    page.wait_for_selector(DRAWER, state="detached")
    page.wait_for_selector(SCRIM_ON, state="detached")
    # 検証
    assert covered == (True, True)
    assert focused == ["filter", "filter", "filter", "filter"]
    assert main_inert(page) is False


def test_drawer_clear(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """条件ごとの「解除」でその条件の選びを外し、下端の「すべて解除」で全ての条件を外す。バッジは値を選んでいる条件の数に追従する（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    open_drawer(page)
    click_value(page, "ready", "着手可能")
    page.wait_for_function("document.querySelector('[data-act=filter] .fbadge')?.textContent === '2'")
    # 実行（状態の条件を解除する）
    page.click(f"{DRAWER} button[aria-label='状態の条件を解除']")
    page.wait_for_function("document.querySelector('[data-act=filter] .fbadge')?.textContent === '1'")
    after_clear_status = (badge_text(page), drawer_groups(page)[0]["sel"], _table_row_ids(page))
    # 実行（すべて解除）
    click_value(page, "status", "未決定")
    page.click(f"{DRAWER} .fd-foot button:has-text('すべて解除')")
    page.wait_for_function("!document.querySelector('[data-act=filter] .fbadge')")
    after_clear_all = (badge_text(page), drawer_head(page), _table_row_ids(page))
    # 検証
    assert after_clear_status == ("1", None, ["D-2", "D-5"])
    assert after_clear_all == (None, {"count": "5 件", "foot": ["5 件を表示"]}, ["D-1", "D-2", "D-3", "D-4", "D-5"])


def test_drawer_tags(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """タグの条件を状態の次に並べ、選ぶとそのタグを持つ検討事項に絞る。表のチップで解除できる（正常系）。"""
    # 準備
    url = write_preview(
        make_item("D-1", status="未決定", tags=[{"name": "プレビュー"}]),
        make_item("D-2", status="未決定", tags=[{"name": "サーバー"}, {"name": "プレビュー"}]),
        make_item("D-3", status="未決定"),
    )
    page = open_preview(url, "#tab=decisions&view=table")
    open_drawer(page)
    groups = drawer_groups(page)
    # 実行
    click_value(page, "tags", "プレビュー")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr[data-id]').length === 2")
    selected = (_table_row_ids(page), drawer_head(page)["count"], badge_text(page))
    tag_chip = ".table-block .chip:has(button[aria-label='タグ: プレビュー の条件を解除'])"
    chip = page.inner_text(tag_chip)
    # ドロワーを開いている間は本文を止めるため、閉じてから表のチップで解除する
    page.keyboard.press("Escape")
    page.wait_for_selector(DRAWER, state="detached")
    page.click(f"{tag_chip} button")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr[data-id]').length === 3")
    # 検証
    assert [group["label"] for group in groups][:2] == ["状態", "タグ"]
    assert groups[1]["values"] == [["サーバー", 1, False], ["プレビュー", 2, False]]
    assert selected == (["D-1", "D-2"], "3 件中 2 件", "2")
    assert chip == "タグ: プレビュー"
    assert checked_values(page, "tags") == []


def test_drawer_zero_value(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """今の条件では 0 件になる値は、薄く出して件数を 0 にし、選べるまま残す（正常系）。"""
    # 準備（着手可否「着手可能」だけを選んで開く。着手可能は未決定の D-2・D-5 だけ）
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&f.ready=着手可能")
    open_drawer(page)
    # 実行
    groups = drawer_groups(page)
    zero_values = page.eval_on_selector_all(
        f'{DRAWER} label.fd-opt.zero:has(input[data-key="status"]) .fd-v',
        "values => values.map(v => v.textContent)",
    )
    click_value(page, "status", "未決定")
    # 検証
    assert groups[0]["values"] == [
        ["要見直し", 0, False],
        ["未決定", 2, False],
        ["保留", 0, False],
        ["決定済み", 0, False],
    ]
    assert zero_values == ["要見直し", "保留", "決定済み"]
    assert checked_values(page, "status") == ["未決定"]


def test_drawer_hash_filter(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ハッシュの `f.{列}` で開くと、開いたときの既定の条件に代えてその条件だけを選んだ状態でドロワーに入り、バッジが付き、ハッシュからは消える（正常系）。"""
    # 準備・実行
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&f.ready=着手可能")
    open_drawer(page)
    groups = {group["label"]: group for group in drawer_groups(page)}
    # 検証
    assert _table_row_ids(page) == ["D-2", "D-5"]
    assert badge_text(page) == "1"
    assert checked_values(page, "ready") == ["着手可能"]
    assert checked_values(page, "status") == []
    assert groups["着手可否"]["sel"] == "1 件を選択"
    assert "f." not in page.evaluate("location.hash")


def test_drawer_when_narrow(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """幅 900px 以下では、ドロワーをトップバーの下から画面の幅いっぱいに重ね、絞り込みのボタンは文字を隠してバッジだけ出す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    page.set_viewport_size(DRAWER_NARROW_VIEWPORT)
    # 実行
    open_drawer(page)
    # 開く動きが終わって、左端に着くのを待つ
    page.wait_for_function("document.querySelector('dialog.drawer').getBoundingClientRect().left === 0")
    box = page.eval_on_selector(
        DRAWER, "d => { const r = d.getBoundingClientRect(); return [r.left, r.width]; }"
    )
    label_visible = page.is_visible(f"{FILTER_BUTTON} .label")
    # 検証
    assert box == [0, DRAWER_NARROW_VIEWPORT["width"]]
    assert label_visible is False
    assert badge_text(page) == "1"


def test_drawer_when_narrow_in_front_of_detail(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """幅 390px で詳細パネルを開いたまま絞り込みのボタンで開くと、ドロワーが詳細パネルの前に出て詳細パネルが `inert` になる。「件を表示」で閉じると、開く前の詳細パネルがそのまま見える（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1"))
    page = open_preview(url, DETAIL_HASH)
    open_narrow(page)
    # 実行（詳細パネルを開いたまま開く）
    open_drawer(page)
    wait_front(page, "drawer")
    in_front = {"left_front": has_left_front(page), "detail_inert": is_inert(page, "detail")}
    # 実行（「件を表示」で閉じる）
    page.get_by_role("button", name="件を表示").click()
    page.wait_for_selector(DRAWER, state="detached")
    wait_front(page, "detail")
    # 検証
    assert in_front == {"left_front": True, "detail_inert": True}
    assert has_left_front(page) is False
    assert is_inert(page, "detail") is False
    assert page.inner_text("aside.panel .d-title") == "D-1の題"


def test_drawer_close_by_escape_when_narrow_in_front_of_detail(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """幅 390px でドロワーが詳細パネルの前に出ているときの Esc は、ドロワーだけを閉じ、詳細パネルは開いたままにする（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1"))
    page = open_preview(url, DETAIL_HASH)
    open_narrow(page)
    open_drawer(page)
    wait_front(page, "drawer")
    # 実行
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_selector(DRAWER, state="detached")
    wait_front(page, "detail")
    assert page.locator("aside.panel.open").count() == 1
    assert "id=D-1" in page.evaluate("location.hash")
    assert is_inert(page, "detail") is False


def test_drawer_value_is_checkbox(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """条件のまとまりは fieldset と legend で組み、値はチェックボックスにして、値の件数に読み上げの名前を付ける（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    open_drawer(page)
    # 実行
    structure = page.evaluate(
        """() => ({
            groups: document.querySelectorAll('dialog.drawer fieldset.fd-group > legend').length,
            checkboxes: [...document.querySelectorAll('dialog.drawer .fd-opt input')].every(i => i.type === 'checkbox'),
            counts: document.querySelector('dialog.drawer .fd-opt .n').getAttribute('aria-label'),
            firstFocused: document.activeElement === document.querySelector('dialog.drawer .fd-text input'),
        })"""
    )
    selector = value_selector("status", "未決定")
    # 検証（先頭の文字の欄へフォーカスを移す。条件のまとまりは「文字を含む」と値を選ぶ 2 つ）
    assert structure == {"groups": 3, "checkboxes": True, "counts": "1 件", "firstFocused": True}
    assert page.locator(selector).count() == 1


def test_chips(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ボードのツールバーの下に条件のチップの行を置き、× で 1 つ解除し、「すべて解除」で全ての条件を外す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=board")
    shown = ".board .card"
    page.wait_for_selector(shown)
    # 実行（開いた直後は、開いたときの既定の状態がチップになっている）
    chips = chip_texts(page)
    below_toolbar = page.evaluate(
        "document.querySelector('.screen.decisions .toolbar').nextElementSibling?.classList.contains('chips') ?? false"
    )
    remove_chip(page, "状態: 保留")
    page.wait_for_function("document.querySelectorAll('.chips .chip').length === 3")
    after_remove = (chip_texts(page), badge_text(page))
    clear_all_chips(page)
    page.wait_for_function("document.querySelectorAll('.chips .chip').length === 0")
    page.wait_for_function(f"document.querySelectorAll('{shown}').length === 5")
    # 検証
    assert chips == ["状態: 要見直し", "状態: 未決定", "状態: 未整理", "状態: 保留"]
    assert below_toolbar is True
    assert after_remove == (["状態: 要見直し", "状態: 未決定", "状態: 未整理"], "1")
    assert badge_text(page) is None


def test_comment_marks_when_board(
    write_commented_preview: WriteReviewPreview, open_preview: OpenPreview
) -> None:
    """ボードのカードのメタ情報の右端に、コメントの件数の印を出す。件数 0 の項目には出さない（正常系）。"""
    # 準備・実行
    url, _ = write_commented_preview()
    page = open_preview(url, "#tab=decisions&view=board")
    page.wait_for_selector(".board button.card")
    # 検証
    assert marks_of(page) == SCREEN_MARKS["decisions"]
    assert page.locator(".board button.card").count() == 4
    assert page.locator(".board button.card .c-meta .cmk").count() == 2
    # 印はメタ情報の並びの右端（最後の子）にあり、読み上げと title は実数の件数
    last = page.eval_on_selector(
        '.board button.card[data-id="D-2"] .c-meta',
        "meta => meta.lastElementChild.querySelector('.cmk') !== null",
    )
    assert last is True
    assert page.inner_text('.board button.card[data-id="D-2"] .cmk .sr-only') == "コメント 2 件"
    assert page.get_attribute('.board button.card[data-id="D-2"] .cmk', "title") == "コメント 2 件"
    # 印だけを押す操作は持たず、カードを押すと詳細パネルを開く
    page.click('.board button.card[data-id="D-2"] .cmk')
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-2の題"


def test_comment_marks_when_table(
    write_commented_preview: WriteReviewPreview, open_preview: OpenPreview
) -> None:
    """表の行のタイトルの右に印を出す。件数 0 の行には出さない（正常系）。"""
    # 準備・実行
    url, _ = write_commented_preview()
    page = open_preview(url, f"#tab=decisions&view=table{ALL_DECISION_STATUSES_HASH}")
    page.wait_for_selector("table.grid tbody tr")
    # 検証
    assert marks_of(page) == SCREEN_MARKS["decisions"]
    assert page.locator("table.grid tbody tr").count() == 5
    assert page.locator("table.grid tbody tr:has(.row-open ~ .cmk-place .cmk)").count() == 2


# 項目を多く持つ検討事項の数（領域の高さを超える数）
MANY_DECISIONS = 40

# 表示形式ごとの、領域の中でスクロールする枠
REGION_SCROLLER = {"board": ".board", "table": ".table-wrap"}


def _write_many_decisions(write_preview: WritePreview, make_item: MakeItem) -> str:
    """領域の高さを超える数の未決定の検討事項を持つ配信の URL を返す。"""
    return write_preview(
        *(
            make_item(f"D-{number}", status="未決定", title=f"検討事項の題 {number}")
            for number in range(1, MANY_DECISIONS + 1)
        )
    )


@pytest.mark.parametrize("view", ["board", "table"])
def test_region_when_wide(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem, view: str
) -> None:
    """幅が広いとき、ページ全体はスクロールせず、帯は見えたままで、ボード・表は領域の高さいっぱいに広がって中でスクロールする（正常系）。"""
    # 準備
    url = _write_many_decisions(write_preview, make_item)
    page = open_preview(url, f"#tab=decisions&view={view}")
    page.set_viewport_size(WIDE_VIEWPORT)
    scroller = REGION_SCROLLER[view]
    page.wait_for_selector(scroller)
    # 実行
    metrics = region_metrics(page, scroller)
    # 検証
    assert_page_does_not_scroll(page)
    # 領域そのものはスクロールせず、枠が領域の底まで広がって中で縦にスクロールする
    assert metrics["content"]["scrollHeight"] <= metrics["content"]["clientHeight"]
    assert metrics["target"]["scrollHeight"] > metrics["target"]["clientHeight"]
    assert metrics["target"]["bottom"] <= metrics["content"]["bottom"]
    assert_bands_stay(page)


@pytest.mark.parametrize("view", ["board", "table"])
def test_region_when_narrow(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem, view: str
) -> None:
    """幅が狭いとき（ボード・表）、ページ全体はスクロールせず、領域ごと縦にスクロールし、帯は見えたまま（正常系）。"""
    # 準備
    url = _write_many_decisions(write_preview, make_item)
    page = open_preview(url, f"#tab=decisions&view={view}")
    page.set_viewport_size(NARROW_VIEWPORT)
    page.wait_for_selector(REGION_SCROLLER[view])
    # 実行
    metrics = region_metrics(page, REGION_SCROLLER[view])
    # 検証
    assert_page_does_not_scroll(page)
    assert metrics["content"]["scrollHeight"] > metrics["content"]["clientHeight"]
    # 枠の中では縦にスクロールしない（領域がスクロールする）
    assert metrics["target"]["scrollHeight"] <= metrics["target"]["clientHeight"] + 1
    assert_bands_stay(page)


def test_board_head_stays(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """ボードを縦に送っても、列の見出しはボードの上に留まる。列は最も長い列の高さまで伸びる（正常系）。"""
    # 準備
    url = write_preview(
        *(make_item(f"D-{number}", status="未決定") for number in range(1, MANY_DECISIONS + 1)),
        make_item("D-100", status="保留"),
    )
    page = open_preview(url, "#tab=decisions&view=board")
    page.set_viewport_size(WIDE_VIEWPORT)
    page.wait_for_selector(".board .card")
    # 実行（ボードを一番下まで送る）
    result = page.evaluate(
        """() => {
            const board = document.querySelector('.board');
            board.scrollTop = board.scrollHeight;
            const boardTop = board.getBoundingClientRect().top;
            const heads = [...document.querySelectorAll('.board-col h2')].map((h) => h.getBoundingClientRect().top - boardTop);
            const heights = [...document.querySelectorAll('.board-col')].map((c) => Math.round(c.getBoundingClientRect().height));
            return {scrolled: board.scrollTop > 0, heads, heights};
        }"""
    )
    # 検証
    assert result["scrolled"] is True
    # 全ての列の見出しが、ボードの上端から数 px 以内に留まる
    assert all(0 <= head <= 8 for head in result["heads"])
    # 列は最も長い列の高さまで伸びる（カードの少ない列も同じ高さ）
    assert len(set(result["heights"])) == 1


def test_drawer_text_fields(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ドロワーの値の条件より上に「文字を含む」の欄（ID・タイトル・前提）を並べ、初めて開くと先頭の欄にフォーカスを移す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    # 実行
    open_drawer(page)
    # 検証
    assert drawer_text_fields(page) == [
        {"key": "id", "label": "ID", "value": ""},
        {"key": "title", "label": "タイトル", "value": ""},
        {"key": "depends_on", "label": "前提", "value": ""},
    ]
    first_group = page.eval_on_selector(f"{DRAWER} .fd-body > fieldset:first-child", "e => e.className")
    assert "fd-text" in first_group
    assert page.eval_on_selector(f"{DRAWER} .fd-text legend", "e => e.textContent") == "文字を含む"
    assert page.evaluate("document.activeElement === document.querySelector('dialog.drawer .fd-text input')")


def test_text_filter(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """文字を入れて打ち終えると、その列の値に文字を含む行に絞り、チップとバッジに出す。値の条件の件数は文字で絞った行で数え、同じ欄の同じ位置にカーソルが残る（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table" + ALL_DECISION_STATUSES_HASH)
    open_drawer(page)
    all_rows = _table_row_ids(page)
    # 実行（ID の欄へ文字を打つ）
    page.fill(f'{DRAWER} input[data-text-key="id"]', "d-2")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr[data-id]').length === 1")
    # 検証
    assert all_rows == ["D-1", "D-2", "D-3", "D-4", "D-5"]
    assert _table_row_ids(page) == ["D-2"]
    # 英数字で終わる列名の後には空白を挟む
    assert chip_texts(page) == [
        "状態: 要見直し",
        "状態: 未決定",
        "状態: 未整理",
        "状態: 保留",
        "状態: 決定済み",
        "状態: 対象外",
        "状態: 取り下げ",
        "ID に「d-2」を含む",
    ]
    assert drawer_head(page)["count"] == "5 件中 1 件"
    assert drawer_text_fields(page)[0] == {"key": "id", "label": "ID", "value": "d-2"}
    # 描き直した後も、打っていた欄にフォーカスとカーソルの位置が残る
    caret = page.evaluate(
        """() => {
            const input = document.querySelector('dialog.drawer input[data-text-key="id"]');
            return [document.activeElement === input, input.selectionStart];
        }"""
    )
    assert caret == [True, 3]
    # 値の条件の件数は、文字で絞った行で数える
    status = {group["label"]: group for group in drawer_groups(page)}["状態"]
    assert sum(count for _, count, _ in status["values"]) == 1


def test_text_filter_chip(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """文字の条件のチップは `{列}に「{文字}」を含む` で、× で解除すると行と欄に戻る。列名が英数字で終わらないときは空白を挟まない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&f.~title=D-3")
    # 実行
    chips = chip_texts(page)
    open_drawer(page)
    field = drawer_text_fields(page)[1]
    # ドロワーが覆う範囲のチップを押すため、いったん閉じる
    close_drawer(page)
    remove_chip(page, "タイトルに「D-3」を含む")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr[data-id]').length === 5")
    open_drawer(page)
    # 検証
    assert chips == ["タイトルに「D-3」を含む"]
    assert field == {"key": "title", "label": "タイトル", "value": "D-3"}
    assert chip_texts(page) == []
    assert drawer_text_fields(page)[1]["value"] == ""


def test_text_filter_when_view_switched(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """文字の条件はボード・表で共有し、表示形式を切り替えても保つ。空にすると外れる（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&f.~title=D-3")
    # 実行
    page.click('[data-view="board"]')
    page.wait_for_selector(".board .card")
    board_cards = page.eval_on_selector_all(".board .card", "c => c.map(x => x.dataset.id)")
    board_chips = chip_texts(page)
    open_drawer(page)
    page.fill(f'{DRAWER} input[data-text-key="title"]', "")
    page.wait_for_function("document.querySelectorAll('.board .card').length > 1")
    # 検証
    assert board_cards == ["D-3"]
    assert board_chips == ["タイトルに「D-3」を含む"]
    assert all("を含む" not in chip for chip in chip_texts(page))


@pytest.mark.parametrize(("view", "width", "filled"), [
    (view, width, filled) for view in ("board", "table") for width, filled in TABLE_BOARD_BOUNDARY_WIDTHS
])
def test_region_at_boundary(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    view: str,
    width: int,
    filled: bool,
) -> None:
    """領域の高さいっぱいに広げる境（721px）の前後の幅で、広げるか領域ごとスクロールするかが切り替わる（正常系）。"""
    # 準備
    url = _write_many_decisions(write_preview, make_item)
    page = open_preview(url, f"#tab=decisions&view={view}")
    page.set_viewport_size({"width": width, "height": BOUNDARY_HEIGHT})
    selector = REGION_SCROLLER[view]
    page.wait_for_selector(selector)
    # 実行・検証
    assert_region_mode(page, selector, filled=filled)


def test_drawer_saved_filter(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """サーバーの配信では、条件を変えるたびに端末へ残し、読み込み直しても開いたときの既定に代えてその条件でドロワーと表を開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    open_drawer(page)
    click_value(page, "ready", "着手可能")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr[data-id]').length === 2")
    # 実行
    reload_preview(page)
    open_drawer(page)
    # 検証
    assert read_saved_filters(page) == {
        "decisions": {"status": DEFAULT_DECISION_STATUSES, "ready": ["着手可能"]}
    }
    assert _table_row_ids(page) == ["D-2", "D-5"]
    assert badge_text(page) == "2"
    # サンプルの検討事項に未整理は無いので、残した状態の条件から外して開く
    assert checked_values(page, "status") == ["要見直し", "未決定", "保留"]
    assert checked_values(page, "ready") == ["着手可能"]


def test_drawer_saved_filter_when_all_cleared(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """条件を全て外して残したときは、読み込み直しても開いたときの既定の条件に戻さず、何も選んでいない状態で開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    open_drawer(page)
    page.click(f"{DRAWER} button[aria-label='状態の条件を解除']")
    page.wait_for_function("!document.querySelector('[data-act=filter] .fbadge')")
    # 実行
    reload_preview(page)
    open_drawer(page)
    # 検証
    assert _table_row_ids(page) == ["D-1", "D-2", "D-3", "D-4", "D-5"]
    assert badge_text(page) is None
    assert checked_values(page, "status") == []


def test_drawer_saved_filter_when_text_filter(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """列の文字の欄に入れた条件も端末へ残し、読み込み直しても欄に文字が入ったまま、その文字で絞って開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    open_drawer(page)
    page.fill(f'{DRAWER} input[data-text-key="id"]', "d-2")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr[data-id]').length === 1")
    # 実行
    reload_preview(page)
    open_drawer(page)
    # 検証
    assert read_saved_filters(page) == {
        "decisions": {"status": DEFAULT_DECISION_STATUSES, "~id": ["d-2"]}
    }
    assert _table_row_ids(page) == ["D-2"]
    assert drawer_text_fields(page)[0] == {"key": "id", "label": "ID", "value": "d-2"}
    assert "ID に「d-2」を含む" in chip_texts(page)


def test_drawer_saved_filter_when_hash_filter(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ハッシュの `f.{列}` で開くと、残した条件に代えてハッシュの条件だけで開き、残した条件は書き換えない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    seed_saved_filters(page, {"decisions": {"status": ["未決定"]}})
    # 実行
    reopen_preview(page, url, "#tab=decisions&view=table&f.ready=着手可能")
    open_drawer(page)
    # 検証
    assert _table_row_ids(page) == ["D-2", "D-5"]
    assert checked_values(page, "ready") == ["着手可能"]
    assert checked_values(page, "status") == []
    assert read_saved_filters(page) == {"decisions": {"status": ["未決定"]}}


def test_drawer_saved_filter_when_value_missing(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """残した条件の値が今の記録に無い、または列を知らないときは、その値と列を外して開く（正常系）。"""
    # 準備（検討事項に取り下げの状態は無く、`unknown` という列も無い）
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    seed_saved_filters(page, {"decisions": {"status": ["未決定", "取り下げ"], "unknown": ["値"]}})
    # 実行
    reload_preview(page)
    open_drawer(page)
    # 検証
    assert _table_row_ids(page) == ["D-2", "D-5"]
    assert badge_text(page) == "1"
    assert checked_values(page, "status") == ["未決定"]


@pytest.mark.parametrize("view", ["board", "table"])
def test_fit_smallest(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, view: str
) -> None:
    """検討事項は、幅 320px でページが横にスクロールせず、表のほかにあふれる区画が無く、絞り込みのボタンが表示幅の中にある。ボードは列の右端も表示幅に収まる（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, f"#tab=decisions&view={view}")
    # 実行
    set_smallest(page)
    # 検証
    assert_fits_smallest(page, (FILTER_BUTTON,))
    if view == "board":
        layout = board_layout(page)
        assert layout["rightmost"] <= layout["viewportWidth"]
        assert not layout["pageScrolls"]


def test_drawer_fit_smallest(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """絞り込みのドロワーは、幅 320px で横にスクロールせず、「件を表示」が表示幅の中にあり、押して閉じられる（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    set_smallest(page)
    # 実行
    open_drawer(page)
    # 検証
    assert_fits_smallest(
        page, (DRAWER, f"{DRAWER} button:has-text('件を表示')"), scope=DRAWER
    )
    close_drawer(page)


# ===== 編集（項目を追加・一覧の保存待ちの印・追加する項目） =====

# 幅 480px（「項目を追加」を印だけにする幅の境）
ADD_NARROW_VIEWPORT = {"width": 480, "height": 800}


@pytest.mark.parametrize("view", ["board", "table"])
def test_add_button(
    write_edit_preview: WriteReviewPreview, make_item: MakeItem, open_preview: OpenPreview, view: str
) -> None:
    """サーバーの配信では、表示形式の切り替えの帯の右端に「項目を追加」を出す（正常系）。"""
    # 準備
    url, _ = write_edit_preview(make_item("D-1"))
    # 実行
    page = open_preview(url, f"#tab=decisions&view={view}")
    page.wait_for_selector(ADD_BUTTON)
    # 検証
    button = page.locator(ADD_BUTTON)
    assert button.count() == 1
    assert button.inner_text().strip() == "項目追加"
    assert button.get_attribute("aria-label") == "検討事項の項目を追加"
    bar = page.locator(".toolbar").bounding_box()
    box = button.bounding_box()
    switch = page.locator(".toolbar .segment").first.bounding_box()
    assert bar is not None
    assert box is not None
    assert switch is not None
    assert box["x"] >= switch["x"] + switch["width"]
    assert bar["x"] + bar["width"] - (box["x"] + box["width"]) <= 24


def test_add_button_narrow(
    write_edit_preview: WriteReviewPreview, make_item: MakeItem, open_preview: OpenPreview
) -> None:
    """幅 480px 以下は「＋」の印だけにし、文字を読み上げに残す（正常系）。"""
    # 準備
    url, _ = write_edit_preview(make_item("D-1"))
    page = open_preview(url, "#tab=decisions&view=board")
    # 実行
    page.set_viewport_size(ADD_NARROW_VIEWPORT)
    # 検証
    button = page.locator(ADD_BUTTON)
    label = button.locator(".lbl").bounding_box()
    assert label is None or label["width"] <= 1
    assert button.locator("svg.icon").is_visible()
    assert button.get_attribute("title") == "項目追加"
    assert page.get_by_role("button", name="検討事項の項目を追加").count() == 1


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
    page = open_preview(url, "#tab=decisions&view=board")
    page.wait_for_selector(PENDING_BUTTON)
    # 検証
    assert_topbar_pending(page)


def test_add_button_hidden_when_diff(
    write_history_preview: WriteReviewPreview,
    write_edits: WriteEdits,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """差分の表示をしている間は、「項目を追加」・保存待ちの印・追加する項目を出さない（正常系）。"""
    # 準備
    url, root = write_history_preview()
    write_edits(
        root,
        make_edit("E-1"),
        make_edit("E-2", target="new-1", op="item-add", key="decisions", value={"title": "足す問い", "status": "未整理"}, before=None, base=None),
    )
    preselect_diff(page, "V-1")
    # 実行
    diff = open_preview(url, "#tab=decisions&view=board")
    diff.wait_for_selector(".df-chip")
    # 検証
    assert diff.locator(ADD_BUTTON).count() == 0
    assert diff.locator(".board .pm").count() == 0
    assert diff.locator(f".board {ADDED_ITEM}").count() == 0
    assert diff.locator(PENDING_BUTTON).count() == 0


def test_add_button_hidden_when_exported(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    tmp_path: Path,
) -> None:
    """配る書き出しでは「項目を追加」を出さない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    out = tmp_path / "配る.html"
    result = call_tool("export", workspace=str(root), out=str(out))
    assert result.is_error is False, result.text
    # 実行
    page = open_preview(out.as_uri(), "#tab=decisions&view=board")
    page.wait_for_selector(".board .card")
    # 検証
    assert page.locator(ADD_BUTTON).count() == 0
    assert page.locator(PENDING_BUTTON).count() == 0


def test_add_item(
    write_edit_preview: WriteReviewPreview, make_item: MakeItem, open_preview: OpenPreview
) -> None:
    """「項目を追加」で開いていた詳細パネルを閉じて追加の入力を開き、タイトルを書いて入力欄を離れると `item-add` を 1 件溜める（正常系）。"""
    # 準備
    url, root = write_edit_preview(make_item("D-1", title="最初の問い"))
    page = open_preview(url, "#tab=decisions&view=board&id=D-1")
    page.wait_for_selector("aside.panel.open")
    # 実行
    page.click(ADD_BUTTON)
    page.wait_for_selector(ADD_PANEL)
    # 検証（開いた直後）
    assert page.locator("aside.panel:not(.pe-add-panel)").count() == 0
    assert page.get_attribute(ADD_PANEL, "aria-label") == "検討事項を追加"
    assert page.locator(ADD_TITLE_INPUT).evaluate("e => e === document.activeElement")
    # 実行（タイトルを書いて離れる）
    page.locator(ADD_TITLE_INPUT).fill("足す問い")
    page.locator(ADD_TITLE_INPUT).blur()
    page.wait_for_selector(f"{PENDING_BUTTON} .count")
    # 検証（溜めた後）
    edits = read_edits_file(root)["items"]
    assert [(edit["op"], edit["key"], edit["value"]["title"]) for edit in edits] == [("item-add", "decisions", "足す問い")]
    assert page.locator(f".board-col[aria-label='未整理'] {ADDED_ITEM}").count() == 1


@pytest.mark.parametrize("view", ["board", "table"])
def test_list_marks(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
    view: str,
) -> None:
    """保存待ちの編集がある項目に、書き換えは保存待ち・削除は保存で削除・直前の保存で書き込めなかった編集は書き込めないの印を付ける（正常系）。"""
    # 準備
    url, _ = write_edit_preview(*edit_items(make_item, "D"), edits=edit_edits(make_edit, "D"))
    page = open_preview(url, f"#tab=decisions&view={view}")
    page.wait_for_selector(PENDING_BUTTON)
    # 実行（直前の保存で D-3 だけ書き込めなくする）
    block_by_saving(page)
    # 検証
    scope = {
        "board": ".board button.card[data-id]",
        "table": "table tr[data-id]",
    }[view]
    marks = item_marks(page, scope)
    assert {id_: (mark["kind"], mark["compact"]) for id_, mark in marks.items()} == {
        "D-1": ("pending", False),
        "D-2": ("remove", False),
        "D-3": ("blocked", False),
    }
    # 文字は、カードと表の行の印に出す
    labels = {"pending": "保存待ち", "remove": "保存で削除", "blocked": "書き込めない"}
    for mark in marks.values():
        assert mark["text"] == labels[mark["kind"]]
    assert page.locator(f"{scope}.pe-removing").count() == 1


def test_added_items_board(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """ボードは、溜めた状態の列（無ければ「未整理」）の先頭に破線の枠で出す。ID の場所に「ID は保存時に決定」を置き、タイトルが空なら「（タイトル未入力）」と出す（正常系）。"""
    # 準備
    url, _ = write_edit_preview(
        make_item("D-1", title="今ある問い", status="未決定"),
        make_item("D-2", title="未整理の問い", status="未整理"),
        edits=(
            make_edit("E-1", target="new-1", op="item-add", key="decisions", value={"title": "足す問い", "status": "未決定"}, before=None, base=None),
            make_edit("E-2", target="new-2", op="item-add", key="decisions", value={"title": "", "status": "未整理"}, before=None, base=None),
        ),
    )
    # 実行
    page = open_preview(url, "#tab=decisions&view=board")
    page.wait_for_selector(ADDED_ITEM)
    # 検証
    assert page.eval_on_selector_all(
        ".board section.board-col",
        "cols => cols.filter(c => c.querySelector('.card')).map(c => [c.getAttribute('aria-label'), [...c.querySelectorAll('.card')].map(k => k.dataset.newId ?? k.dataset.id)])",
    ) == [["未決定", ["new-1", "D-1"]], ["未整理", ["new-2", "D-2"]]]
    first = page.locator(".card[data-new-id='new-1']")
    assert first.evaluate("e => getComputedStyle(e).borderTopStyle") == "dashed"
    assert first.locator(".pe-noid").inner_text() == "ID は保存時に決定"
    assert first.locator(".c-ttl").inner_text() == "足す問い"
    assert first.locator(".pm.pm-pending").count() == 1
    assert page.locator(".card[data-new-id='new-2'] .c-ttl").inner_text() == "（タイトル未入力）"
    assert page.locator(".card[data-new-id='new-1'] .mono").count() == 0


def test_added_items_table(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """表は先頭の行に破線の枠で出す。ID の列に「—」を置く（正常系）。"""
    # 準備
    url, _ = write_edit_preview(
        make_item("D-1", title="今ある問い"),
        edits=(make_edit("E-1", target="new-1", op="item-add", key="decisions", value={"title": "足す問い", "status": "未整理"}, before=None, base=None),),
    )
    # 実行
    page = open_preview(url, "#tab=decisions&view=table")
    page.wait_for_selector(ADDED_ITEM)
    # 検証
    rows = page.eval_on_selector_all("table tbody tr", "rows => rows.map(r => r.dataset.newId ?? r.dataset.id)")
    assert rows == ["new-1", "D-1"]
    row = page.locator("tr[data-new-id='new-1']")
    assert row.locator(".pe-noid").inner_text() == "—"
    assert row.locator(".row-open").inner_text() == "足す問い"
    assert row.locator(".pm.pm-pending").count() == 1


def test_added_item_reopens_input(
    write_edit_preview: WriteReviewPreview, make_item: MakeItem, open_preview: OpenPreview
) -> None:
    """追加する項目を押すと、追加する入力を開き直す（正常系）。"""
    # 準備
    url, _ = write_edit_preview(make_item("D-1"))
    page = open_preview(url, "#tab=decisions&view=board")
    start_add(page, "足す問い")
    page.get_by_role("button", name="追加の入力を閉じる").click()
    page.wait_for_selector(ADD_PANEL, state="detached")
    # 実行
    page.click(f".card{ADDED_ITEM}")
    # 検証
    page.wait_for_selector(ADD_PANEL)
    assert page.locator(ADD_TITLE_INPUT).input_value() == "足す問い"


# 保存待ちの item-add の value.options が、採用まで含めて渡した並びになったか
ADDED_OPTIONS_MATCH_JS = """(items, expected) => items.some(e => e.op === 'item-add'
  && JSON.stringify(e.value.options ?? []) === JSON.stringify(expected))"""


def _wait_added_options(page: Page, expected: list[dict[str, object]]) -> None:
    """保存待ちの item-add の value.options が expected になるのを待つ。"""
    wait_edits_match(page, ADDED_OPTIONS_MATCH_JS, expected)


def test_add_item_with_options(
    write_edit_preview: WriteReviewPreview, make_item: MakeItem, open_preview: OpenPreview
) -> None:
    """追加の入力で書いた案は `item-add` の value.options に溜め、採用を選ぶと決定済みにする。案を削除しても同じ記号の下書きを残さず、開き直すと案をそのまま出す（正常系）。"""
    # 準備
    url, root = write_edit_preview(make_item("D-1"))
    # ボードは既定で決定済みの列を外すため、表で開く
    page = open_preview(url, "#tab=decisions&view=table")
    start_add(page, "足す問い")
    # 実行（案 A・B を書いて離れる）
    for key, content in (("A", "項目ごと"), ("B", "まとめて")):
        page.get_by_role("button", name="案追加").click()
        area = page.get_by_label(f"案 {key} の中身")
        area.fill(content)
        area.blur()
    _wait_added_options(page, [{"key": "A", "content": "項目ごと"}, {"key": "B", "content": "まとめて"}])
    # 実行（案 B を採用する）
    page.get_by_role("radio", name="採用").nth(1).check()
    _wait_added_options(
        page, [{"key": "A", "content": "項目ごと"}, {"key": "B", "content": "まとめて", "adopted": True}]
    )
    # 検証（溜めた後）
    edits = read_edits_file(root)["items"]
    assert [edit["op"] for edit in edits] == ["item-add"]
    value = edits[0]["value"]
    assert value["status"] == "決定済み"
    assert "A" not in value
    assert "B" not in value
    expect(page.locator(PENDING_BUTTON)).to_have_attribute("aria-label", "保存待ち（1 件）", timeout=SETTLE_MS)
    expect(page.get_by_role("button", name="案 B を削除")).to_have_count(0, timeout=SETTLE_MS)
    # 実行（採用していない案 A を削除する）
    page.get_by_role("button", name="案 A を削除").click()
    _wait_added_options(page, [{"key": "B", "content": "まとめて", "adopted": True}])
    # 検証（削除した後）
    expect(page.get_by_label("案 A の中身")).to_have_count(0, timeout=SETTLE_MS)
    # 実行（閉じて開き直す）
    page.get_by_role("button", name="追加の入力を閉じる").click()
    page.wait_for_selector(ADD_PANEL, state="detached")
    page.click(f"tr{ADDED_ITEM} .row-open")
    page.wait_for_selector(ADD_PANEL)
    # 検証（開き直した後）
    expect(page.get_by_label("案 B の中身")).to_have_value("まとめて")
    expect(page.get_by_role("radio", name="採用")).to_be_checked()
    expect(page.get_by_label("案 A の中身")).to_have_count(0)


# 保存待ちの item-add が 1 件で、その value が渡したキーと値を全て持つか
ADDED_VALUE_MATCH_JS = """(items, expected) => {
  const adds = items.filter(e => e.op === 'item-add');
  return adds.length === 1
    && Object.entries(expected).every(([k, v]) => JSON.stringify(adds[0].value[k]) === JSON.stringify(v));
}"""


def _wait_added_value(page: Page, expected: dict[str, object]) -> None:
    """保存待ちの item-add が 1 件で、その value が expected のキーと値を全て持つのを待つ。"""
    wait_edits_match(page, ADDED_VALUE_MATCH_JS, expected)


def _hold_edit_posts(page: Page) -> Callable[[], None]:
    """編集を溜める送信（POST /api/edits）の応答を止め、止めた送信を順に通して以降は止めない関数を返す。"""
    held: list[Route] = []
    holding = [True]

    def handle(route: Route) -> None:
        # 止めている間の溜める送信だけを止め、読み取り（GET）と止めた後の送信は通す
        if holding[0] and route.request.method == "POST":
            held.append(route)
            return
        route.continue_()

    def release() -> None:
        holding[0] = False
        for route in held:
            route.continue_()
        held.clear()

    page.route("**/api/edits", handle)
    return release


def test_add_item_with_options_when_sent_before_response(
    write_edit_preview: WriteReviewPreview, make_item: MakeItem, open_preview: OpenPreview
) -> None:
    """追加の入力で案 A を書いた送信の応答より前に案 B を書いても、`item-add` 1 件の value.options に A・B が溜まり、追加の入力に案 A・B が出る（正常系）。"""
    # 準備
    url, root = write_edit_preview(make_item("D-1"))
    page = open_preview(url, "#tab=decisions&view=table")
    start_add(page, "足す問い")
    release = _hold_edit_posts(page)
    # 実行（案 A を書いて離れ、その送信の応答より前に案 B を書いて離れる）
    page.get_by_role("button", name="案追加").click()
    page.get_by_label("案 A の中身").fill("項目ごと")
    page.get_by_label("案 A の中身").blur()
    page.get_by_role("button", name="案追加").click()
    page.get_by_label("案 B の中身").fill("まとめて")
    page.get_by_label("案 B の中身").blur()
    release()
    _wait_added_value(page, {"options": [{"key": "A", "content": "項目ごと"}, {"key": "B", "content": "まとめて"}]})
    # 検証
    edits = read_edits_file(root)["items"]
    assert [edit["op"] for edit in edits] == ["item-add"]
    assert edits[0]["value"]["options"] == [{"key": "A", "content": "項目ごと"}, {"key": "B", "content": "まとめて"}]
    expect(page.get_by_label("案 A の中身")).to_have_value("項目ごと", timeout=SETTLE_MS)
    expect(page.get_by_label("案 B の中身")).to_have_value("まとめて", timeout=SETTLE_MS)
    expect(page.locator(PENDING_BUTTON)).to_have_attribute("aria-label", "保存待ち（1 件）", timeout=SETTLE_MS)


def test_add_item_with_keys_when_sent_before_response(
    write_edit_preview: WriteReviewPreview, make_item: MakeItem, open_preview: OpenPreview
) -> None:
    """追加の入力でタイトル・タグ・状態を、どれも前の送信の応答より前に続けて書いても、`target` の無い `item-add` を重ねず、1 件の value に全ての値が溜まる（正常系）。"""
    # 準備
    url, root = write_edit_preview(make_item("D-1"))
    page = open_preview(url, "#tab=decisions&view=table")
    release = _hold_edit_posts(page)
    page.click(ADD_BUTTON)
    page.wait_for_selector(ADD_PANEL)
    # 実行（タイトルを書いて離れ、その送信の応答より前にタグを入れ、状態を変える）
    page.locator(ADD_TITLE_INPUT).fill("足す問い")
    page.locator(ADD_TITLE_INPUT).blur()
    page.get_by_label("タグを追加").fill("画面")
    page.get_by_label("タグを追加").press("Enter")
    page.get_by_label("状態", exact=True).select_option("保留")
    release()
    _wait_added_value(page, {"title": "足す問い", "tags": [{"name": "画面"}], "status": "保留"})
    # 検証
    edits = read_edits_file(root)["items"]
    assert [edit["op"] for edit in edits] == ["item-add"]
    assert (edits[0]["value"]["title"], edits[0]["value"]["tags"], edits[0]["value"]["status"]) == (
        "足す問い",
        [{"name": "画面"}],
        "保留",
    )
    expect(page.locator(PENDING_BUTTON)).to_have_attribute("aria-label", "保存待ち（1 件）", timeout=SETTLE_MS)
