"""部品設計『表.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態
STATES = (
    "shared-table--default",
    "shared-table--sorted-asc",
    "shared-table--sorted-desc",
    "shared-table--filtered",
    "shared-table--pinned",
    "shared-table--long-title",
    "shared-table--no-match",
    "shared-table--columns-popover",
    "shared-table--marked",
    "shared-table--text-filtered",
    "shared-table--commented",
    "shared-table--withdrawn",
)

# 位置の比べで許す差（px）
TOLERANCE_PX = 2

# 行の ID を上から返す
_ROW_IDS_JS = (
    """() => [...document.querySelectorAll('tbody tr[data-id]')].map((row) => row.dataset.id)"""
)


def _title_marks(page: Page, row_id: str) -> list[str]:
    """行のタイトルの右に並ぶ印の読み上げ（札の文字・`title`）を左から返す。"""
    return page.locator(
        f"tr[data-id='{row_id}'] td button[data-id='{row_id}'] ~ span"
    ).evaluate_all("marks => marks.map((m) => m.getAttribute('title') ?? m.textContent.trim())")


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_default(open_story: OpenStory) -> None:
    """並べ替えの印は見出しにホバーかフォーカスしたときだけ出し、チップの行の右端に「列の表示」を置いて表との間を 12px 空ける（正常系）。"""
    # 準備
    page = open_story("shared-table--default")
    header = page.get_by_role("columnheader", name="タイトル")
    arrow = header.locator("button[data-sort] svg")
    # 実行
    hidden = arrow.evaluate("e => getComputedStyle(e).opacity")
    header.hover()
    shown = arrow.evaluate("e => getComputedStyle(e).opacity")
    columns = page.get_by_role("button", name="列の表示").bounding_box()
    table = page.locator("#storybook-root table").bounding_box()
    # 検証（並べ替えはどの列にも掛けていない）
    assert page.locator("th[aria-sort=none]").count() == 4
    assert (hidden, shown) == ("0", "1")
    # 検証（列の表示のボタンと表の間）
    assert columns is not None
    assert table is not None
    assert abs(table["y"] - (columns["y"] + columns["height"]) - 12) <= TOLERANCE_PX + 1
    # 検証（行のタイトルはボタンで、記録の順に並ぶ）
    assert page.evaluate(_ROW_IDS_JS) == ["D-1", "D-2", "D-3", "D-4"]
    expect(page.get_by_role("button", name="プレビューの画面の分け方")).to_be_visible()


def test_sorted_asc(open_story: OpenStory) -> None:
    """タイトルで昇順。向きの矢印を出して `aria-sort="ascending"`、行をタイトルの昇順に並べる（正常系）。"""
    # 準備・実行
    page = open_story("shared-table--sorted-asc")
    header = page.get_by_role("columnheader", name="タイトル")
    # 検証
    expect(header).to_have_attribute("aria-sort", "ascending")
    assert (
        header.locator("button[data-sort] svg").evaluate("e => getComputedStyle(e).opacity") == "1"
    )
    assert page.evaluate(_ROW_IDS_JS) == ["D-4", "D-2", "D-1", "D-3"]


def test_sorted_desc(open_story: OpenStory) -> None:
    """タイトルで降順。`aria-sort="descending"` で、行をタイトルの降順に並べる（正常系）。"""
    # 準備・実行
    page = open_story("shared-table--sorted-desc")
    # 検証
    expect(page.get_by_role("columnheader", name="タイトル")).to_have_attribute(
        "aria-sort", "descending"
    )
    assert page.evaluate(_ROW_IDS_JS) == ["D-3", "D-1", "D-2", "D-4"]


def test_filtered(open_story: OpenStory) -> None:
    """確度 = 高で絞り込み中。チップと「すべて解除」を並べ、列の見出しには並べ替えとピン留めだけを置く（正常系）。"""
    # 準備・実行
    page = open_story("shared-table--filtered")
    # 検証
    expect(page.get_by_text("確度: 高")).to_be_visible()
    expect(page.get_by_role("button", name="確度: 高 の条件を解除")).to_be_visible()
    expect(page.get_by_role("button", name="すべて解除")).to_be_visible()
    assert page.evaluate(_ROW_IDS_JS) == ["D-1", "D-3"]
    assert page.get_by_role("columnheader", name="確度").locator("button").evaluate_all(
        "buttons => buttons.map((b) => b.dataset.sort ? 'sort' : 'pin')"
    ) == ["sort", "pin"]


def test_pinned(open_story: OpenStory) -> None:
    """ID の列までピン留め。押した列のボタンだけが押された見た目で、固定した列の境に影（正常系）。"""
    # 準備・実行
    page = open_story("shared-table--pinned")
    cell = page.locator("tr[data-id='D-1'] td").first
    # 検証
    expect(page.get_by_role("button", name="IDまで固定")).to_have_attribute("aria-pressed", "true")
    assert page.locator("button[data-pin][aria-pressed=true]").count() == 1
    assert cell.evaluate("e => getComputedStyle(e).position") == "sticky"
    assert cell.evaluate("e => getComputedStyle(e).boxShadow") != "none"
    assert (
        page.locator("tr[data-id='D-1'] td").nth(1).evaluate("e => getComputedStyle(e).position")
        != "sticky"
    )


def test_long_title(open_story: OpenStory) -> None:
    """長いタイトル。タイトルの列は折り返し、ほかの列は 1 行のまま崩れない（正常系）。"""
    # 準備・実行
    page = open_story("shared-table--long-title")
    page.set_viewport_size({"width": 720, "height": 800})
    cells = page.locator("tr[data-id='D-5'] td")
    title = cells.nth(1).locator("button").bounding_box()
    line_height = (
        cells.nth(1).locator("button").evaluate("e => parseFloat(getComputedStyle(e).lineHeight)")
    )
    # 検証（タイトルは 2 行以上に折り返し、ほかの列は 1 行のまま）
    assert title is not None
    assert title["height"] > line_height * 1.5
    assert cells.nth(2).evaluate("e => getComputedStyle(e).whiteSpace") == "nowrap"
    assert cells.nth(0).evaluate("e => getComputedStyle(e).whiteSpace") == "nowrap"


def test_no_match(open_story: OpenStory) -> None:
    """該当なし（ピン留め中）。表の場所に該当なしと次の操作を書き、横に送っても文言は表の枠の左に留める（正常系）。"""
    # 準備
    page = open_story("shared-table--no-match")
    message = page.locator("[data-no-match]")
    page.set_viewport_size({"width": 320, "height": 600})
    before = message.bounding_box()
    # 実行
    page.locator("#storybook-root table").evaluate(
        "t => { t.parentElement.scrollLeft = t.parentElement.scrollWidth; }"
    )
    after = message.bounding_box()
    # 検証
    expect(message).to_have_text("該当する検討事項はありません。別の条件を試してください。")
    assert page.locator("tbody tr[data-id]").count() == 0
    assert before is not None
    assert after is not None
    assert abs(after["x"] - before["x"]) <= TOLERANCE_PX


def test_columns_popover(open_story: OpenStory) -> None:
    """列の表示のポップオーバーを開いている。題は「列の表示」で、タイトルの列は外せない（正常系）。"""
    # 準備・実行
    page = open_story("shared-table--columns-popover")
    popover = page.get_by_role("dialog")
    # 検証
    expect(popover).to_contain_text("列の表示")
    expect(popover.get_by_role("checkbox", name="タイトル")).to_be_disabled()
    expect(popover.get_by_role("checkbox", name="ID")).to_be_enabled()
    expect(popover.get_by_role("checkbox", name="ID")).to_be_checked()


def test_marked(open_story: OpenStory) -> None:
    """差分の表示の間。変えた行のタイトルの右に変更、足した行に新規の印を置き、印の無い行は変わらない（正常系）。"""
    # 準備・実行
    page = open_story("shared-table--marked")
    # 検証
    assert _title_marks(page, "D-5") == ["変更"]
    assert _title_marks(page, "D-37") == ["新規"]
    assert _title_marks(page, "D-1") == []


def test_text_filtered(open_story: OpenStory) -> None:
    """用語に「移し」を含む行に絞る。「用語に「移し」を含む」と「ID に「G-」を含む」のチップと「すべて解除」を並べる（正常系）。"""
    # 準備・実行
    page = open_story("shared-table--text-filtered")
    # 検証
    expect(page.get_by_text("用語に「移し」を含む")).to_be_visible()
    expect(page.get_by_text("ID に「G-」を含む")).to_be_visible()
    expect(page.get_by_role("button", name="用語に「移し」を含む の条件を解除")).to_be_visible()
    expect(page.get_by_role("button", name="すべて解除")).to_be_visible()
    assert page.evaluate(_ROW_IDS_JS) == ["G-1"]


def test_commented(open_story: OpenStory) -> None:
    """コメントを書いた行。タイトルの右に差分の印、その後ろにコメントの印を置き、印の無い行は変わらない（正常系）。"""
    # 準備・実行
    page = open_story("shared-table--commented")
    # 検証
    assert _title_marks(page, "D-5") == ["変更", "コメント 1 件"]
    assert _title_marks(page, "D-37") == ["コメント 12 件"]
    assert _title_marks(page, "D-1") == []


def test_withdrawn(open_story: OpenStory) -> None:
    """取り下げた行。タイトルの右に取り下げの札、その後ろに差分の印を置き、行の文字を薄くする（正常系）。"""
    # 準備・実行
    page = open_story("shared-table--withdrawn")
    withdrawn = page.locator("tr[data-id='R-1']")
    other = page.locator("tr[data-id='D-1']")
    # 検証
    assert _title_marks(page, "R-1") == ["取り下げ", "変更"]
    assert _title_marks(page, "D-1") == []
    assert withdrawn.evaluate("e => getComputedStyle(e).color") != other.evaluate(
        "e => getComputedStyle(e).color"
    )
