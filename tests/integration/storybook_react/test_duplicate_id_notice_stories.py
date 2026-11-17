"""部品設計『重なった ID の通知.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-duplicateidnotice--single",
    "shared-duplicateidnotice--multiple",
    "shared-duplicateidnotice--narrow",
)

# 幅 390px の画面の大きさ
NARROW_SIZE = {"width": 390, "height": 844}


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_single(open_story: OpenStory) -> None:
    """重なった ID が 1 件。見出しと、種類・ID のリンク・片方の ID を変更する案内を出す（正常系）。"""
    # 準備・実行
    notice = open_story("shared-duplicateidnotice--single").get_by_role("alert")
    # 検証
    assert " ".join(notice.inner_text().split()) == (
        "同じ ID の項目が 2 件あります ほかのセッションの書き込みで、検討事項 D-12 が重なりました。片方の ID を変更してください。"
    )
    expect(notice.get_by_role("link", name="D-12")).to_have_attribute("href", "#id=D-12")
    expect(notice.get_by_role("button", name="通知を閉じる")).to_be_visible()


def test_multiple(open_story: OpenStory) -> None:
    """重なった ID が 3 件。ID のリンクを「、」で並べ、ID の途中で折り返さない（正常系）。"""
    # 準備・実行
    page = open_story("shared-duplicateidnotice--multiple")
    notice = page.get_by_role("alert")
    # 検証
    assert notice.get_by_role("link").all_inner_texts() == ["D-12", "T-3", "N-8"]
    expect(notice).to_contain_text("検討事項 D-12、タスク T-3、メモ N-8")
    assert notice.get_by_role("link").evaluate_all("links => links.map((a) => a.getClientRects().length)") == [1, 1, 1]


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。本文を折り返し、閉じるボタンを右上に残し、横にはみ出さない（正常系）。"""
    # 準備・実行
    page = open_story("shared-duplicateidnotice--narrow")
    page.set_viewport_size(NARROW_SIZE)
    notice = page.get_by_role("alert")
    # 検証
    notice_box = notice.bounding_box()
    close_box = notice.get_by_role("button", name="通知を閉じる").bounding_box()
    link_box = notice.get_by_role("link", name="D-12").bounding_box()
    assert notice_box is not None
    assert close_box is not None
    assert link_box is not None
    assert notice_box["x"] + notice_box["width"] <= NARROW_SIZE["width"]
    assert close_box["x"] > link_box["x"]
    assert close_box["y"] <= notice_box["y"] + notice_box["height"] / 2
