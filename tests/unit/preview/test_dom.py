"""core/dom.ts（要素の組み立て・アイコン・状態の印・選択中）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 空の断片（DocumentFragment）の nodeType
FRAGMENT_NODE_TYPE = 11

# 空の断片を `describe` が返す形（子が無い）
EMPTY_FRAGMENT = {"nodeType": FRAGMENT_NODE_TYPE, "childCount": 0}

# スクロールする要素の背景（ボタンの外）と、ボタンの上の押す位置
BACKGROUND_POINT = (150, 150)
BUTTON_POINT = (60, 60)

# ドラッグで動かした量（左へ・上へ）
DRAG_LEFT = 50
DRAG_UP = 30

# ドラッグを始める前のスクロール位置
START_SCROLL = 100

# 押したとみなす移動の上限（縦・横とも。`PRESS_SLOP_PX`）と、それを超える移動
PRESS_SLOP = 5
PRESS_OVER_SLOP = PRESS_SLOP + 1

# スクロールする要素を置き、中にボタンを持たせる（ボタンは枠の左上から 50px の所に見える）。
# 続けて `enableDragScroll` を付ける式を足して使う
SCROLLER_SETUP = """
    const scroller = document.createElement("div");
    scroller.id = "scroller";
    scroller.style.cssText = "position:fixed;left:0;top:0;width:200px;height:200px;overflow:auto";
    const content = document.createElement("div");
    content.style.cssText = "position:relative;width:1000px;height:1000px";
    const button = document.createElement("button");
    button.style.cssText = "position:absolute;left:150px;top:150px;width:40px;height:24px";
    content.append(button);
    scroller.append(content);
    document.body.append(scroller);
    scroller.scrollLeft = 100;
    scroller.scrollTop = 100;
"""

# `onPress` を渡さずに付ける
SCROLLER_SCRIPT = "() => {" + SCROLLER_SETUP + "    MindmapPreview.enableDragScroll(scroller);\n}"

# `onPress` に呼ばれた回数を `window.pressCount` へ数える関数を渡して付ける
SCROLLER_WITH_PRESS_SCRIPT = (
    "() => {"
    + SCROLLER_SETUP
    + "    window.pressCount = 0;\n"
    + "    MindmapPreview.enableDragScroll(scroller, () => { window.pressCount += 1; });\n}"
)


def test_h(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """属性・リスナー・子を付けた要素を作る（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """() => {
            let clicks = 0;
            const child = document.createElement("i");
            const element = MindmapPreview.h({
                tag: "button",
                attrs: {
                    class: "b",
                    disabled: true,
                    title: null,
                    hidden: false,
                    onclick: () => { clicks += 1; },
                },
                children: ["a", 1, null, false, child],
            });
            element.dispatchEvent(new Event("click"));
            return {
                className: element.className,
                disabled: element.getAttribute("disabled"),
                hasTitle: element.hasAttribute("title"),
                hasHidden: element.hasAttribute("hidden"),
                children: Array.from(element.childNodes).map(
                    (node) => node.nodeType === Node.TEXT_NODE ? node.textContent : node.tagName,
                ),
                clicks,
            };
        }"""
    )
    # 検証
    assert result == {
        "className": "b",
        "disabled": "",
        "hasTitle": False,
        "hasHidden": False,
        "children": ["a", "1", "I"],
        "clicks": 1,
    }


def test_append(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """偽の値を除いて子を足す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    children = preview_page.evaluate(
        """() => {
            const parent = document.createElement("div");
            parent.append(document.createElement("b"));
            MindmapPreview.append({parent, children: ["x", 0, undefined, false]});
            return Array.from(parent.childNodes).map(
                (node) => node.nodeType === Node.TEXT_NODE ? node.textContent : node.tagName,
            );
        }"""
    )
    # 検証
    assert children == ["B", "x", "0"]


def test_icon(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """装飾として隠した線のアイコンを返す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """() => {
            const svg = MindmapPreview.icon("search");
            return {
                tag: svg.tagName,
                className: svg.getAttribute("class"),
                ariaHidden: svg.getAttribute("aria-hidden"),
                shapes: svg.children.length,
            };
        }"""
    )
    # 検証
    assert result["tag"] == "svg"
    assert result["className"] == "icon"
    assert result["ariaHidden"] == "true"
    assert result["shapes"] >= 1


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        pytest.param("決定済み", "svg.mark", id="decided"),
        pytest.param("要見直し", "svg.mark", id="needs_review"),
        pytest.param("完成", "svg.mark", id="completed"),
        pytest.param("知らない", None, id="unknown"),
        pytest.param(None, None, id="undefined"),
    ],
)
def test_status_mark(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    status: str | None,
    expected: str | None,
) -> None:
    """状態の印を返す。知らない状態と未指定は印なし（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """(status) => {
            const mark = MindmapPreview.statusMark(status ?? undefined);
            return mark === null ? null : `${mark.tagName}.${mark.getAttribute("class")}`;
        }""",
        status,
    )
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        pytest.param(
            "未決定",
            {"tag": "SPAN", "className": "st", "dataSt": "未決定", "text": "未決定", "marks": 1},
            id="open",
        ),
        pytest.param(None, EMPTY_FRAGMENT, id="undefined"),
    ],
)
def test_status_badge(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    status: str | None,
    expected: dict[str, Any],
) -> None:
    """印と状態の名前を並べる。状態を持たない項目は空の断片（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """(status) => {
            const node = MindmapPreview.statusBadge(status ?? undefined);
            if (node.nodeType === Node.DOCUMENT_FRAGMENT_NODE) {
                return {nodeType: node.nodeType, childCount: node.childNodes.length};
            }
            return {
                tag: node.tagName,
                className: node.className,
                dataSt: node.getAttribute("data-st"),
                text: node.textContent,
                marks: node.querySelectorAll("svg.mark").length,
            };
        }""",
        status,
    )
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    ("weight", "labeled", "expected"),
    [
        pytest.param("大", False, {"on": 3, "text": "大"}, id="large"),
        pytest.param("中", False, {"on": 2, "text": "中"}, id="medium"),
        pytest.param("小", False, {"on": 1, "text": "小"}, id="small"),
        pytest.param("知らない", False, EMPTY_FRAGMENT, id="unknown"),
        pytest.param(None, False, EMPTY_FRAGMENT, id="undefined"),
        pytest.param("大", True, {"on": 3, "text": "影響度 大"}, id="large_labeled"),
    ],
)
def test_impact_badge(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    weight: str | None,
    labeled: bool,
    expected: dict[str, Any],
) -> None:
    """影響度を目盛りと文字で表す。大・中・小のどれでもない値と未指定は空の断片（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """({weight, labeled}) => {
            const node = MindmapPreview.impactBadge(weight ?? undefined, labeled || undefined);
            if (node.nodeType === Node.DOCUMENT_FRAGMENT_NODE) {
                return {nodeType: node.nodeType, childCount: node.childNodes.length};
            }
            return {on: node.querySelectorAll("i.on").length, text: node.textContent};
        }""",
        {"weight": weight, "labeled": labeled},
    )
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        pytest.param(["UI", "性能"], {"tags": 2}, id="two_tags"),
        pytest.param(None, EMPTY_FRAGMENT, id="undefined"),
    ],
)
def test_tag_list(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    values: list[str] | None,
    expected: dict[str, Any],
) -> None:
    """タグを span.tag で並べる。未指定は空の断片（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """(values) => {
            const node = MindmapPreview.tagList(values ?? undefined);
            if (node.childNodes.length === 0) {
                return {nodeType: node.nodeType, childCount: 0};
            }
            return {tags: node.querySelectorAll("span.tag").length};
        }""",
        values,
    )
    # 検証
    assert result == expected


def test_deliverable_badge(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """箱のアイコンと「納品物」を持つ印を返す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """() => {
            const badge = MindmapPreview.deliverableBadge();
            return {
                tag: badge.tagName,
                className: badge.className,
                icons: badge.querySelectorAll("svg.icon").length,
                text: badge.textContent,
            };
        }"""
    )
    # 検証
    assert result == {"tag": "SPAN", "className": "deliv-badge", "icons": 1, "text": "納品物"}


def test_empty_note(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """空のときの 1 行を p.empty で返す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """() => {
            const note = MindmapPreview.emptyNote("該当なし");
            return {tag: note.tagName, className: note.className, text: note.textContent};
        }"""
    )
    # 検証
    assert result == {"tag": "P", "className": "empty", "text": "該当なし"}


@pytest.mark.parametrize(
    ("start", "expected_scroll"),
    [
        pytest.param(
            BACKGROUND_POINT,
            {"left": START_SCROLL + DRAG_LEFT, "top": START_SCROLL + DRAG_UP},
            id="background",
        ),
        pytest.param(BUTTON_POINT, {"left": START_SCROLL, "top": START_SCROLL}, id="button"),
    ],
)
def test_enable_drag_scroll(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    start: tuple[int, int],
    expected_scroll: dict[str, int],
) -> None:
    """背景のドラッグでスクロールし、ボタンの上では動かさない（正常系）。"""
    # 準備
    load_preview_scripts()
    preview_page.evaluate(SCROLLER_SCRIPT)
    start_x, start_y = start
    # 実行
    preview_page.mouse.move(start_x, start_y)
    preview_page.mouse.down()
    preview_page.mouse.move(start_x - DRAG_LEFT, start_y - DRAG_UP, steps=5)
    preview_page.mouse.up()
    # 検証
    result = preview_page.evaluate(
        """() => {
            const scroller = document.getElementById("scroller");
            return {
                left: scroller.scrollLeft,
                top: scroller.scrollTop,
                dragging: scroller.classList.contains("dragging"),
            };
        }"""
    )
    assert result == {**expected_scroll, "dragging": False}


@pytest.mark.parametrize(
    ("start", "move", "expected_count"),
    [
        pytest.param(BACKGROUND_POINT, (0, 0), 1, id="background_still"),
        pytest.param(BACKGROUND_POINT, (PRESS_SLOP, PRESS_SLOP), 1, id="background_within_slop"),
        pytest.param(BACKGROUND_POINT, (PRESS_OVER_SLOP, 0), 0, id="background_over_slop"),
        pytest.param(BUTTON_POINT, (0, 0), 0, id="button_still"),
    ],
)
def test_enable_drag_scroll_when_pressed(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    start: tuple[int, int],
    move: tuple[int, int],
    expected_count: int,
) -> None:
    """背景を押したときだけ onPress を呼び、ドラッグとボタンの上では呼ばない（正常系）。"""
    # 準備
    load_preview_scripts()
    preview_page.evaluate(SCROLLER_WITH_PRESS_SCRIPT)
    start_x, start_y = start
    move_x, move_y = move
    # 実行
    preview_page.mouse.move(start_x, start_y)
    preview_page.mouse.down()
    preview_page.mouse.move(start_x + move_x, start_y + move_y, steps=5)
    preview_page.mouse.up()
    # 検証
    assert preview_page.evaluate("() => window.pressCount") == expected_count


@pytest.mark.parametrize(
    ("selected", "expected"),
    [
        pytest.param("D-2", {"selected": ["D-2"], "current": "D-2"}, id="item"),
        pytest.param(None, {"selected": [], "current": None}, id="closed"),
    ],
)
def test_mark_selected(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    selected: str | None,
    expected: dict[str, Any],
) -> None:
    """開いた項目だけに selected を付け、閉じたら外す（正常系）。"""
    # 準備
    load_preview_scripts()
    preview_page.evaluate(
        """() => {
            const main = document.createElement("main");
            for (const id of ["D-1", "D-2"]) {
                const row = document.createElement("div");
                row.dataset.id = id;
                main.append(row);
            }
            document.body.append(main);
        }"""
    )
    # 実行
    result = preview_page.evaluate(
        """(selected) => {
            MindmapPreview.markSelected(selected);
            return {
                selected: Array.from(document.querySelectorAll("main [data-id].selected"))
                    .map((row) => row.dataset.id),
                current: MindmapPreview.currentSelection(),
            };
        }""",
        selected,
    )
    # 検証
    assert result == expected


# 左端 0〜420px のパネルと、本文（main）・トップバー（header）を置く。
# ボタンは、本文の左端の A（x=10）・本文の右側の B（x=600）・始めから inert の C（x=20）と、トップバーの D（x=10）
INERT_SETUP = """
    const place = (parent, id, left, top) => {
        const button = document.createElement("button");
        button.id = id;
        button.style.cssText = `position:fixed;left:${left}px;top:${top}px;width:40px;height:24px`;
        parent.append(button);
        return button;
    };
    const topbar = document.createElement("header");
    place(topbar, "D", 10, 20);
    const main = document.createElement("main");
    place(main, "A", 10, 100);
    place(main, "B", 600, 100);
    place(main, "C", 20, 160).inert = true;
    const panel = document.createElement("div");
    panel.style.cssText = "position:fixed;left:0;top:0;width:420px;height:600px";
    document.body.append(topbar, main, panel);
"""

# ボタン A〜D の inert を `{id: inert}` で返す式
INERT_STATES = """
    const inertStates = () => Object.fromEntries(
        ["A", "B", "C", "D"].map((id) => [id, document.getElementById(id).inert])
    );
"""


def test_inert_behind(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """パネルに覆われた部品だけを止め、外すと付けた分だけ戻す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        "() => {"
        + INERT_SETUP
        + INERT_STATES
        + """
            const release = MindmapPreview.inertBehind(panel);
            const covered = inertStates();
            release();
            return {covered, released: inertStates()};
        }"""
    )
    # 検証
    assert result["covered"] == {"A": True, "B": False, "C": True, "D": False}
    # 始めから inert の C は外さない
    assert result["released"] == {"A": False, "B": False, "C": True, "D": False}


def test_inert_behind_when_redrawn(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """本文を描き直してから呼び直すと、新しい部品も止まる（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        "() => {"
        + INERT_SETUP
        + """
            const release = MindmapPreview.inertBehind(panel);
            // 本文を左端のボタン E だけに描き直す
            main.replaceChildren();
            const button = place(main, "E", 10, 100);
            release();
            MindmapPreview.inertBehind(panel);
            button.focus();
            return {inert: button.inert, focused: document.activeElement === button};
        }"""
    )
    # 検証
    assert result == {"inert": True, "focused": False}
