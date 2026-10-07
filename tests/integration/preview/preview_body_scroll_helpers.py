"""詳細パネルと詳細の全画面の、本文のスクロール領域の結合テストが共有する値。"""

from __future__ import annotations

from playwright.sync_api import Page

__all__ = [
    "HANGING_LINES_JS",
    "LONG_BODY",
    "LONG_LINE",
    "LONG_LINES_BODY",
    "NEW_DECISION",
    "SCROLLABLE_REGION_RULE",
    "SETTLED_SCROLL_TOP_JS",
    "TALL_DIAGRAM_BODY",
    "overflows_horizontally",
]

# 本文のスクロール領域に違反が出る axe の規則
SCROLLABLE_REGION_RULE = "scrollable-region-focusable"

# スクロールが止まった（この間隔で 2 回続けて同じ位置）とみなして位置を返す
SETTLED_SCROLL_TOP_JS = """async (selector) => {
  const element = document.querySelector(selector);
  let last = -1;
  while (element.scrollTop !== last) {
    last = element.scrollTop;
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  return last;
}"""

# 縦にあふれる長さで、フォーカスできる要素を持たない本文（資料の項目 A-1 に当てる）
LONG_BODY = "\n\n".join(f"{n} 番目の段落" for n in range(1, 121)) + "\n"

# 本文にフォーカスしたまま描き直すために足す検討事項
NEW_DECISION = {
    "title": "新しい問い",
    "target": "mindmap",
    "category": "データ構造",
    "phase": "要件",
    "status": "未決定",
}

# 窓の幅より長い 1 行（空白を含まず、単語の途中でも折り返さないと収まらない）
LONG_LINE = "a" * 600

# 長い行を持つコードブロックと、記法に長い行を持つ図
LONG_LINES_BODY = f"""# 長い行

```text
{LONG_LINE}
```

```mermaid
flowchart LR
  %% {LONG_LINE}
  A --> B
```
"""

# 記法が縦にあふれる図（コメントの行を並べる）
TALL_DIAGRAM_BODY = (
    "# 縦に長い図\n\n```mermaid\nflowchart LR\n"
    + "".join(f"  %% {n} 行目の注記\n" for n in range(1, 121))
    + "  A --> B\n```\n"
)

# 差分の表示の Raw の足した・消した行ごとに、折り返した行の数と、全ての行の左端が印の右端より右にあるかを返す
HANGING_LINES_JS = """(selector) => {
  const raw = document.querySelector(selector);
  return [...raw.querySelectorAll(".df-line.df-add, .df-line.df-del")].map((line) => {
    const signRight = line.querySelector(".df-sign").getBoundingClientRect().right;
    const range = document.createRange();
    range.selectNodeContents(line.lastChild);
    const rects = [...range.getClientRects()];
    return {
      rows: new Set(rects.map((rect) => Math.round(rect.top))).size,
      clearOfSign: rects.every((rect) => rect.left >= signRight - 1),
    };
  });
}"""


def overflows_horizontally(page: Page, selector: str) -> bool:
    """`selector` の要素が横にあふれている（中身が枠より広い）か。"""
    overflowing: bool = page.eval_on_selector(selector, "e => e.scrollWidth > e.clientWidth")
    return overflowing
