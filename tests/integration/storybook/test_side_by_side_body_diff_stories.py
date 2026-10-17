"""部品設計『左右に並べた本文の差分』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page
from storybook_fixture_types import OpenStory

# 描き終わるまで待つ上限ミリ秒（図は描画のライブラリを読んでから描く）
DIAGRAM_TIMEOUT_MS = 20_000

# 左右の列
BEFORE = ".sbs section.sbs-before"
AFTER = ".sbs section.sbs-after"

# 左右の列ごとに、直下の行の位置・変えた行か・向かいの空きか・文字を返す
_ROWS_JS = """() => [...document.querySelectorAll('.sbs .sbs-col')].map((column) =>
    [...column.querySelectorAll(':scope > .sbs-row')].map((row) => ({
        top: row.getBoundingClientRect().top,
        changed: row.classList.contains('sbs-chg'),
        gap: row.classList.contains('sbs-gap'),
        text: row.textContent.trim(),
    }))
)"""

# 列の中の語の面を、列ごとに文字で返す
_WORDS_JS = """(selector) => [...document.querySelectorAll(`${selector} span.df-word`)].map((word) => word.textContent)"""


def _open(open_story: OpenStory, state: str) -> Page:
    """ストーリーを開く。"""
    return open_story(f"preview-sidebysidebodydiff--{state}")


def _rows(page: Page) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """左右の列の行を返す。"""
    before, after = page.evaluate(_ROWS_JS)
    return before, after


def test_paragraphs(open_story: OpenStory) -> None:
    """1 つ目の段落を消し、末尾に段落を足した。左に消した段落と向かいの縞の空き、右に足した段落と向かいの縞の空きを出し、変えていない段落は左右の同じ高さに印なしで並ぶ（正常系）。"""
    # 準備・実行
    page = _open(open_story, "paragraphs")
    # 検証（列は読み上げの名前を持ち、列の頭の名前の行と空きは読み上げない）
    assert page.get_attribute(BEFORE, "aria-label") == "選んだ時点の本文"
    assert page.get_attribute(AFTER, "aria-label") == "今の本文"
    assert page.get_attribute(".sbs .sbs-head", "aria-hidden") == "true"
    assert page.locator(".sbs .sbs-row.sbs-gap[aria-hidden=true]").count() == 2
    # 検証（左に消した段落、右に足した段落。向かいは空き）
    before, after = _rows(page)
    assert [row["gap"] for row in before] == [False, False, False, True]
    assert [row["gap"] for row in after] == [True, False, False, False]
    assert "消した一つ目の段落です。" in before[0]["text"]
    assert "足した四つ目の段落です。" in after[3]["text"]
    # 検証（消したは左だけ、足したは右だけで、記号と色で分ける）
    assert page.inner_text(f"{BEFORE} del.df-blk > .df-sign") == "−"
    assert page.inner_text(f"{AFTER} ins.df-blk > .df-sign") == "+"
    assert page.locator(f"{BEFORE} ins.df-blk").count() == 0
    assert page.locator(f"{AFTER} del.df-blk").count() == 0
    assert page.eval_on_selector(f"{BEFORE} del.df-blk", "e => getComputedStyle(e).backgroundColor") != page.eval_on_selector(
        f"{AFTER} ins.df-blk", "e => getComputedStyle(e).backgroundColor"
    )
    # 検証（変えていない段落は印なしで、左右の同じ高さに並ぶ）
    assert [row["top"] for row in before] == [row["top"] for row in after]
    assert page.locator(f"{BEFORE} > .sbs-row:not(.sbs-chg) :is(ins, del)").count() == 0
    assert page.locator(f"{AFTER} > .sbs-row:not(.sbs-chg) :is(ins, del)").count() == 0


def test_rewritten(open_story: OpenStory) -> None:
    """段落の中の語を書き換えた。左の消した段落と右の足した段落が向かい合い、変わった語だけに濃い面を付ける（正常系）。"""
    # 準備・実行
    page = _open(open_story, "rewritten")
    page.wait_for_selector(f"{AFTER} span.df-word")
    # 検証（向かい合う 1 行）
    before, after = _rows(page)
    assert [row["changed"] for row in before] == [False, True, False]
    assert [row["gap"] for row in before + after] == [False] * 6
    assert before[1]["top"] == after[1]["top"]
    # 検証（変わった語だけに濃い面）
    assert "".join(page.evaluate(_WORDS_JS, BEFORE)) == "来週"
    assert "".join(page.evaluate(_WORDS_JS, AFTER)) == "今週"
    assert page.locator(f"{BEFORE} > .sbs-row:not(.sbs-chg) span.df-word").count() == 0
    # 検証（濃い面の下も行の面・記号は残る）
    assert page.inner_text(f"{BEFORE} del.df-blk > .df-sign") == "−"
    assert page.inner_text(f"{AFTER} ins.df-blk > .df-sign") == "+"


def test_table_and_list(open_story: OpenStory) -> None:
    """表の行と箇条書きの項目を変えた。左に消した行・項目、右に足した行・項目の印を付け、消した箇条書きの項目は消した色の面と取り消し線で出す（正常系）。"""
    # 準備・実行
    page = _open(open_story, "table-and-list")
    page.wait_for_selector(f"{AFTER} tr.df-add")
    # 検証（表の行）
    assert "並べ替えた" in page.inner_text(f"{BEFORE} tr.df-del")
    assert "変わった語" in page.inner_text(f"{AFTER} tr.df-add")
    assert page.locator(f"{BEFORE} tr.df-add").count() == 0
    assert page.locator(f"{AFTER} tr.df-del").count() == 0
    # 検証（箇条書きの項目: 消した項目は消した色の面と取り消し線、足した項目は足した色の面）
    assert "左上" in page.inner_text(f"{BEFORE} li.df-li-del")
    assert "右上" in page.inner_text(f"{AFTER} li.df-li-add")
    assert page.eval_on_selector(f"{BEFORE} li.df-li-del", "e => getComputedStyle(e).textDecorationLine") == "line-through"
    assert page.eval_on_selector(f"{BEFORE} li.df-li-del", "e => getComputedStyle(e).backgroundColor") != "rgba(0, 0, 0, 0)"
    assert page.eval_on_selector(f"{AFTER} li.df-li-add", "e => getComputedStyle(e).backgroundColor") != "rgba(0, 0, 0, 0)"


def test_diagram(open_story: OpenStory) -> None:
    """図の記法を変えた。左は選んだ時点の図に消した色の破線の枠だけを付け、右は今の図に今と同じ色付けと凡例を付ける（正常系）。"""
    # 準備・実行
    page = _open(open_story, "diagram")
    page.wait_for_selector(f"{AFTER} figure.diagram.df-colored", timeout=DIAGRAM_TIMEOUT_MS)
    page.wait_for_selector(f"{BEFORE} .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証（左: 色付けも凡例も付けず、消した色の破線の枠だけ）
    assert page.locator(f"{BEFORE} figure.diagram.df-colored").count() == 0
    assert page.locator(f"{BEFORE} .df-legend").count() == 0
    assert page.eval_on_selector(f"{BEFORE} figure.diagram", "e => getComputedStyle(e).outlineStyle") == "dashed"
    # 検証（右: 足したノードと変えたノードの色付けと凡例）
    assert page.locator(f"{AFTER} figure.diagram.df-colored g.df-n-add").count() == 1
    assert page.locator(f"{AFTER} figure.diagram.df-colored g.df-n-chg").count() == 1
    assert page.locator(f"{AFTER} .df-legend").count() == 1
    assert page.eval_on_selector(f"{AFTER} figure.diagram", "e => getComputedStyle(e).outlineStyle") != "dashed"
