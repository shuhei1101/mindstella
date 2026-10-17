"""部品設計『本文の差分の並べ方の切り替え』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from storybook_fixture_types import OpenStory

# 切り替えのボタンの組
SWITCH = ".sbs-switch"

# ボタンごとに、文言・並べ方・押している状態を返す
_BUTTONS_JS = """() => [...document.querySelectorAll('.sbs-switch button')].map((button) => ({
    name: button.textContent.trim(),
    layout: button.getAttribute('data-layout'),
    pressed: button.getAttribute('aria-pressed'),
}))"""

# フォーカスのあるボタンの並べ方と、フォーカスの輪（アウトライン）の太さと色が背景と違うかを返す
_FOCUS_JS = """() => {
    const button = document.activeElement;
    const style = getComputedStyle(button);
    return {
        layout: button.getAttribute('data-layout'),
        focusVisible: button.matches(':focus-visible'),
        outlineStyle: style.outlineStyle,
        outlineWidth: style.outlineWidth,
        ringed: style.outlineStyle !== 'none' || style.boxShadow !== 'none',
    };
}"""


def _open(open_story: OpenStory, state: str) -> Page:
    """ストーリーを開く。"""
    return open_story(f"preview-bodydifflayoutswitch--{state}")


def test_inline(open_story: OpenStory) -> None:
    """既定。「インライン」を押した状態で、ボタンの組は読み上げの名前「本文の差分の並べ方」を持つ（正常系）。"""
    # 準備・実行
    page = _open(open_story, "inline")
    # 検証
    assert page.get_attribute(SWITCH, "role") == "group"
    assert page.get_attribute(SWITCH, "aria-label") == "本文の差分の並べ方"
    assert page.evaluate(_BUTTONS_JS) == [
        {"name": "インライン", "layout": "inline", "pressed": "true"},
        {"name": "左右に並べる", "layout": "side", "pressed": "false"},
    ]


def test_side(open_story: OpenStory) -> None:
    """「左右に並べる」を押した状態（正常系）。"""
    # 準備・実行
    page = _open(open_story, "side")
    # 検証
    assert page.evaluate(_BUTTONS_JS) == [
        {"name": "インライン", "layout": "inline", "pressed": "false"},
        {"name": "左右に並べる", "layout": "side", "pressed": "true"},
    ]


def test_focus_on_other(open_story: OpenStory) -> None:
    """「インライン」を押したまま、「左右に並べる」にキーボードのフォーカスを置くと、印の色の輪を出す。押している状態は変わらない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "focus-on-other")
    page.wait_for_function("document.activeElement?.getAttribute('data-layout') === 'side'")
    # 検証
    focus = page.evaluate(_FOCUS_JS)
    assert focus["layout"] == "side"
    assert focus["focusVisible"] is True
    assert focus["ringed"] is True
    assert [button["pressed"] for button in page.evaluate(_BUTTONS_JS)] == ["true", "false"]
