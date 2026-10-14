"""本文のまとまりのリンクの結合テストが共有する、リンクを持つ本文のワークスペースの作り方と値。"""

from __future__ import annotations

from typing import Any

__all__ = [
    "BODY_LINK_HASH",
    "HEADING_IN_VIEW_JS",
    "LINK_BODY",
    "build_body_link_workspace",
]

# D-2 の詳細パネルを V-2 の差分の表示で開くハッシュ
BODY_LINK_HASH = "#tab=decisions&view=table&id=D-2&diff=V-2"

# 本文の頭にまとまりのリンク 4 つと見出しのリンク 1 つ、その後ろに見出し「決め方」（本文のスクロール領域の外から始まる）
LINK_BODY = (
    "## 先頭\n\n"
    "[V-1 へ](#diff=V-1)\n\n"
    "[他の引数つき](#tab=tasks&id=D-1&diff=V-1)\n\n"
    "[無いまとまり](#diff=V-99)\n\n"
    "[前回から](#diff=since)\n\n"
    "[決め方へ](#決め方)\n\n"
    + "\n\n".join(f"先頭の段落 {number}" for number in range(1, 41))
    + "\n\n## 決め方\n\n決め方の段落\n"
)

# 見出しが詳細の本文のスクロール領域の中で画面に入っているかを返す（`bodySelector` は詳細パネルか全画面の本文のスクロール領域）
HEADING_IN_VIEW_JS = """([bodySelector, slug]) => {
    const body = document.querySelector(bodySelector);
    const target = document.querySelector(`[data-heading="${slug}"]`);
    const area = body.getBoundingClientRect();
    const box = target.getBoundingClientRect();
    return box.top >= area.top - 1 && box.bottom <= area.bottom + 1;
}"""


def build_body_link_workspace(make_workspace: Any, make_item: Any, call_tool: Any) -> str:
    """D-1 の本文を書き換えて `commit`（V-1）し、リンクを持つ本文を D-2 に書いて `commit`（V-2）した配信の URL を返す。"""
    root = make_workspace(make_item("D-1"), make_item("D-2"))
    workspace = str(root)
    rewrites = [
        ("D-1", "D-1 の本文を直した\n", "D-1 を直す"),
        ("D-2", LINK_BODY, "D-2 を直す"),
    ]
    for item_id, body, summary in rewrites:
        updated = call_tool("update", workspace=workspace, id=item_id, item={"body_markdown": body})
        assert updated.is_error is False, updated.text
        committed = call_tool("commit", workspace=workspace, summary=summary)
        assert committed.is_error is False, committed.text
    result = call_tool("preview_url", workspace=workspace)
    assert result.is_error is False, result.text
    assert result.data is not None
    return str(result.data["url"])
