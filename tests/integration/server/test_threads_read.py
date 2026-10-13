"""スレッドの読み取り（GET /api/threads）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .fixture_types import (
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
    SnapshotTree,
    WriteThreads,
)
from .http_helpers import http_request
from .thread_helpers import drop_thread_key, threads_path

# 読み取りのパス
THREADS_PATH = "/api/threads"


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
    snapshot_tree: SnapshotTree,
) -> None:
    """全てのスレッドを書き込みと状態の記録ごと返し、AI の既読は変えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="最初の問い"))
    closed_by_ai = {
        "kind": "closed",
        "author": "ai",
        "reason": "了解を受けた",
        "created": "2026-10-12T03:00:00+00:00",
    }
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", body="案 A にする", created="2026-10-12T01:00:00+00:00"),
            target="D-1",
        ),
        make_thread(
            "TH-2",
            make_post("TH-2-1", body="これは何？", read=True, created="2026-10-12T02:00:00+00:00"),
            status="closed",
            events=[closed_by_ai],
        ),
    )
    url = serve_preview(root)
    before = snapshot_tree(root)
    # 実行
    result = http_request(url, THREADS_PATH)
    # 検証
    assert result.status == 200
    assert result.headers["cache-control"] == "no-store"
    threads = result.json()["threads"]
    assert [thread["id"] for thread in threads] == ["TH-2", "TH-1"]
    second = threads[1]
    assert (second["target_title"], second["posts"][0]["body"]) == ("最初の問い", "案 A にする")
    assert [(event["author"], event["reason"]) for event in threads[0]["events"]] == [
        ("ai", "了解を受けた")
    ]
    assert all({"read", "taken", "comment"}.isdisjoint(post) for item in threads for post in item["posts"])
    assert snapshot_tree(root) == before


def test_normal_when_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """threads.yaml が無ければ空を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = http_request(url, THREADS_PATH)
    # 検証
    assert result.status == 200
    assert result.json() == {"threads": []}
    assert not threads_path(root).exists()


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    serve_preview: Callable[[Path], str],
) -> None:
    """手で崩した threads.yaml は読まずに、合わない箇所を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    drop_thread_key(root, "posts")
    url = serve_preview(root)
    # 実行
    result = http_request(url, THREADS_PATH)
    # 検証
    assert result.status == 422
    assert "threads.yaml" in result.json()["detail"]
