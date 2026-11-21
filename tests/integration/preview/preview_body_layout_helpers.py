"""本文の差分の結合テストが共有する、ワークスペースの作り方と値。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from workspace_fixtures import CallTool, MakeWorkspace
from record_write_helpers import call_or_write

__all__ = [
    "HTML_BODY_AFTER",
    "HTML_BODY_BEFORE",
    "MARKDOWN_A1_AFTER",
    "MARKDOWN_A1_BEFORE",
    "MARKDOWN_D1_AFTER",
    "MARKDOWN_D1_BEFORE",
    "build_body_layout_workspace",
    "build_html_body_layout_workspace",
]

# 資料 A-1 の書き換える前と後の本文（1 つ目の段落を消して、末尾に段落を足す）
MARKDOWN_A1_BEFORE = "1 つ目の段落です。\n\n2 つ目の段落です。\n\n3 つ目の段落です。\n"
MARKDOWN_A1_AFTER = "2 つ目の段落です。\n\n3 つ目の段落です。\n\n4 つ目の段落です。\n"

# 検討事項 D-1 の書き換える前と後の本文（2 つ目の段落を書き換える）
MARKDOWN_D1_BEFORE = "1 つ目の段落です。\n\n2 つ目の段落は、来週に決めます。\n\n3 つ目の段落です。\n"
MARKDOWN_D1_AFTER = "1 つ目の段落です。\n\n2 つ目の段落は、今週に決めます。\n\n3 つ目の段落です。\n"

# 段落 3 つを 1 行ずつ持つ HTML の本文と、2 つ目の段落を書き換えた本文
HTML_BODY_BEFORE = "<p>1 つ目の段落</p>\n<p>2 つ目の段落</p>\n<p>3 つ目の段落</p>\n"
HTML_BODY_AFTER = "<p>1 つ目の段落</p>\n<p>書き直した 2 つ目の段落</p>\n<p>3 つ目の段落</p>\n"

def _call(call_tool: Any, name: str, **arguments: Any) -> dict[str, Any]:
    """ツールを呼ぶか記録を書き換え（add・update・remove）、エラーならテストを止めて結果を返す。"""
    return call_or_write(call_tool, name, **arguments)


def build_body_layout_workspace(make_workspace: MakeWorkspace, call_tool: CallTool) -> Path:
    """段落 3 つの Markdown の本文を持つ資料 A-1 と検討事項 D-1 を足して `commit`（V-1）し、A-1 の 1 つ目の段落を消して末尾に段落を足し、D-1 の 2 つ目の段落を書き換えて `commit`（V-2）したワークスペースを作る。"""
    root = make_workspace()
    workspace = str(root)
    decision = {
        "title": "いつ決めるか",
        "status": "未決定",
        "options": [
            {"key": "A", "content": "今週に決める"},
            {"key": "B", "content": "来週に決める"},
        ],
    }
    doc = {"title": "工程の資料", "kind": "図", "status": "下書き"}
    _call(call_tool, "add", workspace=workspace, kind="doc", item={**doc, "body_markdown": MARKDOWN_A1_BEFORE})
    _call(
        call_tool, "add", workspace=workspace, kind="decision", item={**decision, "body_markdown": MARKDOWN_D1_BEFORE}
    )
    _call(call_tool, "commit", workspace=workspace, summary="足す")
    _call(call_tool, "update", workspace=workspace, id="A-1", item={"body_markdown": MARKDOWN_A1_AFTER})
    _call(call_tool, "update", workspace=workspace, id="D-1", item={"body_markdown": MARKDOWN_D1_AFTER})
    _call(call_tool, "commit", workspace=workspace, summary="直す")
    return root


def build_html_body_layout_workspace(make_workspace: MakeWorkspace, call_tool: CallTool) -> Path:
    """段落 3 つを 1 行ずつ持つ HTML の本文の資料 A-1 を足して `commit`（V-1）し、2 つ目の段落を書き換えて `commit`（V-2）したワークスペースを作る。"""
    root = make_workspace()
    workspace = str(root)
    doc = {"title": "画面のモック", "kind": "モック", "status": "下書き"}
    _call(call_tool, "add", workspace=workspace, kind="doc", item={**doc, "body_html": HTML_BODY_BEFORE})
    _call(call_tool, "commit", workspace=workspace, summary="足す")
    _call(call_tool, "update", workspace=workspace, id="A-1", item={"body_html": HTML_BODY_AFTER})
    _call(call_tool, "commit", workspace=workspace, summary="直す")
    return root
