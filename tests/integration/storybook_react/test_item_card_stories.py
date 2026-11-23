"""部品設計『項目のカード.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Locator, expect

from .storybook_react_fixture_types import OpenStory

# カードの右端・下端からマーカーまでの許す差（パディング分。px）
EDGE_TOLERANCE_PX = 12

# 部品設計の状態
STATES = (
    "shared-itemcard--selectable-tags",
    "shared-itemcard--selectable-tags-selected",
    "shared-itemcard--default",
    "shared-itemcard--with-comments",
    "shared-itemcard--selected-with-comments",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_selectable_tags(open_story: OpenStory) -> None:
    """外枠は div で、タイトルのボタンとタグのボタンを入れ子にせず並べる（正常系）。"""
    # 準備・実行
    page = open_story("shared-itemcard--selectable-tags")
    card = page.locator("div[data-card='T-1']")
    # 検証
    expect(card.locator("button[data-id='T-1']")).to_have_text("絞り込みの条件をタブの保存領域に残す")
    expect(card.locator("button[data-tag]")).to_have_count(3)
    expect(card.get_by_role("button", name="タグ「保存」で絞り込む")).to_be_visible()
    assert page.locator("button button").count() == 0
    expect(card.locator("button[data-id='T-1']")).not_to_have_attribute("aria-current", "true")


def test_selectable_tags_selected(open_story: OpenStory) -> None:
    """開いている項目のタイトルに aria-current を付け、タグを押せるまま残す（正常系）。"""
    # 準備・実行
    page = open_story("shared-itemcard--selectable-tags-selected")
    card = page.locator("div[data-card='T-1']")
    # 検証
    expect(card.locator("button[data-id='T-1']")).to_have_attribute("aria-current", "true")
    expect(card.locator("button[data-tag]")).to_have_count(3)


def test_default(open_story: OpenStory) -> None:
    """onSelectTag を指定しないカードはタグを並べない（正常系）。"""
    # 準備・実行
    page = open_story("shared-itemcard--default")
    card = page.locator("div[data-card='T-1']")
    # 検証
    expect(card.locator("button[data-id='T-1']")).to_be_visible()
    expect(card.locator("[data-tag]")).to_have_count(0)


def _mark_box(page_card: Locator) -> dict[str, float]:
    """カードとコメントのマーカーの位置を返す（マーカーの右端・下端とカードの右端・下端の差、ID の行の下端）。"""
    return page_card.evaluate(
        """(card) => {
            const box = card.getBoundingClientRect();
            const mark = card.querySelector('[title^="コメント"]').getBoundingClientRect();
            const idRow = card.querySelector('.font-mono').getBoundingClientRect();
            return {right: box.right - mark.right, bottom: box.bottom - mark.bottom, markTop: mark.top, idBottom: idRow.bottom};
        }"""
    )


def test_with_comments(open_story: OpenStory) -> None:
    """コメントのマーカーをカードの一番下の行の右に配置し、ID の行には配置しない（正常系）。"""
    # 準備・実行
    page = open_story("shared-itemcard--with-comments")
    card = page.locator("div[data-card='T-1']")
    # 検証
    expect(card.get_by_title("コメント 3 件")).to_be_visible()
    box = _mark_box(card)
    assert box["markTop"] >= box["idBottom"]
    assert box["right"] <= EDGE_TOLERANCE_PX
    assert box["bottom"] <= EDGE_TOLERANCE_PX


def test_selected_with_comments(open_story: OpenStory) -> None:
    """選択中のカードは枠と背景がほかのカードと違い、右下のコメントのマーカーの色は変えない（正常系）。"""
    # 準備
    plain = open_story("shared-itemcard--with-comments")
    plain_style = _card_style(plain.locator("div[data-card='T-1']"))
    # 実行
    page = open_story("shared-itemcard--selected-with-comments")
    selected_style = _card_style(page.locator("div[data-card='T-1']"))
    # 検証
    assert selected_style["border"] != plain_style["border"]
    assert selected_style["background"] != plain_style["background"]
    assert selected_style["mark"] == plain_style["mark"]


def _card_style(card: Locator) -> dict[str, str]:
    """カードの枠・背景と、コメントのマーカーの縁・面の色を返す。"""
    return card.evaluate(
        """(card) => {
            const style = getComputedStyle(card);
            const mark = getComputedStyle(card.querySelector('[title^="コメント"]'));
            return {border: style.borderTopColor, background: style.backgroundColor, mark: `${mark.borderTopColor} ${mark.backgroundColor}`};
        }"""
    )
