"""スレッドの書き込みの Markdown の結合テストが共有する、AI の書き込みとレビュー中の返信の本文。"""

from __future__ import annotations

__all__ = ["MARKDOWN_POST_BODY", "MARKDOWN_POST_HASH", "MARKDOWN_REPLY_BODY"]

# スレッドを開くハッシュ
MARKDOWN_POST_HASH = "#tab=decisions"

# AI の書き込みの本文（見出し・項目の ID を含む段落・表・`python` のコード・`mermaid` の図・生の HTML）
MARKDOWN_POST_BODY = "\n".join(
    [
        "## 比べた結果",
        "",
        "D-1 は案 A が合う。",
        "",
        "| 案 | 結果 |",
        "| --- | --- |",
        "| A | 成立 |",
        "",
        "```python",
        'print("ok")',
        "```",
        "",
        "```mermaid",
        "flowchart LR",
        "  A --> B",
        "```",
        "",
        '<img src="x" onerror="window.injected = true">',
    ]
)

# TH-1 へのレビュー中の返信の本文
MARKDOWN_REPLY_BODY = "**起票してよい**"
