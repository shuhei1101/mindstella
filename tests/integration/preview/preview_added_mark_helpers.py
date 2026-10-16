"""本文の差分の足した印（足した色の面と +）の結合テストが共有する、ワークスペースの作り方と線の測り方。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = [
    "DECORATION_LINES_JS",
    "LOOSE_LIST_AFTER",
    "LOOSE_LIST_BEFORE",
    "build_added_mark_workspace",
    "serve_added_mark_workspace",
]

# 検討事項 D-1 の書き換える前の本文（段落・箇条書き・表を 1 つずつ持つ）
BEFORE_ADDED = """# 概要

最初の段落です。

- 項目 1

| 列 A | 列 B |
| --- | --- |
| 1 | 2 |
"""

# D-1 の書き換えた後の本文（段落・箇条書きの項目・表の行を 1 つずつ足す）
AFTER_ADDED = """# 概要

最初の段落です。

足した段落です。

- 項目 1
- 足した項目

| 列 A | 列 B |
| --- | --- |
| 1 | 2 |
| 3 | 4 |
"""

# 項目の間に空行を挟んだ箇条書き（項目の中身が段落で包まれる）の書き換える前と後の本文（項目を 1 つ足す）
LOOSE_LIST_BEFORE = """# 概要

- 項目 1

- 項目 2
"""
LOOSE_LIST_AFTER = """# 概要

- 項目 1

- 項目 2

- 足した項目
"""

# `selector` に当たる要素と、その子孫の計算済みの `text-decoration-line` を、重複を除いて並べて返す
DECORATION_LINES_JS = """selector => {
    const lines = new Set();
    for (const root of document.querySelectorAll(selector)) {
        for (const element of [root, ...root.querySelectorAll('*')]) {
            lines.add(getComputedStyle(element).textDecorationLine);
        }
    }
    return [...lines];
}"""


def _call(call_tool: Any, name: str, **arguments: Any) -> dict[str, Any]:
    """ツールを呼び、エラーならテストを止めて結果を返す。"""
    result = call_tool(name, **arguments)
    assert result.is_error is False, result.text
    return result.data


def build_added_mark_workspace(
    make_workspace: Any, call_tool: Any, before: str = BEFORE_ADDED, after: str = AFTER_ADDED
) -> Path:
    """実際のツールで、本文を `before` から `after` へ書き換えたまとまり V-2 を持つ検討事項 D-1 のワークスペースを作る。"""
    root: Path = make_workspace()
    workspace = str(root)
    decision = {
        "title": "足した印を確かめる問い",
        "status": "未決定",
        "options": [{"key": "A", "content": "案 A"}],
        "weight": "大",
        "category": "データ構造",
        "phase": "要件",
        "target": "mindmap",
    }
    _call(
        call_tool,
        "add",
        workspace=workspace,
        kind="decision",
        item={**decision, "body_markdown": before},
    )
    _call(call_tool, "commit", workspace=workspace, summary="最初の書き込み")
    _call(call_tool, "update", workspace=workspace, id="D-1", item={"body_markdown": after})
    _call(call_tool, "commit", workspace=workspace, summary="足す")
    return root


def serve_added_mark_workspace(
    make_workspace: Any, call_tool: Any, before: str = BEFORE_ADDED, after: str = AFTER_ADDED
) -> str:
    """足した印を確かめるワークスペースを作って配信を立て、その URL を返す。"""
    root = build_added_mark_workspace(make_workspace, call_tool, before, after)
    served = call_tool("preview_url", workspace=str(root))
    assert served.is_error is False, served.text
    assert served.data is not None
    return str(served.data["url"])
