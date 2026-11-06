"""部品設計『絞り込み.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-filterdrawer--default",
    "shared-filterdrawer--selected",
    "shared-filterdrawer--zero-value",
    "shared-filterdrawer--long-tag",
    "shared-filterdrawer--keyword-hits",
    "shared-filterdrawer--no-match",
    "shared-filterdrawer--narrow",
    "shared-filterdrawer--text-conditions",
)

# ドロワーの幅（px）。コメントの一覧と同じ
DRAWER_WIDTH_PX = 420

# 幅 900px 以下で開くときの画面の大きさ
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
    """何も選んでいない。見出しの右は「8 件」で、「解除」と「すべて解除」を出さず、条件は fieldset と legend で組む（正常系）。"""
    # 準備・実行
    page = open_story("shared-filterdrawer--default")
    dialog = page.get_by_role("dialog", name="絞り込み")
    # 検証
    expect(dialog).to_contain_text("8 件")
    expect(dialog.locator("legend")).to_have_text(["種類", "状態", "タグ"])
    assert dialog.get_by_role("button", name="すべて解除").count() == 0
    assert dialog.get_by_role("button", name="解除").count() == 0
    expect(dialog.get_by_role("button", name="8 件を表示")).to_be_visible()
    assert dialog.evaluate("e => e.getBoundingClientRect().width") == DRAWER_WIDTH_PX
    # 検証（開いたら最初の値へフォーカスを移す）
    expect(dialog.get_by_role("checkbox", name="作業")).to_be_focused()


def test_selected(open_story: OpenStory) -> None:
    """状態に 4 つ・タグに 1 つを選んでいる。「36 件中 3 件」、選んだ条件に「{件数} 件を選択」と「解除」、下端に「すべて解除」と「3 件を表示」（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--selected").get_by_role("dialog", name="絞り込み")
    # 検証
    expect(dialog).to_contain_text("36 件中 3 件")
    expect(dialog.locator("fieldset").nth(0).locator("legend")).to_contain_text("4 件を選択")
    expect(dialog.locator("fieldset").nth(1).locator("legend")).to_contain_text("1 件を選択")
    expect(dialog.get_by_role("button", name="状態の条件を解除")).to_be_visible()
    expect(dialog.get_by_role("button", name="タグの条件を解除")).to_be_visible()
    expect(dialog.get_by_role("button", name="すべて解除")).to_be_visible()
    expect(dialog.get_by_role("button", name="3 件を表示")).to_be_visible()
    expect(dialog.get_by_role("checkbox", name="要見直し")).to_be_checked()


def test_zero_value(open_story: OpenStory) -> None:
    """今の条件で 0 件になる値は文字と件数を薄くし、件数の 0 でも伝え、選べるまま残す（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--zero-value").get_by_role("dialog", name="絞り込み")
    zero = dialog.locator("li", has_text="未整理")
    some = dialog.locator("li", has_text="未決定")
    # 検証
    expect(zero.get_by_label("0 件")).to_have_text("0")
    expect(dialog.get_by_role("checkbox", name="未整理")).to_be_enabled()
    assert zero.locator("label").evaluate("e => getComputedStyle(e).color") != some.locator("label").evaluate("e => getComputedStyle(e).color")


def test_long_tag(open_story: OpenStory) -> None:
    """長いタグは値の文字を折り返し、件数の列を押し出さない（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--long-tag").get_by_role("dialog", name="絞り込み")
    long_label = dialog.locator("li label").first
    count = long_label.get_by_label("12 件").bounding_box()
    box = long_label.bounding_box()
    short = dialog.locator("li label").nth(1).bounding_box()
    # 検証
    assert count is not None
    assert box is not None
    assert short is not None
    assert box["height"] > short["height"]
    assert count["x"] + count["width"] <= box["x"] + box["width"] + 1


def test_keyword_hits(open_story: OpenStory) -> None:
    """キーワードに一致した件数を、件数の左に印の色で出す。0 件の一致は出さない（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--keyword-hits").get_by_role("dialog", name="絞り込み")
    hit = dialog.get_by_label("キーワードに一致した項目 2 件")
    count = dialog.get_by_label("5 件")
    # 検証
    expect(hit).to_have_text("2")
    expect(dialog.get_by_label("キーワードに一致した項目 1 件")).to_have_count(1)
    assert dialog.get_by_label("キーワードに一致した項目 0 件").count() == 0
    hit_box = hit.bounding_box()
    count_box = count.bounding_box()
    assert hit_box is not None
    assert count_box is not None
    assert hit_box["x"] < count_box["x"]
    assert hit.evaluate("e => getComputedStyle(e).color") != count.evaluate(
        "e => getComputedStyle(e).color"
    )


def test_no_match(open_story: OpenStory) -> None:
    """該当なし。見出しの右は「8 件中 0 件」、下端のボタンは「0 件を表示」（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--no-match").get_by_role("dialog", name="絞り込み")
    # 検証
    expect(dialog).to_contain_text("8 件中 0 件")
    expect(dialog.get_by_role("button", name="0 件を表示")).to_be_visible()


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。画面の幅いっぱいに重ねる（正常系）。"""
    # 準備
    page = open_story("shared-filterdrawer--narrow")
    # 実行
    page.set_viewport_size(NARROW_SIZE)
    dialog = page.get_by_role("dialog", name="絞り込み")
    # 検証
    assert dialog.evaluate("e => e.getBoundingClientRect().width") == NARROW_SIZE["width"]
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )


def test_text_conditions(open_story: OpenStory) -> None:
    """用語の欄に「移し」を入れている。値の条件より上に「文字を含む」と列ごとの欄を並べ、見出しの右は「6 件中 1 件」（正常系）。"""
    # 準備・実行
    dialog = open_story("shared-filterdrawer--text-conditions").get_by_role(
        "dialog", name="絞り込み"
    )
    # 検証
    expect(dialog.locator("legend").first).to_have_text("文字を含む")
    expect(dialog.get_by_label("用語")).to_have_value("移し")
    expect(dialog.get_by_label("ID")).to_have_value("")
    assert dialog.locator("[data-text-key]").evaluate_all(
        "inputs => inputs.map((i) => i.dataset.textKey)"
    ) == ["id", "title", "meaning", "aliases", "avoid"]
    expect(dialog).to_contain_text("6 件中 1 件")
    # 検証（初めて開くときは先頭の文字の欄へフォーカスを移す）
    expect(dialog.get_by_label("ID")).to_be_focused()
