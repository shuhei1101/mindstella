"""update_thread（スレッドの書き換え）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
    """返信せずに、読んだ利用者の書き込みを取り込み済みにして要約を書き直す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1", make_post("TH-1-1", body="了解", read=True), status="closed", events=[USER_CLOSED]
        ),
    )
    # 実行
    result = call_tool(
        "update_thread",
        workspace=str(root),
        id="TH-1",
        summary="D-6 の確認を出す操作の質問。了解を受けた",
        take=True,
    )
    # 検証
    assert result.is_error is False
    assert result.data == {"id": "TH-1", "taken": ["TH-1-1"], "candidate_tags": []}
    thread = find_thread(root, "TH-1")
    assert thread["summary"] == "D-6 の確認を出す操作の質問。了解を受けた"
    assert thread["posts"][0]["taken"] is not None
    assert (thread["status"], len(thread["posts"]), thread["events"]) == (
        "closed",
        1,
        [USER_CLOSED],
    )
    awaiting = call_tool("threads", workspace=str(root), awaiting=True)
    assert awaiting.data == {"items": []}


def test_normal_when_tags(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
) -> None:
    """タグだけを渡した一覧で置き換える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"), settings={**valid_settings, "tags": [{"name": "画面"}, {"name": "調査"}]}
    )
    write_threads(root, make_thread("TH-1", tags=["画面"], summary="相談"))
    # 実行
    result = call_tool(
        "update_thread", workspace=str(root), id="TH-1", tags=["画面", "調査"]
    )
    # 検証
    assert result.is_error is False
    thread = find_thread(root, "TH-1")
    assert (thread["tags"], thread["summary"]) == (["画面", "調査"], "相談")


def test_error_when_nothing_to_update(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """変えるものが無いときは書かずに終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    before = threads_path(root).read_bytes()
    # 実行
    result = call_tool("update_thread", workspace=str(root), id="TH-1")
    # 検証
    assert result.is_error is True
    assert "エラー: 引数の誤り: summary:" in result.text
    assert threads_path(root).read_bytes() == before


def test_error_when_thread_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """無い ID は書かずに終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1"))
    before = threads_path(root).read_bytes()
    # 実行
    result = call_tool("update_thread", workspace=str(root), id="TH-9", take=True)
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
    result = call_tool("update_thread", workspace=str(root), id="TH-1", take=True)
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
    result = call_tool("update_thread", workspace=str(root), id="TH-1", summary="相談")
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
    result = call_tool("update_thread", workspace=str(root), id="TH-1", summary="相談")
    # 検証
    assert result.is_error is True
    assert any(line.startswith("threads.yaml: items[0]") for line in result.text.splitlines())
    assert threads_path(root).read_bytes() == before


def test_normal_when_unknown_tag(
    make_workspace: MakeWorkspace,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
) -> None:
    """語彙に無いタグを加えた一覧でも置き換え、未登録の候補と近いタグを返す（正常系）。"""
    # 準備
    root = make_workspace(settings={**valid_settings, "tags": [{"name": "起票"}]})
    write_threads(root, make_thread("TH-1", tags=["起票"]))
    config_path = root / RECORD_DIR / "config.yaml"
    config_before = config_path.read_text(encoding="utf-8")
    # 実行
    result = call_tool(
        "update_thread", workspace=str(root), id="TH-1", tags=["起票", "起票の確認"]
    )
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["candidate_tags"] == [
        {"tag": "起票の確認", "ids": ["TH-1"], "similar": ["起票"]}
    ]
    assert find_thread(root, "TH-1")["tags"] == ["起票", "起票の確認"]
    assert config_path.read_text(encoding="utf-8") == config_before
