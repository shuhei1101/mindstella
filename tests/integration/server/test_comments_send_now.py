"""書き込みをすぐ送る（POST /api/comments/send-now）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
import yaml
from claude_pane_fixtures import StartClaudePane

from .fixture_types import (
    MakeComment,
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
    StartServer,
    WriteComments,
    WriteThreads,
)
from .http_helpers import post_json
from .thread_helpers import read_threads, threads_path
from workspace_fixtures import RECORD_DIR

# すぐ送るのパス
SEND_NOW_PATH = "/api/comments/send-now"

# クローズにした記録
CLOSED_EVENT = {"kind": "closed", "author": "user", "reason": None, "created": "2026-10-12T01:00:00+00:00"}


def _comment_ids(root: Path) -> list[str]:
    """comments.yaml のレビュー中の書き込みの ID を並びのまま返す。"""
    saved = yaml.safe_load((root / RECORD_DIR / "comments.yaml").read_text(encoding="utf-8"))
    return [item["id"] for item in saved["items"]]


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """項目へのコメント 1 件を溜めずにオープンのスレッドの最初の書き込みにし、レビュー中の書き込みは残す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1", body="案 B も見たい"))
    url = serve_preview(root)
    # 実行
    result = post_json(url, SEND_NOW_PATH, {"target": "D-1", "body": "案 A にする"})
    # 検証
    assert result.status == 201
    body = result.json()
    assert (body["thread"], body["post"], body["entered"]) == ("TH-1", "TH-1-1", False)
    threads = read_threads(root)
    assert [(item["id"], item["status"], item["target"]) for item in threads] == [("TH-1", "open", "D-1")]
    post = threads[0]["posts"][0]
    assert (post["author"], post["body"], post["read"], post["taken"], post["seen"]) == (
        "user",
        "案 A にする",
        False,
        None,
        True,
    )
    assert "comment" not in post
    assert _comment_ids(root) == ["C-1"]


def test_normal_when_reply(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_post: MakePost,
    make_thread: MakeThread,
    write_comments: WriteComments,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
) -> None:
    """オープンのスレッドへの返信 1 件を、そのスレッドの末尾に足す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", body="どちらにしますか"),
            make_post("TH-1-2", author="ai", body="案 A と案 B があります"),
        ),
    )
    reply = make_comment("C-1", body="少し考える", thread="TH-1")
    del reply["target"]
    write_comments(root, reply)
    url = serve_preview(root)
    # 実行
    result = post_json(url, SEND_NOW_PATH, {"thread": "TH-1", "body": "案 A にする"})
    # 検証
    assert result.status == 201
    assert result.json()["thread"] == "TH-1"
    threads = read_threads(root)
    assert [item["id"] for item in threads] == ["TH-1"]
    last = threads[0]["posts"][-1]
    assert (len(threads[0]["posts"]), last["author"], last["body"]) == (3, "user", "案 A にする")
    assert _comment_ids(root) == ["C-1"]


def test_normal_when_entered_to_claude_code(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
    start_claude_pane: StartClaudePane,
) -> None:
    """送った後、Claude Code のペインへ届いた件数を入力する（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    pane = start_claude_pane(mode="user", cwd=root)
    server = start_server()
    opened = server.call("preview_url", workspace=str(root), session=pane.session)
    assert opened.data is not None
    # 実行
    result = post_json(str(opened.data["url"]), SEND_NOW_PATH, {"target": "D-1", "body": "案 A にする"})
    # 検証
    assert result.status == 201
    assert result.json()["entered"] is True
    assert len(pane.lines()) == 1
    assert (
        '"content": "[mindstella] ユーザーからのコメントが 1 件届きました。読み直してください。"'
        in pane.lines()[0]
    )


def test_error_when_body_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """前後の空白を除いて空の本文は受けない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = post_json(url, SEND_NOW_PATH, {"target": "D-1", "body": "  "})
    # 検証
    assert result.status == 400
    assert not threads_path(root).exists()


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"target": "D-9", "body": "案 A にする"}, id="item-missing"),
        pytest.param({"thread": "TH-1", "body": "了解"}, id="thread-closed"),
    ],
)
def test_error_when_target_stale(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
    payload: dict[str, str],
) -> None:
    """無い項目への書き込みと、クローズか無いスレッドへの返信は送らない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread("TH-1", make_post("TH-1-1", body="これは何？", read=True), status="closed", events=[CLOSED_EVENT]),
    )
    before = threads_path(root).read_bytes()
    url = serve_preview(root)
    # 実行
    result = post_json(url, SEND_NOW_PATH, payload)
    # 検証
    assert result.status == 409
    assert threads_path(root).read_bytes() == before
