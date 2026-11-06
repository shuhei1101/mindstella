"""部品設計『表示形式の切り替え.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-viewswitch--decisions", "shared-viewswitch--tasks", "shared-viewswitch--docs",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    page = open_story(state)
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_current_is_pressed(open_story: OpenStory) -> None:
    """今の表示形式を押した状態にする（正常系）。"""
    expect(open_story("shared-viewswitch--decisions").get_by_role("button", name="マップ")).to_have_attribute("aria-pressed", "true")
    expect(open_story("shared-viewswitch--tasks").get_by_role("button", name="表")).to_have_attribute("aria-pressed", "true")
    expect(open_story("shared-viewswitch--docs").get_by_role("button", name="カード")).to_have_attribute("aria-pressed", "true")
