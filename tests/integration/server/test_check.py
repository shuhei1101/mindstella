"""check（ワークスペースの点検）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .fixture_types import (
    CallTool,
    MakeItem,
    MakeSubmission,
    MakeWorkspace,
    SnapshotTree,
    WriteSubmissions,
)
from .history_helpers import DECISION_ITEM, add_item, commit, update_item


def _problem_keys(problems: list[dict[str, Any]]) -> set[tuple[str, str, str | None, str | None]]:
    """問題から種類・ファイル・ID・キーの組を取り出し、並びを問わない集まりにする。"""
    return {(row["kind"], row["file"], row["id"], row["key"]) for row in problems}


def test_normal_when_clean(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """整ったワークスペースで問題 0 件を返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", body="D-1.md"),
        make_item("D-2", depends_on=["D-1"]),
        bodies={"D-1.md": "本文\n"},
    )
    # 実行
    result = call_tool("check", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data == {"ok": True, "problems": []}


def test_normal_when_problems_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """スキーマ違反・参照切れ・本文のずれを全て返す。問題があるときもツールのエラーにしない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", depends_on=["D-9"]),
        make_item("D-2", status="完了"),
        make_item("R-1", body="R-1.md"),
        bodies={"X-1.md": "どこからも指されない本文\n"},
    )
    write_submissions(root, make_submission("S-1", target="D-8"))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("check", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["ok"] is False
    assert _problem_keys(result.data["problems"]) == {
        ("broken_ref", "decisions.yaml", "D-1", "depends_on"),
        ("broken_ref", "submissions.yaml", "S-1", "target"),
        ("schema", "decisions.yaml", "D-2", "items[1].status"),
        ("missing_body", "research.yaml", "R-1", "items[0].body"),
        ("orphan_body", "docs/X-1.md", None, None),
    }
    assert "D-9" in result.text
    assert "D-8" in result.text
    assert snapshot_tree(root) == before


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("check", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_normal_when_history_stale(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """本文を手で書き換えて前の版を組み立てられない変更履歴を、問題として返す（正常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "decision", {**DECISION_ITEM, "body_markdown": "1 行目\n2 行目\n3 行目\n"})
    commit(call_tool, root, "足す")
    update_item(call_tool, root, "D-1", {"body_markdown": "1 行目\n書き換えた 2 行目\n3 行目\n"})
    (root / "docs" / "D-1.md").write_text("手で書いた A\n手で書いた B\n手で書いた C\n", encoding="utf-8")
    before = snapshot_tree(root)
    # 実行
    result = call_tool("check", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["ok"] is False
    assert ("stale_history", "decisions.yaml", "D-1", "history[0].body_diff") in _problem_keys(
        result.data["problems"]
    )
    assert snapshot_tree(root) == before


def test_normal_when_unknown_phase(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """項目の phase と goal.phase が設定の phases に無ければ unknown_phase を返す（正常系）。"""
    # 準備
    settings = {
        **valid_settings,
        "phases": ["目的", "要件"],
        "goal": {"phase": "結論", "summary": "まとめる", "deliverables": []},
    }
    root = make_workspace(make_item("D-1", phase="発散"), settings=settings)
    before = snapshot_tree(root)
    # 実行
    result = call_tool("check", workspace=str(root))
    # 検証
    assert result.is_error is False
    payload = result.data
    assert payload["ok"] is False
    unknown = {
        (row["file"], row["id"], row["key"], row["detail"])
        for row in payload["problems"]
        if row["kind"] == "unknown_phase"
    }
    assert unknown == {
        ("decisions.yaml", "D-1", "items[0].phase", "発散"),
        ("config.yaml", None, "goal.phase", "結論"),
    }
    assert snapshot_tree(root) == before
