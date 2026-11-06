"""部品設計『絞り込み.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-filterdrawer--default", "shared-filterdrawer--selected", "shared-filterdrawer--zero-value", "shared-filterdrawer--long-tag", "shared-filterdrawer--keyword-hits", "shared-filterdrawer--no-match", "shared-filterdrawer--narrow", "shared-filterdrawer--text-conditions",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    errors: list[str] = []
    page = open_story(state)
    page.on("pageerror", lambda error: errors.append(error.message))
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert errors == []


def test_default_has_no_clear(open_story: OpenStory) -> None:
    """何も選んでいないときは解除を出さない（正常系）。"""
    page = open_story("shared-filterdrawer--default")
    expect(page.get_by_role("dialog")).to_contain_text("12 件")
    assert page.get_by_role("button", name="すべて解除").count() == 0


def test_selected(open_story: OpenStory) -> None:
    """選んだ条件に件数と解除を出し、見出しは絞った件数を示す（正常系）。"""
    dialog = open_story("shared-filterdrawer--selected").get_by_role("dialog")
    expect(dialog).to_contain_text("36 件中 3 件")
    expect(dialog.get_by_role("button", name="すべて解除")).to_be_visible()
    expect(dialog.get_by_role("button", name="3 件を表示")).to_be_visible()


def test_no_match(open_story: OpenStory) -> None:
    """該当なしは「0 件を表示」にする（正常系）。"""
    dialog = open_story("shared-filterdrawer--no-match").get_by_role("dialog")
    expect(dialog.get_by_role("button", name="0 件を表示")).to_be_visible()


def test_keyword_hits(open_story: OpenStory) -> None:
    """キーワードに一致した件数を添える（正常系）。"""
    expect(open_story("shared-filterdrawer--keyword-hits").get_by_label("キーワードに一致した項目 2 件")).to_be_visible()


def test_text_conditions(open_story: OpenStory) -> None:
    """文字の条件の欄に今の文字を入れる（正常系）。"""
    expect(open_story("shared-filterdrawer--text-conditions").locator('[data-text-key="title"]')).to_have_value("移し")
