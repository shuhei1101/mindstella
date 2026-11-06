"""部品設計『左右に並べた本文の差分.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-sidebysidebodydiff--paragraphs", "shared-sidebysidebodydiff--rewritten", "shared-sidebysidebodydiff--table-and-list", "shared-sidebysidebodydiff--diagram",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    page = open_story(state)
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_columns(open_story: OpenStory) -> None:
    """左に選んだ時点、右に今を並べる（正常系）。"""
    page = open_story("shared-sidebysidebodydiff--paragraphs")
    expect(page.get_by_role("region", name="選んだ時点の本文")).to_be_visible()
    expect(page.get_by_role("region", name="今の本文")).to_be_visible()


def test_rewritten_words(open_story: OpenStory) -> None:
    """変わった語に面を付ける（正常系）。"""
    page = open_story("shared-sidebysidebodydiff--rewritten")
    page.wait_for_selector(".sbs .df-word")
    assert page.locator(".sbs .df-word").count() >= 2
