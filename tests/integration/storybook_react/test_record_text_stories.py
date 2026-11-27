"""部品設計『記録の文字.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-recordtext--heading-links",
    "shared-recordtext--link-hover",
    "shared-recordtext--related-title-links",
    "shared-recordtext--card-title-markers",
    "shared-recordtext--marker-hover",
    "shared-recordtext--marker-row-focus",
    "shared-recordtext--marker-no-tooltip",
    "shared-recordtext--card-link-row-markers",
    "shared-recordtext--search-result-markers",
    "shared-recordtext--no-ids",
    "shared-recordtext--long-title",
    "shared-recordtext--touch-link-tap",
)

# 見本の記録の D-1 のツールチップに出る文字（タイトル・ID・種類・状態）
D1_TIP_TEXTS = ("保存先の決め方", "D-1", "検討事項", "未決定")


def _assert_d1_tip(page: Page) -> None:
    """D-1 のタイトル・ID・種類・状態のツールチップが出ている。"""
    tip = page.locator(".term-tip")
    expect(tip).to_be_visible()
    for text in D1_TIP_TEXTS:
        expect(tip).to_contain_text(text)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_heading_links(open_story: OpenStory) -> None:
    """記録にある D-1・TH-1 だけを #id= のリンクにし、記録に無い D-99 は文字のまま出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-recordtext--heading-links")
    heading = page.locator("#storybook-root h2")
    # 検証
    expect(heading).to_have_text("D-1 の比較（TH-1 の続き、D-99 は除く）")
    expect(heading.get_by_role("link")).to_have_count(2)
    expect(heading.get_by_role("link", name="D-1")).to_have_attribute("href", "#id=D-1")
    expect(heading.get_by_role("link", name="TH-1")).to_have_attribute("href", "#id=TH-1")


def test_link_hover(open_story: OpenStory) -> None:
    """D-1 のリンクに乗せると、D-1 のタイトル・ID・種類・状態のツールチップを出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-recordtext--link-hover")
    # 検証
    _assert_d1_tip(page)


def test_link_focus(open_story: OpenStory) -> None:
    """Tab で D-1 のリンクにフォーカスしても、乗せたときと同じツールチップを出す（正常系）。"""
    # 準備
    page = open_story("shared-recordtext--heading-links")
    # 実行
    page.keyboard.press("Tab")
    # 検証
    expect(page.get_by_role("link", name="D-1")).to_be_focused()
    _assert_d1_tip(page)


def test_related_title_links(open_story: OpenStory) -> None:
    """ID のボタンの外側のタイトルの中の D-1 をリンクにする（正常系）。"""
    # 準備・実行
    page = open_story("shared-recordtext--related-title-links")
    row = page.locator("#storybook-root li")
    # 検証
    expect(row.get_by_role("link", name="D-1")).to_have_attribute("href", "#id=D-1")
    expect(row.locator("button a")).to_have_count(0)


def test_card_title_markers(open_story: OpenStory) -> None:
    """ボタンの中の ID はリンクにせず、等幅の点線の下線のマーカーにし、ボタンの aria-describedby で説明を読み上げる（正常系）。"""
    # 準備・実行
    page = open_story("shared-recordtext--card-title-markers")
    button = page.locator("#storybook-root button")
    marker = button.locator("[data-record-id='D-1']")
    # 検証
    expect(button.locator("a")).to_have_count(0)
    expect(page.locator("#storybook-root [tabindex], #storybook-root a")).to_have_count(0)
    expect(marker).to_have_text("D-1")
    expect(button.locator("[data-record-id='D-99']")).to_have_count(0)
    assert marker.evaluate("e => getComputedStyle(e).textDecorationStyle") == "dotted"
    assert marker.evaluate("e => getComputedStyle(e).fontFamily") != button.evaluate("e => getComputedStyle(e).fontFamily")
    expect(button).to_have_attribute("aria-describedby", "card-a1-ids")
    expect(page.locator("#card-a1-ids")).to_have_text("保存先の決め方（D-1） 検討事項 未決定")


def test_marker_hover(open_story: OpenStory) -> None:
    """カードのタイトルの D-1 のマーカーに乗せると、D-1 のツールチップを出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-recordtext--marker-hover")
    # 検証
    _assert_d1_tip(page)


def test_marker_row_focus(open_story: OpenStory) -> None:
    """カードのタイトルのボタンに Tab でフォーカスすると、行の中の ID のツールチップを出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-recordtext--marker-row-focus")
    # 検証
    expect(page.locator("#storybook-root button")).to_be_focused()
    _assert_d1_tip(page)


def test_marker_no_tooltip(open_story: OpenStory) -> None:
    """スレッドの行のボタンの中。D-1 は点線の下線のマーカーのままで、乗せてもボタンにフォーカスしてもツールチップを出さない。ボタンの aria-describedby の説明は残る（正常系）。"""
    # 準備・実行（ストーリーの play で D-1 に乗せ、ボタンにフォーカスする）
    page = open_story("shared-recordtext--marker-no-tooltip")
    button = page.locator("#storybook-root button")
    # 検証
    expect(button).to_be_focused()
    expect(page.locator("#storybook-root [data-record-id='D-1']")).to_have_count(1)
    expect(page.locator(".term-tip")).to_have_count(0)
    expect(button).to_have_accessible_description(re.compile("保存先の決め方"))


def test_card_link_row_markers(open_story: OpenStory) -> None:
    """カードの進める検討事項の行のタイトルの中の D-1 をマーカーにし、カードの中にリンクを増やさない（正常系）。"""
    # 準備・実行
    page = open_story("shared-recordtext--card-link-row-markers")
    # 検証
    expect(page.locator("#storybook-root span > [data-record-id='D-1']")).to_have_text("D-1")
    expect(page.locator("#storybook-root a")).to_have_count(0)
    expect(page.locator("#card-t1-for")).to_contain_text("保存先の決め方（D-1）")


def test_search_result_markers(open_story: OpenStory) -> None:
    """検索の結果の option の中にフォーカスできる要素を配置せず、ID をマーカーにして option の aria-describedby で説明を読み上げる（正常系）。"""
    # 準備・実行
    page = open_story("shared-recordtext--search-result-markers")
    option = page.get_by_role("option")
    # 検証
    expect(option.locator("[data-record-id='D-1']")).to_have_text("D-1")
    expect(option.locator("a, button, [tabindex='0']")).to_have_count(0)
    expect(option).to_have_attribute("aria-describedby", "result-a1-ids")
    expect(page.locator("#result-a1-ids")).to_contain_text("保存先の決め方（D-1）")


def test_no_ids(open_story: OpenStory) -> None:
    """ID を持たないタイトルは文字をそのまま描き、ID の要素を描かない（正常系）。"""
    # 準備・実行
    page = open_story("shared-recordtext--no-ids")
    root = page.locator("#storybook-root")
    # 検証
    expect(root).to_have_text("保存先の比較")
    expect(root.locator("[data-record-id], a")).to_have_count(0)


def test_long_title(open_story: OpenStory) -> None:
    """長いタイトルは ID のリンクの途中でも折り返し、枠の外へはみ出さない（正常系）。"""
    # 準備・実行
    page = open_story("shared-recordtext--long-title")
    heading = page.locator("#storybook-root h2")
    # 検証
    expect(heading.get_by_role("link")).to_have_count(3)
    assert heading.evaluate("e => e.scrollWidth <= e.clientWidth")


def test_touch_link_tap(open_story: OpenStory) -> None:
    """指で D-1 のリンクを 1 回押すと、ツールチップを出さずに `onOpen` を D-1 で 1 回呼ぶ（正常系）。"""
    # 準備・実行
    page = open_story("shared-recordtext--touch-link-tap")
    opened = page.locator("[data-part=opened]")
    # 検証
    expect(opened).to_have_text("D-1")
    expect(page.locator(".term-tip")).to_have_count(0)


def test_link_hover_tip_with_mouse(open_story: OpenStory) -> None:
    """対照として、マウスで D-1 のリンクに乗せたときはツールチップを出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-recordtext--link-hover")
    # 検証
    _assert_d1_tip(page)
