"""埋め込んだ HTML・操作できる部品・資料の書き出しの E2E テストが共有する値と関数。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from playwright.sync_api import Download, Locator, Page

__all__ = [
    "CHART",
    "CHART_ELEMENT",
    "CLIPBOARD_PERMISSIONS",
    "EMBED_TIMEOUT_MS",
    "EXPORT_BODY",
    "EXPORT_ENTRY_NAME",
    "EXPORT_MENU",
    "MARKDOWN_EXPORT_BODY",
    "PARAM_ELEMENT",
    "RANGE",
    "ZOOM_FIT",
    "ZOOM_IN",
    "drag_in_viewport",
    "save_download",
    "viewport_scroll",
]

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

# チャートを描き終わるまで待つ上限ミリ秒
EMBED_TIMEOUT_MS = 20_000

# 範囲に置くチャート（JSON の定義）
CHART_DEFINITION: dict[str, Any] = {
    "type": "bar",
    "title": "件数",
    "scope": "10 月",
    "updated": "2026-10-27",
    "x": {"label": "窓口", "ticks": ["メール", "電話"]},
    "y": {"label": "件"},
    "series": [{"name": "自動返信", "points": [10, 20]}],
}

# 範囲に置く、キー rps のスライダーを持つ操作できる部品（JSON の定義）
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

# 書き出す本文（用語に当たる段落と、チャートと部品を持つ範囲）
EXPORT_BODY = (
    "応答時間の段落\n\n"
    "<!-- html -->\n```html\n"
    f"{CHART_ELEMENT}{PARAM_ELEMENT}\n"
    "```\n<!-- /html -->\n"
)

# Markdown で書き出す本文（範囲の外の段落と、範囲の中の段落）
MARKDOWN_EXPORT_BODY = "範囲の外の段落\n\n<!-- html -->\n```html\n<p>範囲の中の段落</p>\n```\n<!-- /html -->\n"


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
