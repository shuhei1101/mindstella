"""部品設計『変更履歴.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-historydialog--since-selected",
    "shared-historydialog--off",
    "shared-historydialog--no-pending",
    "shared-historydialog--long-name",
    "shared-historydialog--narrow",
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


def test_since_selected(open_story: OpenStory) -> None:
    """「前回開いてから」を選んでいる。見出し「変更履歴」を読み上げ名にした dialog に時点を並べ、選んでいる行に `aria-current` とフォーカスを置く（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-historydialog--since-selected").get_by_role(
        "dialog", name="変更履歴"
    )
    rows = dialog.locator("button[data-sel]")
    # 検証
    assert rows.evaluate_all("rows => rows.map((r) => r.dataset.sel)") == [
        "",
        "pending",
        "since",
        "V-2",
        "V-1",
    ]
    expect(dialog.locator("button[data-sel=since]")).to_have_attribute("aria-current", "true")
    assert dialog.locator("[aria-current=true]").count() == 1
    expect(dialog.locator("button[data-sel=since]")).to_be_focused()
    expect(dialog.locator("button[data-sel=since]")).to_contain_text("5 件")


def test_off(open_story: OpenStory) -> None:
    """差分を出していない。「差分を出さない（今の内容）」の行にチェックと `aria-current` を付ける（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-historydialog--off").get_by_role("dialog", name="変更履歴")
    row = dialog.locator("button[data-sel='']")
    # 検証
    expect(row).to_have_attribute("aria-current", "true")
    expect(row).to_contain_text("差分を出さない（今の内容）")
    assert row.locator("svg").count() == 1
    assert dialog.locator("button[data-sel=since] svg").count() == 0


def test_no_pending(open_story: OpenStory) -> None:
    """まだまとめていない変更が無い。その行を出さない（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-historydialog--no-pending").get_by_role("dialog", name="変更履歴")
    # 検証
    assert dialog.locator("button[data-sel=pending]").count() == 0
    expect(dialog.locator("button[data-sel]")).to_have_count(4)


def test_long_name(open_story: OpenStory) -> None:
    """長い説明のまとまり。名前を折り返し、日時と件数の列を押し出さない（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-historydialog--long-name").get_by_role("dialog", name="変更履歴")
    row = dialog.locator("button[data-sel=V-2]")
    name = row.locator("span span").first
    count = row.get_by_text("3 件")
    # 検証
    assert (
        name.evaluate("e => e.getBoundingClientRect().height")
        > row.locator("span span").nth(1).evaluate("e => e.getBoundingClientRect().height") * 1.5
    )
    count_box = count.bounding_box()
    row_box = row.bounding_box()
    assert count_box is not None
    assert row_box is not None
    assert count_box["x"] + count_box["width"] <= row_box["x"] + row_box["width"] + 1
    assert count.evaluate("e => e.scrollWidth <= e.clientWidth")


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。モーダルを画面幅に合わせ、画面を横に送らない（正常系）。"""
    # 準備
    page = open_story("shared-historydialog--narrow")
    # 実行
    page.set_viewport_size(NARROW_SIZE)
    box = page.get_by_role("dialog", name="変更履歴").bounding_box()
    # 検証
    assert box is not None
    assert box["x"] >= 0
    assert box["x"] + box["width"] <= NARROW_SIZE["width"]
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )
