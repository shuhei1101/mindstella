"""記録の検索（スキルが項目を探し、1 件の中身と参照元・使っている属性名を読む）の E2E テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace, SnapshotTree


@pytest.fixture
def search_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> Path:
    """文字・タグ・属性・参照を持つ D-1・D-2・T-1 のワークスペースを作る。"""
    return make_workspace(
        make_item("D-1", title="スキーマの設計", tags=["データ"], attrs={"担当": "自分"}),
        make_item("D-2", title="別の問い", depends_on=["D-1"], attrs={"担当": "自分"}),
        make_item("T-1", title="作業", attrs={"期限": "10 月"}, **{"for": ["D-1"]}),
    )


def test_normal(search_workspace: Path, call_tool: CallTool, snapshot_tree: SnapshotTree) -> None:
    """文字で探し、D-1 の中身と参照元を読み、使っている属性名を読む（正常系）。"""
    # 準備
    before = snapshot_tree(search_workspace)
    root = str(search_workspace)
    # 実行
    found = call_tool("find", workspace=root, text="スキーマ")
    shown = call_tool("show", workspace=root, id="D-1")
    attrs = call_tool("attrs", workspace=root)
    # 検証
    assert found.is_error is False
    assert [row["id"] for row in found.data["items"]] == ["D-1"]
    assert shown.is_error is False
    shown_payload = shown.data
    assert shown_payload["item"]["title"] == "スキーマの設計"
    assert shown_payload["item"]["status"] == "未決定"
    assert shown_payload["item"]["tags"] == ["データ"]
    assert shown_payload["item"]["attrs"] == {"担当": "自分"}
    assert shown_payload["referenced_by"] == [
        {"id": "D-2", "key": "depends_on"},
        {"id": "T-1", "key": "for"},
    ]
    assert attrs.is_error is False
    counts = {row["name"]: row["count"] for row in attrs.data["attrs"]}
    assert counts == {"担当": 2, "期限": 1}
    assert snapshot_tree(search_workspace) == before


def test_error_when_id_not_found(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """存在しない ID の中身は出せず、ID が無いエラーになる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = call_tool("show", workspace=str(root), id="D-9")
    # 検証
    assert result.is_error is True
    assert "D-9" in result.text
