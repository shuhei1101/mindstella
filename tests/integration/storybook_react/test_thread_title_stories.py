"""部品設計『スレッドの見出しのタイトル.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-threadtitle--full-six-lines",
    "shared-threadtitle--collapsed",
    "shared-threadtitle--full-three-lines",
    "shared-threadtitle--long-word",
    "shared-threadtitle--long-word-collapsed",
)

# 要素の高さと行の高さを返す
_LINES_JS = """(element) => element.getBoundingClientRect().height / parseFloat(getComputedStyle(element).lineHeight)"""


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


@pytest.mark.parametrize("state", ["shared-threadtitle--full-six-lines", "shared-threadtitle--full-three-lines", "shared-threadtitle--long-word"])
def test_full(open_story: OpenStory, state: str) -> None:
    """並びが一番上のときは全文を折り返して出し、`title` を持たない（正常系）。"""
    # 準備・実行
    page = open_story(state)
    title = page.locator("[data-part='thread-title']")
    # 検証
    expect(title).not_to_have_attribute("data-collapsed", "")
    assert title.get_attribute("title") is None
    assert title.evaluate(_LINES_JS) > 1.5
    assert title.evaluate("(element) => element.scrollWidth <= element.clientWidth")


@pytest.mark.parametrize("state", ["shared-threadtitle--collapsed", "shared-threadtitle--long-word-collapsed"])
def test_collapsed(open_story: OpenStory, state: str) -> None:
    """スクロールした後は 1 行にして末尾を省き、`title` に全文を持つ（正常系）。"""
    # 準備・実行
    page = open_story(state)
    title = page.locator("[data-part='thread-title']")
    # 検証
    expect(title).to_have_attribute("data-collapsed", "")
    assert title.get_attribute("title") == title.text_content()
    assert title.evaluate(_LINES_JS) < 1.5
