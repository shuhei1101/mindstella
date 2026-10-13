"""threads（スレッドの一覧）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

from .fixture_types import (
    CallTool,
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
    SnapshotTree,
    WriteThreads,
)
from .thread_helpers import drop_thread_key, threads_path

# 書き込みの日時（古い順）
T_0100 = "2026-10-12T01:00:00+00:00"
T_0200 = "2026-10-12T02:00:00+00:00"
T_0300 = "2026-10-12T03:00:00+00:00"
T_0400 = "2026-10-12T04:00:00+00:00"

# 取り込んだ日時
TAKEN_AT = "2026-10-12T00:30:00+00:00"


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """状態を渡さなければオープンのスレッドだけを新しい順に返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="写しの取り方"))
    long_body = "1 行目\n" + "あ" * 99
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", taken=TAKEN_AT, created="2026-10-12T00:30:00+00:00"),
            make_post("TH-1-2", author="ai", created=T_0100),
            summary="案 A の相談",
            target="D-1",
        ),
        make_thread("TH-2", status="closed"),
        make_thread("TH-3", make_post("TH-3-1", body=long_body, created=T_0200)),
    )
    before = snapshot_tree(root)
    # 実行
    result = call_tool("threads", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    items = result.data["items"]
    assert [item["id"] for item in items] == ["TH-3", "TH-1"]
    first = items[1]
    assert (first["target"], first["target_title"], first["last_author"], first["last_at"]) == (
        "D-1",
        "写しの取り方",
        "ai",
        T_0100,
    )
    assert (first["posts"], first["unread"], first["awaiting"]) == (2, 1, 0)
    unsummarized = items[0]
    assert (unsummarized["summary"], unsummarized["target"], unsummarized["last_author"]) == (
        None,
        None,
        "user",
    )
    assert "\n" not in unsummarized["head"]
    assert len(unsummarized["head"]) == 80
    assert all({"body", "events"}.isdisjoint(item) for item in items)
    assert snapshot_tree(root) == before


def test_normal_when_awaiting(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """状態を渡さずに取り込み待ちで絞ると、クローズのスレッドも返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread("TH-1", make_post("TH-1-1", created=T_0100)),
        make_thread("TH-2", make_post("TH-2-1", created=T_0200), status="closed"),
        make_thread("TH-3", make_post("TH-3-1", taken=TAKEN_AT, created=T_0300)),
    )
    # 実行
    result = call_tool("threads", workspace=str(root), awaiting=True)
    # 検証
    assert result.is_error is False
    assert result.data is not None
    items = result.data["items"]
    assert {item["id"]: (item["status"], item["awaiting"]) for item in items} == {
        "TH-1": ("open", 1),
        "TH-2": ("closed", 1),
    }


def test_normal_when_filtered(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """タグ・未読・状態を重ねて絞る（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread("TH-1", make_post("TH-1-1", created=T_0100), tags=["画面"]),
        make_thread(
            "TH-2", make_post("TH-2-1", read=True, created=T_0200), tags=["画面"]
        ),
        make_thread(
            "TH-3", make_post("TH-3-1", created=T_0300), tags=["画面"], status="closed"
        ),
        make_thread("TH-4", make_post("TH-4-1", created=T_0400), tags=["調査"]),
    )
    # 実行
    unread = call_tool("threads", workspace=str(root), tag="画面", unread=True)
    tagged = call_tool("threads", workspace=str(root), tag="画面", status="all")
    # 検証
    assert unread.data is not None
    assert tagged.data is not None
    assert [item["id"] for item in unread.data["items"]] == ["TH-1"]
    assert {item["id"] for item in tagged.data["items"]} == {"TH-1", "TH-2", "TH-3"}


def test_normal_when_empty(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """threads.yaml が無ければ 0 件を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = call_tool("threads", workspace=str(root), awaiting=True)
    # 検証
    assert result.is_error is False
    assert result.data == {"items": []}
    assert not threads_path(root).exists()


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("threads", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


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
    drop_thread_key(root, "status")
    # 実行
    result = call_tool("threads", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert any(line.startswith("threads.yaml: items[0]") for line in result.text.splitlines())
