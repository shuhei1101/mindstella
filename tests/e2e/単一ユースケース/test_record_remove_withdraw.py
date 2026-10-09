"""記録の削除と取り下げ（スキルが、やめた項目を取り下げ、誤って足した・重複した項目を消す）の E2E テスト。

MCP サーバーを立て、MCP のクライアントで `remove`・`update`・`pending`・`commit`・`check`・`add` を呼んで、結果とワークスペースの状態を確かめる。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from workspace_fixtures import RECORD_DIR, CallTool, MakeItem, MakeWorkspace, SnapshotTree

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from conftest import Replay

# 重複して足したメモのタイトル
DUPLICATE_TITLE = "重複したメモ"

# メモの中身（N-1 と N-2 は同じ中身を重ねて足した）
NOTE_CONTENT = "支出は月ごとに記録する"


def _note(title: str, body: str) -> dict[str, Any]:
    """本文を持つメモとして足す項目を作る。"""
    return {"title": title, "content": NOTE_CONTENT, "body_markdown": body}


def test_normal(
    make_workspace: MakeWorkspace,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """重複したメモを消し、消した項目をまとまりに残して、消した ID を振り直さない（正常系）。"""
    # 準備
    root = make_workspace()
    ws = {"workspace": str(root)}
    replay("add", **ws, kind="note", item=_note("メモ", "残す本文\n"))
    replay("add", **ws, kind="note", item=_note(DUPLICATE_TITLE, "消す本文\n"))
    replay("commit", **ws, summary="メモを足す")
    kept = read_yaml(root, "notes.yaml")["items"][0]
    # 実行
    removed = replay("remove", **ws, id="N-2")
    # 消した直後の記録の状態を控える（この後にメモを足すため、ここで読む）
    notes_after_remove = read_yaml(root, "notes.yaml")["items"]
    body_removed = not (root / RECORD_DIR / "docs" / "N-2.md").exists()
    pending = replay("pending", **ws)
    committed = replay("commit", **ws, summary="重複した N-2 を消す")
    # まとめた直後の記録の状態を控える（この後にメモを足すため、ここで読む）
    sets_after_commit = read_yaml(root, "changes.yaml")["sets"]
    pending_after_commit = replay("pending", **ws)
    added = replay("add", **ws, kind="note", item={"title": "次のメモ", "content": "中身"})
    checked = replay("check", **ws)
    # 検証
    # 消すツールが N-2 を返す
    assert removed["id"] == "N-2"
    # notes.yaml に N-2 が無く、N-1 は消す前のまま残る
    assert notes_after_remove == [kept]
    # .mindstella/docs/ に N-2 の本文が無い
    assert body_removed
    # pending が、消した項目として N-2 の ID・種類・消したときのタイトルを返す
    assert pending["removed"] == [{"id": "N-2", "kind": "note", "title": DUPLICATE_TITLE}]
    # commit の後、増えたまとまりが消した項目に N-2 を持ち、pending が空を返す
    assert committed["removed"] == [{"id": "N-2", "kind": "note", "title": DUPLICATE_TITLE}]
    assert [entry["id"] for entry in sets_after_commit[0]["removed"]] == ["N-2"]
    assert pending_after_commit == {"added": [], "changed": [], "removed": []}
    # 消した後に足したメモの ID が N-3 である
    assert added["id"] == "N-3"
    # check が問題を 0 件で返す
    assert checked == {"ok": True, "problems": []}


def test_normal_when_withdrawn(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """やめた調査は消さずに、取り下げの印と理由を書いて残す（正常系）。"""
    # 準備
    root = make_workspace(make_item("R-1"), make_item("D-1", related=["R-1"]))
    ws = {"workspace": str(root)}
    # 実行
    replay("update", **ws, id="R-1", item={"withdrawn": True, "reason": "調べる必要がなくなった"})
    pending = replay("pending", **ws)
    checked = replay("check", **ws)
    # 検証
    # research.yaml に R-1 が残り、取り下げの印と渡した理由を持つ
    research = read_yaml(root, "research.yaml")["items"][0]
    assert research["id"] == "R-1"
    assert research["withdrawn"] is True
    assert research["reason"] == "調べる必要がなくなった"
    # R-1 の変更履歴が、取り下げる前の値を 1 回分持つ
    assert len(research["history"]) == 1
    assert research["history"][0]["before"] == {"withdrawn": None, "reason": None}
    # D-1 の related が R-1 を指したままである
    assert read_yaml(root, "decisions.yaml")["items"][0]["related"] == ["R-1"]
    # pending が、変えた項目として R-1 を返す
    assert [entry["id"] for entry in pending["changed"]] == ["R-1"]
    # check が問題を 0 件で返す
    assert checked == {"ok": True, "problems": []}


def test_error_when_referenced(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """ほかの項目が指している項目は消さず、指している記録を示すエラーになる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("D-2", depends_on=["D-1"]))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("remove", workspace=str(root), id="D-1")
    # 検証
    # 消すツールがエラーを返し、本文に D-1 を指している D-2 とキー depends_on がある
    assert result.is_error is True
    assert "decisions.yaml: D-2: depends_on" in result.text
    # ワークスペースの全てのファイルの中身が、消すツールを呼ぶ前と同じである
    assert snapshot_tree(root) == before


def test_error_when_item_missing(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """存在しない ID は消さず、渡した ID を示すエラーになる（異常系）。"""
    # 準備
    root = make_workspace(make_item("N-1"))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("remove", workspace=str(root), id="N-9")
    # 検証
    # 消すツールがエラーを返し、本文に渡した ID がある
    assert result.is_error is True
    assert "N-9" in result.text
    # ワークスペースの全てのファイルの中身が、消すツールを呼ぶ前と同じである
    assert snapshot_tree(root) == before
