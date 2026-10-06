"""採用する案の切り替え（スキルが採用する案を切り替え、影響を洗い出す）の E2E テスト。"""

from __future__ import annotations

from typing import Any

import pytest
import yaml
from workspace_fixtures import RECORD_DIR, CallTool, MakeItem, MakeWorkspace, SnapshotTree


@pytest.fixture
def two_options() -> list[dict[str, Any]]:
    """案 A（採用）と案 B を持つ検討事項の案を返す。"""
    return [
        {"key": "A", "content": "種類ごとに分ける", "adopted": True},
        {"key": "B", "content": "1 つにまとめる", "adopted": False},
    ]


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    two_options: list[dict[str, Any]],
) -> None:
    """D-1 の採用する案を B に切り替え、影響を受ける項目を洗い出す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", status="決定済み", options=two_options),
        make_item("D-2", status="決定済み", depends_on=["D-1"]),
        make_item("D-3", depends_on=["D-2"]),
        make_item("T-1", **{"for": ["D-3"]}),
        make_item("D-4", status="決定済み"),
    )
    # 実行
    switched = call_tool("adopt", workspace=str(root), id="D-1", key="B")
    affected = call_tool("impact", workspace=str(root), id="D-1")
    # 検証
    assert switched.is_error is False
    decisions = yaml.safe_load(
        (root / RECORD_DIR / "decisions.yaml").read_text(encoding="utf-8")
    )["items"]
    options = decisions[0]["options"]
    assert options[0]["adopted"] is False
    assert options[1]["adopted"] is True
    # D-1 が変更履歴を 1 回分持ち、切り替える前の案の採否が入っている
    assert len(decisions[0]["history"]) == 1
    assert decisions[0]["history"][0]["before"]["options"] == two_options
    # D-1 の updated_by が ai で、その変更履歴の回が書き換えた人 ai を持つ
    assert decisions[0]["updated_by"] == "ai"
    assert decisions[0]["history"][0]["by"] == "ai"
    assert affected.is_error is False
    rows = affected.data["affected"]
    assert [row["id"] for row in rows] == ["D-2", "D-3", "T-1"]
    assert [row["via"] for row in rows] == [[], ["D-2"], ["D-2", "D-3"]]


def test_error_when_option_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    two_options: list[dict[str, Any]],
) -> None:
    """存在しない案を指すと、持っている案を示すエラーになり、何も書き換えない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=two_options))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("adopt", workspace=str(root), id="D-1", key="Z")
    # 検証
    assert result.is_error is True
    assert "Z" in result.text
    assert "A" in result.text
    assert "B" in result.text
    assert snapshot_tree(root) == before
