"""部品設計『差分の印.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-diffmark--new", "shared-diffmark--changed", "shared-diffmark--new-labeled", "shared-diffmark--removed",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    page = open_story(state)
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_kinds(open_story: OpenStory) -> None:
    """種類の名前を読み上げに残し、札は名前を見せる（正常系）。"""
    assert "新規" in open_story("shared-diffmark--new").text_content("#storybook-root")
    assert "変更" in open_story("shared-diffmark--changed").text_content("#storybook-root")
    assert "消した" in open_story("shared-diffmark--removed").text_content("#storybook-root")
    assert "新規" in open_story("shared-diffmark--new-labeled").inner_text("#storybook-root")
