"""部品設計『本文の差分の並べ方の切り替え.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-bodydifflayoutswitch--inline", "shared-bodydifflayoutswitch--side", "shared-bodydifflayoutswitch--focus-on-other",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    errors: list[str] = []
    page = open_story(state)
    page.on("pageerror", lambda error: errors.append(error.message))
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert errors == []


def test_pressed(open_story: OpenStory) -> None:
    """今の並べ方のボタンを押した状態にする（正常系）。"""
    expect(open_story("shared-bodydifflayoutswitch--inline").get_by_role("button", name="インライン")).to_have_attribute("aria-pressed", "true")
    expect(open_story("shared-bodydifflayoutswitch--side").get_by_role("button", name="左右に並べる")).to_have_attribute("aria-pressed", "true")
