"""部品設計『消した項目の帯.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-removedband--one", "shared-removedband--many-long-titles", "shared-removedband--narrow",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    page = open_story(state)
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_rows(open_story: OpenStory) -> None:
    """消した項目を ID とタイトルで並べる（正常系）。"""
    page = open_story("shared-removedband--one")
    band = page.get_by_role("region", name="この時点で消した項目")
    expect(band).to_contain_text("N-6")
    expect(band).to_contain_text("ゴールを後から変える")
