"""components/diff-minimap.ts（差分のミニマップ）の単体テスト。"""

from __future__ import annotations

from html import escape
from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, LoadPreviewStyles

# ミニマップの印の最小の長さの下限（px）
MARK_FLOOR_PX = 4

# 印の置き方を確かめる帯の高さ（px）と、本文の全体の高さ（px）
LAYOUT_LENGTH = 400
LAYOUT_TOTAL = 4000

# 同じ高さに重なる印の数
CROWDED_COUNT = 100


def _key_diff(*, key_id: str, was: str, now: str) -> str:
    """キーの差分の行（前の値と今の値を並べた `span.df-kv`）の HTML を返す。"""
    return (
        f'<span class="df-kv" data-id="{key_id}">'
        f'<del class="df-was"><span class="sr-only">前の値: </span>{was}</del>'
        '<span class="df-arrow" aria-hidden="true">→</span>'
        f'<ins class="df-now"><span class="sr-only">今の値: </span>{now}</ins>'
        "</span>"
    )


# 足した塊・間の段落・消した表の行を持つ本文（印は足した・消したの 2 つ）
ADDED_AND_DELETED_HTML = (
    '<div class="md">'
    '<ins class="df-blk"><p>足した段落</p></ins>'
    "<p>間の段落</p>"
    '<table><tbody><tr class="df-row df-del"><td>消した行</td></tr></tbody></table>'
    "</div>"
)

# 差分の印を持たない本文
PLAIN_HTML = '<div class="md"><p>変わらない段落</p></div>'

# 足した塊・消した塊・値が変わったキーを、間の段落を挟んで持つ本文（印は 3 つ）
THREE_MARKS_HTML = (
    '<div class="md">'
    '<ins class="df-blk"><p>足した段落</p></ins>'
    "<p>間の段落 A</p>"
    '<del class="df-blk"><p>消した段落</p></del>'
    "<p>間の段落 B</p>"
    "</div>"
    f'<div class="d-value">{_key_diff(key_id="key", was="前", now="今")}</div>'
)

# 消した塊のすぐ後ろに足した塊が続く本文
DELETED_THEN_ADDED_HTML = (
    '<div class="md">'
    '<del class="df-blk" data-id="deleted"><p>消した段落</p></del>'
    '<ins class="df-blk" data-id="added"><p>足した段落</p></ins>'
    "</div>"
)

# 足した塊が 2 つ続き、間の段落を空けて消した表の行がある本文
TWO_ADDED_THEN_DELETED_HTML = (
    '<div class="md">'
    '<ins class="df-blk" data-id="added-1"><p>足した段落 1</p></ins>'
    '<ins class="df-blk" data-id="added-2"><p>足した段落 2</p></ins>'
    "<p>間の段落</p>"
    '<table><tbody><tr class="df-row df-del" data-id="row"><td>消した行</td></tr></tbody></table>'
    "</div>"
)

# 前に無かったキーと、値が変わったキーを持つ本文
NEW_AND_CHANGED_KEYS_HTML = (
    f'<div class="d-value">{_key_diff(key_id="new-key", was="（なし）", now="新しい値")}</div>'
    f'<div class="d-value">{_key_diff(key_id="changed-key", was="前の値", now="今の値")}</div>'
)

# Raw を畳んだ変わった図（隠した Raw が足した行を持つ）を持つ本文
FOLDED_RAW_FIGURE_HTML = (
    '<div class="md">'
    '<figure class="diagram df-changed df-frame" data-id="figure">'
    '<div class="mermaid">図</div>'
    '<pre class="dg-raw df-raw" hidden><span class="df-line df-add">足した行</span></pre>'
    "</figure>"
    "</div>"
)

# Raw を出した変わった図（見えている Raw が足した行と消した行を持つ）を持つ本文
SHOWN_RAW_FIGURE_HTML = (
    '<div class="md">'
    '<figure class="diagram df-changed df-frame" data-id="figure">'
    '<div class="mermaid" hidden>図</div>'
    '<pre class="dg-raw df-raw">'
    '<span class="df-line df-add" data-id="raw-added">足した行</span>'
    '<span class="df-line df-del" data-id="raw-deleted">消した行</span>'
    "</pre>"
    "</figure>"
    "</div>"
)

# HTML の本文の枠の中身（足した要素と変えた要素）
FRAME_DOCUMENT = (
    '<p data-df="add" data-id="in-added">足した要素</p>'
    '<p data-df="chg" data-id="in-changed">変えた要素</p>'
)

# HTML の本文の枠
HTML_FRAME_HTML = (
    '<iframe class="html-frame" sandbox="allow-same-origin" data-id="frame" '
    f'srcdoc="{escape(FRAME_DOCUMENT)}"></iframe>'
)

# 本文を包んだ枠を作って文書に置き、次のコマの後の枠の中身を調べて返す JavaScript
BUILD_FRAME_SCRIPT = """async ({html, shown}) => {
    const body = document.createElement("div");
    body.className = "panel-body";
    body.innerHTML = html;
    const frame = MindmapPreview.diffMinimapFrame({body, shown});
    document.body.append(frame);
    // 印は、文書に入った後の次のコマで置かれる
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const map = frame.querySelector(".df-map");
    const kind = (child) =>
        child.classList.contains("panel-body") ? "body" : child.classList.contains("df-map") ? "map" : "other";
    return {
        isScroll: frame.classList.contains("panel-scroll"),
        children: [...frame.children].map(kind),
        hasMap: frame.classList.contains("has-map"),
        mapHidden: map === null ? null : map.hidden,
        role: map?.getAttribute("role") ?? null,
        label: map?.getAttribute("aria-label") ?? null,
        buttons: [...(map?.querySelectorAll("button") ?? [])].map((button) => ({
            name: button.getAttribute("aria-label"),
            tabStop: button.getAttribute("tabindex") === "0",
        })),
    };
}"""

# 帯の印のうちフォーカスのある印の位置・印ごとのタブの止まり・URL のハッシュを返す JavaScript
READ_FOCUS_SCRIPT = """() => {
    const buttons = [...document.querySelectorAll(".df-map button")];
    return {
        focused: buttons.indexOf(document.activeElement),
        tabStops: buttons.map((button) => button.getAttribute("tabindex") === "0"),
        hash: location.hash,
    };
}"""

# 本文を文書に置き、印の集め方が返した印を、要素の `data-id` に直して返す JavaScript
TARGETS_SCRIPT = """async (html) => {
    const body = document.createElement("div");
    body.className = "panel-body";
    body.innerHTML = html;
    document.body.append(body);
    // HTML の本文の枠は、中身を読み込んでから調べる
    await Promise.all(
        [...body.querySelectorAll("iframe.html-frame")].map(
            (frame) => new Promise((resolve) => frame.addEventListener("load", resolve, {once: true})),
        ),
    );
    const idOf = (element) => element?.getAttribute("data-id") ?? null;
    return MindmapPreview.minimapTargets(body).map((target) => ({
        kind: target.kind,
        first: idOf(target.first),
        last: idOf(target.last),
        frame: idOf(target.frame),
    }));
}"""


@pytest.mark.parametrize(
    ("html", "shown", "expected"),
    [
        pytest.param(
            ADDED_AND_DELETED_HTML,
            True,
            {
                "isScroll": True,
                "children": ["body", "map"],
                "hasMap": True,
                "mapHidden": False,
                "role": "toolbar",
                "label": "変わった箇所",
                "buttons": [
                    {"name": "足した箇所（1 / 2）", "tabStop": True},
                    {"name": "消した箇所（2 / 2）", "tabStop": False},
                ],
            },
            id="shown_with_marks",
        ),
        pytest.param(
            ADDED_AND_DELETED_HTML,
            False,
            {
                "isScroll": True,
                "children": ["body"],
                "hasMap": False,
                "mapHidden": None,
                "role": None,
                "label": None,
                "buttons": [],
            },
            id="not_shown",
        ),
        pytest.param(
            PLAIN_HTML,
            True,
            {
                "isScroll": True,
                "children": ["body", "map"],
                "hasMap": False,
                "mapHidden": True,
                "role": "toolbar",
                "label": "変わった箇所",
                "buttons": [],
            },
            id="shown_without_marks",
        ),
    ],
)
def test_diff_minimap_frame(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    html: str,
    shown: bool,
    expected: dict[str, Any],
) -> None:
    """印のある本文で帯と印を出し、出さないときは本文だけを包む（正常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    # 実行
    observed = preview_page.evaluate(BUILD_FRAME_SCRIPT, {"html": html, "shown": shown})
    # 検証
    assert observed == expected


def _press(page: Page, key: str) -> dict[str, Any]:
    """キーを送り、フォーカスのある印の位置・印ごとのタブの止まり・URL のハッシュを返す。"""
    page.keyboard.press(key)
    return page.evaluate(READ_FOCUS_SCRIPT)


def test_diff_minimap_frame_when_keys(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
) -> None:
    """矢印・Home / End で印の間を移り、ハッシュを変えない（正常系）。"""
    # 準備（URL のハッシュを決め、先頭の印にフォーカスする）
    load_preview_scripts()
    load_preview_styles()
    preview_page.evaluate("() => history.replaceState(null, '', '#keep')")
    preview_page.evaluate(BUILD_FRAME_SCRIPT, {"html": THREE_MARKS_HTML, "shown": True})
    preview_page.evaluate("() => document.querySelector('.df-map button').focus()")
    # 実行
    after_down = _press(preview_page, "ArrowDown")
    after_end = _press(preview_page, "End")
    after_home = _press(preview_page, "Home")
    after_up = _press(preview_page, "ArrowUp")
    # 検証（先頭より前へは移らない。タブの止まりはフォーカスのある印だけ）
    assert after_down == {"focused": 1, "tabStops": [False, True, False], "hash": "#keep"}
    assert after_end == {"focused": 2, "tabStops": [False, False, True], "hash": "#keep"}
    assert after_home == {"focused": 0, "tabStops": [True, False, False], "hash": "#keep"}
    assert after_up == {"focused": 0, "tabStops": [True, False, False], "hash": "#keep"}


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        pytest.param(
            DELETED_THEN_ADDED_HTML,
            [{"kind": "chg", "first": "deleted", "last": "added", "frame": None}],
            id="added_after_deleted_becomes_changed",
        ),
        pytest.param(
            TWO_ADDED_THEN_DELETED_HTML,
            [
                {"kind": "add", "first": "added-1", "last": "added-2", "frame": None},
                {"kind": "del", "first": "row", "last": "row", "frame": None},
            ],
            id="same_kind_merged",
        ),
        pytest.param(
            NEW_AND_CHANGED_KEYS_HTML,
            [
                {"kind": "add", "first": "new-key", "last": "new-key", "frame": None},
                {"kind": "chg", "first": "changed-key", "last": "changed-key", "frame": None},
            ],
            id="keys",
        ),
        pytest.param(
            FOLDED_RAW_FIGURE_HTML,
            [{"kind": "chg", "first": "figure", "last": "figure", "frame": None}],
            id="figure_with_folded_raw",
        ),
        pytest.param(
            SHOWN_RAW_FIGURE_HTML,
            [
                {"kind": "add", "first": "raw-added", "last": "raw-added", "frame": None},
                {"kind": "del", "first": "raw-deleted", "last": "raw-deleted", "frame": None},
            ],
            id="figure_with_shown_raw",
        ),
        pytest.param(
            HTML_FRAME_HTML,
            [
                {"kind": "add", "first": "in-added", "last": "in-added", "frame": "frame"},
                {"kind": "chg", "first": "in-changed", "last": "in-changed", "frame": "frame"},
            ],
            id="html_frame",
        ),
    ],
)
def test_minimap_targets(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    html: str,
    expected: list[dict[str, Any]],
) -> None:
    """続く同じ種類をまとめ、消した塊の直後の足した塊を変わったにする（正常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    # 実行
    targets = preview_page.evaluate(TARGETS_SCRIPT, html)
    # 検証
    assert targets == expected


# 左右に並べた本文（変えた行・変えていない行・変えた行の 3 行）。2 行目の左は空き
SIDE_BY_SIDE_HTML = (
    '<div class="sbs">'
    '<div class="sbs-cols">'
    '<section class="sbs-col sbs-before" aria-label="選んだ時点の本文">'
    '<div class="sbs-row sbs-chg"><div class="md">'
    '<del class="df-blk" data-id="deleted"><p>消した段落</p></del></div></div>'
    '<div class="sbs-row"><div class="md"><p>変えていない段落</p></div></div>'
    '<div class="sbs-row sbs-chg sbs-gap" aria-hidden="true"></div>'
    "</section>"
    '<section class="sbs-col sbs-after" aria-label="今の本文">'
    '<div class="sbs-row sbs-chg"><div class="md">'
    '<ins class="df-blk" data-id="added-first"><p>足した段落</p></ins></div></div>'
    '<div class="sbs-row"><div class="md"><p>変えていない段落</p></div></div>'
    '<div class="sbs-row sbs-chg"><div class="md">'
    '<ins class="df-blk" data-id="added-last"><p>末尾に足した段落</p></ins></div></div>'
    "</section>"
    "</div>"
    "</div>"
)


def test_minimap_targets_when_side_by_side(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
) -> None:
    """左右に並べた本文は高さの順に並べ、向かい合う消した塊と足した塊を変わったにする（正常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    # 実行
    targets = preview_page.evaluate(TARGETS_SCRIPT, SIDE_BY_SIDE_HTML)
    # 検証（向かい合う消した塊と足した塊が変わった 1 つ。末尾の足した塊は足した）
    assert [target["kind"] for target in targets] == ["chg", "add"]
    assert [target["first"] for target in targets] == ["deleted", "added-last"]


@pytest.mark.parametrize(
    ("extents", "expected_sizes", "expected_starts"),
    [
        pytest.param([{"top": 2000, "size": 400}], [40], [200], id="by_ratio"),
        pytest.param(
            [{"top": 0, "size": 10}, {"top": 20, "size": 10}],
            [12, 12],
            [0, 14],
            id="min_length_and_overlap",
        ),
        pytest.param([{"top": 3990, "size": 10}], [12], [388], id="near_end"),
        pytest.param(
            [{"top": 2000, "size": 10}] * CROWDED_COUNT,
            [MARK_FLOOR_PX] * CROWDED_COUNT,
            None,
            id="crowded",
        ),
    ],
)
def test_minimap_layout(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    extents: list[dict[str, int]],
    expected_sizes: list[int],
    expected_starts: list[int] | None,
) -> None:
    """割合で置き、最小の長さと重なりを直す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    layout = preview_page.evaluate(
        "(args) => MindmapPreview.minimapLayout(args)",
        {"extents": extents, "total": LAYOUT_TOTAL, "length": LAYOUT_LENGTH},
    )
    # 検証（どの置き方も、始まりが 0 以上で、帯の終わりを出ない）
    assert [mark["size"] for mark in layout] == expected_sizes
    assert all(mark["start"] >= 0 for mark in layout)
    assert all(mark["start"] + mark["size"] <= LAYOUT_LENGTH for mark in layout)
    assert expected_starts is None or [mark["start"] for mark in layout] == expected_starts
