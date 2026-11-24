"""部品設計『項目の日時.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-itemdates--updated",
    "shared-itemdates--not-updated",
    "shared-itemdates--narrow",
    "shared-itemdates--last-year",
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
    ("state", "expected"),
    [
        ("shared-itemdates--updated", ["作成 11/02 10:15", "更新 11/20 18:40"]),
        ("shared-itemdates--not-updated", ["作成 11/02 10:15", "更新 11/02 10:15"]),
        ("shared-itemdates--last-year", ["作成 2025/12/28 09:00", "更新 11/20 18:40"]),
    ],
)
def test_dates(open_story: OpenStory, state: str, expected: list[str]) -> None:
    """作成と更新を JST で出す。今年でない日時は年も出し、`time` の `datetime` に元の値を持つ（正常系）。"""
    # 準備・実行
    page = open_story(state)
    groups = page.locator("[data-part='item-dates'] > span")
    # 検証
    expect(groups).to_have_text(expected)
    for time in page.locator("[data-part='item-dates'] time").all():
        assert time.get_attribute("datetime") is not None


def test_narrow(open_story: OpenStory) -> None:
    """幅 240px。「作成 {日時}」と「更新 {日時}」の組ごとに折り返し、組の中の文字は折り返さない（正常系）。"""
    # 準備・実行
    page = open_story("shared-itemdates--narrow")
    groups = page.locator("[data-part='item-dates'] > span")
    # 検証
    heights = groups.evaluate_all("items => items.map((e) => e.getBoundingClientRect().height)")
    line_height = groups.first.evaluate("(element) => parseFloat(getComputedStyle(element).lineHeight)")
    assert all(height < line_height * 1.5 for height in heights)
