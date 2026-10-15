"""書き込みのまとまりのリンクの結合テストが共有する、スレッドとレビュー中の返信にリンクを持つワークスペースの作り方と値。"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

__all__ = [
    "DIFF_CHIP_TITLE",
    "DIFF_SETTLE_MS",
    "POST_LINK_HASH",
    "REPLY_BODY",
    "THREAD_POST_BODY",
    "build_post_link_workspace",
    "hash_params",
]

# 差分の表示の札の題（選んだまとまりの説明で終わる）
DIFF_CHIP_TITLE = ".df-chip-t"

# 時点を指すハッシュの書き換えと再描画を待つ上限ミリ秒
DIFF_SETTLE_MS = 10_000

# 検討事項の表を開くハッシュ（押したときに `tab`・`view` が書き換わらないことを確かめる）
POST_LINK_HASH = "#tab=decisions&view=table"

# AI の書き込みの本文。まとまりのリンク 2 つ（`他の引数つき` は `diff` だけを読む）と、リンクにしない書き方 3 つ
THREAD_POST_BODY = (
    "[D-1 を直した](#diff=V-1)。[無いまとまり](#diff=V-99)・[前回から](#diff=since)"
    "・[決め方へ](#決め方)・[他の引数つき](#tab=tasks&id=D-2&diff=V-2)"
)

# TH-1 へのレビュー中の返信の本文（まとまりのリンク 1 つと、文字のままの項目の ID）
REPLY_BODY = "[V-2 の直し](#diff=V-2) は D-2 にも関わる"


def hash_params(page: Any) -> dict[str, list[str]]:
    """今の URL のハッシュを、キー → 値の並びで返す。"""
    return parse_qs(str(page.evaluate("location.hash")).lstrip("#"))


def build_post_link_workspace(make_workspace: Any, make_item: Any, call_tool: Any) -> Path:
    """D-1 を書き換えて `commit`（V-1）し、その後 D-2 を書き換えて `commit`（V-2）したワークスペースのフォルダを返す。"""
    root: Path = make_workspace(make_item("D-1", title="最初の問い"), make_item("D-2", title="次の問い"))
    workspace = str(root)
    for item_id in ("D-1", "D-2"):
        updated = call_tool(
            "update", workspace=workspace, id=item_id, item={"body_markdown": f"{item_id} の本文を直した\n"}
        )
        assert updated.is_error is False, updated.text
        committed = call_tool("commit", workspace=workspace, summary=f"{item_id} を直す")
        assert committed.is_error is False, committed.text
    return root
