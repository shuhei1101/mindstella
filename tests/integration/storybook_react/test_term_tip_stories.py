"""部品設計『本文の印のツールチップ.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-termtip--term-only", "shared-termtip--few", "shared-termtip--doc-only", "shared-termtip--no-description", "shared-termtip--many", "shared-termtip--below", "shared-termtip--shrunk", "shared-termtip--link-focus", "shared-termtip--long-narrow", "shared-termtip--several-terms",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    page = open_story(state)
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_term_only(open_story: OpenStory) -> None:
    """用語 1 件は用語・ID・意味だけを出し、リンクを持たない（正常系）。"""
    tip = open_story("shared-termtip--term-only").get_by_role("tooltip")
    expect(tip).to_contain_text("版を上げる作業")
    assert tip.get_by_role("link").count() == 0


def test_groups(open_story: OpenStory) -> None:
    """用語と資料と調査を種類ごとの見出しで分け、タイトルをリンクにする（正常系）。"""
    page = open_story("shared-termtip--few")
    links = page.locator("#term-tip").get_by_role("link")
    expect(links).to_have_count(3)


def test_several_terms(open_story: OpenStory) -> None:
    """用語 2 件も見出しの下にリンクで並べる（正常系）。"""
    expect(open_story("shared-termtip--several-terms").locator("#term-tip").get_by_role("link")).to_have_count(2)
