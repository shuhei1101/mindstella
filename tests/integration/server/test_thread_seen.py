"""画面からのスレッドの既読（POST /api/threads/{id}/seen）の結合テスト。"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from .fixture_types import (
    LockDirs,
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
    WriteThreads,
)
from .http_helpers import http_request
from .thread_helpers import drop_post_key, find_thread, threads_path
from workspace_fixtures import RECORD_DIR

# 利用者の書き込みを AI が取り込んだ日時
TAKEN_AT = "2026-10-12T01:30:00+00:00"

# AI がクローズにした記録
AI_CLOSED = {
    "kind": "closed",
    "author": "ai",
    "reason": None,
    "created": "2026-10-12T02:00:00+00:00",
}

# 古い更新日時（書き換えたかを更新日時で確かめるため、先にファイルをこの時刻へ戻す）
OLD_MTIME_SEC = 1_000_000_000


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
) -> None:
    """AI の未読の返信を利用者の既読にし、ほかのキーは変えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", read=True, taken=TAKEN_AT),
            make_post("TH-1-2", author="ai", seen=False),
            summary="要約",
            tags=["画面"],
        ),
    )
    url = serve_preview(root)
    before = find_thread(root, "TH-1")
    # 実行
    result = http_request(url, "/api/threads/TH-1/seen", method="POST")
    # 検証
    assert result.status == 200
    assert result.json() == {"id": "TH-1", "seen": ["TH-1-2"]}
    thread = find_thread(root, "TH-1")
    assert [post["seen"] for post in thread["posts"]] == [True, True]
    for post, post_before in zip(thread["posts"], before["posts"], strict=True):
        assert {k: v for k, v in post.items() if k != "seen"} == {
            k: v for k, v in post_before.items() if k != "seen"
        }
    assert (thread["status"], thread["events"], thread["summary"], thread["tags"]) == (
        before["status"],
        before["events"],
        before["summary"],
        before["tags"],
    )


def test_normal_when_nothing_unseen(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
) -> None:
    """未読が無ければ書かずに空を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1", make_post("TH-1-1", read=True, taken=TAKEN_AT), make_post("TH-1-2", author="ai")
        ),
    )
    url = serve_preview(root)
    path = threads_path(root)
    os.utime(path, (OLD_MTIME_SEC, OLD_MTIME_SEC))
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    # 実行
    result = http_request(url, "/api/threads/TH-1/seen", method="POST")
    # 検証
    assert result.status == 200
    assert result.json() == {"id": "TH-1", "seen": []}
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before


def test_normal_when_closed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
) -> None:
    """クローズのスレッドも既読にし、状態は変えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", read=True, taken=TAKEN_AT),
            make_post("TH-1-2", author="ai", seen=False),
            status="closed",
            events=[AI_CLOSED],
        ),
    )
    url = serve_preview(root)
    # 実行
    result = http_request(url, "/api/threads/TH-1/seen", method="POST")
    # 検証
    assert result.status == 200
    assert result.json() == {"id": "TH-1", "seen": ["TH-1-2"]}
    thread = find_thread(root, "TH-1")
    assert (thread["status"], thread["events"]) == ("closed", [AI_CLOSED])
    assert [post["seen"] for post in thread["posts"]] == [True, True]


def test_error_when_origin_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
) -> None:
    """別のサイトのページからの書き換えは受けない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1", make_post("TH-1-1", author="ai", seen=False)))
    url = serve_preview(root)
    before = threads_path(root).read_bytes()
    # 実行
    result = http_request(
        url,
        "/api/threads/TH-1/seen",
        method="POST",
        headers={"Origin": "https://attacker.example"},
    )
    # 検証
    assert result.status == 403
    assert threads_path(root).read_bytes() == before


def test_error_when_thread_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
) -> None:
    """無いスレッドは書き換えない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    url = serve_preview(root)
    before = threads_path(root).read_bytes()
    # 実行
    result = http_request(url, "/api/threads/TH-9/seen", method="POST")
    # 検証
    assert result.status == 404
    assert "TH-9" in result.json()["detail"]
    assert threads_path(root).read_bytes() == before


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
) -> None:
    """手で崩した threads.yaml は書き換えない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1", make_post("TH-1-1", author="ai", seen=False)))
    drop_post_key(root, "seen")
    url = serve_preview(root)
    before = threads_path(root).read_bytes()
    # 実行
    result = http_request(url, "/api/threads/TH-1/seen", method="POST")
    # 検証
    assert result.status == 422
    assert "threads.yaml" in result.json()["detail"]
    assert threads_path(root).read_bytes() == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは前の状態を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1", make_post("TH-1-1", author="ai", seen=False)))
    url = serve_preview(root)
    before = threads_path(root).read_bytes()
    lock_dirs(root / RECORD_DIR)
    # 実行
    result = http_request(url, "/api/threads/TH-1/seen", method="POST")
    # 検証
    assert result.status == 500
    detail = result.json()["detail"]
    assert str(root) in detail
    assert "Traceback" not in detail
    assert threads_path(root).read_bytes() == before
