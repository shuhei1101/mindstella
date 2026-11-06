"""部品設計『取り下げの札.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-withdrawnbadge--default", "shared-withdrawnbadge--large", "shared-withdrawnbadge--beside-status-badges",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    errors: list[str] = []
    page = open_story(state)
    page.on("pageerror", lambda error: errors.append(error.message))
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert errors == []


def test_label(open_story: OpenStory) -> None:
    """「取り下げ」の札を出す（正常系）。"""
    assert "取り下げ" in open_story("shared-withdrawnbadge--default").inner_text("#storybook-root")
    assert "取り下げ" in open_story("shared-withdrawnbadge--large").inner_text("#storybook-root")
