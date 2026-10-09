"""部品設計『コメントの印』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from storybook_fixture_types import OpenStory

# 印の中の「画面の数字」の要素
NUMBER = ".cmk .cmk-n"

# 印と中身がフォーカスを受ける要素を持たず、押す操作（ボタン・リンク・tabindex）を持たないかを数える
INTERACTIVE_SCRIPT = """() => document.querySelectorAll(
    ".cmk button, .cmk a, .cmk [tabindex], .cmk input, button.cmk, a.cmk, .cmk[tabindex]"
).length"""


@pytest.mark.parametrize(
    ("story", "shown", "spoken"),
    [
        pytest.param("preview-commentmark--one", "1", "コメント 1 件", id="one"),
        pytest.param("preview-commentmark--two-digits", "12", "コメント 12 件", id="two_digits"),
        pytest.param("preview-commentmark--overflow", "99+", "コメント 128 件", id="overflow"),
    ],
)
def test_states(open_story: OpenStory, story: str, shown: str, spoken: str) -> None:
    """吹き出しの線と件数を出し、99 を超えると画面は「99+」、読み上げの文字と title は実数にする（正常系）。"""
    # 準備・実行
    page = open_story(story)
    # 検証
    mark = page.locator(".cmk")
    assert mark.count() == 1
    assert page.inner_text(NUMBER) == shown
    assert mark.locator("svg.icon").count() == 1
    assert mark.locator(".sr-only").text_content() == spoken
    assert mark.get_attribute("title") == spoken


def test_accessibility(open_story: OpenStory) -> None:
    """吹き出しと数字は読み上げから外し、押す操作とフォーカスを持たない（正常系）。"""
    # 準備・実行
    page = open_story("preview-commentmark--overflow")
    # 検証
    assert page.get_attribute(".cmk svg.icon", "aria-hidden") == "true"
    assert page.get_attribute(NUMBER, "aria-hidden") == "true"
    assert page.get_attribute(".cmk .sr-only", "aria-hidden") is None
    assert page.evaluate(INTERACTIVE_SCRIPT) == 0
    # Tab キーを押しても、印にフォーカスが当たらない
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement?.closest('.cmk') ?? null") is None
