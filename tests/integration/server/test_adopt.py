"""adopt（採用する案の切り替え）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from .fixture_types import CallTool, LockDirs, MakeItem, MakeWorkspace, SnapshotTree
from .history_helpers import add_item, commit, read_changes
from workspace_fixtures import RECORD_DIR


@pytest.fixture
def two_options() -> list[dict[str, Any]]:
    """案 A（採用）と案 B を持つ検討事項の案を返す。"""
    return [
        {"key": "A", "content": "種類ごとに分ける", "adopted": True},
        {"key": "B", "content": "1 つにまとめる", "adopted": False},
    ]


def test_normal(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    two_options: list[dict[str, Any]],
) -> None:
    """案 A から案 B へ採用を切り替え、変更履歴を 1 回分積む（正常系）。"""
    # 準備
    root = make_workspace()
    add_item(
        call_tool,
        root,
        "decision",
        {
            "title": "D-1の題",
            "status": "決定済み",
            "answer": "案 A に決めた",
            "options": two_options,
        },
    )
    commit(call_tool, root, "足す")
    # 実行
    result = call_tool("adopt", workspace=str(root), id="D-1", key="B")
    # 検証
    assert result.is_error is False
    assert result.data == {
        "id": "D-1",
        "adopted": "B",
        "previous": "A",
        "status": "決定済み",
        "previous_status": "決定済み",
    }
    adopted = yaml.safe_load((root / RECORD_DIR / "decisions.yaml").read_text(encoding="utf-8"))[
        "items"
    ][0]
    assert adopted["options"] == [
        {"key": "A", "content": "種類ごとに分ける", "adopted": False},
        {"key": "B", "content": "1 つにまとめる", "adopted": True},
    ]
    assert adopted["status"] == "決定済み"
    assert adopted["answer"] == "案 A に決めた"
    assert len(adopted["history"]) == 1
    assert adopted["history"][0]["before"]["options"] == two_options
    assert "status" not in adopted["history"][0]["before"]
    assert read_changes(root)["pending"]["changed"] == ["D-1"]


def test_normal_when_undecided_adopted(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """未決定と要見直しの検討事項の案を採用すると、どちらも決定済みになる（正常系）。"""
    # 準備
    option_a = {"key": "A", "content": "種類ごとに分ける"}
    option_b = {"key": "B", "content": "1 つにまとめる", "recommended": True}
    root = make_workspace(
        make_item("D-1", status="未決定", answer="仮の答え", options=[option_a, option_b]),
        make_item("D-2", status="要見直し", options=[{**option_a, "adopted": True}, option_b]),
    )
    commit(call_tool, root, "足す")
    # 実行
    first = call_tool("adopt", workspace=str(root), id="D-1", key="B")
    second = call_tool("adopt", workspace=str(root), id="D-2", key="A")
    # 検証
    assert first.is_error is False
    assert first.data == {
        "id": "D-1",
        "adopted": "B",
        "previous": None,
        "status": "決定済み",
        "previous_status": "未決定",
    }
    assert second.is_error is False
    assert second.data == {
        "id": "D-2",
        "adopted": "A",
        "previous": "A",
        "status": "決定済み",
        "previous_status": "要見直し",
    }
    decided, reviewed = (
        yaml.safe_load((root / RECORD_DIR / "decisions.yaml").read_text(encoding="utf-8"))["items"]
    )
    # 未決定だった D-1: 案 B だけが採用で、推奨の印と答えは残り、変更履歴は状態と案の並びを持つ
    assert decided["status"] == "決定済み"
    assert decided["options"] == [
        {**option_a, "adopted": False},
        {**option_b, "adopted": True},
    ]
    assert decided["answer"] == "仮の答え"
    assert decided["history"][0]["before"] == {
        "status": "未決定",
        "options": [option_a, option_b],
    }
    # 要見直しだった D-2: 案 A が採用のまま、変更履歴は状態だけを持つ
    assert reviewed["status"] == "決定済み"
    assert [option.get("adopted") for option in reviewed["options"]] == [True, False]
    assert reviewed["history"][0]["before"] == {"status": "要見直し"}


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("adopt", workspace=str(root), id="D-1", key="B")
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_id_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """存在しない検討事項は切り替えない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("adopt", workspace=str(root), id="D-9", key="A")
    # 検証
    assert result.is_error is True
    assert "D-9" in result.text
    assert snapshot_tree(root) == before


def test_error_when_option_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    two_options: list[dict[str, Any]],
) -> None:
    """検討事項が持たない記号は切り替えず、持っている記号を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=two_options))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("adopt", workspace=str(root), id="D-1", key="Z")
    # 検証
    assert result.is_error is True
    assert "Z" in result.text
    assert "A" in result.text
    assert "B" in result.text
    assert snapshot_tree(root) == before


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    two_options: list[dict[str, Any]],
) -> None:
    """手で崩した YAML が残っていると切り替えず、合わない箇所を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=two_options), make_item("D-2", status="完了"))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("adopt", workspace=str(root), id="D-1", key="B")
    # 検証
    assert result.is_error is True
    assert "decisions.yaml: items[1].status:" in result.text
    assert snapshot_tree(root) == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
    two_options: list[dict[str, Any]],
) -> None:
    """書き込めないワークスペースでは切り替えず、エラーの行を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=two_options))
    before = snapshot_tree(root)
    lock_dirs(root / RECORD_DIR)
    # 実行
    result = call_tool("adopt", workspace=str(root), id="D-1", key="B")
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert "Traceback" not in result.text
    assert snapshot_tree(root) == before
