"""部品設計『差分のミニマップ.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-diffminimap--kinds", "shared-diffminimap--single-mark", "shared-diffminimap--not-scrollable", "shared-diffminimap--many-marks", "shared-diffminimap--dragging", "shared-diffminimap--no-marks", "shared-diffminimap--hidden", "shared-diffminimap--narrow", "shared-diffminimap--side-by-side",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    page = open_story(state)
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_marks(open_story: OpenStory) -> None:
    """変わった箇所の印の帯を置く（正常系）。"""
    assert open_story("shared-diffminimap--kinds").get_by_role("toolbar", name="変わった箇所").locator("button").count() > 0


def test_hidden(open_story: OpenStory) -> None:
    """`shown` が偽のときは帯を出さない（正常系）。"""
    assert open_story("shared-diffminimap--hidden").get_by_role("toolbar", name="変わった箇所").count() == 0
