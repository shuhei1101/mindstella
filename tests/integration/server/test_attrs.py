"""attrs（属性名の一覧）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

from .fixture_types import CallTool, MakeItem, MakeWorkspace


def test_normal(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool) -> None:
    """種類をまたいで属性名と件数を数える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", attrs={"担当": "自分"}),
        make_item("D-2", attrs={"担当": "自分"}),
        make_item("T-1", attrs={"期限": "来週", "担当": "自分"}),
    )
    # 実行
    result = call_tool("attrs", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data == {
        "attrs": [
            {"name": "担当", "count": 3, "kinds": ["decision", "task"]},
            {"name": "期限", "count": 1, "kinds": ["task"]},
        ]
    }


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("attrs", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text
