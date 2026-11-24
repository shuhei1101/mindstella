"""部品設計『一覧の並びの前後.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-siblingnav--middle",
    "shared-siblingnav--first",
    "shared-siblingnav--last",
    "shared-siblingnav--many-items",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_middle(open_story: OpenStory) -> None:
    """3 件の 2 件目。上向きと下向きの山形のボタンの間に「2 / 3」を出し、枠で 1 つにまとめる（正常系）。"""
    # 準備・実行
    page = open_story("shared-siblingnav--middle")
    group = page.get_by_role("group", name="一覧の並び")
    # 検証
    expect(group).to_have_text("2 / 3")
    expect(group.get_by_role("button", name="一覧の前の項目")).to_be_enabled()
    expect(group.get_by_role("button", name="一覧の次の項目")).to_be_enabled()
    assert group.evaluate("(element) => getComputedStyle(element).borderTopWidth") == "1px"


@pytest.mark.parametrize(
    ("state", "disabled"),
    [("shared-siblingnav--first", "一覧の前の項目"), ("shared-siblingnav--last", "一覧の次の項目")],
)
def test_edge(open_story: OpenStory, state: str, disabled: str) -> None:
    """先頭は「一覧の前の項目」、末尾は「一覧の次の項目」を押せない（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    expect(page.get_by_role("button", name=disabled)).to_be_disabled()


def test_many_items(open_story: OpenStory) -> None:
    """4 桁の件数（「1234 / 5678」）。位置の文字を折り返さない（正常系）。"""
    # 準備・実行
    page = open_story("shared-siblingnav--many-items")
    position = page.get_by_text("1234 / 5678")
    # 検証
    expect(position).to_be_visible()
    box = position.bounding_box()
    line_height = position.evaluate("(element) => parseFloat(getComputedStyle(element).lineHeight)")
    assert box is not None
    assert box["height"] < line_height * 1.5
