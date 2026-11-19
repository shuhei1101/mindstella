"""ワークスペースの削除（DELETE /workspaces/{id}）の結合テスト。"""

from __future__ import annotations

import yaml

from session_fixtures import SessionWorld
from workspace_fixtures import RECORD_DIR


def _closed(world: SessionWorld) -> str:
    """クローズしたワークスペースの ID を返す。状態のフォルダに session.json・launch.json・snapshot/・read_point.json を持つ。"""
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id, status="stopped", pane=None)
    folder = world.state_root / "workspaces" / workspace_id
    (folder / "snapshot").mkdir(exist_ok=True)
    (folder / "read_point.json").write_text('{"read_seq": 1}', encoding="utf-8")
    status, body = world.api("POST", f"/workspaces/{workspace_id}/close")
    assert status == 200, body
    return workspace_id


def _ids(world: SessionWorld) -> list[str]:
    """状態のフォルダの ID の一覧を読む。"""
    loaded = yaml.safe_load((world.state_root / "workspaces.yaml").read_text(encoding="utf-8"))
    return list(loaded.get("ids") or [])


def test_normal(session_world: SessionWorld) -> None:
    """配信元の行・状態のフォルダの記録・ID の一覧の行を削除する（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _closed(world)
    config = (world.folder() / RECORD_DIR / "config.yaml").read_bytes()
    world.pi.requests.clear()
    # 実行
    status, body = world.api("DELETE", f"/workspaces/{workspace_id}")
    # 検証
    assert (status, body) == (200, {"id": workspace_id, "deleted": True})
    assert [request[0] for request in world.pi.changes()] == ["DELETE"]
    assert workspace_id not in world.pi.rows
    assert not (world.state_root / "workspaces" / workspace_id).exists()
    assert workspace_id not in _ids(world)
    assert (world.folder() / RECORD_DIR / "config.yaml").read_bytes() == config
    assert world.api("GET", f"/workspaces/{workspace_id}")[0] == 404


def test_normal_when_source_row_missing(session_world: SessionWorld) -> None:
    """前の削除で行だけ削除されたワークスペースの残りを削除する（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _closed(world)
    del world.pi.rows[workspace_id]
    world.pi.save()
    world.pi.requests.clear()
    # 実行
    status, body = world.api("DELETE", f"/workspaces/{workspace_id}")
    # 検証
    assert (status, body) == (200, {"id": workspace_id, "deleted": True})
    assert world.pi.changes() == []
    assert not (world.state_root / "workspaces" / workspace_id).exists()
    assert workspace_id not in _ids(world)


def test_error_when_workspace_missing(session_world: SessionWorld) -> None:
    """ID の一覧に無いワークスペースは 404 を返し、何も変えない（異常系）。"""
    # 準備
    world = session_world
    world.start()
    world.pi.requests.clear()
    # 実行
    status, body = world.api("DELETE", "/workspaces/mindstella-x-000000")
    # 検証
    assert (status, body["stage"]) == (404, "workspace"), body
    assert world.pi.requests == []


def test_error_when_not_closed(session_world: SessionWorld) -> None:
    """クローズしていなければ 409 を返し、何も変えない（異常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id, status="stopped", pane=None)
    world.pi.requests.clear()
    # 実行
    status, body = world.api("DELETE", f"/workspaces/{workspace_id}")
    # 検証
    assert (status, body["stage"]) == (409, "not_closed"), body
    assert world.pi.changes() == []
    assert (world.state_root / "workspaces" / workspace_id / "session.json").exists()
    assert workspace_id in _ids(world)


def test_error_when_source_failed(session_world: SessionWorld) -> None:
    """project-index が失敗したら 502 を返し、状態のフォルダを変えない（異常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _closed(world)
    world.pi.delete_status = 500
    # 実行
    status, body = world.api("DELETE", f"/workspaces/{workspace_id}")
    # 検証
    assert (status, body["stage"]) == (502, "source"), body
    assert (world.state_root / "workspaces" / workspace_id / "session.json").exists()
    assert workspace_id in _ids(world)
