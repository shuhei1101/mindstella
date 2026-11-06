"""部品設計『本文の形式の札.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-bodyformatbadge--markdown",
    "shared-bodyformatbadge--html",
    "shared-bodyformatbadge--beside-other-badges",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


# 札の枠の太さ・地の色・書体を返す
_BADGE_JS = """(element) => {
    const style = getComputedStyle(element);
    return { border: style.borderTopWidth, background: style.backgroundColor, font: style.fontFamily };
}"""

# 地を敷かない札の背景
TRANSPARENT = "rgba(0, 0, 0, 0)"


def test_markdown(open_story: OpenStory) -> None:
    """Markdown の資料は、地を敷かず、細い枠と `MD` の文字で出し、`title` に「本文は Markdown」を持つ（正常系）。"""
    # 準備・実行
    page = open_story("shared-bodyformatbadge--markdown")
    badge = page.locator("#storybook-root span").first
    style = badge.evaluate(_BADGE_JS)
    # 検証
    expect(badge).to_have_text("MD")
    expect(badge).to_have_attribute("title", "本文は Markdown")
    assert style["border"] == "1px"
    assert style["background"] == TRANSPARENT


def test_html(open_story: OpenStory) -> None:
    """HTML の資料は、地の面を敷いた `HTML` の文字で出し、`title` に「本文は HTML」を持つ（正常系）。"""
    # 準備・実行
    page = open_story("shared-bodyformatbadge--html")
    badge = page.locator("#storybook-root span").first
    # 検証
    expect(badge).to_have_text("HTML")
    expect(badge).to_have_attribute("title", "本文は HTML")
    assert badge.evaluate(_BADGE_JS)["background"] != TRANSPARENT


def test_beside_other_badges(open_story: OpenStory) -> None:
    """状態（完成）・取り下げの札・納品物の印と並べ、形式の札だけが等幅の書体を持つ（正常系）。"""
    # 準備・実行
    page = open_story("shared-bodyformatbadge--beside-other-badges")
    badges = page.locator("#storybook-root > div > span")
    form = badges.nth(0).evaluate(_BADGE_JS)
    others = [badges.nth(index).evaluate(_BADGE_JS)["font"] for index in (1, 2, 3)]
    # 検証
    expect(badges).to_have_text(["HTML", "完成", "取り下げ", "納品物"])
    assert form["font"] not in others
    assert form["background"] != TRANSPARENT
