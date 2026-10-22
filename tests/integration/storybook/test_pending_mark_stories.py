"""部品設計『保存待ちの印』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from integration.preview.preview_a11y_checks import axe_rule_results
from storybook_fixture_types import OpenStory

# 印
MARK = ".pm"

# 印の枠の線の種類・枠の色・文字の色・幅と高さを読む
LOOK_SCRIPT = """e => {
  const style = getComputedStyle(e);
  const box = e.getBoundingClientRect();
  return {
    borderStyle: style.borderTopStyle,
    borderColor: style.borderTopColor,
    color: style.color,
    size: [Math.round(box.width), Math.round(box.height)],
  };
}"""

# 印と中身がフォーカスを受ける要素を持たず、押す操作を持たないかを数える
INTERACTIVE_SCRIPT = """() => document.querySelectorAll(
    ".pm button, .pm a, .pm [tabindex], .pm input, button.pm, a.pm, .pm[tabindex]"
).length"""

# 種類ごとの札の文字と枠の線の種類
KINDS = [
    pytest.param("pending", "保存待ち", "dashed", id="pending"),
    pytest.param("remove", "保存で削除", "dashed", id="remove"),
    pytest.param("blocked", "書き込めない", "solid", id="blocked"),
]


@pytest.mark.parametrize(("kind", "label", "border"), KINDS)
def test_states(open_story: OpenStory, kind: str, label: str, border: str) -> None:
    """種類ごとに枠の線（書き込めないだけ実線）と印と文字の札を出す（正常系）。"""
    # 準備・実行
    page = open_story(f"preview-pendingmark--{kind}")
    # 検証
    mark = page.locator(MARK)
    assert mark.count() == 1
    assert mark.inner_text() == label
    assert mark.locator("svg.icon").count() == 1
    assert page.eval_on_selector(MARK, LOOK_SCRIPT)["borderStyle"] == border
    assert page.locator(f"{MARK}.pm-compact").count() == 0


def test_kinds_are_distinguishable(open_story: OpenStory) -> None:
    """3 種類は、枠の色・文字の色・印の形のどれかで見分けられる。色だけに頼らない（正常系）。"""
    # 準備・実行
    looks = {}
    shapes = {}
    for kind in ("pending", "remove", "blocked"):
        page = open_story(f"preview-pendingmark--{kind}")
        looks[kind] = page.eval_on_selector(MARK, LOOK_SCRIPT)
        shapes[kind] = page.eval_on_selector(f"{MARK} svg.icon", "e => e.innerHTML")
    # 検証
    assert len({looks[kind]["color"] for kind in looks}) == 3
    assert len(set(shapes.values())) == 3
    assert looks["pending"]["borderStyle"] != looks["blocked"]["borderStyle"]


@pytest.mark.parametrize(("kind", "label"), [
    pytest.param("pending", "保存待ち", id="pending"),
    pytest.param("remove", "保存で削除", id="remove"),
    pytest.param("blocked", "書き込めない", id="blocked"),
])
def test_compact(open_story: OpenStory, kind: str, label: str) -> None:
    """印だけの形。幅 20px・高さ 18px の枠に印だけを出し、文字は読み上げと title に残す（正常系）。"""
    # 準備・実行
    page = open_story(f"preview-pendingmark--{kind}-compact")
    # 検証
    mark = page.locator(f"{MARK}.pm-compact")
    assert mark.count() == 1
    assert page.eval_on_selector(MARK, LOOK_SCRIPT)["size"] == [20, 18]
    assert mark.get_attribute("title") == label
    assert mark.locator(".sr-only").inner_text() == label
    # 文字は画面に出ない（印だけ）
    assert mark.locator("svg.icon").count() == 1
    assert page.eval_on_selector(f"{MARK} .sr-only", "e => e.getBoundingClientRect().width") <= 1


def test_dark(open_story: OpenStory) -> None:
    """ダークで 3 種類を並べる。文字は読める濃さ（コントラストの規則に違反しない）で、ライトとは色が変わる（正常系）。"""
    # 準備
    light = open_story("preview-pendingmark--pending")
    light_color = light.eval_on_selector(MARK, LOOK_SCRIPT)["color"]
    # 実行
    page = open_story("preview-pendingmark--dark")
    result = axe_rule_results(page, "#storybook-root", "color-contrast")
    # 検証
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    assert page.locator(MARK).count() == 3
    assert page.locator(MARK).first.evaluate(LOOK_SCRIPT)["color"] != light_color
    assert result["violations"] == []
    assert result["passes"] != []


def test_accessibility(open_story: OpenStory) -> None:
    """印は読み上げから外して文字で持ち、押す操作とフォーカスを持たない（正常系）。"""
    # 準備・実行
    page = open_story("preview-pendingmark--pending")
    # 検証
    assert page.get_attribute(f"{MARK} svg.icon", "aria-hidden") == "true"
    assert page.evaluate(INTERACTIVE_SCRIPT) == 0
    # Tab キーを押しても、印にフォーカスが当たらない
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement?.closest('.pm') ?? null") is None
