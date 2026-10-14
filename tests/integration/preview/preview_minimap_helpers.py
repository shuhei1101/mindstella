"""差分のミニマップの結合テストが共有する、ワークスペースの作り方と値、操作・読み取りの関数。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import Page
from preview_body_scroll_helpers import SETTLED_SCROLL_TOP_JS
from preview_fixture_types import OpenPreview
from preview_head_title_helpers import ANIMATIONS_FINISHED_JS
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace

__all__ = [
    "FULL_SCOPE",
    "MINIMAP_FULL_HASH",
    "MINIMAP_HASH",
    "MINIMAP_TIMEOUT_MS",
    "MINIMAP_VIEWPORT",
    "PANEL_SCOPE",
    "added_paragraph_in_view",
    "build_minimap_workspace",
    "drag_view",
    "hide_minimap_in_storage",
    "map_metrics",
    "mark_at_empty_area",
    "mark_shapes",
    "marks_of_map",
    "open_minimap",
    "press_empty_area",
    "scroll_top",
]

# 詳細パネルと詳細の全画面（本文のスクロール領域とミニマップを持つ外側）
PANEL_SCOPE = "aside.panel"
FULL_SCOPE = "dialog.full"

# 差分の表示で A-1 を開く URL のハッシュ（まとまり V-1）と、全画面で開くハッシュ
MINIMAP_HASH = "#tab=docs&id=A-1&diff=V-1"
MINIMAP_FULL_HASH = f"{MINIMAP_HASH}&full=1"

# 開く画面の幅と高さ
MINIMAP_VIEWPORT = {"width": 1280, "height": 800}

# ミニマップの印が置かれるまで待つ上限ミリ秒
MINIMAP_TIMEOUT_MS = 15_000

# 書き換える前の A-1 の本文（本文のスクロール領域の高さを超える 40 個の段落）
MINIMAP_BODY_BEFORE = (
    "\n\n".join(
        f"{number} 番目の段落です。本文を縦に長くするための文です。" for number in range(1, 41)
    )
    + "\n"
)

# 足した段落
ADDED_PARAGRAPH = "足した段落です。"

# 書き換えた後の A-1 の本文（1 つ目の段落を消し、末尾に段落を 1 つ足す）
MINIMAP_BODY_AFTER = (
    "\n\n".join(
        [f"{number} 番目の段落です。本文を縦に長くするための文です。" for number in range(2, 41)]
        + [ADDED_PARAGRAPH]
    )
    + "\n"
)

# 書き換えていない A-2 の本文
UNCHANGED_BODY = "変わらない本文です。\n"

# 帯・本文・枠の位置と、本文の送りを返す
_METRICS_JS = """(scope) => {
    const body = document.querySelector(`${scope} .panel-body`);
    const map = document.querySelector(`${scope} .df-map`);
    const view = document.querySelector(`${scope} .df-map-view`);
    const bodyRect = body.getBoundingClientRect();
    const mapRect = map.getBoundingClientRect();
    const viewRect = view.getBoundingClientRect();
    return {
        bodyRight: bodyRect.right,
        bodyWidth: bodyRect.width,
        scrollbar: body.offsetWidth - body.clientWidth,
        mapLeft: mapRect.left,
        mapTop: mapRect.top,
        mapWidth: mapRect.width,
        mapHeight: mapRect.height,
        viewTop: viewRect.top,
        viewHeight: viewRect.height,
        viewHidden: view.hidden,
        scrollTop: body.scrollTop,
        clientHeight: body.clientHeight,
        scrollHeight: body.scrollHeight,
    };
}"""

# 印ごとに、種類のクラス・読み上げの名前・形（枠の太さ・塗り・縞か）・位置と高さを返す
_SHAPES_JS = """(scope) => [...document.querySelectorAll(`${scope} .df-map .df-map-m`)].map((mark) => {
    const shape = getComputedStyle(mark.querySelector('i'));
    const rect = mark.getBoundingClientRect();
    return {
        kind: [...mark.classList].find((name) => /^df-(add|del|chg)$/.test(name)) ?? null,
        label: mark.getAttribute('aria-label'),
        border: shape.borderTopWidth,
        fill: shape.backgroundColor,
        stripes: shape.backgroundImage.startsWith('repeating-linear-gradient'),
        top: rect.top,
        height: rect.height,
    };
})"""

# 足した段落が、本文のスクロール領域の見える範囲に入っているか
_ADDED_IN_VIEW_JS = """([scope, text]) => {
    const body = document.querySelector(`${scope} .panel-body`);
    const added = [...body.querySelectorAll('ins.df-blk')].find((block) => block.textContent.includes(text));
    const bodyRect = body.getBoundingClientRect();
    const addedRect = added.getBoundingClientRect();
    return addedRect.top >= bodyRect.top && addedRect.bottom <= bodyRect.bottom;
}"""

# 画面上の座標にある要素が、印（またはその中）か
_MARK_AT_POINT_JS = """([x, y]) =>
    (document.elementFromPoint(x, y)?.closest('.df-map-m') ?? null) !== null"""


def build_minimap_workspace(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> Path:
    """本文に段落を 40 個持つ資料 A-1 の 1 つ目の段落を消し、末尾に段落を足して `commit`（V-1）した、A-2 を持つワークスペースを作る。"""
    root = make_workspace(
        make_item("A-1"),
        make_item("A-2"),
        bodies={"A-1.md": MINIMAP_BODY_BEFORE, "A-2.md": UNCHANGED_BODY},
    )
    workspace = str(root)
    updated = call_tool(
        "update", workspace=workspace, id="A-1", item={"body_markdown": MINIMAP_BODY_AFTER}
    )
    assert updated.is_error is False, updated.text
    committed = call_tool("commit", workspace=workspace, summary="段落を消して足す")
    assert committed.is_error is False, committed.text
    return root


def hide_minimap_in_storage(page: Page) -> None:
    """ページを開く前に、端末の保存領域へ差分のミニマップを表示しない上書きを入れる。"""
    page.add_init_script(
        "try { if (!sessionStorage.getItem('mindmap-seeded')) {"
        " localStorage.setItem('mindmap-preview', JSON.stringify({ minimap: false }));"
        " sessionStorage.setItem('mindmap-seeded', '1'); } } catch (e) {}"
    )


def open_minimap(page: Page, open_preview: OpenPreview, url: str, hash_text: str) -> Page:
    """画面の幅を決めてから、ハッシュを付けて開き、ミニマップの印が置かれて、パネルの動きが終わるまで待つ。"""
    page.set_viewport_size(MINIMAP_VIEWPORT)
    open_preview(url, hash_text)
    page.wait_for_selector(".df-map .df-map-m", timeout=MINIMAP_TIMEOUT_MS)
    # パネルのすべり込みの間は位置が動くため、終わってから操作する
    page.evaluate(ANIMATIONS_FINISHED_JS)
    return page


def map_metrics(page: Page, scope: str) -> dict[str, Any]:
    """帯・本文・見えている範囲の面の位置と、本文の送りを返す。"""
    return page.evaluate(_METRICS_JS, scope)


def mark_shapes(page: Page, scope: str) -> list[dict[str, Any]]:
    """帯の印を上から、種類・読み上げの名前・形・位置と高さで返す。"""
    return page.evaluate(_SHAPES_JS, scope)


def marks_of_map(page: Page, scope: str) -> int:
    """帯が持つ印の数を返す。"""
    return page.locator(f"{scope} .df-map .df-map-m").count()


def added_paragraph_in_view(page: Page, scope: str) -> bool:
    """足した段落が、本文のスクロール領域の見える範囲に入っているかを返す。"""
    return page.evaluate(_ADDED_IN_VIEW_JS, [scope, ADDED_PARAGRAPH])


def scroll_top(page: Page, scope: str) -> float:
    """本文のスクロール領域の送りが止まるのを待って、その位置を返す。"""
    return page.evaluate(SETTLED_SCROLL_TOP_JS, f"{scope} .panel-body")


def _empty_area_point(page: Page, scope: str, *, offset_y: float) -> tuple[float, float]:
    """帯の上端から offset_y の位置（印の無い所）の、画面上の座標を返す。"""
    box = page.locator(f"{scope} .df-map").bounding_box()
    assert box is not None
    return box["x"] + box["width"] / 2, box["y"] + offset_y


def mark_at_empty_area(page: Page, scope: str, *, offset_y: float) -> bool:
    """帯の上端から offset_y の位置にある要素が、印（またはその中）かを返す。"""
    x, y = _empty_area_point(page, scope, offset_y=offset_y)
    return page.evaluate(_MARK_AT_POINT_JS, [x, y])


def press_empty_area(page: Page, scope: str, *, offset_y: float) -> None:
    """帯の上端から offset_y の位置（印の無い所）を押す。"""
    x, y = _empty_area_point(page, scope, offset_y=offset_y)
    page.mouse.click(x, y)


def drag_view(page: Page, scope: str, *, delta_y: float) -> None:
    """見えている範囲の面の中央をマウスで押し、押したまま delta_y だけ動かして離す。"""
    box = page.locator(f"{scope} .df-map-view").bounding_box()
    assert box is not None
    x = box["x"] + box["width"] / 2
    y = box["y"] + box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x, y + delta_y, steps=8)
    page.mouse.up()
