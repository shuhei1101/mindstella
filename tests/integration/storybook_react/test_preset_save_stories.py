"""部品設計『プリセットの保存.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-presetsave--default",
    "shared-presetsave--no-tag-condition",
    "shared-presetsave--open",
    "shared-presetsave--with-other-conditions",
    "shared-presetsave--name-taken",
    "shared-presetsave--long-name",
)

# タグの条件が無いときに出す理由
NO_TAG_REASON = "タグの条件を選ぶと、プリセットとして保存できます。"

# タグの条件のほかの条件があるときに出す文
OTHER_CONDITIONS_NOTE = "タグの条件だけを保存します。状態・種類・文字の条件は保存しません。"

# 名前が重なったときのエラー
NAME_TAKEN_ERROR = "同じ名前のプリセット「画面の設計」が既にあります。別の名前を入れてください。"

# 最大の長さ（40 文字）の名前
LONG_NAME = "画面の設計の見直しで使用する廃止予定の画面と部品をまとめて開くためのプリセット集"

# 要素の右端が親の右端を超えていないか
_FITS_JS = "e => e.getBoundingClientRect().right <= e.parentElement.getBoundingClientRect().right + 0.5"


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_default(open_story: OpenStory) -> None:
    """タグの条件があり、「プリセットとして保存」を押せる（正常系）。"""
    # 準備・実行
    page = open_story("shared-presetsave--default")
    button = page.get_by_role("button", name="プリセットとして保存")
    # 検証
    expect(button).to_be_visible()
    expect(button).not_to_have_attribute("aria-disabled", "true")
    expect(page.get_by_text(NO_TAG_REASON)).to_have_count(0)


def test_no_tag_condition(open_story: OpenStory) -> None:
    """タグの条件が無く、「プリセットとして保存」をフォーカスできるまま押せない見た目にし、理由を結ぶ（正常系）。"""
    # 準備・実行
    page = open_story("shared-presetsave--no-tag-condition")
    button = page.get_by_role("button", name="プリセットとして保存")
    button.focus()
    # 検証
    expect(button).to_have_attribute("aria-disabled", "true")
    assert button.get_attribute("disabled") is None
    expect(button).to_be_focused()
    expect(button).to_have_accessible_description(NO_TAG_REASON)


def test_open(open_story: OpenStory) -> None:
    """名前の入力を開き、「キャンセル」と「保存」を右に並べる（正常系）。"""
    # 準備・実行
    page = open_story("shared-presetsave--open")
    name = page.get_by_label("プリセットの名前")
    cancel = page.get_by_role("button", name="キャンセル")
    save = page.get_by_role("button", name="保存", exact=True)
    # 検証
    expect(name).to_have_value("廃止する画面")
    expect(name).not_to_have_attribute("aria-invalid", "true")
    assert cancel.bounding_box()["x"] < save.bounding_box()["x"]
    expect(page.get_by_text(OTHER_CONDITIONS_NOTE)).to_have_count(0)


def test_with_other_conditions(open_story: OpenStory) -> None:
    """タグの条件のほかに条件があり、タグの条件だけを保存する旨を出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-presetsave--with-other-conditions")
    # 検証
    expect(page.get_by_text(OTHER_CONDITIONS_NOTE)).to_be_visible()


def test_name_taken(open_story: OpenStory) -> None:
    """名前が重なった理由を入力欄の下に出して結び、名前を残す（正常系）。"""
    # 準備・実行
    page = open_story("shared-presetsave--name-taken")
    name = page.get_by_label("プリセットの名前")
    # 検証
    expect(name).to_have_value("画面の設計")
    expect(name).to_have_attribute("aria-invalid", "true")
    expect(name).to_have_accessible_description(NAME_TAKEN_ERROR)


def test_long_name(open_story: OpenStory) -> None:
    """最大の長さの名前でも入力欄が幅を超えず、横にはみ出さない（正常系）。"""
    # 準備・実行
    page = open_story("shared-presetsave--long-name")
    name = page.get_by_label("プリセットの名前")
    # 検証
    expect(name).to_have_value(LONG_NAME)
    assert name.evaluate(_FITS_JS) is True
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth") is True
