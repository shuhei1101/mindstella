"""部品設計『保存待ちの印.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-pendingmark--pending", "shared-pendingmark--remove", "shared-pendingmark--blocked", "shared-pendingmark--pending-compact", "shared-pendingmark--remove-compact", "shared-pendingmark--blocked-compact", "shared-pendingmark--dark",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    page = open_story(state)
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_labels(open_story: OpenStory) -> None:
    """種類ごとの文言を出し、印だけのときは読み上げに残す（正常系）。"""
    assert "保存待ち" in open_story("shared-pendingmark--pending").inner_text("#storybook-root")
    assert "保存で削除" in open_story("shared-pendingmark--remove").inner_text("#storybook-root")
    assert "書き込めない" in open_story("shared-pendingmark--blocked").inner_text("#storybook-root")
    page = open_story("shared-pendingmark--pending-compact")
    expect(page.get_by_title("保存待ち")).to_be_visible()
