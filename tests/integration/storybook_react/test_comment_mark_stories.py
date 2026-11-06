"""部品設計『コメントの印.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-commentmark--one", "shared-commentmark--two-digits", "shared-commentmark--overflow",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    page = open_story(state)
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_counts(open_story: OpenStory) -> None:
    """件数を出し、99 を超えたら丸める（正常系）。"""
    assert "1" in open_story("shared-commentmark--one").inner_text("#storybook-root")
    assert "12" in open_story("shared-commentmark--two-digits").inner_text("#storybook-root")
    assert "99+" in open_story("shared-commentmark--overflow").inner_text("#storybook-root")
