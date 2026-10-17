"""find（項目の検索）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from .fixture_types import CallTool, MakeItem, MakeWorkspace


@pytest.fixture
def schema_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> Path:
    """文字と属性で探すためのワークスペース（D-1・D-2・T-1）を作る。"""
    return make_workspace(
        make_item("D-1", title="スキーマの設計", attrs={"担当": "自分"}),
        make_item(
            "D-2",
            title="別の問い",
            options=[{"key": "A", "content": "スキーマを分ける"}],
        ),
        make_item("T-1", title="作業", attrs={"担当": "自分"}),
    )


def test_normal(schema_workspace: Path, call_tool: CallTool) -> None:
    """文字と属性で探し、両方に合う項目だけを返す（正常系）。"""
    # 実行
    result = call_tool("find", workspace=str(schema_workspace), text="スキーマ", attr=["担当=自分"])
    # 検証
    assert result.is_error is False
    assert result.data == {
        "items": [
            {
                "id": "D-1",
                "kind": "decision",
                "title": "スキーマの設計",
                "status": "未決定",
                "tags": [],
            }
        ],
        "total": 1,
        "next_cursor": None,
        "hint": None,
    }


def test_normal_when_nested_text(schema_workspace: Path, call_tool: CallTool) -> None:
    """文字だけで探すと、案の中身に含む項目も返す（正常系）。"""
    # 実行
    result = call_tool("find", workspace=str(schema_workspace), text="スキーマ")
    # 検証
    assert result.is_error is False
    items = result.data["items"]
    assert [item["id"] for item in items] == ["D-1", "D-2"]


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("find", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_normal_when_tags_and_any_tags(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
) -> None:
    """tags は全てを持つ項目、any_tags はいずれかを持つ項目を返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["データ"]),
        make_item("D-2", tags=["画面"]),
        make_item("T-1", tags=["データ", "画面"]),
        make_item("N-1"),
        settings={**valid_settings, "tags": [{"name": "データ"}, {"name": "画面"}]},
    )
    # 実行
    all_of = call_tool("find", workspace=str(root), tags=["データ", "画面"])
    any_of = call_tool("find", workspace=str(root), any_tags=["データ", "画面"])
    # 検証
    assert all_of.is_error is False
    assert [item["id"] for item in all_of.data["items"]] == ["T-1"]
    assert any_of.is_error is False
    assert [item["id"] for item in any_of.data["items"]] == ["D-1", "D-2", "T-1"]


def test_normal_when_paged(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """件数を超える分は next_cursor で続きを返し、最初のページに絞り込みの案内を添える（正常系）。"""
    # 準備
    root = make_workspace(*(make_item(f"D-{number}") for number in range(1, 6)))
    # 実行
    first = call_tool("find", workspace=str(root), limit=3)
    second = call_tool("find", workspace=str(root), limit=3, cursor=first.data["next_cursor"])
    # 検証
    assert first.is_error is False
    assert [item["id"] for item in first.data["items"]] == ["D-1", "D-2", "D-3"]
    assert first.data["total"] == 5
    assert isinstance(first.data["next_cursor"], str)
    assert "tags" in first.data["hint"]
    assert "kind" in first.data["hint"]
    assert "status" in first.data["hint"]
    assert "next_cursor" in first.data["hint"]
    assert second.is_error is False
    assert [item["id"] for item in second.data["items"]] == ["D-4", "D-5"]
    assert second.data["total"] == 5
    assert second.data["next_cursor"] is None


def test_normal_when_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
) -> None:
    """語彙にあるタグで 0 件になると、空の結果に外せる条件の案内を添える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["データ"]),
        settings={**valid_settings, "tags": [{"name": "データ"}, {"name": "保留"}]},
    )
    # 実行
    result = call_tool("find", workspace=str(root), kind="decision", tags=["保留"])
    # 検証
    assert result.is_error is False
    assert result.data["items"] == []
    assert result.data["total"] == 0
    assert result.data["next_cursor"] is None
    assert "kind" in result.data["hint"]
    assert "tags" in result.data["hint"]


def test_normal_when_detailed(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """detailed は対象・カテゴリー・フェーズ・属性・更新日時を足し、本文と案は返さない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item(
            "D-1",
            target="mindmap",
            category="データ構造",
            phase="要件",
            attrs={"担当": "自分"},
            options=[{"key": "A", "content": "案 A"}, {"key": "B", "content": "案 B"}],
        )
    )
    # 実行
    result = call_tool("find", workspace=str(root), response_format="detailed")
    # 検証
    assert result.is_error is False
    decision = result.data["items"][0]
    assert decision["target"] == "mindmap"
    assert decision["category"] == "データ構造"
    assert decision["phase"] == "要件"
    assert decision["attrs"] == {"担当": "自分"}
    assert "updated" in decision
    assert "options" not in decision
    assert "body" not in decision


def test_error_when_unknown_tag(
    make_workspace: MakeWorkspace, valid_settings: dict[str, Any], call_tool: CallTool
) -> None:
    """語彙に無いタグで探すと、近いタグの候補を添えたエラーで終わる（異常系）。"""
    # 準備
    root = make_workspace(settings={**valid_settings, "tags": [{"name": "データ"}, {"name": "画面"}]})
    # 実行
    result = call_tool("find", workspace=str(root), tags=["データー"])
    # 検証
    assert result.is_error is True
    assert "tags: データー（候補: データ）" in result.text


def test_error_when_cursor_mismatched(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """続きの値を作った条件と違う条件で渡すとエラーで終わる（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"), make_item("D-2"), make_item("D-3"), make_item("T-1")
    )
    first = call_tool("find", workspace=str(root), limit=2)
    # 実行
    result = call_tool(
        "find", workspace=str(root), kind="task", limit=2, cursor=first.data["next_cursor"]
    )
    # 検証
    assert result.is_error is True
    assert "cursor" in result.text
