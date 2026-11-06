"""部品設計『コメントの印.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-commentmark--one",
    "shared-commentmark--two-digits",
    "shared-commentmark--overflow",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


@pytest.mark.parametrize(
    ("state", "shown", "spoken"),
    [
        pytest.param("one", "1", "コメント 1 件", id="one"),
        pytest.param("two-digits", "12", "コメント 12 件", id="two-digits"),
        pytest.param("overflow", "99+", "コメント 128 件", id="overflow"),
    ],
)
def test_count(open_story: OpenStory, state: str, shown: str, spoken: str) -> None:
    """吹き出しと件数を画面に出し、99 を超えると「99+」にする。読み上げと `title` は実数（正常系）。"""
    # 準備・実行
    page = open_story(f"shared-commentmark--{state}")
    mark = page.locator("#storybook-root > span")
    # 検証
    expect(mark.locator("[aria-hidden=true]:not(svg)")).to_have_text(shown)
    expect(mark.locator(".sr-only")).to_have_text(spoken)
    expect(mark).to_have_attribute("title", spoken)
    assert mark.locator("svg").get_attribute("aria-hidden") == "true"
    assert mark.evaluate("e => e.tabIndex") == -1
