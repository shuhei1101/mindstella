"""部品設計『カードの並べ替え.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-cardsort--default",
    "shared-cardsort--docs-initial",
    "shared-cardsort--updated-desc",
    "shared-cardsort--created-asc",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


@pytest.mark.parametrize(
    ("state", "pressed", "title"),
    [
        ("shared-cardsort--default", "連番", "連番"),
        ("shared-cardsort--docs-initial", "更新日時", "更新日時（新しい順）"),
        ("shared-cardsort--updated-desc", "更新日時", "更新日時（新しい順）"),
        ("shared-cardsort--created-asc", "作成日時", "作成日時（古い順）"),
    ],
)
def test_pressed(open_story: OpenStory, state: str, pressed: str, title: str) -> None:
    """選んでいるボタンだけが `aria-pressed="true"` で、日時は向きを `title` と矢印で出す（正常系）。"""
    # 準備・実行
    page = open_story(state)
    group = page.get_by_role("group", name="並べ替え")
    button = group.get_by_role("button", name=pressed)
    # 検証
    expect(group.locator("[aria-pressed='true']")).to_have_count(1)
    expect(button).to_have_attribute("aria-pressed", "true")
    expect(button).to_have_attribute("title", title)
    expect(button.locator("svg")).to_have_count(0 if pressed == "連番" else 1)
