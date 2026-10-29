"""screens/detail.ts（詳細パネル）の単体テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from .fixture_types import (
    LoadLibrary,
    LoadMdmark,
    LoadPreviewScripts,
    LoadPreviewStyles,
    MakeData,
    MakeItem,
    PutMdmarkCss,
)

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
    load_mdmark: LoadMdmark,
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
    load_mdmark()
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
    load_mdmark: LoadMdmark,
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
    load_mdmark()
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
    load_mdmark: LoadMdmark,
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
    load_mdmark()
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
    load_mdmark: LoadMdmark,
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
    load_mdmark()
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
    load_mdmark: LoadMdmark,
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
    load_mdmark()
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

# 末尾の段落を書き換えた変えた回（差分の表示で本文を変えた A-1 にする）
HEADING_BODY_ENTRY = {
    "seq": 1,
    "at": ENTRY_AT,
    "before": {},
    "body_diff": [
        {
            "line": len(HEADING_BODY.splitlines()),
            "now": ["2 つ目の決め方の段落"],
            "before": ["前の 2 つ目の決め方の段落"],
        }
    ],
}

# 本文のスクロール領域を 200px に抑えて詳細パネルを開き、2 つ目の「決め方」が領域に入ったかと、見出しを外させる知らせを調べる
OPEN_HEADING_PANEL_SCRIPT = """async ({data, heading, point, bodyLayout, width}) => {
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
            layout: noop,
        },
        comment: null,
        heading,
        diff: point === null ? null : {...point, added: new Set(), changed: new Set(["A-1"])},
        bodyLayout,
    });
    panel.style.width = `${width}px`;
    document.body.append(panel);
    // 見出しへのスクロールは、文書に入った後の描き直しで付くことがある
    for (let frame = 0; frame < 2; frame += 1) {
        await new Promise((resolve) => requestAnimationFrame(resolve));
    }
    const body = panel.querySelector(".panel-body");
    const area = body.getBoundingClientRect();
    // 左右に並べるときは同じ見出しが 3 か所にあるので、見えている見出しを調べる
    const target = [...panel.querySelectorAll('[data-heading="決め方-1"]')]
        .find((heading) => heading.getClientRects().length > 0);
    const rect = target === undefined ? null : target.getBoundingClientRect();
    return {
        scrolled: body.scrollTop > 0,
        inView: rect !== null && rect.top >= area.top && rect.bottom <= area.bottom,
        nullCalls: headingCalls.filter((slug) => slug === null).length,
    };
}"""


@pytest.mark.parametrize(
    ("heading", "entries", "body_layout", "expected"),
    [
        pytest.param(
            "決め方-1",
            [],
            None,
            {"scrolled": True, "inView": True, "nullCalls": 0},
            id="heading_in_body",
        ),
        pytest.param(
            "無い",
            [],
            None,
            {"scrolled": False, "inView": False, "nullCalls": 1},
            id="heading_not_in_body",
        ),
        pytest.param(
            "決め方-1",
            [HEADING_BODY_ENTRY],
            "side",
            {"scrolled": True, "inView": True, "nullCalls": 0},
            id="heading_in_inline_body_when_side_narrow",
        ),
    ],
)
def test_detail_panel_when_heading(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
    heading: str,
    entries: list[dict[str, Any]],
    body_layout: str | None,
    expected: dict[str, object],
) -> None:
    """指した見出しを画面に入れて開く（正常系）。"""
    # 準備
    data = make_data(
        docs=[make_item("A-1", **({"history": entries, "seq": 1} if entries else {}))],
        bodies={"A-1.md": HEADING_BODY},
    )
    load_preview_scripts()
    load_preview_styles()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        OPEN_HEADING_PANEL_SCRIPT,
        {
            "data": data,
            "heading": heading,
            "point": DIFF_POINT if entries else None,
            "bodyLayout": body_layout,
            "width": 480,
        },
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
    load_mdmark: LoadMdmark,
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
    load_mdmark()
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
    load_mdmark: LoadMdmark,
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
    load_mdmark()
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
    load_mdmark: LoadMdmark,
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
    load_mdmark()
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
    load_mdmark: LoadMdmark,
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
    load_mdmark()
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
OPEN_REVIEW_PANEL_FUNCTION = """const openReviewPanel = async ({data, reviews, removed, editing, editingIn = "detail", full, calls}) => {
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
                editingIn,
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
async ({data, reviews, removed, editing, editingIn}) => {
    const calls = {full: 0, cancelEdit: 0};
    const panel = await openReviewPanel({data, reviews, removed, editing, editingIn, full: false, calls});
    const section = panel.querySelector(".d-review");
    const labelOf = (button) => button.getAttribute("aria-label") ?? button.textContent.trim();
    return {
        count: section.querySelector("h3 .count").textContent.trim(),
        rows: [...section.querySelectorAll("li")].map((row) => ({
            buttons: [...row.querySelectorAll("button")].map(labelOf),
            status: [...row.querySelectorAll('[role="status"]')].map((status) => status.textContent.trim()),
            hasField: row.querySelector("textarea") !== null,
            body: row.querySelector(".review-body")?.textContent ?? null,
        })),
        focuses: [...section.querySelectorAll("[data-focus]")].map((element) => element.getAttribute("data-focus")),
    };
}"""
)


def test_detail_panel_when_review_rows(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """レビュー中のコメントの行に修正・削除を置き、書き換えている行と消した行を元の場所に描く（正常系）。"""
    # 準備
    data = make_data(decisions=[make_item("D-1", status="未決定")])
    load_preview_scripts()
    load_mdmark()
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
            "body": "案 A にする",
        },
        {
            "buttons": ["元に戻す"],
            "status": ["コメントを削除しました。"],
            "hasField": False,
            "body": None,
        },
        {
            "buttons": ["キャンセル", "修正"],
            "status": [],
            "hasField": True,
            "body": None,
        },
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
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """全画面で書き換えの入力欄の Esc は、書き換えだけを捨てて全画面を閉じない（正常系）。"""
    # 準備
    data = make_data(decisions=[make_item("D-1", status="未決定")])
    load_preview_scripts()
    load_mdmark()
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


def test_detail_panel_when_review_editing_in_list(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """コメントの一覧で書き換えている行は、詳細パネルでは本文だけで描く（正常系）。"""
    # 準備
    data = make_data(decisions=[make_item("D-1", status="未決定")])
    load_preview_scripts()
    load_mdmark()
    # 実行
    result = preview_page.evaluate(
        REVIEW_ROWS_SCRIPT,
        {
            "data": data,
            "reviews": [_review_item("C-1", "案 A にする")],
            "removed": [],
            "editing": "C-1",
            "editingIn": "list",
        },
    )
    # 検証
    assert result["rows"] == [
        {"buttons": [], "status": [], "hasField": False, "body": "案 A にする"}
    ]


# 取り下げた理由
WITHDRAWN_REASON = "別の調査で足りた"

# 選んだ時点の後に、取り下げと理由を足した回（前は両方とも無かった）
WITHDRAW_ENTRY = {
    "seq": 1,
    "at": ENTRY_AT,
    "before": {"withdrawn": None, "reason": None},
}

# 詳細パネルを開き（point があれば差分つきで）、題の札・取り下げた理由の節・キーの一覧の取り下げの行を調べる
OPEN_WITHDRAWN_PANEL_SCRIPT = """async ({data, id, point, reasonText}) => {
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const panel = MindmapPreview.detailPanel({
        id,
        index,
        full: false,
        on: {open: noop, close: noop, full: noop, back: noop, forward: noop, diagram: noop},
        comment: null,
        highlight: null,
        diff: point === null ? null : {...point, added: new Set(), changed: new Set([id])},
    });
    document.body.append(panel);
    await new Promise((resolve) => requestAnimationFrame(resolve));
    const reasonSection = [...panel.querySelectorAll("section.d-sec")].find(
        (section) => section.querySelector("h3")?.textContent === "取り下げた理由"
    );
    const withdrawnLabel = [...panel.querySelectorAll("dl.d-meta dt")].find(
        (label) => label.textContent === "取り下げ"
    );
    return {
        titleBadge: (panel.querySelector(".d-title .wd-badge")?.textContent ?? "").includes("取り下げ"),
        reasonSection: reasonSection !== undefined,
        reasonShown: (reasonSection?.textContent ?? "").includes(reasonText),
        reasonAdded: reasonSection?.querySelector(".df-now") != null,
        metaRow: withdrawnLabel !== undefined,
        metaBadgeAdded: withdrawnLabel?.nextElementSibling?.querySelector(".df-now .wd-badge") != null,
    };
}"""


@pytest.mark.parametrize(
    ("item_id", "point", "expected"),
    [
        pytest.param(
            "R-1",
            None,
            {
                "titleBadge": True,
                "reasonSection": True,
                "reasonShown": True,
                "reasonAdded": False,
                "metaRow": False,
                "metaBadgeAdded": False,
            },
            id="withdrawn_without_diff",
        ),
        pytest.param(
            "R-1",
            DIFF_POINT,
            {
                "titleBadge": True,
                "reasonSection": True,
                "reasonShown": True,
                "reasonAdded": True,
                "metaRow": True,
                "metaBadgeAdded": True,
            },
            id="withdrawn_in_range",
        ),
        pytest.param(
            "R-2",
            None,
            {
                "titleBadge": False,
                "reasonSection": False,
                "reasonShown": False,
                "reasonAdded": False,
                "metaRow": False,
                "metaBadgeAdded": False,
            },
            id="not_withdrawn",
        ),
    ],
)
def test_detail_panel_when_withdrawn(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
    item_id: str,
    point: dict[str, Any] | None,
    expected: dict[str, bool],
) -> None:
    """取り下げた項目の題に札を置き、理由を節に出す（正常系）。"""
    # 準備
    data = make_data(
        research=[
            make_item(
                "R-1",
                withdrawn=True,
                reason=WITHDRAWN_REASON,
                history=[WITHDRAW_ENTRY],
                seq=1,
            ),
            make_item("R-2"),
        ]
    )
    load_preview_scripts()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        OPEN_WITHDRAWN_PANEL_SCRIPT,
        {"data": data, "id": item_id, "point": point, "reasonText": WITHDRAWN_REASON},
    )
    # 検証
    assert result == expected


# 詳細パネルを差分つきで開き、本文の差分の語の面（`span.df-word`）を、足した面（add）・消した面（del）と文字に直して調べる。
# 本文の囲み（足した塊 `ins.df-blk`・消した塊 `del.df-blk`）ごと、用語の印と項目の ID のリンクごと、表の行（`tr.df-row`）ごとに分けて返す
OPEN_WORD_DIFF_PANEL_SCRIPT = """async ({data, point}) => {
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
    const wordMarks = (root) => [...root.querySelectorAll("span.df-word")].map((word) => ({
        kind: word.classList.contains("df-add") ? "add" : word.classList.contains("df-del") ? "del" : "none",
        text: word.textContent,
    }));
    const body = panel.querySelector(".md:not(.md-value)");
    const blocks = [...body.querySelectorAll("ins.df-blk, del.df-blk")].map((block) => ({
        tag: block.tagName.toLowerCase(),
        paragraph: block.querySelector("p")?.textContent ?? null,
        words: wordMarks(block),
    }));
    const added = body.querySelector("ins.df-blk p");
    const links = added === null ? null : {
        terms: [...added.querySelectorAll("a.term")].map((link) => link.textContent),
        refs: [...added.querySelectorAll("a.idref")].map((link) => link.getAttribute("data-id")),
        wordsInLinks: added.querySelectorAll("a span.df-word, span.df-word a").length,
    };
    const rows = [...body.querySelectorAll("tr.df-row")].map((row) => ({
        op: row.classList.contains("df-add") ? "add" : "del",
        words: wordMarks(row),
        signs: row.querySelectorAll(".df-sign").length,
        signsInsideWords: [...row.querySelectorAll(".df-sign, .sr-only")]
            .filter((sign) => sign.closest("span.df-word") !== null).length,
    }));
    return {blocks, words: wordMarks(body), links, rows};
}"""


def _body_entry(*, line: int, now: list[str], before: list[str]) -> dict[str, Any]:
    """本文の `body_diff` を 1 つ持つ変更履歴の 1 回分を返す。"""
    return {
        "seq": 1,
        "at": ENTRY_AT,
        "before": {},
        "body_diff": [{"line": line, "now": now, "before": before}],
    }


# 書き換える段落（1 つ目）・変えない段落（2 つ目）・消す段落（3 つ目）を持つ本文の今と、変えた回
WORD_BODY_NOW = "要件は今週までに決める。\n\n変えない段落\n"
WORD_BODY_ENTRY = {
    "seq": 1,
    "at": ENTRY_AT,
    "before": {},
    "body_diff": [
        {
            "line": 1,
            "now": ["要件は今週までに決める。"],
            "before": ["要件は来週までに決める。"],
        },
        {"line": 4, "now": [], "before": ["", "消す段落"]},
    ],
}


def test_detail_panel_when_diff_inline_words(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """書き換えた段落の変わった語だけを囲み、消しただけの段落は囲まない（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1", body="D-1.md", history=[WORD_BODY_ENTRY], seq=1)],
        bodies={"D-1.md": WORD_BODY_NOW},
    )
    load_preview_scripts()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(OPEN_WORD_DIFF_PANEL_SCRIPT, {"data": data, "point": DIFF_POINT})
    # 検証
    assert result["blocks"] == [
        {
            "tag": "del",
            "paragraph": "要件は来週までに決める。",
            "words": [{"kind": "del", "text": "来週"}],
        },
        {
            "tag": "ins",
            "paragraph": "要件は今週までに決める。",
            "words": [{"kind": "add", "text": "今週"}],
        },
        {"tag": "del", "paragraph": "消す段落", "words": []},
    ]
    # 変えない 2 つ目の段落にも、語の面は付かない
    assert result["words"] == [
        {"kind": "del", "text": "来週"},
        {"kind": "add", "text": "今週"},
    ]


# 1 つ目の段落を消し、続く 2 つ目の段落の語を書き換えた本文の今と、変えた回（消した行 3 行・足した行 1 行）
UNPAIRED_BODY_NOW = "要件は今週までに決める。\n"
UNPAIRED_BODY_ENTRY = _body_entry(
    line=1,
    now=["要件は今週までに決める。"],
    before=["消す段落", "", "要件は来週までに決める。"],
)


def test_detail_panel_when_diff_lines_unpaired(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """行の数が揃わない書き換えは語の面を付けない（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1", body="D-1.md", history=[UNPAIRED_BODY_ENTRY], seq=1)],
        bodies={"D-1.md": UNPAIRED_BODY_NOW},
    )
    load_preview_scripts()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(OPEN_WORD_DIFF_PANEL_SCRIPT, {"data": data, "point": DIFF_POINT})
    # 検証
    assert result["words"] == []
    # 行の印は今までどおり
    assert [block["tag"] for block in result["blocks"]] == ["del", "ins"]


# 用語集の用語「要件」
TERM_TITLE = "要件"

# 用語と項目 D-2 の ID を含む段落の語を書き換えた本文の今と、変えた回
LINKS_BODY_NOW = "要件は D-2 と今週までに決める。\n"
LINKS_BODY_ENTRY = _body_entry(
    line=1,
    now=["要件は D-2 と今週までに決める。"],
    before=["要件は D-2 と来週までに決める。"],
)


def test_detail_panel_when_diff_inline_words_keep_links(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """語の面を付けても、本文の用語の印と項目の ID のリンクは分けない（正常系）。"""
    # 準備
    data = make_data(
        decisions=[
            make_item("D-1", body="D-1.md", history=[LINKS_BODY_ENTRY], seq=1),
            make_item("D-2"),
        ],
        terms=[make_item("G-1", title=TERM_TITLE)],
        bodies={"D-1.md": LINKS_BODY_NOW},
    )
    load_preview_scripts()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(OPEN_WORD_DIFF_PANEL_SCRIPT, {"data": data, "point": DIFF_POINT})
    # 検証
    assert result["links"] == {
        "terms": [TERM_TITLE],
        "refs": ["D-2"],
        "wordsInLinks": 0,
    }
    assert result["words"] == [
        {"kind": "del", "text": "来週"},
        {"kind": "add", "text": "今週"},
    ]
    added = [block for block in result["blocks"] if block["tag"] == "ins"]
    assert [block["words"] for block in added] == [[{"kind": "add", "text": "今週"}]]


# 本文の表の本体の行を書き換えた本文（見出し・区切り・1 行の表）の今と、変えた回
TABLE_BODY_NOW = "| 列 A | 列 B |\n| --- | --- |\n| D-1 | 今週 |\n"
TABLE_BODY_ENTRY = _body_entry(line=3, now=["| D-1 | 今週 |"], before=["| D-1 | 来週 |"])


def test_detail_panel_when_diff_inline_words_in_table_row(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """表の行の対では、行の印を除いて比べ、書き換えたセルの語だけを囲む（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1", body="D-1.md", history=[TABLE_BODY_ENTRY], seq=1)],
        bodies={"D-1.md": TABLE_BODY_NOW},
    )
    load_preview_scripts()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(OPEN_WORD_DIFF_PANEL_SCRIPT, {"data": data, "point": DIFF_POINT})
    # 検証
    assert result["rows"] == [
        {
            "op": "del",
            "words": [{"kind": "del", "text": "来週"}],
            "signs": 1,
            "signsInsideWords": 0,
        },
        {
            "op": "add",
            "words": [{"kind": "add", "text": "今週"}],
            "signs": 1,
            "signsInsideWords": 0,
        },
    ]


# 表だけの本文（1 行目から表）の今と、表の直前にあった段落（1〜2 行目）を消した回
REMOVED_BEFORE_TABLE_NOW = "| 列 A | 列 B |\n| --- | --- |\n| D-1 | 今週 |\n"
REMOVED_BEFORE_TABLE_ENTRY = _body_entry(line=1, now=[], before=["消した段落", ""])

# 消した塊の親と直後の兄弟、表の枠の子、表を包む入れ物の子を調べる
REMOVED_BEFORE_TABLE_SCRIPT = """async ({data, point}) => {
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
    const removed = panel.querySelector(".md:not(.md-value) del.df-blk");
    const next = removed.nextElementSibling;
    return {
        parentIsWrap: removed.parentElement.classList.contains("md-table-wrap"),
        nextIsFrame: next !== null && next.classList.contains("md-table-frame"),
        frameChildren: next === null ? null : [...next.children].map((child) => child.className),
        wrapChildren: next?.firstElementChild == null ? null : [...next.firstElementChild.children].map((child) => child.tagName),
    };
}"""


def test_detail_panel_when_diff_removed_before_table(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """表の直前で消した塊を、表を包む入れ物と枠の外（表の前）へ差し込む（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1", body="D-1.md", history=[REMOVED_BEFORE_TABLE_ENTRY], seq=1)],
        bodies={"D-1.md": REMOVED_BEFORE_TABLE_NOW},
    )
    load_preview_scripts()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(REMOVED_BEFORE_TABLE_SCRIPT, {"data": data, "point": DIFF_POINT})
    # 検証
    assert result == {
        "parentIsWrap": False,
        "nextIsFrame": True,
        "frameChildren": ["md-table-wrap"],
        "wrapChildren": ["TABLE"],
    }


# 図のノードのラベルを変えた本文（5 行目にフローチャートのノードを持つ）の今と、変えた回
RAW_BODY_NOW = "# 図\n\n```mermaid\nflowchart TD\n  A[設計を決める] --> B\n```\n"
RAW_BODY_ENTRY = _body_entry(
    line=5, now=["  A[設計を決める] --> B"], before=["  A[仕様を決める] --> B"]
)

# 図の Raw の行（消した行・足した行・変えない行）ごとの語の面を調べる
RAW_LINE_WORDS_SCRIPT = """() => [...document.querySelectorAll("pre.dg-raw.df-raw .df-line")].map((line) => ({
    op: line.classList.contains("df-add") ? "add" : line.classList.contains("df-del") ? "del" : "same",
    words: [...line.querySelectorAll("span.df-word")].map((word) => ({
        kind: word.classList.contains("df-add") ? "add" : word.classList.contains("df-del") ? "del" : "none",
        text: word.textContent,
    })),
}))"""


def test_detail_panel_when_diff_raw_inline_words(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """図の Raw の変えた行の対に、変わった語だけの面を付ける（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1", body="D-1.md", history=[RAW_BODY_ENTRY], seq=1)],
        bodies={"D-1.md": RAW_BODY_NOW},
    )
    load_preview_scripts()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    load_library("mermaid")
    # 実行
    preview_page.evaluate(OPEN_DIAGRAM_PANEL_SCRIPT, {"data": data, "point": DIFF_POINT})
    preview_page.wait_for_function("() => document.querySelector('pre.dg-raw.df-raw') !== null")
    preview_page.click("button[data-act='diagram-raw']")
    lines = preview_page.evaluate(RAW_LINE_WORDS_SCRIPT)
    # 検証
    # 語の面を持つ行は、消した行と足した行の 2 つだけ
    words_by_op = {line["op"]: line["words"] for line in lines if line["words"]}
    assert words_by_op == {
        "del": [{"kind": "del", "text": "仕様"}],
        "add": [{"kind": "add", "text": "設計"}],
    }
    assert sum(1 for line in lines if line["words"]) == len(words_by_op)


# 詳細パネルを差分つきで開き、キーの前の値（`del.df-was`）と今の値（`ins.df-now`）の語の面（`span.df-word`）を、
# 題と、渡した CSS セレクターに当たる要素ごとに、面の文字と読み上げの文字（`span.sr-only`）の置き場所に直して調べる。
# 面を塗らない差分（`span.df-kv.df-plain`）と、パネル全体の語の面の数も返す
OPEN_KEY_WORD_DIFF_PANEL_SCRIPT = """async ({data, point, selectors}) => {
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
    const texts = (root, selector) => [...root.querySelectorAll(selector)].map((word) => word.textContent);
    const pairOf = (root) => ({
        was: texts(root, "del.df-was span.df-word.df-del"),
        now: texts(root, "ins.df-now span.df-word.df-add"),
        wasText: root.querySelector("del.df-was")?.textContent ?? null,
        nowText: root.querySelector("ins.df-now")?.textContent ?? null,
        words: root.querySelectorAll("span.df-word").length,
        reading: [...root.querySelectorAll("span.sr-only")].map((reading) => ({
            text: reading.textContent,
            insideWord: reading.closest("span.df-word") !== null || reading.querySelector("span.df-word") !== null,
        })),
    });
    return {
        title: pairOf(panel.querySelector(".d-title")),
        pairs: selectors.flatMap((selector) => [...panel.querySelectorAll(selector)]).map(pairOf),
        // 前の値・今の値の文字だけ（語の面の有無によらない）
        texts: selectors.flatMap((selector) => [...panel.querySelectorAll(selector)]).map((element) => ({
            was: element.querySelector("del.df-was")?.textContent ?? null,
            now: element.querySelector("ins.df-now")?.textContent ?? null,
        })),
        plain: {
            pairs: panel.querySelectorAll("span.df-kv.df-plain").length,
            words: panel.querySelectorAll("span.df-kv.df-plain span.df-word").length,
        },
        allWords: panel.querySelectorAll("span.df-word").length,
    };
}"""

# 題・背景（`lead`）・案 A の内容・状態を変え、本文を変えない回（前の値を持つ）
KEY_WORDS_ENTRY = {
    "seq": 1,
    "at": ENTRY_AT,
    "before": {
        "title": "要件を来週までに決める",
        "lead": "要件は来週までに決める。",
        "options": [{"key": "A", "content": "毎週の会議で決める"}],
        "status": "未決定",
    },
}

# 読み上げの「前の値: 」「今の値: 」は、語の面の外に置く
READING_OUTSIDE_WORDS = [
    {"text": "前の値: ", "insideWord": False},
    {"text": "今の値: ", "insideWord": False},
]


def test_detail_panel_when_diff_key_words(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """題と文字列の値のキーの差分で、変わった語だけを囲む（正常系）。"""
    # 準備
    data = make_data(
        decisions=[
            make_item(
                "D-1",
                title="要件を今週までに決める",
                lead="要件は今週までに決める。",
                options=[{"key": "A", "content": "毎月の会議で決める"}],
                status="要見直し",
                history=[KEY_WORDS_ENTRY],
                seq=1,
            )
        ],
    )
    load_preview_scripts()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        OPEN_KEY_WORD_DIFF_PANEL_SCRIPT,
        {
            "data": data,
            "point": DIFF_POINT,
            "selectors": ["[data-key=\"lead\"]", "[data-key=\"options[A].content\"]"],
        },
    )
    # 検証
    # 題・背景・案 A の内容は、前の値の消した語と今の値の足した語だけを囲む
    assert (result["title"]["was"], result["title"]["now"]) == (["来週"], ["今週"])
    lead, content = result["pairs"]
    assert (lead["was"], lead["now"]) == (["来週"], ["今週"])
    assert (content["was"], content["now"]) == (["毎週"], ["毎月"])
    # 読み上げの文字は、前の値・今の値の頭に残り、語の面の外にある
    assert result["title"]["reading"] == READING_OUTSIDE_WORDS
    assert lead["reading"] == READING_OUTSIDE_WORDS
    assert content["reading"] == READING_OUTSIDE_WORDS
    assert result["title"]["wasText"] == "前の値: 要件を来週までに決める"
    assert result["title"]["nowText"] == "今の値: 要件を今週までに決める"
    # 状態（面を塗らない差分）は、対が 1 つあり、語の面を持たない
    assert result["plain"] == {"pairs": 1, "words": 0}
    # 語の面は、題・背景・案 A の内容の前の値と今の値の 6 つだけ
    assert result["allWords"] == 6


def _load_libraries(load_library: LoadLibrary, load_mdmark: LoadMdmark, names: list[str]) -> None:
    """渡した名前の描画のライブラリを、ページに読む（mdmark は `loadMdmark` で読む）。"""
    for name in names:
        if name == "mdmark":
            load_mdmark()
        else:
            load_library(name)


@pytest.mark.parametrize(
    ("overrides", "before", "selector", "expected_texts", "libraries"),
    [
        pytest.param(
            {"lead": "要件は来週までに決める。"},
            {"lead": None},
            "[data-key=\"lead\"]",
            [{"was": "前の値: （なし）", "now": "今の値: 要件は来週までに決める。"}],
            ["marked", "mdmark", "jsdiff"],
            id="added",
        ),
        pytest.param(
            {"lead": "予算を承認する"},
            {"lead": "要件は来週までに決める。"},
            "[data-key=\"lead\"]",
            [{"was": "前の値: 要件は来週までに決める。", "now": "今の値: 予算を承認する"}],
            ["marked", "mdmark", "jsdiff"],
            id="unrelated",
        ),
        pytest.param(
            {"tags": ["要件", "運用"], "date": "2026-10-08"},
            {"tags": ["要件", "会議"], "date": "2026-10-01"},
            "dl.d-meta dd.df-key",
            [
                {"was": "前の値: 2026-10-01", "now": "今の値: 2026-10-08"},
                {"was": "前の値: 要件、会議", "now": "今の値: 要件、運用"},
            ],
            ["marked", "mdmark", "jsdiff"],
            id="list_and_date",
        ),
        pytest.param(
            {"lead": "要件は今週までに決める。"},
            {"lead": "要件は来週までに決める。"},
            "[data-key=\"lead\"]",
            [{"was": "前の値: 要件は来週までに決める。", "now": "今の値: 要件は今週までに決める。"}],
            ["marked", "mdmark"],
            id="jsdiff_missing",
        ),
    ],
)
def test_detail_panel_when_diff_key_words_skipped(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
    overrides: dict[str, Any],
    before: dict[str, Any],
    selector: str,
    expected_texts: list[dict[str, str]],
    libraries: list[str],
) -> None:
    """語の面の対でないキーと、比べられない値には語の面を付けない（正常系）。"""
    # 準備
    history = [{"seq": 1, "at": ENTRY_AT, "before": before}]
    data = make_data(decisions=[make_item("D-1", history=history, seq=1, **overrides)])
    load_preview_scripts()
    # jsdiff を読めないケースは、jsdiff を差し込まない
    _load_libraries(load_library, load_mdmark, libraries)
    # 実行
    result = preview_page.evaluate(
        OPEN_KEY_WORD_DIFF_PANEL_SCRIPT, {"data": data, "point": DIFF_POINT, "selectors": [selector]}
    )
    # 検証
    # どの対にも語の面が無い
    assert result["allWords"] == 0
    # 前の値・今の値は、今までどおり del.df-was・ins.df-now で並ぶ
    assert result["texts"] == expected_texts


# 本文の行の差分の打ち切りの時間（ミリ秒。`LINE_DIFF_TIMEOUT_MS`）
LINE_DIFF_TIMEOUT_MS = 40

# 本文の行の差分（`Diff.diffLines`）を打ち切り（`undefined` を返し）、その間に時計を打ち切りの時間より進める包みを被せる
INSTALL_LINE_DIFF_TIMEOUT_SCRIPT = """(timeoutMs) => {
    const now = performance.now.bind(performance);
    let advanced = 0;
    performance.now = () => now() + advanced;
    Diff.diffLines = () => {
        advanced += timeoutMs + 10;
        return undefined;
    };
}"""

# `lead` と本文の 1 行目を書き換えた回（本文の行の差分を呼ぶ）
BODY_TOO_LARGE_ENTRY = {
    "seq": 1,
    "at": ENTRY_AT,
    "before": {"lead": "要件は来週までに決める。"},
    "body_diff": [
        {
            "line": 1,
            "now": ["要件は今週までに決める。"],
            "before": ["要件は来週までに決める。"],
        },
    ],
}


def test_detail_panel_when_diff_key_words_body_too_large(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """本文の行の差分を打ち切ったときは、キーの値の語の差分にも時間を足し直さない（正常系）。"""
    # 準備
    data = make_data(
        decisions=[
            make_item(
                "D-1",
                lead="要件は今週までに決める。",
                body="D-1.md",
                history=[BODY_TOO_LARGE_ENTRY],
                seq=1,
            )
        ],
        bodies={"D-1.md": WORD_BODY_NOW},
    )
    load_preview_scripts()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    preview_page.evaluate(INSTALL_LINE_DIFF_TIMEOUT_SCRIPT, LINE_DIFF_TIMEOUT_MS)
    # 実行
    result = preview_page.evaluate(
        OPEN_KEY_WORD_DIFF_PANEL_SCRIPT,
        {"data": data, "point": DIFF_POINT, "selectors": ['[data-key="lead"]']},
    )
    note = preview_page.evaluate("() => document.querySelector('.df-note')?.textContent ?? ''")
    # 検証
    # 本文の頭に、本文の差分を計算しきれない旨が出る
    assert "本文の差分を出せません" in note
    # 背景の前の値・今の値は今までどおり並び、語の面は付かない
    assert result["texts"] == [
        {"was": "前の値: 要件は来週までに決める。", "now": "今の値: 要件は今週までに決める。"}
    ]
    assert result["allWords"] == 0


# 資料・調査の説明とエイリアスの節の位置と中身、キーの一覧の行を調べる（markers の見出しとキーの要素を、中身の直下の子の位置で返す）
DESCRIPTION_ALIASES_SCRIPT = (
    OPEN_PANEL_FUNCTION
    + """
async ({data, id, markers}) => {
    const panel = await openPanel(data, id);
    const detail = panel.querySelector(".detail");
    const position = (element) => {
        let node = element;
        while (node !== null && node.parentElement !== detail) node = node.parentElement;
        return node === null ? -1 : [...detail.children].indexOf(node);
    };
    const find = (marker) => marker.heading !== undefined
        ? [...panel.querySelectorAll("h3")].find((element) => (element.textContent ?? "").trim() === marker.heading) ?? null
        : panel.querySelector(`[data-key="${marker.key}"]`);
    const descriptionSection = find({heading: "説明"});
    const aliasSection = find({heading: "エイリアス"});
    return {
        positions: markers.map((marker) => position(find(marker))),
        descriptionKeyed: descriptionSection?.parentElement.querySelector('[data-key="description"]') != null,
        tags: [...(aliasSection?.parentElement.querySelectorAll(".tag") ?? [])].map((tag) => tag.textContent),
        metaLabels: [...panel.querySelectorAll("dl.d-meta dt")].map((label) => label.textContent),
    };
}"""
)


@pytest.mark.parametrize(
    ("item_id", "markers", "present", "tags"),
    [
        pytest.param(
            "A-1",
            [{"heading": "説明"}, {"heading": "エイリアス"}, {"heading": "本文"}],
            True,
            ["特殊効果", "エフェクト"],
            id="docs",
        ),
        pytest.param(
            "R-1",
            [
                {"key": "question"},
                {"heading": "説明"},
                {"key": "conclusion"},
                {"heading": "エイリアス"},
                {"heading": "調査の観点"},
            ],
            True,
            ["特殊効果", "エフェクト"],
            id="research",
        ),
        pytest.param("A-2", [{"heading": "説明"}, {"heading": "エイリアス"}], False, [], id="neither"),
    ],
)
def test_detail_panel_when_description_aliases(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
    item_id: str,
    markers: list[dict[str, str]],
    present: bool,
    tags: list[str],
) -> None:
    """資料・調査の説明とエイリアスを決めた位置の節に出す（正常系）。"""
    # 準備
    data = make_data(
        docs=[
            make_item("A-1", description="演出の説明", aliases=["特殊効果", "エフェクト"]),
            make_item("A-2"),
        ],
        research=[
            make_item(
                "R-1",
                question="何を調べたか",
                description="調査の説明",
                conclusion="調べた結論",
                aliases=["特殊効果", "エフェクト"],
                angles=["観点 1"],
            )
        ],
        bodies={"A-1.md": "本文の段落\n", "A-2.md": "本文の段落\n"},
    )
    load_preview_scripts()
    load_mdmark()
    # 実行
    result = preview_page.evaluate(
        DESCRIPTION_ALIASES_SCRIPT, {"data": data, "id": item_id, "markers": markers}
    )
    # 検証
    assert (-1 not in result["positions"]) == present
    assert (result["positions"] == sorted(set(result["positions"]))) == present
    assert result["descriptionKeyed"] == present
    assert result["tags"] == tags
    assert not {"description", "aliases", "説明", "エイリアス"} & set(result["metaLabels"])


# 本文に印を持つ A-1 を開く（用語 G-1「特殊効果」・G-2「保存先」と、エイリアス「特殊効果」を持つ資料 A-2・調査 R-1）。on.open は呼ばれた ID を window.__calls に積む
OPEN_ALIAS_TIP_FUNCTION = """const openAliasTip = async ({data, full}) => {
    window.__calls = {open: [], full: 0};
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const panel = MindmapPreview.detailPanel({
        id: "A-1",
        index,
        full,
        on: {
            open: (id) => window.__calls.open.push(id),
            close: noop,
            full: () => { window.__calls.full += 1; },
            back: noop, forward: noop, diagram: noop, heading: noop,
        },
        comment: null,
        highlight: null,
        diff: null,
    });
    document.body.append(panel);
    // 全画面は開き、横のパネルは画面と同じく open を付けて見せる
    if (full) panel.showModal();
    else panel.classList.add("open");
    window.__panel = panel;
    await new Promise((resolve) => requestAnimationFrame(resolve));
};"""


OPEN_ALIAS_TIP_SCRIPT = OPEN_ALIAS_TIP_FUNCTION + "\n(args) => openAliasTip(args)"


def _alias_tip_data(make_data: MakeData, make_item: MakeItem) -> dict[str, Any]:
    """本文に「特殊効果」と「保存先」を持つ A-1 と、それらに一致する用語・資料・調査を持つ埋め込みのデータを返す。"""
    return make_data(
        terms=[
            make_item("G-1", title="特殊効果", meaning="演出の用語"),
            make_item("G-2", title="保存先", meaning="置き場所の用語"),
        ],
        docs=[
            make_item("A-1", body="A-1.md"),
            make_item("A-2", title="効果の資料", aliases=["特殊効果"], description="資料の説明"),
        ],
        research=[make_item("R-1", title="効果の調査", aliases=["特殊効果"])],
        bodies={"A-1.md": "特殊効果と保存先\n"},
    )


def test_detail_panel_when_alias_tip(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """資料・調査にも一致した印は押すとツールチップを残し、中のリンクで移る（正常系）。"""
    # 準備
    data = _alias_tip_data(make_data, make_item)
    load_preview_scripts()
    load_preview_styles()
    load_mdmark()
    preview_page.evaluate(
        OPEN_ALIAS_TIP_SCRIPT, {"data": data, "full": False}
    )
    links = preview_page.locator("a.tt-link")
    mark = preview_page.locator("a.term", has_text="特殊効果")
    # 実行
    mark.hover()
    links.first.wait_for(state="visible")
    shown = links.evaluate_all("(items) => items.map((item) => item.getAttribute('data-id'))")
    mark.click()
    # ポインターを印から外し、隠す待ち（150 ミリ秒）より長く待つ
    preview_page.mouse.move(1, 1)
    preview_page.wait_for_timeout(400)
    pinned = links.first.is_visible()
    after_pin = preview_page.evaluate("() => window.__calls.open")
    links.filter(has_text="効果の資料").click()
    links.first.wait_for(state="hidden")
    after_link = preview_page.evaluate("() => window.__calls.open")
    preview_page.locator("a.term", has_text="保存先").click()
    after_term = preview_page.evaluate("() => window.__calls.open")
    # 押して残したまま、詳細パネルを描き直す（古いパネルとその中のツールチップが文書から外れる）
    mark.click()
    preview_page.evaluate("() => window.__panel.remove()")
    preview_page.evaluate(OPEN_ALIAS_TIP_SCRIPT, {"data": data, "full": False})
    preview_page.mouse.move(1, 1)
    mark.hover()
    links.first.wait_for(state="visible")
    shown_after_redraw = links.evaluate_all("(items) => items.map((item) => item.getAttribute('data-id'))")
    # 検証
    assert shown == ["G-1", "A-2", "R-1"]
    assert (pinned, after_pin) == (True, [])
    assert after_link == ["A-2"]
    assert after_term == ["A-2", "G-2"]
    assert shown_after_redraw == ["G-1", "A-2", "R-1"]


# 全画面でツールチップの中にフォーカスを移して Esc を押した後の、フォーカスの場所・ツールチップの見え方・知らせた回数と全画面の開き具合
READ_ALIAS_TIP_STATE_SCRIPT = """() => ({
    active: document.activeElement?.matches("a.term") ? "mark" : document.activeElement?.className ?? "",
    full: window.__calls.full,
    open: window.__panel.open,
})"""


def test_detail_panel_when_alias_tip_escape_in_full(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """全画面でツールチップの中にフォーカスがあるときの Esc は、ツールチップだけを閉じて印へ戻す（正常系）。"""
    # 準備
    data = _alias_tip_data(make_data, make_item)
    load_preview_scripts()
    load_preview_styles()
    load_mdmark()
    preview_page.evaluate(
        OPEN_ALIAS_TIP_SCRIPT, {"data": data, "full": True}
    )
    links = preview_page.locator("a.tt-link")
    preview_page.locator("a.term", has_text="特殊効果").focus()
    links.first.wait_for(state="visible")
    # 印から Tab で中の最初のリンクへ移す
    preview_page.keyboard.press("Tab")
    in_link = preview_page.evaluate("() => document.activeElement?.matches('a.tt-link') === true")
    # 実行
    preview_page.keyboard.press("Escape")
    links.first.wait_for(state="hidden")
    # 検証
    assert in_link is True
    assert preview_page.evaluate(READ_ALIAS_TIP_STATE_SCRIPT) == {
        "active": "mark",
        "full": 0,
        "open": True,
    }


# ツールチップの先頭の見出しと並んだ項目の ID を読む（ツールチップは `popover` を持つ要素）
READ_TERM_TIP_SCRIPT = """() => {
    const tip = document.querySelector("a.tt-link")?.closest("[popover]");
    return {
        text: (tip?.textContent ?? "").replace(/\\s+/g, " ").trim(),
        ids: [...(tip?.querySelectorAll("a.tt-link") ?? [])].map((link) => link.getAttribute("data-id")),
    };
}"""


def test_detail_panel_when_term_aliases_tip(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """用語 2 件以上に一致した印は押すとツールチップを残し、中のリンクで移る（正常系）。"""
    # 準備
    data = make_data(
        terms=[
            make_item("G-1", title="移し替え", meaning="移すことの意味"),
            make_item("G-2", title="版の更新", aliases=["移し替え"], meaning="版を上げることの意味"),
        ],
        docs=[make_item("A-1", body="A-1.md")],
        bodies={"A-1.md": "移し替え\n"},
    )
    load_preview_scripts()
    load_preview_styles()
    load_mdmark()
    preview_page.evaluate(OPEN_ALIAS_TIP_SCRIPT, {"data": data, "full": False})
    links = preview_page.locator("a.tt-link")
    mark = preview_page.locator("a.term", has_text="移し替え")
    # 実行
    mark.hover()
    links.first.wait_for(state="visible")
    shown = preview_page.evaluate(READ_TERM_TIP_SCRIPT)
    mark.click()
    # ポインターを印から外し、隠す待ち（150 ミリ秒）より長く待つ
    preview_page.mouse.move(1, 1)
    preview_page.wait_for_timeout(400)
    pinned = links.first.is_visible()
    after_pin = preview_page.evaluate("() => window.__calls.open")
    links.filter(has_text="版の更新").click()
    links.first.wait_for(state="hidden")
    after_link = preview_page.evaluate("() => window.__calls.open")
    # 検証
    assert shown["ids"] == ["G-1", "G-2"]
    assert "用語 2" in shown["text"]
    assert (pinned, after_pin) == (True, [])
    assert after_link == ["G-2"]


# 見出しのタイトル（`.panel-title`）を調べる関数の集まり。`openHeadTitle` が項目を開き（開いていた詳細は外す）、`readHeadTitle` が今の見出しのタイトルの状態を読み、`readHeadButtonWidths` が見出しの表示されているボタンの幅を読み、`scrollBody` が本文のスクロール領域を送って見出しのタイトルの出し入れが済むまで待つ
HEAD_TITLE_FUNCTIONS = """
// 描画と、見張りが返す結果の反映を待つコマ数
const SETTLE_FRAMES = 3;
// 出し入れが済むのを待つ上限（ミリ秒）
const SCROLL_WAIT_MS = 1000;
const frames = (count) => new Promise((resolve) => {
    const tick = (left) => (left === 0 ? resolve() : requestAnimationFrame(() => tick(left - 1)));
    tick(count);
});
const openHeadTitle = async ({data, id, full}) => {
    window.__panel?.remove();
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const panel = MindmapPreview.detailPanel({
        id,
        index,
        full,
        on: {open: noop, close: noop, full: noop, back: noop, forward: noop, diagram: noop, heading: noop},
        comment: null,
        highlight: null,
        diff: null,
    });
    document.body.append(panel);
    // 全画面は開き、横のパネルは画面と同じく open を付けて見せる
    if (full) panel.showModal();
    else panel.classList.add("open");
    window.__panel = panel;
    await frames(SETTLE_FRAMES);
};
const readHeadTitle = () => {
    const title = window.__panel.querySelector(".panel-title");
    if (title === null) return null;
    return {
        shown: title.classList.contains("is-shown"),
        text: title.textContent,
        title: title.getAttribute("title"),
        ariaHidden: title.getAttribute("aria-hidden"),
        visibility: getComputedStyle(title).visibility,
    };
};
// 見出しの表示されているボタン（幅の広い画面で隠れる「一覧へ戻る」は除く）の幅
const readHeadButtonWidths = () => [...window.__panel.querySelectorAll(".panel-head .icon-btn")]
    .filter((button) => button.getClientRects().length > 0)
    .map((button) => button.getBoundingClientRect().width);
const scrollBody = async (position) => {
    const body = window.__panel.querySelector(".panel-body");
    body.scrollTop = position === "end" ? body.scrollHeight : 0;
    const deadline = performance.now() + SCROLL_WAIT_MS;
    // 見張りの結果は次のコマ以降に届くので、出し入れが済む（end なら出る・top なら隠れる）まで待つ
    while (performance.now() < deadline) {
        const title = window.__panel.querySelector(".panel-title");
        if (title !== null && title.classList.contains("is-shown") === (position === "end")) break;
        await frames(1);
    }
};"""


# 本文の頭 → 本文のスクロール領域の下端 → 頭へ戻す の順に、見出しのタイトルの状態を読む。本文の高さは、スクロール領域の高さの何倍かも返す
HEAD_TITLE_ON_SCROLL_SCRIPT = (
    HEAD_TITLE_FUNCTIONS
    + """
async ({data, id}) => {
    await openHeadTitle({data, id, full: false});
    const body = window.__panel.querySelector(".panel-body");
    const bodyRatio = body.scrollHeight / body.clientHeight;
    const top = readHeadTitle();
    const topButtons = readHeadButtonWidths();
    await scrollBody("end");
    const end = readHeadTitle();
    const endButtons = readHeadButtonWidths();
    await scrollBody("top");
    const back = readHeadTitle();
    const backButtons = readHeadButtonWidths();
    return {bodyRatio, top, end, back, buttons: {top: topButtons, end: endButtons, back: backButtons}};
}"""
)

# 見出しのタイトルを確かめる資料のタイトル（見出しの帯の幅に収まらない長さ）
HEAD_TITLE_LONG_TITLE = (
    "話し合いの進め方の手引き（セットアップからヒアリング・リサーチ・方針転換を経て"
    "ゴール判定でリリースするまでの流れと、各段で記録に残すことの一覧）"
)

# 見出しのボタン（`.panel-head .icon-btn`）の幅（`--control-h`）。長いタイトルでも縮まない
HEAD_BUTTON_WIDTH = 32

# 横のパネルの見出しの表示されているボタンの数（戻る・エクスポート・進む・全画面表示・閉じる。「一覧へ戻る」は幅の広い画面で隠れる）
HEAD_BUTTON_COUNT_PANEL = 5

# 全画面の見出しのボタンの数（戻る・エクスポート・進む・元の大きさに戻す）
HEAD_BUTTON_COUNT_FULL = 4

# 本文の高さを、本文のスクロール領域の高さの 3 倍以上にする段落の数
HEAD_TITLE_LONG_BODY_PARAGRAPHS = 200


def _head_title_data(make_data: MakeData, make_item: MakeItem) -> dict[str, Any]:
    """本文の長い資料 A-1（長いタイトル）と、本文の短い資料 A-2 を持つ埋め込みのデータを返す。"""
    long_body = "\n\n".join(f"{number} 番目の段落" for number in range(HEAD_TITLE_LONG_BODY_PARAGRAPHS))
    return make_data(
        docs=[
            make_item("A-1", title=HEAD_TITLE_LONG_TITLE),
            make_item("A-2", title="短い本文の資料"),
        ],
        bodies={"A-1.md": long_body, "A-2.md": "短い段落\n"},
    )


def test_detail_panel_when_head_title_on_scroll(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """本文の先頭のタイトルが本文のスクロール領域の上へ出ている間だけ、見出しのタイトルを出す（正常系）。"""
    # 準備
    data = _head_title_data(make_data, make_item)
    load_preview_scripts()
    load_preview_styles()
    load_mdmark()
    # 実行
    result = preview_page.evaluate(HEAD_TITLE_ON_SCROLL_SCRIPT, {"data": data, "id": "A-1"})
    # 検証
    # どの時点にも見出しのタイトルがある
    assert None not in (result["top"], result["end"], result["back"])
    # 本文はスクロール領域の高さの 3 倍以上ある
    assert result["bodyRatio"] >= 3
    # 本文の頭: タイトルは隠れ、場所は取ったまま。文字は全文を持ち、読み上げからは外す
    assert result["top"] == {
        "shown": False,
        "text": HEAD_TITLE_LONG_TITLE,
        "title": HEAD_TITLE_LONG_TITLE,
        "ariaHidden": "true",
        "visibility": "hidden",
    }
    # 本文の下端: 本文の先頭のタイトルが上へ外れ、見出しのタイトルが出る
    assert result["end"]["shown"] is True
    assert result["end"]["visibility"] == "visible"
    # 頭へ戻す: 隠れる
    assert result["back"]["shown"] is False
    # 長いタイトルでも、どの時点でも見出しのボタンは縮まない
    expected_widths = [HEAD_BUTTON_WIDTH] * HEAD_BUTTON_COUNT_PANEL
    assert result["buttons"]["top"] == expected_widths
    assert result["buttons"]["end"] == expected_widths
    assert result["buttons"]["back"] == expected_widths


# 本文の長い A-1 を開いて本文を送り、本文の短い A-2、本文の頭のままの A-1 の順に開き直して、開き直した直後の見出しのタイトルを読む
HEAD_TITLE_RERENDER_SCRIPT = (
    HEAD_TITLE_FUNCTIONS
    + """
async ({data}) => {
    await openHeadTitle({data, id: "A-1", full: false});
    await scrollBody("end");
    const scrolled = readHeadTitle();
    await openHeadTitle({data, id: "A-2", full: false});
    const short = readHeadTitle();
    await openHeadTitle({data, id: "A-1", full: false});
    const reopened = readHeadTitle();
    return {scrolled, short, reopened};
}"""
)


def test_detail_panel_when_head_title_rerender(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """描き直した後も、今の項目の本文の先頭のタイトルだけを見張る（正常系）。"""
    # 準備
    data = _head_title_data(make_data, make_item)
    load_preview_scripts()
    load_preview_styles()
    load_mdmark()
    # 実行
    result = preview_page.evaluate(HEAD_TITLE_RERENDER_SCRIPT, {"data": data})
    # 検証
    # どの時点にも見出しのタイトルがある
    assert None not in (result["scrolled"], result["short"], result["reopened"])
    # 開き直す前: 送った A-1 は見出しのタイトルが出ている
    assert result["scrolled"]["shown"] is True
    # A-2 を開き直した直後: A-2 のタイトルで、出ていない
    assert (result["short"]["text"], result["short"]["shown"]) == ("短い本文の資料", False)
    # 本文の頭のまま A-1 を開き直した直後: 前の見張りが残らず、出ていない
    assert (result["reopened"]["text"], result["reopened"]["shown"]) == (HEAD_TITLE_LONG_TITLE, False)


# 全画面で本文の長い A-1 を開き、送る前と、モーダルの本文のスクロール領域を下端まで送った後の見出しのタイトルを読む
HEAD_TITLE_FULL_SCRIPT = (
    HEAD_TITLE_FUNCTIONS
    + """
async ({data}) => {
    await openHeadTitle({data, id: "A-1", full: true});
    const before = readHeadTitle();
    const beforeButtons = readHeadButtonWidths();
    await scrollBody("end");
    const after = readHeadTitle();
    const afterButtons = readHeadButtonWidths();
    return {before, after, buttons: {before: beforeButtons, after: afterButtons}, inDialog: window.__panel.matches("dialog") && window.__panel.open};
}"""
)


def test_detail_panel_when_head_title_full(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """全画面でも、本文を送ったときだけ見出しのタイトルを出す（正常系）。"""
    # 準備
    data = _head_title_data(make_data, make_item)
    load_preview_scripts()
    load_preview_styles()
    load_mdmark()
    # 実行
    result = preview_page.evaluate(HEAD_TITLE_FULL_SCRIPT, {"data": data})
    # 検証
    # 送る前も送った後も見出しのタイトルがある
    assert None not in (result["before"], result["after"])
    # 開いているのは全画面の dialog
    assert result["inDialog"] is True
    # 送る前は出ず、送った後は dialog の中の見出しのタイトルが出る
    assert result["before"]["shown"] is False
    assert result["after"]["shown"] is True
    # 送る前も送った後も、見出しのボタンは縮まない
    expected_widths = [HEAD_BUTTON_WIDTH] * HEAD_BUTTON_COUNT_FULL
    assert result["buttons"]["before"] == expected_widths
    assert result["buttons"]["after"] == expected_widths


# 本文の 3 行目にまとまりのリンクを持つ今の本文
CHANGE_SET_LINK_BODY = "1 行目の段落\n\n[V-1 へ](#diff=V-1)\n"

# 3 行目をリンクの段落に書き換えた回（差分の本文でもリンクを描く）
CHANGE_SET_LINK_HISTORY = [
    {
        "seq": 1,
        "at": ENTRY_AT,
        "before": {},
        "body_diff": [{"line": 3, "now": ["[V-1 へ](#diff=V-1)"], "before": ["元の 3 行目の段落"]}],
    },
]

# 詳細パネルを開き、本文の「V-1 へ」を押したときに使う側へ知らせたまとまりと見出しを調べる
CHANGE_SET_LINK_SCRIPT = """async ({data, point}) => {
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const changeSetCalls = [];
    const headingCalls = [];
    const panel = MindmapPreview.detailPanel({
        id: "D-1",
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
            changeSet: (id) => changeSetCalls.push(id),
        },
        comment: null,
        highlight: null,
        diff: point === null ? null : {...point, added: new Set(), changed: new Set(["D-1"])},
    });
    document.body.append(panel);
    await new Promise((resolve) => requestAnimationFrame(resolve));
    const link = [...panel.querySelectorAll(".md a")].find(
        (element) => (element.textContent ?? "").trim() === "V-1 へ",
    );
    link.click();
    return {changeSetCalls, headingCalls};
}"""


@pytest.mark.parametrize(
    "point",
    [
        pytest.param(None, id="without_diff"),
        pytest.param(DIFF_POINT, id="with_diff"),
    ],
)
def test_detail_panel_when_change_set_link(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
    point: dict[str, object] | None,
) -> None:
    """本文のまとまりのリンクで `on.changeSet` を呼ぶ（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1", body="D-1.md", history=CHANGE_SET_LINK_HISTORY)],
        bodies={"D-1.md": CHANGE_SET_LINK_BODY},
    )
    load_preview_scripts()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(CHANGE_SET_LINK_SCRIPT, {"data": data, "point": point})
    # 検証
    assert result == {"changeSetCalls": ["V-1"], "headingCalls": []}


# 1 つ目の段落を消し、末尾に段落を足した本文の今と、変えた回（消した段落と足した段落は離れていて、印は 2 つ）
MINIMAP_NOW_BODY = "残る段落\n\n足した段落\n"
MINIMAP_ENTRY = {
    "seq": 1,
    "at": ENTRY_AT,
    "before": {},
    "body_diff": [
        {"line": 1, "now": [], "before": ["消した段落", ""]},
        {"line": 3, "now": ["足した段落"], "before": []},
    ],
}

# 詳細パネルを開き（差分は withDiff のときだけ）、本文のスクロール領域の中身と、帯の印の数と、本文の読み上げの名前を調べる
OPEN_MINIMAP_PANEL_SCRIPT = """async ({data, point, withDiff, minimap}) => {
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const panel = MindmapPreview.detailPanel({
        id: "D-1",
        index,
        full: false,
        on: {open: noop, close: noop, full: noop, back: noop, forward: noop, diagram: noop},
        comment: null,
        highlight: null,
        diff: withDiff ? {...point, added: new Set(), changed: new Set(["D-1"])} : null,
        minimap,
    });
    document.body.append(panel);
    // 本文の差分と帯の印は、文書に入った後の描き直しで置かれる
    for (let frame = 0; frame < 3; frame += 1) await new Promise((resolve) => requestAnimationFrame(resolve));
    const scroll = panel.querySelector(".panel-scroll");
    const kind = (child) =>
        child.classList.contains("panel-body") ? "body" : child.classList.contains("df-map") ? "map" : "other";
    return {
        children: [...(scroll?.children ?? [])].map(kind),
        marks: panel.querySelectorAll(".df-map button").length,
        bodyLabel: scroll?.querySelector(".panel-body")?.getAttribute("aria-label") ?? null,
    };
}"""


@pytest.mark.parametrize(
    ("with_diff", "minimap", "expected"),
    [
        pytest.param(
            True,
            True,
            {"children": ["body", "map"], "marks": 2, "bodyLabel": "詳細の本文"},
            id="diff_and_minimap",
        ),
        pytest.param(
            True,
            False,
            {"children": ["body"], "marks": 0, "bodyLabel": "詳細の本文"},
            id="diff_and_minimap_off",
        ),
        pytest.param(
            False,
            True,
            {"children": ["body"], "marks": 0, "bodyLabel": "詳細の本文"},
            id="no_diff",
        ),
    ],
)
def test_detail_panel_when_diff_minimap(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
    with_diff: bool,
    minimap: bool,
    expected: dict[str, Any],
) -> None:
    """差分の表示の間だけ本文の右に帯を並べ、表示しない上書きでは並べない（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1", body="D-1.md", history=[MINIMAP_ENTRY], seq=1)],
        bodies={"D-1.md": MINIMAP_NOW_BODY},
    )
    load_preview_scripts()
    load_preview_styles()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        OPEN_MINIMAP_PANEL_SCRIPT,
        {"data": data, "point": DIFF_POINT, "withDiff": with_diff, "minimap": minimap},
    )
    # 検証
    assert result == expected


# 詳細パネルを開き（差分は point があるときだけ）、本文の見出しの段と、足した囲みの中の見出しの上の余白を調べる
OPEN_HEADING_LEVELS_PANEL_SCRIPT = """async ({data, point}) => {
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const panel = MindmapPreview.detailPanel({
        id: "A-1",
        index,
        full: false,
        on: {open: noop, close: noop, full: noop, back: noop, forward: noop, diagram: noop},
        comment: null,
        highlight: null,
        diff: point === null ? null : {...point, added: new Set(), changed: new Set(["A-1"])},
    });
    document.body.append(panel);
    // 本文の差分と見出しの段下げは、文書に入った後の描き直しで置かれる
    for (let frame = 0; frame < 3; frame += 1) await new Promise((resolve) => requestAnimationFrame(resolve));
    const body = panel.querySelector(".md:not(.md-value)");
    const headings = [...body.querySelectorAll("h1, h2, h3, h4, h5, h6")].map((heading) => ({
        text: (heading.textContent ?? "").trim(),
        tag: heading.tagName.toLowerCase(),
        mdLevel: heading.getAttribute("data-md-level"),
        ariaLevel: heading.getAttribute("aria-level"),
    }));
    // 比べる元の段 2 の見出しを、足した囲みの外の同じ本文の中に置いて余白を読む
    const reference = document.createElement("h2");
    reference.setAttribute("data-md-level", "2");
    body.append(reference);
    const referenceMargin = getComputedStyle(reference).marginTop;
    const inBlock = [...body.querySelectorAll("ins.df-blk :is(h1, h2, h3, h4, h5, h6)")].map((heading) => ({
        text: (heading.textContent ?? "").trim(),
        sameAsLevel2: getComputedStyle(heading).marginTop === referenceMargin,
        fourPx: getComputedStyle(heading).marginTop === "4px",
    }));
    return {headings, inBlock};
}"""

# 本文の見出しの最も上の段が `##` の本文（「決め方」の下に「理由」）
HEADING_LEVELS_TOP_H2_BODY = "## 決め方\n\n決め方の段落\n\n### 理由\n\n理由の段落\n"

# 本文の見出しの最も上の段が `#` の本文（「要件」の下に「決め方」）
HEADING_LEVELS_TOP_H1_BODY = "# 要件\n\n要件の段落\n\n## 決め方\n\n決め方の段落\n"

# `##` から `######` までを順に持つ本文
HEADING_LEVELS_H2_TO_H6_BODY = "## 見出し2\n\n### 見出し3\n\n#### 見出し4\n\n##### 見出し5\n\n###### 見出し6\n"

# 前の版が `# 要件` と `## 決め方`、今が `## 決め方` だけの本文の今と、`# 要件` を消した回
HEADING_LEVELS_REMOVED_TOP_BODY = "## 決め方\n"
HEADING_LEVELS_REMOVED_TOP_ENTRY = _body_entry(line=1, now=[], before=["# 要件", ""])

# 前の版が段落だけ、今が `## 決め方` と段落の本文の今と、`## 決め方` を足した回
HEADING_LEVELS_ADDED_BLOCK_BODY = "## 決め方\n\n段落\n"
HEADING_LEVELS_ADDED_BLOCK_ENTRY = _body_entry(line=1, now=["## 決め方", ""], before=[])


@pytest.mark.parametrize(
    ("body", "entries", "point", "expected_headings", "expected_in_block"),
    [
        pytest.param(
            HEADING_LEVELS_TOP_H2_BODY,
            [],
            None,
            [
                {"text": "決め方", "tag": "h4", "mdLevel": "2", "ariaLevel": None},
                {"text": "理由", "tag": "h5", "mdLevel": "3", "ariaLevel": None},
            ],
            [],
            id="top_is_h2",
        ),
        pytest.param(
            HEADING_LEVELS_TOP_H1_BODY,
            [],
            None,
            [
                {"text": "要件", "tag": "h4", "mdLevel": "1", "ariaLevel": None},
                {"text": "決め方", "tag": "h5", "mdLevel": "2", "ariaLevel": None},
            ],
            [],
            id="top_is_h1",
        ),
        pytest.param(
            HEADING_LEVELS_H2_TO_H6_BODY,
            [],
            None,
            [
                {"text": "見出し2", "tag": "h4", "mdLevel": "2", "ariaLevel": None},
                {"text": "見出し3", "tag": "h5", "mdLevel": "3", "ariaLevel": None},
                {"text": "見出し4", "tag": "h6", "mdLevel": "4", "ariaLevel": None},
                {"text": "見出し5", "tag": "h6", "mdLevel": "5", "ariaLevel": "7"},
                {"text": "見出し6", "tag": "h6", "mdLevel": "6", "ariaLevel": "8"},
            ],
            [],
            id="beyond_h6",
        ),
        pytest.param(
            HEADING_LEVELS_REMOVED_TOP_BODY,
            [HEADING_LEVELS_REMOVED_TOP_ENTRY],
            DIFF_POINT,
            [
                {"text": "要件", "tag": "h4", "mdLevel": "1", "ariaLevel": None},
                {"text": "決め方", "tag": "h5", "mdLevel": "2", "ariaLevel": None},
            ],
            [],
            id="diff_removed_part_is_higher",
        ),
        pytest.param(
            HEADING_LEVELS_ADDED_BLOCK_BODY,
            [HEADING_LEVELS_ADDED_BLOCK_ENTRY],
            DIFF_POINT,
            [{"text": "決め方", "tag": "h4", "mdLevel": "2", "ariaLevel": None}],
            [{"text": "決め方", "sameAsLevel2": True, "fourPx": False}],
            id="diff_added_block_margin",
        ),
    ],
)
def test_detail_panel_when_body_heading_levels(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
    body: str,
    entries: list[dict[str, Any]],
    point: dict[str, object] | None,
    expected_headings: list[dict[str, str | None]],
    expected_in_block: list[dict[str, object]],
) -> None:
    """本文の見出しの最も上の段を h4 にし、段の差を保って並べる（正常系）。"""
    # 準備
    data = make_data(
        docs=[make_item("A-1", history=entries, seq=1)],
        bodies={"A-1.md": body},
    )
    load_preview_scripts()
    load_preview_styles()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(OPEN_HEADING_LEVELS_PANEL_SCRIPT, {"data": data, "point": point})
    # 検証
    assert result["headings"] == expected_headings
    # 足した囲みの中の見出しの上の余白は、4px でなく元の段の余白のまま
    assert result["inBlock"] == expected_in_block


# 本文を変えていない資料の変えた回（キーの状態だけを変えた）
BODY_UNCHANGED_ENTRY = {"seq": 1, "at": ENTRY_AT, "before": {"status": "未決定"}}

# 詳細パネルを指定の幅で差分つきに開き、並べ方の切り替えと左右の本文・インラインの本文の見え方を調べる
OPEN_SIDE_BY_SIDE_PANEL_SCRIPT = """async ({data, point, bodyLayout, width}) => {
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const panel = MindmapPreview.detailPanel({
        id: "D-1",
        index,
        full: false,
        on: {open: noop, close: noop, full: noop, back: noop, forward: noop, diagram: noop, layout: noop},
        comment: null,
        highlight: null,
        diff: {...point, added: new Set(), changed: new Set(["D-1"])},
        bodyLayout,
    });
    panel.style.width = `${width}px`;
    document.body.append(panel);
    // 本文の差分と、本文の幅による出し分けは、文書に入った後の描き直しで置かれる
    for (let frame = 0; frame < 4; frame += 1) await new Promise((resolve) => requestAnimationFrame(resolve));
    const visible = (element) => element !== null && element.getClientRects().length > 0;
    const marks = "ins.df-blk, del.df-blk";
    const switchGroup = panel.querySelector(".sbs-switch");
    const pressed = visible(switchGroup)
        ? switchGroup.querySelector('[aria-pressed="true"]').getAttribute("data-layout")
        : null;
    return {
        switch: visible(switchGroup),
        pressed,
        sbs: visible(panel.querySelector(".sbs")),
        sbsFallback: visible(panel.querySelector(".sbs-fallback")),
        inlineMarks: [...panel.querySelectorAll(marks)]
            .filter((mark) => mark.closest(".sbs") === null && visible(mark)).length,
        sbsMarks: [...panel.querySelectorAll(".sbs ins.df-blk, .sbs del.df-blk")]
            .filter(visible).length,
    };
}"""


@pytest.mark.parametrize(
    ("entries", "body_layout", "width", "expected"),
    [
        pytest.param(
            [MINIMAP_ENTRY],
            "inline",
            760,
            {
                "switch": True,
                "pressed": "inline",
                "sbs": False,
                "sbsFallback": False,
                "inlineMarks": 2,
                "sbsMarks": 0,
            },
            id="inline_wide",
        ),
        pytest.param(
            [MINIMAP_ENTRY],
            "side",
            760,
            {
                "switch": True,
                "pressed": "side",
                "sbs": True,
                "sbsFallback": False,
                "inlineMarks": 0,
                "sbsMarks": 2,
            },
            id="side_wide",
        ),
        pytest.param(
            [MINIMAP_ENTRY],
            "side",
            480,
            {
                "switch": False,
                "pressed": None,
                "sbs": False,
                "sbsFallback": True,
                "inlineMarks": 2,
                "sbsMarks": 0,
            },
            id="side_narrow",
        ),
        pytest.param(
            [BODY_UNCHANGED_ENTRY],
            "side",
            760,
            {
                "switch": False,
                "pressed": None,
                "sbs": False,
                "sbsFallback": False,
                "inlineMarks": 0,
                "sbsMarks": 0,
            },
            id="side_body_unchanged",
        ),
    ],
)
def test_detail_panel_when_body_side_by_side(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
    entries: list[dict[str, Any]],
    body_layout: str,
    width: int,
    expected: dict[str, Any],
) -> None:
    """並べ方が side のとき、切り替えと左右の本文を置き、本文の幅が足りなければインラインを出す（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1", body="D-1.md", history=entries, seq=1)],
        bodies={"D-1.md": MINIMAP_NOW_BODY},
    )
    load_preview_scripts()
    load_preview_styles()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        OPEN_SIDE_BY_SIDE_PANEL_SCRIPT,
        {"data": data, "point": DIFF_POINT, "bodyLayout": body_layout, "width": width},
    )
    # 検証
    assert result == expected


# 詳細パネルを「インライン」で開いて URL のハッシュを決め、「左右に並べる」を押して、知らせた並べ方とハッシュを返す
PRESS_SIDE_SCRIPT = """async ({data, point, width}) => {
    history.replaceState(null, "", "#keep");
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const calls = [];
    const panel = MindmapPreview.detailPanel({
        id: "D-1",
        index,
        full: false,
        on: {
            open: noop, close: noop, full: noop, back: noop, forward: noop, diagram: noop,
            layout: (...args) => calls.push(args),
        },
        comment: null,
        highlight: null,
        diff: {...point, added: new Set(), changed: new Set(["D-1"])},
        bodyLayout: "inline",
    });
    panel.style.width = `${width}px`;
    document.body.append(panel);
    for (let frame = 0; frame < 4; frame += 1) await new Promise((resolve) => requestAnimationFrame(resolve));
    panel.querySelector('.sbs-switch button[data-layout="side"]').click();
    return {calls, hash: location.hash};
}"""


def test_detail_panel_when_body_layout_changed(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """並べ方のボタンを押すと on.layout を呼ぶ（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1", body="D-1.md", history=[MINIMAP_ENTRY], seq=1)],
        bodies={"D-1.md": MINIMAP_NOW_BODY},
    )
    load_preview_scripts()
    load_preview_styles()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        PRESS_SIDE_SCRIPT, {"data": data, "point": DIFF_POINT, "width": 760}
    )
    # 検証（URL のハッシュは変わらない）
    assert result == {"calls": [["side"]], "hash": "#keep"}


# 値の要素（data-key がキーのパス）の中の見出しの段と、強調の数を調べる
VALUE_HEADING_LEVELS_SCRIPT = (
    OPEN_PANEL_FUNCTION
    + """
async ({data, id, key}) => {
    const panel = await openPanel(data, id);
    const value = panel.querySelector(`[data-key="${key}"]`);
    return {
        found: value !== null,
        headings: value === null ? [] : [...value.querySelectorAll("h1, h2, h3, h4, h5, h6")].map((heading) => ({
            text: (heading.textContent ?? "").trim(),
            tag: heading.tagName.toLowerCase(),
            mdLevel: heading.getAttribute("data-md-level"),
        })),
        strong: value === null ? 0 : value.querySelectorAll("strong").length,
    };
}"""
)


@pytest.mark.parametrize(
    ("item_id", "kinds", "key", "expected"),
    [
        pytest.param(
            "D-1",
            {"decisions": [{"id": "D-1", "lead": "## 背景\n\n背景の段落\n\n### 経緯\n\n経緯の段落\n"}]},
            "lead",
            {
                "found": True,
                "headings": [
                    {"text": "背景", "tag": "h3", "mdLevel": "2"},
                    {"text": "経緯", "tag": "h4", "mdLevel": "3"},
                ],
                "strong": 0,
            },
            id="lead_after_title",
        ),
        pytest.param(
            "D-2",
            {
                "decisions": [
                    {
                        "id": "D-2",
                        "options": [{"key": "A", "content": "# 案\n\n案の段落\n\n## 中身\n\n中身の段落\n"}],
                    }
                ]
            },
            "options[A].content",
            {
                "found": True,
                "headings": [
                    {"text": "案", "tag": "h4", "mdLevel": "1"},
                    {"text": "中身", "tag": "h5", "mdLevel": "2"},
                ],
                "strong": 0,
            },
            id="option_content_in_section",
        ),
        pytest.param(
            "T-1",
            {"tasks": [{"id": "T-1", "reason": "# 手順\n\n手順の段落\n"}]},
            "reason",
            {
                "found": True,
                "headings": [{"text": "手順", "tag": "h3", "mdLevel": "1"}],
                "strong": 0,
            },
            id="task_reason_after_title",
        ),
        pytest.param(
            "D-3",
            {"decisions": [{"id": "D-3", "lead": "**強調**"}]},
            "lead",
            {"found": True, "headings": [], "strong": 1},
            id="no_headings",
        ),
    ],
)
def test_detail_panel_when_value_heading_levels(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
    item_id: str,
    kinds: dict[str, list[dict[str, object]]],
    key: str,
    expected: dict[str, object],
) -> None:
    """文字列の値の見出しの最も上の段を、置く場所の直上の見出しの次の段にし、段の差を保って並べる（正常系）。"""
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
    load_mdmark()
    # 実行
    result = preview_page.evaluate(
        VALUE_HEADING_LEVELS_SCRIPT, {"data": data, "id": item_id, "key": key}
    )
    # 検証
    assert result == expected


# 詳細パネルを差分つきで開き、背景（`lead`）の前の値（`del.df-was`）と今の値（`ins.df-now`）の、
# 計算後の `white-space`・文字が占める行の数（幅を持つ箱の `top` の種類）・語の面の文字・読み上げの文字の置き場所を調べる
OPEN_KEY_NEWLINE_DIFF_PANEL_SCRIPT = """async ({data, point}) => {
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
    const root = panel.querySelector('[data-key="lead"]');
    const was = root.querySelector("del.df-was");
    const now = root.querySelector("ins.df-now");
    const wasWords = [...was.querySelectorAll("span.df-word.df-del")];
    const nowWords = [...now.querySelectorAll("span.df-word.df-add")];
    const lineCount = (elements) => new Set(
        elements.flatMap((element) => [...element.getClientRects()])
            .filter((rect) => rect.width > 0)
            .map((rect) => Math.round(rect.top)),
    ).size;
    return {
        whiteSpace: [getComputedStyle(was).whiteSpace, getComputedStyle(now).whiteSpace],
        lines: {was: lineCount([was]), now: lineCount([now]), nowWords: lineCount(nowWords)},
        words: {
            was: wasWords.map((word) => word.textContent),
            now: nowWords.map((word) => word.textContent),
        },
        reading: [...root.querySelectorAll("span.sr-only")].map((reading) => ({
            text: reading.textContent,
            insideWord: reading.closest("span.df-word") !== null || reading.querySelector("span.df-word") !== null,
        })),
    };
}"""


@pytest.mark.parametrize(
    ("before_lead", "now_lead", "lines", "words_text"),
    [
        pytest.param(
            "要件を決める。\n期限は来週。",
            "要件を決める。\n期限は今週。",
            {"was": 2, "now": 2, "nowWords": 1},
            {"was": "来週", "now": "今週"},
            id="word_after_newline",
        ),
        pytest.param(
            "予定は来週の会議で決める",
            "予定は今週\n明日の会議で決める",
            {"was": 1, "now": 2, "nowWords": 2},
            {"was": "来週", "now": "今週\n明日"},
            id="word_across_newline",
        ),
    ],
)
def test_detail_panel_when_diff_key_newlines(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
    before_lead: str,
    now_lead: str,
    lines: dict[str, int],
    words_text: dict[str, str],
) -> None:
    """キーの差分の前の値と今の値で、改行を改行として出し、改行をまたぐ語の面を行ごとに付ける（正常系）。"""
    # 準備
    history = [{"seq": 1, "at": ENTRY_AT, "before": {"lead": before_lead}}]
    data = make_data(decisions=[make_item("D-1", lead=now_lead, history=history, seq=1)])
    load_preview_scripts()
    load_preview_styles()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        OPEN_KEY_NEWLINE_DIFF_PANEL_SCRIPT, {"data": data, "point": DIFF_POINT}
    )
    # 検証
    # 前の値・今の値は、書かれた改行を残す
    assert set(result["whiteSpace"]) <= {"pre-wrap", "pre-line"}
    # 前の値・今の値と今の値の語の面は、改行の前後の行に分かれて並ぶ
    assert result["lines"] == lines
    # 語の面は、変わった語だけに付く（改行をまたぐ範囲は行ごとの面の文字をつなげる）
    assert "".join(result["words"]["was"]) == words_text["was"]
    assert "".join(result["words"]["now"]) == words_text["now"]
    # 読み上げの文字は、語の面の外にある
    assert result["reading"] == READING_OUTSIDE_WORDS


# 本文の見せ方の既定（列の固定・見出しの固定・折りたたみはオン、しま模様はオフ）
BODY_VIEW_DEFAULT = {"pin": True, "head": True, "stripes": False, "fold": True}

# 見出し「比較」の下に表と段落 12 個を持ち、その後ろに見出し「料金」を持つ本文
BODY_VIEW_BODY = (
    "## 比較\n\n| 列 A | 列 B |\n| --- | --- |\n| D-1 | 今週 |\n\n"
    + "\n\n".join(f"比較の段落 {number}" for number in range(1, 13))
    + "\n\n### 料金\n\n料金の段落\n"
)

# 表の本体の行（5 行目）を書き換えた変えた回
BODY_VIEW_ENTRY = _body_entry(line=5, now=["| D-1 | 今週 |"], before=["| D-1 | 来週 |"])

# 本文のスクロール領域を 200px に抑えて詳細パネルを開き（畳んでから描き直す指定のときは、「比較」を畳んだパネルを外して開き直し）、
# 本文の見せ方と、見出し「料金」の置かれ方を調べる
OPEN_BODY_VIEW_PANEL_SCRIPT = """async ({data, bodyView, point, heading, foldFirst}) => {
    // 単体テストでは雛形の CSS を読まないので、本文のスクロール領域だけ作る
    const style = document.createElement("style");
    style.textContent = ".panel-body { height: 200px; overflow: auto; }";
    document.head.append(style);
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const open = async (slug) => {
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
                heading: noop,
                layout: noop,
            },
            comment: null,
            heading: slug,
            diff: point === null ? null : {...point, added: new Set(), changed: new Set(["A-1"])},
            bodyLayout: "inline",
            bodyView,
        });
        document.body.append(panel);
        // 描き直しと見出しへのスクロールは、文書に入った後に置かれる
        for (let frame = 0; frame < 3; frame += 1) {
            await new Promise((resolve) => requestAnimationFrame(resolve));
        }
        return panel;
    };
    let panel = await open(null);
    if (foldFirst) {
        panel.querySelector('[data-heading="比較"] button.md-fold').click();
        panel.remove();
        panel = await open(heading);
    }
    const table = panel.querySelector("table");
    const target = panel.querySelector('[data-heading="料金"]');
    const area = panel.querySelector(".panel-body").getBoundingClientRect();
    const rect = target.getBoundingClientRect();
    return {
        arrows: [...panel.querySelectorAll("button.md-fold")].map(
            (button) => button.closest("[data-heading]")?.getAttribute("data-heading") ?? null,
        ),
        framed: table.closest(".md-table-frame") !== null,
        headStick: table.classList.contains("md-head-stick"),
        stripes: table.classList.contains("md-stripes"),
        sectionOpen: target.closest(".md-section-body[hidden]") === null,
        inView: rect.top >= area.top - 1 && rect.bottom <= area.bottom + 1,
    };
}"""


@pytest.mark.parametrize(
    ("body_view", "with_diff", "fold_first", "expected"),
    [
        pytest.param(
            BODY_VIEW_DEFAULT,
            False,
            False,
            {"arrows": ["比較", "料金"], "framed": True, "headStick": True, "stripes": False},
            id="default",
        ),
        pytest.param(
            {**BODY_VIEW_DEFAULT, "stripes": True},
            False,
            False,
            {"framed": True, "stripes": True},
            id="stripes",
        ),
        pytest.param(
            BODY_VIEW_DEFAULT,
            True,
            False,
            {"arrows": [], "framed": True},
            id="body_diff_has_no_fold",
        ),
        pytest.param(
            BODY_VIEW_DEFAULT,
            False,
            True,
            {"sectionOpen": True, "inView": True},
            id="reveal_heading_after_fold",
        ),
    ],
)
def test_detail_panel_when_body_view(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
    body_view: dict[str, bool],
    with_diff: bool,
    fold_first: bool,
    expected: dict[str, Any],
) -> None:
    """本文に見せ方を当て、本文の差分には開閉を置かず、畳んだ見出しへ移るときは開く（正常系）。"""
    # 準備
    entries = [BODY_VIEW_ENTRY] if with_diff else []
    data = make_data(
        docs=[make_item("A-1", **({"history": entries, "seq": 1} if entries else {}))],
        bodies={"A-1.md": BODY_VIEW_BODY},
    )
    load_preview_scripts()
    load_preview_styles()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        OPEN_BODY_VIEW_PANEL_SCRIPT,
        {
            "data": data,
            "bodyView": body_view,
            "point": DIFF_POINT if with_diff else None,
            "heading": "料金",
            "foldFirst": fold_first,
        },
    )
    # 検証
    assert {key: result[key] for key in expected} == expected


@pytest.mark.parametrize(
    ("viewport", "map_view", "expected"),
    [
        pytest.param(1280, False, 880, id="side_1280"),
        pytest.param(1100, False, 700, id="side_1100"),
        pytest.param(1099, False, 939, id="overlap_1099"),
        pytest.param(1000, False, 840, id="overlap_1000"),
        pytest.param(1000, True, 600, id="map_1000"),
        pytest.param(901, True, 501, id="map_901"),
    ],
)
def test_panel_width_max(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    viewport: int,
    map_view: bool,
    expected: int,
) -> None:
    """本文を寄せる幅は本文に残す幅、重ねる幅は左に残す幅で上限を決める（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        "({viewport, mapView}) => MindmapPreview.panelWidthMax({viewport, mapView})",
        {"viewport": viewport, "mapView": map_view},
    )
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    ("width", "expected"),
    [
        pytest.param(640, 640, id="inside"),
        pytest.param(300, 480, id="below_min"),
        pytest.param(1000, 880, id="above_max"),
        pytest.param(700.6, 701, id="rounded"),
    ],
)
def test_clamp_panel_width(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    width: float,
    expected: int,
) -> None:
    """下限と上限の間に収める（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        "({width, max}) => MindmapPreview.clampPanelWidth({width, max})",
        {"width": width, "max": 880},
    )
    # 検証
    assert result == expected


# 幅の区切りを調べるときの表示の幅・高さと、狭めた表示の幅
RESIZER_VIEWPORT = {"width": 1280, "height": 720}
NARROW_VIEWPORT = {"width": 1000, "height": 720}

# 区切りを押して左へ 100px 動かす位置（区切りは画面の右寄りに固定して置く）
DRAG_Y = 200
DRAG_FROM_X = 1010
DRAG_TO_X = 910

# 区切りを描いて文書に置き、変えた幅を知らせる値を window に並べる
MOUNT_RESIZER_SCRIPT = """({stored}) => {
    window.resizerCalls = [];
    const resizer = MindmapPreview.panelResizer({
        stored,
        mapView: () => false,
        onChange: (width) => window.resizerCalls.push(width),
    });
    // ドラッグで押せるように、画面の右寄りに大きさを持たせて置く
    Object.assign(resizer.style, {
        position: "fixed", top: "100px", left: "1000px", width: "24px", height: "300px",
    });
    document.body.append(resizer);
}"""

# 区切りの今の幅と、変えた幅を知らせた値を調べる
READ_RESIZER_SCRIPT = """() => {
    const resizer = document.querySelector('[role="separator"]');
    const root = getComputedStyle(document.documentElement);
    return {
        width: parseFloat(root.getPropertyValue("--panel-w")),
        min: Number(resizer.getAttribute("aria-valuemin")),
        max: Number(resizer.getAttribute("aria-valuemax")),
        now: Number(resizer.getAttribute("aria-valuenow")),
        calls: window.resizerCalls,
    };
}"""

# 区切りにフォーカスして、← → Home End を順に押した後の幅を調べる
PRESS_KEYS_SCRIPT = """() => {
    const resizer = document.querySelector('[role="separator"]');
    resizer.focus();
    const widths = [];
    for (const key of ["ArrowLeft", "ArrowRight", "Home", "End"]) {
        resizer.dispatchEvent(new KeyboardEvent("keydown", {key, bubbles: true}));
        widths.push(Number(resizer.getAttribute("aria-valuenow")));
    }
    return {widths, calls: window.resizerCalls};
}"""


@pytest.mark.parametrize(
    ("stored", "opened", "dragged"),
    [
        pytest.param(None, 640, 740, id="default"),
        pytest.param(768, 768, 868, id="stored"),
        pytest.param(1000, 880, 880, id="stored_above_max"),
    ],
)
def test_panel_resizer(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    stored: int | None,
    opened: int,
    dragged: int,
) -> None:
    """残した幅を上限に収めて当て、ドラッグで幅を変えて知らせる（正常系）。"""
    # 準備
    preview_page.set_viewport_size(RESIZER_VIEWPORT)
    load_preview_scripts()
    preview_page.evaluate(MOUNT_RESIZER_SCRIPT, {"stored": stored})
    # 実行
    before = preview_page.evaluate(READ_RESIZER_SCRIPT)
    preview_page.mouse.move(DRAG_FROM_X, DRAG_Y)
    preview_page.mouse.down()
    preview_page.mouse.move(DRAG_TO_X, DRAG_Y)
    preview_page.mouse.up()
    after = preview_page.evaluate(READ_RESIZER_SCRIPT)
    # 検証
    assert before == {"width": opened, "min": 480, "max": 880, "now": opened, "calls": []}
    assert (after["width"], after["now"]) == (dragged, dragged)
    assert after["calls"][-1] == dragged


def test_panel_resizer_keys(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """矢印キーで刻み、Home・End で下限・上限にする（正常系）。"""
    # 準備
    preview_page.set_viewport_size(RESIZER_VIEWPORT)
    load_preview_scripts()
    preview_page.evaluate(MOUNT_RESIZER_SCRIPT, {"stored": 640})
    # 実行
    result = preview_page.evaluate(PRESS_KEYS_SCRIPT)
    # 検証
    assert result == {"widths": [656, 640, 480, 880], "calls": [656, 640, 480, 880]}


def test_panel_resizer_when_window_resized(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """窓の幅が変わると残した幅を収め直し、広げ直すと残した幅に戻す（正常系）。"""
    # 準備
    preview_page.set_viewport_size(RESIZER_VIEWPORT)
    load_preview_scripts()
    preview_page.evaluate(MOUNT_RESIZER_SCRIPT, {"stored": 880})
    resizer = preview_page.locator('[role="separator"]')
    # 実行
    preview_page.set_viewport_size(NARROW_VIEWPORT)
    expect(resizer).to_have_attribute("aria-valuenow", "840")
    narrowed = preview_page.evaluate(READ_RESIZER_SCRIPT)
    preview_page.set_viewport_size(RESIZER_VIEWPORT)
    expect(resizer).to_have_attribute("aria-valuenow", "880")
    widened = preview_page.evaluate(READ_RESIZER_SCRIPT)
    # 検証
    assert (narrowed["width"], narrowed["max"], narrowed["now"]) == (840, 840, 840)
    assert widened["width"] == 880
    assert (narrowed["calls"], widened["calls"]) == ([], [])


# 埋め込んだ HTML の範囲を持つ資料 A-1 の本文（段落・範囲 1 つ・範囲の外の段落）
EXPORT_BODY = (
    "範囲の外の文\n\n"
    "<!-- html -->\n```html\n<p>範囲の中の文</p>\n```\n<!-- /html -->\n\n"
    "後ろの文\n"
)

# 資料 A-1 の詳細パネルを開き、エクスポートの入口が読む表示に出るかを調べる。
# shared は配る書き出し（comment と edit が null）、editing は編集の表示
OPEN_EXPORT_PANEL_SCRIPT = """async ({data, id, full, shared, editing}) => {
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const item = index.byId.get(id).item;
    const comment = shared ? null : {
        form: {
            target: id,
            on: {input: noop, save: noop, unquote: noop, copy: noop, focus: noop, blur: noop},
        },
        reviews: [],
        edit: {
            removed: [], editing: null, editingIn: "detail", editError: null, editBody: null,
            on: {edit: noop, saveEdit: noop, cancelEdit: noop, remove: noop, restore: noop},
        },
    };
    const edit = shared ? null : {
        editing,
        marks: {},
        form: {
            kind: "docs", item, settings: data.settings, marks: {}, removing: false,
            removedOptions: [], blocked: {}, referrers: [], errors: {}, usedTags: [],
            on: {change: noop, remove: noop, cancelRemove: noop},
        },
        onToggle: noop,
    };
    const panel = MindmapPreview.detailPanel({
        id,
        index,
        full,
        on: {open: noop, close: noop, full: noop, back: noop, forward: noop, diagram: noop, heading: noop},
        comment,
        highlight: null,
        diff: null,
        edit,
    });
    document.body.append(panel);
    if (full) panel.showModal(); else panel.classList.add("open");
    await new Promise((resolve) => requestAnimationFrame(resolve));
}"""


def _export_data(make_data: MakeData, make_item: MakeItem) -> dict[str, Any]:
    """本文が Markdown の資料 A-1・本文が HTML の資料 A-2・検討事項 D-1 を持つ埋め込みのデータを返す。"""
    return make_data(
        decisions=[make_item("D-1")],
        docs=[make_item("A-1", title="エクスポートする資料"), make_item("A-2", body="A-2.html")],
        bodies={"A-1.md": EXPORT_BODY, "A-2.html": "<p>HTML の本文</p>"},
    )


@pytest.mark.parametrize(
    ("item_id", "shared", "editing", "expected"),
    [
        pytest.param("A-1", False, False, 1, id="markdown_doc"),
        pytest.param("A-2", False, False, 0, id="html_doc"),
        pytest.param("D-1", False, False, 0, id="decision"),
        pytest.param("A-1", False, True, 0, id="editing"),
        pytest.param("A-1", True, False, 1, id="shared_export"),
    ],
)
def test_detail_panel_when_export_entry(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
    item_id: str,
    shared: bool,
    editing: bool,
    expected: int,
) -> None:
    """本文が Markdown の資料にだけエクスポートの入口を置く（正常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    load_mdmark()
    data = _export_data(make_data, make_item)
    # 実行
    preview_page.evaluate(
        OPEN_EXPORT_PANEL_SCRIPT,
        {"data": data, "id": item_id, "full": False, "shared": shared, "editing": editing},
    )
    entries = preview_page.get_by_role("button", name="エクスポート", exact=True)
    # 検証
    expect(entries).to_have_count(expected)
    if expected == 1:
        # 全画面表示のボタンより前（左）に置く
        assert preview_page.evaluate(
            """() => {
                const entry = [...document.querySelectorAll("button")].find(
                    (button) => button.getAttribute("aria-label") === "エクスポート",
                );
                const full = document.querySelector('button[aria-label="全画面表示"]');
                return Boolean(entry.compareDocumentPosition(full) & Node.DOCUMENT_POSITION_FOLLOWING);
            }"""
        )


def test_detail_panel_when_export_html(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_mdmark: LoadMdmark,
    put_mdmark_css: PutMdmarkCss,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """HTML でエクスポートすると 1 枚の HTML を保存させ、メニューを閉じて入口へフォーカスを戻す（正常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    load_mdmark()
    put_mdmark_css()
    data = _export_data(make_data, make_item)
    preview_page.evaluate(
        OPEN_EXPORT_PANEL_SCRIPT,
        {"data": data, "id": "A-1", "full": False, "shared": False, "editing": False},
    )
    entry = preview_page.get_by_role("button", name="エクスポート", exact=True)
    entry.click()
    # 実行
    with preview_page.expect_download() as download_info:
        preview_page.get_by_role("button", name="HTML でエクスポート").click()
    download = download_info.value
    exported = Path(download.path()).read_text(encoding="utf-8")
    # 検証
    assert download.suggested_filename == "A-1.html"
    assert 'id="doc-mdmark"' in exported
    assert "エクスポートする資料" in exported
    expect(preview_page.get_by_role("dialog", name="エクスポート")).to_be_hidden()
    expect(entry).to_have_attribute("aria-expanded", "false")
    expect(entry).to_be_focused()


def test_detail_panel_when_export_markdown(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """Markdown でエクスポートすると警告を挙げ、埋め込んだ HTML を除いた本文を保存させる（正常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    load_mdmark()
    data = _export_data(make_data, make_item)
    preview_page.evaluate(
        OPEN_EXPORT_PANEL_SCRIPT,
        {"data": data, "id": "A-1", "full": False, "shared": False, "editing": False},
    )
    downloads: list[Any] = []
    preview_page.on("download", lambda download: downloads.append(download))
    preview_page.get_by_role("button", name="エクスポート", exact=True).click()
    # 実行
    preview_page.get_by_role("button", name="Markdown でエクスポート").click()
    warned = preview_page.get_by_role("button", name="エクスポート", exact=True).count()
    downloads_after_warning = len(downloads)
    preview_page.get_by_role("button", name="戻る", exact=True).click()
    focused_after_back = preview_page.evaluate("() => document.activeElement?.textContent ?? ''")
    preview_page.get_by_role("button", name="Markdown でエクスポート").click()
    with preview_page.expect_download() as download_info:
        preview_page.get_by_role("dialog").get_by_role("button", name="エクスポート", exact=True).click()
    download = download_info.value
    exported = Path(download.path()).read_text(encoding="utf-8")
    # 検証
    # 警告の間は保存されず、警告の「エクスポート」が押せる
    assert downloads_after_warning == 0
    assert warned >= 1
    # 「戻る」でフォーカスが「Markdown でエクスポート」へ戻る
    assert "Markdown でエクスポート" in focused_after_back
    assert download.suggested_filename == "A-1.md"
    assert "範囲の外の文" in exported
    assert "範囲の中の文" not in exported
    assert "<!-- html -->" not in exported


def test_detail_panel_when_export_retry(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_mdmark: LoadMdmark,
    put_mdmark_css: PutMdmarkCss,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """mdmark の中身を取れないときはエラーを出し、再試行でやり直す（異常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    load_mdmark()
    # 最初の CSS の要求だけを失敗させ、2 回目からは配布物の中身を返す
    put_mdmark_css(status=404)
    data = _export_data(make_data, make_item)
    preview_page.evaluate(
        OPEN_EXPORT_PANEL_SCRIPT,
        {"data": data, "id": "A-1", "full": False, "shared": False, "editing": False},
    )
    preview_page.get_by_role("button", name="エクスポート", exact=True).click()
    preview_page.get_by_role("button", name="HTML でエクスポート").click()
    alert = preview_page.get_by_role("alert")
    expect(alert).to_be_visible()
    # 実行
    # 後に足した経路が先に当たるので、CSS の経路を足し直せば 2 回目から読める
    put_mdmark_css()
    with preview_page.expect_download() as download_info:
        preview_page.get_by_role("button", name="再試行").click()
    # 検証
    assert download_info.value.suggested_filename == "A-1.html"
    expect(preview_page.get_by_role("dialog", name="エクスポート")).to_be_hidden()


# 範囲 2 つを持つ今の本文（2 つ目の範囲の 1 つ目の段落を書き換え、末尾に段落を足した後）
EMBEDDED_DIFF_NOW = (
    "範囲の外の文\n\n"
    "<!-- html -->\n```html\n<p>一つ目の範囲の段落</p>\n```\n<!-- /html -->\n\n"
    "<!-- html -->\n```html\n<p>書き換え後</p>\n<p>二つ目の範囲の段落</p>\n<p>足した段落</p>\n```\n<!-- /html -->\n"
)

# 2 つ目の範囲（11 行目から）の書き換え前と、足す前の段落の並び
EMBEDDED_DIFF_ENTRY = _body_entry(
    line=11,
    now=["<p>書き換え後</p>", "<p>二つ目の範囲の段落</p>", "<p>足した段落</p>"],
    before=["<p>書き換え前</p>", "<p>二つ目の範囲の段落</p>"],
)

# 差分つきで資料 A-1 の詳細パネルを開く
OPEN_EMBEDDED_DIFF_PANEL_SCRIPT = """async ({data, point}) => {
    const index = MindmapPreview.buildIndex(data);
    const noop = () => {};
    const panel = MindmapPreview.detailPanel({
        id: "A-1",
        index,
        full: false,
        on: {open: noop, close: noop, full: noop, back: noop, forward: noop, diagram: noop, heading: noop},
        comment: null,
        highlight: null,
        diff: {...point, added: new Set(), changed: new Set(["A-1"])},
    });
    document.body.append(panel);
    panel.classList.add("open");
    await new Promise((resolve) => requestAnimationFrame(resolve));
}"""


def test_detail_panel_when_embedded_html_diff(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_library: LoadLibrary,
    load_mdmark: LoadMdmark,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """変わった埋め込んだ HTML の範囲だけを HTML の本文の差分に置き換える（正常系）。"""
    # 準備
    data = make_data(
        docs=[make_item("A-1", body="A-1.md", history=[EMBEDDED_DIFF_ENTRY])],
        bodies={"A-1.md": EMBEDDED_DIFF_NOW},
    )
    load_preview_scripts()
    load_preview_styles()
    load_library("marked")
    load_mdmark()
    load_library("jsdiff")
    preview_page.evaluate(OPEN_EMBEDDED_DIFF_PANEL_SCRIPT, {"data": data, "point": DIFF_POINT})
    panel = preview_page.locator("aside.panel")
    # 実行
    raw_pressed = panel.get_by_role("button", name="原文の差分").get_attribute("aria-pressed")
    unchanged_range_count = panel.locator(".md > .mdmark-html:visible").count()
    panel.get_by_role("button", name="描いた結果（変更後）").click()
    after = panel.evaluate(
        """(panel) => ({
            changed: [...panel.querySelectorAll('[data-df="chg"]')].map((element) => element.textContent.trim()),
            added: [...panel.querySelectorAll('[data-df="add"]')].map((element) => element.textContent.trim()),
            lineMarksInRanges: panel.querySelectorAll(".mdmark-html ins.df-blk, .mdmark-html del.df-blk").length,
        })"""
    )
    # 検証
    # 1 つ目の範囲はそのまま描かれ、2 つ目は差分に置き換わって「原文の差分」を選んだ状態で開く
    assert unchanged_range_count == 1
    assert raw_pressed == "true"
    expect(panel.get_by_text("埋め込んだ HTML")).to_be_visible()
    # 変更後は、書き換えた段落に変わったマーカー、足した段落に足したマーカーが付く
    assert after == {"changed": ["書き換え後"], "added": ["足した段落"], "lineMarksInRanges": 0}
