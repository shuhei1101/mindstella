"""画面設計『つながり』（キャンバスは項目 ID `graph-canvas`）の結合テスト。"""

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
from preview_fixture_types import OpenPreview, WriteReviewPreview, WriteSamplePreview
from preview_history_helpers import assert_topbar_history, preselect_diff
from preview_mark_helpers import MARK_TIMEOUT_MS

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
    assert page.inner_text("main h1") == "つながり"
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
    """つながりでも、トップバーに「変更履歴」のボタンと選んだ時点の札を出し、玉と線には印を付けない（正常系）。"""
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
    """つながりの見た目の値をキャンバスの入れ物に渡す。既定は深宇宙で、値ごとの描き分けはまだ無い（正常系）。"""
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
