"""画面設計『図の拡大.tsx』の結合テスト。"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Locator, Page, expect
from preview_fixture_types import WritePreview, WriteReviewPreview
from preview_spa_helpers import open_spa
from workspace_fixtures import MakeItem

# 図が窓の中央にあるとみなす差（px）
CENTER_TOLERANCE_PX = 16


@pytest.fixture
def viewer(page: Page, write_preview: WritePreview, make_item: MakeItem) -> Locator:
    """本文の図を拡大して開き、図の拡大のモーダルを返す。"""
    url = write_preview(make_item("D-1", title="図", status="未決定", body="D-1.md"), bodies={"D-1.md": "```mermaid\nflowchart LR; A-->B\n```\n"})
    open_spa(page, url, "?tab=decisions&id=D-1")
    page.locator(".mermaid svg").wait_for()
    page.get_by_role("button", name="図を拡大表示").click()
    return page.get_by_role("dialog", name="図の拡大")


def test_fits_on_open(viewer: Locator) -> None:
    """開いた直後に窓へ収まる大きさで中央に置く（正常系）。"""
    expect(viewer.locator(".font-mono")).not_to_have_text("100%")
    box = viewer.locator(".select-text svg").bounding_box()
    frame = viewer.bounding_box()
    assert box is not None
    assert frame is not None
    assert abs((box["x"] + box["width"] / 2) - (frame["x"] + frame["width"] / 2)) < CENTER_TOLERANCE_PX


def test_raw_shows_source(viewer: Locator) -> None:
    """Raw で図の代わりに記法を出す（正常系）。"""
    raw = viewer.get_by_role("button", name="Raw")
    raw.click()
    expect(raw).to_have_attribute("aria-pressed", "true")
    expect(viewer.get_by_role("region", name="図の記法")).to_contain_text("A-->B")


def test_back_closes(page: Page, viewer: Locator) -> None:
    """「本文へ戻る」で閉じる（正常系）。"""
    viewer.get_by_role("button", name="本文へ戻る").click()
    expect(page.get_by_role("dialog", name="図の拡大")).to_have_count(0)


# ─── 画面設計の要素の確認項目 ───

# 図を描き終わるまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000

# 「本文へ戻る」を印だけにする幅の上限（px）
ICON_BACK_MAX_WIDTH = 389


def test_close_label(viewer: Locator) -> None:
    """閉じるの読み上げの名前と文言は「本文へ戻る」（正常系）。"""
    # 準備・実行
    close = viewer.get_by_role("button", name="本文へ戻る")
    # 検証
    expect(close).to_have_text("本文へ戻る")


def test_close_label_when_narrow(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """幅 389px 以下では文字を隠して印だけにし、読み上げの名前は「本文へ戻る」のまま（正常系）。"""
    # 準備
    page.set_viewport_size({"width": ICON_BACK_MAX_WIDTH, "height": 800})
    url = write_preview(make_item("D-1", title="図", status="未決定", body="D-1.md"), bodies={"D-1.md": "```mermaid\nflowchart LR; A-->B\n```\n"})
    open_spa(page, url, "?tab=decisions&id=D-1")
    page.locator(".mermaid svg").wait_for(timeout=DIAGRAM_TIMEOUT_MS)
    # 実行
    page.get_by_role("button", name="図を拡大表示").click()
    close = page.get_by_role("dialog", name="図の拡大").get_by_role("button", name="本文へ戻る")
    # 検証
    expect(close).to_be_visible()
    expect(close.get_by_text("本文へ戻る")).to_be_hidden()


def test_diff_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """差分の表示の間で図の記法が変わったときは、図に差分の色を付け、窓の下端に凡例を並べる（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions&id=D-1&diff=V-2")
    page.locator("figure.diagram.df-colored").wait_for(timeout=DIAGRAM_TIMEOUT_MS)
    # 実行
    page.get_by_role("button", name="図を拡大表示").click()
    dialog = page.get_by_role("dialog", name="図の拡大")
    # 検証
    expect(dialog.locator("svg g.df-n-add")).to_have_count(1)
    expect(dialog.locator(".df-legend")).to_have_count(1)


def test_diff_hidden(viewer: Locator) -> None:
    """差分の表示でないときは、図の差分の色と凡例を出さない（正常系）。"""
    # 準備・実行・検証
    expect(viewer.locator("svg g.df-n-add, svg g.df-n-chg")).to_have_count(0)
    expect(viewer.locator(".df-legend")).to_have_count(0)


def test_raw_label(viewer: Locator) -> None:
    """Raw のボタンの文言は「Raw」で、押した状態を `aria-pressed` で伝える（正常系）。"""
    # 準備・実行
    raw = viewer.get_by_role("button", name="Raw")
    # 検証
    expect(raw).to_have_text("Raw")
    expect(raw).to_have_attribute("aria-pressed", "false")


def test_raw_visible(viewer: Locator) -> None:
    """Raw のボタンは常に上の帯に置く（正常系）。"""
    # 準備・実行・検証
    expect(viewer.get_by_role("button", name="Raw")).to_be_visible()


def test_source_visible(viewer: Locator) -> None:
    """記法は Raw を押している間だけ出し、もう一度押すと図へ戻る（正常系）。"""
    # 準備
    raw = viewer.get_by_role("button", name="Raw")
    region = viewer.get_by_role("region", name="図の記法")
    expect(region).to_have_count(0)
    # 実行
    raw.click()
    expect(region).to_be_visible()
    raw.click()
    # 検証
    expect(region).to_have_count(0)
    expect(viewer.locator(".select-text svg")).to_be_visible()


# 倍率の表示を数で返す
_PERCENT_JS = """(dialog) => parseInt(dialog.querySelector('.font-mono').textContent, 10)"""

# 図の置き場所の左上（px）を返す
_STAGE_JS = """(dialog) => {
    const box = dialog.querySelector('.select-text').getBoundingClientRect();
    return { x: box.left, y: box.top };
}"""


def test_wheel_zooms(page: Page, viewer: Locator) -> None:
    """図の上でホイールを回すと拡大し、逆に回すと縮小する（正常系）。"""
    # 準備
    expect(viewer.locator(".font-mono")).to_have_text(re.compile(r"\d+%"))
    before = viewer.evaluate(_PERCENT_JS)
    box = viewer.locator(".select-text").bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    # 実行
    page.mouse.wheel(0, -300)
    page.wait_for_function(f"document.querySelector('[role=dialog] .font-mono').textContent !== '{before}%'")
    zoomed_in = viewer.evaluate(_PERCENT_JS)
    page.mouse.wheel(0, 600)
    page.wait_for_function(f"parseInt(document.querySelector('[role=dialog] .font-mono').textContent, 10) < {zoomed_in}")
    # 検証
    assert zoomed_in > before
    assert viewer.evaluate(_PERCENT_JS) < zoomed_in


def test_background_drag_moves(page: Page, viewer: Locator) -> None:
    """背景をドラッグすると図が動く（正常系）。"""
    # 準備
    canvas = viewer.locator(".cursor-grab").bounding_box()
    assert canvas is not None
    before = viewer.evaluate(_STAGE_JS)
    # 実行（図の外の背景の左上の隅を押して動かす）
    page.mouse.move(canvas["x"] + 8, canvas["y"] + 8)
    page.mouse.down()
    page.mouse.move(canvas["x"] + 88, canvas["y"] + 48, steps=5)
    page.mouse.up()
    after = viewer.evaluate(_STAGE_JS)
    # 検証
    assert abs(after["x"] - before["x"] - 80) <= 2
    assert abs(after["y"] - before["y"] - 40) <= 2


def test_escape_closes(page: Page, viewer: Locator) -> None:
    """Esc で図の拡大を閉じ、詳細パネルは開いたまま（正常系）。"""
    # 準備・実行
    page.keyboard.press("Escape")
    # 検証
    expect(page.get_by_role("dialog", name="図の拡大")).to_have_count(0)
    expect(page.get_by_role("complementary", name="詳細")).to_be_visible()
