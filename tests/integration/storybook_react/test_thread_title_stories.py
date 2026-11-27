"""部品設計『スレッドの見出しのタイトル.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Browser, expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-threadtitle--full-six-lines",
    "shared-threadtitle--expanded",
    "shared-threadtitle--long-text",
    "shared-threadtitle--long-text-expanded",
    "shared-threadtitle--short",
    "shared-threadtitle--collapsed",
    "shared-threadtitle--full-three-lines",
    "shared-threadtitle--long-word",
    "shared-threadtitle--long-word-collapsed",
    "shared-threadtitle--title-id-links",
    "shared-threadtitle--title-id-links-collapsed",
)

# 全文を開いた間の見出しの中の最大の高さ（px。部品設計『スレッドの見出しのタイトル』の LongTextExpanded）
_EXPANDED_MAX_HEIGHT_PX = 288

# 開閉のボタンの見た目の高さと、指の端末の押せる領域の下限・上下に広げる幅（px。部品設計のアクセシビリティ）
_BUTTON_HEIGHT_PX = 28
_TOUCH_TARGET_PX = 44
_TOUCH_EXTEND_PX = 8

# ページ全体が横にスクロールしない
_NO_PAGE_SCROLL_JS = "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"

# 開閉のボタンの高さと、::after の高さ・ボタンの上端からの位置を返す
_AFTER_RECT_JS = """(element) => {
  const style = getComputedStyle(element, "::after");
  return { button: element.getBoundingClientRect().height, after: parseFloat(style.height) || (element.getBoundingClientRect().height - parseFloat(style.top) - parseFloat(style.bottom)), top: parseFloat(style.top) };
}"""

# 要素の高さと行の高さを返す
_LINES_JS = """(element) => element.getBoundingClientRect().height / parseFloat(getComputedStyle(element).lineHeight)"""


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


@pytest.mark.parametrize("state", ["shared-threadtitle--full-six-lines", "shared-threadtitle--full-three-lines", "shared-threadtitle--long-text"])
def test_clamped(open_story: OpenStory, state: str) -> None:
    """並びが一番上で 2 行を超えるタイトルは 2 行で省略し、下に「続きを表示」を出す。パネルの幅を超えない（正常系）。"""
    # 準備・実行
    page = open_story(state)
    title = page.locator("[data-part='thread-title']")
    text = title.locator("span[id]").first
    button = page.get_by_role("button", name="タイトルの続きを表示")
    # 検証
    expect(title).to_have_attribute("data-clamped", "")
    expect(button).to_have_attribute("aria-expanded", "false")
    expect(button).to_have_text("続きを表示")
    assert text.evaluate(_LINES_JS) < 2.5
    assert title.get_attribute("title") is None
    assert page.evaluate(_NO_PAGE_SCROLL_JS)


def test_long_word(open_story: OpenStory) -> None:
    """1 単語の長い英字も、パネルの幅で折り返して横にはみ出さない（正常系）。"""
    # 準備・実行
    page = open_story("shared-threadtitle--long-word")
    title = page.locator("[data-part='thread-title']")
    # 検証
    expect(title).not_to_have_attribute("data-collapsed", "")
    assert title.evaluate("(element) => element.scrollWidth <= element.clientWidth")
    assert page.evaluate(_NO_PAGE_SCROLL_JS)


@pytest.mark.parametrize("state", ["shared-threadtitle--expanded", "shared-threadtitle--long-text-expanded"])
def test_expanded(open_story: OpenStory, state: str) -> None:
    """「続きを表示」を押すと全文を出し、見出しの中で 288px までにしてスクロールさせ、「折りたたむ」にする（正常系）。"""
    # 準備・実行
    page = open_story(state)
    button = page.get_by_role("button", name="タイトルを折りたたむ")
    region = page.get_by_role("region", name="スレッドのタイトルの全文")
    # 検証
    expect(button).to_have_attribute("aria-expanded", "true")
    expect(button).to_have_text("折りたたむ")
    expect(region).to_have_attribute("tabindex", "0")
    expect(page.locator("[data-part='thread-title']")).not_to_have_attribute("data-clamped", "")
    assert region.evaluate("(element) => element.getBoundingClientRect().height") <= _EXPANDED_MAX_HEIGHT_PX
    assert page.evaluate(_NO_PAGE_SCROLL_JS)


def test_long_text_expanded_scroll(open_story: OpenStory) -> None:
    """3000 文字を超える全文は見出しの中でスクロールする（正常系）。"""
    # 準備・実行
    page = open_story("shared-threadtitle--long-text-expanded")
    region = page.get_by_role("region", name="スレッドのタイトルの全文")
    # 検証
    assert region.evaluate("(element) => element.scrollHeight > element.clientHeight")


def test_toggle_back(open_story: OpenStory) -> None:
    """「折りたたむ」を押すと 2 行の省略に戻す（正常系）。"""
    # 準備
    page = open_story("shared-threadtitle--expanded")
    # 実行
    page.get_by_role("button", name="タイトルを折りたたむ").click()
    # 検証
    expect(page.locator("[data-part='thread-title']")).to_have_attribute("data-clamped", "")
    expect(page.get_by_role("button", name="タイトルの続きを表示")).to_have_attribute("aria-expanded", "false")
    expect(page.get_by_role("region")).to_have_count(0)


def test_short(open_story: OpenStory) -> None:
    """2 行に収まるタイトルは省略せず、開閉のボタンを出さない（正常系）。"""
    # 準備・実行
    page = open_story("shared-threadtitle--short")
    # 検証
    expect(page.locator("[data-part='thread-title']")).not_to_have_attribute("data-clamped", "")
    expect(page.get_by_role("button")).to_have_count(0)


def test_touch_target(browser: Browser, storybook_react_url: str) -> None:
    """指の端末では開閉のボタンの押せる領域を、見た目の高さを変えずに上下 8px ずつ広げて 44px 以上にする（正常系）。"""
    # 準備
    context = browser.new_context(has_touch=True, is_mobile=True, viewport={"width": 390, "height": 844})
    page = context.new_page()
    page.goto(f"{storybook_react_url}/iframe.html?id=shared-threadtitle--full-six-lines&viewMode=story")
    button = page.get_by_role("button", name="タイトルの続きを表示")
    # 実行
    rects = button.evaluate(_AFTER_RECT_JS)
    context.close()
    # 検証
    assert rects["button"] == pytest.approx(_BUTTON_HEIGHT_PX, abs=1)
    assert rects["after"] >= _TOUCH_TARGET_PX
    assert rects["top"] == pytest.approx(-_TOUCH_EXTEND_PX, abs=1)


@pytest.mark.parametrize("state", ["shared-threadtitle--collapsed", "shared-threadtitle--long-word-collapsed"])
def test_collapsed(open_story: OpenStory, state: str) -> None:
    """スクロールした後は 1 行にして末尾を省き、`title` に全文を持つ（正常系）。"""
    # 準備・実行
    page = open_story(state)
    title = page.locator("[data-part='thread-title']")
    # 検証
    text = title.locator("span[id]").first
    expect(title).to_have_attribute("data-collapsed", "")
    assert text.get_attribute("title") == text.text_content()
    assert text.evaluate(_LINES_JS) < 1.5
    expect(page.get_by_role("button")).to_have_count(0)


@pytest.mark.parametrize("state", ["shared-threadtitle--title-id-links", "shared-threadtitle--title-id-links-collapsed"])
def test_title_id_links(open_story: OpenStory, state: str) -> None:
    """記録にある D-1・TH-1 を本文のリンクと同じ #id= のリンクにし、D-99 は文字のまま出す。1 行にしても見えている ID はリンクのまま（正常系）。"""
    # 準備・実行
    page = open_story(state)
    root = page.locator("#storybook-root")
    # 検証
    expect(root.get_by_role("link")).to_have_count(2)
    expect(root.get_by_role("link", name="D-1")).to_have_attribute("href", "#id=D-1")
    expect(root.get_by_role("link", name="TH-1")).to_have_attribute("href", "#id=TH-1")
    expect(root.get_by_role("link", name="D-1")).to_be_visible()
