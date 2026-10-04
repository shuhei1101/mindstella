"""PoC: 詳細パネルの本文の選択範囲を、元の Markdown の行の範囲へ対応づけられるかを確かめる。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page
from preview_fixture_types import OpenPreview, WritePreview
from workspace_fixtures import MakeItem

# 図を描き終わるまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000

# 本文の行（1 始まり）を左に添えた形で読むと、期待値の行が追える
BODY = "\n".join(
    [
        "# 見出しの一",  # 1
        "",  # 2
        "手順は **必ず** 守る。詳しくは [規約](https://e.x) と `code` と \\* を読む。",  # 3
        "二行目でも 守る と書く。",  # 4
        "三行目",  # 5
        "",  # 6
        "- 一つ目の段落",  # 7
        "",  # 8
        "  二つ目の段落",  # 9
        "- 次の項目",  # 10
        "",  # 11
        "1. 番号一",  # 12
        "2. 番号二",  # 13
        "   - 入れ子",  # 14
        "",  # 15
        "> 引用一",  # 16
        ">",  # 17
        "> 引用二",  # 18
        "",  # 19
        "| 列 A | 列 B |",  # 20
        "| --- | --- |",  # 21
        "| セル1 | セル2 |",  # 22
        "| セル3 | セル4 |",  # 23
        "",  # 24
        "```text",  # 25
        "コード一",  # 26
        "コード二",  # 27
        "```",  # 28
        "",  # 29
        "一行目ハード  ",  # 30（行末の空白 2 つ）
        "二行目ハード\\",  # 31（行末の \）
        "三行目ハード",  # 32
        "",  # 33
        "- 項目のコード",  # 34
        "",  # 35
        "  ```text",  # 36
        "  項目コード一",  # 37
        "  項目コード二",  # 38
        "  ```",  # 39
        "",  # 40
        "図の前の段落",  # 41
        "",  # 42
        "```mermaid",  # 43
        "flowchart LR",  # 44
        "  A --> B",  # 45
        "```",  # 46
        "",  # 47
        "図の後の段落",  # 48
        "",
    ]
)

# 根の要素の中の文を、全ての文字の並びの中の位置で選び、selectionLines の結果を返す
SELECT_JS = """
([root, startText, startNth, endText, endNth]) => {
  const container = document.querySelector(root);
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  const nodes = [];
  let all = "";
  while (walker.nextNode()) { nodes.push([walker.currentNode, all.length]); all += walker.currentNode.data; }
  const find = (text, nth) => { let at = -1; for (let i = 0; i <= nth; i++) at = all.indexOf(text, at + 1); return at; };
  const point = (offset) => {
    for (let i = nodes.length - 1; i >= 0; i--) {
      const [node, base] = nodes[i];
      if (base <= offset) return [node, offset - base];
    }
  };
  const start = find(startText, startNth);
  const end = find(endText, endNth) + endText.length;
  if (start < 0 || end < endText.length) throw new Error("文が見つからない: " + startText + " / " + endText);
  const range = document.createRange();
  const [sn, so] = point(start);
  const [en, eo] = point(end - 1);
  range.setStart(sn, so);
  range.setEnd(en, eo + 1);
  const result = MindmapPreview.selectionLines(range);
  return result === null ? null : [result.start, result.end];
}
"""

# 要素の中身を全て選び、selectionLines の結果を返す
SELECT_ALL_JS = """
(root) => {
  const range = document.createRange();
  range.selectNodeContents(document.querySelector(root));
  const result = MindmapPreview.selectionLines(range);
  return result === null ? null : [result.start, result.end];
}
"""

# 本文の行の印を持つべき要素のうち、印を持たないものの数（図の入れ物と原文は除く）
UNMARKED_JS = """
(root) => [...document.querySelectorAll(
  root + " .md p, " + root + " .md h4, " + root + " .md h5, " + root + " .md h6, "
  + root + " .md tr, " + root + " .md pre:not(.dg-raw), " + root + " .md ol > li"
)].filter(e => !e.closest(".diagram") && !e.hasAttribute("data-line-start")).map(e => e.tagName + ":" + e.textContent.slice(0, 10))
"""

# 印を足した描き方と、今の描き方の HTML を比べる（印の属性を除く）
SAME_LOOK_JS = """
(source) => {
  const before = DOMPurify.sanitize(marked.parse(source, { async: false }));
  const after = DOMPurify.sanitize(MindmapPreview.renderWithLines(source)).replace(/ data-line-start="\\d+"/g, "");
  return [before === after, before.length, after.length];
}
"""

# 1000 行の本文を今の描き方と印を足した描き方でそれぞれ 15 回描き、中央値のミリ秒を返す
TIMING_JS = """
(source) => {
  const median = (fn) => {
    const times = [];
    for (let i = 0; i < 15; i++) { const t = performance.now(); fn(); times.push(performance.now() - t); }
    times.sort((a, b) => a - b);
    return times[7];
  };
  const lines = source.split("\\n").length;
  const big = Array(Math.ceil(1000 / lines)).fill(source).join("\\n");
  const heap = () => performance.memory.usedJSHeapSize / 1024 / 1024;
  const heapStart = heap();
  const before = median(() => DOMPurify.sanitize(marked.parse(big, { async: false })));
  const heapBefore = heap();
  const after = median(() => DOMPurify.sanitize(MindmapPreview.renderWithLines(big)));
  const heapAfter = heap();
  return { lines: big.split("\\n").length, before, after, increase: after - before, heapStart, heapBefore, heapAfter };
}
"""

# 選択を作る場所（詳細パネル・詳細の全画面）
PANEL = "aside.panel"
FULL = "dialog.full"


@pytest.fixture
def body_url(write_preview: WritePreview, make_item: MakeItem) -> str:
    """同じ本文を持つ検討事項 D-1 と資料 A-1 のワークスペースを配る URL を返す。"""
    items: list[dict[str, Any]] = [
        make_item("D-1", status="未決定", body="D-1.md", depends_on=["D-2"]),
        make_item("D-2", status="決定済み"),
        make_item("A-1", deliverable=False, status="下書き", body="A-1.md"),
    ]
    return write_preview(*items, bodies={"D-1.md": BODY, "A-1.md": BODY})


def _open_panel(open_preview: OpenPreview, url: str, hash_text: str) -> Page:
    """詳細パネルを開き、図を描き終わるまで待つ。"""
    page = open_preview(url, hash_text)
    page.wait_for_selector("aside.panel.open .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    return page


CASES = [
    pytest.param("見出しの一", 0, "見出しの一", 0, [1, 1], id="heading"),
    pytest.param("三行目", 0, "三行目", 0, [5, 5], id="paragraph_third_line"),
    pytest.param("二つ目の段落", 0, "二つ目の段落", 0, [9, 9], id="loose_item_second_paragraph"),
    pytest.param("番号二", 0, "番号二", 0, [13, 13], id="ordered_list"),
    pytest.param("入れ子", 0, "入れ子", 0, [14, 14], id="nested_item"),
    pytest.param("引用二", 0, "引用二", 0, [18, 18], id="blockquote"),
    pytest.param("セル4", 0, "セル4", 0, [23, 23], id="table_cell"),
    pytest.param("列 B", 0, "列 B", 0, [20, 20], id="table_header"),
    pytest.param("コード二", 0, "コード二", 0, [27, 27], id="code_block"),
    pytest.param("項目コード二", 0, "項目コード二", 0, [38, 38], id="code_in_item"),
    pytest.param("必ず 守る", 0, "必ず 守る", 0, [3, 3], id="inline_bold"),
    pytest.param("規約 と code と * を読む", 0, "規約 と code と * を読む", 0, [3, 3], id="inline_link_code_escape"),
    pytest.param("詳しくは", 0, "二行目でも", 0, [3, 4], id="soft_break"),
    pytest.param("二行目ハード", 0, "二行目ハード", 0, [31, 31], id="hard_break_spaces"),
    pytest.param("三行目ハード", 0, "三行目ハード", 0, [32, 32], id="hard_break_backslash"),
    pytest.param("守る", 0, "守る", 0, [3, 3], id="duplicate_first"),
    pytest.param("守る", 1, "守る", 1, [4, 4], id="duplicate_second"),
    pytest.param("三行目", 0, "一つ目の段落", 0, [5, 7], id="across_paragraph_list"),
    pytest.param("図の前の段落", 0, "図の後の段落", 0, [41, 48], id="across_diagram"),
]


@pytest.mark.parametrize(("start", "start_nth", "end", "end_nth", "expected"), CASES)
def test_panel_lines(
    body_url: str,
    open_preview: OpenPreview,
    start: str,
    start_nth: int,
    end: str,
    end_nth: int,
    expected: list[int],
) -> None:
    """詳細パネルの本文の選択が、元の Markdown の行の範囲になる（正常系）。"""
    # 準備
    page = _open_panel(open_preview, body_url, "#tab=decisions&view=table&id=D-1")
    # 実行
    result = page.evaluate(SELECT_JS, [f"{PANEL} .md", start, start_nth, end, end_nth])
    # 検証
    assert result == expected


@pytest.mark.parametrize(("start", "start_nth", "end", "end_nth", "expected"), CASES)
def test_full_lines(
    body_url: str,
    open_preview: OpenPreview,
    start: str,
    start_nth: int,
    end: str,
    end_nth: int,
    expected: list[int],
) -> None:
    """詳細の全画面の本文の選択が、元の Markdown の行の範囲になる（正常系）。"""
    # 準備
    page = _open_panel(open_preview, body_url, "#tab=decisions&view=table&id=D-1")
    page.click(f'{PANEL} button[data-act="full"]')
    page.wait_for_selector(f"{FULL}[open] .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 実行
    result = page.evaluate(SELECT_JS, [f"{FULL} .md", start, start_nth, end, end_nth])
    # 検証
    assert result == expected


@pytest.mark.parametrize(("start", "start_nth", "end", "end_nth", "expected"), CASES)
def test_doc_lines(
    body_url: str,
    open_preview: OpenPreview,
    start: str,
    start_nth: int,
    end: str,
    end_nth: int,
    expected: list[int],
) -> None:
    """資料の本文の選択が、元の Markdown の行の範囲になる（正常系）。"""
    # 準備
    page = _open_panel(open_preview, body_url, "#tab=docs&id=A-1")
    # 実行
    result = page.evaluate(SELECT_JS, [f"{PANEL} .md", start, start_nth, end, end_nth])
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    "root",
    [
        pytest.param(f"{PANEL} .d-title", id="title"),
        pytest.param(f"{PANEL} button.idlink", id="related_items"),
        pytest.param(f"{PANEL} .dg-raw", id="diagram_raw"),
        pytest.param(f"{PANEL} .mermaid svg", id="diagram_svg"),
    ],
)
def test_outside_body(body_url: str, open_preview: OpenPreview, root: str) -> None:
    """本文の外の選択では行の範囲を返さない（異常系）。"""
    # 準備
    page = _open_panel(open_preview, body_url, "#tab=decisions&view=table&id=D-1")
    # 実行
    result = page.evaluate(SELECT_ALL_JS, root)
    # 検証
    assert result is None


def test_markers_survive(body_url: str, open_preview: OpenPreview) -> None:
    """無害化・図の置き換え・見出しの段下げの後も、印を付ける単位の全てが印を持つ（正常系）。"""
    # 準備
    page = _open_panel(open_preview, body_url, "#tab=decisions&view=table&id=D-1")
    # 実行
    unmarked = page.evaluate(UNMARKED_JS, PANEL)
    # 検証
    assert unmarked == []


def test_same_look(body_url: str, open_preview: OpenPreview) -> None:
    """印の属性を除いた HTML が、今の描き方の出力と一致する（正常系）。"""
    # 準備
    page = _open_panel(open_preview, body_url, "#tab=decisions&view=table&id=D-1")
    # 実行
    same, before_length, after_length = page.evaluate(SAME_LOOK_JS, BODY)
    # 検証
    assert same is True, (before_length, after_length)


def test_render_time(body_url: str, open_preview: OpenPreview) -> None:
    """1000 行の本文で、印を付ける描き方の増えが 100ms 以内（正常系）。"""
    # 準備
    page = _open_panel(open_preview, body_url, "#tab=decisions&view=table&id=D-1")
    # 実行
    timing = page.evaluate(TIMING_JS, BODY)
    print(f"描く時間: {timing}")
    # 検証
    assert timing["increase"] <= 100
