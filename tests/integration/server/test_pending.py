"""pending（まだまとめていない変更）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

from .fixture_types import CallTool, MakeWorkspace, SnapshotTree
from .history_helpers import DECISION_ITEM, add_item, commit, remove_item, update_item
from workspace_fixtures import RECORD_DIR

# 手で崩した `changes.yaml`（`pending` から `added` を消した）
BROKEN_CHANGES = "last_seq: 0\nsets: []\npending:\n  changed: []\n"


def test_normal(make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree) -> None:
    """足した項目と、変えた項目・変えたキーを返し、何も書き換えない（正常系）。"""
    # 準備
    root = make_workspace()
    decision_id = add_item(call_tool, root, "decision", DECISION_ITEM)
    commit(call_tool, root, "足す")
    update_item(call_tool, root, decision_id, {"answer": "種類ごとに分ける", "reason": "探しやすい"})
    task_id = add_item(call_tool, root, "task", {"title": "決める", "kind": "作業", "status": "未着手"})
    before = snapshot_tree(root)
    # 実行
    result = call_tool("pending", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["added"] == [{"id": task_id, "title": "決める"}]
    assert len(result.data["changed"]) == 1
    changed = result.data["changed"][0]
    assert changed["id"] == decision_id
    assert changed["title"] == DECISION_ITEM["title"]
    assert sorted(changed["keys"]) == ["answer", "reason"]
    assert snapshot_tree(root) == before


def test_normal_when_empty(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """まとめていない変更が無ければ、空の一覧を返し、changes.yaml を作らない（正常系）。"""
    # 準備
    root = make_workspace()
    # 実行
    result = call_tool("pending", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["added"] == []
    assert result.data["changed"] == []
    assert not (root / RECORD_DIR / "changes.yaml").exists()


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("pending", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_schema_mismatch(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """手で崩した changes.yaml が残っていると、合わない箇所を返す（異常系）。"""
    # 準備
    root = make_workspace(raw_files={"changes.yaml": BROKEN_CHANGES})
    # 実行
    result = call_tool("pending", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert "changes.yaml: pending" in result.text


def test_normal_when_item_removed(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """まとめた後に消した項目を、ID・種類・消したときのタイトルで返す（正常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "note", {"title": "メモ", "content": "中身"})
    add_item(call_tool, root, "note", {"title": "重複したメモ", "content": "中身"})
    commit(call_tool, root, "足す")
    remove_item(call_tool, root, "N-2")
    # 実行
    result = call_tool("pending", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["removed"] == [{"id": "N-2", "kind": "note", "title": "重複したメモ"}]
    assert result.data["added"] == []
    assert result.data["changed"] == []
