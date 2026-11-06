"""部品設計『Markdownの本文.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-markdownbody--column-widths", "shared-markdownbody--small-table", "shared-markdownbody--pin-hover", "shared-markdownbody--pinned", "shared-markdownbody--pin-off", "shared-markdownbody--head-stuck", "shared-markdownbody--head-off", "shared-markdownbody--stripes", "shared-markdownbody--stripes-in-diff", "shared-markdownbody--sections", "shared-markdownbody--folded", "shared-markdownbody--fold-off", "shared-markdownbody--code-block", "shared-markdownbody--code-copied", "shared-markdownbody--callouts", "shared-markdownbody--narrow", "shared-markdownbody--in-thread-post", "shared-markdownbody--embedded-html",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    page = open_story(state)
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_table_tools(open_story: OpenStory) -> None:
    """列の固定のボタンを置き、`display` で外せる（正常系）。"""
    page = open_story("shared-markdownbody--pinned")
    page.wait_for_selector(".mdmark table")
    assert page.locator("button.md-pin").count() > 0
    page = open_story("shared-markdownbody--pin-off")
    page.wait_for_selector(".mdmark table")
    assert page.locator("button.md-pin").count() == 0


def test_fold(open_story: OpenStory) -> None:
    """見出しの矢印で畳み、`fold` が偽なら置かない（正常系）。"""
    page = open_story("shared-markdownbody--folded")
    arrow = page.get_by_role("button", name="料金を開閉")
    arrow.click()
    expect(arrow).to_have_attribute("aria-expanded", "false")
    page = open_story("shared-markdownbody--fold-off")
    page.wait_for_selector(".mdmark h2")
    assert page.locator("button.md-fold").count() == 0


def test_code_block(open_story: OpenStory) -> None:
    """言語の札とコピーのボタンを置く（正常系）。"""
    page = open_story("shared-markdownbody--code-block")
    expect(page.locator(".code-lang")).to_have_text("python")
    assert page.get_by_role("button", name="コードをコピー").count() == 2


def test_thread_post_has_no_table_tools(open_story: OpenStory) -> None:
    """`tables` が偽なら表に手を入れない（正常系）。"""
    page = open_story("shared-markdownbody--in-thread-post")
    page.wait_for_selector(".mdmark table")
    assert page.locator(".md-table-frame, button.md-pin").count() == 0
