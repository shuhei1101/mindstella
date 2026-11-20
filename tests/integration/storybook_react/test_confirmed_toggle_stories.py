"""部品設計『確認済みの切り替え.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-confirmedtoggle--unconfirmed",
    "shared-confirmedtoggle--confirmed",
    "shared-confirmedtoggle--saving",
    "shared-confirmedtoggle--in-detail-header",
)

# 幅 480px 以下（文言を隠してアイコンだけにする幅）の画面幅
NARROW_WIDTH = 480

# 文言の見た目の幅と高さを返す（sr-only は 1px 四方）
_LABEL_SIZE_JS = """(element) => { const b = element.getBoundingClientRect(); return { width: b.width, height: b.height }; }"""


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_unconfirmed(open_story: OpenStory) -> None:
    """未確認。空のチェックと「確認済み」で、押した状態ではなく、押すと確認済みにする旨の title を持つ（正常系）。"""
    # 準備・実行
    page = open_story("shared-confirmedtoggle--unconfirmed")
    button = page.get_by_role("button", name="確認済み")
    # 検証
    expect(button).to_have_attribute("aria-pressed", "false")
    expect(button).to_have_attribute("title", "確認済みにする")
    expect(button).to_be_enabled()


def test_confirmed(open_story: OpenStory) -> None:
    """確認済み。押した状態で、解除する旨の title を持ち、色が未確認と違う（正常系）。"""
    # 準備
    unconfirmed = open_story("shared-confirmedtoggle--unconfirmed").get_by_role("button", name="確認済み").evaluate("(e) => getComputedStyle(e).color")
    # 実行
    page = open_story("shared-confirmedtoggle--confirmed")
    button = page.get_by_role("button", name="確認済み")
    # 検証
    expect(button).to_have_attribute("aria-pressed", "true")
    expect(button).to_have_attribute("title", "確認済みを解除する")
    assert button.evaluate("(e) => getComputedStyle(e).color") != unconfirmed


def test_saving(open_story: OpenStory) -> None:
    """書き込みの応答を待っている間は押せない（正常系）。"""
    # 準備・実行
    page = open_story("shared-confirmedtoggle--saving")
    # 検証
    expect(page.get_by_role("button", name="確認済み")).to_be_disabled()


def test_in_detail_header(open_story: OpenStory) -> None:
    """詳細パネルの見出しで種類と ID の後・「編集する」の前に並び、幅 480px 以下では文言を見た目から外して読み上げには残す（正常系）。"""
    # 準備
    page = open_story("shared-confirmedtoggle--in-detail-header")
    names = page.locator("#storybook-root button").evaluate_all("(buttons) => buttons.map((b) => b.getAttribute('aria-label') ?? b.textContent.trim())")
    # 実行
    page.set_viewport_size({"width": NARROW_WIDTH, "height": 800})
    label = page.get_by_role("button", name="確認済み").locator("span")
    # 検証
    assert names[:2] == ["確認済み", "編集する"]
    assert label.evaluate(_LABEL_SIZE_JS) == {"width": 1, "height": 1}
    expect(page.get_by_role("button", name="確認済み")).to_be_visible()
