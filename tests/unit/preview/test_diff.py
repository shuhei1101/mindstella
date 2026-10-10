"""core/diff.ts（選んだ時点の印・前の版の組み立て・行の差分・図の要素の突き合わせ）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadLibrary, LoadPreviewScripts

# 差分の時点を決める記録の日時（V-1 より後・V-2 より前の「前回開いてから」の始まりを含む）
FIRST_SET_AT = "2026-10-01T09:00:00+00:00"
SINCE = "2026-10-02T00:00:00+00:00"
SECOND_SET_AT = "2026-10-03T09:00:00+00:00"

# 消した項目を持つまとまりの日時（V-1 より後・「前回開いてから」の始まりより前）
REMOVED_SET_AT = "2026-10-01T18:00:00+00:00"

# 変更履歴の 1 回分に入れる日時
ENTRY_AT = "2026-10-03T09:00:00+00:00"

# 大きな書き換えの行数と、打ち切りを確かめる呼び出しの上限（ミリ秒）
LARGE_LINE_COUNT = 5000
TIMEOUT_LIMIT_MS = 200

# 1・3・5 行目に段落を持つ本文と、3 行目・5 行目の段落を消した後の本文
THREE_PARAGRAPHS = "1 行目の段落\n\n3 行目の段落\n\n5 行目の段落\n"
WITHOUT_MIDDLE_PARAGRAPH = "1 行目の段落\n\n5 行目の段落\n"
WITHOUT_LAST_PARAGRAPH = "1 行目の段落\n\n3 行目の段落\n"

# 見出し・区切り・3 行の表と、その 2 行目を消した後の表
TABLE_HEADER_LINES = ["| 列 A | 列 B |", "| --- | --- |"]
TABLE_THREE_ROWS = "\n".join([*TABLE_HEADER_LINES, "| 1 | 2 |", "| 3 | 4 |", "| 5 | 6 |", ""])
TABLE_WITHOUT_SECOND_ROW = "\n".join([*TABLE_HEADER_LINES, "| 1 | 2 |", "| 5 | 6 |", ""])

# 図の差分を確かめる前後の記法（足したもの・文字を変えたもの・消したものが 1 つずつ）
FLOWCHART_BEFORE = "flowchart TD\n  A[開始]\n  B_1[処理]\n  C[終了]\n"
FLOWCHART_AFTER = "flowchart TD\n  A[開始]\n  B_1[処理を変えた]\n  D[追加]\n"
SEQUENCE_BEFORE = (
    "sequenceDiagram\n  participant A\n  participant B\n"
    "  A->>B: 依頼\n  B-->>A: 応答\n  A->>B: 確認\n  B-->>A: 完了\n"
)
SEQUENCE_AFTER = (
    "sequenceDiagram\n  participant A\n  participant B\n"
    "  A->>B: 依頼を変えた\n  B-->>A: 応答\n  B-->>A: 完了\n  A->>B: 追加\n"
)
CLASS_BEFORE = "classDiagram\n  class Customer\n  class Order {\n    +place()\n  }\n  class Item\n"
CLASS_AFTER = (
    "classDiagram\n  class Customer\n  class Order {\n    +cancel()\n  }\n  class Invoice\n"
)
ER_BEFORE = (
    "erDiagram\n  CUSTOMER {\n    string name\n  }\n  ORDER {\n    int id\n  }\n"
    "  ITEM {\n    int code\n  }\n"
)
ER_AFTER = (
    "erDiagram\n  CUSTOMER {\n    string title\n  }\n  ORDER {\n    int id\n  }\n"
    "  INVOICE {\n    int number\n  }\n"
)
STATE_BEFORE = "stateDiagram-v2\n  s1 : 待機\n  s2 : 実行\n  s3 : 終了\n"
STATE_AFTER = "stateDiagram-v2\n  s1 : 待機\n  s2 : 実行中\n  s4 : 追加\n"

# 色付けの対象外の種類（gantt）の前後の記法
GANTT_BEFORE = "gantt\n  dateFormat YYYY-MM-DD\n  section 準備\n  設計 :a1, 2026-10-01, 3d\n"
GANTT_AFTER = (
    "gantt\n  dateFormat YYYY-MM-DD\n  section 準備\n  設計 :a1, 2026-10-01, 3d\n"
    "  実装 :a2, after a1, 5d\n"
)

# 前後の記法を mermaid で描き、図の差分を取って、要素の文字の並びにして返す
DIFF_DIAGRAM_SCRIPT = """async ({type, before, after}) => {
    mermaid.initialize({startOnLoad: false});
    const render = async (id, source, left) => {
        const {svg} = await mermaid.render(id, source);
        const holder = document.createElement("div");
        holder.style.position = "absolute";
        holder.style.left = left;
        holder.innerHTML = svg;
        document.body.append(holder);
        return holder.querySelector("svg");
    };
    const beforeSvg = await render("diff-before", before, "-10000px");
    const afterSvg = await render("diff-after", after, "0px");
    const diff = MindmapPreview.diffDiagram(type, beforeSvg, afterSvg);
    if (diff === null) return null;
    const text = (element) => (element.textContent ?? "").replace(/\\s+/g, " ").trim();
    return {
        added: diff.added.map(text),
        changed: diff.changed.map(text),
        removed: diff.removed,
    };
}"""


# 書き方を変えないノードと辺（`<br>`・Markdown・文字参照・アイコン・`:::class`・辺のラベル・ラベルなし）を持つ flowchart
NOTATION_BEFORE = (
    "flowchart TD\n"
    '  A["一行目<br>二行目"] --> B["`**太字** の文字`"]\n'
    '  B -->|"はい<br>そう"| C["引用 &quot;記号&quot; &amp; &lt;b&gt;"]\n'
    '  C --> D["fa:fa-user 人"]\n'
    "  D --> E[ノード]:::hot\n"
    "  E --> F[次]\n"
    "  classDef hot fill:#f99\n"
)
# 上の記法のうち、別のノード F の文字だけを変える
NOTATION_AFTER = NOTATION_BEFORE.replace("F[次]", "F[次を変えた]")

# 同じ端点（A → B）の辺を 2 本持つ flowchart と、片方の辺のラベルだけを変えた後
TWO_EDGES_BEFORE = "flowchart TD\n  A[判定] -->|はい| B[次]\n  A -->|いいえ| B\n"
TWO_EDGES_FIRST_CHANGED = "flowchart TD\n  A[判定] -->|はい!| B[次]\n  A -->|いいえ| B\n"
TWO_EDGES_SECOND_CHANGED = "flowchart TD\n  A[判定] -->|はい| B[次]\n  A -->|いいえ!| B\n"

# id に `_` を含むノード（my_node）の辺を持つ flowchart と、別のノードの文字だけを変えた後
UNDERSCORE_NODE_BEFORE = "flowchart TD\n  my_node --> B[次]\n  B --> C[終]\n"
UNDERSCORE_NODE_AFTER = "flowchart TD\n  my_node --> B[次]\n  B --> C[終を変えた]\n"

# id を付けた辺（A e1@--> B）を持つ flowchart と、別のノードの文字だけを変えた後
EDGE_ID_BEFORE = "flowchart TD\n  A e1@--> B[次]\n  B --> C[終]\n"
EDGE_ID_AFTER = "flowchart TD\n  A e1@--> B[次]\n  B --> C[終を変えた]\n"

# ノードの文字を変えた subgraph の前後
SUBGRAPH_BEFORE = "flowchart TD\n  subgraph S[枠]\n    A[中] --> B[外へ]\n  end\n  B --> C[先]\n"
SUBGRAPH_AFTER = (
    "flowchart TD\n  subgraph S[枠]\n    A[中を変えた] --> B[外へ]\n  end\n  B --> C[先]\n"
)

# 辺とノードを足し消した前後（B → C を消して B → D を足す）
EDGE_SWAP_BEFORE = "flowchart LR\n  A --> B --> C\n"
EDGE_SWAP_AFTER = "flowchart LR\n  A --> B --> D\n"

# 形の違うノードの文字を変えた前後
SHAPES_BEFORE = "flowchart TD\n  A((丸)) --> B{判定}\n  B --> C[(DB)]\n"
SHAPES_AFTER = "flowchart TD\n  A((丸い)) --> B{判定}\n  B --> C[(DB)]\n"

# `graph` で始まる図の前後
GRAPH_BEFORE = "graph LR\n  A[一] --> B[二]\n"
GRAPH_AFTER = "graph LR\n  A[一] --> B[二を変えた]\n"

# Markdown のラベルと `<br>` のラベルのノードを消した前後
REMOVED_LABELS_BEFORE = 'flowchart TD\n  A[残す]\n  B["`**消す** 方`"]\n  C["上段<br>下段"]\n'
REMOVED_LABELS_AFTER = "flowchart TD\n  A[残す]\n"

# 書きかけで解析できない flowchart（`A -->` で終わる）
UNFINISHED_FLOWCHART = "flowchart TD\n  A[開始] -->\n"

# 前の版が flowchart でない組（今の版は flowchart）の前後
SEQUENCE_TO_FLOWCHART_BEFORE = "sequenceDiagram\n  A->>B: 依頼\n"
SEQUENCE_TO_FLOWCHART_AFTER = "flowchart TD\n  A[開始] --> B[終了]\n"

# 前の版を描いて `diffDiagram` で突き合わせた結果と、前後の記法から `diffDiagramFromSource` で突き合わせた結果を、
# 今の版の SVG の中の要素の位置と文字に直して返す（位置は同じ今の版の SVG から数える）
DIFF_FROM_SOURCE_SCRIPT = """async ({type, before, after}) => {
    const afterHolder = document.createElement("div");
    afterHolder.style.cssText = "position:absolute;left:0;width:1200px";
    document.body.append(afterHolder);
    const afterSvg = await MindmapPreview.renderDiagramSvg(after);
    afterHolder.append(afterSvg);
    const beforeHolder = document.createElement("div");
    beforeHolder.style.cssText = "position:absolute;left:-10000px;width:1200px";
    document.body.append(beforeHolder);
    const beforeSvg = await MindmapPreview.renderDiagramSvg(before);
    beforeHolder.append(beforeSvg);
    const all = [...afterSvg.querySelectorAll("*")];
    const text = (element) => (element.textContent ?? "").replace(/\\s+/g, " ").trim();
    const marks = (elements) => elements
        .map((element) => [all.indexOf(element), text(element)])
        .sort((left, right) => left[0] - right[0]);
    const shape = (diff) => diff === null ? null : {
        added: marks(diff.added),
        changed: marks(diff.changed),
        removed: [...diff.removed].sort(),
    };
    const rendered = shape(MindmapPreview.diffDiagram(type, beforeSvg, afterSvg));
    const parsed = shape(await MindmapPreview.diffDiagramFromSource(type, before, after, afterSvg));
    const texts = (pairs) => pairs.map(([, name]) => name);
    return {
        rendered,
        parsed,
        renderedTexts: {
            added: texts(rendered.added),
            changed: texts(rendered.changed),
            removed: rendered.removed,
        },
    };
}"""

# 前後の記法で `diffDiagramFromSource` を呼び、`null` を返したか例外を投げたかだけを返す
DIFF_FROM_SOURCE_RESULT_SCRIPT = """async ({type, before, after}) => {
    const holder = document.createElement("div");
    document.body.append(holder);
    const afterSvg = await MindmapPreview.renderDiagramSvg(after);
    holder.append(afterSvg);
    try {
        const diff = await MindmapPreview.diffDiagramFromSource(type, before, after, afterSvg);
        return {threw: false, isNull: diff === null};
    } catch (error) {
        return {threw: true, isNull: false};
    }
}"""

# 前後の記法で `diffDiagramFromSource` を呼び、消したノードの名前だけを並べ替えて返す
DIFF_FROM_SOURCE_REMOVED_SCRIPT = """async ({type, before, after}) => {
    const holder = document.createElement("div");
    document.body.append(holder);
    const afterSvg = await MindmapPreview.renderDiagramSvg(after);
    holder.append(afterSvg);
    const diff = await MindmapPreview.diffDiagramFromSource(type, before, after, afterSvg);
    return diff === null ? null : [...diff.removed].sort();
}"""


def _lines_of(prefix: str) -> str:
    """全ての行が prefix で始まり、行ごとに違う 5000 行の本文を作る。"""
    return "\n".join(f"{prefix} {index}" for index in range(LARGE_LINE_COUNT)) + "\n"


@pytest.mark.parametrize(
    ("sel", "expected"),
    [
        pytest.param(
            "V-1",
            {"added": [], "changed": ["A-1"], "fromSeq": 0, "untilSeq": 1},
            id="old_set",
        ),
        pytest.param(
            "since",
            {"added": ["D-6"], "changed": ["D-3"], "fromSeq": 1, "untilSeq": None},
            id="since",
        ),
    ],
)
def test_resolve_diff_point(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    sel: str,
    expected: dict[str, Any],
) -> None:
    """古いまとまりと「前回開いてから」で印と範囲が分かれる（正常系）。"""
    # 準備
    load_preview_scripts()
    changes = {
        "last_seq": 2,
        "sets": [
            {
                "id": "V-2",
                "at": SECOND_SET_AT,
                "summary": "決める",
                "until_seq": 2,
                "added": ["D-6"],
                "changed": ["D-3"],
            },
            {
                "id": "V-1",
                "at": FIRST_SET_AT,
                "summary": "最初",
                "until_seq": 1,
                "added": [],
                "changed": ["A-1"],
            },
        ],
        "pending": {"added": [], "changed": []},
    }
    # 実行
    result = preview_page.evaluate(
        """([changes, sel, since]) => {
            const point = MindmapPreview.resolveDiffPoint(changes, sel, since);
            return {
                added: [...point.added].sort(),
                changed: [...point.changed].sort(),
                fromSeq: point.fromSeq,
                untilSeq: point.untilSeq,
            };
        }""",
        [changes, sel, SINCE],
    )
    # 検証
    assert result == expected


# 消した項目を持つ記録の `changes`（新しい順）。V-1 と V-3 は `removed` を持たない
REMOVED_CHANGES = {
    "last_seq": 4,
    "sets": [
        {
            "id": "V-4",
            "at": SECOND_SET_AT,
            "summary": "消す",
            "until_seq": 4,
            "added": [],
            "changed": [],
            "removed": [{"id": "N-7", "kind": "note", "title": "足してすぐ消したメモ"}],
        },
        {
            "id": "V-3",
            "at": SECOND_SET_AT,
            "summary": "足す",
            "until_seq": 3,
            "added": ["N-7"],
            "changed": [],
        },
        {
            "id": "V-2",
            "at": REMOVED_SET_AT,
            "summary": "変えて消す",
            "until_seq": 2,
            "added": [],
            "changed": ["R-1"],
            "removed": [{"id": "N-6", "kind": "note", "title": "消したメモ"}],
        },
        {
            "id": "V-1",
            "at": FIRST_SET_AT,
            "summary": "最初",
            "until_seq": 1,
            "added": [],
            "changed": ["A-1"],
        },
    ],
    "pending": {"added": [], "changed": []},
}


@pytest.mark.parametrize(
    ("sel", "expected"),
    [
        pytest.param(
            "V-2",
            {
                "added": [],
                "changed": ["R-1"],
                "removed": [{"id": "N-6", "kind": "note", "title": "消したメモ"}],
            },
            id="set_with_removed",
        ),
        pytest.param(
            "since",
            {
                "added": [],
                "changed": [],
                "removed": [{"id": "N-7", "kind": "note", "title": "足してすぐ消したメモ"}],
            },
            id="since_added_then_removed",
        ),
    ],
)
def test_resolve_diff_point_when_removed(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    sel: str,
    expected: dict[str, Any],
) -> None:
    """消した項目を持ち、合わせた範囲で足して消した項目は新規にしない（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """([changes, sel, since]) => {
            const point = MindmapPreview.resolveDiffPoint(changes, sel, since);
            return {
                added: [...point.added].sort(),
                changed: [...point.changed].sort(),
                removed: [...point.removed.values()].map(({id, kind, title}) => ({id, kind, title})),
            };
        }""",
        [REMOVED_CHANGES, sel, SINCE],
    )
    # 検証
    assert result == expected


def test_resolve_diff_point_when_pending_removed_only(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """消した項目だけのまだまとめていない変更も時点になる（正常系）。"""
    # 準備
    load_preview_scripts()
    changes = {
        "last_seq": 1,
        "sets": [],
        "pending": {
            "added": [],
            "changed": [],
            "removed": [{"id": "N-2", "kind": "note", "title": "消したメモ"}],
        },
    }
    # 実行
    result = preview_page.evaluate(
        """([changes, since]) => {
            const point = MindmapPreview.resolveDiffPoint(changes, "pending", since);
            if (point === null) return null;
            return {
                added: [...point.added],
                changed: [...point.changed],
                removed: [...point.removed.values()].map(({id, kind, title}) => ({id, kind, title})),
            };
        }""",
        [changes, SINCE],
    )
    # 検証
    assert result == {
        "added": [],
        "changed": [],
        "removed": [{"id": "N-2", "kind": "note", "title": "消したメモ"}],
    }


@pytest.mark.parametrize(
    ("kind", "point", "expected_ids"),
    [
        pytest.param(
            "notes",
            {
                "removed": [
                    {"id": "N-10", "kind": "note", "title": "十番目のメモ"},
                    {"id": "D-53", "kind": "decision", "title": "消した検討事項"},
                    {"id": "N-6", "kind": "note", "title": "六番目のメモ"},
                ]
            },
            ["N-6", "N-10"],
            id="notes",
        ),
        pytest.param(
            "tasks",
            {
                "removed": [
                    {"id": "N-10", "kind": "note", "title": "十番目のメモ"},
                    {"id": "D-53", "kind": "decision", "title": "消した検討事項"},
                    {"id": "N-6", "kind": "note", "title": "六番目のメモ"},
                ]
            },
            [],
            id="no_removed_of_kind",
        ),
        pytest.param("notes", None, [], id="no_point"),
    ],
)
def test_removed_of(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    kind: str,
    point: dict[str, Any] | None,
    expected_ids: list[str],
) -> None:
    """画面の種類の消した項目だけを ID の順に返す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    ids = preview_page.evaluate(
        """({kind, point}) => {
            // 時点は、消した項目を渡した並びのまま持つ Map として組む
            const diffPoint =
                point === null
                    ? null
                    : {
                        sel: "pending",
                        name: "まだまとめていない変更",
                        sub: "",
                        added: new Set(),
                        changed: new Set(),
                        fromSeq: 0,
                        untilSeq: null,
                        removed: new Map(point.removed.map((item) => [item.id, item])),
                    };
            return MindmapPreview.removedOf({point: diffPoint, kind}).map((item) => item.id);
        }""",
        {"kind": kind, "point": point},
    )
    # 検証
    assert ids == expected_ids


def test_build_versions(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """古いまとまりの前後のキーと本文を組み立てる（正常系）。"""
    # 準備
    load_preview_scripts()
    item = {
        "id": "D-1",
        "title": "問い",
        "status": "決定済み",
        "history": [
            {"seq": 2, "at": ENTRY_AT, "before": {"status": "未決定"}},
            {
                "seq": 1,
                "at": ENTRY_AT,
                "before": {},
                "body_diff": [
                    {"line": 2, "now": ["新しい 2 行目"], "before": ["元の 2 行目"]},
                ],
            },
        ],
    }
    body = "1 行目\n新しい 2 行目\n3 行目\n"
    point = {"sel": "V-1", "name": "最初", "sub": "10/01 18:00", "fromSeq": 0, "untilSeq": 1}
    # 実行
    versions = preview_page.evaluate(
        """([item, body, point]) => MindmapPreview.buildVersions(
            item, body, {...point, added: new Set(), changed: new Set()}
        )""",
        [item, body, point],
    )
    # 検証
    assert versions["after"]["status"] == "未決定"
    assert versions["before"]["status"] == "未決定"
    assert versions["afterBody"] == body
    assert versions["beforeBody"] == "1 行目\n元の 2 行目\n3 行目\n"
    assert versions["trimmed"] is False
    assert versions["bodyUnavailable"] is False


def test_build_versions_when_trimmed(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """消えた回は組み立てられない（正常系）。"""
    # 準備
    load_preview_scripts()
    item = {
        "id": "D-1",
        "title": "問い",
        "status": "決定済み",
        "history": [{"seq": 2, "at": ENTRY_AT, "before": {"status": "未決定"}}],
    }
    point = {"sel": "V-1", "name": "最初", "sub": "10/01 18:00", "fromSeq": 0, "untilSeq": 1}
    # 実行
    versions = preview_page.evaluate(
        """([item, point]) => MindmapPreview.buildVersions(
            item, "本文\\n", {...point, added: new Set(), changed: new Set()}
        )""",
        [item, point],
    )
    # 検証
    assert versions["trimmed"] is True
    assert versions["before"] is None
    assert versions["beforeBody"] is None


def test_build_versions_when_body_rewritten(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """本文が当たらなければ本文だけ出せない（正常系）。"""
    # 準備
    load_preview_scripts()
    item = {
        "id": "D-1",
        "title": "問い",
        "status": "決定済み",
        "history": [
            {
                "seq": 1,
                "at": ENTRY_AT,
                "before": {"status": "未決定"},
                "body_diff": [
                    {"line": 2, "now": ["今の本文に無い行"], "before": ["元の行"]},
                ],
            }
        ],
    }
    point = {"sel": "since", "name": "前回開いてから", "sub": "10/02 09:00 より後", "fromSeq": 0}
    # 実行
    versions = preview_page.evaluate(
        """([item, point]) => MindmapPreview.buildVersions(
            item, "1 行目\\n2 行目\\n", {...point, untilSeq: null, added: new Set(), changed: new Set()}
        )""",
        [item, point],
    )
    # 検証
    assert versions["bodyUnavailable"] is True
    assert versions["beforeBody"] is None
    assert versions["before"]["status"] == "未決定"


@pytest.mark.parametrize(
    ("dropped_seq", "trimmed"),
    [
        pytest.param(7, True, id="dropped_in_range"),
        pytest.param(5, False, id="dropped_before_range"),
    ],
)
def test_build_versions_when_dropped_in_range(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    dropped_seq: int,
    trimmed: bool,
) -> None:
    """範囲の中の古い回が消えていれば組み立てられない。範囲より前の回が消えただけなら組み立てる（正常系）。"""
    # 準備
    load_preview_scripts()
    item = {
        "id": "D-1",
        "title": "問い",
        "status": "決定済み",
        "history": [{"seq": 9, "at": ENTRY_AT, "before": {"status": "未決定"}}],
        "history_dropped_seq": dropped_seq,
    }
    point = {"sel": "since", "name": "前回開いてから", "sub": "10/02 09:00 より後", "fromSeq": 5}
    # 実行
    versions = preview_page.evaluate(
        """([item, point]) => MindmapPreview.buildVersions(
            item, "", {...point, untilSeq: null, added: new Set(), changed: new Set()}
        )""",
        [item, point],
    )
    # 検証
    assert versions["trimmed"] is trimmed
    if trimmed:
        assert versions["before"] is None
        assert versions["beforeBody"] is None
    else:
        assert versions["before"]["status"] == "未決定"


def test_diff_line_parts(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """足した行と消した行を分ける（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("jsdiff")
    # 実行
    parts = preview_page.evaluate(
        """() => MindmapPreview.diffLineParts(
            "1 行目\\n2 行目\\n3 行目\\n", "1 行目\\n書き換えた 2 行目\\n3 行目\\n"
        )"""
    )
    # 検証
    assert parts == [
        {"kind": "same", "lines": ["1 行目"]},
        {"kind": "removed", "lines": ["2 行目"]},
        {"kind": "added", "lines": ["書き換えた 2 行目"]},
        {"kind": "same", "lines": ["3 行目"]},
    ]


def test_diff_line_parts_when_timeout(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """丸ごと書き換えた大きな本文は打ち切る（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        """([before, after]) => {
            const started = performance.now();
            const parts = MindmapPreview.diffLineParts(before, after);
            return {parts, elapsed: performance.now() - started};
        }""",
        [_lines_of("前"), _lines_of("後")],
    )
    # 検証
    assert result["parts"] is None
    assert result["elapsed"] < TIMEOUT_LIMIT_MS


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        pytest.param(
            THREE_PARAGRAPHS,
            WITHOUT_MIDDLE_PARAGRAPH,
            [{"lines": ["3 行目の段落", ""], "beforeLine": 3, "tableHeader": None}],
            id="middle_paragraph",
        ),
        pytest.param(
            THREE_PARAGRAPHS,
            WITHOUT_LAST_PARAGRAPH,
            [{"lines": ["", "5 行目の段落"], "beforeLine": None, "tableHeader": None}],
            id="last_paragraph",
        ),
    ],
)
def test_place_removed_blocks(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    before: str,
    after: str,
    expected: list[dict[str, Any]],
) -> None:
    """消した段落を直後の今の行の前に置き、末尾は null にする（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("jsdiff")
    # 実行
    blocks = preview_page.evaluate(
        """([before, after]) => MindmapPreview.placeRemovedBlocks(
            MindmapPreview.diffLineParts(before, after)
        )""",
        [before, after],
    )
    # 検証
    assert blocks == expected


def test_place_removed_blocks_when_table_row(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """表の 1 行だけを消したとき、表の見出しを添える（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("jsdiff")
    # 実行
    blocks = preview_page.evaluate(
        """([before, after]) => MindmapPreview.placeRemovedBlocks(
            MindmapPreview.diffLineParts(before, after)
        )""",
        [TABLE_THREE_ROWS, TABLE_WITHOUT_SECOND_ROW],
    )
    # 検証
    assert blocks == [{"lines": ["| 3 | 4 |"], "beforeLine": 4, "tableHeader": TABLE_HEADER_LINES}]


@pytest.mark.parametrize(
    ("diagram_type", "before", "after", "added", "changed", "removed"),
    [
        pytest.param(
            "flowchart",
            FLOWCHART_BEFORE,
            FLOWCHART_AFTER,
            "追加",
            "処理を変えた",
            "終了",
            id="flowchart",
        ),
        pytest.param(
            "sequenceDiagram",
            SEQUENCE_BEFORE,
            SEQUENCE_AFTER,
            "追加",
            "依頼を変えた",
            "確認",
            id="sequence",
        ),
        pytest.param(
            "classDiagram", CLASS_BEFORE, CLASS_AFTER, "Invoice", "cancel()", "Item", id="class"
        ),
        pytest.param("erDiagram", ER_BEFORE, ER_AFTER, "INVOICE", "title", "ITEM", id="er"),
        pytest.param(
            "stateDiagram-v2", STATE_BEFORE, STATE_AFTER, "追加", "実行中", "終了", id="state"
        ),
    ],
)
def test_diff_diagram(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    diagram_type: str,
    before: str,
    after: str,
    added: str,
    changed: str,
    removed: str,
) -> None:
    """5 種類で足した・変えた・消したものを取りこぼさない（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("mermaid")
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        DIFF_DIAGRAM_SCRIPT, {"type": diagram_type, "before": before, "after": after}
    )
    # 検証
    assert result is not None
    assert [len(result["added"]), len(result["changed"]), len(result["removed"])] == [1, 1, 1]
    assert added in result["added"][0]
    assert changed in result["changed"][0]
    assert removed in result["removed"][0]


def test_diff_diagram_when_type_not_colored(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """色付けの対象外の種類は null を返す（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("mermaid")
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        DIFF_DIAGRAM_SCRIPT, {"type": "gantt", "before": GANTT_BEFORE, "after": GANTT_AFTER}
    )
    # 検証
    assert result is None


@pytest.mark.parametrize(
    ("diagram_type", "before", "after", "expected"),
    [
        pytest.param(
            "flowchart",
            NOTATION_BEFORE,
            NOTATION_AFTER,
            {"added": [], "changed": ["次を変えた"], "removed": []},
            id="notation_unchanged",
        ),
        pytest.param(
            "flowchart",
            SHAPES_BEFORE,
            SHAPES_AFTER,
            {"added": [], "changed": ["丸い"], "removed": []},
            id="label_changed",
        ),
        pytest.param(
            "flowchart",
            EDGE_SWAP_BEFORE,
            EDGE_SWAP_AFTER,
            {"added": ["", "D"], "changed": [], "removed": ["B → C", "C"]},
            id="node_and_edge_swapped",
        ),
        pytest.param(
            "flowchart",
            TWO_EDGES_BEFORE,
            TWO_EDGES_FIRST_CHANGED,
            {"added": [], "changed": [""], "removed": []},
            id="two_edges_first_changed",
        ),
        pytest.param(
            "flowchart",
            TWO_EDGES_BEFORE,
            TWO_EDGES_SECOND_CHANGED,
            {"added": [], "changed": [""], "removed": []},
            id="two_edges_second_changed",
        ),
        pytest.param(
            "flowchart",
            UNDERSCORE_NODE_BEFORE,
            UNDERSCORE_NODE_AFTER,
            {"added": [], "changed": ["終を変えた"], "removed": []},
            id="node_id_with_underscore",
        ),
        pytest.param(
            "flowchart",
            EDGE_ID_BEFORE,
            EDGE_ID_AFTER,
            {"added": [], "changed": ["終を変えた"], "removed": []},
            id="edge_with_id",
        ),
        pytest.param(
            "flowchart",
            SUBGRAPH_BEFORE,
            SUBGRAPH_AFTER,
            {"added": [], "changed": ["中を変えた"], "removed": []},
            id="subgraph",
        ),
        pytest.param(
            "graph",
            GRAPH_BEFORE,
            GRAPH_AFTER,
            {"added": [], "changed": ["二を変えた"], "removed": []},
            id="graph",
        ),
    ],
)
def test_diff_diagram_from_source(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_library: LoadLibrary,
    diagram_type: str,
    before: str,
    after: str,
    expected: dict[str, list[str]],
) -> None:
    """ラベルの書き方によらず、前の版を描いて突き合わせたときと同じ差分を返す（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("mermaid")
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        DIFF_FROM_SOURCE_SCRIPT, {"type": diagram_type, "before": before, "after": after}
    )
    # 検証
    assert result["renderedTexts"] == expected
    assert result["parsed"] == result["rendered"]


def test_diff_diagram_from_source_when_removed_label_marked(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """消したノードの名前は、画面に出る文字にそろえる（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("mermaid")
    load_library("jsdiff")
    # 実行
    removed = preview_page.evaluate(
        DIFF_FROM_SOURCE_REMOVED_SCRIPT,
        {"type": "flowchart", "before": REMOVED_LABELS_BEFORE, "after": REMOVED_LABELS_AFTER},
    )
    # 検証
    assert removed == ["上段 下段", "消す 方"]


def test_diff_diagram_from_source_when_type_not_flowchart(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """flowchart でない種類は null を返す（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("mermaid")
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        DIFF_FROM_SOURCE_RESULT_SCRIPT,
        {"type": "sequenceDiagram", "before": SEQUENCE_BEFORE, "after": SEQUENCE_AFTER},
    )
    # 検証
    assert result == {"threw": False, "isNull": True}


def test_diff_diagram_from_source_when_parse_fails(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """解析できない記法は、例外を外へ出さずに null を返す（異常系）。"""
    # 準備
    load_preview_scripts()
    load_library("mermaid")
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        DIFF_FROM_SOURCE_RESULT_SCRIPT,
        {"type": "flowchart", "before": UNFINISHED_FLOWCHART, "after": FLOWCHART_AFTER},
    )
    # 検証
    assert result == {"threw": False, "isNull": True}


def test_diff_diagram_from_source_when_before_not_flowchart(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """前の版が flowchart でない組は、例外を外へ出さずに null を返す（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("mermaid")
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        DIFF_FROM_SOURCE_RESULT_SCRIPT,
        {
            "type": "flowchart",
            "before": SEQUENCE_TO_FLOWCHART_BEFORE,
            "after": SEQUENCE_TO_FLOWCHART_AFTER,
        },
    )
    # 検証
    assert result == {"threw": False, "isNull": True}
