"""部品設計『チップの入力.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-chipsinput--default",
    "shared-chipsinput--main-toggle",
    "shared-chipsinput--main-toggle-disabled",
    "shared-chipsinput--main-toggle-long-narrow",
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


def test_default(open_story: OpenStory) -> None:
    """参照の ID を等幅の文字のチップで並べ、主題のトグルを持たない。外すボタンは「{値} を外す」（正常系）。"""
    # 準備・実行
    page = open_story("shared-chipsinput--default")
    group = page.get_by_role("group", name="依存先")
    chip = group.locator("span", has=page.get_by_role("button", name="D-1 を外す")).first
    # 検証
    expect(page.get_by_role("button", name="T-3 を外す")).to_be_visible()
    assert group.get_by_role("button", name="を主題").count() == 0
    assert "mono" in chip.evaluate("e => getComputedStyle(e).fontFamily").lower()
    expect(page.get_by_role("combobox", name="依存先を追加")).to_have_attribute(
        "placeholder", "ID を入れる"
    )


def test_main_toggle(open_story: OpenStory) -> None:
    """項目のタグ。主題のタグのトグルは押した状態（`title` は「主題を外す」）、ほかは押していない状態（「主題にする」）で、押せる範囲は 24px（正常系）。"""
    # 準備・実行
    page = open_story("shared-chipsinput--main-toggle")
    main = page.get_by_role("button", name="画面 を主題")
    other = page.get_by_role("button", name="記録の形 を主題")
    box = main.bounding_box()
    # 検証
    expect(main).to_have_attribute("aria-pressed", "true")
    expect(main).to_have_attribute("title", "主題を外す")
    expect(other).to_have_attribute("aria-pressed", "false")
    expect(other).to_have_attribute("title", "主題にする")
    assert main.locator("svg").inner_html() != other.locator("svg").inner_html()
    assert box is not None
    assert (box["width"], box["height"]) == (24, 24)
    # 検証（入力欄に記録で使われているタグを候補として出す）
    assert page.locator("datalist option").evaluate_all(
        "options => options.map((o) => o.value)"
    ) == ["画面", "記録の形", "通知", "タスク"]


def test_main_toggle_disabled(open_story: OpenStory) -> None:
    """削除を溜めた項目のタグ。入力欄・外すボタン・主題のトグルを押せない（正常系）。"""
    # 準備・実行
    page = open_story("shared-chipsinput--main-toggle-disabled")
    # 検証
    expect(page.get_by_role("combobox", name="タグを追加")).to_be_disabled()
    expect(page.get_by_role("button", name="画面 を外す")).to_be_disabled()
    expect(page.get_by_role("button", name="画面 を主題")).to_be_disabled()


def test_main_toggle_long_narrow(open_story: OpenStory) -> None:
    """幅 320px で長い主題のタグを並べる。収まらないチップは次の行へ回し、トグルは名前と同じ行に残す（正常系）。"""
    # 準備・実行
    page = open_story("shared-chipsinput--main-toggle-long-narrow")
    toggle = page.get_by_role(
        "button", name="すべての画面の絞り込みとドロワーの並び を主題"
    ).bounding_box()
    first = page.locator("[role=group] > span").first.bounding_box()
    second = page.locator("[role=group] > span").nth(1).bounding_box()
    # 検証
    assert toggle is not None
    assert first is not None
    assert second is not None
    assert second["y"] > first["y"]
    assert first["y"] <= toggle["y"] + toggle["height"] / 2 <= first["y"] + first["height"]
