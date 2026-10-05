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
