"""components/markdown-body.ts（Markdown の本文の見せ方）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, LoadPreviewStyles

# 本文の見せ方の既定（列の固定・見出しの固定・折りたたみはオン、しま模様はオフ）
BODY_VIEW_DEFAULT = {"pin": True, "head": True, "stripes": False, "fold": True}

# 同じ位置の誤差として許す px
PIXEL_TOLERANCE = 1

# 本文を作って文書に置く関数と、描き直しの終わりを待つ関数
MOUNT_FUNCTIONS = """const mount = (html, width = 800) => {
    const host = document.createElement("div");
    host.style.width = `${width}px`;
    const root = document.createElement("div");
    root.className = "md";
    root.innerHTML = html;
    host.append(root);
    document.body.append(host);
    return root;
};
const frames = async (count = 3) => {
    for (let index = 0; index < count; index += 1) {
        await new Promise((resolve) => requestAnimationFrame(resolve));
    }
};"""


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("名前", 2, id="full_width"),
        pytest.param("ID-12", 2.5, id="half_width"),
        pytest.param(" 比較 abc ", 4, id="trims_surrounding_spaces"),
        pytest.param("", 0, id="empty"),
        pytest.param("😀", 1, id="emoji"),
    ],
)
def test_text_width(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    text: str,
    expected: float,
) -> None:
    """全角を 1、半角を 0.5 と数える（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    width = preview_page.evaluate("(text) => MindmapPreview.textWidth(text)", text)
    # 検証
    assert width == expected


@pytest.mark.parametrize(
    ("max_width", "expected"),
    [
        pytest.param(8, {"kind": "short", "minEm": None}, id="short_at_boundary"),
        pytest.param(8.5, {"kind": "medium", "minEm": 7}, id="medium_just_over_short"),
        pytest.param(12, {"kind": "medium", "minEm": 8}, id="medium"),
        pytest.param(24.5, {"kind": "medium", "minEm": 14}, id="medium_capped"),
        pytest.param(25, {"kind": "long", "minEm": None}, id="long_at_boundary"),
    ],
)
def test_column_size(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    max_width: float,
    expected: dict[str, Any],
) -> None:
    """境目の前後で列の種類を分け、中くらいの列の最小の幅に上限を掛ける（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    size = preview_page.evaluate("(maxWidth) => MindmapPreview.columnSize(maxWidth)", max_width)
    # 検証
    assert size == expected


# h2「候補」（下に h3「料金」と h4「内訳」）と h2「まとめ」を持つ本文
SECTIONS_HTML = (
    '<h2 data-heading="候補">候補</h2><p>候補の説明</p>'
    '<h3 data-heading="料金">料金</h3><p>料金の説明</p>'
    '<h4 data-heading="内訳">内訳</h4><p>内訳の説明</p>'
    '<h2 data-heading="まとめ">まとめ</h2><p id="summary-text">まとめの説明</p>'
)

# 本文に見せ方を当て、「料金」「候補」の順に畳んでから、見出しへ移る前の処理を呼び、2 つの入れ物の状態を返す JavaScript
REVEAL_HEADING_SCRIPT = (
    MOUNT_FUNCTIONS
    + """
({html, slug}) => {
    const root = mount(html);
    MindmapPreview.decorateMarkdown({root});
    const arrow = (name) => root.querySelector(`[data-heading="${name}"] button.md-fold`);
    const state = () => Object.fromEntries(["候補", "料金"].map((name) => {
        const button = arrow(name);
        const section = document.getElementById(button.getAttribute("aria-controls"));
        return [name, {
            expanded: button.getAttribute("aria-expanded"),
            hidden: section.hasAttribute("hidden"),
            isSection: section.classList.contains("md-section-body"),
        }];
    }));
    arrow("料金").click();
    arrow("候補").click();
    const before = state();
    let error = null;
    try {
        MindmapPreview.revealHeading({root, slug});
    } catch (caught) {
        error = String(caught);
    }
    return {before, after: state(), error};
}"""
)

# 畳んだ後の 1 つの入れ物の状態
FOLDED = {"expanded": "false", "hidden": True, "isSection": True}

# 開いた後の 1 つの入れ物の状態
OPENED = {"expanded": "true", "hidden": False, "isSection": True}


@pytest.mark.parametrize(
    ("slug", "expected_after"),
    [
        pytest.param("内訳", {"候補": OPENED, "料金": OPENED}, id="heading_under_folded_sections"),
        pytest.param("まとめ", {"候補": FOLDED, "料金": FOLDED}, id="heading_outside_sections"),
        pytest.param("無い", {"候補": FOLDED, "料金": FOLDED}, id="heading_not_in_body"),
    ],
)
def test_reveal_heading(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    slug: str,
    expected_after: dict[str, Any],
) -> None:
    """畳んだ入れ物の中の見出しへ移るときは外側まで開く（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(REVEAL_HEADING_SCRIPT, {"html": SECTIONS_HTML, "slug": slug})
    # 検証
    assert result["before"] == {"候補": FOLDED, "料金": FOLDED}
    assert result["after"] == expected_after
    assert result["error"] is None


# 表を前後の段落と一緒に高さ 300px の領域に置き、領域を送った後の見出しの行の位置を調べる JavaScript
BIND_TABLE_HEADS_SCRIPT = (
    MOUNT_FUNCTIONS
    + """
async ({scrollTo, sticky, unbind}) => {
    const style = document.createElement("style");
    style.textContent = ".panel-body { height: 300px; overflow: auto; }";
    document.head.append(style);
    const scroller = document.createElement("div");
    scroller.className = "panel-body";
    const paragraphs = (label, count) => Array.from(
        {length: count}, (_, index) => `<p>${label} ${index + 1} の段落</p>`,
    ).join("");
    const rows = Array.from(
        {length: 20}, (_, index) => `<tr><td>行 ${index + 1}</td><td>値 ${index + 1}</td></tr>`,
    ).join("");
    scroller.innerHTML = `<div class="md">${paragraphs("前", 4)}`
        + '<div class="md-table-wrap">'
        + `<table${sticky ? ' class="md-head-stick"' : ""}>`
        + `<thead><tr><th>列 A</th><th>列 B</th></tr></thead><tbody>${rows}</tbody></table></div>`
        + `${paragraphs("後", 30)}</div>`;
    document.body.append(scroller);
    const table = scroller.querySelector("table");
    const head = table.querySelector("thead th");
    const stop = MindmapPreview.bindTableHeads(scroller);
    await frames();
    if (unbind) stop();
    const area = scroller.getBoundingClientRect();
    const tableTop = table.getBoundingClientRect().top - area.top + scroller.scrollTop;
    const tableHeight = table.getBoundingClientRect().height;
    const target = {
        top: 0,
        middle: tableTop + tableHeight / 2,
        past: tableTop + tableHeight + 40,
    }[scrollTo];
    scroller.scrollTop = target;
    await frames();
    const headRect = head.getBoundingClientRect();
    const tableRect = table.getBoundingClientRect();
    const offset = getComputedStyle(head).getPropertyValue("--head-offset").trim();
    return {
        reached: Math.abs(scroller.scrollTop - target) <= 1,
        offset: offset === "" ? null : parseFloat(offset),
        headTopFromArea: headRect.top - scroller.getBoundingClientRect().top,
        headBottomFromTableBottom: headRect.bottom - tableRect.bottom,
        stuck: table.classList.contains("md-head-stuck"),
    };
}"""
)


@pytest.mark.parametrize(
    ("scroll_to", "sticky", "unbind"),
    [
        pytest.param("top", True, False, id="before_table"),
        pytest.param("middle", True, False, id="middle_of_table"),
        pytest.param("past", True, False, id="past_table"),
        pytest.param("middle", False, False, id="table_without_head_stick"),
        pytest.param("middle", True, True, id="after_unbind"),
    ],
)
def test_bind_table_heads(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    scroll_to: str,
    sticky: bool,
    unbind: bool,
) -> None:
    """領域を送ると見出しの行を上端に残し、表の下端を越えない（正常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    # 実行
    result = preview_page.evaluate(
        BIND_TABLE_HEADS_SCRIPT, {"scrollTo": scroll_to, "sticky": sticky, "unbind": unbind}
    )
    # 検証
    assert result["reached"] is True
    if scroll_to == "top" or unbind:
        # 表の上端まで送らない間と、見張りを外した後は、見出しの行をずらさない
        assert result["offset"] == 0
        assert result["stuck"] is False
    elif not sticky:
        # `md-head-stick` を持たない表は、`--head-offset` を持たない
        assert result["offset"] is None
        assert result["stuck"] is False
    elif scroll_to == "middle":
        assert result["offset"] > 0
        assert result["stuck"] is True
        assert abs(result["headTopFromArea"]) <= PIXEL_TOLERANCE
    else:
        assert result["offset"] > 0
        assert result["stuck"] is True
        assert result["headBottomFromTableBottom"] <= PIXEL_TOLERANCE


# 列を 3 つ持つ表（ID は 3 文字、名前は全角 12 文字、説明は全角 30 文字）を持つ本文
TABLE_HTML = (
    '<div class="md-table-wrap"><table>'
    '<thead><tr data-line-start="1"><th>ID</th><th>名前</th><th>説明</th></tr></thead>'
    "<tbody>"
    f'<tr data-line-start="3"><td>D-1</td><td>{"名前" * 6}</td><td>{"説明" * 15}</td></tr>'
    f'<tr data-line-start="4"><td>D-2</td><td>{"名称" * 6}</td><td>{"概要" * 15}</td></tr>'
    "</tbody></table></div>"
)

# 本文に見せ方を当て、表の列の印・包み・行の印を返す JavaScript
DECORATE_TABLE_SCRIPT = (
    MOUNT_FUNCTIONS
    + """
async (html) => {
    const root = mount(html, 400);
    MindmapPreview.decorateMarkdown({root});
    await frames();
    const rows = [...root.querySelectorAll("tr")];
    const column = (index) => rows.map((row) => row.children[index]);
    const wrap = root.querySelector(".md-table-wrap");
    return {
        sizes: [0, 1, 2].map((index) => [...new Set(column(index).map((cell) => cell.dataset.colSize))]),
        nameMinEm: [...new Set(column(1).map((cell) => cell.style.getPropertyValue("--md-col-min")))],
        framed: wrap.parentElement.classList.contains("md-table-frame"),
        fade: wrap.parentElement.hasAttribute("data-fade"),
        lines: rows.map((row) => row.getAttribute("data-line-start")),
    };
}"""
)


def test_decorate_markdown_when_table(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
) -> None:
    """列の文字数で幅の印を付け、表を送らない枠で包む（正常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    # 実行
    result = preview_page.evaluate(DECORATE_TABLE_SCRIPT, TABLE_HTML)
    # 検証
    assert result["sizes"] == [["short"], ["medium"], ["long"]]
    assert result["nameMinEm"] == ["8em"]
    assert result["framed"] is True
    assert result["fade"] is True
    assert result["lines"] == ["1", "3", "4"]


# 列を 4 つ持つ表（見出しは ID・名前・担当・説明）を持つ本文
PIN_HTML = (
    '<div class="md-table-wrap"><table>'
    "<thead><tr><th>ID</th><th>名前</th><th>担当</th><th>説明</th></tr></thead>"
    "<tbody>"
    "<tr><td>D-1</td><td>要件</td><td>佐藤</td><td>要件を決める</td></tr>"
    "<tr><td>D-2</td><td>設計</td><td>鈴木</td><td>設計を決める</td></tr>"
    "</tbody></table></div>"
)

# 本文に見せ方を当て、固定のボタンを順に押してから、ボタンと固定したセルの状態を返す JavaScript
DECORATE_PIN_SCRIPT = (
    MOUNT_FUNCTIONS
    + """
async ({html, display, presses}) => {
    const root = mount(html);
    MindmapPreview.decorateMarkdown({root, display});
    await frames();
    const buttons = () => [...root.querySelectorAll("thead button.md-pin")];
    for (const index of presses) {
        buttons()[index].click();
        await frames();
    }
    const rows = [...root.querySelectorAll("tr")];
    const isSticky = (cell) => getComputedStyle(cell).position === "sticky";
    const first = rows[0].children[0];
    const second = rows[0].children[1];
    return {
        names: buttons().map((button) => button.getAttribute("aria-label")),
        pressed: buttons().map((button) => button.getAttribute("aria-pressed")),
        columns: buttons().map((button) => button.closest("th").cellIndex),
        stickyColumns: [0, 1, 2, 3].filter((index) => rows.every((row) => isSticky(row.children[index]))),
        stickyCells: rows.flatMap((row) => [...row.children]).filter(isSticky).length,
        secondLeftGap: isSticky(second)
            ? parseFloat(getComputedStyle(second).left) - first.getBoundingClientRect().width
            : null,
    };
}"""
)


@pytest.mark.parametrize(
    ("display", "presses", "expected"),
    [
        pytest.param(
            BODY_VIEW_DEFAULT,
            [1],
            {
                "pressed": ["false", "true", "false"],
                "stickyColumns": [0, 1],
                "stickyCells": 6,
                "has_gap": True,
            },
            id="pin_second_column",
        ),
        pytest.param(
            BODY_VIEW_DEFAULT,
            [1, 1],
            {
                "pressed": ["false", "false", "false"],
                "stickyColumns": [],
                "stickyCells": 0,
                "has_gap": False,
            },
            id="press_twice_unpins",
        ),
        pytest.param(
            {**BODY_VIEW_DEFAULT, "pin": False},
            [],
            {"pressed": [], "stickyColumns": [], "stickyCells": 0, "has_gap": False},
            id="pin_off",
        ),
    ],
)
def test_decorate_markdown_when_pin(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    display: dict[str, bool],
    presses: list[int],
    expected: dict[str, Any],
) -> None:
    """固定のボタンで押した列までを固定し、もう一度押すと外す（正常系）。"""
    # 準備
    load_preview_scripts()
    load_preview_styles()
    # 実行
    result = preview_page.evaluate(
        DECORATE_PIN_SCRIPT, {"html": PIN_HTML, "display": display, "presses": presses}
    )
    # 検証
    assert result["pressed"] == expected["pressed"]
    assert result["stickyColumns"] == expected["stickyColumns"]
    assert result["stickyCells"] == expected["stickyCells"]
    if expected["pressed"]:
        # 最後の列（説明）には固定のボタンが無い
        assert result["columns"] == [0, 1, 2]
        assert result["names"] == ["IDまで固定", "名前まで固定", "担当まで固定"]
    else:
        assert result["names"] == []
    if expected["has_gap"]:
        # 2 列目の左の位置は、1 列目の幅だけ空け、固定した列が重ならない
        assert abs(result["secondLeftGap"]) <= PIXEL_TOLERANCE
    else:
        assert result["secondLeftGap"] is None


# 本文に見せ方を当て、表のクラスを返す JavaScript
DECORATE_TABLE_CLASSES_SCRIPT = (
    MOUNT_FUNCTIONS
    + """
({html, display}) => {
    const root = mount(html);
    MindmapPreview.decorateMarkdown({root, display});
    const table = root.querySelector("table");
    return {
        headStick: table.classList.contains("md-head-stick"),
        stripes: table.classList.contains("md-stripes"),
    };
}"""
)


@pytest.mark.parametrize(
    ("display", "expected"),
    [
        pytest.param(BODY_VIEW_DEFAULT, {"headStick": True, "stripes": False}, id="default"),
        pytest.param(
            {**BODY_VIEW_DEFAULT, "stripes": True, "head": False},
            {"headStick": False, "stripes": True},
            id="stripes_on_head_off",
        ),
    ],
)
def test_decorate_markdown_when_stripes_and_head(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    display: dict[str, bool],
    expected: dict[str, bool],
) -> None:
    """しま模様と見出しの固定を設定のとおりに付ける（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        DECORATE_TABLE_CLASSES_SCRIPT, {"html": PIN_HTML, "display": display}
    )
    # 検証
    assert result == expected


# 上の本文の末尾に、中身の無い h2「付録」を足した本文
FOLD_HTML = SECTIONS_HTML + '<h2 data-heading="付録">付録</h2>'

# 本文に見せ方を当て、（押す指定のとき）「料金」の矢印を押してから、矢印と入れ物の状態を返す JavaScript
DECORATE_FOLD_SCRIPT = (
    MOUNT_FUNCTIONS
    + """
({html, display, fold, press}) => {
    const root = mount(html);
    MindmapPreview.decorateMarkdown(fold === null ? {root, display} : {root, display, fold});
    const arrow = (name) => root.querySelector(`[data-heading="${name}"] button.md-fold`);
    const names = ["候補", "料金", "内訳", "まとめ", "付録"];
    if (press) arrow("料金").click();
    const folded = (selector) => root.querySelector(selector).closest(".md-section-body[hidden]");
    return {
        arrows: names.filter((name) => arrow(name) !== null),
        labels: names.filter((name) => arrow(name) !== null).map((name) => arrow(name).getAttribute("aria-label")),
        priceExpanded: arrow("料金")?.getAttribute("aria-expanded") ?? null,
        detailHidden: folded('[data-heading="内訳"]')?.getAttribute("hidden") ?? null,
        summaryFolded: folded("#summary-text") !== null,
    };
}"""
)


@pytest.mark.parametrize(
    ("display", "fold", "press", "expected"),
    [
        pytest.param(
            BODY_VIEW_DEFAULT,
            None,
            True,
            {
                "arrows": ["候補", "料金", "まとめ"],
                "labels": ["候補を開閉", "料金を開閉", "まとめを開閉"],
                "priceExpanded": "false",
                "detailHidden": "until-found",
                "summaryFolded": False,
            },
            id="press_price_arrow",
        ),
        pytest.param(
            BODY_VIEW_DEFAULT,
            False,
            False,
            {
                "arrows": [],
                "labels": [],
                "priceExpanded": None,
                "detailHidden": None,
                "summaryFolded": False,
            },
            id="fold_prop_off",
        ),
        pytest.param(
            {**BODY_VIEW_DEFAULT, "fold": False},
            None,
            False,
            {
                "arrows": [],
                "labels": [],
                "priceExpanded": None,
                "detailHidden": None,
                "summaryFolded": False,
            },
            id="display_fold_off",
        ),
    ],
)
def test_decorate_markdown_when_fold(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    display: dict[str, bool],
    fold: bool | None,
    press: bool,
    expected: dict[str, Any],
) -> None:
    """上位 2 つの階層の見出しにだけ開閉を置き、畳むと次の同じか上の階層の見出しまでを隠す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        DECORATE_FOLD_SCRIPT, {"html": FOLD_HTML, "display": display, "fold": fold, "press": press}
    )
    # 検証
    assert result == expected


# 言語 bash のコードブロック・言語の無いコードブロック・Alert の引用・印の無い引用を持つ本文
CODE_AND_CALLOUT_HTML = (
    '<pre><code class="language-bash">echo hello\nls</code></pre>'
    "<pre><code>plain text</code></pre>"
    '<blockquote data-line-start="9"><p>[!WARNING]\n守らないと壊れます。</p></blockquote>'
    '<blockquote data-line-start="12"><p>ただの引用です。</p></blockquote>'
)

# クリップボードへの書き込みを控え、コードブロックの札・ボタンと、引用の囲みを調べる JavaScript
DECORATE_CODE_AND_CALLOUT_SCRIPT = (
    MOUNT_FUNCTIONS
    + """
async (html) => {
    const writes = [];
    Object.defineProperty(navigator, "clipboard", {
        configurable: true,
        value: {writeText: async (text) => { writes.push(text); }},
    });
    const root = mount(html);
    const plainQuote = root.querySelectorAll("blockquote")[1];
    const plainQuoteBefore = plainQuote.outerHTML;
    MindmapPreview.decorateMarkdown({root});
    const blocks = [...root.querySelectorAll("div.md-code")].map((wrap) => {
        const pre = wrap.querySelector(":scope > pre");
        const buttons = [...wrap.querySelectorAll("button")].filter((button) => !pre.contains(button));
        const labels = [...wrap.querySelectorAll("*")]
            .filter((element) => !pre.contains(element) && !element.closest("button"))
            .map((element) => (element.textContent ?? "").trim())
            .filter((text) => text !== "");
        return {
            hasPre: pre !== null,
            labels: [...new Set(labels)],
            buttonNames: buttons.map((button) => button.getAttribute("aria-label")),
            code: pre.querySelector("code").textContent,
            press: () => buttons[0].click(),
        };
    });
    blocks[0].press();
    await frames();
    const [callout, plain] = root.querySelectorAll("blockquote");
    return {
        blocks: blocks.map(({hasPre, labels, buttonNames}) => ({hasPre, labels, buttonNames})),
        writes,
        firstCode: blocks[0].code,
        callout: {
            isCallout: callout.classList.contains("md-callout"),
            hasTitle: (callout.textContent ?? "").includes("警告"),
            hasMarker: (callout.textContent ?? "").includes("[!WARNING]"),
            line: callout.getAttribute("data-line-start"),
        },
        plainQuoteChanged: plain.outerHTML !== plainQuoteBefore,
        plainQuoteIsCallout: plain.classList.contains("md-callout"),
    };
}"""
)


def test_decorate_markdown_when_code_and_callout(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """コードブロックに札とコピーを、Alert の引用に囲みを付ける（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(DECORATE_CODE_AND_CALLOUT_SCRIPT, CODE_AND_CALLOUT_HTML)
    # 検証
    assert result["blocks"] == [
        {"hasPre": True, "labels": ["bash"], "buttonNames": ["コードをコピー"]},
        {"hasPre": True, "labels": [], "buttonNames": ["コードをコピー"]},
    ]
    assert result["writes"] == [result["firstCode"]]
    assert result["callout"] == {
        "isCallout": True,
        "hasTitle": True,
        "hasMarker": False,
        "line": "9",
    }
    assert result["plainQuoteChanged"] is False
    assert result["plainQuoteIsCallout"] is False
