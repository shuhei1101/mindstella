"""検討事項の案の編集（スキルが案を記号で指して 1 つずつ足す・直す・消す）の E2E テスト。

MCP サーバーを立て、MCP のクライアントで案を書き換えるツールを呼んで、ワークスペースの状態を確かめる。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from workspace_fixtures import CallTool, MakeItem, MakeWorkspace, SnapshotTree

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import Replay

# 案 A（利点・欠点を持つ）と案 B
OPTION_A: dict[str, Any] = {
    "key": "A",
    "content": "種類ごとに分ける",
    "pros": "探しやすい",
    "cons": "ファイルが増える",
}
OPTION_B: dict[str, Any] = {"key": "B", "content": "1 つにまとめる"}


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    replay: Replay,
    call_tool: CallTool,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """案 B を足し、案 A の pros を直し、案 C を足して消す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", lead="キーを分けるかを決める", options=[OPTION_A]),
    )
    ws = {"workspace": str(root), "id": "D-1"}
    before = read_yaml(root, "decisions.yaml")["items"][0]
    option_b = {"content": "1 つにまとめる", "pros": "ファイルが少ない"}
    # 実行
    replay("edit_option", **ws, action="add", key="B", option=option_b)
    replay("edit_option", **ws, action="update", key="A", option={"pros": "見つけやすい"})
    replay("edit_option", **ws, action="add", key="C", option={"content": "ファイルを分けない"})
    replay("edit_option", **ws, action="remove", key="C")
    checked = call_tool("check", workspace=str(root))
    # 検証
    item = read_yaml(root, "decisions.yaml")["items"][0]
    # D-1 の案が A・B の 2 件で、この並びである
    assert [option["key"] for option in item["options"]] == ["A", "B"]
    # 案 A の pros が直した値で、content・cons は元の値である
    assert item["options"][0] == {**OPTION_A, "pros": "見つけやすい"}
    # 案 B が足した中身を持ち、adopted が真ではない
    assert item["options"][1] == {"key": "B", **option_b}
    # D-1 の状態・タイトル・問いの説明が元の値である
    for key in ("status", "title", "lead"):
        assert item[key] == before[key]
    # D-1 の変更履歴が 4 回分で、どの回も options の前の値を持つ
    assert len(item["history"]) == 4
    assert all("options" in entry["before"] for entry in item["history"])
    # D-1 の updated_by が ai である
    assert item["updated_by"] == "ai"
    # ワークスペースの全ての YAML がスキーマに合う
    assert checked.data["problems"] == []


def test_error_when_key_exists(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """同じ記号の案を足すと、記号が重なるエラーになり、何も書き換えない（異常系）。"""
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
    # 案を書き換えるツールがエラーを返し、本文に D-1 と記号 B がある
    assert result.is_error is True
    assert "D-1" in result.text
    assert "B" in result.text
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before


def test_error_when_key_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """無い記号の案を直すと、記号の案が無いエラーになり、何も書き換えない（異常系）。"""
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
    # 案を書き換えるツールがエラーを返し、本文に D-1 と記号 Z がある
    assert result.is_error is True
    assert "D-1" in result.text
    assert "Z" in result.text
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before


def test_error_when_adopted_option_removed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    read_yaml: Callable[[Path, str], Any],
    snapshot_tree: SnapshotTree,
) -> None:
    """採用している案を消すと、先に採用を切り替えるよう示すエラーになり、何も書き換えない（異常系）。"""
    # 準備
    options = [{**OPTION_A, "adopted": True}, OPTION_B]
    root = make_workspace(make_item("D-1", status="決定済み", answer="A に決めた", options=options))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("edit_option", workspace=str(root), id="D-1", action="remove", key="A")
    # 検証
    # 案を書き換えるツールがエラーを返し、本文に D-1 と記号 A と、採用している案であることがある
    assert result.is_error is True
    assert "D-1" in result.text
    assert "A" in result.text
    assert "採用している案" in result.text
    # D-1 の案が A・B のままで、A が採用されたままである
    assert read_yaml(root, "decisions.yaml")["items"][0]["options"] == options
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before


def test_normal_when_recommendation_moved(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """案 B に推奨の印を立て、案 A の印を外す（正常系）。"""
    # 準備
    options = [{**OPTION_A, "recommended": True}, OPTION_B]
    root = make_workspace(make_item("D-1", status="未決定", options=options))
    # 実行
    replay(
        "edit_option",
        workspace=str(root),
        id="D-1",
        action="update",
        key="B",
        option={"recommended": True},
    )
    # 検証
    item = read_yaml(root, "decisions.yaml")["items"][0]
    # D-1 の案 B だけが推奨の印を持ち、案 A は持たない
    assert item["options"][1]["recommended"] is True
    assert "recommended" not in item["options"][0]
    # 案 A・B の content と並びが元のままである
    assert [(option["key"], option["content"]) for option in item["options"]] == [
        ("A", OPTION_A["content"]),
        ("B", OPTION_B["content"]),
    ]
    # D-1 の状態が未決定のままで、どの案も採用でない
    assert item["status"] == "未決定"
    assert all("adopted" not in option for option in item["options"])
    # D-1 の変更履歴が 1 回分で、options の前の値（案 A の推奨の印）を持つ
    assert len(item["history"]) == 1
    assert item["history"][0]["before"]["options"] == options


def test_error_when_last_option_removed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """未決定の検討事項の最後の案を消すと、案を 1 つ以上残すよう示すエラーになり、何も書き換えない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", status="未決定", options=[OPTION_A]))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("edit_option", workspace=str(root), id="D-1", action="remove", key="A")
    # 検証
    # 案を書き換えるツールがエラーを返し、本文に D-1 と記号 A と、案を 1 つ以上残す旨がある
    assert result.is_error is True
    assert "D-1" in result.text
    assert "A" in result.text
    assert "1 つ以上" in result.text
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before
