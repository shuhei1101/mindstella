"""部品設計『本文の印のツールチップ』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page
from storybook_fixture_types import OpenStory

# 位置の比べで許す差（ピクセル）。ツールチップを置いた後に文字の読み込みで本文が 1px ほど動くことがある
POSITION_TOLERANCE_PX = 2

# ツールチップの最大の高さ（ピクセル）と、印との間の空き・画面の端から空ける幅（ピクセル）
TIP_MAX_HEIGHT_PX = 360
TIP_GAP_PX = 6
SCREEN_EDGE_PX = 8

# 上下どちらにも収まらないストーリーの画面の大きさと、狭い幅のストーリーの画面の大きさ
SHORT_SIZE = {"width": 1000, "height": 420}
NARROW_SIZE = {"width": 390, "height": 844}

# ツールチップ（開いている）
TIP_OPEN = "#term-tip:popover-open"

# ツールチップの形（役割・種類ごとの見出し・項目のリンク・項目の説明・区切り線）を読む
READ_SHAPE_SCRIPT = """() => {
  const tip = document.getElementById('term-tip');
  const line = (element) => element === undefined ? null : getComputedStyle(element).borderTopWidth;
  return {
    role: tip.getAttribute('role'),
    kinds: [...tip.querySelectorAll('.tt-kind')].map((e) => e.textContent),
    links: [...tip.querySelectorAll('a.tt-link')].map((a) => a.dataset.id),
    bodies: [...tip.querySelectorAll('.tt-item')].map((li) => [
      li.querySelector('a.tt-link').dataset.id,
      li.querySelector('.tt-body')?.textContent ?? null,
    ]),
    groupLine: line(tip.querySelectorAll('.tt-group')[1]),
    itemLine: line(tip.querySelectorAll('.tt-item')[1]),
  };
}"""

# ツールチップと印の枠（小数のまま）・ツールチップの中のスクロールを読む
READ_BOX_SCRIPT = """() => {
  const tip = document.getElementById('term-tip');
  const box = tip.getBoundingClientRect();
  const mark = document.querySelector('a.term').getBoundingClientRect();
  return {
    top: box.top, bottom: box.bottom, left: box.left, right: box.right, height: box.height,
    markTop: mark.top, markBottom: mark.bottom,
    scrollable: tip.scrollHeight > tip.clientHeight,
  };
}"""


def _open_tip(open_story: OpenStory, story_id: str) -> Page:
    """ストーリーを開き、ツールチップが開いて置き場所が決まるのを待つ。"""
    page = open_story(story_id)
    page.wait_for_selector(TIP_OPEN)
    page.wait_for_timeout(300)
    return page


def test_term_only(open_story: OpenStory) -> None:
    """用語だけに一致した印。今と同じく用語・ID・意味を出し、役割は tooltip で、見出し・区切り線・リンクを持たない（正常系）。"""
    # 準備・実行
    page = _open_tip(open_story, "preview-termtip--term-only")
    # 検証
    shape: dict[str, Any] = page.evaluate(READ_SHAPE_SCRIPT)
    assert shape["role"] == "tooltip"
    assert shape["kinds"] == []
    assert shape["links"] == []
    assert page.text_content("#term-tip .tt-head") == "特殊効果G-1"
    assert page.text_content("#term-tip .tt-body") == "画面に重ねる演出"


def test_few(open_story: OpenStory) -> None:
    """用語・資料・調査に 1 件ずつ一致した印。種類ごとの見出しと区切り線で分け、全てのタイトルがリンクになる（正常系）。"""
    # 準備・実行
    page = _open_tip(open_story, "preview-termtip--few")
    # 検証
    shape: dict[str, Any] = page.evaluate(READ_SHAPE_SCRIPT)
    assert shape["role"] is None
    assert shape["kinds"] == ["用語 1", "資料 1", "調査 1"]
    assert shape["links"] == ["G-1", "A-2", "R-1"]
    assert shape["groupLine"] == "1px"


def test_several_terms(open_story: OpenStory) -> None:
    """用語 2 件だけに一致した印。「用語 2」の見出しの下に 2 件を区切り線で分けて並べ、それぞれ用語・ID・意味を出してタイトルをリンクにし、役割は付けない（正常系）。"""
    # 準備・実行
    page = _open_tip(open_story, "preview-termtip--several-terms")
    # 検証
    shape: dict[str, Any] = page.evaluate(READ_SHAPE_SCRIPT)
    bodies = dict(shape["bodies"])
    assert shape["role"] is None
    assert shape["kinds"] == ["用語 2"]
    assert shape["links"] == ["G-1", "G-2"]
    assert bodies == {"G-1": "画面に重ねる演出", "G-2": "特殊効果の別の言い方として使う用語"}
    assert shape["itemLine"] == "1px"


def test_doc_only(open_story: OpenStory) -> None:
    """資料 1 件だけに一致した印。「資料 1」の見出しの下に 1 件（正常系）。"""
    # 準備・実行
    page = _open_tip(open_story, "preview-termtip--doc-only")
    # 検証
    shape: dict[str, Any] = page.evaluate(READ_SHAPE_SCRIPT)
    assert shape["kinds"] == ["資料 1"]
    assert shape["links"] == ["A-2"]


def test_no_description(open_story: OpenStory) -> None:
    """説明を持たない資料。タイトルと ID だけを出し、説明の行を持たない（正常系）。"""
    # 準備・実行
    page = _open_tip(open_story, "preview-termtip--no-description")
    # 検証
    shape: dict[str, Any] = page.evaluate(READ_SHAPE_SCRIPT)
    bodies = dict(shape["bodies"])
    assert shape["links"] == ["G-1", "A-9", "A-3"]
    assert bodies["A-9"] is None
    assert bodies["A-3"] == "炎を揺らしながら画面の下から重ねるノード"
    assert shape["itemLine"] == "0px"


def test_many(open_story: OpenStory) -> None:
    """用語 1・資料 6・調査 1 に一致した印。最大の高さ（360px）で止まり、印の上に出し、中をスクロールして末尾の調査まで読める（正常系）。"""
    # 準備・実行
    page = _open_tip(open_story, "preview-termtip--many")
    page.wait_for_function("document.getElementById('term-tip').scrollTop > 0")
    # 検証
    box: dict[str, Any] = page.evaluate(READ_BOX_SCRIPT)
    assert box["height"] == pytest.approx(TIP_MAX_HEIGHT_PX, abs=POSITION_TOLERANCE_PX)
    assert box["bottom"] == pytest.approx(box["markTop"] - TIP_GAP_PX, abs=POSITION_TOLERANCE_PX)
    assert box["scrollable"] is True
    last = page.evaluate(
        "() => { const t = document.getElementById('term-tip'); const l = [...t.querySelectorAll('a.tt-link')].at(-1); const b = l.getBoundingClientRect(); const r = t.getBoundingClientRect(); return [l.dataset.id, b.bottom <= r.bottom + 1 && b.top >= r.top]; }"
    )
    assert last == ["R-1", True]


def test_below(open_story: OpenStory) -> None:
    """印の上に収まらない。印の下に出す（正常系）。"""
    # 準備・実行
    page = _open_tip(open_story, "preview-termtip--below")
    # 検証
    box: dict[str, Any] = page.evaluate(READ_BOX_SCRIPT)
    assert box["top"] == pytest.approx(box["markBottom"] + TIP_GAP_PX, abs=POSITION_TOLERANCE_PX)
    assert box["height"] == pytest.approx(TIP_MAX_HEIGHT_PX, abs=POSITION_TOLERANCE_PX)


def test_shrunk(page: Page, open_story: OpenStory) -> None:
    """上下どちらにも収まらない。広い側（上）に出して、印との 6px と画面の端の 8px を除いた高さに縮め、下端を印に留め、中をスクロールする（正常系）。"""
    # 準備（印の位置は描くときの画面の高さで決まるので、高さを変えてから開く）
    page.set_viewport_size(SHORT_SIZE)
    # 実行
    _open_tip(open_story, "preview-termtip--shrunk")
    # 検証
    box: dict[str, Any] = page.evaluate(READ_BOX_SCRIPT)
    assert box["bottom"] == pytest.approx(box["markTop"] - TIP_GAP_PX, abs=POSITION_TOLERANCE_PX)
    assert box["height"] == pytest.approx(box["markTop"] - TIP_GAP_PX - SCREEN_EDGE_PX, abs=POSITION_TOLERANCE_PX)
    assert box["top"] == pytest.approx(SCREEN_EDGE_PX, abs=POSITION_TOLERANCE_PX)
    assert box["scrollable"] is True


def test_link_focus(open_story: OpenStory) -> None:
    """印から Tab で中の最初のリンクへ移った。印の色の輪でフォーカスを示す（正常系）。"""
    # 準備・実行
    page = _open_tip(open_story, "preview-termtip--link-focus")
    # 検証
    page.wait_for_function("document.activeElement?.matches('#term-tip a.tt-link')")
    ring = page.evaluate(
        "() => { const s = getComputedStyle(document.activeElement); return [document.activeElement.dataset.id, s.outlineStyle, s.outlineWidth]; }"
    )
    assert ring == ["G-1", "solid", "2px"]


def test_long_narrow(page: Page, open_story: OpenStory) -> None:
    """長いタイトル・説明を幅 390px で出す。折り返し、画面の端から 8px の内側に収まり、横にあふれない（正常系）。"""
    # 準備（ツールチップの幅は描くときの画面の幅で決まるので、幅を変えてから開く）
    page.set_viewport_size(NARROW_SIZE)
    # 実行
    _open_tip(open_story, "preview-termtip--long-narrow")
    # 検証
    box: dict[str, Any] = page.evaluate(READ_BOX_SCRIPT)
    assert box["left"] >= SCREEN_EDGE_PX - 0.5
    assert box["right"] <= NARROW_SIZE["width"] - SCREEN_EDGE_PX + 0.5
    long_link = page.evaluate(
        "() => { const l = document.querySelector('#term-tip a.tt-link[data-id=\"A-10\"]'); return l.getBoundingClientRect().height > parseFloat(getComputedStyle(l).lineHeight) * 1.5; }"
    )
    assert long_link is True
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
