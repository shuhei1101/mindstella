"""画面設計『ネットワーク』（キャンバスは項目 ID `graph-canvas`）の結合テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page
from preview_drawer_helpers import (
    DRAWER,
    badge_text,
    checked_values,
    chip_texts,
    click_value,
    close_drawer,
    drawer_groups,
    drawer_head,
    open_drawer,
    remove_chip,
)
from preview_fixture_types import OpenPreview, WritePreview, WriteReviewPreview, WriteSamplePreview
from preview_history_helpers import assert_topbar_history, preselect_diff
from preview_layout_helpers import (
    WIDE_VIEWPORT,
    assert_bands_stay,
    assert_page_does_not_scroll,
    region_metrics,
)
from preview_mark_helpers import MARK_TIMEOUT_MS
from preview_network_helpers import (
    ball_at,
    blank_point,
    ball_centers,
    canvas_center,
    canvas_hash,
    changed_pixels,
    click_at,
    install_key_spy,
    install_status_mark_spy,
    is_moving,
    key_draws,
    nearest_ball,
    other_ball,
    remember_pixels,
    settle,
    status_marks,
)
from preview_settings_helpers import LOOK_SELECT, pick_look, read_prefs
from workspace_fixtures import MakeItem

# 狭い幅の画面の大きさ（空の旨の文はどの幅でも出す）
NARROW_WIDTH = 800
NARROW_HEIGHT = 700

# 絞り込みの条件に合う項目が無いときに出す文
NO_MATCH_TEXT = "表示する項目はありません。"

# 項目の種類の値の並び（検討事項・タスク・調査・資料・用語集・メモ・会話ログ）
KIND_LABELS = ["検討事項", "タスク", "調査", "資料", "用語集", "メモ", "会話ログ"]

# キャンバスに描かれた画素のうち、背景以外が 1 つでもあるかを調べる
HAS_DRAWING_SCRIPT = """() => {
    const canvas = document.getElementById('graph-canvas');
    const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    for (let i = 3; i < data.length; i += 4) if (data[i] !== 0) return true;
    return false;
}"""


def test_canvas(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """3D のキャンバスに全種類の項目と関連を描く（正常系）。"""
    # 準備
    url = write_sample_preview()
    # 実行
    page = open_preview(url, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    # 検証
    assert page.get_attribute("#graph-canvas", "role") == "img"
    # 読み上げの説明に、L キーでロックを付け外しできることを添える
    assert "L キーで、詳細を開いている項目をロック・解除" in page.get_attribute("#graph-canvas", "aria-label")
    assert page.inner_text("main h1") == "ネットワーク"
    assert page.get_attribute('nav.tabbar a[data-tab="graph"]', "aria-current") == "page"
    # 種類の帯は出さない
    assert page.locator(".legend").count() == 0


def test_drawer_type(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ドロワーの種類（項目の種類）の値を選ぶと、その種類の玉だけを描く。何も選んでいない状態で開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    # 実行
    open_drawer(page)
    groups = {group["label"]: group for group in drawer_groups(page)}
    initial = (badge_text(page), drawer_head(page)["count"])
    click_value(page, "type", "会話ログ")
    page.wait_for_function("document.querySelector('dialog.drawer .fd-count').textContent === '14 件中 1 件'")
    # 検証
    assert list(groups)[:2] == ["種類", "状態"]
    assert [value[0] for value in groups["種類"]["values"]] == KIND_LABELS
    assert [value[1] for value in groups["種類"]["values"]] == [5, 3, 1, 2, 1, 1, 1]
    assert all(value[2] is False for value in groups["種類"]["values"])
    assert initial == (None, "14 件")
    assert checked_values(page, "type") == ["会話ログ"]
    assert badge_text(page) == "1"
    # 種類の値には、種類の色の点を添える
    assert page.locator(f"{DRAWER} .fd-group:first-of-type .fd-opt .kdot").count() == len(KIND_LABELS)


def test_drawer_status(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ドロワーの状態は、検討事項・タスク・資料の状態を並べ、選ぶと状態を持たない種類の玉を外す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    open_drawer(page)
    groups = {group["label"]: group for group in drawer_groups(page)}
    # 実行
    click_value(page, "status", "完成")
    page.wait_for_function("document.querySelector('dialog.drawer .fd-count').textContent === '14 件中 1 件'")
    # 検証
    assert [value[0] for value in groups["状態"]["values"]] == [
        "要見直し",
        "未決定",
        "保留",
        "決定済み",
        "未着手",
        "進行中",
        "完了",
        "下書き",
        "完成",
    ]
    assert checked_values(page, "status") == ["完成"]
    # 種類の値の件数は、状態で絞った項目で数え直す（資料の 1 件だけ）
    counts = {value[0]: value[1] for value in drawer_groups(page)[0]["values"]}
    assert counts["資料"] == 1
    assert counts["メモ"] == 0


def test_open_item_from_hash(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ハッシュの id で項目を選ぶと、詳細パネルを開いたままキャンバスを保つ（正常系）。"""
    # 準備
    url = write_sample_preview()
    # 実行
    page = open_preview(url, "#tab=graph&id=D-2")
    page.wait_for_selector("aside.panel.open")
    # 検証
    assert page.inner_text("aside.panel .d-title") == "D-2の題"
    assert page.locator("#graph-canvas").count() == 1


def test_no_match_note(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """条件に合う項目が無いと、どの幅でも枠の中央に空の旨を出す。条件を 1 つ外して項目が合うようになると消す（正常系）。"""
    # 準備（条件に合う項目があるときは出さない。種類が会話ログで、状態が完成の項目は無い）
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    shown_before = page.is_visible("p.map-empty")
    page = open_preview(url, "#tab=graph&f.type=会話ログ&f.status=完成")
    page.wait_for_selector("p.map-empty", state="visible")
    # 検証（広い幅）
    assert shown_before is False
    assert page.inner_text("p.map-empty") == NO_MATCH_TEXT
    # 実行（狭い幅へ）
    page.set_viewport_size({"width": NARROW_WIDTH, "height": NARROW_HEIGHT})
    page.wait_for_selector("p.map-empty", state="visible")
    # 検証（狭い幅）
    assert page.inner_text("p.map-empty") == NO_MATCH_TEXT
    # 実行（状態の条件を解除する）
    open_drawer(page)
    page.click(f"{DRAWER} button[aria-label='状態の条件を解除']")
    page.wait_for_selector("p.map-empty", state="hidden")
    # 検証
    assert page.is_visible("p.map-empty") is False


def test_topbar_history(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """ネットワークでも、トップバーに「変更履歴」のボタンと選んだ時点の札を出し、玉と線には印を付けない（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=graph")
    page.wait_for_selector("#graph-canvas")
    # 検証
    assert_topbar_history(page)
    assert page.locator("main .df-mark").count() == 0


def test_chips(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """キャンバスの上に条件のチップの行を置き、× で解除するとドロワーの選びとキャンバスを戻す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    open_drawer(page)
    click_value(page, "type", "会話ログ")
    close_drawer(page)
    # 実行
    chips = chip_texts(page)
    above_canvas = page.evaluate(
        "document.querySelector('.screen.graph .chips').getBoundingClientRect().bottom <= document.getElementById('graph-canvas').getBoundingClientRect().top"
    )
    remove_chip(page, "種類: 会話ログ")
    page.wait_for_function("document.querySelectorAll('.chips').length === 0")
    open_drawer(page)
    # 検証
    assert chips == ["種類: 会話ログ"]
    assert above_canvas is True
    assert checked_values(page, "type") == []
    assert badge_text(page) is None
    assert drawer_head(page)["count"] == "14 件"



def test_look(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ネットワークの見た目の値をキャンバスの入れ物に渡す。個人の上書きもワークスペースの既定も無いときは深宇宙（正常系）。"""
    # 準備
    url = write_sample_preview()
    # 実行
    page = open_preview(url, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    # 検証
    assert page.get_attribute(".screen.graph", "data-look") == "deep"


# 描いている名前の横の印のうち、見せているものの画面の数字と外形を、キャンバスの外形とともに返す（隠している印は含めない）
VISIBLE_MARKS_SCRIPT = """() => {
    const canvas = document.getElementById('graph-canvas').getBoundingClientRect();
    const marks = [...document.querySelectorAll('.g3-marks .cmk')]
        .filter(mark => mark.style.visibility !== 'hidden')
        .map(mark => {
            const box = mark.getBoundingClientRect();
            return {count: mark.querySelector('.cmk-n').textContent, left: box.left, top: box.top, right: box.right, bottom: box.bottom};
        });
    return {canvas: {left: canvas.left, top: canvas.top, right: canvas.right, bottom: canvas.bottom}, marks};
}"""

# 近づく前の、全体を表示した距離で印が出ないことを確かめる待ち（ミリ秒。玉が広がる 1.4 秒より長く）
FIT_SETTLE_MS = 2_500

# 近づいた後に視点が寄り終わるまで待つミリ秒
ZOOM_SETTLE_MS = 700

# 回して視点を変える回数と、1 回に動かす横の量（px）、動かし始める点（キャンバスの上の点）
EDGE_SAMPLES = 8
EDGE_DRAG_DX = 40
EDGE_DRAG_START = {"x": 120, "y": 300}


def _visible_marks(page: Page) -> dict[str, Any]:
    """見せている名前の横の印を、キャンバスの外形とともに返す。"""
    result: dict[str, Any] = page.evaluate(VISIBLE_MARKS_SCRIPT)
    return result


def test_comment_marks_when_far(
    write_commented_preview: WriteReviewPreview, open_preview: OpenPreview
) -> None:
    """全体を表示した距離では、名前が読める大きさにならないので印を出さない（正常系）。"""
    # 準備・実行
    url, _ = write_commented_preview()
    page = open_preview(url, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    page.wait_for_timeout(FIT_SETTLE_MS)
    # 検証
    assert _visible_marks(page)["marks"] == []
    assert page.get_attribute("#graph-canvas", "role") == "img"


def test_comment_marks_when_near(
    write_commented_preview: WriteReviewPreview, open_preview: OpenPreview
) -> None:
    """名前が読める大きさまで寄ると、件数のある玉の名前の右に印を出し、印はキャンバスに収まる。印だけを押す操作は持たない（正常系）。"""
    # 準備・実行
    url, _ = write_commented_preview()
    page = open_preview(url, "#tab=graph&id=D-2")
    page.wait_for_function(
        "[...document.querySelectorAll('.g3-marks .cmk')].some(m => m.style.visibility !== 'hidden')",
        timeout=MARK_TIMEOUT_MS,
    )
    # 検証
    shown = _visible_marks(page)
    canvas = shown["canvas"]
    # 選んだ玉の件数 2 の印が出て、出た印はどれも件数のある項目のもの（1 件か 2 件）
    assert "2" in [mark["count"] for mark in shown["marks"]]
    assert {mark["count"] for mark in shown["marks"]} <= {"1", "2"}
    for mark in shown["marks"]:
        assert canvas["left"] <= mark["left"] and mark["right"] <= canvas["right"]
        assert canvas["top"] <= mark["top"] and mark["bottom"] <= canvas["bottom"]
    # 印を重ねる層は押下をキャンバスへ通す
    assert page.eval_on_selector(".g3-marks", "e => getComputedStyle(e).pointerEvents") == "none"
    assert page.locator(".g3-marks button, .g3-marks a").count() == 0


@pytest.mark.parametrize(
    "viewport",
    [
        pytest.param(None, id="desktop"),
        pytest.param({"width": 390, "height": 844}, id="phone"),
    ],
)
def test_comment_marks_when_edge(
    write_commented_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    viewport: dict[str, int] | None,
) -> None:
    """寄ったまま回して縁に玉がかかっても、見せている印はどれもキャンバスに収まる（正常系）。"""
    # 準備（件数のある項目を選び、名前が読める大きさまで寄せる。狭い幅では周りの玉が縁にかかる）
    url, _ = write_commented_preview()
    page = open_preview(url, "#tab=graph&id=D-2")
    if viewport is not None:
        page.set_viewport_size(viewport)
    page.wait_for_function(
        "[...document.querySelectorAll('.g3-marks .cmk')].some(m => m.style.visibility !== 'hidden')",
        timeout=MARK_TIMEOUT_MS,
    )
    # 実行（寄ったまま回し、視点を変えるたびに出ている印を集める）
    seen: list[dict[str, Any]] = []
    for step in range(EDGE_SAMPLES):
        page.mouse.move(EDGE_DRAG_START["x"], EDGE_DRAG_START["y"])
        page.mouse.down()
        page.mouse.move(EDGE_DRAG_START["x"] + EDGE_DRAG_DX * (step + 1), EDGE_DRAG_START["y"], steps=5)
        page.mouse.up()
        page.wait_for_timeout(ZOOM_SETTLE_MS)
        seen.append(_visible_marks(page))
    # 検証（見せている印は、どの視点でも描く枠がキャンバスに収まる）
    assert any(sample["marks"] for sample in seen)
    for sample in seen:
        canvas = sample["canvas"]
        for mark in sample["marks"]:
            assert canvas["left"] <= mark["left"] and mark["right"] <= canvas["right"]
            assert canvas["top"] <= mark["top"] and mark["bottom"] <= canvas["bottom"]


def test_region(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """3D のキャンバスは領域の高さいっぱいに広がり、ページ全体はスクロールせず、帯は見えたまま（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph")
    page.set_viewport_size(WIDE_VIEWPORT)
    page.wait_for_selector("#graph-canvas")
    # 実行
    metrics = region_metrics(page, "#graph-canvas")
    # 検証
    assert_page_does_not_scroll(page)
    # キャンバスの底は領域の底の近くにある（領域の下の余白の分だけ内側）
    assert metrics["content"]["bottom"] - metrics["target"]["bottom"] <= 80
    assert metrics["target"]["bottom"] - metrics["target"]["top"] >= 360
    assert_bands_stay(page)


def test_drawer_has_no_text_fields(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ネットワークの絞り込みのドロワーには、文字の欄を出さない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph")
    # 実行
    open_drawer(page)
    # 検証
    assert page.locator(f"{DRAWER} .fd-text").count() == 0


# 5 つの見た目（値と、ドロップダウンに出す名前）
LOOKS = {
    "glow": "グロウ",
    "starlight": "星の光",
    "constellation": "星図",
    "deep": "深宇宙",
    "dust": "星屑",
}

# 見た目のドロップダウンを置く、キャンバスの端からの余白の上限（CSS ピクセル）
LOOK_PICK_EDGE_PX = 40

# 見た目のドロップダウンの大きさを比べる画面の幅
LOOK_PICK_WIDTHS = [1280, 800, 390]

# 見た目の描き直しなど、動きを減らす設定では止まる動きが 2 回の読み取りの間に出るのを待つミリ秒
MOTION_GAP_MS = 700

# 玉が広がり終わるまで待つミリ秒（開いたときは中心から 1.4 秒かけて広がる）
INTRO_MS = 2_500

# 絵が変わったと見なす違う画素の数の下限と、変わっていないと見なす上限
CHANGED_AT_LEAST = 30
UNCHANGED_AT_MOST = 5


def _reduce_motion(page: Page) -> None:
    """動きを減らす設定にする（星のまたたき・広がる輪・自動の回転が止まり、画が静止する）。"""
    page.emulate_media(reduced_motion="reduce")


def test_look_dropdown(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """見た目のドロップダウンは、キャンバスの右上に重ね、5 つの見た目を決まった順に並べて既定に「（既定）」を添える。アイコンは付けず、読み上げの名前は「ネットワークの見た目」で、面の色で塗る（正常系）。"""
    # 準備・実行
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    canvas = page.locator("#graph-canvas").bounding_box()
    select = page.locator(LOOK_SELECT).bounding_box()
    options = page.eval_on_selector_all(
        f"{LOOK_SELECT} option", "items => items.map(o => o.textContent)"
    )
    background = page.eval_on_selector(LOOK_SELECT, "e => getComputedStyle(e).backgroundColor")
    # 検証
    assert canvas is not None and select is not None
    assert options == ["グロウ", "星の光", "星図", "深宇宙（既定）", "星屑"]
    assert page.eval_on_selector(LOOK_SELECT, "e => e.value") == "deep"
    assert page.get_by_role("combobox", name="ネットワークの見た目").count() == 1
    assert page.locator(".look-pick svg").count() == 0
    # キャンバスの右上に収まる
    assert canvas["x"] + canvas["width"] - (select["x"] + select["width"]) <= LOOK_PICK_EDGE_PX
    assert select["y"] - canvas["y"] <= LOOK_PICK_EDGE_PX
    assert select["x"] >= canvas["x"] and select["y"] >= canvas["y"]
    # どの地の上でも読めるよう、面の色で塗る（透明でない）
    assert background != "rgba(0, 0, 0, 0)"


def test_look_dropdown_when_narrow(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """見た目のドロップダウンは、狭い幅でも同じ大きさで右上に置く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    sizes: list[tuple[float, float]] = []
    corners: list[tuple[bool, bool]] = []
    # 実行（幅を変えながら、大きさと隅の位置を控える）
    for width in LOOK_PICK_WIDTHS:
        page.set_viewport_size({"width": width, "height": NARROW_HEIGHT})
        page.wait_for_function(f"innerWidth === {width}")
        select = page.locator(LOOK_SELECT).bounding_box()
        canvas = page.locator("#graph-canvas").bounding_box()
        assert select is not None and canvas is not None
        sizes.append((round(select["width"]), round(select["height"])))
        corners.append(
            (
                canvas["x"] + canvas["width"] - (select["x"] + select["width"]) <= LOOK_PICK_EDGE_PX,
                select["y"] - canvas["y"] <= LOOK_PICK_EDGE_PX,
            )
        )
    # 検証
    assert len(set(sizes)) == 1
    assert corners == [(True, True)] * len(LOOK_PICK_WIDTHS)


def test_look_pick(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """見た目を選ぶと、玉と線を作り直さずその見た目で描き、視点・選んだ項目は変えない。個人の上書きとして端末に残し、サーバーへは送らない（正常系）。"""
    # 準備
    _reduce_motion(page)
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph&id=D-2")
    page.wait_for_selector("aside.panel.open")
    page.evaluate("window.__canvasBefore = document.getElementById('graph-canvas')")
    page.mouse.move(*_blank(page))
    settle(page)
    remember_pixels(page, "before")
    requests: list[str] = []
    page.on("request", lambda request: requests.append(f"{request.method} {request.url}"))
    # 実行
    pick_look(page, "dust")
    settle(page)
    # 検証
    assert page.get_attribute(".screen.graph", "data-look") == "dust"
    assert changed_pixels(page, "before") > CHANGED_AT_LEAST
    # キャンバスの要素は作り直さない
    assert page.evaluate("window.__canvasBefore === document.getElementById('graph-canvas')")
    # 選んだ項目と詳細パネルは変えない
    assert page.evaluate("location.hash") == "#tab=graph&id=D-2"
    assert page.inner_text("aside.panel .d-title") == "D-2の題"
    prefs = read_prefs(page)
    assert prefs is not None
    assert prefs["look"] == "dust"
    assert [request for request in requests if request.startswith(("PUT", "POST"))] == []


def _blank(page: Page) -> tuple[float, float]:
    """キャンバスの右下の隅の点（玉に当たらない余白）の画面の座標を返す。"""
    box = page.locator("#graph-canvas").bounding_box()
    assert box is not None
    return box["x"] + box["width"] - 12, box["y"] + box["height"] - 12


def _hashes_of_looks(page: Page) -> dict[str, str]:
    """5 つの見た目を順に当て、それぞれの絵を表す文字列を返す。"""
    hashes: dict[str, str] = {}
    for look in LOOKS:
        pick_look(page, look)
        page.wait_for_timeout(MOTION_GAP_MS)
        hashes[look] = canvas_hash(page)
    return hashes


def test_looks_differ(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """5 つの見た目は、同じ記録を互いに違う絵で描き、ライトとダークでも絵を変える（正常系）。"""
    # 準備
    _reduce_motion(page)
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    page.mouse.move(*_blank(page))
    settle(page)
    # 実行
    page.evaluate("document.documentElement.dataset.theme = 'dark'")
    dark = _hashes_of_looks(page)
    page.evaluate("document.documentElement.dataset.theme = 'light'")
    light = _hashes_of_looks(page)
    # 検証
    assert len(set(dark.values())) == len(LOOKS)
    assert len(set(light.values())) == len(LOOKS)
    assert [dark[look] != light[look] for look in LOOKS] == [True] * len(LOOKS)


@pytest.mark.parametrize("look", list(LOOKS))
def test_motion_when_reduced(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page, look: str
) -> None:
    """動きを減らす設定のとき、どの見た目でも、自分で動くもの（またたき・広がる輪・自動の回転）を止めて画を静止させる（正常系）。"""
    # 準備
    _reduce_motion(page)
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    pick_look(page, look)
    page.wait_for_timeout(INTRO_MS)
    # 実行
    first = canvas_hash(page)
    page.wait_for_timeout(MOTION_GAP_MS)
    second = canvas_hash(page)
    # 検証
    assert first == second


@pytest.mark.parametrize("look", list(LOOKS))
def test_motion_when_not_reduced(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, look: str
) -> None:
    """動きを減らす設定でないとき、どの見た目でも、星のまたたきなど自分で動くもので画が変わり続ける（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    pick_look(page, look)
    page.wait_for_timeout(INTRO_MS)
    # 実行
    first = canvas_hash(page)
    page.wait_for_timeout(MOTION_GAP_MS)
    second = canvas_hash(page)
    # 検証
    assert first != second


def test_motion_follows_setting(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """動きを減らす設定が開いたまま変わっても、次のコマから当てる。止めた画は動かず、戻すとまた動く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    page.wait_for_timeout(INTRO_MS)
    # 実行（動く → 止める → 戻す）
    moving = is_moving(page)
    _reduce_motion(page)
    # 止めた直後は、視点と濃さが目標へ寄り終わるまで動くので、画が止まってから比べる
    settle(page)
    still = is_moving(page)
    page.emulate_media(reduced_motion="no-preference")
    page.wait_for_timeout(MOTION_GAP_MS)
    back = is_moving(page)
    # 検証
    assert moving is True
    assert still is False
    assert back is True


# 鍵を描く領域（キャンバスの中心まわり）で、鍵の有無を区別できる違う画素の数の下限
KEY_PIXELS_AT_LEAST = 30

# 鍵の震えを確かめるまでの時間と、収まるまでの時間（ミリ秒。震えは約 1 秒）
SHAKE_EARLY_MS = 250

# 状態の印を数える前に待つミリ秒（玉が広がり、印の画像が読み込まれるまで）
MARK_WAIT_MS = 3_000

# 詳細を開いている項目の状態の印は、その項目と前提・後続の項目の分まで（D-2 は D-1・D-4・T-1 とつながる）
NEAR_ITEMS_OF_D2 = 4

# キャンバスの要素
CANVAS_SELECTOR = "#graph-canvas"


def _open_still(open_preview: OpenPreview, url: str, hash_text: str, page: Page) -> Page:
    """動きを減らす設定で項目を開いたネットワークを、マウスを余白に置いたまま静止するまで待って返す。"""
    _reduce_motion(page)
    opened = open_preview(url, hash_text)
    opened.wait_for_selector("aside.panel.open")
    opened.mouse.move(*blank_point(opened))
    settle(opened)
    return opened


def _press_ball(page: Page, x: float, y: float) -> None:
    """玉（か余白）を押し、マウスを余白へ戻して、画が静止するまで待つ。"""
    click_at(page, x, y)
    page.mouse.move(*blank_point(page))
    settle(page)


def _hash(page: Page) -> str:
    """URL のハッシュを返す。"""
    value: str = page.evaluate("location.hash")
    return value


def test_lock_toggle(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """詳細を開いている項目の玉を押すとロックして閉じた鍵を出し、もう一度押すとロックを外して鍵が消える。どちらも詳細は開いたまま（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = _open_still(open_preview, url, "#tab=graph&id=D-2", page)
    remember_pixels(page, "free")
    cx, cy = canvas_center(page)
    # 実行（ロックする）
    _press_ball(page, cx, cy)
    locked = changed_pixels(page, "free")
    # 実行（ロックを外す）
    _press_ball(page, cx, cy)
    unlocked = changed_pixels(page, "free")
    # 検証
    assert locked >= KEY_PIXELS_AT_LEAST
    assert unlocked <= UNCHANGED_AT_MOST
    assert _hash(page) == "#tab=graph&id=D-2"
    assert page.locator("aside.panel.open").count() == 1


def test_lock_holds_when_other_pressed(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """ロック中にほかの玉を押すと、詳細だけをその項目に切り替え、中心と強調をロックした項目に留める。ロックした玉を押すと、詳細をロックした項目に戻すだけで、ロックは外さない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = _open_still(open_preview, url, "#tab=graph&id=D-2", page)
    cx, cy = canvas_center(page)
    _press_ball(page, cx, cy)
    remember_pixels(page, "locked")
    ox, oy = other_ball(page)
    # 実行（ほかの玉を押す）
    _press_ball(page, ox, oy)
    after_other = (_hash(page), page.inner_text("aside.panel .d-title"))
    held = ball_at(page, *canvas_center(page))
    # 実行（ロックした玉を押す）
    _press_ball(page, *canvas_center(page))
    # 検証
    assert after_other[0] != "#tab=graph&id=D-2"
    assert after_other[1] != "D-2の題"
    assert held is True
    assert _hash(page) == "#tab=graph&id=D-2"
    assert page.inner_text("aside.panel .d-title") == "D-2の題"
    # ロックは外れておらず、閉じた鍵のままの絵に戻る
    assert changed_pixels(page, "locked") <= UNCHANGED_AT_MOST


def test_lock_keeps_center_when_other_opened_and_pressed_again(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """ロック中に開いた別の項目の玉をもう一度押しても、何も変えず鍵を震わせるだけにする。ロック・詳細・表示は変わらず、震えは約 1 秒で収まる（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = _open_still(open_preview, url, "#tab=graph&id=D-2", page)
    _press_ball(page, *canvas_center(page))
    ox, oy = other_ball(page)
    _press_ball(page, ox, oy)
    opened = _hash(page)
    remember_pixels(page, "before")
    # 実行（開いている別の項目の玉をもう一度押す。押した後に少し動くので、近い玉を探し直す）
    ox, oy = nearest_ball(page, ox, oy)
    click_at(page, ox, oy)
    page.mouse.move(*blank_point(page))
    page.wait_for_timeout(SHAKE_EARLY_MS)
    shaking = changed_pixels(page, "before")
    settle(page)
    # 検証
    assert shaking >= KEY_PIXELS_AT_LEAST
    assert changed_pixels(page, "before") <= UNCHANGED_AT_MOST
    assert _hash(page) == opened


def test_lock_shake_when_blank_pressed(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """ロックした項目の詳細を開いているときに余白を押すと、ロック・詳細・表示を変えず、閉じた鍵を震わせる（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = _open_still(open_preview, url, "#tab=graph&id=D-2", page)
    _press_ball(page, *canvas_center(page))
    remember_pixels(page, "before")
    # 実行
    x, y = blank_point(page)
    click_at(page, x, y)
    page.wait_for_timeout(SHAKE_EARLY_MS)
    shaking = changed_pixels(page, "before")
    settle(page)
    # 検証
    assert shaking >= KEY_PIXELS_AT_LEAST
    assert changed_pixels(page, "before") <= UNCHANGED_AT_MOST
    assert _hash(page) == "#tab=graph&id=D-2"
    assert page.locator("aside.panel.open").count() == 1


def test_blank_press_when_unlocked(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """ロックしていないとき、余白を押すと詳細を閉じて全体の表示へ戻す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = _open_still(open_preview, url, "#tab=graph&id=D-2", page)
    # 実行
    click_at(page, *blank_point(page))
    page.wait_for_selector("aside.panel.open", state="detached")
    # 検証
    assert "id=" not in _hash(page)


def test_open_other_when_unlocked(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """ロックしていないとき、ほかの玉を押すと詳細をその項目に切り替える。ロックはしない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = _open_still(open_preview, url, "#tab=graph&id=D-2", page)
    remember_pixels(page, "free")
    ox, oy = other_ball(page)
    # 実行
    click_at(page, ox, oy)
    page.wait_for_function("!location.hash.includes('id=D-2')")
    # 検証（押した項目へ移り、その項目をもう一度押すとロックする = 最初の押しではロックしていない）
    assert page.inner_text("aside.panel .d-title") != "D-2の題"


def test_lock_key_shortcut(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """`L` キーで、詳細を開いている項目の玉をもう一度押したのと同じ規則でロックを付け外しする（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = _open_still(open_preview, url, "#tab=graph&id=D-2", page)
    remember_pixels(page, "free")
    # 実行（ロックする）
    page.keyboard.press("l")
    settle(page)
    locked = changed_pixels(page, "free")
    # 実行（ロックを外す）
    page.keyboard.press("l")
    settle(page)
    unlocked = changed_pixels(page, "free")
    # 検証
    assert locked >= KEY_PIXELS_AT_LEAST
    assert unlocked <= UNCHANGED_AT_MOST
    assert _hash(page) == "#tab=graph&id=D-2"


def test_lock_key_shake_when_other_opened(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """ロック中にほかの項目の詳細を開いているとき、`L` キーを押しても何も変えず、鍵を震わせる（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = _open_still(open_preview, url, "#tab=graph&id=D-2", page)
    _press_ball(page, *canvas_center(page))
    _press_ball(page, *other_ball(page))
    opened = _hash(page)
    remember_pixels(page, "before")
    # 実行
    page.keyboard.press("l")
    page.wait_for_timeout(SHAKE_EARLY_MS)
    shaking = changed_pixels(page, "before")
    settle(page)
    # 検証
    assert shaking >= KEY_PIXELS_AT_LEAST
    assert changed_pixels(page, "before") <= UNCHANGED_AT_MOST
    assert _hash(page) == opened


def test_lock_key_ignored(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """詳細を開いていないとき、修飾キー付きのとき、重ねる面（ダイアログ）を開いているときは、`L` キーを受けない（正常系）。"""
    # 準備（詳細を開いていない）
    _reduce_motion(page)
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    page.mouse.move(*blank_point(page))
    settle(page)
    remember_pixels(page, "none")
    # 実行（詳細を開いていないときの L）
    page.keyboard.press("l")
    settle(page)
    without_detail = changed_pixels(page, "none")
    # 準備（詳細を開く）
    page.evaluate("location.hash = '#tab=graph&id=D-2'")
    page.wait_for_selector("aside.panel.open")
    page.mouse.move(*blank_point(page))
    settle(page)
    remember_pixels(page, "open")
    # 実行（修飾キー付きの L）
    page.keyboard.press("Alt+l")
    settle(page)
    with_modifier = changed_pixels(page, "open")
    # 実行（検索のダイアログを開いているときの L）
    page.keyboard.press("Control+k")
    page.wait_for_selector("dialog.search[open]")
    page.keyboard.type("l")
    page.keyboard.press("Escape")
    page.wait_for_selector("dialog.search[open]", state="detached")
    page.mouse.move(*blank_point(page))
    settle(page)
    with_dialog = changed_pixels(page, "open")
    # 検証
    assert without_detail <= UNCHANGED_AT_MOST
    assert with_modifier <= UNCHANGED_AT_MOST
    assert with_dialog <= UNCHANGED_AT_MOST


def test_lock_stays_when_tab_moved(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """ロックは、詳細を閉じても、タブを行き来しても残る。検討事項のマップのロックとは別に持つ（正常系）。"""
    # 準備（ロックして、検討事項へ移り、ネットワークへ戻る）
    url = write_sample_preview()
    page = _open_still(open_preview, url, "#tab=graph&id=D-2", page)
    _press_ball(page, *canvas_center(page))
    page.click('nav.tabbar a[data-tab="decisions"]')
    page.wait_for_selector("#decision-map, table.grid, .board")
    page.click('nav.tabbar a[data-tab="graph"]')
    page.wait_for_selector(CANVAS_SELECTOR)
    page.mouse.move(*blank_point(page))
    settle(page)
    # 実行（ほかの玉を押してから、中心の玉を押す。ロックが残っていれば、中心はロックした D-2 のまま）
    _press_ball(page, *other_ball(page))
    _press_ball(page, *canvas_center(page))
    # 検証
    assert _hash(page) == "#tab=graph&id=D-2"
    # 検討事項のマップにはロックの鍵が無い（別に持つ）
    page.click('nav.tabbar a[data-tab="decisions"]')
    page.click('.segment button[data-view="map"]')
    page.wait_for_selector("#decision-map .map-node.n-item")
    assert page.locator("#decision-map button.n-item.locked").count() == 0


def test_lock_when_narrow(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """幅 900px 以下では詳細が全面に出るため、ロックしない。`L` キーを押しても、後で広げたときにロックは残っていない（正常系）。"""
    # 準備（狭い幅で項目を開いて閉じ、広げた絵を取る）
    _reduce_motion(page)
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph&id=D-2")
    page.set_viewport_size({"width": NARROW_WIDTH, "height": NARROW_HEIGHT})
    page.keyboard.press("Escape")
    page.wait_for_selector("aside.panel.open", state="detached")
    page.set_viewport_size(WIDE_VIEWPORT)
    page.mouse.move(*blank_point(page))
    settle(page)
    remember_pixels(page, "base")
    # 実行（狭い幅で項目を開き直して L を押し、閉じて広げる）
    page.set_viewport_size({"width": NARROW_WIDTH, "height": NARROW_HEIGHT})
    page.evaluate("location.hash = '#tab=graph&id=D-2'")
    page.wait_for_selector("aside.panel.open")
    page.keyboard.press("l")
    page.keyboard.press("Escape")
    page.wait_for_selector("aside.panel.open", state="detached")
    page.set_viewport_size(WIDE_VIEWPORT)
    page.mouse.move(*blank_point(page))
    settle(page)
    # 検証（鍵が出ていれば、鍵の分だけ画素が変わる）
    assert changed_pixels(page, "base") < KEY_PIXELS_AT_LEAST


def test_status_marks(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """注目しているときだけ、起点とつながる項目の名前の左に状態の印を描く。何も注目していないときは描かない。印は正方形で、状態ごとに違う絵（正常系）。"""
    # 準備・実行（何も注目していない）
    install_status_mark_spy(page)
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    page.wait_for_timeout(MARK_WAIT_MS)
    idle = status_marks(page)
    # 実行（項目を開く）
    page.evaluate("location.hash = '#tab=graph&id=D-2'")
    page.wait_for_selector("aside.panel.open")
    page.wait_for_timeout(MARK_WAIT_MS)
    focused = status_marks(page)
    # 検証
    assert idle == []
    assert 1 <= len(focused) <= NEAR_ITEMS_OF_D2
    assert all(mark["width"] == mark["height"] > 0 for mark in focused)
    assert all(0 < mark["alpha"] <= 1 for mark in focused)
    # 状態ごとに違う絵（D-1 決定済み・D-2 未決定・D-4 保留・T-1 進行中）
    assert len({mark["source"] for mark in focused}) == len(focused)
    # 印は、ロック中も注目の起点につながる項目の分を描く
    page.keyboard.press("l")
    page.wait_for_timeout(MARK_WAIT_MS)
    assert 1 <= len(status_marks(page)) <= NEAR_ITEMS_OF_D2


@pytest.mark.parametrize("look", list(LOOKS))
def test_comment_marks_when_each_look(
    write_commented_preview: WriteReviewPreview, open_preview: OpenPreview, look: str
) -> None:
    """名前の横のコメントの印は、5 つの見た目のどれでも、名前が読める大きさまで寄ると出て、キャンバスに収まる（正常系）。"""
    # 準備・実行
    url, _ = write_commented_preview()
    page = open_preview(url, "#tab=graph&id=D-2")
    pick_look(page, look)
    page.wait_for_function(
        "[...document.querySelectorAll('.g3-marks .cmk')].some(m => m.style.visibility !== 'hidden')",
        timeout=MARK_TIMEOUT_MS,
    )
    # 検証
    shown = _visible_marks(page)
    canvas = shown["canvas"]
    assert "2" in [mark["count"] for mark in shown["marks"]]
    for mark in shown["marks"]:
        assert canvas["left"] <= mark["left"] and mark["right"] <= canvas["right"]
        assert canvas["top"] <= mark["top"] and mark["bottom"] <= canvas["bottom"]


# 鍵の幅（12px）と、名前・鍵の間の隙間（3px）。鍵を出すとき、コメントの印がこの分だけ右へずれる
KEY_WIDTH_PX = 12
KEY_GAP_PX = 3

# 名前の右端とコメントの印の間の隙間（px）
MARK_GAP_PX = 4

# 位置を比べるときに許す差（px）
POSITION_TOLERANCE_PX = 1

# カーソルを動かしてから、開いた鍵が出入りするのを待つミリ秒
HOVER_SETTLE_MS = 600

# 全体を見る距離より遠くへ離れるホイールの量（1 回で最も遠い距離に届く）
WHEEL_OUT_DELTA = 1_000

# D-2 のコメントの印（件数 2）の左端を返す。見せている印だけを引く
MARK_LEFT_SCRIPT = """() => {
    const mark = [...document.querySelectorAll('.g3-marks .cmk')]
        .find((item) => item.style.visibility !== 'hidden' && item.querySelector('.cmk-n').textContent === '2');
    if (mark === undefined) return null;
    return Number.parseFloat(/translate\\(([-\\d.]+)px/.exec(mark.style.transform)[1]);
}"""


def _open_spied(open_preview: OpenPreview, url: str, hash_text: str, page: Page) -> Page:
    """鍵の記録を入れ、動きを減らす設定で項目を開いたネットワークを、画が静止するまで待って返す。"""
    _reduce_motion(page)
    install_key_spy(page)
    opened = open_preview(url, hash_text)
    opened.wait_for_selector("aside.panel.open")
    opened.mouse.move(*blank_point(opened))
    settle(opened)
    return opened


def test_lock_when_quick_double_press(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """何も選んでいないとき、ある玉を素早く同じ位置で 2 回押すと、1 回目で詳細が開いてキャンバスが縮んでも、その項目への 2 回押しとしてロックする（正常系）。"""
    # 準備
    _reduce_motion(page)
    install_key_spy(page)
    url = write_sample_preview()
    page = open_preview(url, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    page.mouse.move(*blank_point(page))
    settle(page)
    # 詳細が開いてキャンバスが縮んでも押した位置がキャンバスに残るよう、左寄りの玉を選ぶ
    x, y = min(ball_centers(page), key=lambda center: center[0])
    # 実行（動かさずに続けて 2 回押す）
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.up()
    page.mouse.down()
    page.mouse.up()
    page.wait_for_function("location.hash.includes('id=')")
    page.mouse.move(*blank_point(page))
    settle(page)
    draws = key_draws(page)
    # 検証
    assert len(draws) == 1
    assert draws[0]["closed"] is True
    assert page.locator("aside.panel.open").count() == 1


def test_open_key_when_hovered(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """ロックしていないとき、開いた鍵は詳細を開いている玉にカーソルを乗せたときだけ出す。ほかの玉に乗せても出さず、ロック中は閉じた鍵だけを出す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = _open_spied(open_preview, url, "#tab=graph&id=D-2", page)
    cx, cy = canvas_center(page)
    other = other_ball(page)
    away = key_draws(page)
    # 実行（開いている玉に乗せる → ほかの玉に乗せる → 外す）
    page.mouse.move(cx, cy)
    page.wait_for_timeout(HOVER_SETTLE_MS)
    on_open = key_draws(page)
    page.mouse.move(*other)
    page.wait_for_timeout(HOVER_SETTLE_MS)
    on_other = key_draws(page)
    page.mouse.move(*blank_point(page))
    page.wait_for_timeout(HOVER_SETTLE_MS)
    left = key_draws(page)
    # 実行（ロックしてから乗せる）
    page.keyboard.press("l")
    settle(page)
    locked_away = key_draws(page)
    page.mouse.move(cx, cy)
    page.wait_for_timeout(HOVER_SETTLE_MS)
    locked_on = key_draws(page)
    # 検証
    assert away == []
    assert [draw["closed"] for draw in on_open] == [False]
    assert on_other == []
    assert left == []
    assert [draw["closed"] for draw in locked_away] == [True]
    assert [draw["closed"] for draw in locked_on] == [True]


def test_key_sits_between_name_and_comment_mark(
    write_commented_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """名前・鍵・コメントの印の順に並べ、鍵を出すときだけ鍵の幅と隙間の分だけ印を右へずらす（正常系）。"""
    # 準備
    _reduce_motion(page)
    install_key_spy(page)
    url, _ = write_commented_preview()
    page = open_preview(url, "#tab=graph&id=D-2")
    page.wait_for_function(
        "[...document.querySelectorAll('.g3-marks .cmk')].some(m => m.style.visibility !== 'hidden')",
        timeout=MARK_TIMEOUT_MS,
    )
    page.mouse.move(*blank_point(page))
    settle(page)
    without_key = page.evaluate(MARK_LEFT_SCRIPT)
    no_key_drawn = key_draws(page)
    # 実行
    page.keyboard.press("l")
    settle(page)
    with_key = page.evaluate(MARK_LEFT_SCRIPT)
    draws = key_draws(page)
    # 検証
    assert no_key_drawn == []
    assert without_key is not None and with_key is not None
    assert len(draws) == 1 and draws[0]["closed"] is True
    shift = KEY_WIDTH_PX + KEY_GAP_PX
    assert abs((with_key - without_key) - shift) <= POSITION_TOLERANCE_PX
    # 名前の右端は、鍵が無いときの印の左端から隙間を引いた所。鍵はそこから隙間をあけて置き、印は鍵の右に続く
    name_right = without_key - MARK_GAP_PX
    assert abs(draws[0]["left"] - (name_right + KEY_GAP_PX)) <= POSITION_TOLERANCE_PX
    assert draws[0]["left"] + draws[0]["size"] <= with_key + POSITION_TOLERANCE_PX


def test_key_badge_when_far(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """名前が出ない遠い距離では、閉じた鍵を玉の右上の札の中に出す。名前が出る距離では札を使わない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = _open_spied(open_preview, url, "#tab=graph&id=D-2", page)
    page.keyboard.press("l")
    settle(page)
    near = key_draws(page)
    # 実行（最も遠い距離まで離れる）
    page.mouse.move(*blank_point(page))
    page.mouse.wheel(0, WHEEL_OUT_DELTA)
    settle(page)
    far = key_draws(page)
    # 検証
    assert [(draw["closed"], draw["badge"]) for draw in near] == [(True, False)]
    assert [(draw["closed"], draw["badge"]) for draw in far] == [(True, True)]


def test_lock_key_ignored_when_select_focused(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview, page: Page
) -> None:
    """入力欄（見た目のドロップダウン）にフォーカスがあるときは、`L` キーを受けない。フォーカスを外すと受ける（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = _open_spied(open_preview, url, "#tab=graph&id=D-2", page)
    page.focus(LOOK_SELECT)
    # 実行（ドロップダウンにフォーカスがある）
    page.keyboard.press("l")
    settle(page)
    while_focused = key_draws(page)
    look = page.eval_on_selector(LOOK_SELECT, "select => select.value")
    # 実行（フォーカスを外す）
    page.evaluate("document.activeElement.blur()")
    page.keyboard.press("l")
    settle(page)
    after_blur = key_draws(page)
    # 検証
    assert while_focused == []
    assert look == "deep"
    assert [draw["closed"] for draw in after_blur] == [True]
