"""reply（スレッドへの返信）の結合テスト。"""

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
from .thread_helpers import drop_thread_key, find_thread, threads_path
from workspace_fixtures import RECORD_DIR


def _write_open_thread(
    root: Path, make_post: MakePost, make_thread: MakeThread, write_threads: WriteThreads
) -> None:
    """既読で取り込んでいない利用者の書き込みと、その後の未読の書き込みを持つオープンの TH-1 を書く。"""
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", body="案 A にする", read=True),
            make_post("TH-1-2", body="案 B も見たい"),
            target="D-1",
        ),
    )


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """返信を足し、要約を書き直し、読んだ利用者の書き込みを取り込み済みにする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    _write_open_thread(root, make_post, make_thread, write_threads)
    seen_before = [post["seen"] for post in find_thread(root, "TH-1")["posts"]]
    # 実行
    result = call_tool(
        "reply",
        workspace=str(root),
        id="TH-1",
        body="D-1 を案 A で決定にしました",
        summary="D-1 の案の相談。案 A で決定",
    )
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert (result.data["id"], result.data["post"], result.data["taken"]) == (
        "TH-1",
        "TH-1-3",
        ["TH-1-1"],
    )
    thread = find_thread(root, "TH-1")
    first, second, reply = thread["posts"]
    assert first["taken"] == result.data["created"]
    assert second["taken"] is None
    assert (reply["author"], reply["body"], reply["read"]) == (
        "ai",
        "D-1 を案 A で決定にしました",
        True,
    )
    assert (thread["status"], thread["summary"]) == ("open", "D-1 の案の相談。案 A で決定")
    # 足した AI の書き込みは利用者の未読で、利用者の書き込みの既読は呼ぶ前と同じ
    assert reply["seen"] is False
    assert [first["seen"], second["seen"]] == seen_before


def test_normal_when_not_take(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """take を偽にすると返信と要約だけを書く（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    _write_open_thread(root, make_post, make_thread, write_threads)
    # 実行
    result = call_tool(
        "reply", workspace=str(root), id="TH-1", body="見ます", summary="案の相談", take=False
    )
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["taken"] == []
    posts = find_thread(root, "TH-1")["posts"]
    assert [post["taken"] for post in posts[:2]] == [None, None]
    assert posts[2]["author"] == "ai"


def test_error_when_thread_closed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """クローズのスレッドには返信せず、オープンに戻すよう返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", body="これは何？", read=True),
            status="closed",
            events=[
                {"kind": "closed", "author": "user", "reason": None, "created": "2026-10-12T01:00:00+00:00"}
            ],
        ),
    )
    before = threads_path(root).read_bytes()
    # 実行
    result = call_tool("reply", workspace=str(root), id="TH-1", body="答えます", summary="質問")
    # 検証
    assert result.is_error is True
    assert "TH-1" in result.text
    assert "set_thread_status" in result.text
    assert threads_path(root).read_bytes() == before


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
    result = call_tool("reply", workspace=str(root), id="TH-9", body="答えます", summary="質問")
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
    result = call_tool("reply", workspace=str(root), id="TH-1", body="答えます", summary="質問")
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
    """書き込めないワークスペースでは前のスレッドを残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    before = threads_path(root).read_bytes()
    lock_dirs(root / RECORD_DIR)
    # 実行
    result = call_tool("reply", workspace=str(root), id="TH-1", body="答えます", summary="質問")
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
    """手で崩した threads.yaml には書かずに、合わない箇所を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    drop_thread_key(root, "status")
    before = threads_path(root).read_bytes()
    # 実行
    result = call_tool("reply", workspace=str(root), id="TH-1", body="答えます", summary="質問")
    # 検証
    assert result.is_error is True
    assert any(line.startswith("threads.yaml: items[0]") for line in result.text.splitlines())
    assert threads_path(root).read_bytes() == before


def test_error_when_body_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """空白だけの本文では返信しない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    before = threads_path(root).read_bytes()
    # 実行
    result = call_tool("reply", workspace=str(root), id="TH-1", body="", summary="質問")
    # 検証
    assert result.is_error is True
    assert "エラー: 引数の誤り: body:" in result.text
    assert threads_path(root).read_bytes() == before
