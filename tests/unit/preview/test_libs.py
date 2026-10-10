"""core/libs.ts（描画のライブラリの有無と呼び出し・選んだ範囲から箇所を求める処理）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadLibrary, LoadPreviewScripts, MakeData, MakeItem

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


# 図の記法（フローチャート 2 種）
FLOWCHART_A = "flowchart TD\n  A --> B"
FLOWCHART_B = "flowchart TD\n  C --> D"

# `mermaid.render` に渡った記法を `window.renderedSources` に数える包みと、図の入れ物 1 つを持つ要素を描く `window.drawDiagram` をページに被せる
INSTALL_RENDER_PROBE_SCRIPT = """() => {
    window.renderedSources = [];
    const original = mermaid.render.bind(mermaid);
    mermaid.render = (id, source) => {
        window.renderedSources.push(source);
        return original(id, source);
    };
    window.drawDiagram = async (source) => {
        const root = document.createElement("div");
        const container = document.createElement("div");
        container.setAttribute("data-source", source);
        root.append(container);
        document.body.append(root);
        await MindmapPreview.renderDiagrams(root);
        return container;
    };
}"""


def test_render_diagrams_when_same_source_again(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """直前に描いた同じ記法の図は描き直さず、新しい ID で写す（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("mermaid")
    preview_page.evaluate(INSTALL_RENDER_PROBE_SCRIPT)
    # 実行
    result = preview_page.evaluate(
        """async (source) => {
            const first = await window.drawDiagram(source);
            const second = await window.drawDiagram(source);
            const firstId = first.querySelector("svg").id;
            const secondSvg = second.querySelector("svg");
            return {
                renderCount: window.renderedSources.length,
                firstId,
                secondId: secondSvg.id,
                secondLeaksFirstId: new RegExp(firstId + "(?![0-9])").test(secondSvg.outerHTML),
            };
        }""",
        FLOWCHART_A,
    )
    # 検証
    assert result["renderCount"] == 1
    assert result["secondId"] != result["firstId"]
    assert result["secondLeaksFirstId"] is False


def test_render_diagrams_when_source_not_in_last_call(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """覚えるのは直前の呼び出しの図だけで、その前の図は描き直す（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("mermaid")
    preview_page.evaluate(INSTALL_RENDER_PROBE_SCRIPT)
    # 実行
    render_count = preview_page.evaluate(
        """async ({sourceA, sourceB}) => {
            await window.drawDiagram(sourceA);
            await window.drawDiagram(sourceB);
            await window.drawDiagram(sourceA);
            return window.renderedSources.length;
        }""",
        {"sourceA": FLOWCHART_A, "sourceB": FLOWCHART_B},
    )
    # 検証
    assert render_count == 3


def test_render_diagrams_when_theme_changed(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """テーマが変わったら、同じ記法の図も描き直す（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("mermaid")
    preview_page.evaluate(INSTALL_RENDER_PROBE_SCRIPT)
    # 実行
    render_count = preview_page.evaluate(
        """async (source) => {
            await window.drawDiagram(source);
            document.documentElement.style.setProperty("--surface", "#102030");
            await window.drawDiagram(source);
            return window.renderedSources.length;
        }""",
        FLOWCHART_A,
    )
    # 検証
    assert render_count == 2


def test_render_diagram_svg(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """記法を SVG の要素にして返し、描けない記法は null を返す（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("mermaid")
    broken_source = "これは図の構文ではない ((("
    # 実行
    result = preview_page.evaluate(
        """async ({source, brokenSource}) => {
            const bodyChildrenBefore = document.body.children.length;
            const drawn = await MindmapPreview.renderDiagramSvg(source);
            const broken = await MindmapPreview.renderDiagramSvg(brokenSource);
            return {
                drawnIsSvg: drawn instanceof SVGElement && drawn.localName === "svg",
                broken,
                bodyChildrenBefore,
                bodyChildrenAfter: document.body.children.length,
            };
        }""",
        {"source": FLOWCHART_A, "brokenSource": broken_source},
    )
    # 検証
    assert result["drawnIsSvg"] is True
    assert result["broken"] is None
    assert result["bodyChildrenAfter"] == result["bodyChildrenBefore"]


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


def test_heading_slug(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """空白を - にし、同じ文言に番号を続ける（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    slugs = preview_page.evaluate(
        """() => {
            const seen = new Map();
            return [" 保存先 ", "決め 方", "決め 方", "決め 方"].map(
                (text) => MindmapPreview.headingSlug({text, seen}),
            );
        }"""
    )
    # 検証
    assert slugs == ["保存先", "決め-方", "決め-方-1", "決め-方-2"]


# 見出し「保存先」「決め方」「決め方」と、段落の `#見出し` のリンク 2 つ（1 つは本文に無い見出し）
LINK_HEADINGS_SOURCE = "## 保存先\n\n## 決め方\n\n## 決め方\n\n[決め方](#決め方) と [無い](#無い)\n"

# 見出しに名前と # を付け、押したときに知らせた名前と、押した後の URL のハッシュを調べる
LINK_HEADINGS_SCRIPT = """(source) => {
    const root = MindmapPreview.renderMarkdown(source);
    document.body.append(root);
    const calls = [];
    MindmapPreview.linkHeadings({root, onHeading: (slug) => calls.push(slug)});
    const headings = [...root.querySelectorAll("h1, h2, h3, h4, h5, h6")];
    const paragraphLinks = [...root.querySelectorAll("p a")];
    const result = {
        slugs: headings.map((heading) => heading.getAttribute("data-heading")),
        hashLinkCounts: headings.map((heading) => heading.querySelectorAll("a").length),
        paragraphHrefs: paragraphLinks.map((link) => link.getAttribute("href")),
    };
    // 2 つ目の「決め方」の見出しの #、段落の `[決め方]`、段落の `[無い]` の順に押す
    headings[2].querySelector("a").click();
    paragraphLinks[0].click();
    paragraphLinks[1].click();
    return {...result, calls, hash: location.hash};
}"""


def test_link_headings(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """見出しに名前と # を付け、`#見出し` で知らせる（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    # 実行
    result = preview_page.evaluate(LINK_HEADINGS_SCRIPT, LINK_HEADINGS_SOURCE)
    # 検証
    assert result["slugs"] == ["保存先", "決め方", "決め方-1"]
    assert result["hashLinkCounts"] == [1, 1, 1]
    # marked は日本語の href をパーセントエンコードして描く
    assert result["paragraphHrefs"] == ["#%E6%B1%BA%E3%82%81%E6%96%B9", "#%E7%84%A1%E3%81%84"]
    assert result["calls"] == ["決め方-1", "決め方"]
    assert result["hash"] == ""


# 本文: 見出し「保存先」、用語・ID を並べた段落、コードブロック
LINK_BODY_SOURCE = (
    "## 保存先\n\n保存先と AIM と AI と D-3 と `D-5` と D-99 と XD-3\n\n```\n保存先 D-3\n```\n"
)

# 本文に印とリンクを付け、段落・見出し・コードブロックの中の印とリンク、押したときの知らせを調べる
LINK_BODY_SCRIPT = """({data, source, selfId}) => {
    const index = MindmapPreview.buildIndex(data);
    const root = MindmapPreview.renderMarkdown(source);
    document.body.append(root);
    const calls = [];
    MindmapPreview.linkHeadings({root, onHeading: () => {}});
    MindmapPreview.linkBody({root, index, selfId, onOpen: (id) => calls.push(id)});
    const pairs = (selector) => [...root.querySelectorAll(selector)].map(
        (element) => [element.textContent, element.getAttribute("data-id")],
    );
    const result = {
        terms: pairs("p a.term"),
        refs: pairs("p a.idref"),
        headingMarks: root.querySelectorAll("h1 .term, h1 .idref, h2 .term, h2 .idref").length,
        codeBlockMarks: root.querySelectorAll("pre .term, pre .idref").length,
        allMarks: root.querySelectorAll(".term, .idref").length,
    };
    // 印（G-1）とリンク（D-3）を押す。押したとき既定の動作を止めるか（click が取り消された）も見る
    const press = (element) => !element.dispatchEvent(
        new MouseEvent("click", {bubbles: true, cancelable: true}),
    );
    const termPrevented = result.terms.length > 0 && press(root.querySelector("p a.term"));
    const refPrevented = result.refs.length > 0 && press(root.querySelector("p a.idref"));
    return {...result, calls, termPrevented, refPrevented};
}"""


def test_link_body(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """文中の用語と ID だけに印を付ける（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-3"), make_item("D-5")],
        docs=[make_item("A-1")],
        terms=[
            make_item("G-1", title="保存先"),
            make_item("G-2", title="保存"),
            make_item("G-3", title="AI"),
        ],
    )
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    # 実行
    result = preview_page.evaluate(
        LINK_BODY_SCRIPT, {"data": data, "source": LINK_BODY_SOURCE, "selfId": "A-1"}
    )
    # 検証
    assert result["terms"] == [["保存先", "G-1"], ["AI", "G-3"]]
    assert result["refs"] == [["D-3", "D-3"], ["D-5", "D-5"]]
    assert result["headingMarks"] == 0
    assert result["codeBlockMarks"] == 0
    assert result["calls"] == ["G-1", "D-3"]
    assert (result["termPrevented"], result["refPrevented"]) == (True, True)


def test_link_body_when_self(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """開いている項目自身には付けない（正常系）。"""
    # 準備
    data = make_data(terms=[make_item("G-1", title="保存先")])
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    # 実行
    result = preview_page.evaluate(
        LINK_BODY_SCRIPT, {"data": data, "source": "保存先と G-1\n", "selfId": "G-1"}
    )
    # 検証
    assert result["allMarks"] == 0


# 値の Markdown（強調・実行される属性を持つ画像・スクリプト・箇条書き 2 行）
VALUE_MARKDOWN = '**強調** <img src=x onerror="window.__x=1"> <script>window.__x=2</script>\n\n- 項目 1\n- 項目 2\n'


def test_render_value(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """値の Markdown を描き、スクリプトを動かさない（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    # 実行
    result = preview_page.evaluate(
        """async (source) => {
            const element = MindmapPreview.renderValue(source);
            document.body.append(element);
            // 差し込んだ後に走る属性・スクリプトがあれば、ここで動く
            await new Promise((resolve) => requestAnimationFrame(resolve));
            return {
                isElement: typeof element !== "string",
                className: element.className,
                strong: element.querySelectorAll("strong").length,
                items: element.querySelectorAll("li").length,
                html: element.innerHTML,
                marked: element.querySelectorAll("[data-line-start]").length,
                dirty: window.__x,
            };
        }""",
        VALUE_MARKDOWN,
    )
    # 検証
    assert result["isElement"] is True
    assert "md-value" in result["className"].split()
    assert result["strong"] == 1
    assert result["items"] == 2
    assert "onerror" not in result["html"]
    assert "<script" not in result["html"]
    assert result["marked"] == 0
    assert result["dirty"] is None


@pytest.mark.parametrize(
    "present_library",
    [
        pytest.param("DOMPurify", id="marked_missing"),
        pytest.param("marked", id="dompurify_missing"),
    ],
)
def test_render_value_when_library_missing(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    present_library: str,
) -> None:
    """ライブラリが読めなければ文字のまま返す（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library(present_library)
    # 実行
    result = preview_page.evaluate("(source) => MindmapPreview.renderValue(source)", "**強調**")
    # 検証
    assert result == "**強調**"


# html のコードブロックを 1 つ持つ本文（見出しは 1 行目、前の段落は 3 行目、コードブロックは 5〜7 行目、後の段落は 9 行目）
HTML_CODE_BLOCK_SOURCE = (
    "# 見出し\n\n前の段落\n\n```html\n<p>a</p><script>x()</script>\n```\n\n後の段落\n"
)


def test_render_markdown_when_html_code_block(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """html のコードブロックを枠の入れ物にし、前後は今までどおり描く（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    # 実行
    result = preview_page.evaluate(
        """(source) => {
            const root = MindmapPreview.renderMarkdown(source);
            const marks = (selector) =>
                [...root.querySelectorAll(selector)].map((e) => e.getAttribute("data-line-start"));
            const blocks = root.querySelectorAll(".html-block");
            return {
                blockCount: blocks.length,
                blockSource: blocks.length > 0 ? blocks[0].getAttribute("data-source") : null,
                blockMark: blocks.length > 0 ? blocks[0].getAttribute("data-line-start") : null,
                preCount: root.querySelectorAll("pre").length,
                heading: marks("h1"),
                paragraph: marks("p"),
            };
        }""",
        HTML_CODE_BLOCK_SOURCE,
    )
    # 検証
    assert result["blockCount"] == 1
    assert "<p>a</p><script>x()</script>" in result["blockSource"]
    assert result["blockMark"] == "5"
    assert result["preCount"] == 0
    assert result["heading"] == ["1"]
    assert result["paragraph"] == ["3", "9"]


# 選んだ箇所を求める HTML の本文の原文（左の数字は行。サーバーの行の印を足す前）
HTML_SAMPLE_SOURCE = "\n".join(
    [
        "<!doctype html>",  # 1
        '<html><head><meta charset="utf-8">',  # 2
        "<style>",  # 3
        "  * { margin: 40px !important; }",  # 4
        "  body, p { color: rgb(255, 0, 0) !important; }",  # 5
        "  p > a { color: rgb(0, 255, 0) !important; }",  # 6
        "</style>",  # 7
        '<script>var s = "<p>x</p>"; if (1 < 2) { s += "<p>y</p>"; }</script>',  # 8
        "</head>",  # 9
        "<body>",  # 10
        "<!-- <p>コメントの中の段落</p> -->",  # 11
        '<h1 id="h">見出しの文</h1>',  # 12
        '<p title="a>b">一行目の文',  # 13
        "二行目の文</p>",  # 14
        "<div",  # 15
        '  class="multi">複数行の開きタグの文</div>',  # 16
        "<ul>",  # 17
        "  <li>項目いち",  # 18
        "  <li>項目に<ul><li>入れ子の項目</li></ul>",  # 19
        "</ul>",  # 20
        "<table>",  # 21
        "  <tr><td>表のいち</td><td>表のに</td></tr>",  # 22
        "  <tr><td>表のさん</td><td>表のよん</td></tr>",  # 23
        "</table>",  # 24
        "<p>改行の<br>",  # 25
        "あとの文</p>",  # 26
        "<p>省いた閉じタグの段落",  # 27
        "<p>次の段落 &amp; 文字参照</p>",  # 28
        "<section><div><p>深い入れ子の文</p></div></section>",  # 29
        '<p><a href="#">リンクの文</a></p>',  # 30
        '<button id="click">押す</button>',  # 31
        '<img src="data:,">',  # 32
        '<p id="tail">最後の文</p>',  # 33
        "</body></html>",  # 34
    ]
)

# 上の原文に、サーバーの `mark_lines` と同じ形（開きタグのタグ名の直後に、中身が始まる行の印）を足したもの
HTML_SAMPLE_MARKED = "\n".join(
    [
        "<!doctype html>",
        '<html><head><meta charset="utf-8">',
        "<style>",
        "  * { margin: 40px !important; }",
        "  body, p { color: rgb(255, 0, 0) !important; }",
        "  p > a { color: rgb(0, 255, 0) !important; }",
        "</style>",
        '<script>var s = "<p>x</p>"; if (1 < 2) { s += "<p>y</p>"; }</script>',
        "</head>",
        "<body>",
        "<!-- <p>コメントの中の段落</p> -->",
        '<h1 data-line="12" id="h">見出しの文</h1>',
        '<p data-line="13" title="a>b">一行目の文',
        "二行目の文</p>",
        '<div data-line="16"',
        '  class="multi">複数行の開きタグの文</div>',
        '<ul data-line="17">',
        '  <li data-line="18">項目いち',
        '  <li data-line="19">項目に<ul data-line="19"><li data-line="19">入れ子の項目</li></ul>',
        "</ul>",
        '<table data-line="21">',
        '  <tr data-line="22"><td data-line="22">表のいち</td><td data-line="22">表のに</td></tr>',
        '  <tr data-line="23"><td data-line="23">表のさん</td><td data-line="23">表のよん</td></tr>',
        "</table>",
        '<p data-line="25">改行の<br data-line="25">',
        "あとの文</p>",
        '<p data-line="27">省いた閉じタグの段落',
        '<p data-line="28">次の段落 &amp; 文字参照</p>',
        '<section data-line="29"><div data-line="29"><p data-line="29">深い入れ子の文</p></div></section>',
        '<p data-line="30"><a data-line="30" href="#">リンクの文</a></p>',
        '<button data-line="31" id="click">押す</button>',
        '<img data-line="32" src="data:,">',
        '<p data-line="33" id="tail">最後の文</p>',
        "</body></html>",
    ]
)

# 選び始めの文の頭から、選び終わりの文の終わりまでを選び、箇所の行の範囲を返す
SELECT_HTML_SCRIPT = """([marked, source, startText, endText]) => {
    const doc = new DOMParser().parseFromString(marked, "text/html");
    const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    const startNode = nodes.find((node) => node.data.includes(startText));
    const startOffset = startNode.data.indexOf(startText);
    const endNode = nodes
        .slice(nodes.indexOf(startNode))
        .find((node) => node.data.includes(endText));
    const endOffset =
        endNode.data.indexOf(endText, endNode === startNode ? startOffset : 0) + endText.length;
    const range = doc.createRange();
    range.setStart(startNode, startOffset);
    range.setEnd(endNode, endOffset);
    const location = MindmapPreview.htmlSelectionLocation(range, source);
    return location === null ? null : {kind: location.kind, start: location.start, end: location.end};
}"""

# PoC #215 の 12 ケース: (見本の中の選び方, 期待する行の範囲)
HTML_POC_CASES = [
    pytest.param("見出しの文", "見出しの文", 12, 12, id="heading"),
    pytest.param("一行目の文", "一行目の文", 13, 13, id="paragraph_first_line"),
    pytest.param("二行目の文", "二行目の文", 14, 14, id="paragraph_second_line"),
    pytest.param("一行目の文", "二行目の文", 13, 14, id="paragraph_across_lines"),
    pytest.param("複数行の開きタグの文", "複数行の開きタグの文", 16, 16, id="multi_line_tag"),
    pytest.param("項目いち", "項目いち", 18, 18, id="omitted_end_tag_item"),
    pytest.param("入れ子の項目", "入れ子の項目", 19, 19, id="nested_item"),
    pytest.param("項目いち", "入れ子の項目", 18, 19, id="across_items"),
    pytest.param("表のさん", "表のよん", 23, 23, id="table_row"),
    pytest.param("あとの文", "あとの文", 26, 26, id="after_line_break"),
    pytest.param("見出しの文", "二行目の文", 12, 14, id="across_blocks"),
    pytest.param("最後の文", "最後の文", 33, 33, id="after_comment_and_script"),
]


@pytest.mark.parametrize(("start_text", "end_text", "start", "end"), HTML_POC_CASES)
def test_html_selection_location(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    start_text: str,
    end_text: str,
    start: int,
    end: int,
) -> None:
    """選んだ端を元の HTML の行にする（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        SELECT_HTML_SCRIPT, [HTML_SAMPLE_MARKED, HTML_SAMPLE_SOURCE, start_text, end_text]
    )
    # 検証
    assert result == {"kind": "body", "start": start, "end": end}


@pytest.mark.parametrize(
    ("source", "marked", "start_text", "end_text", "start", "end"),
    [
        pytest.param(
            '<p><span><span\nclass="x">中の文</span></span>\n三行目の文</p>',
            '<p data-line="1"><span data-line="1"><span data-line="2"\n'
            'class="x">中の文</span></span>\n三行目の文</p>',
            "三行目の文",
            "三行目の文",
            3,
            3,
            id="after_nested_multi_line_tag",
        ),
        pytest.param(
            "<p>a<br>別の文</p>",
            '<p data-line="1">a<br data-line="1">別の文</p>',
            "別の文",
            "別の文",
            1,
            1,
            id="after_br",
        ),
        pytest.param(
            "<pre>\nコードの文\n</pre>",
            '<pre data-line="1">\nコードの文\n</pre>',
            "コードの文",
            "コードの文",
            2,
            2,
            id="after_pre_line_break",
        ),
        pytest.param(
            "<div>前の文\n<!-- 一行目\n二行目 -->\n後の文</div>",
            '<div data-line="1">前の文\n<!-- 一行目\n二行目 -->\n後の文</div>',
            "後の文",
            "後の文",
            4,
            4,
            id="after_multi_line_comment",
        ),
    ],
)
def test_html_selection_location_when_line_shifts(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    source: str,
    marked: str,
    start_text: str,
    end_text: str,
    start: int,
    end: int,
) -> None:
    """改行の数え方が分かれる選び方でも、元の HTML の行にする（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(SELECT_HTML_SCRIPT, [marked, source, start_text, end_text])
    # 検証
    assert result == {"kind": "body", "start": start, "end": end}


# 印を持つ要素より前の文を持つ HTML の本文の原文と、行の印を足したもの
HTML_OUTSIDE_SOURCE = "文頭の文\n<p>段落</p>\n<p>次の段落</p>"
HTML_OUTSIDE_MARKED = '文頭の文\n<p data-line="2">段落</p>\n<p data-line="3">次の段落</p>'

# 選び方を指す記述から範囲を作って、htmlSelectionLocation の結果を返す
SELECT_HTML_OUTSIDE_SCRIPT = """([marked, source, how]) => {
    const doc = new DOMParser().parseFromString(marked, "text/html");
    const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    const range = doc.createRange();
    if (how.kind === "collapsed") {
        range.setStart(doc.querySelector("p").firstChild, 1);
        range.collapse(true);
    } else if (how.kind === "whitespace") {
        range.selectNodeContents(nodes.find((node) => node.data.length > 0 && node.data.trim() === ""));
    } else {
        range.selectNodeContents(nodes.find((node) => node.data.includes(how.text)));
    }
    return MindmapPreview.htmlSelectionLocation(range, source);
}"""


@pytest.mark.parametrize(
    "how",
    [
        pytest.param({"kind": "collapsed"}, id="empty"),
        pytest.param({"kind": "whitespace"}, id="blank_only"),
        pytest.param({"kind": "text", "text": "文頭の文"}, id="before_first_mark"),
    ],
)
def test_html_selection_location_when_outside(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, how: dict[str, str]
) -> None:
    """印の無い範囲と空の選択は null（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        SELECT_HTML_OUTSIDE_SCRIPT, [HTML_OUTSIDE_MARKED, HTML_OUTSIDE_SOURCE, how]
    )
    # 検証
    assert result is None
