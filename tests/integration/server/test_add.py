"""add（項目の追加）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .fixture_types import CallTool, LockDirs, MakeItem, MakeWorkspace, SnapshotTree

# リクエスト例の検討事項
NEW_DECISION: dict[str, Any] = {
    "title": "YAML のキーをどう分けるか",
    "target": "mindmap",
    "category": "データ構造",
    "phase": "要件",
    "status": "未決定",
    "lead": "種類ごとにキーを分けるかを決める。",
    "weight": "大",
    "depends_on": ["D-1"],
    "body_markdown": "## 経緯\n\n種類ごとに分ける案を考えた。\n",
}


def test_normal(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool) -> None:
    """本文つきの検討事項を足す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = call_tool("add", workspace=str(root), kind="decision", item=NEW_DECISION)
    # 検証
    assert result.is_error is False
    assert result.data == {
        "id": "D-2",
        "file": "decisions.yaml",
        "body": "docs/D-2.md",
    }
    added = yaml.safe_load((root / "decisions.yaml").read_text(encoding="utf-8"))["items"][1]
    created = added.pop("created")
    updated = added.pop("updated")
    assert created == updated
    # 通し番号は、足したときに振った `changes.yaml` の `last_seq` と同じ
    changes = yaml.safe_load((root / "changes.yaml").read_text(encoding="utf-8"))
    assert added.pop("seq") == changes["last_seq"]
    assert added.pop("added_seq") == changes["last_seq"]
    assert added == {
        "id": "D-2",
        "title": "YAML のキーをどう分けるか",
        "target": "mindmap",
        "category": "データ構造",
        "phase": "要件",
        "status": "未決定",
        "lead": "種類ごとにキーを分けるかを決める。",
        "weight": "大",
        "depends_on": ["D-1"],
        "body": "D-2.md",
    }
    assert (root / "docs" / "D-2.md").read_text(encoding="utf-8") == NEW_DECISION["body_markdown"]
    # 足した項目は変更履歴を持たず、まだまとめていない変更の足した項目に入る
    assert "history" not in added
    assert changes["pending"]["added"] == ["D-2"]


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("add", workspace=str(root), kind="decision", item=NEW_DECISION)
    # 検証
    assert result.is_error is True
    assert str(root) in result.text
    assert list(root.iterdir()) == []


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """状態の値が決めた名前に無い検討事項は足さず、合わない箇所を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    item = {**NEW_DECISION, "status": "完了"}
    # 実行
    result = call_tool("add", workspace=str(root), kind="decision", item=item)
    # 検証
    assert result.is_error is True
    assert "decisions.yaml: items[1].status:" in result.text
    assert "完了" in result.text
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
    lock_dirs(root, root / "docs")
    # 実行
    result = call_tool("add", workspace=str(root), kind="decision", item=NEW_DECISION)
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert "Traceback" not in result.text
    assert snapshot_tree(root) == before


def test_error_when_file_shape_broken(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """書き戻すと既存の項目を失うファイルには足さず、そのファイルの問題を返す（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("D-2"),
        raw_files={"decisions.yaml": "- id: D-1\n  title: 一番上が配列\n"},
    )
    before = snapshot_tree(root)
    # 実行
    result = call_tool("add", workspace=str(root), kind="decision", item=NEW_DECISION)
    # 検証
    assert result.is_error is True
    assert "decisions.yaml: " in result.text
    assert snapshot_tree(root) == before
