"""HTML の本文の画面の結合テストが共有する値と、枠の中の選択・測りの関数。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Frame, Page

__all__ = [
    "BODY_FRAME",
    "BODY_WITH_HTML_CODE_BLOCK",
    "BODY_WITHOUT_HTML_CODE_BLOCK",
    "LEAKING_HTML_BODY",
    "MARKED_FRAME",
    "FRAME_SETTLE_MS",
    "drag_select_in_frame",
    "frame_height_gap",
    "frame_of",
    "leak_counts",
    "select_in_frame",
    "style_snapshot",
    "text_rect_in_page",
    "wait_frame_rendered",
]

# 詳細パネルの HTML の本文の枠
BODY_FRAME = "aside.panel iframe.html-frame[data-html-body]"

# 差分の表示の間、描いた結果を入れる枠
MARKED_FRAME = "aside.panel .html-marked iframe.html-frame"

# 枠の描き終わり・高さ合わせ・選択の判定が済むまで待つミリ秒
FRAME_SETTLE_MS = 400

# 枠を描き終えるまで待つ上限ミリ秒
FRAME_RENDER_TIMEOUT_MS = 15_000

# マウスで選ぶときの動かす回数
DRAG_STEPS = 6

# 本文の CSS が画面へ漏れるかを確かめる、全てに `!important` で塗る本文（スクリプト・`onerror`・`onclick` は印を残そうとする）
LEAKING_HTML_BODY = """<style>
  * { color: rgb(255, 0, 0) !important; margin: 40px !important; }
  body { background: rgb(0, 0, 255) !important; padding: 40px !important; }
  p { color: rgb(0, 128, 0) !important; margin: 24px !important; }
</style>
<h1>画面のモック</h1>
<p>一覧の画面</p>
<table><tr><th>列</th><td>値</td></tr></table>
<svg width="40" height="40"><circle cx="20" cy="20" r="18" fill="orange"/></svg>
<script>window.__leak = 1; parent.__leak = 1;</script>
<img src="x" onerror="window.__leak = 1; parent.__leak = 1">
<button id="click" onclick="window.__leak = 1; parent.__leak = 1">押す</button>
"""

# 言語指定 `html` のコードブロックを持つ本文（コードブロックは `<style>` で `p` を塗り、スクリプトを持つ）
BODY_WITH_HTML_CODE_BLOCK = """# 見出し

前の段落

```html
<style>p { color: rgb(255, 0, 0) !important; margin: 40px !important; }</style>
<p>枠の中の段落</p>
<script>parent.__leak = 1;</script>
```

後の段落
"""

# `html` のコードブロックを持たない、前後の段落だけの本文（描く前の色の見本）
BODY_WITHOUT_HTML_CODE_BLOCK = """# 見出し

前の段落

後の段落
"""

# 枠の中の文を、始まりから終わりまで選んで `pointerup` を送る
SELECT_IN_FRAME_SCRIPT = """([startText, endText]) => {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let start = null;
  let end = null;
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (start === null && node.data.includes(startText)) {
      start = [node, node.data.indexOf(startText)];
    }
    if (start !== null && node.data.includes(endText, start[0] === node ? start[1] : 0)) {
      const from = start[0] === node ? start[1] : 0;
      end = [node, node.data.indexOf(endText, from) + endText.length];
      break;
    }
  }
  const range = document.createRange();
  range.setStart(start[0], start[1]);
  range.setEnd(end[0], end[1]);
  const selection = getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
  document.dispatchEvent(new Event("pointerup"));
}"""

# 枠の中の文の矩形に、枠の位置を足した親の画面の座標を返す
TEXT_RECT_SCRIPT = """([selector, text]) => {
  const frame = document.querySelector(selector);
  const doc = frame.contentDocument;
  const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    const at = node.data.indexOf(text);
    if (at < 0) continue;
    const range = doc.createRange();
    range.setStart(node, at);
    range.setEnd(node, at + text.length);
    const rect = range.getBoundingClientRect();
    const outer = frame.getBoundingClientRect();
    return {
      left: outer.left + frame.clientLeft + rect.left,
      top: outer.top + frame.clientTop + rect.top,
      width: rect.width,
      height: rect.height,
    };
  }
  return null;
}"""

# 枠の高さと、中の文書の高さの差（px）を返す
HEIGHT_GAP_SCRIPT = """(selector) => {
  const frame = document.querySelector(selector);
  return Math.abs(frame.clientHeight - frame.contentDocument.documentElement.scrollHeight);
}"""

# 画面に残る印（本文のスクリプトが動くと立つ変数）を、親の画面と枠の中で数える
LEAK_SCRIPT = """(selector) => {
  const frame = document.querySelector(selector);
  return { parent: window.__leak || 0, frame: frame.contentWindow.__leak || 0 };
}"""

# 要素の色・余白・背景を返す
STYLE_SCRIPT = """(selectors) => Object.fromEntries(selectors.map((selector) => {
  const style = getComputedStyle(document.querySelector(selector));
  return [selector, {
    color: style.color,
    margin: style.margin,
    padding: style.padding,
    background: style.backgroundColor,
  }];
}))"""


def wait_frame_rendered(page: Page, selector: str) -> None:
    """枠が描き終わり（`data-rendered`）、高さ合わせが済むまで待つ。"""
    page.wait_for_selector(f"{selector}[data-rendered]", state="attached", timeout=FRAME_RENDER_TIMEOUT_MS)
    page.wait_for_timeout(FRAME_SETTLE_MS)


def frame_of(page: Page, selector: str) -> Frame:
    """枠（iframe）の中の文書の Frame を返す。"""
    handle = page.locator(selector).first.element_handle()
    frame = handle.content_frame()
    assert frame is not None, f"{selector} の中の文書がありません"
    return frame


def select_in_frame(page: Page, selector: str, start_text: str, end_text: str) -> None:
    """枠の中で start_text の頭から end_text の終わりまでを選び、`pointerup` を送る。"""
    frame_of(page, selector).evaluate(SELECT_IN_FRAME_SCRIPT, [start_text, end_text])


def text_rect_in_page(page: Page, selector: str, text: str) -> dict[str, Any]:
    """枠の中の文の矩形を、親の画面の座標で返す。"""
    rect = page.evaluate(TEXT_RECT_SCRIPT, [selector, text])
    assert rect is not None, f"{selector} の中に文がありません: {text}"
    return rect


def drag_select_in_frame(page: Page, selector: str, text: str) -> None:
    """枠の中の文の上を、マウスで左から右へ引いて選ぶ（枠の上では `page.mouse` が返らないため、CDP で入力を送る）。"""
    rect = text_rect_in_page(page, selector, text)
    y = rect["top"] + rect["height"] / 2
    start_x = rect["left"] + 1
    end_x = rect["left"] + rect["width"] - 1
    cdp = page.context.new_cdp_session(page)

    def mouse(kind: str, x: float, buttons: int, **extra: object) -> None:
        cdp.send(
            "Input.dispatchMouseEvent",
            {"type": kind, "x": x, "y": y, "button": "left", "buttons": buttons, **extra},
        )

    mouse("mouseMoved", start_x, 0)
    mouse("mousePressed", start_x, 1, clickCount=1)
    for step in range(1, DRAG_STEPS + 1):
        mouse("mouseMoved", start_x + (end_x - start_x) * step / DRAG_STEPS, 1)
    mouse("mouseReleased", end_x, 0, clickCount=1)


def frame_height_gap(page: Page, selector: str) -> float:
    """枠の高さと中の文書の高さの差（px）を返す。"""
    return float(page.evaluate(HEIGHT_GAP_SCRIPT, selector))


def leak_counts(page: Page, selector: str) -> dict[str, int]:
    """本文のスクリプトが動いた印を、親の画面と枠の中で数えて返す。"""
    return dict(page.evaluate(LEAK_SCRIPT, selector))


def style_snapshot(page: Page, selectors: list[str]) -> dict[str, dict[str, str]]:
    """要素ごとの色・余白・背景を返す。"""
    return dict(page.evaluate(STYLE_SCRIPT, selectors))
