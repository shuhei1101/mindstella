"""edit_option（案の書き換え）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from .fixture_types import CallTool, LockDirs, MakeItem, MakeWorkspace, SnapshotTree
from .history_helpers import add_item, commit, read_changes, read_items
from workspace_fixtures import RECORD_DIR

# 案 A（利点・欠点を持つ）と案 B
OPTION_A: dict[str, Any] = {
    "key": "A",
    "content": "種類ごとに分ける",
    "pros": "探しやすい",
    "cons": "ファイルが増える",
}
OPTION_B: dict[str, Any] = {"key": "B", "content": "1 つにまとめる"}


@pytest.fixture
def decision_workspace(make_workspace: MakeWorkspace, call_tool: CallTool):
    """案の並びを渡すと、その案を持つ検討事項 D-1 を足して commit したワークスペースを作る関数を返す。"""

    def _make(options: list[dict[str, Any]], **item: Any) -> Path:
        """D-1 を足して commit したワークスペース（保持する回数は既定の 5）を作る。"""
        root = make_workspace()
        add_item(
            call_tool,
            root,
            "decision",
            {"title": "D-1の題", "status": "未決定", "options": options, **item},
        )
        commit(call_tool, root, "足す")
        return root

    return _make


def test_normal_when_added(decision_workspace, call_tool: CallTool) -> None:
    """案を並びの末尾に足し、変更履歴を積む（正常系）。"""
    # 準備
    root = decision_workspace([OPTION_A])
    option = {"content": "1 つにまとめる", "pros": "ファイルが少ない"}
    # 実行
    result = call_tool(
        "edit_option", workspace=str(root), id="D-1", action="add", key="B", option=option
    )
    # 検証
    assert result.is_error is False
    added = {"key": "B", **option}
    assert result.data == {
        "id": "D-1",
        "file": ".mindstella/decisions.yaml",
        "options": [OPTION_A, added],
        "changed": True,
    }
    item = read_items(root, "decisions.yaml")[0]
    assert item["options"] == [OPTION_A, added]
    assert len(item["history"]) == 1
    assert item["history"][0]["before"] == {"options": [OPTION_A]}
    changes = read_changes(root)
    assert changes["pending"]["changed"] == ["D-1"]
    assert item["seq"] == changes["last_seq"]


def test_normal_when_updated(decision_workspace, call_tool: CallTool) -> None:
    """指した案の渡したキーだけを置き換え、ほかの案はそのまま残す（正常系）。"""
    # 準備
    root = decision_workspace([OPTION_A, OPTION_B])
    # 実行
    result = call_tool(
        "edit_option",
        workspace=str(root),
        id="D-1",
        action="update",
        key="A",
        option={"pros": "見つけやすい", "cons": None},
    )
    # 検証
    assert result.is_error is False
    updated = {"key": "A", "content": "種類ごとに分ける", "pros": "見つけやすい"}
    assert result.data is not None
    assert result.data["options"] == [updated, OPTION_B]
    assert result.data["changed"] is True
    item = read_items(root, "decisions.yaml")[0]
    assert item["options"] == [updated, OPTION_B]
    assert len(item["history"]) == 1
    assert item["history"][0]["before"] == {"options": [OPTION_A, OPTION_B]}


def test_normal_when_removed(decision_workspace, call_tool: CallTool) -> None:
    """採用していない案を消す（正常系）。"""
    # 準備
    adopted_a = {**OPTION_A, "adopted": True}
    option_c = {"key": "C", "content": "ファイルを分けない"}
    root = decision_workspace(
        [adopted_a, OPTION_B, option_c], status="決定済み", answer="A に決めた"
    )
    # 実行
    result = call_tool(
        "edit_option", workspace=str(root), id="D-1", action="remove", key="B"
    )
    # 検証
    assert result.is_error is False
    item = read_items(root, "decisions.yaml")[0]
    assert item["options"] == [adopted_a, option_c]
    assert item["status"] == "決定済み"
    assert item["answer"] == "A に決めた"


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("edit_option", workspace=str(root), id="D-1", action="remove", key="A")
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_id_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """存在しない検討事項を指すと、何も書かずに渡した ID を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("edit_option", workspace=str(root), id="D-9", action="remove", key="A")
    # 検証
    assert result.is_error is True
    assert "D-9" in result.text
    assert snapshot_tree(root) == before


def test_error_when_key_exists(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """既にある記号の案は足さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=[OPTION_A, OPTION_B]))
    before = snapshot_tree(root)
    # 実行
    result = call_tool(
        "edit_option",
        workspace=str(root),
        id="D-1",
        action="add",
        key="B",
        option={"content": "別の案"},
    )
    # 検証
    assert result.is_error is True
    assert "D-1" in result.text
    assert "B" in result.text
    assert snapshot_tree(root) == before


def test_error_when_key_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """無い記号の案は直さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=[OPTION_A]))
    before = snapshot_tree(root)
    # 実行
    result = call_tool(
        "edit_option",
        workspace=str(root),
        id="D-1",
        action="update",
        key="Z",
        option={"content": "直す"},
    )
    # 検証
    assert result.is_error is True
    assert "D-1" in result.text
    assert "Z" in result.text
    assert snapshot_tree(root) == before


def test_error_when_adopted_option_removed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """採用している案は消さず、採用を先に移すよう示す（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", options=[{**OPTION_A, "adopted": True}, OPTION_B])
    )
    before = snapshot_tree(root)
    # 実行
    result = call_tool("edit_option", workspace=str(root), id="D-1", action="remove", key="A")
    # 検証
    assert result.is_error is True
    assert "D-1" in result.text
    assert "A" in result.text
    assert "adopt" in result.text
    assert snapshot_tree(root) == before


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """案の中身がスキーマに合わないと、何も書かない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=[OPTION_A]))
    before = snapshot_tree(root)
    # 実行
    result = call_tool(
        "edit_option",
        workspace=str(root),
        id="D-1",
        action="add",
        key="B",
        option={"content": 1},
    )
    # 検証
    assert result.is_error is True
    assert any(
        line.startswith("decisions.yaml") and "content" in line for line in result.text.splitlines()
    )
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
    root = make_workspace(make_item("D-1", options=[OPTION_A]))
    before = snapshot_tree(root)
    lock_dirs(root / RECORD_DIR)
    # 実行
    result = call_tool(
        "edit_option",
        workspace=str(root),
        id="D-1",
        action="add",
        key="B",
        option={"content": "1 つにまとめる"},
    )
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert "Traceback" not in result.text
    assert snapshot_tree(root) == before


def test_error_when_argument_invalid(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """採用の印を option で渡すと、何も書かずに引数の誤りを返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=[OPTION_A, OPTION_B]))
    before = snapshot_tree(root)
    # 実行
    result = call_tool(
        "edit_option",
        workspace=str(root),
        id="D-1",
        action="update",
        key="B",
        option={"adopted": True},
    )
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: 引数の誤り: option:")
    assert "adopted" in result.text
    assert snapshot_tree(root) == before
