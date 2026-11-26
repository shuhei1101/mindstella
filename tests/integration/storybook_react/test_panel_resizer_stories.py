"""部品設計『幅の区切り.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from .storybook_react_fixture_types import OpenStory

# ドラッグでポインターを動かす幅（px）
DRAG_PX = 40

# 区切りの帯の幅（マウスの端末・指の端末。px）
STRIP_WIDTH_PX = 24
TOUCH_STRIP_WIDTH_PX = 44


def _separator(page: Page) -> Locator:
    """ストーリーの幅の区切りを返す。"""
    return page.get_by_role("separator")


def _drag(page: Page, separator: Locator, dx: int) -> None:
    """区切りの中央を押し、横へ dx だけ動かして離す。"""
    box = separator.bounding_box()
    assert box is not None
    x = box["x"] + box["width"] / 2
    y = box["y"] + box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + dx / 2, y)
    page.mouse.move(x + dx, y)
    page.mouse.up()


def _cursor(separator: Locator) -> str:
    """区切りのカーソルを返す。"""
    return separator.evaluate("(element) => getComputedStyle(element).cursor")


def test_left(open_story: OpenStory, page_errors: list[str]) -> None:
    """パネルの左端の区切りは、← と左へのドラッグで広がる（正常系）。"""
    # 準備
    page = open_story("shared-panelresizer--left")
    separator = _separator(page)
    expect(separator).to_have_attribute("aria-label", "詳細パネルの幅")
    expect(separator).to_have_attribute("aria-orientation", "vertical")
    expect(separator).to_have_attribute("aria-valuemin", "480")
    expect(separator).to_have_attribute("aria-valuemax", "1040")
    # 実行
    separator.focus()
    page.keyboard.press("ArrowLeft")
    # 検証
    expect(separator).to_have_attribute("aria-valuenow", "656")
    # 実行
    _drag(page, separator, -DRAG_PX)
    # 検証
    expect(separator).to_have_attribute("aria-valuenow", str(656 + DRAG_PX))
    assert _cursor(separator) == "col-resize"
    assert separator.bounding_box()["width"] == STRIP_WIDTH_PX  # type: ignore[index]
    assert page_errors == []


def test_right(open_story: OpenStory, page_errors: list[str]) -> None:
    """パネルの右端の区切りは、→ と右へのドラッグで広がり、← で狭まる（正常系）。"""
    # 準備
    page = open_story("shared-panelresizer--right")
    separator = _separator(page)
    expect(separator).to_have_attribute("aria-label", "コメントの一覧の幅")
    expect(separator).to_have_attribute("aria-valuenow", "384")
    # 実行
    separator.focus()
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowLeft")
    # 検証
    expect(separator).to_have_attribute("aria-valuenow", "400")
    # 実行
    _drag(page, separator, DRAG_PX)
    # 検証
    expect(separator).to_have_attribute("aria-valuenow", str(400 + DRAG_PX))
    assert page_errors == []


def test_at_min(open_story: OpenStory, page_errors: list[str]) -> None:
    """下限では、狭める向きのキー・ドラッグでも下限のままで、広げる向きのカーソルにする（正常系）。"""
    # 準備
    page = open_story("shared-panelresizer--at-min")
    separator = _separator(page)
    # 実行
    separator.focus()
    page.keyboard.press("ArrowLeft")
    _drag(page, separator, -DRAG_PX)
    # 検証
    expect(separator).to_have_attribute("aria-valuenow", "320")
    assert _cursor(separator) == "e-resize"
    # 実行
    page.keyboard.press("End")
    # 検証
    expect(separator).to_have_attribute("aria-valuenow", "800")
    assert page_errors == []


def test_at_max(open_story: OpenStory, page_errors: list[str]) -> None:
    """上限では、広げる向きのキー・ドラッグでも上限のままで、狭める向きのカーソルにする（正常系）。"""
    # 準備
    page = open_story("shared-panelresizer--at-max")
    separator = _separator(page)
    # 実行
    separator.focus()
    page.keyboard.press("ArrowRight")
    _drag(page, separator, DRAG_PX)
    # 検証
    expect(separator).to_have_attribute("aria-valuenow", "800")
    assert _cursor(separator) == "w-resize"
    # 実行
    page.keyboard.press("Home")
    # 検証
    expect(separator).to_have_attribute("aria-valuenow", "320")
    assert page_errors == []


def test_touch(open_story: OpenStory, page: Page, page_errors: list[str]) -> None:
    """指の端末（pointer: coarse）では、帯の幅を 44px にしてパネルの端の線を帯の中央に挟む（正常系）。"""
    # 準備
    session = page.context.new_cdp_session(page)
    session.send("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 1})
    session.send("Emulation.setEmitTouchEventsForMouse", {"enabled": True, "configuration": "mobile"})
    # 実行
    page = open_story("shared-panelresizer--touch")
    separator = _separator(page)
    # 検証
    assert page.evaluate("matchMedia('(pointer: coarse)').matches") is True
    strip = separator.bounding_box()
    assert strip is not None
    assert strip["width"] == TOUCH_STRIP_WIDTH_PX
    panel = separator.evaluate_handle("(element) => element.parentElement").as_element()
    assert panel is not None
    edge = panel.bounding_box()
    assert edge is not None
    # パネルの右端が帯の中央にある
    assert abs(strip["x"] + strip["width"] / 2 - (edge["x"] + edge["width"])) <= 1
    assert page_errors == []
