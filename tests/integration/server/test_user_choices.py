"""user_choices（利用者が案を選んだ検討事項の一覧）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

from .fixture_types import (
    CallTool,
    MakeComment,
    MakeItem,
    MakeWorkspace,
    SnapshotTree,
    WriteComments,
)

# 案 A・B を持つ未決定の検討事項の案
OPTIONS = [{"key": "A", "content": "種類ごとに分ける"}, {"key": "B", "content": "1 つにまとめる"}]


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """送信した選択だけを送信した日時の古い順に返却し、送信前の案の選択は返却しない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", options=OPTIONS, user_choice={"key": "B", "at": "2026-11-01T10:00:00+00:00"}),
        make_item(
            "D-2",
            options=OPTIONS,
            user_choice={"key": "A", "note": "費用を優先する", "at": "2026-11-01T09:00:00+00:00"},
        ),
        make_item("D-3", options=OPTIONS),
    )
    # D-3 への送信前の案の選択（本文を持たない）
    pending = make_comment("C-1", target="D-3", choice={"key": "A"})
    del pending["body"]
    write_comments(root, pending)
    before = snapshot_tree(root)
    # 実行
    result = call_tool("user_choices", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    items = result.data["items"]
    assert [item["id"] for item in items] == ["D-2", "D-1"]
    assert (items[0]["key"], items[0]["content"], items[0]["note"]) == (
        "A",
        "種類ごとに分ける",
        "費用を優先する",
    )
    assert items[1]["note"] is None
    assert snapshot_tree(root) == before


def test_normal_when_no_choices(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """利用者が案を選んだ検討事項が無ければ空の配列を返却する（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    # 実行
    result = call_tool("user_choices", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data == {"items": []}


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すとツールのエラーにする（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("user_choices", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """利用者の選択が案に無い記号を指すとツールのエラーにし、合わない箇所を返却する（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", options=OPTIONS, user_choice={"key": "Z", "at": "2026-11-01T10:00:00+00:00"})
    )
    # 実行
    result = call_tool("user_choices", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert "decisions.yaml: items[0].user_choice:" in result.text
