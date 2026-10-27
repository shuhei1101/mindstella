"""埋め込んだ HTML・操作できる部品・資料のエクスポートの結合テストが共有する値と関数。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from playwright.sync_api import Download, Locator, Page
from workspace_fixtures import CallTool, MakeWorkspace

__all__ = [
    "CHART",
    "CLIPBOARD_PERMISSIONS",
    "EMBEDDED_BODY",
    "EMBED_TIMEOUT_MS",
    "EXPORT_BODY",
    "EXPORT_ENTRY_NAME",
    "EXPORT_MENU",
    "MARKDOWN_EXPORT_BODY",
    "MDMARK_URL_PATTERN",
    "OUTSIDE_ONLY_AFTER",
    "OUTSIDE_ONLY_BEFORE",
    "RANGE",
    "ZOOM_FIT",
    "ZOOM_IN",
    "build_embedded_diff_workspace",
    "drag_in_viewport",
    "save_download",
    "viewport_scroll",
]

# チャートを描き終わるまで待つ上限ミリ秒
EMBED_TIMEOUT_MS = 20_000

# 詳細パネルの本文の中の、埋め込んだ HTML の範囲と、その中のチャート・倍率の操作
RANGE = "aside.panel .md .mdmark-html"
CHART = f"{RANGE} figure.mdmark-diagram"
ZOOM_IN = 'button[data-tool="in"]'
ZOOM_FIT = "button.mdmark-diagram-zoom"

# 「エクスポート」の入口の読み上げの名前と、メニューの要素
EXPORT_ENTRY_NAME = "エクスポート"
EXPORT_MENU = "div.doc-export"

# クリップボードの読み書きを許す権限
CLIPBOARD_PERMISSIONS = ["clipboard-read", "clipboard-write"]

# mdmark の CSS と JavaScript の配信元の URL
MDMARK_URL_PATTERN = "https://cdn.jsdelivr.net/gh/shuhei1101/mdmark@*/dist/index.*"

# 埋め込んだ HTML の範囲に置くチャート（JSON の定義）
CHART_DEFINITION: dict[str, Any] = {
    "type": "bar",
    "title": "件数",
    "scope": "10 月",
    "updated": "2026-10-27",
    "x": {"label": "窓口", "ticks": ["メール", "電話"]},
    "y": {"label": "件"},
    "series": [{"name": "自動返信", "points": [10, 20]}],
}

# 埋め込んだ HTML の範囲に置く、キー rps のスライダーを持つ操作できる部品（JSON の定義）
PARAM_DEFINITION: dict[str, Any] = {
    "title": "リクエスト数の見積もり",
    "knob": {"key": "rps", "label": "リクエスト数", "min": 0, "max": 10, "step": 1, "value": 5},
    "chart": {
        "title": "応答時間",
        "scope": "ピーク時",
        "updated": "2026-10-27",
        "x": {"label": "経過", "ticks": ["0", "1"]},
        "y": {"label": "ミリ秒", "min": 0, "max": 100, "step": 50},
    },
    "table": {str(value): [value * 10, value * 10 + 5] for value in range(11)},
}

# 本文に置くチャートと操作できる部品の要素
CHART_ELEMENT = f"<mdmark-chart>{json.dumps(CHART_DEFINITION, ensure_ascii=False)}</mdmark-chart>"
PARAM_ELEMENT = f"<mdmark-param>{json.dumps(PARAM_DEFINITION, ensure_ascii=False)}</mdmark-param>"

# 範囲を 1 つ持つ本文（範囲は半角カナと後ろの空白を含む段落・チャート・部品・実行されるスクリプトと `onclick` を持つボタンを持つ）
EMBEDDED_BODY = (
    "範囲の外の文\n\n"
    "<!-- html -->\n```html\n"
    "<p>ﾋﾟｰｸ時の応答時間 と A-2</p>\n"
    f"{CHART_ELEMENT}{PARAM_ELEMENT}\n"
    '<script>window.__script = 1</script><button onclick="window.__onclick = 1">実行</button>\n'
    "```\n<!-- /html -->\n\n"
    "後ろの文\n"
)

# エクスポートする本文（用語に当たる段落と、チャートと部品を持つ範囲）
EXPORT_BODY = (
    "応答時間の段落\n\n"
    "<!-- html -->\n```html\n"
    f"{CHART_ELEMENT}{PARAM_ELEMENT}\n"
    "```\n<!-- /html -->\n"
)

# Markdown でエクスポートする本文（範囲の外の段落と、範囲の中の段落）
MARKDOWN_EXPORT_BODY = "範囲の外の文\n\n<!-- html -->\n```html\n<p>範囲の中の文</p>\n```\n<!-- /html -->\n"

# 範囲の差分の本文（段落 1 つと、段落 3 つを 1 行ずつ持つ範囲 1 つ。2 つ目の段落を書き換える）
DIFF_BODY_BEFORE = (
    "範囲の外の段落\n\n"
    "<!-- html -->\n```html\n"
    "<p>1 つ目の段落</p>\n<p>2 つ目の段落</p>\n<p>3 つ目の段落</p>\n"
    "```\n<!-- /html -->\n"
)
DIFF_BODY_AFTER = DIFF_BODY_BEFORE.replace("<p>2 つ目の段落</p>", "<p>書き直した 2 つ目の段落</p>")

# 範囲の外の段落だけを書き換える本文（範囲の中身は同じ）
OUTSIDE_ONLY_BEFORE = DIFF_BODY_BEFORE
OUTSIDE_ONLY_AFTER = DIFF_BODY_BEFORE.replace("範囲の外の段落", "書き直した範囲の外の段落")


def build_embedded_diff_workspace(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    *,
    before: str = DIFF_BODY_BEFORE,
    after: str = DIFF_BODY_AFTER,
) -> Path:
    """範囲を持つ Markdown の本文の資料 A-1 を `before` で足して `commit`（V-1）し、`after` へ書き換えて `commit`（V-2、説明「直す」）したワークスペースを作る。"""
    root = make_workspace()
    workspace = str(root)
    doc = {"title": "範囲を持つ資料", "kind": "図", "deliverable": False, "status": "下書き"}
    steps = (
        ("add", {"kind": "doc", "item": {**doc, "body_markdown": before}}),
        ("commit", {"summary": "足す"}),
        ("update", {"id": "A-1", "item": {"body_markdown": after}}),
        ("commit", {"summary": "直す"}),
    )
    for name, arguments in steps:
        result = call_tool(name, workspace=workspace, **arguments)
        assert result.is_error is False, result.text
    return root


def save_download(download: Download, directory: Path) -> Path:
    """ダウンロードを、提案された名前のまま `directory` に保存して返す（ブラウザの一時のファイル名には拡張子が無く、HTML として開けない）。"""
    path = directory / download.suggested_filename
    download.save_as(str(path))
    return path


def viewport_scroll(figure: Locator) -> dict[str, float]:
    """チャートの表示の領域のスクロールの位置（左・上）を返す。"""
    return figure.evaluate(
        "figure => { const v = figure.querySelector('.mdmark-diagram-viewport'); return {left: v.scrollLeft, top: v.scrollTop}; }"
    )


def drag_in_viewport(page: Page, figure: Locator, *, dx: int, dy: int) -> None:
    """チャートの表示の領域の中央から `dx`・`dy` だけマウスでドラッグする（領域を画面の中へ送ってから始める）。"""
    viewport = figure.locator(".mdmark-diagram-viewport")
    viewport.scroll_into_view_if_needed()
    box = viewport.bounding_box()
    assert box is not None
    center_x = box["x"] + box["width"] / 2
    center_y = box["y"] + box["height"] / 2
    page.mouse.move(center_x, center_y)
    page.mouse.down()
    # 一度に動かさず、細かく動かして押したままの動きとして届ける
    steps = 10
    for step in range(1, steps + 1):
        page.mouse.move(center_x + dx * step / steps, center_y + dy * step / steps)
        page.wait_for_timeout(30)
    page.mouse.up()
