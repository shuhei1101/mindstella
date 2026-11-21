"""delete_preset（プリセットの削除）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .fixture_types import CallTool, MakeWorkspace
from .preset_helpers import config_text, eq, read_settings, with_presets


def test_normal(make_workspace: MakeWorkspace, valid_settings: dict[str, Any], call_tool: CallTool) -> None:
    """プリセットを削除し、ほかのプリセットの並びを保つ（正常系）。"""
    # 準備
    root = make_workspace(
        settings=with_presets(
            valid_settings,
            {"name": "画面の設計", "filter": eq("画面")},
            {"name": "通知", "filter": eq("通知")},
            {"name": "保存", "filter": eq("保存")},
        )
    )
    # 実行
    result = call_tool("delete_preset", workspace=str(root), name="通知")
    # 検証
    assert result.is_error is False, result.text
    assert result.data is not None
    assert result.data["deleted"]["name"] == "通知"
    assert result.data["remaining"] == 2
    assert [entry["name"] for entry in read_settings(root)["presets"]] == ["画面の設計", "保存"]


def test_normal_when_last(make_workspace: MakeWorkspace, valid_settings: dict[str, Any], call_tool: CallTool) -> None:
    """最後の 1 件を削除すると presets のキーごと除く（正常系）。"""
    # 準備
    root = make_workspace(settings=with_presets(valid_settings, {"name": "画面の設計", "filter": eq("画面")}))
    # 実行
    result = call_tool("delete_preset", workspace=str(root), name="画面の設計")
    # 検証
    assert result.is_error is False, result.text
    assert result.data is not None
    assert result.data["remaining"] == 0
    assert read_settings(root) == valid_settings


def test_error_when_preset_not_found(
    make_workspace: MakeWorkspace, valid_settings: dict[str, Any], call_tool: CallTool
) -> None:
    """該当するプリセットが無い名前を拒む（異常系）。"""
    # 準備
    root = make_workspace(settings=with_presets(valid_settings, {"name": "画面の設計", "filter": eq("画面")}))
    before = config_text(root)
    # 実行
    result = call_tool("delete_preset", workspace=str(root), name="通知")
    # 検証
    assert result.is_error is True
    assert "通知" in result.text
    assert "画面の設計" in result.text
    assert config_text(root) == before


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """.mindstella/config.yaml が無いフォルダを指すと、何も書き込まずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("delete_preset", workspace=str(root), name="画面の設計")
    # 検証
    assert result.is_error is True
    assert str(root) in result.text
    assert list(root.iterdir()) == []
