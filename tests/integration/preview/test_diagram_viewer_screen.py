"""画面設計『図の拡大』（詳細パネルからのモーダル）の結合テスト。"""

from __future__ import annotations

import re

from playwright.sync_api import Page
from preview_fixture_types import OpenPreview, WriteReviewPreview, WriteSamplePreview
from preview_history_helpers import preselect_diff

# 図を描き終わるまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000

# 図の上でホイールを回す量（拡大する向き）
WHEEL_DELTA = -300

# 図の上の位置（モーダルの中央）
DIAGRAM_POINT = (640, 400)


def _open_viewer(write_sample_preview, open_preview) -> Page:
    """詳細パネルの図の拡大を開いて、そのページを返す。"""
    page = open_preview(write_sample_preview(), "#tab=decisions&view=table&id=D-3")
    page.wait_for_selector("aside.panel .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    page.click('aside.panel button[data-act="diagram-zoom"]')
    page.wait_for_selector("dialog.viewer[open] .v-stage svg")
    return page


def _percent(page: Page) -> int:
    """道具の行に出ている倍率（%）を数にして返す。"""
    text = page.inner_text("dialog.viewer .v-pct")
    found = re.search(r"\d+", text)
    assert found is not None, text
    return int(found.group())


def test_open_and_close(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """詳細パネルから図をモーダルで開き、本文へ戻るで閉じる（正常系）。"""
    # 準備・実行
    page = _open_viewer(write_sample_preview, open_preview)
    # 検証
    assert page.locator("dialog.viewer .v-stage svg").count() == 1
    # 図を置く窓が高さを持ち、窓に収まる倍率（正の値）で開く
    assert page.evaluate("document.querySelector('dialog.viewer .v-canvas').clientHeight") > 0
    assert _percent(page) > 0
    page.click('dialog.viewer button[data-act="diagram-close"]')
    page.wait_for_function("!document.querySelector('dialog.viewer')")
    assert page.locator("aside.panel.open").count() == 1


def test_close_by_escape(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """Esc で図の拡大を閉じ、詳細パネルは開いたままにする（正常系）。"""
    # 準備
    page = _open_viewer(write_sample_preview, open_preview)
    # 実行
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_function("!document.querySelector('dialog.viewer')")
    assert page.locator("aside.panel.open").count() == 1
    assert "id=D-3" in page.evaluate("location.hash")


def test_zoom(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """拡大・縮小のボタンとホイールで倍率を変える（正常系）。"""
    # 準備
    page = _open_viewer(write_sample_preview, open_preview)
    page.wait_for_function("document.querySelector('dialog.viewer .v-pct').textContent.match(/\\d/)")
    before = _percent(page)
    # 実行・検証
    page.click('dialog.viewer button[aria-label="拡大"]')
    after_button = _percent(page)
    assert after_button > before
    page.mouse.move(*DIAGRAM_POINT)
    page.mouse.wheel(0, WHEEL_DELTA)
    page.wait_for_function(
        f"parseInt(document.querySelector('dialog.viewer .v-pct').textContent.match(/\\d+/)[0]) > {after_button}"
    )
    after_wheel = _percent(page)
    page.click('dialog.viewer button[aria-label="縮小"]')
    assert _percent(page) < after_wheel


def test_text_selectable(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """図の文字は選んでコピーできる（正常系）。"""
    # 準備
    page = _open_viewer(write_sample_preview, open_preview)
    # 実行・検証
    select = page.evaluate(
        "getComputedStyle(document.querySelector('dialog.viewer .v-stage svg text, dialog.viewer .v-stage svg .nodeLabel')).userSelect"
    )
    assert select == "text"


# ─── 差分の表示 ───



def _open_diff_viewer(
    write_history_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    page: Page,
    hash_text: str,
    selector: str,
) -> Page:
    """差分の表示（まとまり V-2）で詳細パネルの図を色付けし終えるのを待って、図の拡大を開く。"""
    url, _ = write_history_preview()
    preselect_diff(page, "V-2")
    open_preview(url, hash_text)
    page.wait_for_selector(selector, timeout=DIAGRAM_TIMEOUT_MS)
    page.click('aside.panel button[data-act="diagram-zoom"]')
    page.wait_for_selector("dialog.viewer[open] .v-stage svg")
    return page


def test_raw(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """Raw を押すと図の代わりに記法を出し、押した状態を aria-pressed で伝える。差分の表示でなければ今の記法のまま出す（正常系）。"""
    # 準備
    page = _open_viewer(write_sample_preview, open_preview)
    button = page.locator('dialog.viewer button[data-act="viewer-raw"]')
    assert button.get_attribute("aria-pressed") == "false"
    # 実行
    button.click()
    # 検証
    assert button.get_attribute("aria-pressed") == "true"
    assert not page.is_visible("dialog.viewer .v-canvas")
    raw = page.locator("dialog.viewer .v-raw")
    assert raw.is_visible()
    assert "flowchart LR" in raw.inner_text()
    assert raw.locator(".df-line").count() == 0
    # もう一度押すと図へ戻る
    button.click()
    assert button.get_attribute("aria-pressed") == "false"
    assert page.is_visible("dialog.viewer .v-canvas")


def test_diff(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """差分の表示の間は、詳細パネルと同じ色を付け、窓の下端に凡例と「消したもの」を並べる（正常系）。"""
    # 準備・実行
    _open_diff_viewer(
        write_history_preview,
        open_preview,
        page,
        "#tab=decisions&view=table&id=D-1",
        "aside.panel figure.diagram.df-colored",
    )
    # 検証
    assert page.locator("dialog.viewer .v-stage g.df-n-add").count() == 1
    assert page.locator("dialog.viewer .v-stage g.df-n-chg").count() == 1
    notes = page.locator("dialog.viewer .v-notes")
    assert notes.locator(".df-lg-add").count() == 1
    assert notes.locator(".df-lg-chg").count() == 1
    assert any("終了" in text for text in notes.locator(".df-removed li").all_inner_texts())
    # 凡例は窓の下端（図を置く窓より下）に置く
    notes_box = notes.bounding_box()
    canvas_box = page.locator("dialog.viewer .v-canvas").bounding_box()
    assert notes_box is not None
    assert canvas_box is not None
    assert notes_box["y"] >= canvas_box["y"] + canvas_box["height"] - 1


def test_diff_when_frame(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """色を付けない種類の変わった図は、窓の内側に破線の枠を引き、Raw で見るよう案内する（正常系）。"""
    # 準備・実行
    _open_diff_viewer(
        write_history_preview,
        open_preview,
        page,
        "#tab=docs&view=table&id=A-1",
        "aside.panel figure.diagram.df-frame",
    )
    # 検証
    assert "図の中の変更は Raw で見られます" in page.inner_text("dialog.viewer .v-notes")
    assert page.eval_on_selector(
        "dialog.viewer .v-canvas", "e => getComputedStyle(e).outlineStyle"
    ) == "dashed"


def test_diff_raw(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """差分の表示の間の Raw は、記法の行ごとに足した行（+）と消した行（−）を印つきで出す（正常系）。"""
    # 準備
    _open_diff_viewer(
        write_history_preview,
        open_preview,
        page,
        "#tab=decisions&view=table&id=D-1",
        "aside.panel figure.diagram.df-colored",
    )
    # 実行
    page.click('dialog.viewer button[data-act="viewer-raw"]')
    # 検証
    raw = page.locator("dialog.viewer .v-raw.df-raw")
    assert raw.is_visible()
    assert any("処理を変えた" in text for text in raw.locator(".df-line.df-add").all_inner_texts())
    assert any("終了" in text for text in raw.locator(".df-line.df-del").all_inner_texts())
    assert page.get_attribute('dialog.viewer button[data-act="viewer-raw"]', "aria-pressed") == "true"
