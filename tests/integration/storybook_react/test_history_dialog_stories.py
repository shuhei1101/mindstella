"""部品設計『変更履歴.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-historydialog--unread",
    "shared-historydialog--change-set-selected",
    "shared-historydialog--all-read",
    "shared-historydialog--empty",
    "shared-historydialog--many",
    "shared-historydialog--no-pending",
    "shared-historydialog--long-text",
    "shared-historydialog--external",
    "shared-historydialog--narrow",
)

# 幅 390px の画面の大きさ
NARROW_SIZE = {"width": 390, "height": 844}

# 押す領域の縦横の下限（px）
TARGET_MIN_PX = 24


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_unread(open_story: OpenStory) -> None:
    """差分を出していない。最新・まだまとめていない変更・まとまりを新しい順に並べ、未読のまとまりにマーカーを付けて件数を出す（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-historydialog--unread").get_by_role("dialog", name="変更履歴")
    rows = dialog.locator("button[data-sel]")
    # 検証
    assert rows.evaluate_all("rows => rows.map((r) => r.dataset.sel)") == ["", "pending", "V-3", "V-2", "V-1"]
    expect(dialog.locator("button[data-sel='']")).to_have_attribute("aria-current", "true")
    expect(dialog.locator("button[data-sel='']")).to_contain_text("最新")
    expect(dialog.get_by_text("未読 2 件", exact=True)).to_be_visible()
    expect(dialog.get_by_role("button", name="すべて既読にする")).to_be_enabled()
    expect(dialog.locator("button[data-sel='V-3']").get_by_text("未読", exact=True)).to_have_count(1)
    expect(dialog.locator("button[data-sel='V-2']").get_by_text("未読", exact=True)).to_have_count(1)
    expect(dialog.locator("button[data-sel='V-1']").get_by_text("未読", exact=True)).to_have_count(0)


def test_change_set_selected(open_story: OpenStory) -> None:
    """未読のまとまりを選んだ後。その行にチェックを付けてマーカーを外し、未読を 1 件にする（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-historydialog--change-set-selected").get_by_role("dialog", name="変更履歴")
    row = dialog.locator("button[data-sel='V-3']")
    # 検証
    expect(row).to_have_attribute("aria-current", "true")
    expect(row).to_be_focused()
    expect(row.get_by_text("未読", exact=True)).to_have_count(0)
    expect(dialog.get_by_text("未読 1 件", exact=True)).to_be_visible()


def test_all_read(open_story: OpenStory) -> None:
    """未読が無い。「未読はありません」を出し、「すべて既読にする」を押せない（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-historydialog--all-read").get_by_role("dialog", name="変更履歴")
    # 検証
    expect(dialog.get_by_text("未読はありません", exact=True)).to_be_visible()
    expect(dialog.get_by_role("button", name="すべて既読にする")).to_be_disabled()


def test_empty(open_story: OpenStory) -> None:
    """まとまりがまだ無い。「最新」の行だけを出す（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-historydialog--empty").get_by_role("dialog", name="変更履歴")
    # 検証
    expect(dialog.locator("button[data-sel]")).to_have_count(1)
    expect(dialog.locator("button[data-sel='']")).to_contain_text("最新")


def test_many(open_story: OpenStory) -> None:
    """まとまりが 30 件。一覧を縦にスクロールし、未読の件数と「すべて既読にする」は一覧の上に残す（正常系）。"""
    # 準備
    dialog = open_story("shared-historydialog--many").get_by_role("dialog", name="変更履歴")
    last = dialog.locator("button[data-sel='V-1']")
    # 実行
    last.scroll_into_view_if_needed()
    # 検証
    expect(last).to_be_in_viewport()
    expect(dialog.get_by_text("未読 12 件", exact=True)).to_be_in_viewport()
    expect(dialog.get_by_role("button", name="すべて既読にする")).to_be_in_viewport()


def test_no_pending(open_story: OpenStory) -> None:
    """まだまとめていない変更が無い。その行を出さない（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-historydialog--no-pending").get_by_role("dialog", name="変更履歴")
    # 検証
    assert dialog.locator("button[data-sel=pending]").count() == 0
    expect(dialog.locator("button[data-sel]")).to_have_count(4)


def test_long_text(open_story: OpenStory) -> None:
    """長い説明の未読のまとまり。名前を折り返し、日時と件数の列を押し出さない（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-historydialog--long-text").get_by_role("dialog", name="変更履歴")
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
    """幅 390px。モーダルを画面幅に合わせ、画面を横に送らず、「すべて既読にする」の押す領域を縦横 24px 以上にする（正常系）。"""
    # 準備
    page = open_story("shared-historydialog--narrow")
    # 実行
    page.set_viewport_size(NARROW_SIZE)
    box = page.get_by_role("dialog", name="変更履歴").bounding_box()
    mark_all = page.get_by_role("button", name="すべて既読にする").bounding_box()
    # 検証
    assert box is not None
    assert box["x"] >= 0
    assert box["x"] + box["width"] <= NARROW_SIZE["width"]
    assert mark_all is not None
    assert (mark_all["width"] >= TARGET_MIN_PX, mark_all["height"] >= TARGET_MIN_PX) == (True, True)
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )


def test_external(open_story: OpenStory) -> None:
    """外部の変更のまとまりの名前の横に「外部の変更」の札を付け、行の読み上げ名に含める（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-historydialog--external").get_by_role("dialog", name="変更履歴")
    row = dialog.locator("button[data-sel='V-3']")
    # 検証
    expect(row).to_contain_text("ほかのセッションの書き込み")
    expect(row).to_contain_text("外部の変更")
    assert "ほかのセッションの書き込み 外部の変更" in " ".join(row.inner_text().split())
    assert dialog.get_by_text("外部の変更", exact=True).count() == 1
