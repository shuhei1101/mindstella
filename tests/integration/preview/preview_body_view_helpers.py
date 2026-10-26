"""Markdown の本文の見せ方（表の列の固定・見出しの固定・しま模様・セクションの折りたたみ）の結合テストが共有する、ワークスペースの作り方と値、操作・読み取りの関数。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from playwright.sync_api import Page
from preview_head_title_helpers import ANIMATIONS_FINISHED_JS
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace

__all__ = [
    "BODY_VIEW_DIFF_HASH",
    "BODY_VIEW_HASH",
    "BODY_VIEW_SCOPE",
    "BODY_VIEW_VIEWPORT",
    "build_body_view_workspace",
    "open_body_view",
    "seed_body_view",
    "table_state",
]

# 詳細パネル（本文のスクロール領域を持つ外側）
BODY_VIEW_SCOPE = "aside.panel"

# 資料 A-4 を開く URL のハッシュと、差分の表示で開くハッシュ（まとまり V-1）
BODY_VIEW_HASH = "#tab=docs&id=A-4"
BODY_VIEW_DIFF_HASH = f"{BODY_VIEW_HASH}&diff=V-1"

# 開く画面の幅と高さ（資料の詳細パネルの本文の幅が 560px 以上になる）
BODY_VIEW_VIEWPORT = {"width": 1280, "height": 800}

# 表を描き終えるまで待つ上限ミリ秒
BODY_VIEW_TIMEOUT_MS = 15_000

# 表の行の数
ROW_COUNT = 20

# 表の見出しの行
_TABLE_HEAD = "| ID | 状態 | 名前 | 担当 | 期限 | 種別 | 優先度 | 説明 |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n"

# 説明の列の文（25 文字を超える長文）
_DESCRIPTION = "列の文字数で幅と折り返しを決め、表が本文の幅に収まらないときは表の中だけで横に送れるようにする。"


def _row(number: int, description: str = _DESCRIPTION) -> str:
    """表の 1 行（ID・状態・名前・担当・期限・種別・優先度・説明の 8 列）を返す。"""
    return f"| D-{number} | 検討中 | 本文の表の見せ方を決める {number} | 佐藤 | 2026-10-{number:02d} | 設計 | 高 | {description} |\n"


def _body(*, rows: int, description_of_second: str = _DESCRIPTION) -> str:
    """見出し「比較」の下に表を置き、見出し「まとめ」の下に段落を置いた本文を返す。"""
    lines = [_row(number, description_of_second if number == 2 else _DESCRIPTION) for number in range(1, rows + 1)]
    return f"## 比較\n\n{_TABLE_HEAD}{''.join(lines)}\n## まとめ\n\n表の見せ方をまとめた段落です。\n"


# 書き換える前の本文（2 行目の説明が違い、最後の行が無い）と、書き換えた後の本文
BODY_BEFORE = _body(rows=ROW_COUNT - 1, description_of_second="書き換える前の説明です。")
BODY_AFTER = _body(rows=ROW_COUNT)

# 表の状態を返す（見出しの行・入れ物・固定した列・縦の位置・横の送り）
_TABLE_STATE_JS = """(scope) => {
    const area = document.querySelector(`${scope} .panel-body`);
    const wrap = area.querySelector('.md-table-wrap');
    const frame = wrap.parentElement;
    const heads = [...wrap.querySelectorAll('thead th')];
    const edge = wrap.getBoundingClientRect().left;
    const fontSize = parseFloat(getComputedStyle(heads[heads.length - 1]).fontSize);
    const named = (cell) => cell.firstChild.textContent.trim();
    return {
        names: heads.map(named),
        sizes: heads.map((cell) => cell.dataset.colSize),
        widths: Object.fromEntries(heads.map((cell) => [named(cell), cell.getBoundingClientRect().width / fontSize])),
        nowraps: Object.fromEntries(heads.map((cell, index) => [named(cell), getComputedStyle(wrap.querySelectorAll('tbody tr:first-child td')[index]).whiteSpace === 'nowrap'])),
        fill: wrap.querySelector('tbody').getBoundingClientRect().width <= wrap.clientWidth + 1 && wrap.scrollWidth <= wrap.clientWidth,
        wrapScrolls: wrap.scrollWidth > wrap.clientWidth,
        fade: frame.hasAttribute('data-fade'),
        scrollLeft: wrap.scrollLeft,
        pinned: heads.filter((cell) => cell.classList.contains('md-pinned')).map(named),
        pinnedLefts: heads.filter((cell) => cell.classList.contains('md-pinned')).map((cell) => cell.getBoundingClientRect().left - edge),
        pinnedRights: heads.filter((cell) => cell.classList.contains('md-pinned')).map((cell) => cell.getBoundingClientRect().right - edge),
        lastLeft: heads[heads.length - 1].getBoundingClientRect().left - edge,
        wrapWidth: wrap.clientWidth,
        areaTop: area.getBoundingClientRect().top,
        headTop: heads[0].getBoundingClientRect().top,
        stuck: wrap.querySelector('table').classList.contains('md-head-stuck'),
        rowColors: [...wrap.querySelectorAll('tbody tr')].map((row) => getComputedStyle(row.firstElementChild).backgroundColor),
    };
}"""


def _call(call_tool: CallTool, name: str, **arguments: Any) -> None:
    """ツールを呼び、エラーでないことを確かめる。"""
    result = call_tool(name, **arguments)
    assert result.is_error is False, result.text


def build_body_view_workspace(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool) -> Path:
    """8 列の表と見出し「比較」「まとめ」を持つ資料 A-4 を、2 行目の説明を書き換え最後の行を足して `commit`（V-1）したワークスペースを作る。"""
    root = make_workspace(make_item("A-4"), bodies={"A-4.md": BODY_BEFORE})
    workspace = str(root)
    _call(call_tool, "update", workspace=workspace, id="A-4", item={"body_markdown": BODY_AFTER})
    _call(call_tool, "commit", workspace=workspace, summary="表を直す")
    return root


def seed_body_view(page: Page, prefs: dict[str, Any]) -> None:
    """ページを開く前に、端末の保存領域へ個人の上書き（本文の見せ方・差分の並べ方・選んだ時点）を入れる。"""
    value = json.dumps(prefs)
    page.add_init_script(
        "try { if (!sessionStorage.getItem('mindmap-seeded')) {"
        f" localStorage.setItem('mindmap-preview', {json.dumps(value)});"
        " sessionStorage.setItem('mindmap-seeded', '1'); } } catch (e) {}"
    )


def open_body_view(page: Page, open_preview: Any, url: str, hash_text: str = BODY_VIEW_HASH) -> Page:
    """画面の幅を決めてから、ハッシュを付けて開き、表が置かれて、パネルの動きが終わるまで待つ。"""
    page.set_viewport_size(BODY_VIEW_VIEWPORT)
    open_preview(url, hash_text)
    page.wait_for_selector(f"{BODY_VIEW_SCOPE} .md-table-wrap", timeout=BODY_VIEW_TIMEOUT_MS)
    # パネルのすべり込みの間は位置が動くため、終わってから操作する
    page.evaluate(ANIMATIONS_FINISHED_JS)
    return page


def table_state(page: Page, scope: str = BODY_VIEW_SCOPE) -> dict[str, Any]:
    """本文の最初の表の、列の種類・幅・折り返し・固定・縦の位置・横の送りを返す。"""
    return page.evaluate(_TABLE_STATE_JS, scope)
