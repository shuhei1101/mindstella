"""部品設計『本文の差分の見せ方の切り替え.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-bodydiffviewswitch--rendered",
    "shared-bodydiffviewswitch--source",
    "shared-bodydiffviewswitch--focus-on-other",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_rendered(open_story: OpenStory) -> None:
    """既定。「描いた結果」を押した状態で、2 つのボタンの組を「本文の差分の見せ方」と読み上げる（正常系）。"""
    # 準備・実行
    page = open_story("shared-bodydiffviewswitch--rendered")
    group = page.get_by_role("group", name="本文の差分の見せ方")
    # 検証
    expect(group.get_by_role("button")).to_have_text(["描いた結果", "原文の差分"])
    expect(group.get_by_role("button", name="描いた結果")).to_have_attribute("aria-pressed", "true")
    expect(group.get_by_role("button", name="原文の差分")).to_have_attribute("aria-pressed", "false")


def test_source(open_story: OpenStory) -> None:
    """「原文の差分」を押した状態（正常系）。"""
    # 準備・実行
    page = open_story("shared-bodydiffviewswitch--source")
    # 検証
    expect(page.get_by_role("button", name="原文の差分")).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_role("button", name="描いた結果")).to_have_attribute("aria-pressed", "false")


def test_focus_on_other(open_story: OpenStory) -> None:
    """「描いた結果」を押したまま「原文の差分」にフォーカスを置くと、マーカーの色の輪を出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-bodydiffviewswitch--focus-on-other")
    other = page.get_by_role("button", name="原文の差分")
    # 検証
    expect(other).to_be_focused()
    expect(page.get_by_role("button", name="描いた結果")).to_have_attribute("aria-pressed", "true")
    assert other.evaluate("e => getComputedStyle(e).outlineStyle") != "none"
