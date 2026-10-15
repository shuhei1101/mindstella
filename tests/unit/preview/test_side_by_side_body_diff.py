"""components/side-by-side-body-diff.ts（左右に並べた本文の差分）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadLibrary, LoadPreviewScripts, LoadPreviewStyles

# 語の差分を打ち切るまでの余裕（ミリ秒）。テストの本文では打ち切りに届かない
DEADLINE_MARGIN_MS = 5000

# 全ての行が違う本文の行数
LARGE_LINE_COUNT = 5000

# 本文を置く幅（px）
BODY_WIDTH_PX = 600

# 段落 3 つの 1 つ目を消し、末尾に段落を足した前後
PARAGRAPHS_BEFORE = "消す段落\n\n残る段落 A\n\n残る段落 B\n"
PARAGRAPHS_AFTER = "残る段落 A\n\n残る段落 B\n\n足す段落\n"

# 1 つ目の段落を 3 段落の長さに書き換えた前後（2 つ目・3 つ目の段落は変えない）
LONG_FIRST_BEFORE = "短い一つ目の段落\n\n二つ目の段落\n\n三つ目の段落\n"
LONG_FIRST_AFTER = "長い一つ目の段落です。" * 60 + "\n\n二つ目の段落\n\n三つ目の段落\n"

# 見出し `## 決め方` と `### 理由` を持ち、`### 理由` の下の段落だけを書き換えた前後
HEADINGS_BEFORE = "## 決め方\n\n決め方の段落\n\n### 理由\n\n理由の段落\n"
HEADINGS_AFTER = "## 決め方\n\n決め方の段落\n\n### 理由\n\n書き換えた理由の段落\n"

# 左右に並べた本文を作って本文の幅の枠に置き、次のコマの後の見た目を調べる JavaScript の共通の部分
BUILD_SCRIPT = """async ({before, after, lined}) => {
    const host = document.createElement("div");
    host.style.width = "%(width)spx";
    document.body.append(host);
    const diff = MindmapPreview.sideBySideBodyDiff({
        before,
        after,
        lined,
        deadline: performance.now() + %(margin)s,
    });
    if (diff === null) return null;
    host.append(diff.root);
    // 高さの揃え直しは、文書に入った後の次のコマで行う
    for (let frame = 0; frame < 4; frame += 1) await new Promise((resolve) => requestAnimationFrame(resolve));
    const columns = [...diff.root.querySelectorAll("section.sbs-col")];
    %(read)s
}"""

# 列の行の種類（空き・消した塊・足した塊・変えていない行）を上から並べ、読み上げの名前と行の印の数を返す
READ_ROWS = """
    const kindOf = (row) =>
        row.classList.contains("sbs-gap") ? "gap"
        : row.querySelector("del.df-blk") !== null ? "del"
        : row.querySelector("ins.df-blk") !== null ? "ins"
        : "same";
    const rowKinds = (column) => [...column.querySelectorAll(".sbs-row")].map(kindOf);
    return {
        labels: columns.map((column) => column.getAttribute("aria-label")),
        left: rowKinds(columns[0]),
        right: rowKinds(columns[1]),
        leftLined: columns[0].querySelectorAll("[data-line-start]").length,
        rightLined: columns[1].querySelectorAll("[data-line-start]").length > 0,
    };"""

# 変えていない 2 つの行の段落の上端を、左右の列ごとに返す
READ_TOPS = """
    const tops = (column) => [...column.querySelectorAll(".sbs-row")]
        .slice(1)
        .map((row) => Math.round(row.querySelector("p").getBoundingClientRect().top));
    return {left: tops(columns[0]), right: tops(columns[1])};"""

# 列ごとの見出しの文字と要素名を返す
READ_HEADINGS = """
    const headings = (column) => [...column.querySelectorAll("h1, h2, h3, h4, h5, h6")].map((heading) => ({
        text: (heading.textContent ?? "").trim(),
        tag: heading.tagName.toLowerCase(),
    }));
    return {left: headings(columns[0]), right: headings(columns[1])};"""


def _script(read: str) -> str:
    """共通の組み立てに、調べる部分を差し込んだ JavaScript を返す。"""
    return BUILD_SCRIPT % {"width": BODY_WIDTH_PX, "margin": DEADLINE_MARGIN_MS, "read": read}


@pytest.mark.parametrize(
    ("lined", "expected_right_lined"),
    [
        pytest.param(True, True, id="lined"),
        pytest.param(False, False, id="not_lined"),
    ],
)
def test_side_by_side_body_diff(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_library: LoadLibrary,
    lined: bool,
    expected_right_lined: bool,
) -> None:
    """消した印を左、足した印を右に付け、片側だけの塊の向かいを空きにする（正常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    load_library("marked")
    load_library("DOMPurify")
    load_library("jsdiff")
    # 実行
    result = preview_page.evaluate(
        _script(READ_ROWS), {"before": PARAGRAPHS_BEFORE, "after": PARAGRAPHS_AFTER, "lined": lined}
    )
    # 検証（左の列は行の印を持たない。右の列は lined のときだけ持つ）
    assert result["left"] == ["del", "same", "same", "gap"]
    assert result["right"] == ["gap", "same", "same", "ins"]
    assert result["labels"] == ["選んだ時点の本文", "今の本文"]
    assert result["leftLined"] == 0
    assert result["rightLined"] is expected_right_lined


def test_side_by_side_body_diff_when_aligned(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_library: LoadLibrary,
) -> None:
    """変えていない塊は左右で上端の高さが揃う（正常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    load_library("marked")
    load_library("DOMPurify")
    load_library("jsdiff")
    # 実行
    tops = preview_page.evaluate(
        _script(READ_TOPS), {"before": LONG_FIRST_BEFORE, "after": LONG_FIRST_AFTER, "lined": True}
    )
    # 検証（2 つ目・3 つ目の段落の左右の上端が同じ）
    assert len(tops["left"]) == 2
    assert tops["left"] == tops["right"]


def test_side_by_side_body_diff_when_timeout(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """行の差分を打ち切ったら描かない（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    load_library("jsdiff")
    before = "\n".join(f"前 {index}" for index in range(LARGE_LINE_COUNT)) + "\n"
    after = "\n".join(f"後 {index}" for index in range(LARGE_LINE_COUNT)) + "\n"
    # 実行
    result = preview_page.evaluate(
        _script(READ_ROWS), {"before": before, "after": after, "lined": True}
    )
    # 検証
    assert result is None


def test_side_by_side_body_diff_when_headings(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    load_library: LoadLibrary,
) -> None:
    """見出しの段は前後を合わせた最も上の段から 1 つの差で下げ、左右で揃う（正常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    load_library("marked")
    load_library("DOMPurify")
    load_library("jsdiff")
    expected: list[dict[str, Any]] = [
        {"text": "決め方", "tag": "h4"},
        {"text": "理由", "tag": "h5"},
    ]
    # 実行
    headings = preview_page.evaluate(
        _script(READ_HEADINGS),
        {"before": HEADINGS_BEFORE, "after": HEADINGS_AFTER, "lined": True},
    )
    # 検証
    assert headings == {"left": expected, "right": expected}
