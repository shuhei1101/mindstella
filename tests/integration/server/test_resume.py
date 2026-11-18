"""再開の状況（POST /_admin/sessions/{session}/resume）の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from record_write_helpers import write_items
from session_fixtures import SessionWorld
from workspace_fixtures import TEST_SESSION_ID

from .fixture_types import MakePost, MakeThread, SnapshotTree, WriteThreads
from .history_helpers import read_changes

# 状態に無い MindStella のセッションの ID
UNKNOWN_SESSION_ID = "S-ffffffffffff"

# 前回参照した時点より前に足す項目（要見直しの D-1・進行中の T-1・未決定の D-2）
ITEMS = [
    ("decision", {"title": "見直す問い", "status": "要見直し", "options": [{"key": "A", "content": "案 A"}]}),
    ("task", {"title": "進めている作業", "kind": "作業", "status": "進行中"}),
    ("decision", {"title": "まだ決めない問い", "status": "未決定", "options": [{"key": "A", "content": "案 A"}]}),
]


def _start(world: SessionWorld) -> tuple[Path, Path]:
    """ワークスペースを作り、MindStella のセッションを状態に書いて、フォルダと状態のフォルダを返す。"""
    world.start()
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id, session=TEST_SESSION_ID)
    return world.folder(), world.session_file(workspace_id).parent


def _resume(world: SessionWorld, source: str, session_id: str = TEST_SESSION_ID) -> tuple[int, dict[str, Any]]:
    """再開の状況を求める。"""
    return world.api("POST", f"/_admin/sessions/{session_id}/resume", {"source": source})


def test_normal(
    session_world: SessionWorld,
    make_thread: MakeThread,
    make_post: MakePost,
    write_threads: WriteThreads,
) -> None:
    """再開のとき、前回参照した後の変更と要見直し・進行中・取り込み待ちを返し、前回参照した時点は進めない（正常系）。"""
    # 準備
    world = session_world
    root, state = _start(world)
    server = world.servers[0]
    write_items(server.call, str(root), add=ITEMS)
    read_seq = read_changes(root)["last_seq"]
    (state / "read_point.json").write_text(json.dumps({"read_seq": read_seq}), encoding="utf-8")
    write_items(server.call, str(root), update={"D-1": {"title": "書き換えた問い"}})
    write_threads(root, make_thread("TH-1", make_post("TH-1-1")))
    # 実行
    status, body = _resume(world, "compact")
    _again_status, again = _resume(world, "compact")
    # 検証
    assert status == 200
    assert (body["trigger"], body["awaiting_threads"]) == ("resume", 1)
    assert body["changed"] == [{"id": "D-1", "kind": "decision", "title": "書き換えた問い", "updated_by": "ai"}]
    assert body["needs_review"] == [{"id": "D-1", "title": "書き換えた問い"}]
    assert body["in_progress"] == [{"id": "T-1", "title": "進めている作業"}]
    # 次の候補を返さず、未決定の D-2 を並べない
    assert "next" not in body
    assert "D-2" not in json.dumps(body, ensure_ascii=False)
    # 前回参照した時点は進めない
    assert body["until_seq"] == read_changes(root)["last_seq"]
    assert json.loads((state / "read_point.json").read_text(encoding="utf-8")) == {"read_seq": read_seq}
    assert again["changed"] == body["changed"]
    # 注入文
    context = body["context"]
    assert "再開しました。取り込み待ちのコメントのスレッドは 1 件です。" in context
    assert "- D-1 書き換えた問い" in context
    assert "- T-1 進めている作業" in context
    assert "mindstella/startup" in context
    assert "/mindstella:" not in context


def test_normal_when_startup(session_world: SessionWorld) -> None:
    """前回参照した時点が無いときは変更を返さず、今の通し番号を until_seq で返す（正常系）。"""
    # 準備
    world = session_world
    root, state = _start(world)
    write_items(world.servers[0].call, str(root), add=ITEMS[:1])
    # 実行
    status, body = _resume(world, "startup")
    # 検証
    assert status == 200
    assert body["trigger"] == "startup"
    assert (body["changed"], body["removed"]) == ([], [])
    assert body["until_seq"] == read_changes(root)["last_seq"]
    assert not (state / "read_point.json").exists()
    assert "起動しました。" in body["context"]


def test_error_when_unknown_session(session_world: SessionWorld, snapshot_tree: SnapshotTree) -> None:
    """状態に無い session には 404 を返し、何も書かない（異常系）。"""
    # 準備
    world = session_world
    _start(world)
    before = snapshot_tree(world.state_root)
    # 実行
    status, _body = _resume(world, "compact", session_id=UNKNOWN_SESSION_ID)
    # 検証
    assert status == 404
    assert snapshot_tree(world.state_root) == before
