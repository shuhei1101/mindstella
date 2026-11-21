"""部品設計『絞り込みの条件のチップ.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-filterchips--tag-match-all",
    "shared-filterchips--tag-match-any",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_tag_match_all(open_story: OpenStory) -> None:
    """既定の「すべて含む」ではタグのチップを「タグ: {名前}」にする（正常系）。"""
    # 準備・実行
    page = open_story("shared-filterchips--tag-match-all")
    # 検証
    expect(page.get_by_text("タグ: 保存", exact=True)).to_be_visible()
    expect(page.get_by_text("タグ: 画面", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="タグ: 保存 の条件を解除")).to_be_visible()
    expect(page.get_by_role("button", name="すべて解除")).to_be_visible()


def test_tag_match_any(open_story: OpenStory) -> None:
    """「どれかを含む」でタグが 2 つ以上なら、タグのチップを「タグ（どれかを含む）: {名前}」にする（正常系）。"""
    # 準備・実行
    page = open_story("shared-filterchips--tag-match-any")
    # 検証
    expect(page.get_by_text("タグ（どれかを含む）: 保存", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="タグ（どれかを含む）: 画面 の条件を解除")).to_be_visible()
    expect(page.get_by_text("状態: 未着手", exact=True)).to_be_visible()
