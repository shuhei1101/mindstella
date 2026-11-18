"""前回参照した時点の更新（POST /_admin/sessions/{session}/read_point）の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from record_write_helpers import write_items
from session_fixtures import SessionWorld
from workspace_fixtures import TEST_SESSION_ID

from .fixture_types import SnapshotTree
from .history_helpers import read_changes

# 状態に無い MindStella のセッションの ID
UNKNOWN_SESSION_ID = "S-ffffffffffff"

# 1 回の書き換えで足す 5 件の項目（通し番号を 5 まで進める）
FIVE_NOTES = [("note", {"title": f"メモ {number}", "content": "中身"}) for number in range(1, 6)]

# まだ知らせていない移し替えの報告
MIGRATION_REPORT = {
    "not_carried": [{"item": "D-1", "key": "phase", "value": "要件"}],
    "provisional": [{"file": "config.yaml", "key": "summary", "value": "家計簿"}],
}


def _prepare(world: SessionWorld, read_seq: int, *, migration: bool = False) -> tuple[Path, Path]:
    """通し番号が 5 のワークスペースと MindStella のセッションを作り、前回参照した時点を read_seq にして、フォルダと状態のフォルダを返す。"""
    server = world.start()
    workspace_id = str(world.create_workspace()["id"])
    root = world.folder()
    write_items(server.call, str(root), add=FIVE_NOTES)
    assert read_changes(root)["last_seq"] == 5
    world.write_session(workspace_id, session=TEST_SESSION_ID)
    state = world.session_file(workspace_id).parent
    (state / "read_point.json").write_text(json.dumps({"read_seq": read_seq}), encoding="utf-8")
    # 移し替えの報告を持つ: 状態のフォルダに置く
    if migration:
        (state / "migration.json").write_text(json.dumps(MIGRATION_REPORT), encoding="utf-8")
    return root, state


def _post(world: SessionWorld, body: dict[str, Any], session_id: str = TEST_SESSION_ID) -> tuple[int, dict[str, Any]]:
    """前回参照した時点の更新を送る。"""
    return world.api("POST", f"/_admin/sessions/{session_id}/read_point", body)


def _read_seq(state: Path) -> int:
    """状態のフォルダの `read_point.json` の `read_seq`。"""
    return json.loads((state / "read_point.json").read_text(encoding="utf-8"))["read_seq"]


def test_normal(session_world: SessionWorld) -> None:
    """until_seq まで前回参照した時点を進め、移し替えの報告を消す（正常系）。"""
    # 準備
    _root, state = _prepare(session_world, 3, migration=True)
    # 実行
    status, body = _post(session_world, {"until_seq": 5})
    # 検証
    assert (status, body) == (200, {"read_seq": 5})
    assert _read_seq(state) == 5
    assert not (state / "migration.json").exists()


def test_normal_when_already_ahead(session_world: SessionWorld) -> None:
    """今の read_seq が until_seq 以上なら書き換えない（正常系）。"""
    # 準備
    _root, state = _prepare(session_world, 5)
    # 実行
    status, body = _post(session_world, {"until_seq": 3})
    # 検証
    assert (status, body) == (200, {"read_seq": 5})
    assert _read_seq(state) == 5


def test_error_when_beyond_last_seq(session_world: SessionWorld) -> None:
    """until_seq が last_seq より大きいと 400 を返し、何も書かない（異常系）。"""
    # 準備
    _root, state = _prepare(session_world, 3)
    # 実行
    status, _body = _post(session_world, {"until_seq": 9})
    # 検証
    assert status == 400
    assert _read_seq(state) == 3


def test_error_when_unknown_session(session_world: SessionWorld, snapshot_tree: SnapshotTree) -> None:
    """状態に無い session には 404 を返し、何も書かない（異常系）。"""
    # 準備
    _prepare(session_world, 3)
    before = snapshot_tree(session_world.state_root)
    # 実行
    status, _body = _post(session_world, {"until_seq": 5}, session_id=UNKNOWN_SESSION_ID)
    # 検証
    assert status == 404
    assert snapshot_tree(session_world.state_root) == before
