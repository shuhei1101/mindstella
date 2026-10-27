"""資料を読む（納品物を先頭にしたカードとボードで見て、絞り込み、カードから本文を開く）の E2E テスト。"""

from __future__ import annotations

import json
from typing import Any

from embed_helpers import (
    CHART,
    CHART_ELEMENT,
    CLIPBOARD_PERMISSIONS,
    EMBED_TIMEOUT_MS,
    PARAM_ELEMENT,
    RANGE,
    ZOOM_FIT,
    ZOOM_IN,
    drag_in_viewport,
    viewport_scroll,
)
from playwright.sync_api import Page, expect
from preview_helpers import (
    OpenPreview,
    ServeWorkspace,
    ServePreview,
    badge_text,
    close_drawer,
    open_drawer,
    snapshot_records,
    toggle_value,
)
from workspace_fixtures import MakeItem, SnapshotTree

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


# 段落（「応答時間」と A-2 を含む）・埋め込んだ HTML の範囲（同じ文を含む段落・チャート・スライダー・スクリプト・onclick を持つボタン）・範囲の外の html のコードブロックを持つ本文
EMBEDDED_BODY = (
    "応答時間と A-2 を読む段落\n\n"
    "<!-- html -->\n```html\n"
    "<p>ﾋﾟｰｸ時の応答時間 と A-2</p>\n"
    f"{CHART_ELEMENT}{PARAM_ELEMENT}\n"
    '<script>window.__script = 1</script><button onclick="window.__onclick = 1">実行</button>\n'
    "```\n<!-- /html -->\n\n"
    "```html\n<p>範囲の外の html</p>\n```\n"
)

# 範囲の外の html のコードブロックを描いた、HTML の本文の枠
OUTSIDE_HTML_FRAME = "aside.panel .md iframe.html-frame"


def test_normal_when_embedded_html_and_parts(
    serve_workspace: ServeWorkspace,
    open_preview: OpenPreview,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    page: Page,
) -> None:
    """埋め込んだ HTML を本文の中に描き、チャートを動かし、スライダーを動かして今の値の JSON をコピーし、用語のツールチップと項目へのリンクを使う（正常系）。"""
    # 準備
    page.context.grant_permissions(CLIPBOARD_PERMISSIONS)
    url, root = serve_workspace(
        make_item("A-1", title="埋め込む資料"),
        make_item("A-2"),
        make_item("G-1", title="用語", aliases=["応答時間"], meaning="返すまでの時間"),
        bodies={"A-1.md": EMBEDDED_BODY},
    )
    before = snapshot_records(snapshot_tree(root))
    # 実行（資料のタブで A-1 を押す）
    open_preview(url, "#tab=docs")
    page.click('.doc-card[data-id="A-1"]')
    page.wait_for_selector(CHART, timeout=EMBED_TIMEOUT_MS)
    page.get_by_role("button", name="実行", exact=True).click()
    # 検証（範囲の HTML が要素で描かれ、範囲の中のスクリプトは動かず文書にも残らない）
    assert page.locator("aside.panel .md > .mdmark-html").count() == 1
    assert page.locator(f"{RANGE} script, {RANGE} [onclick]").count() == 0
    assert page.evaluate("[window.__script, window.__onclick]") == [None, None]
    # 検証（範囲の外の html のコードブロックは、今のまま HTML の本文の枠で描かれる）
    expect(page.locator(OUTSIDE_HTML_FRAME)).to_have_count(1)
    assert page.get_attribute(OUTSIDE_HTML_FRAME, "sandbox") == "allow-same-origin"
    # 実行（チャートを拡大して、拡大したチャートをドラッグする）
    chart = page.locator(CHART).first
    fit_before = int(chart.locator(ZOOM_FIT).inner_text().rstrip("%"))
    chart.locator(ZOOM_IN).click()
    chart.locator(ZOOM_IN).click()
    fit_after = int(chart.locator(ZOOM_FIT).inner_text().rstrip("%"))
    scroll_before = viewport_scroll(chart)
    drag_in_viewport(page, chart, dx=-80, dy=-50)
    scroll_after = viewport_scroll(chart)
    # 検証（倍率が上がり、表示の位置が変わる。図の拡大の画面は開かない）
    assert fit_after > fit_before
    assert scroll_after["left"] > scroll_before["left"]
    assert scroll_after["top"] > scroll_before["top"]
    assert page.locator("dialog.viewer[open]").count() == 0
    # 検証（拡大・縮小のボタンはチャートだけにあり、段落とスライダーには付かない）
    assert page.locator(f"{RANGE} {ZOOM_IN}").count() == page.locator(CHART).count()
    assert page.locator(f"{RANGE} p [data-tool], {RANGE} .mdmark-param-knob [data-tool]").count() == 0
    # 実行（スライダーを矢印キーで動かし、今の値をコピーするボタンを押す）
    page.focus(f"{RANGE} input[type=range]")
    page.keyboard.press("ArrowRight")
    page.get_by_role("button", name="今の値をコピー").click()
    # 検証（値とグラフが描き直され、クリップボードに今の値の JSON が入る）
    assert page.inner_text(f"{RANGE} .mdmark-param output") == "6"
    assert "今の値（6）" in page.inner_text(f"{RANGE} .mdmark-param .mdmark-diagram-legend")
    assert json.loads(page.evaluate("navigator.clipboard.readText()")) == {
        "rps": {"name": "リクエスト数", "value": 6}
    }
    # 検証（段落と範囲の中の「応答時間」の両方に用語のマーカーが付く）
    assert page.locator("aside.panel .md > p a.term").count() == 1
    assert page.locator(f"{RANGE} a.term").count() == 1
    # 実行（範囲の中の「応答時間」のマーカーに乗せる）
    page.hover(f"{RANGE} a.term")
    # 検証（G-1 のツールチップが出る）
    expect(page.locator("#term-tip")).to_be_visible()
    expect(page.locator("#term-tip")).to_contain_text("返すまでの時間")
    # 実行（範囲の中の A-2 のリンクを押す）
    history_length = page.evaluate("history.length")
    page.click(f"{RANGE} a.idref")
    # 検証（A-2 の詳細パネルへ移り、履歴に積まれる）
    expect(page.locator("aside.panel .d-title")).to_have_text("A-2の題")
    assert page.evaluate("location.hash") == "#tab=docs&id=A-2"
    assert page.evaluate("history.length") == history_length + 1
    # ワークスペースの YAML と本文の中身が、開く前と同じ
    assert snapshot_records(snapshot_tree(root)) == before
