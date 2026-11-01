"""部品設計『選んだ箇所のコメントの入口』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# ストーリーが選んだ範囲として渡す矩形（画面の中ほどの 1 行）の左端と、始まりの上端
MIDDLE_ANCHOR_LEFT_PX = 120
MIDDLE_ANCHOR_TOP_PX = 160

# 上に収まらないストーリー（Below）が選んだ範囲の終わりの行として渡す矩形の左端と、下端
BELOW_ANCHOR_LAST_LEFT_PX = 120
BELOW_ANCHOR_LAST_BOTTOM_PX = 72

# 入口と選んだ範囲との間の空き（ピクセル）
PILL_GAP_PX = 6

# 入口の大きさ（ピクセル）。押せる的は高さ 32px 以上
PILL_SIZE_PX = 32

# 入口を画面の端から内側に収める幅（ピクセル）
SCREEN_EDGE_PX = 8

# ポインターを入口からツールチップへ動かすときの刻み（間の透明な領域を通る）
POINTER_STEPS = 10

# 入口の名前（読み上げとツールチップ）
PILL_NAME = "選んだ箇所にコメント"

PILL = "button.selection-comment"
TIP = "button.selection-comment .sc-tip"

# 入口の枠を読む
PILL_BOX_SCRIPT = """() => {
  const r = document.querySelector('button.selection-comment').getBoundingClientRect();
  return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height };
}"""

# ツールチップの枠を読む
TIP_BOX_SCRIPT = """() => {
  const r = document.querySelector('button.selection-comment .sc-tip').getBoundingClientRect();
  return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height };
}"""

# 入口の見た目（面の色・輪・角の丸め）を読む
PILL_STYLE_SCRIPT = """() => {
  const s = getComputedStyle(document.querySelector('button.selection-comment'));
  return { background: s.backgroundColor, outline: s.outlineStyle, radius: parseFloat(s.borderTopLeftRadius) };
}"""

# 入口の面が透けていないか（面の色の不透明度が 1 か）を読む
PILL_OPAQUE_SCRIPT = """() => {
  const probe = document.createElement('canvas').getContext('2d');
  probe.fillStyle = getComputedStyle(document.querySelector('button.selection-comment')).backgroundColor;
  return probe.fillStyle.startsWith('#');
}"""


def test_above(open_story: OpenStory) -> None:
    """選んだ範囲の始まりの上に出す。幅と高さ 32px の丸に印だけで、左端を始まりの左端に揃え、面は不透明（正常系）。"""
    # 準備・実行
    page = open_story("preview-selectioncomment--above")
    # 検証
    pill = page.get_by_role("button", name=PILL_NAME)
    assert pill.count() == 1
    assert pill.locator("svg.icon").count() == 1
    assert pill.inner_text() == ""
    box = page.evaluate(PILL_BOX_SCRIPT)
    assert box["bottom"] == MIDDLE_ANCHOR_TOP_PX - PILL_GAP_PX
    assert box["left"] == MIDDLE_ANCHOR_LEFT_PX
    assert box["width"] == PILL_SIZE_PX
    assert box["height"] == PILL_SIZE_PX
    assert page.evaluate(PILL_STYLE_SCRIPT)["radius"] >= PILL_SIZE_PX / 2
    assert page.evaluate(PILL_OPAQUE_SCRIPT)
    assert page.locator(PILL).get_attribute("data-side") == "above"


def test_hover(open_story: OpenStory) -> None:
    """ホバー。面の色を変え、名前のツールチップを入口の上に出し、ツールチップへポインターを動かしても消さない（正常系）。"""
    # 準備
    page = open_story("preview-selectioncomment--hover")
    before = page.evaluate(PILL_STYLE_SCRIPT)
    assert page.locator(TIP).is_hidden()
    # 実行
    page.hover(PILL)
    # 検証（面の色だけを変え、フォーカスの輪は出さない。ツールチップは入口の上に名前を出す）
    after = page.evaluate(PILL_STYLE_SCRIPT)
    assert after["background"] != before["background"]
    assert after["outline"] == "none"
    assert page.locator(TIP).is_visible()
    assert page.locator(TIP).inner_text() == PILL_NAME
    pill_box = page.evaluate(PILL_BOX_SCRIPT)
    tip_box = page.evaluate(TIP_BOX_SCRIPT)
    assert tip_box["bottom"] <= pill_box["top"]
    # 実行（ポインターを入口の中央から真上の、ツールチップの縦の中央へ動かす）
    page.mouse.move(
        (pill_box["left"] + pill_box["right"]) / 2,
        (tip_box["top"] + tip_box["bottom"]) / 2,
        steps=POINTER_STEPS,
    )
    # 検証（ツールチップの上でも消えない）
    assert page.locator(TIP).is_visible()


def test_focus(open_story: OpenStory) -> None:
    """キーボードのフォーカス。印の色の輪で、ホバーと見分け、ホバーと同じ名前のツールチップを出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-selectioncomment--focus")
    page.wait_for_function("document.activeElement?.classList.contains('selection-comment')")
    # 検証
    assert page.evaluate(PILL_STYLE_SCRIPT)["outline"] == "solid"
    assert page.locator(TIP).is_visible()
    assert page.locator(TIP).inner_text() == PILL_NAME


def test_below(open_story: OpenStory) -> None:
    """上に収まらない。選んだ範囲の終わりの下に、終わりの行の左端に揃えて出し、ツールチップは入口の下に出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-selectioncomment--below")
    page.hover(PILL)
    # 検証
    box = page.evaluate(PILL_BOX_SCRIPT)
    assert box["top"] == BELOW_ANCHOR_LAST_BOTTOM_PX + PILL_GAP_PX
    assert box["left"] == BELOW_ANCHOR_LAST_LEFT_PX
    assert box["width"] == PILL_SIZE_PX
    assert box["height"] == PILL_SIZE_PX
    assert page.locator(PILL).get_attribute("data-side") == "below"
    assert page.locator(TIP).is_visible()
    assert page.evaluate(TIP_BOX_SCRIPT)["top"] >= box["bottom"]


def test_narrow(page: Page, open_story: OpenStory) -> None:
    """幅 390px で選んだ範囲が画面の端に寄る。入口を画面の端から 8px の内側に収め、ツールチップを入口の右端に揃えて画面の外へはみ出さない（正常系）。"""
    # 準備（入口の位置は描くときの画面の幅で決まるので、幅を変えてから開く）
    page.set_viewport_size(NARROW_SIZE)
    open_story("preview-selectioncomment--narrow")
    # 実行
    page.hover(PILL)
    # 検証
    box = page.evaluate(PILL_BOX_SCRIPT)
    tip = page.evaluate(TIP_BOX_SCRIPT)
    assert box["right"] == NARROW_SIZE["width"] - SCREEN_EDGE_PX
    assert box["width"] == PILL_SIZE_PX
    assert page.locator(PILL).get_attribute("data-tip") == "end"
    assert tip["right"] <= box["right"]
    assert tip["left"] >= 0
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
