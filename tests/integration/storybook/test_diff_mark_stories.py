"""部品設計『差分の印』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory

# 印の記号の色を読む
COLOR_SCRIPT = "e => getComputedStyle(e).color"

# 塗りの色を読む
FILL_SCRIPT = "e => getComputedStyle(e).fill"


def test_new(open_story: OpenStory) -> None:
    """新規。丸や枠で囲まず太い + だけを出し、名前は読み上げと title に持つ（正常系）。"""
    # 準備・実行
    page = open_story("preview-diffmark--new")
    # 検証
    mark = page.locator(".df-mark.df-new")
    assert mark.count() == 1
    assert mark.get_attribute("title") == "新規"
    assert mark.locator(".sr-only").inner_text() == "新規"
    assert mark.locator("svg.icon").get_attribute("aria-hidden") == "true"
    assert page.locator(".df-badge").count() == 0
    assert page.eval_on_selector(".df-mark", "e => getComputedStyle(e).borderTopWidth") == "0px"


def test_changed(open_story: OpenStory) -> None:
    """変更。丸や枠で囲まず塗った ● だけを出し、決定済みの状態の印とは色で分かれる（正常系）。"""
    # 準備・実行
    page = open_story("preview-diffmark--changed")
    # 検証
    mark = page.locator(".df-mark.df-chg")
    assert mark.count() == 1
    assert mark.get_attribute("title") == "変更"
    assert mark.locator(".sr-only").inner_text() == "変更"
    assert page.eval_on_selector(".df-mark svg.icon", FILL_SCRIPT) != "none"
    # 決定済みの状態の印（緑）とは違う色
    done = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--st-done').trim()")
    assert done != ""
    assert page.eval_on_selector(".df-mark", COLOR_SCRIPT) != page.evaluate(
        "(color) => { const e = document.createElement('i'); e.style.color = color; document.body.append(e); const c = getComputedStyle(e).color; e.remove(); return c; }",
        done,
    )


def test_new_labeled(open_story: OpenStory) -> None:
    """詳細パネルの題の横の新規の札。記号に「新規」の文言を付ける（正常系）。"""
    # 準備・実行
    page = open_story("preview-diffmark--new-labeled")
    # 検証
    badge = page.locator(".df-badge.df-new")
    assert badge.count() == 1
    assert badge.inner_text() == "新規"
    assert badge.locator("svg.icon").count() == 1
    assert page.locator(".df-mark").count() == 0
