"""screens/detail.ts（詳細パネル）の単体テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadLibrary, LoadPreviewScripts, MakeData, MakeItem

# 変更履歴の 1 回分の日時
ENTRY_AT = "2026-10-03T09:00:00+00:00"

# 今の本文（1 行目の段落・空行・3 行目の段落）と、前の版の本文（1 行目の後ろに 2 つの段落があった）
NOW_BODY = "1 行目の段落\n\n今の 3 行目の段落\n"

# 今の 3 行目の前に、前の版の 2 つの段落（と空行）を差し込む差分
REMOVED_PARAGRAPHS_DIFF = [
    {"line": 3, "now": [], "before": ["消した段落 A", "", "消した段落 B", ""]},
]

# 差分の表示で選んだ時点（今まで。この項目は変わった項目）
DIFF_POINT = {
    "sel": "pending",
    "name": "まだまとめていない変更",
    "sub": "AI がまだ区切っていない書き換え",
    "fromSeq": 0,
    "untilSeq": None,
}

# 詳細パネルを差分つきで開き、示した箇所と、消した部分の段落を調べる
OPEN_DIFF_PANEL_SCRIPT = """async ({data, point, highlight}) => {
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const panel = MindmapPreview.detailPanel({
        id: "D-1",
        index,
        full: false,
        on: {open: noop, close: noop, full: noop, back: noop, forward: noop, diagram: noop},
        comment: null,
        highlight,
        diff: {...point, added: new Set(), changed: new Set(["D-1"])},
    });
    document.body.append(panel);
    // 示す箇所へのスクロールと印は、文書に入った後の描き直しで付くことがある
    await new Promise((resolve) => requestAnimationFrame(resolve));
    const hits = [...panel.querySelectorAll(".loc-hit")].map((element) => ({
        line: element.getAttribute("data-line-start"),
        text: (element.textContent ?? "").trim(),
    }));
    const removed = [...panel.querySelectorAll(".md p")]
        .filter((paragraph) => (paragraph.textContent ?? "").includes("消した段落"))
        .map((paragraph) => ({
            text: (paragraph.textContent ?? "").trim(),
            underLineMark: paragraph.closest("[data-line-start]") !== null,
        }));
    return {hits, removed};
}"""


def test_detail_panel_when_diff_highlight(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """差分の表示の間も、消した部分の後ろの箇所を今の行のブロックで示す（正常系）。"""
    # 準備
    entry = {
        "seq": 1,
        "at": ENTRY_AT,
        "before": {},
        "body_diff": REMOVED_PARAGRAPHS_DIFF,
    }
    data = make_data(
        decisions=[make_item("D-1", body="D-1.md", history=[entry])],
        bodies={"D-1.md": NOW_BODY},
    )
    highlight = {"kind": "body", "start": 3, "end": 3, "text": "今の 3 行目の段落"}
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        OPEN_DIFF_PANEL_SCRIPT,
        {"data": data, "point": DIFF_POINT, "highlight": highlight},
    )
    # 検証
    assert result["hits"] == [{"line": "3", "text": "今の 3 行目の段落"}]
    first, second = result["removed"]
    assert "消した段落 A" in first["text"]
    assert "消した段落 B" in second["text"]
    assert (first["underLineMark"], second["underLineMark"]) == (False, False)


# 古いまとまり V-1 の直後の本文（3 行目の段落）と、V-2 で頭に段落を足して行がずれた今の本文
OLD_SET_NOW_BODY = "頭に足した段落\n\n1 行目の段落\n\nV-1 の 3 行目の段落\n"

# V-2 の後に頭へ段落を足した回（seq 2）と、V-1 の 3 行目を書き換えた回（seq 1）
OLD_SET_HISTORY = [
    {
        "seq": 2,
        "at": ENTRY_AT,
        "before": {},
        "body_diff": [{"line": 1, "now": ["頭に足した段落", ""], "before": []}],
    },
    {
        "seq": 1,
        "at": ENTRY_AT,
        "before": {},
        "body_diff": [
            {
                "line": 3,
                "now": ["V-1 の 3 行目の段落"],
                "before": ["元の 3 行目の段落"],
            },
        ],
    },
]

# 古いまとまり V-1 を選んだ時点（その後の V-2 も同じ項目を直している）
OLD_SET_POINT = {
    "sel": "V-1",
    "name": "最初の書き換え",
    "sub": "10/03 18:00",
    "fromSeq": 0,
    "untilSeq": 1,
}

# 詳細パネルを開き、本文の行の印と示した箇所を調べる
OPEN_OLD_SET_PANEL_SCRIPT = """async ({data, point, highlight}) => {
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const panel = MindmapPreview.detailPanel({
        id: "D-1",
        index,
        full: false,
        on: {open: noop, close: noop, full: noop, back: noop, forward: noop, diagram: noop},
        comment: null,
        highlight,
        diff: {...point, added: new Set(), changed: new Set(["D-1"])},
    });
    document.body.append(panel);
    await new Promise((resolve) => requestAnimationFrame(resolve));
    return {
        marked: panel.querySelectorAll(".md [data-line-start]").length,
        hits: panel.querySelectorAll(".loc-hit").length,
        text: panel.querySelector(".md:not(.md-value)")?.textContent ?? "",
    };
}"""


def test_detail_panel_when_old_set_after_body_edit(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """古いまとまりを選び、その後に本文を直した項目では、本文の行の印を外す（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1", body="D-1.md", history=OLD_SET_HISTORY)],
        bodies={"D-1.md": OLD_SET_NOW_BODY},
    )
    highlight = {"kind": "body", "start": 5, "end": 5, "text": "V-1 の 3 行目の段落"}
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        OPEN_OLD_SET_PANEL_SCRIPT,
        {"data": data, "point": OLD_SET_POINT, "highlight": highlight},
    )
    # 検証
    assert "V-1 の 3 行目の段落" in result["text"]
    assert result["marked"] == 0
    assert result["hits"] == 0


# 選んだ時点の後に、答えと編集した人（利用者 → AI）が変わった回
EDITOR_ENTRY = {
    "seq": 1,
    "at": ENTRY_AT,
    "before": {"answer": None, "updated_by": "user"},
}

# 詳細パネルを差分つきで開き、差分の印の数と、編集した人の値が出ているかを調べる
OPEN_EDITOR_PANEL_SCRIPT = """async ({data, point}) => {
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const panel = MindmapPreview.detailPanel({
        id: "D-1",
        index,
        full: false,
        on: {open: noop, close: noop, full: noop, back: noop, forward: noop, diagram: noop},
        comment: null,
        highlight: null,
        diff: {...point, added: new Set(), changed: new Set(["D-1"])},
    });
    document.body.append(panel);
    await new Promise((resolve) => requestAnimationFrame(resolve));
    return {
        keyMarks: panel.querySelectorAll(".df-key").length,
        valueMarks: panel.querySelectorAll(".df-kv").length,
        answerMarked: panel.querySelector(".d-answer.df-key .df-now")?.textContent ?? "",
        editorShown: (panel.textContent ?? "").includes("user") || (panel.textContent ?? "").includes("ai"),
    };
}"""


def test_detail_panel_when_diff_editor_only(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """編集した人だけが変わったキーは差分に出さない（正常系）。"""
    # 準備
    data = make_data(
        decisions=[
            make_item(
                "D-1",
                answer="新しい答え",
                updated_by="ai",
                history=[EDITOR_ENTRY],
                seq=1,
            )
        ],
    )
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        OPEN_EDITOR_PANEL_SCRIPT, {"data": data, "point": DIFF_POINT}
    )
    # 検証
    assert result["keyMarks"] == 1
    assert result["valueMarks"] == 1
    assert "新しい答え" in result["answerMarked"]
    assert result["editorShown"] is False


# 今の本文（5 行目に図のノードの文字を持つフローチャート）
DIAGRAM_NOW_BODY = "# 図\n\n```mermaid\nflowchart TD\n  A[今の文字] --> B\n```\n"

# 選んだ時点の後に、図のノードの文字を 1 つ変えた回
DIAGRAM_ENTRY = {
    "seq": 1,
    "at": ENTRY_AT,
    "before": {},
    "body_diff": [
        {"line": 5, "now": ["  A[今の文字] --> B"], "before": ["  A[前の文字] --> B"]},
    ],
}

# `mermaid.render` に渡った記法を `window.renderedSources` に数える包みを被せる
INSTALL_RENDER_COUNTER_SCRIPT = """() => {
    window.renderedSources = [];
    const original = mermaid.render.bind(mermaid);
    mermaid.render = (id, source) => {
        window.renderedSources.push(source);
        return original(id, source);
    };
}"""

# 詳細パネルを開いて文書に入れる（差分があれば差分つきで開く）
OPEN_DIAGRAM_PANEL_SCRIPT = """({data, point}) => {
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    window.openedPanel?.remove();
    window.openedPanel = MindmapPreview.detailPanel({
        id: "D-1",
        index,
        full: false,
        on: {open: noop, close: noop, full: noop, back: noop, forward: noop, diagram: noop},
        comment: null,
        highlight: null,
        diff: point === null ? null : {...point, added: new Set(), changed: new Set(["D-1"])},
    });
    document.body.append(window.openedPanel);
}"""


def test_detail_panel_when_diff_reuses_current_diagram(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """開いたまま時点を選ぶと、flowchart の図は今の版を描き直さず、前の版も描かずに差分の印を付ける（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1", body="D-1.md", history=[DIAGRAM_ENTRY], seq=1)],
        bodies={"D-1.md": DIAGRAM_NOW_BODY},
    )
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    load_library("jsdiff")
    load_library("mermaid")
    preview_page.evaluate(INSTALL_RENDER_COUNTER_SCRIPT)
    # 差分なしで開いて、今の版の図を描き終える
    preview_page.evaluate(OPEN_DIAGRAM_PANEL_SCRIPT, {"data": data, "point": None})
    preview_page.wait_for_function(
        "() => document.querySelector('.mermaid svg') !== null"
    )
    preview_page.evaluate("() => { window.renderedSources.length = 0; }")
    # 実行
    preview_page.evaluate(
        OPEN_DIAGRAM_PANEL_SCRIPT, {"data": data, "point": DIFF_POINT}
    )
    preview_page.wait_for_function(
        "() => document.querySelector('.mermaid svg .df-n-chg') !== null"
    )
    rendered_sources = preview_page.evaluate("() => window.renderedSources")
    # 検証
    assert rendered_sources == []


# 今の本文（5 行目にメッセージの文字を持つ sequenceDiagram）と、前の版の図の記法
SEQUENCE_NOW_BODY = "# 図\n\n```mermaid\nsequenceDiagram\n  A->>B: 今の依頼\n```\n"
SEQUENCE_BEFORE_SOURCE = "sequenceDiagram\n  A->>B: 前の依頼\n"

# 選んだ時点の後に、メッセージの文字を 1 つ変えた回
SEQUENCE_ENTRY = {
    "seq": 1,
    "at": ENTRY_AT,
    "before": {},
    "body_diff": [
        {"line": 5, "now": ["  A->>B: 今の依頼"], "before": ["  A->>B: 前の依頼"]},
    ],
}


def test_detail_panel_when_diff_renders_before_sequence(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """flowchart でない図は、前の版の図だけを描いて突き合わせる（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1", body="D-1.md", history=[SEQUENCE_ENTRY], seq=1)],
        bodies={"D-1.md": SEQUENCE_NOW_BODY},
    )
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    load_library("jsdiff")
    load_library("mermaid")
    preview_page.evaluate(INSTALL_RENDER_COUNTER_SCRIPT)
    # 差分なしで開いて、今の版の図を描き終える
    preview_page.evaluate(OPEN_DIAGRAM_PANEL_SCRIPT, {"data": data, "point": None})
    preview_page.wait_for_function(
        "() => document.querySelector('.mermaid svg') !== null"
    )
    preview_page.evaluate("() => { window.renderedSources.length = 0; }")
    # 実行
    preview_page.evaluate(
        OPEN_DIAGRAM_PANEL_SCRIPT, {"data": data, "point": DIFF_POINT}
    )
    preview_page.wait_for_function(
        "() => document.querySelector('.mermaid svg .df-t-chg') !== null"
    )
    rendered_sources = preview_page.evaluate("() => window.renderedSources")
    # 検証
    assert rendered_sources == [SEQUENCE_BEFORE_SOURCE]


# 見出し「決め方」を 2 つ持つ本文（2 つの見出しの間に、本文の領域を超える段落を置く）
HEADING_BODY = (
    "## 決め方\n\n"
    + "\n\n".join(f"1 つ目の決め方の段落 {number}" for number in range(1, 13))
    + "\n\n## 決め方\n\n2 つ目の決め方の段落\n"
)

# 本文のスクロール領域を 200px に抑えて詳細パネルを開き、2 つ目の「決め方」が領域に入ったかと、見出しを外させる知らせを調べる
OPEN_HEADING_PANEL_SCRIPT = """async ({data, heading}) => {
    // 単体テストでは雛形の CSS を読まないので、本文のスクロール領域だけ作る
    const style = document.createElement("style");
    style.textContent = ".panel-body { height: 200px; overflow: auto; }";
    document.head.append(style);
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const headingCalls = [];
    const panel = MindmapPreview.detailPanel({
        id: "A-1",
        index,
        full: false,
        on: {
            open: noop,
            close: noop,
            full: noop,
            back: noop,
            forward: noop,
            diagram: noop,
            heading: (slug) => headingCalls.push(slug),
        },
        comment: null,
        heading,
    });
    document.body.append(panel);
    // 見出しへのスクロールは、文書に入った後の描き直しで付くことがある
    for (let frame = 0; frame < 2; frame += 1) {
        await new Promise((resolve) => requestAnimationFrame(resolve));
    }
    const body = panel.querySelector(".panel-body");
    const area = body.getBoundingClientRect();
    const target = panel.querySelector('[data-heading="決め方-1"]');
    const rect = target === null ? null : target.getBoundingClientRect();
    return {
        scrolled: body.scrollTop > 0,
        inView: rect !== null && rect.top >= area.top && rect.bottom <= area.bottom,
        nullCalls: headingCalls.filter((slug) => slug === null).length,
    };
}"""


@pytest.mark.parametrize(
    ("heading", "expected"),
    [
        pytest.param(
            "決め方-1",
            {"scrolled": True, "inView": True, "nullCalls": 0},
            id="heading_in_body",
        ),
        pytest.param(
            "無い",
            {"scrolled": False, "inView": False, "nullCalls": 1},
            id="heading_not_in_body",
        ),
    ],
)
def test_detail_panel_when_heading(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    make_data: MakeData,
    make_item: MakeItem,
    heading: str,
    expected: dict[str, object],
) -> None:
    """指した見出しを画面に入れて開く（正常系）。"""
    # 準備
    data = make_data(docs=[make_item("A-1")], bodies={"A-1.md": HEADING_BODY})
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    # 実行
    result = preview_page.evaluate(
        OPEN_HEADING_PANEL_SCRIPT, {"data": data, "heading": heading}
    )
    # 検証
    assert result == expected


# 詳細パネルを開いて文書に差し込む関数（描いた後の描き直しを 1 フレーム待つ）
OPEN_PANEL_FUNCTION = """const openPanel = async (data, id) => {
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const panel = MindmapPreview.detailPanel({
        id,
        index,
        full: false,
        on: {open: noop, close: noop, full: noop, back: noop, forward: noop, diagram: noop},
        comment: null,
        highlight: null,
        diff: null,
    });
    document.body.append(panel);
    await new Promise((resolve) => requestAnimationFrame(resolve));
    return panel;
};"""

# 検討事項の中身の並びと、案の採用・不採用の表示を調べる
DECISION_ORDER_SCRIPT = (
    OPEN_PANEL_FUNCTION
    + """
async ({data}) => {
    const panel = await openPanel(data, "D-1");
    const detail = panel.querySelector(".detail");
    // 中身の直下の子のうち、印を含むものの位置
    const position = (element) => {
        let node = element;
        while (node !== null && node.parentElement !== detail) node = node.parentElement;
        return node === null ? -1 : [...detail.children].indexOf(node);
    };
    const heading = [...panel.querySelectorAll("h3")].find(
        (element) => (element.textContent ?? "").trim() === "採用した案と理由",
    );
    const results = [...panel.querySelectorAll(".opt")].map((option) => ({
        key: option.querySelector(".key")?.textContent ?? "",
        result: (option.querySelector(".res")?.textContent ?? "").trim(),
    }));
    return {
        positions: [
            position(panel.querySelector('[data-key="lead"]')),
            position(panel.querySelector(".opt")),
            position(heading ?? null),
            position(panel.querySelector(".md:not(.md-value)")),
        ],
        decided: heading === undefined
            ? []
            : [...heading.parentElement.querySelectorAll("[data-key]")].map((element) => element.getAttribute("data-key")),
        results,
    };
}"""
)


def test_detail_panel_when_decision_order(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """検討事項を 背景 → 案 → 採用した案と理由 → 本文 の順に描く（正常系）。"""
    # 準備
    decision = make_item(
        "D-1",
        status="決定済み",
        lead="何を決めるか",
        answer="月ごとに分ける",
        reason="探しやすい",
        body="D-1.md",
        options=[
            {"key": "A", "content": "案 A", "adopted": True},
            {"key": "B", "content": "案 B", "adopted": False},
            {"key": "C", "content": "案 C"},
        ],
    )
    data = make_data(decisions=[decision], bodies={"D-1.md": "本文の段落\n"})
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    # 実行
    result = preview_page.evaluate(DECISION_ORDER_SCRIPT, {"data": data})
    # 検証
    positions = result["positions"]
    assert -1 not in positions
    assert positions == sorted(set(positions))
    assert result["decided"] == ["answer", "reason"]
    assert result["results"] == [
        {"key": "A", "result": "採用"},
        {"key": "B", "result": "不採用"},
        {"key": "C", "result": ""},
    ]


# 推奨の印を持つ案の記号と、採用した案と理由の節の有無、案ごとの結果の表示を調べる
RECOMMENDED_SCRIPT = (
    OPEN_PANEL_FUNCTION
    + """
async ({data, id}) => {
    const panel = await openPanel(data, id);
    const headings = [...panel.querySelectorAll("h3")].map((element) => (element.textContent ?? "").trim());
    const options = [...panel.querySelectorAll(".opt")];
    return {
        recommended: options
            .filter((option) => (option.querySelector(".o-head")?.textContent ?? "").includes("推奨"))
            .map((option) => option.querySelector(".key")?.textContent ?? ""),
        stars: panel.querySelectorAll(".opt .o-head svg").length,
        hasDecidedSection: headings.includes("採用した案と理由"),
        results: options.map((option) => (option.querySelector(".res")?.textContent ?? "").trim()),
    };
}"""
)


@pytest.mark.parametrize(
    ("item_id", "status", "options", "expected"),
    [
        pytest.param(
            "D-1",
            "未決定",
            [
                {"key": "A", "content": "案 A"},
                {"key": "B", "content": "案 B", "recommended": True},
            ],
            {
                "recommended": ["B"],
                "stars": 1,
                "hasDecidedSection": False,
                "results": ["", ""],
            },
            id="undecided_with_recommended",
        ),
        pytest.param(
            "D-2",
            "決定済み",
            [
                {"key": "A", "content": "案 A", "adopted": True},
                {"key": "B", "content": "案 B", "recommended": True},
            ],
            {
                "recommended": [],
                "stars": 0,
                "hasDecidedSection": False,
                "results": ["採用", ""],
            },
            id="decided_hides_recommended",
        ),
        pytest.param(
            "D-3",
            "未決定",
            [{"key": "A", "content": "案 A"}, {"key": "B", "content": "案 B"}],
            {
                "recommended": [],
                "stars": 0,
                "hasDecidedSection": False,
                "results": ["", ""],
            },
            id="undecided_without_recommended",
        ),
    ],
)
def test_detail_panel_when_recommended(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    make_data: MakeData,
    make_item: MakeItem,
    item_id: str,
    status: str,
    options: list[dict[str, object]],
    expected: dict[str, object],
) -> None:
    """採用した案が無いときだけ、推奨の案に推奨のバッジを出す（正常系）。"""
    # 準備
    data = make_data(decisions=[make_item(item_id, status=status, options=options)])
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    # 実行
    result = preview_page.evaluate(RECOMMENDED_SCRIPT, {"data": data, "id": item_id})
    # 検証
    assert result == expected


# 値の要素（data-key がキーのパス）の中の強調と、Markdown の記号の残りを調べる
MARKDOWN_VALUES_SCRIPT = (
    OPEN_PANEL_FUNCTION
    + """
async ({data, id, keys}) => {
    const panel = await openPanel(data, id);
    return {
        values: keys.map((key) => {
            const element = panel.querySelector(`[data-key="${key}"]`);
            return {
                key,
                found: element !== null,
                strong: element === null ? 0 : element.querySelectorAll("strong").length,
                raw: element === null ? false : (element.textContent ?? "").includes("**"),
            };
        }),
        dirty: window.__x,
    };
}"""
)


@pytest.mark.parametrize(
    ("item_id", "kinds", "keys"),
    [
        pytest.param(
            "D-1",
            {
                "decisions": [
                    {
                        "id": "D-1",
                        "status": "決定済み",
                        "lead": "**強調**",
                        "answer": "**強調**",
                        "reason": "**強調**",
                        "options": [
                            {
                                "key": "A",
                                "content": "案 A",
                                "pros": "**強調**",
                                "adopted": True,
                            }
                        ],
                    }
                ]
            },
            ["lead", "answer", "reason", "options[A].pros"],
            id="decision",
        ),
        pytest.param(
            "T-1",
            {"tasks": [{"id": "T-1", "reason": "**強調**"}]},
            ["reason"],
            id="task",
        ),
        pytest.param(
            "R-1",
            {
                "research": [
                    {"id": "R-1", "question": "**強調**", "conclusion": "**強調**"}
                ]
            },
            ["question", "conclusion"],
            id="research",
        ),
        pytest.param(
            "G-1",
            {"terms": [{"id": "G-1", "meaning": "**強調**"}]},
            ["meaning"],
            id="term",
        ),
        pytest.param(
            "N-1",
            {
                "notes": [
                    {
                        "id": "N-1",
                        "content": '**強調** <img src=x onerror="window.__x=1">',
                    }
                ]
            },
            ["content"],
            id="note",
        ),
    ],
)
def test_detail_panel_when_markdown_values(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    make_data: MakeData,
    make_item: MakeItem,
    item_id: str,
    kinds: dict[str, list[dict[str, object]]],
    keys: list[str],
) -> None:
    """文字列の値を Markdown で描き、キーのパスを保つ（正常系）。"""
    # 準備
    data = make_data(
        **{
            kind: [
                make_item(item["id"], **{k: v for k, v in item.items() if k != "id"})
                for item in items
            ]
            for kind, items in kinds.items()
        }
    )
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    # 実行
    result = preview_page.evaluate(
        MARKDOWN_VALUES_SCRIPT, {"data": data, "id": item_id, "keys": keys}
    )
    # 検証
    assert result["values"] == [
        {"key": key, "found": True, "strong": 1, "raw": False} for key in keys
    ]
    assert result["dirty"] is None


# 案の値（data-key がキーのパス）の文字と強調の数、値の要素が無いかを調べる
OPTION_LIST_VALUES_SCRIPT = (
    OPEN_PANEL_FUNCTION
    + """
async ({data, id}) => {
    const panel = await openPanel(data, id);
    const pros = panel.querySelector('[data-key="options[A].pros"]');
    return {
        prosText: pros === null ? null : (pros.textContent ?? "").trim(),
        prosStrong: pros === null ? 0 : pros.querySelectorAll("strong").length,
        consFound: panel.querySelector('[data-key="options[A].cons"]') !== null,
    };
}"""
)


def test_detail_panel_when_option_list_values(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """案のメリット・デメリットが文字列の配列でも、つないで描く（正常系）。"""
    # 準備
    data = make_data(
        decisions=[
            make_item(
                "D-1",
                status="未決定",
                options=[
                    {
                        "key": "A",
                        "content": "案 A",
                        "pros": ["速い", "**安い**"],
                        "cons": [],
                    }
                ],
            )
        ]
    )
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    # 実行
    result = preview_page.evaluate(
        OPTION_LIST_VALUES_SCRIPT, {"data": data, "id": "D-1"}
    )
    # 検証
    assert result == {"prosText": "速い、安い", "prosStrong": 1, "consFound": False}


# レビュー中のコメントの溜めた日時
REVIEW_CREATED = "2026-10-05T03:00:00+00:00"


def _review_item(item_id: str, body: str) -> dict[str, object]:
    """D-1 へのレビュー中のコメントを返す。"""
    return {
        "id": item_id,
        "target": "D-1",
        "target_title": "問い",
        "loc": None,
        "body": body,
        "created": REVIEW_CREATED,
    }


# 詳細パネルに渡す、下端の入力欄とレビュー中のコメントと行の操作の引数を作り、文書に置く関数
OPEN_REVIEW_PANEL_FUNCTION = """const openReviewPanel = async ({data, reviews, removed, editing, full, calls}) => {
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const count = (name) => () => { calls[name] += 1; };
    const panel = MindmapPreview.detailPanel({
        id: "D-1",
        index,
        full,
        on: {
            open: noop, close: noop, full: count("full"), back: noop, forward: noop, diagram: noop,
            heading: noop,
        },
        comment: {
            form: {
                target: "D-1",
                on: {input: noop, save: noop, unquote: noop, copy: noop, focus: noop, blur: noop},
            },
            reviews,
            edit: {
                removed,
                editing,
                editError: null,
                editBody: null,
                on: {
                    edit: noop, saveEdit: noop, cancelEdit: count("cancelEdit"), remove: noop,
                    restore: noop,
                },
            },
        },
        highlight: null,
        diff: null,
    });
    document.body.append(panel);
    if (full) panel.showModal();
    await new Promise((resolve) => requestAnimationFrame(resolve));
    return panel;
};"""

# レビュー中のコメントの節の行を、順に調べる
REVIEW_ROWS_SCRIPT = (
    OPEN_REVIEW_PANEL_FUNCTION
    + """
async ({data, reviews, removed, editing}) => {
    const calls = {full: 0, cancelEdit: 0};
    const panel = await openReviewPanel({data, reviews, removed, editing, full: false, calls});
    const section = panel.querySelector(".d-review");
    const labelOf = (button) => button.getAttribute("aria-label") ?? button.textContent.trim();
    return {
        count: section.querySelector("h3 .count").textContent.trim(),
        rows: [...section.querySelectorAll("li")].map((row) => ({
            buttons: [...row.querySelectorAll("button")].map(labelOf),
            status: [...row.querySelectorAll('[role="status"]')].map((status) => status.textContent.trim()),
            hasField: row.querySelector("textarea") !== null,
        })),
        focuses: [...section.querySelectorAll("[data-focus]")].map((element) => element.getAttribute("data-focus")),
    };
}"""
)


def test_detail_panel_when_review_rows(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """レビュー中のコメントの行に修正・削除を置き、書き換えている行と消した行を元の場所に描く（正常系）。"""
    # 準備
    data = make_data(decisions=[make_item("D-1", status="未決定")])
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    # 実行
    result = preview_page.evaluate(
        REVIEW_ROWS_SCRIPT,
        {
            "data": data,
            "reviews": [
                _review_item("C-1", "案 A にする"),
                _review_item("C-3", "案 B も見たい"),
            ],
            "removed": [_review_item("C-2", "消したコメント")],
            "editing": "C-3",
        },
    )
    # 検証
    assert result["count"] == "2"
    assert result["rows"] == [
        {
            "buttons": ["D-1 へのコメントを修正", "D-1 へのコメントを削除"],
            "status": [],
            "hasField": False,
        },
        {
            "buttons": ["元に戻す"],
            "status": ["コメントを削除しました。"],
            "hasField": False,
        },
        {"buttons": ["キャンセル", "修正"], "status": [], "hasField": True},
    ]
    assert result["focuses"] == [
        "detail-edit-open:C-1",
        "detail-remove:C-1",
        "detail-restore:C-2",
        "detail-edit:C-3",
    ]


# 全画面で書き換えの入力欄にフォーカスして Esc を押す前の用意（押した後の結果は別に読む）
OPEN_FULL_EDIT_SCRIPT = (
    OPEN_REVIEW_PANEL_FUNCTION
    + """
async ({data, reviews}) => {
    window.__calls = {full: 0, cancelEdit: 0};
    window.__panel = await openReviewPanel({
        data, reviews, removed: [], editing: "C-1", full: true, calls: window.__calls,
    });
    const field = window.__panel.querySelector(".d-review textarea");
    if (field !== null) field.focus();
    return field !== null;
}"""
)

# Esc を押した後の、呼ばれた回数と全画面の開き具合
READ_FULL_EDIT_SCRIPT = """() => ({
    calls: window.__calls,
    open: window.__panel.open,
})"""


def test_detail_panel_when_review_escape_in_full(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """全画面で書き換えの入力欄の Esc は、書き換えだけを捨てて全画面を閉じない（正常系）。"""
    # 準備
    data = make_data(decisions=[make_item("D-1", status="未決定")])
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    has_field = preview_page.evaluate(
        OPEN_FULL_EDIT_SCRIPT,
        {"data": data, "reviews": [_review_item("C-1", "案 A にする")]},
    )
    # 実行
    preview_page.keyboard.press("Escape")
    # 検証
    assert has_field is True
    assert preview_page.evaluate(READ_FULL_EDIT_SCRIPT) == {
        "calls": {"full": 0, "cancelEdit": 1},
        "open": True,
    }
