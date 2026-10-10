"""画面設計『検討事項』（マップ・ボード・表。マップは項目 ID `decision-map`）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page
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
    MAP_BOUNDARY_WIDTHS,
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
    MIN_UI_FONT_SIZE_PX,
    PHONE_VIEWPORT,
    TRANSPARENT,
    board_edges,
    board_layout,
    map_item_id_font_size,
    pin_id_column,
    table_cell_backgrounds,
)
from workspace_fixtures import MakeItem

# マップを字下げの一覧に切り替える幅の境（これ以下）
NARROW_WIDTH = 800

# 狭い幅の画面の高さ
NARROW_HEIGHT = 700

# マップの項目の節点の幅と高さ（印の有無によらず同じ）
MAP_NODE_WIDTH = 268
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

# マップに検討事項が 1 件も描かれていない
NO_MAP_ITEM_SCRIPT = "!document.querySelector('#decision-map .map-node.n-item')"

# 項目を選んでいる（詳細パネルが開き、マップの節に選んだ印が付き、ほかが薄い）
SELECTED_MAP_SCRIPT = (
    "!!document.querySelector('aside.panel.open')"
    " && !!document.querySelector('#decision-map button.map-node.sel')"
    " && document.getElementById('decision-map').classList.contains('focusing')"
)

# 選びが外れている（詳細パネルが閉じ、マップの節の選んだ印と薄い表示が消えている）
DESELECTED_MAP_SCRIPT = (
    "!document.querySelector('aside.panel.open')"
    " && !document.querySelector('#decision-map button.map-node.sel')"
    " && !document.getElementById('decision-map').classList.contains('focusing')"
)

# 余白を押してから、描き直しなどで変わるものが落ち着くまで待つ時間（ms。変わらないことを確かめる前に置く）
PRESS_SETTLE_MS = 400

# 押したとみなす移動の上限（`PRESS_SLOP_PX`）と、それを超える移動（px）
PRESS_SLOP_PX = 5
DRAG_OVER_SLOP_PX = PRESS_SLOP_PX + 1

# 余白の点を探すとき、マップの枠の右下から内へ入る余白と、探す間隔（px）
BLANK_SCAN_MARGIN_PX = 24
BLANK_SCAN_STEP_PX = 20

# 拡大・縮小で倍率を決めるための「拡大」を押す回数（上限の倍率になる）と、スクロールさせる位置（px）
ZOOM_IN_CLICKS = 6
SCROLL_LEFT_PX = 150
SCROLL_TOP_PX = 40

# マップの枠の右下から内へ探して、枠・拡大の土台・マップの面だけが当たる余白の点（画面上の座標）を返す
BLANK_POINT_SCRIPT = """([margin, step]) => {
    const canvas = document.getElementById("decision-map");
    const wrap = canvas.closest(".map-wrap");
    const blanks = [wrap, wrap.firstElementChild, canvas];
    const box = wrap.getBoundingClientRect();
    const right = box.left + wrap.clientLeft + wrap.clientWidth;
    const bottom = box.top + wrap.clientTop + wrap.clientHeight;
    for (let y = bottom - margin; y > box.top; y -= step) {
        for (let x = right - margin; x > box.left; x -= step) {
            if (blanks.includes(document.elementFromPoint(x, y))) return { x, y };
        }
    }
    return null;
}"""

# 木の枝（対象 → カテゴリーの最初の線）の中ほどの点（画面上の座標）を返す
EDGE_POINT_SCRIPT = """() => {
    const path = document.querySelector("#decision-map svg.edges path.edge-tree");
    const middle = path.getPointAtLength(path.getTotalLength() / 2);
    const point = new DOMPoint(middle.x, middle.y).matrixTransform(path.getScreenCTM());
    return { x: point.x, y: point.y };
}"""

# ホイールの拡大・縮小: 1 回の刻み（奥へ回す deltaY）・手前へ回す deltaY・倍率の上限と下限・刻みの掛け率・回す回数の上限（上限・下限に届く回数より多い）
WHEEL_IN_DELTA = -100
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

# 全体を表示のときの、マップの右と下の余白（px）
FIT_MARGIN_RIGHT_PX = 240

# マップの倍率（`transform: scale(...)` の数値）を返す
MAP_SCALE_SCRIPT = """() => Number.parseFloat(document.getElementById("decision-map").style.transform.slice(6))"""

# マップの土台の右の余白（土台の幅 - 木の幅 × 倍率）と、枠の幅
MAP_MARGIN_SCRIPT = """() => {
    const canvas = document.getElementById("decision-map");
    const wrap = canvas.closest(".map-wrap");
    const scale = Number.parseFloat(canvas.style.transform.slice(6));
    return { margin: wrap.firstElementChild.offsetWidth - canvas.offsetWidth * scale, frame: wrap.clientWidth };
}"""

# マップの枠のスクロールの位置と、拡大の倍率
MAP_VIEW_SCRIPT = """() => {
    const canvas = document.getElementById("decision-map");
    const wrap = canvas.closest(".map-wrap");
    return { left: wrap.scrollLeft, top: wrap.scrollTop, transform: canvas.style.transform };
}"""

# 鍵の震えが収まるまで待つ時間（ms。震えは約 1 秒）と、震え始めを確かめるまでの時間
SHAKE_DONE_MS = 1_800
SHAKE_EARLY_MS = 120

# 素早い 2 回押しにする、続けて押す間隔（ms。450ms 未満）
QUICK_PRESS_GAP_MS = 80

# 節の鍵（閉じた鍵はロックした節だけ、開いた鍵は詳細を開いている節にカーソルを乗せたときだけ表示する）
LOCKED_NODE = "#decision-map button.n-item.locked"
KEY = "#decision-map button.n-item .lk"

# 節の鍵が表示されている（`display` が `none` でない）節の ID を返す
SHOWN_KEYS_SCRIPT = """() => [...document.querySelectorAll('#decision-map button.n-item')]
    .filter(node => getComputedStyle(node.querySelector('.lk')).display !== 'none')
    .map(node => node.dataset.node)"""



def _view_pressed(page: Page, view: str) -> str | None:
    """表示形式の切り替えで、その形式のボタンが押されているかを返す。"""
    return page.get_attribute(f'.segment button[data-view="{view}"]', "aria-pressed")


def _map_item_ids(page: Page) -> list[str]:
    """マップに描かれている検討事項の ID を並びのまま返す。"""
    return page.eval_on_selector_all(
        "#decision-map .map-node.n-item", "nodes => nodes.map(n => n.dataset.node)"
    )


def test_view_switch(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """表示形式の切り替えは、view の無いハッシュでボードが押された状態で開き、ボード・マップ・表の順に並び、行き来するとハッシュの view を置き換える（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions")
    history_length = page.evaluate("history.length")
    assert _view_pressed(page, "board") == "true"
    assert page.eval_on_selector_all(
        ".segment button", "buttons => buttons.map(b => b.dataset.view)"
    ) == ["board", "map", "table"]
    # 実行・検証
    for view in ("map", "table", "board"):
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


def test_map(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """対象 → カテゴリー → フェーズ → 検討事項の木をマップに描き、項目を押すと詳細パネルを開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    # 実行・検証（既定は決定済みを隠した状態）
    kinds = page.eval_on_selector_all(
        "#decision-map .map-node",
        "nodes => nodes.map(n => n.className.split(' ').find(c => c.startsWith('n-')))",
    )
    assert kinds[:3] == ["n-target", "n-category", "n-phase"]
    assert _map_item_ids(page) == ["D-2", "D-3", "D-4", "D-5"]
    page.click('#decision-map button[data-node="D-2"]')
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-2の題"
    assert "id=D-2" in page.evaluate("location.hash")


def test_map_drawer_status(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ドロワーの状態の値を選ぶとその状態の検討事項をマップに出し、外すと隠す。状態の帯は出さない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    open_drawer(page)
    initial = checked_values(page, "status")
    # 実行
    click_value(page, "status", "決定済み")
    page.wait_for_selector('#decision-map button[data-node="D-1"]')
    shown = _map_item_ids(page)
    click_value(page, "status", "保留")
    page.wait_for_function("!document.querySelector('#decision-map [data-node=\"D-4\"]')")
    # 検証
    assert initial == ["要見直し", "未決定", "保留"]
    assert "D-1" in shown
    assert "D-4" not in _map_item_ids(page)
    assert page.locator(".legend").count() == 0


def test_map_keyword(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """キーワードを名前に含む項目を強調する（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    # 実行
    page.fill("input.map-q", "D-2")
    page.wait_for_selector("#decision-map .map-node.hit")
    # 検証
    hits = page.eval_on_selector_all(
        "#decision-map .map-node.hit", "nodes => nodes.map(n => n.dataset.node)"
    )
    assert hits == ["D-2"]
    assert page.get_attribute("input.map-q", "placeholder") == "タイトルで強調"
    assert page.get_attribute("input.map-q", "aria-label") == "タイトルで強調するキーワード"


def test_map_zoom(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """拡大・縮小で倍率を変え、全体を表示で全体が収まる倍率に戻す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    fit = page.locator(".zoom button", has_text="全体を表示")
    assert fit.get_attribute("aria-pressed") == "true"
    # 実行・検証
    page.click('.zoom button[aria-label="拡大"]')
    page.wait_for_function(
        "document.querySelector('.zoom .btn').getAttribute('aria-pressed') === 'false'"
    )
    page.click(".zoom .btn")
    page.wait_for_function(
        "document.querySelector('.zoom .btn').getAttribute('aria-pressed') === 'true'"
    )


def _open_wheel_map(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> tuple[Page, str]:
    """サンプルの記録（マップが枠より小さい）をマップで開き、最後の検討事項の節の中心にマウスを置いて、節のセレクターを返す。"""
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    page.set_viewport_size(DESKTOP_VIEWPORT)
    page.wait_for_selector("#decision-map .map-node.n-item")
    node = f'#decision-map button[data-node="{_map_item_ids(page)[-1]}"]'
    center = _box_center(page, node)
    page.mouse.move(center["x"], center["y"])
    return page, node


def test_map_wheel_zoom(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """マップの枠の上でホイールを奥へ回すと倍率が 1.12 倍になり、回す前にマウスの下にあった節がマウスの下に残る。ページは動かず、全体を表示の押された状態が外れる（正常系）。"""
    # 準備
    page, node = _open_wheel_map(write_sample_preview, open_preview)
    before = _box_center(page, node)
    fit_scale = page.evaluate(MAP_SCALE_SCRIPT)
    assert page.locator(".zoom .btn").get_attribute("aria-pressed") == "true"
    # 実行
    page.mouse.wheel(0, WHEEL_IN_DELTA)
    page.wait_for_timeout(WHEEL_SETTLE_MS)
    # 検証
    after = _box_center(page, node)
    assert page.evaluate(MAP_SCALE_SCRIPT) == pytest.approx(fit_scale * WHEEL_FACTOR)
    assert abs(after["x"] - before["x"]) <= WHEEL_POINT_TOLERANCE_PX
    assert abs(after["y"] - before["y"]) <= WHEEL_POINT_TOLERANCE_PX
    assert page.evaluate("window.scrollY") == 0
    assert page.locator(".zoom .btn").get_attribute("aria-pressed") == "false"
    # マップの枠は、マウスの下の点を残す分だけ送られている
    view = page.evaluate(MAP_VIEW_SCRIPT)
    assert view["left"] > 0
    assert view["top"] > 0


def test_map_wheel_zoom_when_repeated(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """奥へ回し続けると倍率は 150% で止まり、手前へ回し続けると 40% で止まる。回している間、節はマウスの下に残り、ページは動かない（正常系）。"""
    # 準備
    page, node = _open_wheel_map(write_sample_preview, open_preview)
    before = _box_center(page, node)
    # 実行・検証（奥へ）
    for _ in range(WHEEL_MAX_TURNS):
        page.mouse.wheel(0, WHEEL_IN_DELTA)
    page.wait_for_timeout(WHEEL_SETTLE_MS)
    assert page.evaluate(MAP_SCALE_SCRIPT) == pytest.approx(WHEEL_ZOOM_MAX)
    assert abs(_box_center(page, node)["x"] - before["x"]) <= WHEEL_POINT_TOLERANCE_PX
    assert abs(_box_center(page, node)["y"] - before["y"]) <= WHEEL_POINT_TOLERANCE_PX
    # 150% でさらに奥へ回しても、倍率も節の位置も変わらない
    page.mouse.wheel(0, WHEEL_IN_DELTA)
    page.wait_for_timeout(WHEEL_SETTLE_MS)
    assert page.evaluate(MAP_SCALE_SCRIPT) == pytest.approx(WHEEL_ZOOM_MAX)
    assert page.evaluate("window.scrollY") == 0
    # 実行・検証（手前へ）
    for _ in range(WHEEL_MAX_TURNS * 2):
        page.mouse.wheel(0, WHEEL_OUT_DELTA)
    page.wait_for_timeout(WHEEL_SETTLE_MS)
    assert page.evaluate(MAP_SCALE_SCRIPT) == pytest.approx(WHEEL_ZOOM_MIN)
    assert page.evaluate("window.scrollY") == 0


def test_map_wheel_zoom_when_zoomed_out_after_scrolled(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """拡大で枠を送った後に手前へ 1 回回しても、回す前にマウスの下にあった節がマウスの下に残る（正常系）。"""
    # 準備（奥へ 1 回回して、枠のスクロールの位置が 0 より大きい状態にする）
    page, node = _open_wheel_map(write_sample_preview, open_preview)
    before = _box_center(page, node)
    page.mouse.wheel(0, WHEEL_IN_DELTA)
    page.wait_for_timeout(WHEEL_SETTLE_MS)
    zoomed_in = page.evaluate(MAP_VIEW_SCRIPT)
    assert zoomed_in["left"] > 0
    assert zoomed_in["top"] > 0
    zoomed_scale = page.evaluate(MAP_SCALE_SCRIPT)
    # 実行
    page.mouse.wheel(0, WHEEL_OUT_DELTA)
    page.wait_for_timeout(WHEEL_SETTLE_MS)
    # 検証
    after = _box_center(page, node)
    assert page.evaluate(MAP_SCALE_SCRIPT) == pytest.approx(zoomed_scale / WHEEL_FACTOR)
    assert abs(after["x"] - before["x"]) <= WHEEL_POINT_TOLERANCE_PX
    assert abs(after["y"] - before["y"]) <= WHEEL_POINT_TOLERANCE_PX
    assert page.evaluate("window.scrollY") == 0


def test_map_wheel_zoom_when_fit_pressed(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ホイールで倍率を数値にしたあいだはマップの右に枠の幅の余白を持ち、全体を表示を押すと押された状態と元の余白に戻る（正常系）。"""
    # 準備
    page, _ = _open_wheel_map(write_sample_preview, open_preview)
    fit_before = page.evaluate(MAP_MARGIN_SCRIPT)
    fit_scale = page.evaluate(MAP_SCALE_SCRIPT)
    assert fit_before["margin"] == pytest.approx(FIT_MARGIN_RIGHT_PX, abs=MARGIN_TOLERANCE_PX)
    # 実行・検証（ホイールで数値の倍率にする）
    page.mouse.wheel(0, WHEEL_IN_DELTA)
    page.wait_for_timeout(WHEEL_SETTLE_MS)
    zoomed = page.evaluate(MAP_MARGIN_SCRIPT)
    assert zoomed["margin"] == pytest.approx(zoomed["frame"], abs=MARGIN_TOLERANCE_PX)
    # 実行・検証（全体を表示に戻す）
    page.click(".zoom .btn")
    page.wait_for_function(
        "document.querySelector('.zoom .btn').getAttribute('aria-pressed') === 'true'"
    )
    assert page.evaluate(MAP_MARGIN_SCRIPT)["margin"] == pytest.approx(
        FIT_MARGIN_RIGHT_PX, abs=MARGIN_TOLERANCE_PX
    )
    assert page.evaluate(MAP_SCALE_SCRIPT) == pytest.approx(fit_scale)


def test_map_wheel_zoom_when_horizontal(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """横にだけ回した件（deltaY が 0）では倍率を変えない（正常系）。"""
    # 準備
    page, _ = _open_wheel_map(write_sample_preview, open_preview)
    scale_before = page.evaluate(MAP_SCALE_SCRIPT)
    # 実行
    page.mouse.wheel(WHEEL_OUT_DELTA, 0)
    page.wait_for_timeout(WHEEL_SETTLE_MS)
    # 検証
    assert page.evaluate(MAP_SCALE_SCRIPT) == scale_before
    assert page.locator(".zoom .btn").get_attribute("aria-pressed") == "true"


def test_map_zoom_buttons_when_wheel_zoomed(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """縮小・拡大・全体を表示のボタンはホイールの拡大・縮小の後も残り、押すと倍率を変える（正常系）。"""
    # 準備
    page, _ = _open_wheel_map(write_sample_preview, open_preview)
    page.mouse.wheel(0, WHEEL_IN_DELTA)
    page.wait_for_timeout(WHEEL_SETTLE_MS)
    scale_before = page.evaluate(MAP_SCALE_SCRIPT)
    # 実行
    page.click('.zoom button[aria-label="縮小"]')
    # 検証
    assert page.evaluate(MAP_SCALE_SCRIPT) < scale_before
    assert page.locator('.zoom button[aria-label="拡大"]').count() == 1
    assert page.locator(".zoom .btn").count() == 1


def _open_selected_map(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> Page:
    """項目 D-2 を選んだ状態でマップを開き、選びが描き終わるまで待つ。"""
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=map&id=D-2")
    page.wait_for_function(SELECTED_MAP_SCRIPT)
    return page


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


def _blank_point(page: Page) -> dict[str, float]:
    """マップの枠の中の、節にも線にも当たらない余白の点を返す。"""
    point = page.evaluate(BLANK_POINT_SCRIPT, [BLANK_SCAN_MARGIN_PX, BLANK_SCAN_STEP_PX])
    assert point is not None
    return point


@pytest.mark.parametrize(
    "place",
    [
        pytest.param("blank", id="blank"),
        pytest.param(".n-target", id="target_node"),
        pytest.param(".n-category", id="category_node"),
        pytest.param(".n-phase", id="phase_node"),
        pytest.param("edge", id="edge"),
    ],
)
def test_map_background_press(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, place: str
) -> None:
    """項目を選んだ状態で余白を押して離すと、詳細パネルを閉じ、ハッシュから項目の ID を外し、強調と薄い表示を消す（正常系）。"""
    # 準備（選んだ項目が中央に来る位置から、左上の節と線が見える位置へ送る）
    page = _open_selected_map(write_sample_preview, open_preview)
    page.evaluate("document.querySelector('.map-wrap').scrollTo({left: 0, top: 0})")
    if place == "blank":
        point = _blank_point(page)
    elif place == "edge":
        point = page.evaluate(EDGE_POINT_SCRIPT)
    else:
        point = _box_center(page, f"#decision-map {place}")
    # 実行
    _press_at(page, point)
    page.wait_for_function(DESELECTED_MAP_SCRIPT)
    # 検証
    assert "id=" not in page.evaluate("location.hash")
    assert page.evaluate("document.querySelectorAll('#decision-map .flow-dot').length") == 0
    assert _map_item_ids(page) == ["D-2", "D-3", "D-4", "D-5"]


def test_map_background_press_when_dragged(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """余白を押して上限を超えてドラッグし離したときは、選びを保つ（正常系）。"""
    # 準備
    page = _open_selected_map(write_sample_preview, open_preview)
    hash_text = page.evaluate("location.hash")
    point = _blank_point(page)
    # 実行
    page.mouse.move(point["x"], point["y"])
    page.mouse.down()
    page.mouse.move(point["x"] - DRAG_OVER_SLOP_PX, point["y"], steps=3)
    page.mouse.up()
    page.wait_for_timeout(PRESS_SETTLE_MS)
    # 検証
    assert page.evaluate(SELECTED_MAP_SCRIPT) is True
    assert page.evaluate("location.hash") == hash_text


def test_map_background_press_when_nothing_selected(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """何も選んでいないときに余白を押しても、ハッシュとマップの表示が変わらない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    hash_text = page.evaluate("location.hash")
    history_length = page.evaluate("history.length")
    view_before = page.evaluate(MAP_VIEW_SCRIPT)
    # 実行
    _press_at(page, _blank_point(page))
    page.wait_for_timeout(PRESS_SETTLE_MS)
    # 検証
    assert page.evaluate("location.hash") == hash_text
    assert page.evaluate("history.length") == history_length
    assert page.evaluate(DESELECTED_MAP_SCRIPT) is True
    assert _map_item_ids(page) == ["D-2", "D-3", "D-4", "D-5"]
    assert page.evaluate(MAP_VIEW_SCRIPT) == view_before


def test_map_background_press_when_zoomed(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """拡大・縮小で倍率を決めたとき、余白を押す前後でスクロールの位置と倍率が変わらない（正常系）。"""
    # 準備
    page = _open_selected_map(write_sample_preview, open_preview)
    for _ in range(ZOOM_IN_CLICKS):
        page.click('.zoom button[aria-label="拡大"]')
    page.wait_for_function(
        "document.querySelector('.zoom .btn').getAttribute('aria-pressed') === 'false'"
    )
    page.evaluate(
        "([left, top]) => document.querySelector('.map-wrap').scrollTo({left, top})",
        [SCROLL_LEFT_PX, SCROLL_TOP_PX],
    )
    before = page.evaluate(MAP_VIEW_SCRIPT)
    # スクロールが効いていて、押した後に枠が広がっても位置が切り詰められない余地がある
    assert before["left"] == SCROLL_LEFT_PX
    assert before["top"] == SCROLL_TOP_PX
    # 実行
    _press_at(page, _blank_point(page))
    page.wait_for_function(DESELECTED_MAP_SCRIPT)
    page.wait_for_timeout(PRESS_SETTLE_MS)
    # 検証
    assert page.evaluate(MAP_VIEW_SCRIPT) == before


def _node_point(page: Page, item_id: str) -> dict[str, float]:
    """マップの項目の節の中心（画面上の座標）を返す。"""
    return _box_center(page, f'#decision-map button.n-item[data-node="{item_id}"]')


def _press_node(page: Page, item_id: str) -> None:
    """マップの項目の節を押して離し、マウスを節から離す。"""
    _press_at(page, _node_point(page, item_id))
    page.mouse.move(0, 0)


def _locked_ids(page: Page) -> list[str]:
    """ロックした節の ID を返す。"""
    ids: list[str] = page.eval_on_selector_all(LOCKED_NODE, "nodes => nodes.map(n => n.dataset.node)")
    return ids


def _shown_keys(page: Page) -> list[str]:
    """鍵を表示している節の ID を返す。"""
    ids: list[str] = page.evaluate(SHOWN_KEYS_SCRIPT)
    return ids


def test_map_lock_when_open_item_pressed(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """詳細を開いている節を押すとロックして閉じた鍵を出し、もう一度押すとロックを外す。どちらも詳細は開いたまま（正常系）。"""
    # 準備
    page = _open_selected_map(write_sample_preview, open_preview)
    shown_before = _shown_keys(page)
    # 実行（ロックする）
    _press_node(page, "D-2")
    page.wait_for_selector(f'{LOCKED_NODE}[data-node="D-2"]')
    locked = (_locked_ids(page), _shown_keys(page), page.evaluate("location.hash"))
    # 実行（ロックを外す）
    _press_node(page, "D-2")
    page.wait_for_selector(LOCKED_NODE, state="detached")
    # 検証
    assert shown_before == []
    assert locked == (["D-2"], ["D-2"], "#tab=decisions&view=map&id=D-2")
    assert page.locator(f"{KEY} svg.icon").count() == 4
    assert page.evaluate("location.hash") == "#tab=decisions&view=map&id=D-2"
    assert page.locator("aside.panel.open").count() == 1


def test_map_open_when_other_item_pressed(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ロックしていないとき、ほかの節を押すと詳細をその項目に切り替える。ロックはしない（正常系）。"""
    # 準備
    page = _open_selected_map(write_sample_preview, open_preview)
    # 実行
    _press_node(page, "D-3")
    page.wait_for_function("location.hash.includes('id=D-3')")
    # 検証
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    assert _locked_ids(page) == []


def test_map_lock_keeps_node_when_other_opened(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ロック中にほかの節を押すと、詳細だけをその項目に切り替える。ロックした節は閉じた鍵を保ち、押した節には選んだ印だけが付く（正常系）。"""
    # 準備
    page = _open_selected_map(write_sample_preview, open_preview)
    _press_node(page, "D-2")
    page.wait_for_selector(LOCKED_NODE)
    # 実行
    _press_node(page, "D-3")
    page.wait_for_function("location.hash.includes('id=D-3')")
    # 検証
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    assert _locked_ids(page) == ["D-2"]
    assert _shown_keys(page) == ["D-2"]
    assert page.eval_on_selector_all(
        "#decision-map button.n-item.sel", "nodes => nodes.map(n => n.dataset.node)"
    ) == ["D-3"]
    assert page.evaluate("document.getElementById('decision-map').classList.contains('has-lock')")


def test_map_return_to_locked_when_locked_pressed(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ロック中にほかの項目を開いているとき、ロックした節を押すと、詳細をロックした項目に戻すだけにする。ロックは外さない（正常系）。"""
    # 準備
    page = _open_selected_map(write_sample_preview, open_preview)
    _press_node(page, "D-2")
    page.wait_for_selector(LOCKED_NODE)
    _press_node(page, "D-3")
    page.wait_for_function("location.hash.includes('id=D-3')")
    # 実行
    _press_node(page, "D-2")
    page.wait_for_function("location.hash.includes('id=D-2')")
    # 検証
    assert page.inner_text("aside.panel .d-title") == "D-2の題"
    assert _locked_ids(page) == ["D-2"]


def test_map_shake_when_blank_pressed_while_locked(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ロックした項目の詳細を開いているときに余白を押すと、ロック・詳細・表示を変えず、閉じた鍵を約 1 秒震わせる。震えは赤く、収まると元の見た目に戻る（正常系）。"""
    # 準備
    page = _open_selected_map(write_sample_preview, open_preview)
    _press_node(page, "D-2")
    page.wait_for_selector(LOCKED_NODE)
    point = _blank_point(page)
    quiet = page.eval_on_selector(f"{LOCKED_NODE} .lk", "key => key.getAttribute('style')")
    # 実行
    _press_at(page, point)
    page.mouse.move(0, 0)
    page.wait_for_timeout(SHAKE_EARLY_MS)
    shaking = page.eval_on_selector(f"{LOCKED_NODE} .lk", "key => key.getAttribute('style')")
    page.wait_for_timeout(SHAKE_DONE_MS)
    # 検証
    assert quiet is None
    assert shaking is not None
    assert "rotate(" in shaking
    assert "transform-origin: 50% 0" in shaking
    assert page.eval_on_selector(f"{LOCKED_NODE} .lk", "key => key.getAttribute('style')") is None
    assert page.evaluate("location.hash") == "#tab=decisions&view=map&id=D-2"
    assert _locked_ids(page) == ["D-2"]
    assert page.locator("aside.panel.open").count() == 1


def test_map_shake_when_same_other_item_pressed_while_locked(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ロック中に開いている別の項目の節をもう一度押すと、何も変えず、鍵を震わせる（正常系）。"""
    # 準備
    page = _open_selected_map(write_sample_preview, open_preview)
    _press_node(page, "D-2")
    page.wait_for_selector(LOCKED_NODE)
    _press_node(page, "D-3")
    page.wait_for_function("location.hash.includes('id=D-3')")
    page.wait_for_timeout(SHAKE_DONE_MS)
    # 実行
    _press_node(page, "D-3")
    page.wait_for_timeout(SHAKE_EARLY_MS)
    shaking = page.eval_on_selector(f"{LOCKED_NODE} .lk", "key => key.getAttribute('style')")
    # 検証
    assert shaking is not None
    assert page.evaluate("location.hash") == "#tab=decisions&view=map&id=D-3"
    assert _locked_ids(page) == ["D-2"]


def test_map_open_key_when_hovered(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ロックしていないとき、開いた鍵は詳細を開いている節にカーソルを乗せたときだけ出す。押しても何も起きない鍵なので、乗せただけでは詳細もロックも変えない（正常系）。"""
    # 準備
    page = _open_selected_map(write_sample_preview, open_preview)
    page.mouse.move(0, 0)
    away = _shown_keys(page)
    # 実行
    page.mouse.move(_node_point(page, "D-2")["x"], _node_point(page, "D-2")["y"])
    page.wait_for_function("document.querySelector('#decision-map button.n-item.sel:hover') !== null")
    hovered = _shown_keys(page)
    page.mouse.move(_node_point(page, "D-3")["x"], _node_point(page, "D-3")["y"])
    page.wait_for_function("document.querySelector('#decision-map button.n-item.sel:hover') === null")
    other_hovered = _shown_keys(page)
    # 検証
    assert away == []
    assert hovered == ["D-2"]
    assert other_hovered == []
    assert _locked_ids(page) == []
    assert page.evaluate("location.hash") == "#tab=decisions&view=map&id=D-2"


def test_map_lock_stays_when_detail_closed_and_tab_moved(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ロックは詳細を閉じても、タブを行き来しても残り、閉じた鍵を出し続ける。ネットワークのロックとは別に持つ（正常系）。"""
    # 準備
    page = _open_selected_map(write_sample_preview, open_preview)
    _press_node(page, "D-2")
    page.wait_for_selector(LOCKED_NODE)
    # 実行（詳細を閉じる）
    page.keyboard.press("Escape")
    page.wait_for_selector("aside.panel.open", state="detached")
    after_close = (_locked_ids(page), _shown_keys(page))
    # 実行（ネットワークへ移って戻る）
    page.click('nav.tabbar a[data-tab="graph"]')
    page.wait_for_selector("#graph-canvas")
    page.click('nav.tabbar a[data-tab="decisions"]')
    page.click('.segment button[data-view="map"]')
    page.wait_for_selector(LOCKED_NODE)
    # 検証
    assert after_close == (["D-2"], ["D-2"])
    assert _locked_ids(page) == ["D-2"]
    assert _shown_keys(page) == ["D-2"]


def test_map_lock_when_quick_double_press(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """何も選んでいないとき、同じ節を素早く 2 回押すと、1 回目で詳細が開いて枠がずれても、その節への 2 回押しとしてロックする（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    point = _node_point(page, "D-3")
    # 実行
    page.mouse.move(point["x"], point["y"])
    page.mouse.down()
    page.mouse.up()
    page.wait_for_timeout(QUICK_PRESS_GAP_MS)
    page.mouse.down()
    page.mouse.up()
    page.wait_for_selector(LOCKED_NODE)
    # 検証
    assert _locked_ids(page) == ["D-3"]
    assert page.evaluate("location.hash") == "#tab=decisions&view=map&id=D-3"


def test_map_lock_when_narrow(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """幅 900px 以下の字下げの一覧ではロックしない。押した項目を開くだけで、鍵も出さない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    page.set_viewport_size({"width": NARROW_WIDTH, "height": NARROW_HEIGHT})
    page.wait_for_selector("nav.map-outline", state="visible")
    # 実行（開いている項目をもう一度押しても、ロックしない）
    page.click('nav.map-outline button[data-id="D-3"]')
    page.wait_for_selector("aside.panel.open")
    page.click('nav.map-outline button[data-id="D-3"]', force=True)
    page.wait_for_timeout(PRESS_SETTLE_MS)
    # 検証
    assert page.locator(LOCKED_NODE).count() == 0
    assert page.locator("nav.map-outline .lk").count() == 0


def test_map_key_does_not_overlap_comment_mark(
    write_commented_preview: WriteReviewPreview, open_preview: OpenPreview
) -> None:
    """節の鍵は 1 行目の右端、コメントの印は 2 行目の右端に置き、重ならない（正常系）。"""
    # 準備
    url, _ = write_commented_preview()
    page = open_preview(url, "#tab=decisions&view=map&id=D-2")
    page.wait_for_function(SELECTED_MAP_SCRIPT)
    # 実行
    _press_node(page, "D-2")
    page.wait_for_selector(f'{LOCKED_NODE}[data-node="D-2"]')
    boxes = page.evaluate(
        """() => {
            const node = document.querySelector('#decision-map button.n-item.locked');
            const key = node.querySelector('.lk').getBoundingClientRect();
            const mark = node.querySelector('.r2 .cmk').getBoundingClientRect();
            const frame = node.getBoundingClientRect();
            return {
                apart: key.bottom <= mark.top || key.right <= mark.left || mark.right <= key.left,
                keyInside: key.left >= frame.left && key.right <= frame.right && key.top >= frame.top && key.bottom <= frame.bottom,
                keyOnFirstRow: key.top < frame.top + frame.height / 2,
            };
        }"""
    )
    # 検証
    assert boxes == {"apart": True, "keyInside": True, "keyOnFirstRow": True}


def test_map_when_narrow(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """幅が狭いと、マップを字下げの一覧に切り替え、押すと詳細を開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    page.set_viewport_size({"width": NARROW_WIDTH, "height": NARROW_HEIGHT})
    # 実行
    page.wait_for_selector("nav.map-outline", state="visible")
    # 検証
    assert page.is_visible("nav.map-outline")
    assert not page.is_visible("#decision-map")
    page.click('nav.map-outline button[data-id="D-3"]')
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-3の題"


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
        make_item("D-2", status="未決定", depends_on=["D-1"]),
    )
    page = open_preview(url, "#tab=decisions&view=table")
    # 実行
    ready = page.eval_on_selector_all(
        "table.grid tbody tr",
        "rows => rows.map(r => [r.dataset.id, r.querySelector('td[data-col=\"7\"]').textContent])",
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
        "rows => rows.map(r => [r.dataset.id, r.querySelector('td[data-col=\"7\"]').textContent])",
    )
    # 検証
    assert ready == [
        ["D-1", "なし"],
        ["D-2", "着手可能"],
        ["D-3", "なし"],
        ["D-4", "なし"],
        ["D-5", "着手可能"],
    ]
    assert page.inner_text('table.grid thead th[data-col="7"]').strip().startswith("着手可否")
    # 行のタイトルを押すと詳細を開く
    page.click('table.grid button.row-open[data-id="D-4"]')
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-4の題"


def test_map_no_match_note(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """条件に合う検討事項が無いと、幅 901px 以上はマップの枠の中央、900px 以下は字下げの一覧に空の旨を出し、条件を戻すと消す（正常系）。"""
    # 準備（条件に合う検討事項があるときは出さない。記録に無い状態だけを選んで開き直す）
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    shown_before = page.is_visible("p.map-empty")
    page = open_preview(url, "#tab=decisions&view=map&f.status=取り下げ")
    page.wait_for_selector("p.map-empty", state="visible")
    # 検証（広い幅: マップの枠の中央）
    assert shown_before is False
    assert page.inner_text("p.map-empty") == NO_MATCH_TEXT
    assert not page.is_visible("nav.map-outline")
    # 実行（狭い幅へ）
    page.set_viewport_size({"width": NARROW_WIDTH, "height": NARROW_HEIGHT})
    page.wait_for_selector("nav.map-outline", state="visible")
    # 検証（狭い幅: 字下げの一覧）
    assert page.inner_text("nav.map-outline p.empty") == NO_MATCH_TEXT
    assert not page.is_visible("p.map-empty")
    # 実行（条件を 1 つ足すと、空の旨を消す）
    open_drawer(page)
    click_value(page, "status", "未決定")
    page.wait_for_selector('nav.map-outline button[data-id="D-2"]')
    # 検証
    assert page.locator("nav.map-outline p.empty").count() == 0


def test_map_item_id_size(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """マップの項目の 2 行目の ID は、計算後の文字の大きさが 11px 以上である（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    # 実行
    size = map_item_id_font_size(page)
    # 検証
    assert size >= MIN_UI_FONT_SIZE_PX


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


def test_diff_marks_when_map(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """マップの箱に印を置く。狭い幅の字下げの一覧にも同じ印を置く（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    # 検証
    marked = page.eval_on_selector_all(
        "#decision-map .map-node.n-item:has(.df-mark.df-chg)", "nodes => nodes.map(n => n.dataset.node)"
    )
    # 既定で表示する状態（決定済みを除く）の検討事項だけが箱になる
    assert sorted(marked) == ["D-2"]
    # 狭い幅の字下げの一覧
    page.set_viewport_size({"width": 800, "height": 700})
    page.wait_for_selector(".map-outline button[data-id] .df-mark")
    outlined = page.eval_on_selector_all(
        ".map-outline button[data-id]:has(.df-mark.df-chg)", "buttons => buttons.map(b => b.dataset.id)"
    )
    assert sorted(outlined) == ["D-2"]
    assert_topbar_history(page)


@pytest.mark.parametrize(
    ("view", "below"),
    [
        pytest.param("table", "table.grid", id="table"),
        pytest.param("board", ".board", id="board"),
        pytest.param("map", "#decision-map", id="map"),
    ],
)
def test_removed_band(
    write_removed_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    page: Page,
    view: str,
    below: str,
) -> None:
    """差分の表示の間、選んだ時点で消した検討事項を、表示形式によらず一覧の上の帯に ID の順で並べる。押せず、マップの節にもしない（正常系）。"""
    # 準備・実行
    url, _ = write_removed_preview()
    preselect_diff(page, "V-2")
    open_preview(url, f"#tab=decisions&view={view}")
    page.wait_for_selector(below)
    # 検証
    assert_removed_band(page, REMOVED_IN_V2_BY_TAB["decisions"])
    assert_band_above(page, below)
    # 消した検討事項は、マップの節・ボードのカード・表の行にしない
    assert page.locator('[data-node="D-3"], [data-node="D-4"], [data-id="D-3"], [data-id="D-4"]').count() == 0


def test_removed_band_when_outline(
    write_removed_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """マップが幅 900px 以下の字下げの一覧になっても、同じ帯を一覧の上に置く（正常系）。"""
    # 準備
    url, _ = write_removed_preview()
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=decisions&view=map")
    # 実行
    page.set_viewport_size({"width": NARROW_WIDTH, "height": NARROW_HEIGHT})
    page.wait_for_selector(".map-outline")
    # 検証
    assert_removed_band(page, REMOVED_IN_V2_BY_TAB["decisions"])
    assert_band_above(page, ".map-outline")


def test_removed_band_when_filtered(
    write_removed_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """絞り込みの条件で一覧の行が 0 件になっても、消した項目は絞り込まず全て帯に出す（正常系）。"""
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
    assert [group["label"] for group in groups] == [
        "状態",
        "システム",
        "カテゴリー",
        "フェーズ",
        "影響度",
        "着手可否",
    ]
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
    """マップ・ボード・表を切り替えても、ドロワーで選んだ条件を保つ（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    open_drawer(page)
    click_value(page, "status", "決定済み")
    page.wait_for_selector('#decision-map button[data-node="D-1"]')
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
    """見出しの ×・下端の「{件数} 件を表示」・ドロワーの中の Esc・絞り込みのボタンで閉じ、閉じたら絞り込みのボタンへフォーカスを戻す。外側を押しても閉じない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    focused: list[str | None] = []
    # 実行（外側を押しても閉じない）
    open_drawer(page)
    page.mouse.click(900, 500)
    still_open = page.locator(DRAWER_OPEN).count()
    # 実行（×・下端のボタン・Esc で閉じる）
    for close in (
        lambda: page.click(f"{DRAWER} button[aria-label='絞り込みを閉じる']"),
        lambda: page.click(f"{DRAWER} .fd-foot .btn.primary"),
        lambda: page.keyboard.press("Escape"),
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
    # 検証
    assert still_open == 1
    assert focused == ["filter", "filter", "filter"]


def test_drawer_clear(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """条件ごとの「解除」でその条件の選びを外し、下端の「すべて解除」で全ての条件を外す。バッジは値を選んでいる条件の数に追従する（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    open_drawer(page)
    click_value(page, "phase", "要件")
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
    assert after_clear_status == ("1", None, ["D-2", "D-3"])
    assert after_clear_all == (None, {"count": "5 件", "foot": ["5 件を表示"]}, ["D-1", "D-2", "D-3", "D-4", "D-5"])


def test_drawer_tags(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """タグの条件を状態の次に並べ、選ぶとそのタグを持つ検討事項に絞る。表のチップで解除できる（正常系）。"""
    # 準備
    url = write_preview(
        make_item("D-1", status="未決定", tags=["プレビュー"]),
        make_item("D-2", status="未決定", tags=["サーバー", "プレビュー"]),
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
    # 準備（フェーズ「目的」だけを選んで開く。目的は決定済みの D-1 だけ）
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&f.phase=目的")
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
        ["未決定", 0, False],
        ["保留", 0, False],
        ["決定済み", 1, False],
    ]
    assert zero_values == ["要見直し", "未決定", "保留"]
    assert checked_values(page, "status") == ["未決定"]


def test_drawer_keyword_hits(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """マップでキーワードを入れると、ドロワーの値の件数の左に、キーワードに一致した件数を出す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    open_drawer(page)
    # 実行
    page.fill("input.map-q", "D-2")
    page.wait_for_selector(f"{DRAWER} .hit-n")
    hits = page.eval_on_selector_all(
        f'{DRAWER} .fd-opt:has(input[data-key="status"]):has(.hit-n)',
        "opts => opts.map(o => [o.querySelector('.fd-v').textContent, o.querySelector('.hit-n').textContent, o.querySelector('.hit-n').getAttribute('aria-label')])",
    )
    # 検証
    assert hits == [["未決定", "1", "キーワードに一致した項目 1 件"]]


def test_drawer_hash_filter(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ハッシュの `f.{列}` で開くと、開いたときの既定の条件に代えてその条件だけを選んだ状態でドロワーに入り、バッジが付き、ハッシュからは消える（正常系）。"""
    # 準備・実行
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&f.phase=要件")
    open_drawer(page)
    groups = {group["label"]: group for group in drawer_groups(page)}
    # 検証
    assert _table_row_ids(page) == ["D-2", "D-3"]
    assert badge_text(page) == "1"
    assert checked_values(page, "phase") == ["要件"]
    assert checked_values(page, "status") == []
    assert groups["フェーズ"]["sel"] == "1 件を選択"
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
    # 検証（先頭の文字の欄へフォーカスを移す。条件のまとまりは「文字を含む」と値を選ぶ 6 つ）
    assert structure == {"groups": 7, "checkboxes": True, "counts": "1 件", "firstFocused": True}
    assert page.locator(selector).count() == 1


@pytest.mark.parametrize("view", ["map", "board"])
def test_chips(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, view: str
) -> None:
    """マップ・ボードのツールバーの下に条件のチップの行を置き、× で 1 つ解除し、「すべて解除」で全ての条件を外す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, f"#tab=decisions&view={view}")
    shown = "#decision-map .map-node.n-item" if view == "map" else ".board .card"
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


def test_comment_marks_when_map(
    write_commented_preview: WriteReviewPreview, open_preview: OpenPreview
) -> None:
    """マップの節点は 268×48 で、2 行目の右端に印を出す。印の有無で節点の幅を変えない（正常系）。"""
    # 準備・実行
    url, _ = write_commented_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    # 検証
    assert marks_of(page, "#decision-map") == SCREEN_MARKS["decisions"]
    sizes = page.eval_on_selector_all(
        "#decision-map .map-node.n-item",
        "nodes => nodes.map(n => [n.dataset.node, n.offsetWidth, n.offsetHeight])",
    )
    assert sorted(sizes) == [
        ["D-2", MAP_NODE_WIDTH, MAP_NODE_HEIGHT],
        ["D-3", MAP_NODE_WIDTH, MAP_NODE_HEIGHT],
        ["D-4", MAP_NODE_WIDTH, MAP_NODE_HEIGHT],
        ["D-5", MAP_NODE_WIDTH, MAP_NODE_HEIGHT],
    ]
    # 印は 2 行目（メタ情報）の右端にあり、節点の中に収まる
    inside = page.evaluate(
        """() => [...document.querySelectorAll('#decision-map .map-node.n-item .r2 .cmk')].every(mark => {
            const node = mark.closest('.map-node').getBoundingClientRect();
            const box = mark.getBoundingClientRect();
            return box.left >= node.left && box.right <= node.right && box.top >= node.top && box.bottom <= node.bottom;
        })"""
    )
    assert inside is True
    assert page.locator("#decision-map .map-node .r2 .cmk").count() == 2


def test_comment_marks_when_outline(
    write_commented_preview: WriteReviewPreview, open_preview: OpenPreview
) -> None:
    """幅 900px 以下の字下げの一覧は、行のタイトルの右に印を出す（正常系）。"""
    # 準備
    url, _ = write_commented_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    # 実行
    page.set_viewport_size({"width": NARROW_WIDTH, "height": NARROW_HEIGHT})
    page.wait_for_selector(".map-outline button[data-id] .cmk")
    # 検証
    assert marks_of(page, ".map-outline") == SCREEN_MARKS["decisions"]
    last = page.eval_on_selector(
        '.map-outline button[data-id="D-2"]',
        "b => b.lastElementChild.matches('.cmk-place') && b.lastElementChild.querySelector('.cmk') !== null",
    )
    assert last is True


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
REGION_SCROLLER = {"board": ".board", "table": ".table-wrap", "map": ".map-wrap"}


def _write_many_decisions(write_preview: WritePreview, make_item: MakeItem) -> str:
    """領域の高さを超える数の未決定の検討事項を持つ配信の URL を返す。"""
    return write_preview(
        *(
            make_item(f"D-{number}", status="未決定", title=f"検討事項の題 {number}")
            for number in range(1, MANY_DECISIONS + 1)
        )
    )


@pytest.mark.parametrize("view", ["board", "table", "map"])
def test_region_when_wide(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem, view: str
) -> None:
    """幅が広いとき、ページ全体はスクロールせず、帯は見えたままで、ボード・表・マップは領域の高さいっぱいに広がって中でスクロールする（正常系）。"""
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


def test_map_middle_labels(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """マップの中間の層のラベルは、カテゴリーが面と線と太字、フェーズが地の色の面と薄い線と小さい文字で、描く要素の class に当たっている（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    page.set_viewport_size(WIDE_VIEWPORT)
    page.wait_for_selector("#decision-map .map-node.n-category")
    # 実行
    styles = page.evaluate(
        """() => {
            const read = (selector) => {
                const style = getComputedStyle(document.querySelector(selector));
                return {
                    background: style.backgroundColor,
                    border: style.borderTopWidth + ' ' + style.borderTopStyle,
                    weight: Number(style.fontWeight),
                    size: parseFloat(style.fontSize),
                };
            };
            const probeBackground = (name) => {
                const element = document.createElement('i');
                element.style.backgroundColor = `var(${name})`;
                document.body.append(element);
                const color = getComputedStyle(element).backgroundColor;
                element.remove();
                return color;
            };
            return {
                category: read('#decision-map .n-category'),
                phase: read('#decision-map .n-phase'),
                surface: probeBackground('--surface'),
                bg: probeBackground('--bg'),
            };
        }"""
    )
    # 検証
    assert styles["category"]["background"] == styles["surface"]
    assert styles["category"]["border"] == "1px solid"
    assert styles["category"]["weight"] >= 600
    assert styles["phase"]["background"] == styles["bg"]
    assert styles["phase"]["border"] == "1px solid"
    # フェーズはカテゴリーより小さい文字
    assert styles["phase"]["size"] < styles["category"]["size"]


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
    """文字の条件はマップ・ボード・表で共有し、表示形式を切り替えても保つ。空にすると外れる（正常系）。"""
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
    *[(view, width, filled) for view in ("board", "table") for width, filled in TABLE_BOARD_BOUNDARY_WIDTHS],
    *[("map", width, filled) for width, filled in MAP_BOUNDARY_WIDTHS],
])
def test_region_at_boundary(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    view: str,
    width: int,
    filled: bool,
) -> None:
    """領域の高さいっぱいに広げる境（表・ボードは 721px、マップは 901px）の前後の幅で、広げるか領域ごとスクロールするかが切り替わる（正常系）。"""
    # 準備
    url = _write_many_decisions(write_preview, make_item)
    page = open_preview(url, f"#tab=decisions&view={view}")
    page.set_viewport_size({"width": width, "height": BOUNDARY_HEIGHT})
    # マップは 900px 以下だと字下げの一覧になるので、そのときは領域を指す
    selector = REGION_SCROLLER[view] if filled or view != "map" else ".map-outline"
    page.wait_for_selector(selector)
    # 実行・検証
    if view == "map" and not filled:
        metrics = region_metrics(page)
        assert_page_does_not_scroll(page)
        assert metrics["content"]["scrollHeight"] > metrics["content"]["clientHeight"]
        assert_bands_stay(page)
    else:
        assert_region_mode(page, selector, filled=filled)


def test_drawer_saved_filter(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """サーバーの配信では、条件を変えるたびに端末へ残し、読み込み直しても開いたときの既定に代えてその条件でドロワーと表を開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    open_drawer(page)
    click_value(page, "phase", "要件")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr[data-id]').length === 2")
    # 実行
    reload_preview(page)
    open_drawer(page)
    # 検証
    assert read_saved_filters(page) == {
        "decisions": {"status": DEFAULT_DECISION_STATUSES, "phase": ["要件"]}
    }
    assert _table_row_ids(page) == ["D-2", "D-3"]
    assert badge_text(page) == "2"
    # サンプルの検討事項に未整理は無いので、残した状態の条件から外して開く
    assert checked_values(page, "status") == ["要見直し", "未決定", "保留"]
    assert checked_values(page, "phase") == ["要件"]


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
    reopen_preview(page, url, "#tab=decisions&view=table&f.phase=要件")
    open_drawer(page)
    # 検証
    assert _table_row_ids(page) == ["D-2", "D-3"]
    assert checked_values(page, "phase") == ["要件"]
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
