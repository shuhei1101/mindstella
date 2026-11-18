"""components/markdown-body.ts（Markdown の本文の見せ方）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadMdmark, LoadPreviewScripts

# 本文の見せ方の既定（折りたたみはオン）
BODY_VIEW_DEFAULT = {"fold": True}

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


# 言語 bash のコードブロック・言語の無いコードブロック・mdmark が描いた Alert の囲み・印の無い引用を持つ本文
CODE_AND_CALLOUT_HTML = (
    '<pre><code class="language-bash">echo hello\nls</code></pre>'
    "<pre><code>plain text</code></pre>"
    '<div class="markdown-alert markdown-alert-warning" data-line-start="9">'
    '<p class="markdown-alert-title">警告</p><p>守らないと壊れます。</p></div>'
    '<blockquote data-line-start="12"><p>ただの引用です。</p></blockquote>'
)

# クリップボードへの書き込みを控え、同じ本文に 2 回当てて、コードブロックの札・ボタンと、Alert の囲みの見出しを調べる JavaScript
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
    const plainQuote = root.querySelector("blockquote");
    const plainQuoteBefore = plainQuote.outerHTML;
    MindmapPreview.decorateMarkdown({root});
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
            labels,
            buttonNames: buttons.map((button) => button.getAttribute("aria-label")),
            code: pre.querySelector("code").textContent,
            press: () => buttons[0].click(),
        };
    });
    blocks[0].press();
    await frames();
    const title = root.querySelector("div.markdown-alert > p.markdown-alert-title");
    return {
        blocks: blocks.map(({hasPre, labels, buttonNames}) => ({hasPre, labels, buttonNames})),
        nestedWraps: root.querySelectorAll("div.md-code div.md-code").length,
        writes,
        firstCode: blocks[0].code,
        callout: {
            icons: title.querySelectorAll("svg").length,
            iconFirst: title.firstElementChild?.outerHTML === MindmapPreview.icon("alert").outerHTML
                && title.firstChild === title.firstElementChild,
            title: (title.textContent ?? "").trim(),
        },
        plainQuoteChanged: plainQuote.outerHTML !== plainQuoteBefore,
    };
}"""
)


def test_decorate_markdown_when_code_and_callout(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """コードブロックに札とコピーを、Alert の囲みの見出しにアイコンを付ける（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(DECORATE_CODE_AND_CALLOUT_SCRIPT, CODE_AND_CALLOUT_HTML)
    # 検証
    assert result["blocks"] == [
        {"hasPre": True, "labels": ["bash"], "buttonNames": ["コードをコピー"]},
        {"hasPre": True, "labels": [], "buttonNames": ["コードをコピー"]},
    ]
    assert result["nestedWraps"] == 0
    assert result["writes"] == [result["firstCode"]]
    assert result["callout"] == {"icons": 1, "iconFirst": True, "title": "警告"}
    assert result["plainQuoteChanged"] is False


# 3 列の表・言語 bash のコードブロック・補足の囲みを持つ Markdown の本文
TABLES_SOURCE = (
    "| ID | 名前 | 説明 |\n| --- | --- | --- |\n| D-1 | 要件を決める | 要件を決めるための長い説明の文章です |\n\n"
    "```bash\necho hello\n```\n\n"
    "> [!NOTE]\n> 知っておくと早い。\n"
)

# 本文を renderMarkdown で描き（表の機能は `table` の指定のとおり）、見せ方を当てる前後の表の中の要素と、コードブロック・Alert の囲みの見出しの状態を返す JavaScript
DECORATE_RENDERED_SCRIPT = """({source, table}) => {
    const root = MindmapPreview.renderMarkdown(source, {table});
    document.body.append(root);
    const tableState = () => [...root.querySelectorAll(".mdmark-table, .mdmark-table *")].map(
        (element) => `${element.tagName}|${element.className}|${[...element.attributes].map((a) => `${a.name}=${a.value}`).sort().join(",")}`
    );
    const before = tableState();
    MindmapPreview.decorateMarkdown({root, display: {fold: true}, fold: false});
    const wrap = root.querySelector("div.md-code");
    const pre = wrap.querySelector(":scope > pre");
    const title = root.querySelector("div.markdown-alert > p.markdown-alert-title");
    return {
        inMdmarkTable: root.querySelector("table").closest(".mdmark-table") !== null,
        tableUnchanged: JSON.stringify(tableState()) === JSON.stringify(before),
        colSizes: root.querySelectorAll("[data-col-size]").length,
        frames: root.querySelectorAll("div.md-table-frame").length,
        pins: root.querySelectorAll("button.md-pin").length,
        codeButtons: [...wrap.querySelectorAll("button")].filter((button) => !pre.contains(button)).length,
        codeLabels: [...wrap.querySelectorAll("*")]
            .filter((element) => !pre.contains(element) && !element.closest("button"))
            .map((element) => (element.textContent ?? "").trim())
            .filter((text) => text !== ""),
        noteIcon: title.firstElementChild?.outerHTML === MindmapPreview.icon("note").outerHTML,
    };
}"""


def test_decorate_markdown_when_table(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_mdmark: LoadMdmark
) -> None:
    """mdmark の表の機能で描いた表に見せ方を当てない（正常系）。"""
    # 準備
    load_preview_scripts()
    load_mdmark()
    # 実行
    result = preview_page.evaluate(
        DECORATE_RENDERED_SCRIPT, {"source": TABLES_SOURCE, "table": True}
    )
    # 検証
    assert result["inMdmarkTable"] is True
    assert result["tableUnchanged"] is True
    assert (result["colSizes"], result["frames"], result["pins"]) == (0, 0, 0)


def test_decorate_markdown_when_tables_off(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_mdmark: LoadMdmark
) -> None:
    """表の機能をオフで描いた本文にも、コードと Alert の見せ方を当てる（正常系）。"""
    # 準備
    load_preview_scripts()
    load_mdmark()
    # 実行
    result = preview_page.evaluate(
        DECORATE_RENDERED_SCRIPT, {"source": TABLES_SOURCE, "table": False}
    )
    # 検証
    assert result == {
        "inMdmarkTable": False,
        "tableUnchanged": True,
        "colSizes": 0,
        "frames": 0,
        "pins": 0,
        "codeButtons": 1,
        "codeLabels": ["bash"],
        "noteIcon": True,
    }
