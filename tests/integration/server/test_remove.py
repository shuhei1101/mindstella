"""remove（項目の削除）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any


from .fixture_types import (
    CallTool,
    LockDirs,
    MakeComment,
    MakeItem,
    MakeSubmission,
    MakeWorkspace,
    SnapshotTree,
    WriteComments,
    WriteSubmissions,
)
from .history_helpers import add_item, commit, read_changes, read_items
from workspace_fixtures import RECORD_DIR

# 消すメモのタイトル
DUPLICATE_TITLE = "重複したメモ"

# 取り込んだ日時
TAKEN_AT = "2026-10-02T08:00:00+00:00"


def _note(title: str, *, body: str | None = None) -> dict[str, Any]:
    """メモとして足す項目を作る（body があれば本文つき）。"""
    item: dict[str, Any] = {"title": title, "content": f"{title}の中身"}
    if body is not None:
        item["body_markdown"] = body
    return item


def test_normal(make_workspace: MakeWorkspace, call_tool: CallTool) -> None:
    """まとめた後の重複したメモを消し、まだまとめていない変更に消した項目を残す（正常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "note", _note("残すメモ", body="残す本文\n"))
    add_item(call_tool, root, "note", _note(DUPLICATE_TITLE, body="消す本文\n"))
    commit(call_tool, root, "足す")
    kept = read_items(root, "notes.yaml")[0]
    # 実行
    result = call_tool("remove", workspace=str(root), id="N-2")
    # 検証
    assert result.is_error is False
    assert result.data == {
        "id": "N-2",
        "kind": "note",
        "title": DUPLICATE_TITLE,
        "file": ".mindstella/notes.yaml",
        "body_removed": True,
    }
    assert read_items(root, "notes.yaml") == [kept]
    assert not (root / RECORD_DIR / "docs" / "N-2.md").exists()
    changes = read_changes(root)
    assert len(changes["pending"]["removed"]) == 1
    removed = changes["pending"]["removed"][0]
    assert removed["id"] == "N-2"
    assert removed["kind"] == "note"
    assert removed["title"] == DUPLICATE_TITLE
    assert removed["seq"] == changes["last_seq"]
    assert changes["pending"]["added"] == []
    assert changes["pending"]["changed"] == []


def test_normal_when_added_since_last_commit(
    make_workspace: MakeWorkspace, call_tool: CallTool
) -> None:
    """最後のまとまりより後に足した項目を消すと、足した項目から除き、消した項目に記録する（正常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "note", _note("あとで消すメモ"))
    # 実行
    result = call_tool("remove", workspace=str(root), id="N-1")
    # 検証
    assert result.is_error is False
    assert "N-1" not in [item["id"] for item in read_items(root, "notes.yaml")]
    pending = read_changes(root)["pending"]
    assert pending["added"] == []
    assert pending["changed"] == []
    assert len(pending["removed"]) == 1
    assert pending["removed"][0]["id"] == "N-1"
    assert "added_seq" in pending["removed"][0]
    # 消した後に足したメモは、消した ID を振り直さない
    assert add_item(call_tool, root, "note", _note("次のメモ")) == "N-2"


def test_normal_when_only_taken_submission_refers(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
    call_tool: CallTool,
) -> None:
    """取り込み済みの送信が向けた項目は消せる（正常系）。"""
    # 準備
    root = make_workspace(make_item("N-1"))
    write_submissions(root, make_submission("S-1", target="N-1", taken=TAKEN_AT))
    submissions_before = (root / RECORD_DIR / "submissions.yaml").read_bytes()
    # 実行
    result = call_tool("remove", workspace=str(root), id="N-1")
    # 検証
    assert result.is_error is False
    assert "N-1" not in [item["id"] for item in read_items(root, "notes.yaml")]
    assert (root / RECORD_DIR / "submissions.yaml").read_bytes() == submissions_before


def test_error_when_referenced(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """ほかの項目が指している項目は消さず、指している記録を返す（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("D-2", depends_on=["D-1"]),
        make_item("T-1", **{"for": ["D-1"]}),
    )
    before = snapshot_tree(root)
    # 実行
    result = call_tool("remove", workspace=str(root), id="D-1")
    # 検証
    assert result.is_error is True
    lines = result.text.splitlines()
    assert lines[0] == "エラー: D-1 はほかの記録が指しているため消せません"
    assert "decisions.yaml: D-2: depends_on" in lines
    assert "tasks.yaml: T-1: for" in lines
    assert snapshot_tree(root) == before


def test_error_when_referenced_by_deliverable_and_comment(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """ゴールの納品物の資料と、レビュー中のコメントが向けた項目は消さない（異常系）。"""
    # 準備
    settings = {
        **valid_settings,
        "goal": {**valid_settings["goal"], "deliverables": [{"title": "仕様", "doc": "A-1"}]},
    }
    root = make_workspace(
        make_item("A-1"), settings=settings, bodies={"A-1.md": "本文\n"}
    )
    write_comments(root, make_comment("C-1", target="A-1"))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("remove", workspace=str(root), id="A-1")
    # 検証
    assert result.is_error is True
    assert "config.yaml: goal.deliverables[0].doc" in result.text
    assert "comments.yaml: C-1: target" in result.text
    assert snapshot_tree(root) == before


def test_error_when_id_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """存在しない ID は消さず、渡した ID を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("N-1"))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("remove", workspace=str(root), id="N-9")
    # 検証
    assert result.is_error is True
    assert "N-9" in result.text
    assert snapshot_tree(root) == before


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("remove", workspace=str(root), id="N-1")
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは何も消さず、エラーの行を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("N-1", body="N-1.md"), bodies={"N-1.md": "本文\n"})
    before = snapshot_tree(root)
    lock_dirs(root / RECORD_DIR, root / RECORD_DIR / "docs")
    # 実行
    result = call_tool("remove", workspace=str(root), id="N-1")
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert "Traceback" not in result.text
    assert snapshot_tree(root) == before
    assert (root / RECORD_DIR / "docs" / "N-1.md").exists()
