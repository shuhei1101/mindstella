"""components/term-tip.ts（本文の印のツールチップ）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, LoadPreviewStyles, MakeItem

# 本文の印（a.term）と、その次にフォーカスできる要素を持つ本文を置き、ツールチップを作って文書に差し込む関数。
# ポップオーバーなら開き、置き場所が決まるまで 2 フレーム待つ
MOUNT_TIP_FUNCTION = """const mountTip = async ({entries, rect = null}) => {
    window.__calls = {open: [], close: 0};
    const body = document.createElement("div");
    body.className = "md";
    body.innerHTML = '<p>前 <a class="term" id="anchor" href="#">印</a> <button id="after" type="button">次</button></p>';
    document.body.append(body);
    const anchor = body.querySelector("#anchor");
    if (rect !== null) {
        anchor.style.cssText = `position:fixed;display:block;left:${rect.left}px;top:${rect.top}px;width:${rect.width}px;height:${rect.height}px`;
    }
    const tip = MindmapPreview.termTip({
        entries,
        anchor,
        pinned: false,
        on: {
            open: (id) => window.__calls.open.push(id),
            close: () => { window.__calls.close += 1; },
        },
    });
    document.body.append(tip);
    if (tip.hasAttribute("popover") && !tip.matches(":popover-open")) tip.showPopover();
    const frames = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    await frames();
    return {tip, anchor, frames};
};"""

# ツールチップの形（役割・種類ごとの見出し・リンクと、リンクの項目に添えた文）を調べる
CONTENT_SCRIPT = (
    MOUNT_TIP_FUNCTION
    + """
async ({entries, mustInclude}) => {
    const {tip} = await mountTip({entries});
    const squash = (text) => (text ?? "").replace(/\\s+/g, " ").trim();
    // 「用語 1」の形の見出し（入れ子の外側だけ）
    const matching = [...tip.querySelectorAll("*")].filter(
        (element) => /^(用語|資料|調査) \\d+$/.test(squash(element.textContent)),
    );
    const headings = matching
        .filter((element) => !matching.some((other) => other !== element && element.contains(other)))
        .map((element) => squash(element.textContent));
    const links = [...tip.querySelectorAll("a.tt-link")].map((link) => {
        const id = link.getAttribute("data-id");
        const title = squash(link.textContent);
        // 項目の行から、タイトルと ID と括弧・空白を除いた残り（説明・意味）
        const row = link.closest("li") ?? link.parentElement;
        const rest = squash(row.textContent).replace(title, "").replace(id, "").replace(/[\\s()（）]/g, "");
        return {id, title, rest};
    });
    const text = squash(tip.textContent);
    return {
        role: tip.getAttribute("role"),
        headings,
        links,
        containsAll: mustInclude.every((word) => text.includes(word)),
    };
}"""
)

def _entries(make_item: MakeItem, *item_ids: str) -> list[dict[str, Any]]:
    """用語 G-1・資料 A-2（説明あり）・資料 A-9（説明なし）・調査 R-1 のうち、渡した ID の項目を並べた引数を返す。"""
    items = {
        "G-1": ("terms", make_item("G-1", title="保存先", meaning="用語の意味")),
        "A-2": ("docs", make_item("A-2", title="効果の資料", description="資料の説明")),
        "A-9": ("docs", make_item("A-9", title="説明なし資料")),
        "R-1": ("research", make_item("R-1", title="効果の調査", description="調査の説明")),
    }
    return [{"kind": items[item_id][0], "item": items[item_id][1]} for item_id in item_ids]


@pytest.mark.parametrize(
    ("item_ids", "expected"),
    [
        pytest.param(
            ["G-1"],
            {"role": "tooltip", "headings": [], "links": [], "containsAll": True},
            id="terms_only",
        ),
        pytest.param(
            ["G-1", "A-2", "A-9", "R-1"],
            {
                "role": None,
                "headings": ["用語 1", "資料 2", "調査 1"],
                "links": [
                    {"id": "G-1", "title": "保存先", "rest": "用語の意味"},
                    {"id": "A-2", "title": "効果の資料", "rest": "資料の説明"},
                    {"id": "A-9", "title": "説明なし資料", "rest": ""},
                    {"id": "R-1", "title": "効果の調査", "rest": "調査の説明"},
                ],
                "containsAll": True,
            },
            id="with_docs_and_research",
        ),
    ],
)
def test_term_tip_content(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_item: MakeItem,
    item_ids: list[str],
    expected: dict[str, Any],
) -> None:
    """用語だけは今と同じ形、資料・調査を含むと見出しと区切りとリンクで並べる（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        CONTENT_SCRIPT,
        {"entries": _entries(make_item, *item_ids), "mustInclude": ["保存先", "G-1", "用語の意味"]},
    )
    # 検証
    assert result == expected


# 印の矩形（画面の中ほど・上端の近く）
MIDDLE_RECT = {"left": 400, "top": 300, "width": 60, "height": 20}
TOP_RECT = {"left": 400, "top": 10, "width": 60, "height": 20}

# ツールチップを置き、印との間の空き・縮めた高さの余白・中身を減らした後の高さの変わりを調べる
POSITION_SCRIPT = (
    MOUNT_TIP_FUNCTION
    + """
async ({entries, rect}) => {
    const {tip, anchor, frames} = await mountTip({entries, rect});
    const mark = anchor.getBoundingClientRect();
    const box = tip.getBoundingClientRect();
    const height = box.height;
    // 中身を減らして、高さが変わるかを見る
    [...tip.querySelectorAll("li")].slice(2).forEach((row) => row.remove());
    await frames();
    return {
        gapAbove: Math.round(mark.top - box.bottom),
        gapBelow: Math.round(box.top - mark.bottom),
        unusedAbove: Math.round(mark.top - 6 - height),
        heightChanged: tip.getBoundingClientRect().height !== height,
    };
}"""
)


@pytest.mark.parametrize(
    ("viewport_height", "rect", "docs", "expected"),
    [
        pytest.param(720, MIDDLE_RECT, 2, {"gapAbove": 6}, id="middle"),
        pytest.param(720, TOP_RECT, 2, {"gapBelow": 6}, id="near_top"),
        pytest.param(
            520,
            MIDDLE_RECT,
            8,
            {"gapAbove": 6, "unusedAbove": 0, "heightChanged": False},
            id="neither_fits",
        ),
    ],
)
def test_term_tip_position(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    load_preview_styles: LoadPreviewStyles,
    make_item: MakeItem,
    viewport_height: int,
    rect: dict[str, int],
    docs: int,
    expected: dict[str, Any],
) -> None:
    """上に出し、収まらなければ下、どちらにも収まらなければ広い側に縮める（正常系）。"""
    # 準備
    preview_page.set_viewport_size({"width": 1280, "height": viewport_height})
    load_preview_scripts()
    load_preview_styles()
    entries = [
        {
            "kind": "docs",
            "item": make_item(
                f"A-{number}",
                title=f"効果の資料 {number}",
                description="資料の説明が長く、ツールチップの中で折り返して何行かに分かれる。" * 2,
            ),
        }
        for number in range(1, docs + 1)
    ]
    # 実行
    result = preview_page.evaluate(POSITION_SCRIPT, {"entries": entries, "rect": rect})
    # 検証
    assert {key: result[key] for key in expected} == expected


# Tab・Shift+Tab・Esc・Enter を押す前に、リンクが 2 つのツールチップを置く
KEYS_SETUP_SCRIPT = (
    MOUNT_TIP_FUNCTION
    + """
async ({entries}) => {
    await mountTip({entries});
    return [...document.querySelectorAll("a.tt-link")].map((link) => link.getAttribute("data-id"));
}"""
)

# リンク（最初・最後）にフォーカスを置く
FOCUS_LINK_SCRIPT = """(position) => {
    const links = [...document.querySelectorAll("a.tt-link")];
    links.at(position).focus();
}"""

# フォーカスのある要素の ID と、知らせた回数
READ_STATE_SCRIPT = """() => ({
    active: document.activeElement?.id ?? "",
    open: window.__calls.open,
    close: window.__calls.close,
})"""


def test_term_tip_keys(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, make_item: MakeItem
) -> None:
    """中の Tab と Esc とリンクの押下（正常系）。"""
    # 準備
    load_preview_scripts()
    entries = [
        {"kind": "docs", "item": make_item("A-2", title="効果の資料")},
        {"kind": "docs", "item": make_item("A-3", title="別の資料")},
    ]
    link_ids = preview_page.evaluate(KEYS_SETUP_SCRIPT, {"entries": entries})
    # 実行
    preview_page.evaluate(FOCUS_LINK_SCRIPT, 0)
    preview_page.keyboard.press("Shift+Tab")
    after_shift_tab = preview_page.evaluate(READ_STATE_SCRIPT)
    preview_page.evaluate(FOCUS_LINK_SCRIPT, -1)
    preview_page.keyboard.press("Tab")
    after_tab = preview_page.evaluate(READ_STATE_SCRIPT)
    preview_page.evaluate(FOCUS_LINK_SCRIPT, 0)
    preview_page.keyboard.press("Escape")
    after_escape = preview_page.evaluate(READ_STATE_SCRIPT)
    preview_page.evaluate(FOCUS_LINK_SCRIPT, -1)
    preview_page.keyboard.press("Enter")
    after_enter = preview_page.evaluate(READ_STATE_SCRIPT)
    # 検証
    assert link_ids == ["A-2", "A-3"]
    assert after_shift_tab["active"] == "anchor"
    assert (after_tab["active"], after_tab["close"]) == ("after", 1)
    assert (after_escape["active"], after_escape["close"]) == ("anchor", 2)
    assert after_enter["open"] == ["A-3"]
