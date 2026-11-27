"""部品設計『お気に入りの星.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-favoritetoggle--off",
    "shared-favoritetoggle--on",
    "shared-favoritetoggle--focused",
)

# 星のボタンの読み上げ名（ストーリーの title は「画面の配色の比較」）
BUTTON_NAME = "画面の配色の比較をお気に入りに登録"


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


@pytest.mark.parametrize(
    ("state", "pressed"),
    [
        pytest.param("shared-favoritetoggle--off", "false", id="off"),
        pytest.param("shared-favoritetoggle--on", "true", id="on"),
    ],
)
def test_pressed(open_story: OpenStory, state: str, pressed: str) -> None:
    """登録しているかを aria-pressed で示し、読み上げ名に項目のタイトルを含める（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    button = page.get_by_role("button", name=BUTTON_NAME)
    expect(button).to_have_attribute("aria-pressed", pressed)


def test_focused(open_story: OpenStory) -> None:
    """キーボードでフォーカスすると星のボタンにフォーカスが当たり、輪郭を出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-favoritetoggle--focused")
    # 検証
    button = page.get_by_role("button", name=BUTTON_NAME)
    expect(button).to_be_focused()
    assert button.evaluate("(el) => getComputedStyle(el).outlineStyle") != "none"
