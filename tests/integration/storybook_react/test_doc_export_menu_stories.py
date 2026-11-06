"""部品設計『資料のエクスポートのメニュー.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-docexportmenu--choose", "shared-docexportmenu--warn", "shared-docexportmenu--busy", "shared-docexportmenu--error", "shared-docexportmenu--back-from-warn", "shared-docexportmenu--narrow", "shared-docexportmenu--warn-narrow",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    page = open_story(state)
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_views(open_story: OpenStory) -> None:
    """中身を替えて出す（正常系）。"""
    expect(open_story("shared-docexportmenu--choose").get_by_role("button", name="HTML でエクスポート")).to_be_visible()
    expect(open_story("shared-docexportmenu--warn").get_by_role("button", name="エクスポート", exact=True)).to_be_focused()
    expect(open_story("shared-docexportmenu--busy").get_by_role("status")).to_have_text("エクスポートしています…")
    expect(open_story("shared-docexportmenu--error").get_by_role("button", name="再試行")).to_be_focused()


def test_back_from_warn_focus(open_story: OpenStory) -> None:
    """警告から戻した行へフォーカスを置く（正常系）。"""
    expect(open_story("shared-docexportmenu--back-from-warn").get_by_role("button", name="Markdown でエクスポート")).to_be_focused()
