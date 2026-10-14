"""画面からのスレッドの状態の書き換え（PATCH /api/threads/{id}）の結合テスト。"""

from __future__ import annotations

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
from .http_helpers import http_request, send_json
from .thread_helpers import drop_thread_key, find_thread, threads_path
from workspace_fixtures import RECORD_DIR

# AI がクローズにした記録
AI_CLOSED = {
    "kind": "closed",
    "author": "ai",
    "reason": None,
    "created": "2026-10-12T01:00:00+00:00",
}


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
) -> None:
    """利用者が理由つきでクローズにし、書き手・理由・日時を残す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1", make_post("TH-1-1")))
    url = serve_preview(root)
    # 実行
    result = send_json(
        url, "PATCH", "/api/threads/TH-1", {"status": "closed", "reason": "案 A で決着"}
    )
    # 検証
    assert result.status == 200
    assert result.json() == {"id": "TH-1", "status": "closed", "changed": True}
    thread = find_thread(root, "TH-1")
    last = thread["events"][-1]
    assert (thread["status"], last["kind"], last["author"], last["reason"]) == (
        "closed",
        "closed",
        "user",
        "案 A で決着",
    )
    assert last["created"]
    assert (thread["posts"][0]["read"], thread["posts"][0]["taken"]) == (False, None)


def test_normal_when_reopen(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
) -> None:
    """理由を書かずにオープンに戻す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1", status="closed", events=[AI_CLOSED]))
    url = serve_preview(root)
    # 実行
    result = send_json(url, "PATCH", "/api/threads/TH-1", {"status": "open"})
    # 検証
    assert result.status == 200
    thread = find_thread(root, "TH-1")
    last = thread["events"][-1]
    assert (thread["status"], last["kind"], last["author"], last["reason"]) == (
        "open",
        "reopened",
        "user",
        None,
    )


def test_error_when_status_missing(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
) -> None:
    """status を持たない本文は受けない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    url = serve_preview(root)
    before = threads_path(root).read_bytes()
    # 実行
    result = send_json(url, "PATCH", "/api/threads/TH-1", {"reason": "決着"})
    # 検証
    assert result.status == 400
    assert "status" in result.json()["detail"]
    assert threads_path(root).read_bytes() == before


def test_error_when_origin_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
) -> None:
    """別のサイトのページからの書き換えは受けない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    url = serve_preview(root)
    before = threads_path(root).read_bytes()
    # 実行
    result = send_json(
        url,
        "PATCH",
        "/api/threads/TH-1",
        {"status": "closed"},
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
    result = send_json(url, "PATCH", "/api/threads/TH-9", {"status": "closed"})
    # 検証
    assert result.status == 404
    assert "TH-9" in result.json()["detail"]
    assert threads_path(root).read_bytes() == before


def test_error_when_not_json(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
) -> None:
    """フォームの形の本文は受けない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    url = serve_preview(root)
    before = threads_path(root).read_bytes()
    # 実行
    result = http_request(
        url,
        "/api/threads/TH-1",
        method="PATCH",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body="status=closed",
    )
    # 検証
    assert result.status == 415
    assert threads_path(root).read_bytes() == before


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
) -> None:
    """手で崩した threads.yaml は書き換えない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    drop_thread_key(root, "posts")
    url = serve_preview(root)
    before = threads_path(root).read_bytes()
    # 実行
    result = send_json(url, "PATCH", "/api/threads/TH-1", {"status": "closed"})
    # 検証
    assert result.status == 422
    assert threads_path(root).read_bytes() == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは前の状態を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    url = serve_preview(root)
    before = threads_path(root).read_bytes()
    lock_dirs(root / RECORD_DIR)
    # 実行
    result = send_json(url, "PATCH", "/api/threads/TH-1", {"status": "closed"})
    # 検証
    assert result.status == 500
    detail = result.json()["detail"]
    assert str(root) in detail
    assert "Traceback" not in detail
    assert threads_path(root).read_bytes() == before
