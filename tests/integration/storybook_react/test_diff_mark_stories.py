"""部品設計『差分の印.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-diffmark--new",
    "shared-diffmark--changed",
    "shared-diffmark--new-labeled",
    "shared-diffmark--removed",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


# 記号の絵（path の d）・色・大きさを返す
_MARK_JS = """(mark) => {
    const svg = mark.querySelector('svg');
    return {
        drawing: svg.innerHTML,
        color: getComputedStyle(mark).color,
        width: svg.getBoundingClientRect().width,
        border: getComputedStyle(mark).borderTopWidth,
    };
}"""


def _mark(open_story: OpenStory, state: str) -> dict[str, object]:
    """ストーリーを開き、印の記号の絵・色・大きさを返す。"""
    return (
        open_story(f"shared-diffmark--{state}").locator("#storybook-root > span").evaluate(_MARK_JS)
    )


def test_new(open_story: OpenStory) -> None:
    """新規は、丸や枠で囲まず記号だけで、読み上げと `title` に「新規」を持つ（正常系）。"""
    # 準備・実行
    page = open_story("shared-diffmark--new")
    mark = page.locator("#storybook-root > span")
    # 検証
    expect(mark).to_have_attribute("title", "新規")
    expect(mark.locator(".sr-only")).to_have_text("新規")
    assert mark.locator("svg").get_attribute("aria-hidden") == "true"
    assert mark.evaluate(_MARK_JS)["border"] == "0px"


def test_changed(open_story: OpenStory) -> None:
    """変更は、新規と違う記号と色で、読み上げと `title` に「変更」を持つ（正常系）。"""
    # 準備
    new = _mark(open_story, "new")
    # 実行
    page = open_story("shared-diffmark--changed")
    mark = page.locator("#storybook-root > span")
    changed = mark.evaluate(_MARK_JS)
    # 検証
    expect(mark).to_have_attribute("title", "変更")
    assert changed["drawing"] != new["drawing"]
    assert changed["color"] != new["color"]


def test_new_labeled(open_story: OpenStory) -> None:
    """詳細パネルの題の横の新規の札は、記号に「新規」の文言を付け、枠で囲む（正常系）。"""
    # 準備・実行
    page = open_story("shared-diffmark--new-labeled")
    mark = page.locator("#storybook-root > span")
    # 検証
    expect(mark).to_have_text("新規")
    assert mark.evaluate(_MARK_JS)["border"] == "1px"


def test_removed(open_story: OpenStory) -> None:
    """消したは、新規・変更と違う記号と色で、同じ大きさ。読み上げと `title` に「消した」を持つ（正常系）。"""
    # 準備
    new = _mark(open_story, "new")
    changed = _mark(open_story, "changed")
    # 実行
    page = open_story("shared-diffmark--removed")
    mark = page.locator("#storybook-root > span")
    removed = mark.evaluate(_MARK_JS)
    # 検証
    expect(mark).to_have_attribute("title", "消した")
    assert removed["drawing"] not in (new["drawing"], changed["drawing"])
    assert removed["color"] not in (new["color"], changed["color"])
    assert removed["width"] == new["width"] == changed["width"]
