"""status（再開時の状況）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

from workspace_fixtures import ADOPTED_OPTIONS

from .fixture_types import CallTool, MakeItem, MakeWorkspace, SnapshotTree


def test_normal(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool) -> None:
    """要見直し・進行中・再開可能・決定待ち・そのほかの保留・次の候補を分けて返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", title="見直しの問い", status="要見直し"),
        make_item("T-1", title="進めている作業", status="進行中"),
        make_item("D-2", title="再開できる保留", status="保留", depends_on=["D-3"]),
        make_item("D-3", title="決まった問い", status="決定済み", options=ADOPTED_OPTIONS),
        make_item("D-4", title="決定待ちの保留", status="保留", depends_on=["D-5"]),
        make_item("D-5", title="次に決める問い"),
        make_item("D-6", title="予算待ち", status="保留", reason="予算が決まったら"),
    )
    # 実行
    result = call_tool("status", workspace=str(root))
    # 検証
    assert result.is_error is False
    payload = result.data
    assert payload["needs_review"] == [{"id": "D-1", "title": "見直しの問い"}]
    assert payload["in_progress"] == [{"id": "T-1", "title": "進めている作業"}]
    assert payload["resumable"] == [{"id": "D-2", "title": "再開できる保留"}]
    assert payload["waiting"] == [
        {"id": "D-4", "title": "決定待ちの保留", "waiting_for": ["D-5"]},
    ]
    assert payload["on_hold"] == [
        {"id": "D-6", "title": "予算待ち", "reason": "予算が決まったら"},
    ]
    assert len(payload["next"]) == 1
    assert payload["next"][0]["id"] == "D-5"


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("status", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_old_settings_file(
    tmp_path: Path, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """mindmap.yaml だけがあるフォルダは、移し替えを案内するエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "old-workspace"
    root.mkdir()
    (root / "mindmap.yaml").write_text("field: システム開発\n", encoding="utf-8")
    (root / "decisions.yaml").write_text("items: []\n", encoding="utf-8")
    before = snapshot_tree(root)
    # 実行（migrate 以外のツールの代表として status を呼ぶ）
    result = call_tool("status", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text
    assert "/mindstella:upgrade" in result.text
    assert snapshot_tree(root) == before
