"""update（項目の更新）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .fixture_types import (
    CallTool,
    LockDirs,
    MakeItem,
    MakeLegacyWorkspace,
    MakeWorkspace,
    SnapshotTree,
)
from .history_helpers import (
    DECISION_ITEM,
    add_item,
    commit,
    read_changes,
    read_items,
    update_item,
    write_settings,
)

# 検討事項 D-1 を足して `commit` した後の `changes.yaml`
COMMITTED_D1 = (
    "last_seq: 0\nsets:\n- id: V-1\n  at: '2026-10-01T00:00:00+00:00'\n  summary: 足す\n"
    "  until_seq: 0\n  added: [D-1]\n  changed: []\npending:\n  added: []\n  changed: []\n"
)

# 本文（3 行）と、2 行目を書き換えた本文
BODY_BEFORE = "1 行目\n2 行目\n3 行目\n"
BODY_AFTER = "1 行目\n書き換えた 2 行目\n3 行目\n"


def _read_decisions(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの検討事項の並びを読む。"""
    return yaml.safe_load((root / "decisions.yaml").read_text(encoding="utf-8"))["items"]


def test_normal(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool) -> None:
    """検討事項の答えと状態を直し、不要になったキーを消して、変更履歴を 1 回分積む（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", status="未決定", lead=DECISION_ITEM["lead"], weight="大"),
        raw_files={"changes.yaml": COMMITTED_D1},
    )
    item = {"answer": "種類ごとに分ける", "status": "決定済み", "weight": None}
    # 実行
    result = call_tool("update", workspace=str(root), id="D-1", item=item)
    # 検証
    assert result.is_error is False
    payload = result.data
    assert payload["id"] == "D-1"
    assert payload["file"] == "decisions.yaml"
    assert payload["changed"] == ["answer", "status", "weight"]
    updated_item = _read_decisions(root)[0]
    assert updated_item["answer"] == "種類ごとに分ける"
    assert updated_item["status"] == "決定済み"
    assert "weight" not in updated_item
    assert updated_item["lead"] == DECISION_ITEM["lead"]
    assert updated_item["created"] == "2026-10-01T00:00:00+00:00"
    assert updated_item["updated"] > updated_item["created"]
    assert len(updated_item["history"]) == 1
    assert updated_item["history"][0]["before"] == {
        "answer": None,
        "status": "未決定",
        "weight": "大",
    }
    changes = read_changes(root)
    assert changes["pending"]["changed"] == ["D-1"]
    assert changes["last_seq"] == updated_item["history"][0]["seq"]


def test_normal_when_body_rewritten_over_limit(
    make_workspace: MakeWorkspace, call_tool: CallTool
) -> None:
    """本文を直して保持する回数を超えると、古い回を消して消した回の seq を残す（正常系）。"""
    # 準備
    root = make_workspace()
    write_settings(root, history_limit=1)
    add_item(call_tool, root, "decision", {**DECISION_ITEM, "body_markdown": BODY_BEFORE})
    commit(call_tool, root, "足す")
    update_item(call_tool, root, "D-1", {"answer": "種類ごとに分ける"})
    answer_seq = read_items(root, "decisions.yaml")[0]["history"][0]["seq"]
    # 実行
    result = call_tool("update", workspace=str(root), id="D-1", item={"body_markdown": BODY_AFTER})
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["changed"] == ["body_markdown"]
    item = _read_decisions(root)[0]
    assert len(item["history"]) == 1
    entry = item["history"][0]
    assert "answer" not in entry["before"]
    assert entry["body_diff"] == [
        {"line": 2, "now": ["書き換えた 2 行目"], "before": ["2 行目"]},
    ]
    assert (root / "docs" / "D-1.md").read_text(encoding="utf-8") == BODY_AFTER
    assert item["history_dropped_seq"] == answer_seq


def test_normal_when_nothing_changed(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """今と同じ値を渡すと、変更履歴を積まず、まとめていない変更にも足さない（正常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "decision", {**DECISION_ITEM, "answer": "a"})
    commit(call_tool, root, "足す")
    # 実行
    result = call_tool("update", workspace=str(root), id="D-1", item={"answer": "a"})
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["changed"] == []
    assert "history" not in _read_decisions(root)[0]
    assert read_changes(root)["pending"] == {"added": [], "changed": []}


def test_normal_when_limit_zero(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """保持する回数が 0 のときは積まず、持っている変更履歴を消す（正常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "decision", DECISION_ITEM)
    commit(call_tool, root, "足す")
    update_item(call_tool, root, "D-1", {"answer": "種類ごとに分ける"})
    commit(call_tool, root, "直す")
    assert "history" in _read_decisions(root)[0]
    write_settings(root, history_limit=0)
    # 実行
    result = call_tool("update", workspace=str(root), id="D-1", item={"status": "決定済み"})
    # 検証
    assert result.is_error is False
    item = _read_decisions(root)[0]
    assert item["status"] == "決定済み"
    assert "history" not in item
    assert read_changes(root)["pending"]["changed"] == []


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """mindmap.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("update", workspace=str(root), id="D-1", item={"answer": "a"})
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_id_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """存在しない ID は直さず、渡した ID を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("update", workspace=str(root), id="D-9", item={"answer": "a"})
    # 検証
    assert result.is_error is True
    assert "D-9" in result.text
    assert snapshot_tree(root) == before


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """スクリプトが付けるキー created を渡すと直さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    item = {"created": "2000-01-01T00:00:00+00:00"}
    # 実行
    result = call_tool("update", workspace=str(root), id="D-1", item=item)
    # 検証
    assert result.is_error is True
    assert "created" in result.text
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
    lock_dirs(root)
    # 実行
    result = call_tool("update", workspace=str(root), id="D-1", item={"answer": "a"})
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert "Traceback" not in result.text
    assert snapshot_tree(root) == before


def test_error_when_legacy_format(
    make_item: MakeItem,
    make_legacy_workspace: MakeLegacyWorkspace,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """資料の done が残るワークスペースでは何も書かず、/mindstella:upgrade を案内して終わる（異常系）。"""
    # 準備
    root = make_legacy_workspace(make_item("D-1"), legacy_docs={"A-1": True})
    before = snapshot_tree(root)
    # 実行
    result = call_tool("update", workspace=str(root), id="D-1", item={"answer": "種類ごとに分ける"})
    # 検証
    assert result.is_error is True
    lines = result.text.splitlines()
    assert any(line.startswith("docs.yaml: items[0]") for line in lines)
    assert lines[-1] == "ヒント: 前の版の形式の記録は /mindstella:upgrade で今の形式に移せます"
    assert snapshot_tree(root) == before
