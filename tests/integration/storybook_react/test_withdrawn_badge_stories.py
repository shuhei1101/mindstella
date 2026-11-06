"""部品設計『取り下げの札.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-withdrawnbadge--default",
    "shared-withdrawnbadge--large",
    "shared-withdrawnbadge--beside-status-badges",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


# 札の高さ・枠の太さを返す
_BADGE_JS = """(element) => ({ height: element.getBoundingClientRect().height, border: getComputedStyle(element).borderTopWidth })"""


def test_default(open_story: OpenStory) -> None:
    """表の行・カードのタイトルの右に置く大きさ。枠付きの × と「取り下げ」で、× は読み上げに出さない（正常系）。"""
    # 準備・実行
    page = open_story("shared-withdrawnbadge--default")
    badge = page.locator("#storybook-root span", has_text="取り下げ").first
    # 検証
    expect(badge).to_have_text("取り下げ")
    assert badge.locator("svg").get_attribute("aria-hidden") == "true"
    assert badge.evaluate(_BADGE_JS)["border"] == "1px"


def test_large(open_story: OpenStory) -> None:
    """詳細パネルの題の右に置く大きさ。既定より一回り大きい（正常系）。"""
    # 準備
    default = (
        open_story("shared-withdrawnbadge--default")
        .locator("#storybook-root span")
        .first.evaluate(_BADGE_JS)
    )
    # 実行
    page = open_story("shared-withdrawnbadge--large")
    large = page.locator("#storybook-root span").first.evaluate(_BADGE_JS)
    # 検証
    expect(page.locator("#storybook-root span").first).to_have_text("取り下げ")
    assert large["height"] > default["height"]
    assert large["border"] == "1px"


def test_beside_status_badges(open_story: OpenStory) -> None:
    """検討事項の状態「取り下げ」・タスクの状態「中止」・資料の状態「完成」と並べ、取り下げの札だけが枠を持つ（正常系）。"""
    # 準備・実行
    page = open_story("shared-withdrawnbadge--beside-status-badges")
    statuses = page.locator("[data-status]")
    badge = page.locator("#storybook-root > div > span:not([data-status])")
    # 検証（状態は印と文言で並び、枠を持たない）
    expect(statuses).to_have_text(["取り下げ", "中止", "完成"])
    assert statuses.evaluate_all(
        "items => items.map((e) => getComputedStyle(e).borderTopWidth)"
    ) == ["0px", "0px", "0px"]
    # 検証（取り下げの札は枠を持ち、同じ文言）
    expect(badge).to_have_text("取り下げ")
    assert badge.evaluate(_BADGE_JS)["border"] == "1px"
