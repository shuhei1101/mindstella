"""部品設計『表示形式の切り替え.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-viewswitch--decisions",
    "shared-viewswitch--tasks",
    "shared-viewswitch--docs",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


# ボタンの幅と、組の左端からの位置を返す
_BOXES_JS = """(group) => [...group.querySelectorAll('button')].map((b) => ({
    width: b.getBoundingClientRect().width,
    left: b.getBoundingClientRect().left - group.getBoundingClientRect().left,
}))"""


def test_decisions(open_story: OpenStory) -> None:
    """検討事項（マップ・ボード・表）でマップを選んでいる。組を「表示形式」と読み上げ、選んでいる形式を `aria-pressed` で伝える（正常系）。"""
    # 準備・実行
    page = open_story("shared-viewswitch--decisions")
    group = page.get_by_role("group", name="表示形式")
    # 検証
    expect(group.get_by_role("button")).to_have_text(["マップ", "ボード", "表"])
    expect(group.get_by_role("button", name="マップ")).to_have_attribute("aria-pressed", "true")
    assert group.locator("button[aria-pressed=true]").count() == 1


def test_tasks(open_story: OpenStory) -> None:
    """タスク（ボード・表）で表を選んでいる。形式の数が違っても 1 つの幅と左端の位置が検討事項と同じ（正常系）。"""
    # 準備
    decisions = (
        open_story("shared-viewswitch--decisions")
        .get_by_role("group", name="表示形式")
        .evaluate(_BOXES_JS)
    )
    # 実行
    page = open_story("shared-viewswitch--tasks")
    group = page.get_by_role("group", name="表示形式")
    boxes = group.evaluate(_BOXES_JS)
    # 検証
    expect(group.get_by_role("button")).to_have_text(["ボード", "表"])
    expect(group.get_by_role("button", name="表")).to_have_attribute("aria-pressed", "true")
    assert boxes[0] == decisions[0]
    assert boxes[1]["width"] == decisions[1]["width"]


def test_docs(open_story: OpenStory) -> None:
    """資料（カード・ボード・表）でカードを選んでいる（正常系）。"""
    # 準備・実行
    page = open_story("shared-viewswitch--docs")
    group = page.get_by_role("group", name="表示形式")
    # 検証
    expect(group.get_by_role("button")).to_have_text(["カード", "ボード", "表"])
    expect(group.get_by_role("button", name="カード")).to_have_attribute("aria-pressed", "true")
