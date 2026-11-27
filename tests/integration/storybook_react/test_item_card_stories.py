"""部品設計『項目のカード.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Locator, expect

from .storybook_react_fixture_types import OpenStory

# カードの右端・下端からマーカーまでの許す差（パディング分。px）
EDGE_TOLERANCE_PX = 12

# 部品設計の状態
STATES = (
    "shared-itemcard--selectable-tags",
    "shared-itemcard--selectable-tags-selected",
    "shared-itemcard--default",
    "shared-itemcard--with-comments",
    "shared-itemcard--selected-with-comments",
    "shared-itemcard--dates",
    "shared-itemcard--dates-narrow",
    "shared-itemcard--title-id-markers",
    "shared-itemcard--favorite-off",
    "shared-itemcard--favorite-on",
    "shared-itemcard--favorite-long-title",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_selectable_tags(open_story: OpenStory) -> None:
    """外枠は div で、タイトルのボタンとタグのボタンを入れ子にせず並べる（正常系）。"""
    # 準備・実行
    page = open_story("shared-itemcard--selectable-tags")
    card = page.locator("div[data-card='T-1']")
    # 検証
    expect(card.locator("button[data-id='T-1']")).to_have_text("絞り込みの条件をタブの保存領域に残す")
    expect(card.locator("button[data-tag]")).to_have_count(3)
    expect(card.get_by_role("button", name="タグ「保存」で絞り込む")).to_be_visible()
    assert page.locator("button button").count() == 0
    expect(card.locator("button[data-id='T-1']")).not_to_have_attribute("aria-current", "true")


def test_selectable_tags_selected(open_story: OpenStory) -> None:
    """開いている項目のタイトルに aria-current を付け、タグを押せるまま残す（正常系）。"""
    # 準備・実行
    page = open_story("shared-itemcard--selectable-tags-selected")
    card = page.locator("div[data-card='T-1']")
    # 検証
    expect(card.locator("button[data-id='T-1']")).to_have_attribute("aria-current", "true")
    expect(card.locator("button[data-tag]")).to_have_count(3)


def test_default(open_story: OpenStory) -> None:
    """onSelectTag を指定しないカードはタグを並べない（正常系）。"""
    # 準備・実行
    page = open_story("shared-itemcard--default")
    card = page.locator("div[data-card='T-1']")
    # 検証
    expect(card.locator("button[data-id='T-1']")).to_be_visible()
    expect(card.locator("[data-tag]")).to_have_count(0)


def _mark_box(page_card: Locator) -> dict[str, float]:
    """カードとコメントのマーカーの位置を返す（マーカーの右端・下端とカードの右端・下端の差、ID の行の下端）。"""
    return page_card.evaluate(
        """(card) => {
            const box = card.getBoundingClientRect();
            const mark = card.querySelector('[title^="コメント"]').getBoundingClientRect();
            const idRow = card.querySelector('.font-mono').getBoundingClientRect();
            return {right: box.right - mark.right, bottom: box.bottom - mark.bottom, markTop: mark.top, idBottom: idRow.bottom};
        }"""
    )


def test_with_comments(open_story: OpenStory) -> None:
    """コメントのマーカーをカードの一番下の行の右に配置し、ID の行には配置しない（正常系）。"""
    # 準備・実行
    page = open_story("shared-itemcard--with-comments")
    card = page.locator("div[data-card='T-1']")
    # 検証
    expect(card.get_by_title("コメント 3 件")).to_be_visible()
    box = _mark_box(card)
    assert box["markTop"] >= box["idBottom"]
    assert box["right"] <= EDGE_TOLERANCE_PX
    assert box["bottom"] <= EDGE_TOLERANCE_PX


def test_selected_with_comments(open_story: OpenStory) -> None:
    """選択中のカードは枠と背景がほかのカードと違い、右下のコメントのマーカーの色は変えない（正常系）。"""
    # 準備
    plain = open_story("shared-itemcard--with-comments")
    plain_style = _card_style(plain.locator("div[data-card='T-1']"))
    # 実行
    page = open_story("shared-itemcard--selected-with-comments")
    selected_style = _card_style(page.locator("div[data-card='T-1']"))
    # 検証
    assert selected_style["border"] != plain_style["border"]
    assert selected_style["background"] != plain_style["background"]
    assert selected_style["mark"] == plain_style["mark"]


def _card_style(card: Locator) -> dict[str, str]:
    """カードの枠・背景と、コメントのマーカーの縁・面の色を返す。"""
    return card.evaluate(
        """(card) => {
            const style = getComputedStyle(card);
            const mark = getComputedStyle(card.querySelector('[title^="コメント"]'));
            return {border: style.borderTopColor, background: style.backgroundColor, mark: `${mark.borderTopColor} ${mark.backgroundColor}`};
        }"""
    )


def test_dates(open_story: OpenStory) -> None:
    """種類・状態の文字の行の次に「作成 {日時}」「更新 {日時}」を出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-itemcard--dates")
    dates = page.locator("[data-part='item-dates'] > span")
    # 検証
    expect(dates).to_have_text(["作成 11/02 10:15", "更新 11/20 18:40"])


def test_dates_narrow(open_story: OpenStory) -> None:
    """列の幅 240px。日時は組ごとに折り返し、カードの外へはみ出さない（正常系）。"""
    # 準備・実行
    page = open_story("shared-itemcard--dates-narrow")
    card = page.locator("[data-card]").first
    dates = page.locator("[data-part='item-dates']")
    # 検証
    card_box = card.bounding_box()
    dates_box = dates.bounding_box()
    assert card_box is not None and dates_box is not None
    assert dates_box["x"] + dates_box["width"] <= card_box["x"] + card_box["width"] + 1


# 見本の記録の D-1 のツールチップに出る文字（タイトル・ID・種類・状態）
D1_TIP_TEXTS = ("保存先の決め方", "D-1", "検討事項", "未決定")


def test_title_id_markers(open_story: OpenStory) -> None:
    """タイトルと関係する項目のタイトルの中の記録にある D-1 をマーカーにし、D-99 は文字のまま、カードの中にリンクを増やさない（正常系）。"""
    # 準備・実行
    page = open_story("shared-itemcard--title-id-markers")
    card = page.locator("div[data-card]")
    title = card.locator("button[data-id]")
    # 検証
    expect(title.locator("[data-record-id='D-1']")).to_have_text("D-1")
    expect(title.locator("[data-record-id='D-99']")).to_have_count(0)
    expect(card.locator("a")).to_have_count(0)
    expect(card.locator(":scope > span [data-record-id='D-1']")).to_have_count(1)
    described = (title.get_attribute("aria-describedby") or "").split()
    expect(page.locator(f"#{described[0]}")).to_contain_text("保存先の決め方（D-1）")


@pytest.mark.parametrize("viewport", [{"width": 1280, "height": 800}, {"width": 390, "height": 844}])
def test_title_id_marker_hover(open_story: OpenStory, viewport: dict[str, int]) -> None:
    """タイトルの D-1 のマーカーに乗せると、ボタンの ::after に覆われずに D-1 のツールチップを出す（正常系）。"""
    # 準備
    page = open_story("shared-itemcard--title-id-markers")
    page.set_viewport_size(viewport)
    # 実行
    page.locator("button[data-id] [data-record-id='D-1']").hover()
    # 検証
    tip = page.locator(".term-tip")
    expect(tip).to_be_visible()
    for text in D1_TIP_TEXTS:
        expect(tip).to_contain_text(text)


def test_title_id_marker_focus(open_story: OpenStory) -> None:
    """タイトルのボタンに Tab でフォーカスすると、タイトルの中の D-1 のツールチップを出す（正常系）。"""
    # 準備
    page = open_story("shared-itemcard--title-id-markers")
    # 実行
    page.keyboard.press("Tab")
    # 検証
    expect(page.locator("button[data-id]")).to_be_focused()
    expect(page.locator(".term-tip")).to_contain_text("保存先の決め方")


@pytest.mark.parametrize(
    ("state", "pressed"),
    [
        pytest.param("shared-itemcard--favorite-off", "false", id="off"),
        pytest.param("shared-itemcard--favorite-on", "true", id="on"),
    ],
)
def test_favorite(open_story: OpenStory, state: str, pressed: str) -> None:
    """カードの右上に星を出し、登録しているかを aria-pressed で示す（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    card = page.locator("[data-card]").first
    star = card.locator("[data-favorite]")
    expect(star).to_have_attribute("aria-pressed", pressed)
    card_box = card.bounding_box()
    star_box = star.bounding_box()
    assert card_box is not None and star_box is not None
    assert star_box["x"] + star_box["width"] <= card_box["x"] + card_box["width"]
    assert star_box["x"] > card_box["x"] + card_box["width"] / 2
    assert star_box["y"] - card_box["y"] < star_box["height"]


def test_favorite_long_title(open_story: OpenStory) -> None:
    """長いタイトルは星と重ならずに折り返す（正常系）。"""
    # 準備・実行
    page = open_story("shared-itemcard--favorite-long-title")
    # 検証
    card = page.locator("[data-card]").first
    title = card.locator("button[data-id]").bounding_box()
    star = card.locator("[data-favorite]").bounding_box()
    assert title is not None and star is not None
    assert title["x"] + title["width"] <= star["x"] + 1
