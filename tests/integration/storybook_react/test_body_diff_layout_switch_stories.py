"""部品設計『本文の差分の並べ方の切り替え.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-bodydifflayoutswitch--inline",
    "shared-bodydifflayoutswitch--side",
    "shared-bodydifflayoutswitch--focus-on-other",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_inline(open_story: OpenStory) -> None:
    """既定。「インライン」を押した状態で、2 つのボタンの組を「本文の差分の並べ方」と読み上げる（正常系）。"""
    # 準備・実行
    page = open_story("shared-bodydifflayoutswitch--inline")
    group = page.get_by_role("group", name="本文の差分の並べ方")
    # 検証
    expect(group.get_by_role("button")).to_have_text(["インライン", "左右に並べる"])
    expect(group.get_by_role("button", name="インライン")).to_have_attribute("aria-pressed", "true")
    expect(group.get_by_role("button", name="左右に並べる")).to_have_attribute(
        "aria-pressed", "false"
    )


def test_side(open_story: OpenStory) -> None:
    """「左右に並べる」を押した状態（正常系）。"""
    # 準備・実行
    page = open_story("shared-bodydifflayoutswitch--side")
    # 検証
    expect(page.get_by_role("button", name="左右に並べる")).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(page.get_by_role("button", name="インライン")).to_have_attribute("aria-pressed", "false")


def test_focus_on_other(open_story: OpenStory) -> None:
    """「インライン」を押したまま「左右に並べる」にフォーカスを置くと、印の色の輪を出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-bodydifflayoutswitch--focus-on-other")
    other = page.get_by_role("button", name="左右に並べる")
    # 検証
    expect(other).to_be_focused()
    expect(page.get_by_role("button", name="インライン")).to_have_attribute("aria-pressed", "true")
    assert other.evaluate("e => getComputedStyle(e).outlineStyle") != "none"
