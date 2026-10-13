"""thread（スレッドを読む）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

from .fixture_types import (
    CallTool,
    LockDirs,
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
    WriteThreads,
)
from .thread_helpers import drop_post_key, find_thread, threads_path
from workspace_fixtures import RECORD_DIR

# 取り込んだ日時
TAKEN_AT = "2026-10-12T00:30:00+00:00"

# クローズとオープンへの戻しの記録
EVENTS = [
    {"kind": "closed", "author": "user", "reason": None, "created": "2026-10-12T01:30:00+00:00"},
    {"kind": "reopened", "author": "user", "reason": None, "created": "2026-10-12T01:40:00+00:00"},
]


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """未読の書き込みだけを返し、返した書き込みを既読にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", body="案 A にする", read=True, taken=TAKEN_AT),
            make_post("TH-1-2", author="ai", body="案 A で進めます"),
            make_post("TH-1-3", body="了解"),
            target="D-1",
            events=EVENTS,
        ),
    )
    # 実行
    first = call_tool("thread", workspace=str(root), id="TH-1")
    # 検証
    assert first.is_error is False
    assert first.data is not None
    assert [(post["id"], post["body"], post["read"], post["taken"]) for post in first.data["posts"]] == [
        ("TH-1-3", "了解", False, None)
    ]
    assert [(event["kind"], event["author"]) for event in first.data["events"]] == [
        ("closed", "user"),
        ("reopened", "user"),
    ]
    saved = find_thread(root, "TH-1")["posts"]
    assert [post["read"] for post in saved] == [True, True, True]
    assert saved[2]["taken"] is None
    second = call_tool("thread", workspace=str(root), id="TH-1")
    assert second.data is not None
    assert second.data["posts"] == []


def test_normal_when_all_posts(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """未読だけに絞らなければ既読の書き込みも返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", read=True, taken=TAKEN_AT),
            make_post("TH-1-2", author="ai"),
            make_post("TH-1-3"),
        ),
    )
    # 実行
    result = call_tool("thread", workspace=str(root), id="TH-1", unread_only=False)
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert [post["id"] for post in result.data["posts"]] == ["TH-1-1", "TH-1-2", "TH-1-3"]
    assert [post["read"] for post in find_thread(root, "TH-1")["posts"]] == [True, True, True]


def test_error_when_thread_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """無い ID を指すと何も書かずに終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    before = threads_path(root).read_bytes()
    # 実行
    result = call_tool("thread", workspace=str(root), id="TH-9")
    # 検証
    assert result.is_error is True
    assert "TH-9" in result.text
    assert threads_path(root).read_bytes() == before


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("thread", workspace=str(root), id="TH-1")
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
    lock_dirs: LockDirs,
) -> None:
    """既読を書けないときは既読にせずエラーで終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    before = threads_path(root).read_bytes()
    lock_dirs(root / RECORD_DIR)
    # 実行
    result = call_tool("thread", workspace=str(root), id="TH-1")
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert "Traceback" not in result.text
    assert threads_path(root).read_bytes() == before


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """手で崩した threads.yaml は読まずに、合わない箇所を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    drop_post_key(root, "author")
    before = threads_path(root).read_bytes()
    # 実行
    result = call_tool("thread", workspace=str(root), id="TH-1")
    # 検証
    assert result.is_error is True
    assert any(line.startswith("threads.yaml: items[0]") for line in result.text.splitlines())
    assert threads_path(root).read_bytes() == before
