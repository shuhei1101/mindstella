"""next_id（ID の採番）の結合テスト。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .fixture_types import CallTool, MakeItem, MakeWorkspace, McpServer, SnapshotTree

# 消した D-3 を、まだまとめていない変更に持つ changes.yaml
CHANGES_WITH_REMOVED = """last_seq: 3
sets: []
pending:
  added: []
  changed: []
  removed:
  - id: D-3
    kind: decision
    title: 消した問い
    seq: 3
    added_seq: 1
"""


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """種類の連番の最大 + 1 を返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"), make_item("D-2"), raw_files={"changes.yaml": CHANGES_WITH_REMOVED}
    )
    before = snapshot_tree(root)
    # 実行
    result = call_tool("next_id", workspace=str(root), kind="decision")
    # 検証
    assert result.is_error is False
    assert result.data == {"ids": ["D-4"]}
    assert snapshot_tree(root) == before


def test_normal_when_parallel(
    make_workspace: MakeWorkspace, make_item: MakeItem, mcp_server: McpServer
) -> None:
    """書き込む前に続けて取っても、同じ ID を返さない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    first = mcp_server.client
    second = mcp_server.connect()
    # 実行
    with ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(first.call, "next_id", workspace=str(root), kind="decision")
        two = pool.submit(second.call, "next_id", workspace=str(root), kind="decision", count=2)
        results = [one.result(), two.result()]
    after = first.call("next_id", workspace=str(root), kind="decision")
    # 検証
    assert [result.is_error for result in results] == [False, False]
    assert sorted(
        [*results[0].data["ids"], *results[1].data["ids"]]  # type: ignore[index]
    ) == ["D-2", "D-3", "D-4"]
    assert after.data == {"ids": ["D-5"]}


def test_error_when_unknown_kind(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """知らない種類には ID を振らない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    rejected = call_tool("next_id", workspace=str(root), kind="thread")
    accepted = call_tool("next_id", workspace=str(root), kind="decision")
    # 検証
    assert rejected.is_error is True
    assert rejected.text.startswith("エラー: 引数の誤り: kind:")
    assert accepted.data == {"ids": ["D-2"]}


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """.mindstella/config.yaml が無いフォルダを指すと、ID を振らない（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("next_id", workspace=str(root), kind="decision")
    # 検証
    assert result.is_error is True
    assert str(root) in result.text
