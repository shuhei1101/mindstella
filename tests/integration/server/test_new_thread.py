"""new_thread（スレッドを立てる）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from .fixture_types import (
    CallTool,
    LockDirs,
    MakeItem,
    MakeThread,
    MakeWorkspace,
    WriteThreads,
)
from .thread_helpers import drop_thread_key, find_thread, threads_path
from workspace_fixtures import RECORD_DIR


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """AI の問いを最初の書き込みにしてオープンのスレッドを立てる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    existing = make_thread("TH-1")
    write_threads(root, existing)
    # 実行
    result = call_tool(
        "new_thread",
        workspace=str(root),
        body="D-1 の比べた結果を Issue に起票してよいですか",
        summary="D-1 の比べた結果を Issue に起票してよいかの確認。返事待ち",
        tags=["起票"],
        target="D-1",
    )
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert (result.data["id"], result.data["post"]) == ("TH-2", "TH-2-1")
    created = find_thread(root, "TH-2")
    assert (created["status"], created["tags"], created["target"]) == ("open", ["起票"], "D-1")
    assert created["summary"] == "D-1 の比べた結果を Issue に起票してよいかの確認。返事待ち"
    assert len(created["posts"]) == 1
    post = created["posts"][0]
    assert (post["author"], post["read"], "taken" in post) == ("ai", True, False)
    assert find_thread(root, "TH-1") == existing
    awaiting = call_tool("threads", workspace=str(root), awaiting=True)
    assert awaiting.data is not None
    assert [item["id"] for item in awaiting.data["items"]] == ["TH-1"]


@pytest.mark.parametrize(
    ("arguments", "expected_text"),
    [
        pytest.param({"body": "  ", "summary": "確認"}, "エラー: 引数の誤り: body:", id="body_empty"),
        pytest.param(
            {"body": "起票してよいですか", "summary": "確認", "target": "D-9"},
            "D-9",
            id="target_not_found",
        ),
    ],
)
def test_error_when_rejected(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    arguments: dict[str, str],
    expected_text: str,
) -> None:
    """空白だけの本文と無い項目へは立てない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = call_tool("new_thread", workspace=str(root), **arguments)
    # 検証
    assert result.is_error is True
    assert expected_text in result.text
    assert not threads_path(root).exists()


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("new_thread", workspace=str(root), body="確認", summary="確認")
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
    result = call_tool("new_thread", workspace=str(root), body="確認", summary="確認")
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
    result = call_tool("new_thread", workspace=str(root), body="確認", summary="確認")
    # 検証
    assert result.is_error is True
    assert any(line.startswith("threads.yaml: items[0]") for line in result.text.splitlines())
    assert threads_path(root).read_bytes() == before
