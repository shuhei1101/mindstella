"""部品設計『保存待ちの印.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-pendingmark--pending",
    "shared-pendingmark--remove",
    "shared-pendingmark--blocked",
    "shared-pendingmark--pending-compact",
    "shared-pendingmark--remove-compact",
    "shared-pendingmark--blocked-compact",
    "shared-pendingmark--dark",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


# 枠の線の種類・枠の色・印の絵・大きさを返す
_MARK_JS = """(mark) => {
    const style = getComputedStyle(mark);
    return {
        line: style.borderTopStyle,
        color: style.borderTopColor,
        drawing: mark.querySelector('svg').innerHTML,
        width: mark.getBoundingClientRect().width,
        height: mark.getBoundingClientRect().height,
    };
}"""


def _mark(open_story: OpenStory, state: str) -> dict[str, object]:
    """ストーリーを開き、印の枠と絵を返す。"""
    return (
        open_story(f"shared-pendingmark--{state}")
        .locator("#storybook-root > span")
        .evaluate(_MARK_JS)
    )


def test_pending(open_story: OpenStory) -> None:
    """書き換え・追加の編集は、破線の枠に重ねた紙の印と「保存待ち」。印は読み上げに出さず、フォーカスも受けない（正常系）。"""
    # 準備・実行
    page = open_story("shared-pendingmark--pending")
    mark = page.locator("#storybook-root > span")
    # 検証
    expect(mark).to_have_text("保存待ち")
    assert mark.evaluate(_MARK_JS)["line"] == "dashed"
    assert mark.locator("svg").get_attribute("aria-hidden") == "true"
    assert mark.evaluate("e => e.tabIndex") == -1


def test_remove(open_story: OpenStory) -> None:
    """削除の編集は、保存待ちと違う色の破線の枠に、ゴミ箱の印と「保存で削除」（正常系）。"""
    # 準備
    pending = _mark(open_story, "pending")
    # 実行
    page = open_story("shared-pendingmark--remove")
    mark = page.locator("#storybook-root > span")
    remove = mark.evaluate(_MARK_JS)
    # 検証
    expect(mark).to_have_text("保存で削除")
    assert remove["line"] == "dashed"
    assert remove["color"] != pending["color"]
    assert remove["drawing"] != pending["drawing"]


def test_blocked(open_story: OpenStory) -> None:
    """保存で書き込めなかった編集は、実線の枠に警告の印と「書き込めない」（正常系）。"""
    # 準備
    pending = _mark(open_story, "pending")
    # 実行
    page = open_story("shared-pendingmark--blocked")
    mark = page.locator("#storybook-root > span")
    blocked = mark.evaluate(_MARK_JS)
    # 検証
    expect(mark).to_have_text("書き込めない")
    assert blocked["line"] == "solid"
    assert blocked["drawing"] != pending["drawing"]


@pytest.mark.parametrize(
    ("state", "label", "line"),
    [
        pytest.param("pending-compact", "保存待ち", "dashed", id="pending"),
        pytest.param("remove-compact", "保存で削除", "dashed", id="remove"),
        pytest.param("blocked-compact", "書き込めない", "solid", id="blocked"),
    ],
)
def test_compact(open_story: OpenStory, state: str, label: str, line: str) -> None:
    """印だけの形は幅 20px・高さ 18px の枠に印だけを出し、文字は読み上げと `title` に残す（正常系）。"""
    # 準備・実行
    page = open_story(f"shared-pendingmark--{state}")
    mark = page.locator("#storybook-root > span")
    shape = mark.evaluate(_MARK_JS)
    # 検証
    expect(mark).to_have_attribute("title", label)
    expect(mark.locator(".sr-only")).to_have_text(label)
    assert (shape["width"], shape["height"], shape["line"]) == (20, 18, line)


def test_dark(open_story: OpenStory) -> None:
    """ダークで 3 種類を並べる。ダークのトークンで描き、3 種類の枠の色が分かれる（正常系）。"""
    # 準備・実行
    page = open_story("shared-pendingmark--dark")
    marks = page.locator("#storybook-root > div > span")
    colors = marks.evaluate_all("items => items.map((e) => getComputedStyle(e).borderTopColor)")
    # 検証
    expect(marks).to_have_text(["保存待ち", "保存で削除", "書き込めない"])
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    assert len(set(colors)) == 3
