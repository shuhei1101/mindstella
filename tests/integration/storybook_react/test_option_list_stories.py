"""部品設計『案の一覧.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Locator, Page, expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "features-detail-optionlist--not-chosen",
    "features-detail-optionlist--chosen",
    "features-detail-optionlist--chosen-with-note",
    "features-detail-optionlist--editing",
    "features-detail-optionlist--sent",
    "features-detail-optionlist--long-text",
    "features-detail-optionlist--many",
    "features-detail-optionlist--decided",
    "features-detail-optionlist--narrow",
)

# 案のカード（記号の読み上げ「案 {記号}」の札を持つ枠）
CARD = "div.rounded-control:has(> div [data-key='options[{key}].content'])"

# 幅 390px の画面の大きさと、押す領域の縦横の下限（px）
NARROW_SIZE = {"width": 390, "height": 844}
TARGET_MIN_PX = 24


def _card(page: Page, key: str) -> Locator:
    """案の記号のカードを返却する。"""
    return page.locator(CARD.format(key=key))


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_not_chosen(open_story: OpenStory) -> None:
    """まだ選んでいない。どの案にも「この案を選ぶ」を出し、推奨の案に推奨の札と推奨理由を出す（正常系）。"""
    # 準備・実行
    page = open_story("features-detail-optionlist--not-chosen")
    # 検証
    expect(page.get_by_role("button", name="案 A を選ぶ")).to_be_visible()
    expect(page.get_by_role("button", name="案 B を選ぶ")).to_be_visible()
    expect(_card(page, "B").get_by_text("推奨", exact=True)).to_be_visible()
    expect(_card(page, "B").get_by_text("推奨理由", exact=True)).to_be_visible()
    expect(page.get_by_text("選択済み")).to_have_count(0)


def test_chosen(open_story: OpenStory) -> None:
    """一言なしで選んだ（送信前）。カードと札の線を破線にし、「一言なし」と編集・取り消しを出す（正常系）。"""
    # 準備・実行
    page = open_story("features-detail-optionlist--chosen")
    card = _card(page, "B")
    # 検証
    expect(card).to_have_css("border-top-style", "dashed")
    expect(card.get_by_text("選択済み")).to_be_visible()
    expect(card.get_by_text("一言なし", exact=True)).to_be_visible()
    expect(card.get_by_role("button", name="一言を編集")).to_be_visible()
    expect(card.get_by_role("button", name="選択を取り消す")).to_be_visible()
    expect(page.get_by_role("button", name="案 A を選ぶ")).to_be_visible()


def test_chosen_with_note(open_story: OpenStory) -> None:
    """一言つきで選んだ（送信前）。カードの下に一言を出す（正常系）。"""
    # 準備・実行
    page = open_story("features-detail-optionlist--chosen-with-note")
    # 検証
    expect(_card(page, "B").get_by_text("一言: 費用を優先する", exact=True)).to_be_visible()


def test_editing(open_story: OpenStory) -> None:
    """「この案を選ぶ」を押した後。一言（任意）の入力と「キャンセル」「この案を選ぶ」を出す（正常系）。"""
    # 準備・実行
    page = open_story("features-detail-optionlist--editing")
    card = _card(page, "B")
    # 検証
    expect(card.get_by_role("textbox", name="一言（任意）")).to_be_focused()
    expect(card.get_by_role("button", name="キャンセル")).to_be_visible()
    expect(card.get_by_role("button", name="この案を選ぶ")).to_be_visible()


def test_sent(open_story: OpenStory) -> None:
    """送信済み。カードと札の線を実線にし、編集・取り消しを出さず、AI の採用の札と見分けられる（正常系）。"""
    # 準備・実行
    page = open_story("features-detail-optionlist--sent")
    card = _card(page, "B")
    # 検証
    expect(card).to_have_css("border-top-style", "solid")
    expect(card.get_by_text("選択済み")).to_be_visible()
    expect(card.get_by_role("button", name="一言を編集")).to_have_count(0)
    expect(card.get_by_role("button", name="選択を取り消す")).to_have_count(0)
    expect(card.get_by_text("採用", exact=True)).to_have_count(0)


def test_long_text(open_story: OpenStory) -> None:
    """長い一言。カードの幅で折り返し、ボタンを押し出さない（正常系）。"""
    # 準備・実行
    page = open_story("features-detail-optionlist--long-text")
    card = _card(page, "A")
    # 検証
    assert card.evaluate("e => e.scrollWidth <= e.clientWidth")
    expect(card.get_by_role("button", name="選択を取り消す")).to_be_in_viewport()


def test_many(open_story: OpenStory) -> None:
    """案が 5 つで案 C を選んだ。カードを縦に並べ、選んだカードだけに札を出す（正常系）。"""
    # 準備・実行
    page = open_story("features-detail-optionlist--many")
    # 検証
    expect(page.get_by_text("選択済み")).to_have_count(1)
    expect(_card(page, "C").get_by_text("選択済み")).to_be_visible()
    top_a = _card(page, "A").bounding_box()
    top_e = _card(page, "E").bounding_box()
    assert top_a is not None
    assert top_e is not None
    assert top_a["y"] < top_e["y"]


def test_decided(open_story: OpenStory) -> None:
    """決定済み。採用・不採用の札を出し、選ぶ操作を出さない（正常系）。"""
    # 準備・実行
    page = open_story("features-detail-optionlist--decided")
    # 検証
    expect(_card(page, "B").get_by_text("採用", exact=True)).to_be_visible()
    expect(_card(page, "A").get_by_text("不採用", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="案 A を選ぶ")).to_have_count(0)


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。画面を横にスクロールさせず、選ぶ・編集・取り消しの押す領域を縦横 24px 以上にする（正常系）。"""
    # 準備
    page = open_story("features-detail-optionlist--narrow")
    # 実行
    page.set_viewport_size(NARROW_SIZE)
    choose = page.get_by_role("button", name="案 A を選ぶ").bounding_box()
    edit = page.get_by_role("button", name="一言を編集").bounding_box()
    cancel = page.get_by_role("button", name="選択を取り消す").bounding_box()
    # 検証
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    assert choose is not None
    assert edit is not None
    assert cancel is not None
    assert min(choose["width"], choose["height"], edit["width"], edit["height"], cancel["width"], cancel["height"]) >= TARGET_MIN_PX
