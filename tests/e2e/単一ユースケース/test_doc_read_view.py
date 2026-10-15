"""資料を読む（納品物を先頭にしたカードとボードで見て、絞り込み、カードから本文を開く）の E2E テスト。"""

from __future__ import annotations

from typing import Any

from preview_helpers import (
    OpenPreview,
    ServePreview,
    badge_text,
    close_drawer,
    open_drawer,
    toggle_value,
)
from workspace_fixtures import MakeItem

# 見出しと表を持つ資料の本文
SPEC_BODY = """## 仕様の見出し

| 項目 | 値 |
| --- | --- |
| 列 | 3 |
"""


def test_normal(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """納品物を先頭にカードを並べ、ボードで状態の列に分けて本文を読み、カードに戻して種類で絞り込み、本文を見出しと表で読む（正常系）。"""
    # 準備
    url = serve_preview(
        make_item("A-1", deliverable=False, kind="メモ書き", status="下書き"),
        make_item("A-2", deliverable=True, kind="仕様書", status="完成"),
        settings=valid_settings,
        bodies={"A-1.md": "メモ書きの本文\n", "A-2.md": SPEC_BODY},
    )
    # 実行
    page = open_preview(url, "#tab=docs")
    # 検証（カードの並びと状態）
    cards = page.eval_on_selector_all(".doc-card", "cards => cards.map(c => c.dataset.id)")
    assert cards == ["A-2", "A-1"]
    assert page.locator('.doc-card[data-id="A-2"] .deliv-badge').count() == 1
    assert page.locator('.doc-card[data-id="A-1"] .deliv-badge').count() == 0
    statuses = page.eval_on_selector_all(
        ".doc-card", "cards => cards.map(c => [c.dataset.id, c.querySelector('.st').dataset.st])"
    )
    assert statuses == [["A-2", "完成"], ["A-1", "下書き"]]
    # 表示形式をボードに切り替えると、状態の 3 列に分かれ、確認中の列は 0 件で出る
    page.click('.segment button[data-view="board"]')
    page.wait_for_selector(".board")
    columns = page.eval_on_selector_all(
        ".board section.board-col",
        """cols => cols.map(c => [
            c.getAttribute('aria-label'),
            c.querySelector('h2 .n').textContent,
            [...c.querySelectorAll('.card')].map(k => k.dataset.id),
        ])""",
    )
    assert columns == [["下書き", "1", ["A-1"]], ["確認中", "0", []], ["完成", "1", ["A-2"]]]
    # ボードの A-1 のカードを押すと、詳細パネルに A-1 の本文が出る
    page.click('.board .doc-card[data-id="A-1"]')
    page.wait_for_selector("aside.panel.open")
    page.wait_for_function(
        "document.querySelector('aside.panel .md')?.textContent.includes('メモ書きの本文')"
    )
    # 表示形式をカードに戻すと、納品物を先頭にしたカードが出る
    page.click('.segment button[data-view="cards"]')
    page.wait_for_selector(".doc-grid")
    assert page.eval_on_selector_all(".doc-card", "cards => cards.map(c => c.dataset.id)") == [
        "A-2",
        "A-1",
    ]
    # 絞り込みのボタンを押し、ドロワーで種類 = 仕様書を選ぶ
    open_drawer(page)
    toggle_value(page, "kind", "仕様書")
    page.wait_for_function("document.querySelectorAll('.doc-card').length === 1")
    close_drawer(page)
    assert page.eval_on_selector_all(".doc-card", "cards => cards.map(c => c.dataset.id)") == [
        "A-2"
    ]
    chips = page.eval_on_selector_all(".chips .chip", "chips => chips.map(c => c.textContent)")
    assert chips == ["種類: 仕様書"]
    assert badge_text(page) == "1"
    # カードを押すと、詳細パネルに本文が見出しと表で描かれる
    page.click('.doc-card[data-id="A-2"]')
    page.wait_for_selector('aside.panel.open .md [data-md-level="2"]')
    assert page.inner_text('aside.panel .md [data-md-level="2"]') == "仕様の見出し"
    assert page.locator("aside.panel .md table").count() == 1
    cells = page.eval_on_selector_all(
        "aside.panel .md td", "cells => cells.map(c => c.textContent)"
    )
    assert cells == ["列", "3"]


# カードとボードのカードごとに、資料の ID と形式の札の文言を返す
CARD_BADGES_SCRIPT = (
    "cards => cards.map(c => [c.dataset.id, c.querySelector('.doc-kind .fmt-badge')?.textContent])"
)


def test_normal_when_body_format_badge(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """カード・ボード・表のどれでも、本文の形式を札の文言（HTML / MD）で示す（正常系）。"""
    # 準備（A-1 は本文が Markdown の仕様書、A-2 は本文が HTML のモック）
    url = serve_preview(
        make_item("A-1", kind="仕様書"),
        make_item("A-2", kind="モック", body="A-2.html"),
        settings=valid_settings,
        bodies={"A-1.md": SPEC_BODY, "A-2.html": "<h1>画面のモック</h1>\n<p>一覧の画面</p>\n"},
    )
    # 実行（資料のタブを開く）
    page = open_preview(url, "#tab=docs")
    # 検証（カード）
    cards = page.eval_on_selector_all(".doc-card", CARD_BADGES_SCRIPT)
    assert sorted(cards) == [["A-1", "MD"], ["A-2", "HTML"]]
    # 実行（表示形式をボードに切り替える）
    page.click('.segment button[data-view="board"]')
    page.wait_for_selector(".board")
    # 検証（ボード）
    board = page.eval_on_selector_all(".board .doc-card", CARD_BADGES_SCRIPT)
    assert sorted(board) == [["A-1", "MD"], ["A-2", "HTML"]]
    # 実行（表示形式を表に切り替える）
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector("table.grid tbody tr")
    # 検証（表: 「形式」の列に HTML / MD）
    headers = page.eval_on_selector_all(
        "table.grid thead th", "ths => ths.map(th => th.textContent.trim())"
    )
    column = next(index for index, text in enumerate(headers) if text.startswith("形式"))
    cells = page.eval_on_selector_all(
        "table.grid tbody tr",
        f"rows => rows.map(r => [r.dataset.id, r.children[{column}].textContent.trim()])",
    )
    assert sorted(cells) == [["A-1", "MD"], ["A-2", "HTML"]]
