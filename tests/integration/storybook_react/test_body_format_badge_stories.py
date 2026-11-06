"""部品設計『本文の形式の札.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-bodyformatbadge--markdown", "shared-bodyformatbadge--html", "shared-bodyformatbadge--beside-other-badges",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    errors: list[str] = []
    page = open_story(state)
    page.on("pageerror", lambda error: errors.append(error.message))
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert errors == []


def test_labels(open_story: OpenStory) -> None:
    """形式を `MD` / `HTML` で示す（正常系）。"""
    assert open_story("shared-bodyformatbadge--markdown").inner_text("#storybook-root").strip() == "MD"
    assert open_story("shared-bodyformatbadge--html").inner_text("#storybook-root").strip() == "HTML"
