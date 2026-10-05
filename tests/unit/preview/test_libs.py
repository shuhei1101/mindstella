"""core/libs.ts（描画のライブラリの有無と呼び出し・選んだ範囲から箇所を求める処理）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadLibrary, LoadPreviewScripts

# 本文の Markdown（見出し・表・実行される属性を持つ画像・mermaid のコードブロック）
MARKDOWN_SOURCE = (
    "# 見出し\n\n"
    "| 列 A | 列 B |\n| --- | --- |\n| 1 | 2 |\n\n"
    "<img src=x onerror=alert(1)>\n\n"
    "```mermaid\nflowchart TD\n  A --> B\n```\n"
)


def test_missing_libraries(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """グローバルが無いものだけ返す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    missing = preview_page.evaluate(
        """() => {
            window.marked = {};
            return MindmapPreview.missingLibraries(["marked", "DOMPurify"]);
        }"""
    )
    # 検証
    assert missing == ["DOMPurify"]


def test_library_notice(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """名前を並べた知らせを返す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    notice = preview_page.evaluate(
        """() => {
            const element = MindmapPreview.libraryNotice({names: ["marked", "DOMPurify"], what: "本文"});
            return {role: element.getAttribute("role"), text: element.textContent};
        }"""
    )
    # 検証
    assert notice["role"] == "alert"
    assert "読み込めなかったライブラリ: marked・DOMPurify" in notice["text"]
    assert "通信を確認して、ページを再読み込みしてください。" in notice["text"]


def test_render_markdown(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """無害化して描き、図の入れ物を作る（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    # 実行
    result = preview_page.evaluate(
        """(source) => {
            const root = MindmapPreview.renderMarkdown(source);
            const containers = root.querySelectorAll("[data-source]");
            return {
                hasHeading: root.querySelector("h1") !== null,
                hasTable: root.querySelector("table") !== null,
                html: root.innerHTML,
                containerCount: containers.length,
                source: containers.length > 0 ? containers[0].getAttribute("data-source") : null,
            };
        }""",
        MARKDOWN_SOURCE,
    )
    # 検証
    assert result["hasHeading"] is True
    assert result["hasTable"] is True
    assert "onerror" not in result["html"]
    assert result["containerCount"] == 1
    assert "flowchart TD" in result["source"]


def test_render_markdown_when_library_missing(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """ライブラリが無ければ知らせと原文（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """(source) => {
            const root = MindmapPreview.renderMarkdown(source);
            return {
                alert: root.querySelector('[role="alert"]').textContent,
                pre: root.querySelector("pre").textContent,
            };
        }""",
        MARKDOWN_SOURCE,
    )
    # 検証
    for name in ("marked", "DOMPurify", "mermaid"):
        assert name in result["alert"]
    assert result["pre"] == MARKDOWN_SOURCE


def test_render_diagrams(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """図を SVG に描き、描けない図は原文を残す（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("mermaid")
    broken_source = "これは図の構文ではない ((("
    # 実行
    result = preview_page.evaluate(
        """async (brokenSource) => {
            const root = document.createElement("div");
            for (const source of ["flowchart TD\\n  A --> B", brokenSource]) {
                const container = document.createElement("div");
                container.setAttribute("data-source", source);
                root.append(container);
            }
            document.body.append(root);
            await MindmapPreview.renderDiagrams(root);
            return [...root.children].map((container) => ({
                hasSvg: container.querySelector("svg") !== null,
                text: container.textContent,
            }));
        }""",
        broken_source,
    )
    # 検証
    assert result[0]["hasSvg"] is True
    assert result[1]["hasSvg"] is False
    assert "この図は表示できませんでした。原文を表示します。" in result[1]["text"]
    assert broken_source in result[1]["text"]


# 行の印を確かめる本文。左の数字は本文の行（1 始まり）で、表は見出しの行と区切りの行の次から 1 行ずつ、フェンスのコードはフェンスの次の行を印にする
LINE_MARK_SOURCE = "\n".join(
    [
        "# 見出し",  # 1
        "",  # 2
        "段落の一行目",  # 3
        "続きの行",  # 4
        "",  # 5
        "- 項目一",  # 6
        "  - 入れ子",  # 7
        "",  # 8
        "| 列 A | 列 B |",  # 9
        "| --- | --- |",  # 10
        "| 1 | 2 |",  # 11
        "| 3 | 4 |",  # 12
        "",  # 13
        "```text",  # 14
        "コード一",  # 15
        "コード二",  # 16
        "```",  # 17
        "",  # 18
        "```mermaid",  # 19
        "flowchart TD",  # 20
        "  A --> B",  # 21
        "```",  # 22
        "",
    ]
)

# 行の印を付けても見た目が変わらないことを比べる本文（図を含まない）
LOOK_SOURCE = "\n".join(LINE_MARK_SOURCE.split("\n")[:17]) + "\n"


def test_render_markdown_when_line_marks(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """ブロックに元の行の印を付け、見た目を変えない（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    # 実行
    result = preview_page.evaluate(
        """([source, lookSource]) => {
            const root = MindmapPreview.renderMarkdown(source);
            const marks = (selector) =>
                [...root.querySelectorAll(selector)].map((e) => e.getAttribute("data-line-start"));
            const plain = DOMPurify.sanitize(marked.parse(lookSource, {async: false}));
            const marked_ = MindmapPreview.renderMarkdown(lookSource).innerHTML;
            return {
                heading: marks("h1"),
                paragraph: marks("p"),
                items: marks("li"),
                rows: marks("tr"),
                code: marks("pre:not(.dg-raw)"),
                diagramMarks: root.querySelectorAll(".diagram [data-line-start]").length,
                containerMark: root.querySelector(".diagram").getAttribute("data-line-start"),
                sameLook: marked_.replace(/ data-line-start="\\d+"/g, "") === plain,
            };
        }""",
        [LINE_MARK_SOURCE, LOOK_SOURCE],
    )
    # 検証
    assert result == {
        "heading": ["1"],
        "paragraph": ["3"],
        "items": ["6", "7"],
        "rows": ["9", "11", "12"],
        "code": ["15"],
        "diagramMarks": 0,
        "containerMark": None,
        "sameLook": True,
    }


# 選んだ範囲を調べる本文。左の数字は本文の行（1 始まり）
SELECTION_BODY = "\n".join(
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

# 本文の描いた要素と、項目の値（案 B の短所）を置いたパネル（選んだ範囲を調べる文書）。
# removedBefore の行のブロックの前に、行の印を持たない消した部分を差し込む（差分の表示の間）
SELECTION_DOCUMENT_SCRIPT = """([source, removedBefore]) => {
    const panel = document.createElement("div");
    panel.className = "panel";
    const md = document.createElement("div");
    md.className = "md";
    md.append(MindmapPreview.renderMarkdown(source));
    if (removedBefore !== null) {
        const removed = document.createElement("div");
        removed.className = "diff-removed";
        removed.innerHTML = "<p>消した段落</p>";
        md.querySelector(`[data-line-start="${removedBefore}"]`).before(removed);
    }
    const value = document.createElement("div");
    value.setAttribute("data-key", "options[B].cons");
    value.textContent = "数が多いと長い";
    panel.append(md, value);
    document.body.append(panel);
}"""

# パネルの中の文を、全ての文字の並びの中の位置で選び、selectionLocation の結果を返す
SELECT_TEXT_SCRIPT = """([startText, startNth, endText, endNth]) => {
    const container = document.querySelector(".panel");
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
    const nodes = [];
    let all = "";
    while (walker.nextNode()) {
        nodes.push([walker.currentNode, all.length]);
        all += walker.currentNode.data;
    }
    const find = (text, nth) => {
        let at = -1;
        for (let i = 0; i <= nth; i++) at = all.indexOf(text, at + 1);
        return at;
    };
    const point = (offset) => {
        for (let i = nodes.length - 1; i >= 0; i--) {
            const [node, base] = nodes[i];
            if (base <= offset) return [node, offset - base];
        }
    };
    const start = find(startText, startNth);
    const end = find(endText, endNth) + endText.length;
    const range = document.createRange();
    const [startNode, startOffset] = point(start);
    const [endNode, endOffset] = point(end - 1);
    range.setStart(startNode, startOffset);
    range.setEnd(endNode, endOffset + 1);
    return MindmapPreview.selectionLocation(range);
}"""

BODY_SELECTION_CASES = [
    pytest.param(
        "見出しの一", 0, "見出しの一", 0, {"kind": "body", "start": 1, "end": 1}, id="heading"
    ),
    pytest.param("三行目", 0, "三行目", 0, {"kind": "body", "start": 5, "end": 5}, id="paragraph"),
    pytest.param(
        "二つ目の段落",
        0,
        "二つ目の段落",
        0,
        {"kind": "body", "start": 9, "end": 9},
        id="loose_item",
    ),
    pytest.param("番号二", 0, "番号二", 0, {"kind": "body", "start": 13, "end": 13}, id="ordered"),
    pytest.param("入れ子", 0, "入れ子", 0, {"kind": "body", "start": 14, "end": 14}, id="nested"),
    pytest.param("引用二", 0, "引用二", 0, {"kind": "body", "start": 18, "end": 18}, id="quote"),
    pytest.param("セル4", 0, "セル4", 0, {"kind": "body", "start": 23, "end": 23}, id="table_cell"),
    pytest.param("列 B", 0, "列 B", 0, {"kind": "body", "start": 20, "end": 20}, id="table_header"),
    pytest.param("コード二", 0, "コード二", 0, {"kind": "body", "start": 27, "end": 27}, id="code"),
    pytest.param(
        "項目コード二",
        0,
        "項目コード二",
        0,
        {"kind": "body", "start": 38, "end": 38},
        id="item_code",
    ),
    pytest.param("必ず 守る", 0, "必ず 守る", 0, {"kind": "body", "start": 3, "end": 3}, id="bold"),
    pytest.param(
        "規約 と code と * を読む",
        0,
        "規約 と code と * を読む",
        0,
        {"kind": "body", "start": 3, "end": 3},
        id="link_code_escape",
    ),
    pytest.param(
        "詳しくは", 0, "二行目でも", 0, {"kind": "body", "start": 3, "end": 4}, id="soft_break"
    ),
    pytest.param(
        "二行目ハード",
        0,
        "二行目ハード",
        0,
        {"kind": "body", "start": 31, "end": 31},
        id="hard_space",
    ),
    pytest.param(
        "三行目ハード",
        0,
        "三行目ハード",
        0,
        {"kind": "body", "start": 32, "end": 32},
        id="hard_slash",
    ),
    pytest.param(
        "守る", 0, "守る", 0, {"kind": "body", "start": 3, "end": 3}, id="duplicate_first"
    ),
    pytest.param(
        "守る", 1, "守る", 1, {"kind": "body", "start": 4, "end": 4}, id="duplicate_second"
    ),
    pytest.param(
        "三行目",
        0,
        "一つ目の段落",
        0,
        {"kind": "body", "start": 5, "end": 7},
        id="paragraph_to_list",
    ),
    pytest.param(
        "図の前の段落",
        0,
        "図の後の段落",
        0,
        {"kind": "body", "start": 41, "end": 48},
        id="across_diagram",
    ),
    pytest.param(
        "数が多いと長い",
        0,
        "数が多いと長い",
        0,
        {"kind": "value", "key": "options[B].cons", "text": "数が多いと長い"},
        id="value",
    ),
]

# 全ての選び方に、消した部分を差し込む行（差し込まないときは None）を添える。
# 差分の表示の間は、消した部分の後ろの段落（41 行目）を選んでも、今の本文の行で求める
SELECTION_CASES = [
    *(pytest.param(*case.values, None, id=case.id) for case in BODY_SELECTION_CASES),
    pytest.param(
        "図の前の段落",
        0,
        "図の前の段落",
        0,
        {"kind": "body", "start": 41, "end": 41},
        41,
        id="after_removed",
    ),
]


@pytest.mark.parametrize(
    ("start", "start_nth", "end", "end_nth", "expected", "removed_before"), SELECTION_CASES
)
def test_selection_location(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    start: str,
    start_nth: int,
    end: str,
    end_nth: int,
    expected: dict[str, Any],
    removed_before: int | None,
) -> None:
    """本文の行の範囲と値のキーを求める（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    preview_page.evaluate(SELECTION_DOCUMENT_SCRIPT, [SELECTION_BODY, removed_before])
    # 実行
    result = preview_page.evaluate(SELECT_TEXT_SCRIPT, [start, start_nth, end, end_nth])
    # 検証
    assert expected.items() <= result.items()


# 本文・見出しの帯・関係する項目・図・値を置いたパネル（本文と値の外の選択を調べる文書）
OUTSIDE_DOCUMENT_SCRIPT = """() => {
    document.body.innerHTML = `
        <div class="panel">
          <div class="d-head"><span>D-1</span><button type="button">閉じる</button></div>
          <div class="md">
            <p data-line-start="1">本文の段落</p>
            <div class="diff-removed"><p>消した段落</p></div>
            <p data-line-start="3">続きの段落</p>
            <figure class="diagram">
              <div class="mermaid"><svg><text>図の文字</text></svg></div>
              <pre class="dg-raw">flowchart LR</pre>
            </figure>
          </div>
          <button class="idlink" type="button">D-2</button>
          <div data-key="title">値のタイトル</div>
        </div>`;
}"""

# 選び方を指す記述から範囲を作って、selectionLocation の結果を返す
SELECT_OUTSIDE_SCRIPT = """(how) => {
    const range = document.createRange();
    if (how.kind === "collapsed") {
        range.setStart(document.querySelector(how.selector).firstChild, 1);
        range.collapse(true);
    } else if (how.kind === "contents") {
        range.selectNodeContents(document.querySelector(how.selector));
    } else {
        range.setStart(document.querySelector(how.from).firstChild, 0);
        range.setEnd(document.querySelector(how.to).firstChild, 2);
    }
    return MindmapPreview.selectionLocation(range);
}"""


@pytest.mark.parametrize(
    "how",
    [
        pytest.param({"kind": "collapsed", "selector": ".md p"}, id="empty"),
        pytest.param({"kind": "contents", "selector": ".d-head"}, id="header_band"),
        pytest.param({"kind": "contents", "selector": ".idlink"}, id="related_items"),
        pytest.param({"kind": "contents", "selector": ".mermaid svg"}, id="diagram_svg"),
        pytest.param({"kind": "contents", "selector": ".dg-raw"}, id="diagram_raw"),
        pytest.param({"kind": "between", "from": ".md p", "to": "[data-key]"}, id="body_to_value"),
        pytest.param({"kind": "contents", "selector": ".diff-removed p"}, id="removed_part"),
        pytest.param(
            {"kind": "between", "from": ".diff-removed p", "to": '.md p[data-line-start="3"]'},
            id="removed_to_current",
        ),
    ],
)
def test_selection_location_when_outside(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, how: dict[str, str]
) -> None:
    """本文と値の外は null（正常系）。"""
    # 準備
    load_preview_scripts()
    preview_page.evaluate(OUTSIDE_DOCUMENT_SCRIPT)
    # 実行
    result = preview_page.evaluate(SELECT_OUTSIDE_SCRIPT, how)
    # 検証
    assert result is None
