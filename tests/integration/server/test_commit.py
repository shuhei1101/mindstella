"""commit（書き換えのまとまり）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

from .fixture_types import CallTool, LockDirs, MakeWorkspace, SnapshotTree
from .history_helpers import (
    DECISION_ITEM,
    add_item,
    commit,
    read_changes,
    read_items,
    update_item,
)
from workspace_fixtures import RECORD_DIR

# 手で崩した `changes.yaml`（`pending` から `added` を消した）
BROKEN_CHANGES = "last_seq: 0\nsets: []\npending:\n  changed: []\n"


def test_normal(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """まだまとめていない書き換えを、説明つきのまとまりにする（正常系）。"""
    # 準備
    root = make_workspace()
    decision_id = add_item(call_tool, root, "decision", DECISION_ITEM)
    commit(call_tool, root, "足す")
    update_item(call_tool, root, decision_id, {"answer": "種類ごとに分ける"})
    task_id = add_item(call_tool, root, "task", {"title": "決める", "kind": "作業", "status": "未着手"})
    first = read_changes(root)
    before = {
        "decisions": (root / RECORD_DIR / "decisions.yaml").read_bytes(),
        "tasks": (root / RECORD_DIR / "tasks.yaml").read_bytes(),
    }
    # 実行
    result = call_tool("commit", workspace=str(root), summary="D-1 を決め、T-1 を積む")
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["id"] == "V-2"
    assert result.data["added"] == [task_id]
    assert result.data["changed"] == [decision_id]
    assert result.data["summary"] == "D-1 を決め、T-1 を積む"
    changes = read_changes(root)
    assert changes["sets"][0]["id"] == "V-2"
    assert changes["sets"][0]["until_seq"] == changes["last_seq"]
    assert changes["pending"] == {"added": [], "changed": []}
    history_seq = read_items(root, "decisions.yaml")[0]["history"][0]["seq"]
    assert first["sets"][0]["until_seq"] < history_seq <= changes["sets"][0]["until_seq"]
    assert (root / RECORD_DIR / "decisions.yaml").read_bytes() == before["decisions"]
    assert (root / RECORD_DIR / "tasks.yaml").read_bytes() == before["tasks"]


def test_normal_when_nothing_pending(
    make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """まとめる書き換えが無いときは、まとまりを足さない（正常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "decision", DECISION_ITEM)
    commit(call_tool, root, "足す")
    before = snapshot_tree(root)
    # 実行
    result = call_tool("commit", workspace=str(root), summary="何もしない")
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["id"] is None
    assert result.data["at"] is None
    assert result.data["summary"] is None
    assert result.data["added"] == []
    assert result.data["changed"] == []
    assert snapshot_tree(root) == before


def test_error_when_summary_empty(
    make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """空白だけの説明は引数の誤りにして、何も書かない（異常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "decision", DECISION_ITEM)
    before = snapshot_tree(root)
    # 実行
    result = call_tool("commit", workspace=str(root), summary="   ")
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: 引数の誤り: summary:")
    assert snapshot_tree(root) == before


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("commit", workspace=str(root), summary="a")
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """手で崩した changes.yaml が残っていると、まとめずに合わない箇所を返す（異常系）。"""
    # 準備
    root = make_workspace(raw_files={"changes.yaml": BROKEN_CHANGES})
    before = snapshot_tree(root)
    # 実行
    result = call_tool("commit", workspace=str(root), summary="a")
    # 検証
    assert result.is_error is True
    assert "changes.yaml: pending" in result.text
    assert snapshot_tree(root) == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは、まとめずにエラーの行を返す（異常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "decision", DECISION_ITEM)
    before = snapshot_tree(root)
    lock_dirs(root / RECORD_DIR)
    # 実行
    result = call_tool("commit", workspace=str(root), summary="a")
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert "Traceback" not in result.text
    assert snapshot_tree(root) == before
