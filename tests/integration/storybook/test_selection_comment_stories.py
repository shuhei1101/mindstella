"""部品設計『選んだ箇所のコメントの入口』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# ストーリーが選んだ範囲として渡す矩形（画面の中ほどの 1 行）の下端
MIDDLE_ANCHOR_BOTTOM_PX = 182

# 入口と選んだ範囲との間の空き（ピクセル）
PILL_GAP_PX = 6

# 入口の大きさ（ピクセル）。押せる的は高さ 32px 以上
PILL_WIDTH_PX = 104
PILL_HEIGHT_PX = 32

# 入口を画面の端から内側に収める幅（ピクセル）
SCREEN_EDGE_PX = 8

# 画面の下に収まらないストーリーが、選んだ範囲の始まりの上端を置く画面の下端からの距離（ピクセル）
ABOVE_ANCHOR_FIRST_TOP_FROM_BOTTOM_PX = 70

# 入口の枠を読む
PILL_BOX_SCRIPT = """() => {
  const r = document.querySelector('button.selection-comment').getBoundingClientRect();
  return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height };
}"""

# 入口の見た目（面の色・輪・角の丸め）を読む
PILL_STYLE_SCRIPT = """() => {
  const s = getComputedStyle(document.querySelector('button.selection-comment'));
  return { background: s.backgroundColor, outline: s.outlineStyle, radius: parseFloat(s.borderTopLeftRadius) };
}"""


def test_below(open_story: OpenStory) -> None:
    """選んだ範囲の終わりの下に出す。角を丸め切った横長の形（ピル）に、印と「コメント」を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-selectioncomment--below")
    # 検証
    pill = page.get_by_role("button", name="選んだ箇所にコメント")
    assert pill.count() == 1
    assert pill.inner_text() == "コメント"
    assert pill.locator("svg.icon").count() == 1
    box = page.evaluate(PILL_BOX_SCRIPT)
    assert box["top"] == MIDDLE_ANCHOR_BOTTOM_PX + PILL_GAP_PX
    assert box["height"] >= PILL_HEIGHT_PX
    assert page.evaluate(PILL_STYLE_SCRIPT)["radius"] >= box["height"] / 2


def test_hover(open_story: OpenStory) -> None:
    """ホバー。面の色だけを変え、キーボードのフォーカスの輪は出さない（正常系）。"""
    # 準備
    page = open_story("preview-selectioncomment--hover")
    before = page.evaluate(PILL_STYLE_SCRIPT)
    # 実行
    page.hover("button.selection-comment")
    # 検証
    after = page.evaluate(PILL_STYLE_SCRIPT)
    assert after["background"] != before["background"]
    assert after["outline"] == "none"


def test_focus(open_story: OpenStory) -> None:
    """キーボードのフォーカス。印の色の輪を出し、ホバーと見分ける（正常系）。"""
    # 準備・実行
    page = open_story("preview-selectioncomment--focus")
    page.wait_for_function("document.activeElement?.classList.contains('selection-comment')")
    # 検証
    assert page.evaluate(PILL_STYLE_SCRIPT)["outline"] == "solid"


def test_above(open_story: OpenStory) -> None:
    """下に収まらない。選んだ範囲の始まりの上に出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-selectioncomment--above")
    # 検証
    box = page.evaluate(PILL_BOX_SCRIPT)
    viewport_height = page.evaluate("innerHeight")
    first_top = viewport_height - ABOVE_ANCHOR_FIRST_TOP_FROM_BOTTOM_PX
    assert box["bottom"] == first_top - PILL_GAP_PX
    assert box["height"] >= PILL_HEIGHT_PX


def test_narrow(page: Page, open_story: OpenStory) -> None:
    """幅 390px で選んだ範囲が画面の端に寄る。入口を画面の端から 8px の内側に収める（正常系）。"""
    # 準備（入口の位置は描くときの画面の幅で決まるので、幅を変えてから開く）
    page.set_viewport_size(NARROW_SIZE)
    # 実行
    open_story("preview-selectioncomment--narrow")
    # 検証
    box = page.evaluate(PILL_BOX_SCRIPT)
    assert box["left"] >= SCREEN_EDGE_PX
    assert box["right"] <= NARROW_SIZE["width"] - SCREEN_EDGE_PX
    assert box["width"] == PILL_WIDTH_PX
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
