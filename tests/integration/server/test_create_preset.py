"""create_preset（プリセットの作成）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from .fixture_types import CallTool, MakeItem, MakeWorkspace, SnapshotTree
from .preset_helpers import config_text, eq, ne, read_settings, tags, with_presets

# 設定ファイルの直下からのパス
CONFIG = ".mindstella/config.yaml"


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """プリセットを追加し、該当する件数を返却する（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1", tags=tags("画面")),
        make_item("A-2", tags=tags("画面", "廃止")),
        make_item("A-3"),
    )
    before = snapshot_tree(root)
    expr = {"and": [eq("画面"), ne("廃止")]}
    # 実行
    result = call_tool("create_preset", workspace=str(root), name="画面の設計", filter=expr)
    # 検証
    assert result.is_error is False, result.text
    assert result.data is not None
    assert result.data["count"] == 1
    assert result.data["warnings"] == []
    assert result.data["files"] == [CONFIG]
    settings = read_settings(root)
    assert settings["presets"] == [{"name": "画面の設計", "filter": expr}]
    assert {key: value for key, value in settings.items() if key != "presets"} == valid_settings
    # 設定以外のファイル（種類ごとの YAML と docs/）が呼ぶ前と同じ
    after = snapshot_tree(root)
    assert {name: text for name, text in after.items() if name != CONFIG} == {
        name: text for name, text in before.items() if name != CONFIG
    }


def test_normal_when_no_match(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """どの項目にも該当しないプリセットも保存し、警告を添える（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1", tags=tags("画面")))
    # 実行
    result = call_tool("create_preset", workspace=str(root), name="通知", filter=eq("通知"))
    # 検証
    assert result.is_error is False, result.text
    assert result.data is not None
    assert result.data["count"] == 0
    assert len(result.data["warnings"]) == 1
    assert [entry["name"] for entry in read_settings(root)["presets"]] == ["通知"]


@pytest.mark.parametrize(
    ("expr", "reason"),
    [
        pytest.param({"and": []}, "filter.and: 空の束", id="empty_bundle"),
        pytest.param({"and": [{"or": [{"not": {"and": [eq("a")]}}]}]}, "3 レイヤー", id="too_deep"),
        pytest.param({**eq("a"), "case_sensitive": True}, "filter.case_sensitive", id="unknown_key"),
    ],
)
def test_error_when_filter_invalid(
    make_workspace: MakeWorkspace, call_tool: CallTool, expr: dict[str, Any], reason: str
) -> None:
    """空の束・4 レイヤーの入れ子・受け付けないキーを拒み、何も書き込まない（異常系）。"""
    # 準備
    root = make_workspace()
    before = config_text(root)
    # 実行
    result = call_tool("create_preset", workspace=str(root), name="画面の設計", filter=expr)
    # 検証
    assert result.is_error is True
    assert reason in result.text
    assert config_text(root) == before


def test_error_when_name_taken(
    make_workspace: MakeWorkspace, valid_settings: dict[str, Any], call_tool: CallTool
) -> None:
    """全角半角・大文字小文字だけ違う名前も重なりとして拒む（異常系）。"""
    # 準備
    root = make_workspace(settings=with_presets(valid_settings, {"name": "UI の設計", "filter": eq("画面")}))
    before = config_text(root)
    # 実行
    result = call_tool("create_preset", workspace=str(root), name="ｕｉ の設計", filter=eq("画面"))
    # 検証
    assert result.is_error is True
    assert "UI の設計" in result.text
    assert config_text(root) == before


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """.mindstella/config.yaml が無いフォルダを指すと、何も書き込まずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("create_preset", workspace=str(root), name="画面の設計", filter=eq("画面"))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text
    assert list(root.iterdir()) == []
