"""tags（タグの一覧）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .fixture_types import CallTool, MakeItem, MakeWorkspace


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
) -> None:
    """語彙のタグごとに、説明と種類をまたいで数えた件数を返す。持つ項目が無いタグも返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["データ"]),
        make_item("D-2", tags=["画面"]),
        make_item("T-1", tags=["データ"]),
        make_item("N-1"),
        settings={
            **valid_settings,
            "tags": [
                {"name": "データ", "summary": "記録の形"},
                {"name": "画面", "summary": "利用者が見る画面"},
                {"name": "保留"},
            ],
        },
    )
    # 実行
    result = call_tool("tags", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data == {
        "tags": [
            {"name": "データ", "summary": "記録の形", "count": 2, "kinds": ["decision", "task"]},
            {"name": "保留", "summary": None, "count": 0, "kinds": []},
            {"name": "画面", "summary": "利用者が見る画面", "count": 1, "kinds": ["decision"]},
        ]
    }


def test_normal_when_no_tags(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """語彙が空なら空の一覧を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = call_tool("tags", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data == {"tags": []}


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("tags", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text
