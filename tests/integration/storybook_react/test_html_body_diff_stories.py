"""部品設計『HTMLの本文の差分.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-htmlbodydiff--rendered", "shared-htmlbodydiff--raw-diff", "shared-htmlbodydiff--removed-only", "shared-htmlbodydiff--from-markdown", "shared-htmlbodydiff--side-rendered", "shared-htmlbodydiff--side-raw", "shared-htmlbodydiff--side-from-markdown", "shared-htmlbodydiff--range-raw", "shared-htmlbodydiff--range-before", "shared-htmlbodydiff--range-after",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    errors: list[str] = []
    page = open_story(state)
    page.on("pageerror", lambda error: errors.append(error.message))
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert errors == []


def test_switch_to_raw(open_story: OpenStory) -> None:
    """「原文の差分」へ切り替える（正常系）。"""
    page = open_story("shared-htmlbodydiff--rendered")
    button = page.get_by_role("button", name="原文の差分")
    button.click()
    expect(button).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_label("原文の差分")).to_be_visible()


def test_removed_only(open_story: OpenStory) -> None:
    """消しただけのときは凡例に添える（正常系）。"""
    expect(open_story("shared-htmlbodydiff--removed-only").get_by_text("消した箇所は原文の差分で見られます")).to_be_visible()


def test_from_markdown(open_story: OpenStory) -> None:
    """選んだ時点が Markdown なら切り替えを出さない（正常系）。"""
    page = open_story("shared-htmlbodydiff--from-markdown")
    page.wait_for_selector(".html-diff")
    assert page.get_by_role("button", name="描いた結果").count() == 0
