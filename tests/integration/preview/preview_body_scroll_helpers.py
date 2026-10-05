"""詳細パネルと詳細の全画面の、本文のスクロール領域の結合テストが共有する値。"""

from __future__ import annotations

__all__ = ["LONG_BODY", "NEW_DECISION", "SCROLLABLE_REGION_RULE", "SETTLED_SCROLL_TOP_JS"]

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
