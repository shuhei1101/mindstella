"""画面設計『図の拡大.tsx』の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Locator, Page, expect
from preview_fixture_types import WritePreview
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
