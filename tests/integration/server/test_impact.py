"""impact（影響の洗い出し）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

from .fixture_types import CallTool, MakeItem, MakeWorkspace, SnapshotTree


def test_normal(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool) -> None:
    """検討事項から依存とタスクをたどり、関係しない項目は出さない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("D-2", title="直接の依存", depends_on=["D-1"]),
        make_item("D-3", title="派生した問い", parent="D-2"),
        make_item("D-4", title="関連するだけ", related=["D-1"]),
        make_item("T-1", title="進めるタスク", **{"for": ["D-3"]}),
    )
    # 実行
    result = call_tool("impact", workspace=str(root), id="D-1")
    # 検証
    assert result.is_error is False
    payload = result.data
    assert payload["id"] == "D-1"
    assert payload["affected"] == [
        {"id": "D-2", "title": "直接の依存", "status": "未決定", "via": [], "key": "depends_on"},
        {"id": "D-3", "title": "派生した問い", "status": "未決定", "via": ["D-2"], "key": "parent"},
        {
            "id": "T-1",
            "title": "進めるタスク",
            "status": "未着手",
            "via": ["D-2", "D-3"],
            "key": "for",
        },
    ]


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """mindmap.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("impact", workspace=str(root), id="D-1")
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_id_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """存在しない ID を起点にするとエラーで終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("impact", workspace=str(root), id="D-9")
    # 検証
    assert result.is_error is True
    assert "D-9" in result.text
    assert snapshot_tree(root) == before
