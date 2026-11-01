"""tags（タグの一覧）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

from .fixture_types import (
    CallTool,
    MakeItem,
    MakeThread,
    MakeWorkspace,
    SnapshotTree,
    WriteThreads,
)


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """項目とスレッドが使うタグを、表記の違いをまとめて件数の多い順に返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=[{"name": "API"}]),
        make_item("D-2", tags=[{"name": "画面"}]),
        make_item("T-1", tags=[{"name": "ａｐｉ"}]),
        make_item("N-1"),
    )
    write_threads(root, make_thread("TH-1", tags=["api", "画面"]))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("tags", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data == {
        "tags": [
            {"name": "api", "count": 3, "kinds": ["decision", "task", "thread"]},
            {"name": "画面", "count": 2, "kinds": ["decision", "thread"]},
        ]
    }
    # 項目とスレッドのタグは書いたときの表記のまま（ファイルが呼ぶ前と同じ）
    assert snapshot_tree(root) == before


def test_normal_when_no_tags(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """どの項目もスレッドもタグを持たなければ空の一覧を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = call_tool("tags", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data == {"tags": []}


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """.mindstella/config.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("tags", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text
