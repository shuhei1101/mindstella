"""batch（まとめての読み書き）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .fixture_types import CallTool, LockDirs, MakeItem, MakeWorkspace, SnapshotTree
from .history_helpers import add_item, commit, read_changes, read_items
from workspace_fixtures import RECORD_DIR

# 先に足した項目を指す $番号 を使う、追加・更新・取得の操作
NORMAL_OPERATIONS: list[dict[str, Any]] = [
    {
        "op": "add",
        "kind": "decision",
        "item": {
            "title": "記録の単位",
            "target": "mindmap",
            "category": "データ構造",
            "phase": "要件",
            "status": "未決定",
            "options": [{"key": "A", "content": "1 日ごと"}],
        },
    },
    {
        "op": "add",
        "kind": "task",
        "item": {"title": "記録の単位を調べる", "kind": "調査", "status": "未着手", "for": ["$1"]},
    },
    {"op": "update", "id": "D-1", "item": {"answer": "月ごとに分ける", "status": "決定済み"}},
    {"op": "show", "id": "D-1"},
]


def test_normal(
    make_workspace: MakeWorkspace, call_tool: CallTool
) -> None:
    """追加・先の追加を指す追加・更新・取得を 1 回で当てる（正常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "decision", {"title": "最初の問い", "status": "未決定"})
    commit(call_tool, root, "足す")
    # 実行
    result = call_tool("batch", workspace=str(root), operations=NORMAL_OPERATIONS)
    # 検証
    assert result.is_error is False
    assert result.data is not None
    results = result.data["results"]
    assert [entry["op"] for entry in results] == ["add", "add", "update", "show"]
    assert results[0]["result"]["id"] == "D-2"
    assert results[1]["result"]["id"] == "T-1"
    shown = results[3]["result"]["item"]
    assert shown["answer"] == "月ごとに分ける"
    assert shown["status"] == "決定済み"
    task = read_items(root, "tasks.yaml")[0]
    assert task["for"] == ["D-2"]
    decisions = {item["id"]: item for item in read_items(root, "decisions.yaml")}
    assert len(decisions["D-1"]["history"]) == 1
    # 3 つの書き換えの通し番号がどれも違い、最も大きいものが last_seq と同じ
    seqs = [decisions["D-2"]["seq"], task["seq"], decisions["D-1"]["seq"]]
    changes = read_changes(root)
    assert len(set(seqs)) == 3
    assert max(seqs) == changes["last_seq"]
    assert changes["pending"] == {"added": ["D-2", "T-1"], "changed": ["D-1"]}


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("batch", workspace=str(root), operations=NORMAL_OPERATIONS[:1])
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_id_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """途中の更新が存在しない ID を指すと、前の追加も書かずに終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    operations = [
        NORMAL_OPERATIONS[0],
        {"op": "update", "id": "D-9", "item": {"answer": "a"}},
    ]
    # 実行
    result = call_tool("batch", workspace=str(root), operations=operations)
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: 2 番目の操作（update）:")
    assert "D-9" in result.text
    assert snapshot_tree(root) == before


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """途中の更新がスキーマに合わないと、何も書かずに終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    operations = [
        NORMAL_OPERATIONS[0],
        {"op": "update", "id": "D-1", "item": {"status": "完了"}},
    ]
    # 実行
    result = call_tool("batch", workspace=str(root), operations=operations)
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: 2 番目の操作（update）:")
    assert any(
        line.startswith("decisions.yaml") and "status" in line for line in result.text.splitlines()
    )
    assert snapshot_tree(root) == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは何も書き換えず、エラーの行を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    lock_dirs(root / RECORD_DIR)
    operations = [
        NORMAL_OPERATIONS[0],
        {"op": "update", "id": "D-1", "item": {"answer": "a"}},
    ]
    # 実行
    result = call_tool("batch", workspace=str(root), operations=operations)
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert "Traceback" not in result.text
    assert snapshot_tree(root) == before


def test_error_when_argument_invalid(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """後ろの追加を指す $番号 を渡すと、何も書かずに引数の誤りを返す（異常系）。"""
    # 準備
    root = make_workspace()
    before = snapshot_tree(root)
    operations = [
        {
            "op": "add",
            "kind": "task",
            "item": {"title": "調べる", "kind": "調査", "status": "未着手", "for": ["$2"]},
        },
        NORMAL_OPERATIONS[0],
    ]
    # 実行
    result = call_tool("batch", workspace=str(root), operations=operations)
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: 1 番目の操作（add）:")
    assert "$2" in result.text
    assert snapshot_tree(root) == before
