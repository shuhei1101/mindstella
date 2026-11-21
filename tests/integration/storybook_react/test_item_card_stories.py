"""部品設計『項目のカード.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-itemcard--selectable-tags",
    "shared-itemcard--selectable-tags-selected",
    "shared-itemcard--default",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_selectable_tags(open_story: OpenStory) -> None:
    """外枠は div で、タイトルのボタンとタグのボタンを入れ子にせず並べる（正常系）。"""
    # 準備・実行
    page = open_story("shared-itemcard--selectable-tags")
    card = page.locator("div[data-card='T-1']")
    # 検証
    expect(card.locator("button[data-id='T-1']")).to_have_text("絞り込みの条件をタブの保存領域に残す")
    expect(card.locator("button[data-tag]")).to_have_count(3)
    expect(card.get_by_role("button", name="タグ「保存」で絞り込む")).to_be_visible()
    assert page.locator("button button").count() == 0
    expect(card.locator("button[data-id='T-1']")).not_to_have_attribute("aria-current", "true")


def test_selectable_tags_selected(open_story: OpenStory) -> None:
    """開いている項目のタイトルに aria-current を付け、タグを押せるまま残す（正常系）。"""
    # 準備・実行
    page = open_story("shared-itemcard--selectable-tags-selected")
    card = page.locator("div[data-card='T-1']")
    # 検証
    expect(card.locator("button[data-id='T-1']")).to_have_attribute("aria-current", "true")
    expect(card.locator("button[data-tag]")).to_have_count(3)


def test_default(open_story: OpenStory) -> None:
    """onSelectTag を指定しないカードはタグを並べない（正常系）。"""
    # 準備・実行
    page = open_story("shared-itemcard--default")
    card = page.locator("div[data-card='T-1']")
    # 検証
    expect(card.locator("button[data-id='T-1']")).to_be_visible()
    expect(card.locator("[data-tag]")).to_have_count(0)
