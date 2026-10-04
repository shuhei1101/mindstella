"""記録の追加と更新（スキルが検討事項などを足し、後から直す）の E2E テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace, SnapshotTree

# スキルが足す検討事項の中身
NEW_DECISION: dict[str, Any] = {
    "title": "YAML のキーをどう分けるか",
    "target": "mindmap",
    "category": "データ構造",
    "phase": "要件",
    "status": "未決定",
    "lead": "種類ごとにキーを分けるかを決める。",
    "weight": "大",
}


def _read_decisions(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの検討事項の並びを読む。"""
    return yaml.safe_load((root / "decisions.yaml").read_text(encoding="utf-8"))["items"]


def _stdin(data: dict[str, Any]) -> str:
    """標準入力に渡す JSON の文字列にする。"""
    return json.dumps(data, ensure_ascii=False)


def test_normal(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """検討事項を足し、その答えと状態を直す（正常系）。"""
    # 準備
    root = make_workspace()
    # 実行
    added = call_tool("add", workspace=str(root), kind="decision", item=NEW_DECISION)
    item_id = added.data["id"]
    after_add = _read_decisions(root)[0]
    updated = call_tool(
        "update",
        workspace=str(root),
        id=item_id,
        item={"answer": "種類ごとに分ける", "status": "決定済み"},
    )
    checked = call_tool("check", workspace=str(root))
    # 検証
    assert added.is_error is False
    assert item_id.startswith("D-")
    assert len(_read_decisions(root)) == 1
    assert after_add["title"] == "YAML のキーをどう分けるか"
    assert after_add["target"] == "mindmap"
    assert after_add["category"] == "データ構造"
    assert after_add["phase"] == "要件"
    assert after_add["lead"] == "種類ごとにキーを分けるかを決める。"
    assert after_add["weight"] == "大"
    assert updated.is_error is False
    after_update = _read_decisions(root)[0]
    assert after_update["answer"] == "種類ごとに分ける"
    assert after_update["status"] == "決定済み"
    assert after_update["created"] == after_add["created"]
    assert after_update["updated"] >= after_add["updated"]
    # ワークスペースの全ての YAML がスキーマに合う
    assert checked.is_error is False


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """状態に決めた名前に無い値を入れた検討事項は足さず、合わない箇所を示すエラーになる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行
    result = call_tool(
        "add", workspace=str(root), kind="decision", item={**NEW_DECISION, "status": "完了"}
    )
    # 検証
    assert result.is_error is True
    assert "status" in result.text
    assert "完了" in result.text
    assert snapshot_tree(root) == before


def test_error_when_id_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """存在しない ID の答えは直せず、ID が無いエラーになる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("update", workspace=str(root), id="D-9", item={"answer": "決めた答え"})
    # 検証
    assert result.is_error is True
    assert "D-9" in result.text
    assert snapshot_tree(root) == before
