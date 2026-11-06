"""部品設計『変更履歴.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-historydialog--since-selected", "shared-historydialog--off", "shared-historydialog--no-pending", "shared-historydialog--long-name", "shared-historydialog--narrow",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    page = open_story(state)
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_current_is_checked(open_story: OpenStory) -> None:
    """選んでいる時点に印を付ける（正常系）。"""
    page = open_story("shared-historydialog--since-selected")
    expect(page.get_by_role("dialog")).to_contain_text("前回開いてから")
    expect(page.get_by_role("dialog")).to_contain_text("まだまとめていない変更")


def test_no_pending(open_story: OpenStory) -> None:
    """まだまとめていない変更が無いときは行を出さない（正常系）。"""
    expect(open_story("shared-historydialog--no-pending").get_by_role("dialog")).not_to_contain_text("まだまとめていない変更")
