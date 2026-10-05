"""screens/detail.ts（詳細パネル）の単体テスト。"""

from __future__ import annotations

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
    entry = {"seq": 1, "at": ENTRY_AT, "before": {}, "body_diff": REMOVED_PARAGRAPHS_DIFF}
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
        OPEN_DIFF_PANEL_SCRIPT, {"data": data, "point": DIFF_POINT, "highlight": highlight}
    )
    # 検証
    assert result["hits"] == [{"line": "3", "text": "今の 3 行目の段落"}]
    first, second = result["removed"]
    assert "消した段落 A" in first["text"]
    assert "消した段落 B" in second["text"]
    assert (first["underLineMark"], second["underLineMark"]) == (False, False)
