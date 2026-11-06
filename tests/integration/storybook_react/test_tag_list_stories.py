"""部品設計『タグの並び.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-taglist--one-main", "shared-taglist--two-main", "shared-taglist--no-main", "shared-taglist--string-tags", "shared-taglist--long-narrow",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    page = open_story(state)
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_main_tag(open_story: OpenStory) -> None:
    """主題のタグは名前に主題の印を添え、主題でないタグには添えない（正常系）。"""
    page = open_story("shared-taglist--one-main")
    expect(page.get_by_title("主題")).to_have_count(1)
    assert open_story("shared-taglist--no-main").get_by_title("主題").count() == 0
    assert "通知" in open_story("shared-taglist--string-tags").inner_text("#storybook-root")
