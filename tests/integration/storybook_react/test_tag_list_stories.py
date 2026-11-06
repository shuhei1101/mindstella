"""部品設計『タグの並び.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-taglist--one-main",
    "shared-taglist--two-main",
    "shared-taglist--no-main",
    "shared-taglist--string-tags",
    "shared-taglist--long-narrow",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


# タグの名前（読み上げだけの「主題」を除く）・主題か・マーカーの有無・枠の色を返す
_TAGS_JS = """() => [...document.querySelectorAll('[data-tags] > span')].map((tag) => ({
    name: [...tag.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE).map((node) => node.textContent).join(''),
    main: tag.getAttribute('title') === '主題',
    marker: tag.querySelector('svg[aria-hidden=true]') !== null,
    border: getComputedStyle(tag).borderTopColor,
}))"""


def test_one_main(open_story: OpenStory) -> None:
    """主題のタグは二重丸のマーカーと読み上げの「主題」・`title` を持ち、枠を 1 段濃くする（正常系）。"""
    # 準備・実行
    page = open_story("shared-taglist--one-main")
    tags = page.evaluate(_TAGS_JS)
    # 検証
    assert [(tag["name"], tag["main"], tag["marker"]) for tag in tags] == [
        ("画面", True, True),
        ("記録の形", False, False),
    ]
    assert tags[0]["border"] != tags[1]["border"]
    expect(page.locator("[data-tags] > span").first.locator(".sr-only")).to_have_text("主題")


def test_two_main(open_story: OpenStory) -> None:
    """主題のタグが 2 つ。主題を先頭へ寄せず、記録の順のまま並べる（正常系）。"""
    # 準備・実行
    tags = open_story("shared-taglist--two-main").evaluate(_TAGS_JS)
    # 検証
    assert [(tag["name"], tag["main"]) for tag in tags] == [
        ("mindstella", False),
        ("ゴールと設定", True),
        ("画面", True),
    ]


def test_no_main(open_story: OpenStory) -> None:
    """主題のタグが無い。どのタグもマーカーを持たない（正常系）。"""
    # 準備・実行
    tags = open_story("shared-taglist--no-main").evaluate(_TAGS_JS)
    # 検証
    assert [(tag["name"], tag["marker"]) for tag in tags] == [
        ("mindstella", False),
        ("タスク", False),
    ]


def test_string_tags(open_story: OpenStory) -> None:
    """名前の文字列の並びを渡すと、どれも主題でないタグとして出す（正常系）。"""
    # 準備・実行
    tags = open_story("shared-taglist--string-tags").evaluate(_TAGS_JS)
    # 検証
    assert [(tag["name"], tag["main"], tag["marker"]) for tag in tags] == [
        ("通知", False, False),
        ("画面", False, False),
    ]


def test_long_narrow(open_story: OpenStory) -> None:
    """幅 320px で長い主題のタグを並べる。収まらないタグは次の行へ回し、マーカーは名前と同じ行に残す（正常系）。"""
    # 準備・実行
    page = open_story("shared-taglist--long-narrow")
    tags = page.locator("[data-tags] > span")
    first = tags.first.bounding_box()
    marker = tags.first.locator("svg").bounding_box()
    last = tags.last.bounding_box()
    # 検証
    assert first is not None
    assert marker is not None
    assert last is not None
    assert last["y"] > first["y"]
    assert first["y"] <= marker["y"] <= first["y"] + first["height"]
