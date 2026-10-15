"""set_thread_status（スレッドの状態の書き換え）の結合テスト。"""

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

# 利用者がクローズにした記録
USER_CLOSED = {
    "kind": "closed",
    "author": "user",
    "reason": None,
    "created": "2026-10-12T01:00:00+00:00",
}


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """AI が理由つきでクローズにし、書き手・理由・日時を残す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1", make_post("TH-1-1", body="了解", read=True)))
    # 実行
    result = call_tool(
        "set_thread_status", workspace=str(root), id="TH-1", status="closed", reason="了解を受けた"
    )
    # 検証
    assert result.is_error is False
    assert result.data == {"id": "TH-1", "status": "closed", "changed": True}
    thread = find_thread(root, "TH-1")
    assert thread["status"] == "closed"
    last = thread["events"][-1]
    assert (last["kind"], last["author"], last["reason"]) == ("closed", "ai", "了解を受けた")
    assert last["created"]
    assert [post["id"] for post in thread["posts"]] == ["TH-1-1"]


def test_normal_when_reopen(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """クローズのスレッドを AI が理由つきでオープンに戻す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1", make_post("TH-1-1", body="これは何？"), status="closed", events=[USER_CLOSED]
        ),
    )
    # 実行
    result = call_tool(
        "set_thread_status", workspace=str(root), id="TH-1", status="open", reason="質問に答える"
    )
    reply = call_tool("reply", workspace=str(root), id="TH-1", body="答えます", summary="質問")
    # 検証
    assert result.is_error is False
    thread = find_thread(root, "TH-1")
    assert thread["status"] == "open"
    last = thread["events"][-1]
    assert (last["kind"], last["author"], last["reason"]) == ("reopened", "ai", "質問に答える")
    assert reply.is_error is False


def test_normal_when_unchanged(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """既に渡した状態なら記録を足さずに返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1", status="closed", events=[USER_CLOSED]))
    before = threads_path(root).read_bytes()
    # 実行
    result = call_tool("set_thread_status", workspace=str(root), id="TH-1", status="closed")
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["changed"] is False
    assert threads_path(root).read_bytes() == before


def test_error_when_reason_too_long(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """上限を超える理由では状態を変えない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    before = threads_path(root).read_bytes()
    # 実行
    result = call_tool(
        "set_thread_status", workspace=str(root), id="TH-1", status="closed", reason="あ" * 401
    )
    # 検証
    assert result.is_error is True
    assert "エラー: 引数の誤り: reason:" in result.text
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
    result = call_tool("set_thread_status", workspace=str(root), id="TH-9", status="closed")
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
    result = call_tool("set_thread_status", workspace=str(root), id="TH-1", status="closed")
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
    """書き込めないワークスペースでは前の状態を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    before = threads_path(root).read_bytes()
    lock_dirs(root / RECORD_DIR)
    # 実行
    result = call_tool("set_thread_status", workspace=str(root), id="TH-1", status="closed")
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
    drop_thread_key(root, "posts")
    before = threads_path(root).read_bytes()
    # 実行
    result = call_tool("set_thread_status", workspace=str(root), id="TH-1", status="closed")
    # 検証
    assert result.is_error is True
    assert any(line.startswith("threads.yaml: items[0]") for line in result.text.splitlines())
    assert threads_path(root).read_bytes() == before
