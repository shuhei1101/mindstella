"""部品設計『表.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = ("shared-table--default", "shared-table--sorted-asc", "shared-table--sorted-desc", "shared-table--filtered", "shared-table--pinned", "shared-table--long-title", "shared-table--no-match", "shared-table--columns-popover", "shared-table--marked", "shared-table--text-filtered", "shared-table--commented", "shared-table--withdrawn",)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    page = open_story(state)
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_sort_direction(open_story: OpenStory) -> None:
    """並べている列に `aria-sort` を付ける（正常系）。"""
    expect(open_story("shared-table--sorted-asc").get_by_role("columnheader", name="タイトル")).to_have_attribute("aria-sort", "ascending")
    expect(open_story("shared-table--sorted-desc").get_by_role("columnheader", name="タイトル")).to_have_attribute("aria-sort", "descending")


def test_filtered_chips(open_story: OpenStory) -> None:
    """条件のチップと「すべて解除」を並べる（正常系）。"""
    page = open_story("shared-table--filtered")
    expect(page.get_by_text("確度: 高")).to_be_visible()
    expect(page.get_by_role("button", name="すべて解除")).to_be_visible()


def test_pinned(open_story: OpenStory) -> None:
    """押した列のボタンだけを押された見た目にする（正常系）。"""
    page = open_story("shared-table--pinned")
    expect(page.get_by_role("button", name="IDまで固定")).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_role("button", name="タイトルまで固定")).to_have_attribute("aria-pressed", "false")


def test_no_match(open_story: OpenStory) -> None:
    """該当なしの文言を出す（正常系）。"""
    expect(open_story("shared-table--no-match").get_by_text("別の条件を試してください")).to_be_visible()


def test_columns_popover(open_story: OpenStory) -> None:
    """列の表示でタイトルの列は外せない（正常系）。"""
    page = open_story("shared-table--columns-popover")
    page.get_by_role("button", name="列の表示").click()
    expect(page.get_by_role("checkbox", name="タイトル")).to_be_disabled()


def test_marked_and_commented(open_story: OpenStory) -> None:
    """差分の印とコメントの印をタイトルの右に置く（正常系）。"""
    assert "変更" in (open_story("shared-table--marked").text_content("tr[data-id='D-5']") or "")
    assert "12" in (open_story("shared-table--commented").text_content("tr[data-id='D-37']") or "")


def test_withdrawn(open_story: OpenStory) -> None:
    """取り下げた行に札を置く（正常系）。"""
    page = open_story("shared-table--withdrawn")
    assert "取り下げ" in (page.text_content("tr[data-id='R-1']") or "")
    assert "取り下げ" not in (page.text_content("tr[data-id='R-2']") or "")


def test_text_filtered(open_story: OpenStory) -> None:
    """文字の条件のチップを出す（正常系）。"""
    expect(open_story("shared-table--text-filtered").get_by_text("用語に「移し」を含む")).to_be_visible()
