"""部品設計『HTMLの本文の枠.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-htmlbodyframe--rendered", "shared-htmlbodyframe--style-isolated", "shared-htmlbodyframe--loading", "shared-htmlbodyframe--with-scripts", "shared-htmlbodyframe--code-block", "shared-htmlbodyframe--diff-marks", "shared-htmlbodyframe--narrow", "shared-htmlbodyframe--viewport-relative", "shared-htmlbodyframe--links", "shared-htmlbodyframe--anchor-links",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    page = open_story(state)
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_sandbox(open_story: OpenStory) -> None:
    """スクリプトを動かさない枠に描く（正常系）。"""
    page = open_story("shared-htmlbodyframe--with-scripts")
    frame = page.locator("iframe")
    expect(frame).to_have_attribute("sandbox", "allow-same-origin")
    expect(page.frame_locator("iframe").get_by_role("heading", name="見出し")).to_be_visible()


def test_style_isolated(open_story: OpenStory) -> None:
    """本文のスタイルは枠の外へ漏れない（正常系）。"""
    page = open_story("shared-htmlbodyframe--style-isolated")
    expect(page.frame_locator("iframe").get_by_text("枠の中")).to_be_visible()
    assert page.evaluate("getComputedStyle(document.body).color") != "rgb(255, 0, 0)"


def test_diff_marks(open_story: OpenStory) -> None:
    """足した行と変えた行の要素に印を付ける（正常系）。"""
    frame = open_story("shared-htmlbodyframe--diff-marks").frame_locator("iframe")
    expect(frame.locator('[data-df="add"]')).to_have_text("五")
    expect(frame.locator('[data-df="chg"]')).to_have_text("三")


def test_frame_grows_to_content(open_story: OpenStory) -> None:
    """枠の高さが `100vh` の本文でも伸び続けない（正常系）。"""
    page = open_story("shared-htmlbodyframe--viewport-relative")
    page.wait_for_function("document.querySelector('iframe').offsetHeight > 0")
    first = page.locator("iframe").bounding_box()
    page.wait_for_timeout(300)
    assert first == page.locator("iframe").bounding_box()
