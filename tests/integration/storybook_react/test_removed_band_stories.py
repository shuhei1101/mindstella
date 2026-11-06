"""部品設計『消した項目の帯.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-removedband--one",
    "shared-removedband--many-long-titles",
    "shared-removedband--narrow",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_one(open_story: OpenStory) -> None:
    """1 件。見出し「消した項目」と件数 1、消した印・ID・タイトルを並べ、帯を「この時点で消した項目」と読み上げる（正常系）。"""
    # 準備・実行
    page = open_story("shared-removedband--one")
    band = page.get_by_role("region", name="この時点で消した項目")
    items = band.get_by_role("listitem")
    # 検証
    expect(band.get_by_role("heading")).to_have_text("消した項目1")
    expect(items).to_have_count(1)
    expect(items.first).to_contain_text("N-6")
    expect(items.first).to_contain_text("ゴールを後から変える・足す・無しで始める")
    expect(items.first.locator("[title=消した]")).to_have_count(1)
    # 検証（項目はボタン・リンクにしない）
    assert band.locator("button, a").count() == 0


def test_many_long_titles(open_story: OpenStory) -> None:
    """3 件で長いタイトルを含む。渡した並びで並べ、タイトルは途中で切らずに折り返す（正常系）。"""
    # 準備・実行
    page = open_story("shared-removedband--many-long-titles")
    items = page.get_by_role("listitem")
    long_title = items.nth(1).locator("span").last
    # 検証
    expect(items).to_have_count(3)
    expect(items.nth(0)).to_contain_text("D-53")
    expect(items.nth(2)).to_contain_text("D-55")
    expect(long_title).to_have_text(
        "変更履歴のモーダルを時系列の一覧にして、未読の印を付け、読んだ時点から後の書き換えだけを数えるか"
    )
    assert long_title.evaluate(
        "e => e.scrollWidth <= e.clientWidth && getComputedStyle(e).textOverflow !== 'ellipsis'"
    )


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。見出しの下に項目を折り返し、ページを横に送らない（正常系）。"""
    # 準備
    page = open_story("shared-removedband--narrow")
    # 実行
    page.set_viewport_size({"width": 390, "height": 844})
    heading = page.get_by_role("heading").bounding_box()
    first = page.get_by_role("listitem").first.bounding_box()
    # 検証
    assert heading is not None
    assert first is not None
    assert first["y"] >= heading["y"] + heading["height"]
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )
