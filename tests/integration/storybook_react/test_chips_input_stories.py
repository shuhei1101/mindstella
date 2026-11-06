"""部品設計『チップの入力.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-chipsinput--default", "shared-chipsinput--main-toggle", "shared-chipsinput--main-toggle-disabled", "shared-chipsinput--main-toggle-long-narrow",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    page = open_story(state)
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_main_toggle(open_story: OpenStory) -> None:
    """主題のトグルは押した状態を伝える（正常系）。"""
    page = open_story("shared-chipsinput--main-toggle")
    expect(page.get_by_role("button", name="画面 を主題")).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_role("button", name="通知 を主題")).to_have_attribute("aria-pressed", "false")


def test_disabled(open_story: OpenStory) -> None:
    """削除を溜めた項目では入力欄と外すボタンを押せない（正常系）。"""
    page = open_story("shared-chipsinput--main-toggle-disabled")
    expect(page.get_by_role("combobox")).to_be_disabled()
    expect(page.get_by_role("button", name="画面 を外す")).to_be_disabled()


def test_default_has_no_toggle(open_story: OpenStory) -> None:
    """参照の ID は主題のトグルを持たない（正常系）。"""
    assert open_story("shared-chipsinput--default").get_by_role("button", name="D-1 を主題").count() == 0
