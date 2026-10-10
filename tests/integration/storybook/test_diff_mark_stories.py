"""部品設計『差分の印』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory

# 印の記号の色を読む
COLOR_SCRIPT = "e => getComputedStyle(e).color"

# 塗りの色を読む
FILL_SCRIPT = "e => getComputedStyle(e).fill"

# 印の幅と高さを読む
SIZE_SCRIPT = "e => [e.getBoundingClientRect().width, e.getBoundingClientRect().height]"


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


def test_removed(open_story: OpenStory) -> None:
    """消した。丸や枠で囲まず差分の色の赤の太い − だけを出し、新規・変更と同じ大きさで、名前は読み上げと title に持つ（正常系）。"""
    # 準備・実行
    page = open_story("preview-diffmark--removed")
    # 検証
    mark = page.locator(".df-mark.df-del")
    assert mark.count() == 1
    assert mark.get_attribute("title") == "消した"
    assert mark.locator(".sr-only").inner_text() == "消した"
    assert mark.locator("svg.icon").get_attribute("aria-hidden") == "true"
    assert page.locator(".df-badge").count() == 0
    assert page.eval_on_selector(".df-mark", "e => getComputedStyle(e).borderTopWidth") == "0px"
    # 差分の色の赤。新規・変更の印の色とは違う
    removed_color = page.eval_on_selector(".df-mark", COLOR_SCRIPT)
    assert removed_color == page.evaluate(
        "(() => { const e = document.createElement('i'); e.style.color = getComputedStyle(document.documentElement).getPropertyValue('--df-del'); document.body.append(e); const c = getComputedStyle(e).color; e.remove(); return c; })()"
    )
    # 形は − 1 本の線で、新規の + と変更の ● とは別
    assert page.locator(".df-mark svg.icon path").count() == 1
    assert page.eval_on_selector(".df-mark svg.icon path", "e => e.getAttribute('d')") == "M5 12h14"
    removed_size = page.eval_on_selector(".df-mark", SIZE_SCRIPT)
    # 色は新規・変更の印と違い、大きさは同じ
    new_page = open_story("preview-diffmark--new")
    assert new_page.eval_on_selector(".df-mark", COLOR_SCRIPT) != removed_color
    assert new_page.eval_on_selector(".df-mark", SIZE_SCRIPT) == removed_size
    changed_page = open_story("preview-diffmark--changed")
    assert changed_page.eval_on_selector(".df-mark", COLOR_SCRIPT) != removed_color
    assert changed_page.eval_on_selector(".df-mark", SIZE_SCRIPT) == removed_size
