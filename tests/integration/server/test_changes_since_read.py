"""changes_since_read（前回読んだ時点からの変更）の結合テスト。"""

from __future__ import annotations

import stat
from pathlib import Path

from .fixture_types import CallTool, LockDirs, MakeWorkspace, SnapshotTree
from .history_helpers import OPTIONS, add_item, read_changes, update_item, write_settings
from workspace_fixtures import RECORD_DIR

# 3 行の本文（2 行目だけを書き換える）
BODY = "1 行目\n2 行目\n3 行目\n"
REWRITTEN_BODY = "1 行目\n書き換えた 2 行目\n3 行目\n"


def test_normal(make_workspace: MakeWorkspace, call_tool: CallTool, snapshot_tree: SnapshotTree) -> None:
    """読んだ時点より後の追加と変更を、読んだ時点の値つきで返し、読んだ時点を進める（正常系）。"""
    # 準備
    root = make_workspace()
    add_item(
        call_tool,
        root,
        "decision",
        {"title": "問い A", "status": "未決定", "options": OPTIONS, "body_markdown": BODY},
    )
    first = call_tool("changes_since_read", workspace=str(root))
    assert first.is_error is False
    update_item(call_tool, root, "D-1", {"title": "問い B"})
    update_item(call_tool, root, "D-1", {"title": "問い C", "body_markdown": REWRITTEN_BODY})
    add_item(call_tool, root, "task", {"title": "調べる", "kind": "調査", "status": "未着手"})
    before = snapshot_tree(root)
    # 実行
    result = call_tool("changes_since_read", workspace=str(root))
    again = call_tool("changes_since_read", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["had_read_point"] is True
    assert result.data["added"] == [
        {"id": "T-1", "kind": "task", "title": "調べる", "updated_by": "ai"}
    ]
    assert len(result.data["changed"]) == 1
    changed = result.data["changed"][0]
    assert changed["id"] == "D-1"
    assert changed["before"] == {"title": "問い A"}
    # 読んだ後の 2 回の書き換えは AI がした
    assert changed["updated_by"] == "ai"
    assert changed["by"] == ["ai"]
    # 本文は変えた 2 行目だけの差分で、1 行目・3 行目を含まない
    assert changed["body_diff"] == [{"line": 2, "now": ["書き換えた 2 行目"], "before": ["2 行目"]}]
    # 読んだ後、読んだ時点が last_seq と同じ
    changes = read_changes(root)
    assert changes["read_seq"] == changes["last_seq"] == result.data["until_seq"]
    # 2 回目は空
    assert again.data is not None
    assert again.data["added"] == []
    assert again.data["changed"] == []
    # 項目の YAML と本文は書き換えない
    after = snapshot_tree(root)
    assert {name: text for name, text in after.items() if name != ".mindstella/changes.yaml"} == {
        name: text for name, text in before.items() if name != ".mindstella/changes.yaml"
    }


def test_normal_when_no_read_point(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """読んだ時点が無ければ差分を返さず、今の last_seq を記録する（正常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "decision", {"title": "問い", "status": "未決定", "options": OPTIONS})
    update_item(call_tool, root, "D-1", {"answer": "答え"})
    # 実行
    result = call_tool("changes_since_read", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["had_read_point"] is False
    assert result.data["read_seq"] is None
    assert result.data["added"] == []
    assert result.data["changed"] == []
    changes = read_changes(root)
    assert changes["read_seq"] == changes["last_seq"]


def test_normal_when_history_limit_zero(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """変更履歴が無いときは、変えた項目を ID だけで返す（正常系）。"""
    # 準備
    root = make_workspace()
    write_settings(root, history_limit=0)
    add_item(call_tool, root, "decision", {"title": "問い", "status": "未決定", "options": OPTIONS})
    call_tool("changes_since_read", workspace=str(root))
    update_item(call_tool, root, "D-1", {"answer": "答え"})
    add_item(call_tool, root, "task", {"title": "調べる", "kind": "調査", "status": "未着手"})
    # 実行
    result = call_tool("changes_since_read", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert [entry["id"] for entry in result.data["added"]] == ["T-1"]
    assert len(result.data["changed"]) == 1
    changed = result.data["changed"][0]
    assert changed["id"] == "D-1"
    assert changed["before"] is None
    assert changed["body_diff"] is None


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("changes_since_read", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text
    assert not (root / RECORD_DIR / "changes.yaml").exists()


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """読んだ時点を書けないときは書き換えず、次に呼んだときに同じ変更を返す（異常系）。"""
    # 準備
    root = make_workspace()
    call_tool("changes_since_read", workspace=str(root))
    add_item(call_tool, root, "decision", {"title": "問い", "status": "未決定", "options": OPTIONS})
    read_before = read_changes(root)["read_seq"]
    before = snapshot_tree(root)
    lock_dirs(root / RECORD_DIR)
    # 実行
    failed = call_tool("changes_since_read", workspace=str(root))
    # 検証
    assert failed.is_error is True
    assert failed.text.startswith("エラー: ")
    assert "Traceback" not in failed.text
    assert snapshot_tree(root) == before
    # 権限を戻して呼び直すと、同じ変更が返る
    (root / RECORD_DIR).chmod(stat.S_IRWXU)
    assert read_changes(root)["read_seq"] == read_before
    retry = call_tool("changes_since_read", workspace=str(root))
    assert retry.is_error is False
    assert retry.data is not None
    assert [entry["id"] for entry in retry.data["added"]] == ["D-1"]
