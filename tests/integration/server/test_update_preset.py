"""update_preset（プリセットの更新）の結合テスト。"""

from __future__ import annotations

from typing import Any

from .fixture_types import CallTool, MakeItem, MakeWorkspace
from .preset_helpers import config_text, eq, ne, read_settings, tags, with_presets

# 「画面の設計」の説明
DESCRIPTION = "画面の設計の資料だけを開く"


def test_normal(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any], call_tool: CallTool
) -> None:
    """タグの式を置き換え、名前と説明と並びを保つ（正常系）。"""
    # 準備
    notice = {"name": "通知", "filter": eq("通知")}
    root = make_workspace(
        make_item("A-1", tags=tags("画面")),
        make_item("A-2", tags=tags("画面", "廃止")),
        settings=with_presets(
            valid_settings,
            {"name": "画面の設計", "description": DESCRIPTION, "filter": eq("画面")},
            notice,
        ),
    )
    expr = {"and": [eq("画面"), ne("廃止")]}
    # 実行
    result = call_tool("update_preset", workspace=str(root), name="画面の設計", filter=expr)
    # 検証
    assert result.is_error is False, result.text
    assert result.data is not None
    assert (result.data["count"], result.data["position"]) == (1, 1)
    assert read_settings(root)["presets"] == [
        {"name": "画面の設計", "description": DESCRIPTION, "filter": expr},
        notice,
    ]


def test_normal_when_rename_and_move(
    make_workspace: MakeWorkspace, valid_settings: dict[str, Any], call_tool: CallTool
) -> None:
    """名前を変え、並びの先頭へ移す（正常系）。"""
    # 準備
    root = make_workspace(
        settings=with_presets(
            valid_settings,
            {"name": "画面の設計", "filter": eq("画面")},
            {"name": "通知", "filter": eq("通知")},
        )
    )
    # 実行
    result = call_tool("update_preset", workspace=str(root), name="通知", new_name="通知の設計", position=1)
    # 検証
    assert result.is_error is False, result.text
    assert result.data is not None
    assert result.data["position"] == 1
    assert read_settings(root)["presets"] == [
        {"name": "通知の設計", "filter": eq("通知")},
        {"name": "画面の設計", "filter": eq("画面")},
    ]


def test_normal_when_unchanged(
    make_workspace: MakeWorkspace, valid_settings: dict[str, Any], call_tool: CallTool
) -> None:
    """今と同じ値を指定すると、書き込まずに同じ結果を返却する（正常系）。"""
    # 準備
    root = make_workspace(settings=with_presets(valid_settings, {"name": "画面の設計", "filter": eq("画面")}))
    config = root / ".mindstella" / "config.yaml"
    before = config.stat().st_mtime_ns
    # 実行
    result = call_tool("update_preset", workspace=str(root), name="画面の設計", filter=eq("画面"))
    # 検証
    assert result.is_error is False, result.text
    assert result.data is not None
    assert result.data["files"] == []
    assert config.stat().st_mtime_ns == before


def test_error_when_preset_not_found(
    make_workspace: MakeWorkspace, valid_settings: dict[str, Any], call_tool: CallTool
) -> None:
    """該当するプリセットが無い名前を拒む（異常系）。"""
    # 準備
    root = make_workspace(settings=with_presets(valid_settings, {"name": "画面の設計", "filter": eq("画面")}))
    before = config_text(root)
    # 実行
    result = call_tool("update_preset", workspace=str(root), name="通知", filter=eq("通知"))
    # 検証
    assert result.is_error is True
    assert "通知" in result.text
    assert "画面の設計" in result.text
    assert config_text(root) == before


def test_error_when_name_taken(
    make_workspace: MakeWorkspace, valid_settings: dict[str, Any], call_tool: CallTool
) -> None:
    """ほかのプリセットと重なる変更後の名前を拒む（異常系）。"""
    # 準備
    root = make_workspace(
        settings=with_presets(
            valid_settings,
            {"name": "画面の設計", "filter": eq("画面")},
            {"name": "通知", "filter": eq("通知")},
        )
    )
    before = config_text(root)
    # 実行
    result = call_tool("update_preset", workspace=str(root), name="通知", new_name="画面の設計")
    # 検証
    assert result.is_error is True
    assert "画面の設計" in result.text
    assert config_text(root) == before


def test_error_when_filter_invalid(
    make_workspace: MakeWorkspace, valid_settings: dict[str, Any], call_tool: CallTool
) -> None:
    """空の束を持つ式を拒む（異常系）。"""
    # 準備
    root = make_workspace(settings=with_presets(valid_settings, {"name": "画面の設計", "filter": eq("画面")}))
    before = config_text(root)
    # 実行
    result = call_tool("update_preset", workspace=str(root), name="画面の設計", filter={"or": []})
    # 検証
    assert result.is_error is True
    assert "filter.or: 空の束" in result.text
    assert config_text(root) == before


def test_error_when_nothing_given(
    make_workspace: MakeWorkspace, valid_settings: dict[str, Any], call_tool: CallTool
) -> None:
    """書き換える値を 1 つも指定しないと拒む（異常系）。"""
    # 準備
    root = make_workspace(settings=with_presets(valid_settings, {"name": "画面の設計", "filter": eq("画面")}))
    before = config_text(root)
    # 実行
    result = call_tool("update_preset", workspace=str(root), name="画面の設計")
    # 検証
    assert result.is_error is True
    assert "new_name" in result.text
    assert config_text(root) == before
