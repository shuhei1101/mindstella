"""部品設計『本文の目次.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-bodytoc--default",
    "shared-bodytoc--open",
    "shared-bodytoc--long-heading",
)

# 長い見出しの全文
LONG_TEXT = "記録をワークスペースの直下とホームの設定フォルダのどちらに置くかを比べた結果と、それぞれの持ち出しやすさ"

# 要素の左の内側の余白（px）
_PADDING_LEFT_JS = "e => parseFloat(getComputedStyle(e).paddingLeft)"


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_default(open_story: OpenStory) -> None:
    """閉じた目次のボタンを、読み上げの名前とツールチップつきのアイコンだけで出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-bodytoc--default")
    button = page.get_by_role("button", name="本文の目次")
    # 検証
    expect(button).to_be_visible()
    expect(button).to_have_attribute("title", "本文の目次")
    expect(button).to_have_text("")
    expect(page.get_by_role("navigation", name="本文の目次")).to_have_count(0)


def test_open(open_story: OpenStory) -> None:
    """開いた目次の上端に「目次」を置き、下の階層の見出しを字下げする。Esc で閉じてボタンへフォーカスを戻す（正常系）。"""
    # 準備
    page = open_story("shared-bodytoc--open")
    nav = page.get_by_role("navigation", name="本文の目次")
    items = nav.get_by_role("button")
    # 検証
    expect(page.get_by_text("目次", exact=True)).to_be_visible()
    expect(items).to_have_text(["目的", "保存先", "決め方", "残る論点"])
    paddings = [items.nth(index).evaluate(_PADDING_LEFT_JS) for index in range(3)]
    assert paddings[0] < paddings[1] < paddings[2]
    # 実行
    page.keyboard.press("Escape")
    # 検証
    expect(nav).to_have_count(0)
    expect(page.get_by_role("button", name="本文の目次")).to_be_focused()


def test_long_heading(open_story: OpenStory) -> None:
    """長い見出しを 1 行で省略し、全文を title に持たせる（正常系）。"""
    # 準備・実行
    page = open_story("shared-bodytoc--long-heading")
    item = page.get_by_role("navigation", name="本文の目次").get_by_role("button", name=LONG_TEXT)
    # 検証
    expect(item).to_have_attribute("title", LONG_TEXT)
    assert item.evaluate("e => getComputedStyle(e).textOverflow") == "ellipsis"
    assert item.evaluate("e => e.scrollWidth > e.clientWidth") is True
