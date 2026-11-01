"""Markdown の本文の表とセクションの見せ方（表の列の固定・見出しの固定・しま模様・セクションの折りたたみ）の E2E テストが共有する本文と値、操作・読み取りの関数。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Locator, Page

__all__ = [
    "BODY_HASH",
    "BODY_VIEWPORT_WIDTH",
    "DOCS_HASH",
    "PANEL_BODY",
    "POSITION_TOLERANCE_PX",
    "SMALL_TABLE_BODY",
    "TABLE_WRAP",
    "WIDE_TABLE_BODY",
    "fold_button",
    "head_offset_from_top",
    "heading_link_href",
    "open_a4_from_cards",
    "pinned_layout",
    "row_colors",
    "scroll_body_down",
    "scroll_body_to_top",
    "scroll_table_to_end",
    "table_layout",
    "table_scrolled_past_top",
    "wait_head_at_top",
    "wait_table_rendered",
]

# 資料の画面と、資料 A-4 の詳細パネルを開いた URL のハッシュ
DOCS_HASH = "#tab=docs"
BODY_HASH = "#tab=docs&id=A-4"

# 詳細パネルの本文の幅が、列の多い表を収められない幅になる画面の幅
BODY_VIEWPORT_WIDTH = 1280

# 詳細パネル、本文のスクロール領域、本文の表の入れ物
DETAIL_PANEL = "aside.panel"
PANEL_BODY = f"{DETAIL_PANEL} .panel-body"
TABLE_WRAP = f"{PANEL_BODY} .md-table-wrap"

# 画面が描き終わるまで待つ上限ミリ秒
RENDER_TIMEOUT_MS = 20_000

# 位置が合っているとみなす差（px）
POSITION_TOLERANCE_PX = 2

# 本文を縦に送ってから、表の途中まで進んだとみなす送り量（px）
BODY_SCROLL_PX = 300

# ホイールを回すときのマウスを、要素の上端から下げる量（px）
WHEEL_POINT_OFFSET_PX = 60

# ホイールを回す量（px）。表の幅・本文の高さより大きくして端まで送る
TABLE_WHEEL_PX = 5000

# 表の行の数
WIDE_ROW_COUNT = 20
SMALL_ROW_COUNT = 6

# 幅の広い表の見出しの行
_WIDE_HEAD = (
    "| ID | 状態 | 名前 | 担当 | 期限 | 種別 | 優先度 | 説明 |\n"
    "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
)

# 説明の列の文（80 文字を超える長文）
_DESCRIPTION = (
    "列の文字数で幅と折り返しを決め、表が本文の幅に収まらないときは表の中だけで横に送れるようにする。"
    "このセルは八十文字を超える長い文で、どの行でも同じ一定の幅で折り返される。"
)


def _wide_row(number: int) -> str:
    """幅の広い表の 1 行（ID・状態・名前・担当・期限・種別・優先度・説明）を返す。"""
    return (
        f"| D-{number} | 検討中 | 本文の表の見せ方を決める {number} | ドキュメント担当チーム"
        f" | 2026-10-{number:02d} 18:00 | 画面設計と部品設計の確認 | 最優先 | {_DESCRIPTION} |\n"
    )


# 見出し「比較」の下に 8 列・20 行の表を置き、見出し「補足」の下に段落を置いた本文
WIDE_TABLE_BODY = (
    f"## 比較\n\n{_WIDE_HEAD}"
    + "".join(_wide_row(number) for number in range(1, WIDE_ROW_COUNT + 1))
    + "\n## 補足\n\n補足の段落です。\n"
)

# 見出し「比較」の下に 4 列・6 行の表を置いた本文
SMALL_TABLE_BODY = (
    "## 比較\n\n| ID | 状態 | 名前 | 担当 |\n| --- | --- | --- | --- |\n"
    + "".join(f"| D-{number} | 検討中 | 本文の表の見せ方 {number} | 佐藤 |\n" for number in range(1, SMALL_ROW_COUNT + 1))
)

# 表の列の種類ごとの折り返しと、しま模様の色の数を返す
_TABLE_LAYOUT_JS = """() => {
    const wrap = document.querySelector('aside.panel .panel-body .md-table-wrap');
    const area = document.querySelector('aside.panel .panel-body');
    const heads = [...wrap.querySelectorAll('thead th')];
    const rows = [...wrap.querySelectorAll('tbody tr')];
    const named = (cell) => cell.firstChild.textContent.trim();
    const lineCount = (cell) => {
        const range = document.createRange();
        range.selectNodeContents(cell);
        return new Set([...range.getClientRects()].map((rect) => Math.round(rect.top))).size;
    };
    const linesOf = (name) => {
        const index = heads.findIndex((cell) => named(cell) === name);
        return rows.map((row) => lineCount(row.children[index]));
    };
    const widthsOf = (name) => {
        const index = heads.findIndex((cell) => named(cell) === name);
        return new Set(rows.map((row) => Math.round(row.children[index].getBoundingClientRect().width)));
    };
    const names = ['ID', '状態', '優先度', '説明'];
    return {
        maxLines: Object.fromEntries(names.map((name) => [name, Math.max(...linesOf(name))])),
        minLines: Object.fromEntries(names.map((name) => [name, Math.min(...linesOf(name))])),
        descriptionWidthCount: widthsOf('説明').size,
        wrapScrolls: wrap.scrollWidth > wrap.clientWidth + 1,
        areaScrolls: area.scrollWidth > area.clientWidth + 1,
        stripeColorCount: new Set(rows.map((row) => getComputedStyle(row.firstElementChild).backgroundColor)).size,
    };
}"""

# 表の本体の行ごとの、先頭のセルの背景色を返す
_ROW_COLORS_JS = """() => [...document.querySelectorAll('aside.panel .panel-body .md-table-wrap tbody tr')]
    .map((row) => getComputedStyle(row.firstElementChild).backgroundColor)"""

# 固定した列と右端の列が、表の入れ物の中に見えているかを返す
_PINNED_LAYOUT_JS = """() => {
    const wrap = document.querySelector('aside.panel .panel-body .md-table-wrap');
    const edge = wrap.getBoundingClientRect();
    const heads = [...wrap.querySelectorAll('thead th')];
    const named = (cell) => cell.firstChild.textContent.trim();
    const inside = (cell) => {
        const rect = cell.getBoundingClientRect();
        return rect.left >= edge.left - 1 && rect.right <= edge.right + 1;
    };
    return {
        scrollLeft: wrap.scrollLeft,
        visible: Object.fromEntries(heads.map((cell) => [named(cell), inside(cell)])),
        firstLeft: heads[0].getBoundingClientRect().left - edge.left,
    };
}"""

# 表の入れ物が右端まで送られたか
_AT_TABLE_END_JS = """() => {
    const wrap = document.querySelector('aside.panel .panel-body .md-table-wrap');
    return wrap.scrollLeft >= wrap.scrollWidth - wrap.clientWidth - 1;
}"""

# 本文のスクロール領域の上端から、表の見出しの行の上端までの距離（px）
_HEAD_OFFSET_JS = """() => {
    const area = document.querySelector('aside.panel .panel-body');
    const head = area.querySelector('.md-table-wrap thead th');
    return Math.abs(head.getBoundingClientRect().top - area.getBoundingClientRect().top);
}"""

# 表の入れ物の上端が、本文のスクロール領域の上端より上に出ているか
_TABLE_PAST_TOP_JS = """() => {
    const area = document.querySelector('aside.panel .panel-body');
    const wrap = area.querySelector('.md-table-wrap');
    return wrap.getBoundingClientRect().top < area.getBoundingClientRect().top - 1;
}"""

# パネルのすべり込みなどの動きが終わるまで待つ
_ANIMATIONS_FINISHED_JS = """async () => {
    await document.fonts.ready;
    await Promise.all(document.getAnimations().map((animation) => animation.finished));
}"""


def wait_table_rendered(page: Page) -> None:
    """詳細パネルに本文の表が置かれて、パネルのすべり込みなどの動きが終わるまで待つ。"""
    page.wait_for_selector(TABLE_WRAP, timeout=RENDER_TIMEOUT_MS)
    page.evaluate(_ANIMATIONS_FINISHED_JS)


def open_a4_from_cards(page: Page) -> None:
    """資料の画面のカードで A-4 を押し、詳細パネルに表が置かれて動きが終わるまで待つ。"""
    page.click('.doc-card[data-id="A-4"]')
    wait_table_rendered(page)


def table_layout(page: Page) -> dict[str, Any]:
    """本文の最初の表の、列の種類ごとの行数・説明の列の幅の数・横に送れるか・しま模様の色の数を返す。"""
    return page.evaluate(_TABLE_LAYOUT_JS)


def row_colors(page: Page) -> list[str]:
    """本文の最初の表の本体の行ごとに、先頭のセルの背景色を返す。"""
    return page.evaluate(_ROW_COLORS_JS)


def pinned_layout(page: Page) -> dict[str, Any]:
    """本文の最初の表の、横の送り量・列ごとに入れ物の中に見えているか・先頭の列の左端の位置を返す。"""
    return page.evaluate(_PINNED_LAYOUT_JS)


def _move_mouse_over(page: Page, selector: str) -> None:
    """マウスを、要素の上端から少し下の横の中央へ動かす（要素が画面より背が高くても画面の中に収まる）。"""
    box = page.locator(selector).bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + WHEEL_POINT_OFFSET_PX)


def scroll_table_to_end(page: Page) -> None:
    """表の上でマウスホイールを横に回して、表の入れ物を右端まで送る。"""
    _move_mouse_over(page, TABLE_WRAP)
    page.mouse.wheel(TABLE_WHEEL_PX, 0)
    page.wait_for_function(_AT_TABLE_END_JS)


def scroll_body_down(page: Page) -> None:
    """本文の上でマウスホイールを縦に回して、本文を表の途中まで進める。"""
    _move_mouse_over(page, PANEL_BODY)
    page.mouse.wheel(0, BODY_SCROLL_PX)
    page.wait_for_function(
        "scrollPx => document.querySelector('aside.panel .panel-body').scrollTop >= scrollPx - 1",
        arg=BODY_SCROLL_PX,
    )


def scroll_body_to_top(page: Page) -> None:
    """本文の上でマウスホイールを縦に回して、本文を先頭まで戻す。"""
    _move_mouse_over(page, PANEL_BODY)
    page.mouse.wheel(0, -TABLE_WHEEL_PX)
    page.wait_for_function("document.querySelector('aside.panel .panel-body').scrollTop === 0")


def head_offset_from_top(page: Page) -> float:
    """表の見出しの行の上端と、本文のスクロール領域の上端との距離（px）を返す。"""
    return page.evaluate(_HEAD_OFFSET_JS)


def wait_head_at_top(page: Page) -> None:
    """表の見出しの行が、本文のスクロール領域の上端に見えるまで待つ。"""
    page.wait_for_function(
        "tolerance => { const area = document.querySelector('aside.panel .panel-body');"
        " const head = area.querySelector('.md-table-wrap thead th');"
        " return Math.abs(head.getBoundingClientRect().top - area.getBoundingClientRect().top) <= tolerance; }",
        arg=POSITION_TOLERANCE_PX,
    )


def table_scrolled_past_top(page: Page) -> bool:
    """表の入れ物の上端が、本文のスクロール領域の上端より上へ送られているかを返す。"""
    return page.evaluate(_TABLE_PAST_TOP_JS)


def fold_button(page: Page, heading: str) -> Locator:
    """見出しの頭の、節を開閉する矢印のボタンを返す。"""
    return page.get_by_role("button", name=f"{heading}を開閉")


def heading_link_href(page: Page, heading: str) -> str | None:
    """見出しの `#` のリンクの href を返す。"""
    return page.get_by_role("link", name=f"見出し「{heading}」へのリンク").get_attribute("href")
