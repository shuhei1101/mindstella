"""update（項目の更新）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .fixture_types import (
    CallTool,
    LockDirs,
    MakeItem,
    MakeLegacyWorkspace,
    MakeWorkspace,
    SnapshotTree,
)


def _read_decisions(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの検討事項の並びを読む。"""
    return yaml.safe_load((root / "decisions.yaml").read_text(encoding="utf-8"))["items"]


def test_normal(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool) -> None:
    """検討事項の答えと状態を直し、不要になったキーを消す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", lead="キーを種類ごとに分けるか", weight="大"))
    item = {"answer": "種類ごとに分ける", "status": "決定済み", "weight": None}
    # 実行
    result = call_tool("update", workspace=str(root), id="D-1", item=item)
    # 検証
    assert result.is_error is False
    payload = result.data
    assert payload["id"] == "D-1"
    assert payload["file"] == "decisions.yaml"
    assert payload["changed"] == ["answer", "status", "weight"]
    updated_item = _read_decisions(root)[0]
    updated = updated_item.pop("updated")
    assert updated > "2026-10-01T00:00:00+00:00"
    assert updated_item == {
        "id": "D-1",
        "title": "D-1の題",
        "status": "決定済み",
        "lead": "キーを種類ごとに分けるか",
        "answer": "種類ごとに分ける",
        "created": "2026-10-01T00:00:00+00:00",
    }


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """mindmap.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("update", workspace=str(root), id="D-1", item={"answer": "a"})
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_id_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """存在しない ID は直さず、渡した ID を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("update", workspace=str(root), id="D-9", item={"answer": "a"})
    # 検証
    assert result.is_error is True
    assert "D-9" in result.text
    assert snapshot_tree(root) == before


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """スクリプトが付けるキー created を渡すと直さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    item = {"created": "2000-01-01T00:00:00+00:00"}
    # 実行
    result = call_tool("update", workspace=str(root), id="D-1", item=item)
    # 検証
    assert result.is_error is True
    assert "created" in result.text
    assert snapshot_tree(root) == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは何も書き換えず、エラーの行を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    lock_dirs(root)
    # 実行
    result = call_tool("update", workspace=str(root), id="D-1", item={"answer": "a"})
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert "Traceback" not in result.text
    assert snapshot_tree(root) == before


def test_error_when_legacy_format(
    make_item: MakeItem,
    make_legacy_workspace: MakeLegacyWorkspace,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """資料の done が残るワークスペースでは何も書かず、/mindstella:upgrade を案内して終わる（異常系）。"""
    # 準備
    root = make_legacy_workspace(make_item("D-1"), legacy_docs={"A-1": True})
    before = snapshot_tree(root)
    # 実行
    result = call_tool("update", workspace=str(root), id="D-1", item={"answer": "種類ごとに分ける"})
    # 検証
    assert result.is_error is True
    lines = result.text.splitlines()
    assert any(line.startswith("docs.yaml: items[0]") for line in lines)
    assert lines[-1] == "ヒント: 前の版の形式の記録は /mindstella:upgrade で今の形式に移せます"
    assert snapshot_tree(root) == before
