"""reset_unread.py（SessionStart のフックが呼ぶ、スレッドの書き込みを未読へ戻すスクリプト）の結合テスト。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from workspace_fixtures import REPO_ROOT

from .fixture_types import (
    CallTool,
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
    SnapshotTree,
    WriteThreads,
)
from .thread_helpers import drop_thread_key, find_thread, threads_path

# フックが起動するスクリプト
RESET_SCRIPT = (
    REPO_ROOT / "plugins" / "mindstella" / "skills" / "mindmap" / "scripts" / "reset_unread.py"
)

# 子プロセス 1 回を待つ上限秒数
COMMAND_TIMEOUT_SEC = 60

# 取り込んだ日時
TAKEN_AT = "2026-10-12T00:30:00+00:00"

# AI がクローズにした記録
AI_CLOSED = {
    "kind": "closed",
    "author": "ai",
    "reason": "了解を受けた",
    "created": "2026-10-12T02:00:00+00:00",
}


def _run_hook(cwd: Path) -> subprocess.CompletedProcess[str]:
    """フックと同じく、標準入力に `cwd` と `source` の JSON を渡してスクリプトを起動する。"""
    return subprocess.run(
        [sys.executable, str(RESET_SCRIPT)],
        input=json.dumps({"cwd": str(cwd), "source": "clear"}),
        capture_output=True,
        text=True,
        timeout=COMMAND_TIMEOUT_SEC,
        check=False,
    )


def test_normal(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """作業フォルダとその直下のワークスペースの全ての書き込みを未読に戻し、取り込み済みは残す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), name="talk")
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", read=True, taken=TAKEN_AT),
            make_post("TH-1-2", author="ai"),
            summary="相談",
            tags=["画面"],
        ),
        make_thread(
            "TH-2",
            make_post("TH-2-1", read=True, taken=TAKEN_AT),
            status="closed",
            events=[AI_CLOSED],
        ),
    )
    # 実行
    result = _run_hook(tmp_path)
    # 検証
    assert result.returncode == 0
    assert result.stdout == ""
    first, second = find_thread(root, "TH-1"), find_thread(root, "TH-2")
    assert [post["read"] for post in first["posts"] + second["posts"]] == [False, False, False]
    assert [post["taken"] for post in first["posts"][:1] + second["posts"]] == [TAKEN_AT, TAKEN_AT]
    assert (first["summary"], first["tags"], first["status"]) == ("相談", ["画面"], "open")
    assert (second["status"], second["events"]) == ("closed", [AI_CLOSED])
    awaiting = call_tool("threads", workspace=str(root), awaiting=True)
    assert awaiting.data == {"items": []}


def test_normal_when_no_workspace(tmp_path: Path, snapshot_tree: SnapshotTree) -> None:
    """ワークスペースを持たないフォルダでは何も書かずに終わる（正常系）。"""
    # 準備
    before = snapshot_tree(tmp_path)
    # 実行
    result = _run_hook(tmp_path)
    # 検証
    assert result.returncode == 0
    assert result.stdout == ""
    assert snapshot_tree(tmp_path) == before


def test_normal_when_schema_mismatch(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """読めない threads.yaml は書き換えず、会話の始まりを止めない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), name="talk")
    write_threads(root, make_thread("TH-1"))
    drop_thread_key(root, "posts")
    before = threads_path(root).read_bytes()
    # 実行
    result = _run_hook(tmp_path)
    # 検証
    assert result.returncode == 0
    assert result.stdout == ""
    assert "threads.yaml" in result.stderr
    assert threads_path(root).read_bytes() == before
