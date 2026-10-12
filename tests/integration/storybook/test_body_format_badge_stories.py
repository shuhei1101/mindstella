"""部品設計『本文の形式の札』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory

# 札の高さ・枠の太さ・地の色・文字の書体を読む
BADGE_SCRIPT = """(selector) => {
    const style = getComputedStyle(document.querySelector(selector));
    return {
        height: parseFloat(style.height),
        border: style.borderTopWidth,
        background: style.backgroundColor,
        fontFamily: style.fontFamily,
    };
}"""

# 札の高さ
BADGE_HEIGHT_PX = 20

# 地を敷かない札の背景
TRANSPARENT = "rgba(0, 0, 0, 0)"


def test_markdown(open_story: OpenStory) -> None:
    """Markdown の資料は、地を敷かず、細い枠と `MD` の文字で出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-bodyformatbadge--markdown")
    # 検証
    badge = page.locator(".fmt-badge.fmt-md")
    assert badge.count() == 1
    assert badge.inner_text() == "MD"
    assert badge.get_attribute("title") == "本文は Markdown"
    style = page.evaluate(BADGE_SCRIPT, ".fmt-badge")
    assert style["border"] == "1px"
    assert style["background"] == TRANSPARENT
    assert style["height"] == BADGE_HEIGHT_PX


def test_html(open_story: OpenStory) -> None:
    """HTML の資料は、地の面を敷いた `HTML` の文字で出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-bodyformatbadge--html")
    # 検証
    badge = page.locator(".fmt-badge.fmt-html")
    assert badge.count() == 1
    assert badge.inner_text() == "HTML"
    assert badge.get_attribute("title") == "本文は HTML"
    style = page.evaluate(BADGE_SCRIPT, ".fmt-badge")
    assert style["border"] == "1px"
    assert style["background"] != TRANSPARENT
    assert style["height"] == BADGE_HEIGHT_PX


def test_beside_other_badges(open_story: OpenStory) -> None:
    """種類・状態の札（完成）・取り下げの札・納品物の印と並べ、等幅の文字と地で見分けられる（正常系）。"""
    # 準備・実行
    page = open_story("preview-bodyformatbadge--beside-other-badges")
    # 検証
    assert page.locator(".fmt-badge").inner_text() == "HTML"
    assert page.locator(".st").inner_text() == "完成"
    assert page.locator(".wd-badge").inner_text() == "取り下げ"
    assert page.locator(".deliv-badge").count() == 1
    # 形式の札だけが等幅の書体と地の面を持つ
    format_badge = page.evaluate(BADGE_SCRIPT, ".fmt-badge")
    status_badge = page.evaluate(BADGE_SCRIPT, ".st")
    assert format_badge["fontFamily"] != status_badge["fontFamily"]
    assert format_badge["background"] != TRANSPARENT
