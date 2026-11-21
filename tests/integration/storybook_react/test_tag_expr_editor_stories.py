"""部品設計『タグの条件の詳細』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-tagexpreditor--empty",
    "shared-tagexpreditor--include-exclude",
    "shared-tagexpreditor--nested",
    "shared-tagexpreditor--many-tags",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_empty(open_story: OpenStory) -> None:
    """条件が 1 つでタグを選択していないときは、入力欄だけを出し、条件削除を出さない（正常系）。"""
    # 準備・実行
    page = open_story("shared-tagexpreditor--empty")
    # 検証
    expect(page.get_by_role("combobox", name="タグを追加")).to_be_visible()
    assert page.get_by_role("button", name="条件削除").count() == 0


def test_include_exclude(open_story: OpenStory) -> None:
    """条件ごとに比較方法と、選択したタグのチップを出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-tagexpreditor--include-exclude")
    # 検証
    expect(page.get_by_role("combobox", name="タグの比較方法")).to_have_count(2)
    expect(page.get_by_role("combobox", name="タグの比較方法").nth(1)).to_have_value("ne")
    expect(page.get_by_role("button", name="廃止 を解除")).to_be_visible()


def test_nested(open_story: OpenStory) -> None:
    """3 レイヤー目のグループでは「グループ追加」を出さない（正常系）。"""
    # 準備・実行
    page = open_story("shared-tagexpreditor--nested")
    expect(page.get_by_role("button", name="グループ追加")).to_have_count(2)
    # 実行（2 レイヤー目のグループの「グループ追加」は、子より後ろの最上位のボタンより前に並ぶ）
    page.get_by_role("button", name="グループ追加").first.click()
    # 検証（追加した 3 レイヤー目のグループは「グループ追加」を持たない）
    expect(page.get_by_role("button", name="条件追加")).to_have_count(3)
    expect(page.get_by_role("button", name="グループ追加")).to_have_count(2)


def test_many_tags(open_story: OpenStory) -> None:
    """タグが 50 件あっても、選択したタグだけをチップで出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-tagexpreditor--many-tags")
    # 検証
    expect(page.get_by_role("button", name="を解除")).to_have_count(3)


def test_unknown_tag(open_story: OpenStory) -> None:
    """候補に無いタグを入れると追加せず、入力欄の直下に誤りを出す（異常系）。"""
    # 準備
    page = open_story("shared-tagexpreditor--empty")
    field = page.get_by_role("combobox", name="タグを追加")
    # 実行
    field.fill("未登録")
    field.press("Enter")
    # 検証
    expect(page.get_by_text("該当するタグはありません")).to_be_visible()
    assert page.get_by_role("button", name="未登録 を解除").count() == 0
