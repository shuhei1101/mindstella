"""ワークスペースの開き直し（POST /workspaces/{id}/reopen）の結合テスト。"""

from __future__ import annotations

from session_fixtures import SessionWorld
from workspace_fixtures import RECORD_DIR, MakePost, MakeThread, WriteThreads


def _closed(world: SessionWorld) -> str:
    """クローズしたワークスペース（close_pending が真）の ID を返す。"""
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id, status="stopped", pane=None)
    status, body = world.api("POST", f"/workspaces/{workspace_id}/close")
    assert status == 200, body
    return workspace_id


def test_normal(
    session_world: SessionWorld,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """クローズしたワークスペースの配信元の行を戻し、クローズ待ちを解く（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _closed(world)
    write_threads(world.folder(), make_thread("TH-1", make_post("TH-1-1")))
    launch = (world.state_root / "workspaces" / workspace_id / "launch.json").read_bytes()
    config = (world.folder() / RECORD_DIR / "config.yaml").read_bytes()
    world.pi.requests.clear()
    # 実行
    status, body = world.api("POST", f"/workspaces/{workspace_id}/reopen")
    # 検証
    assert (status, body) == (200, {"id": workspace_id, "reopened": True, "closed": False})
    assert [request[2]["source"] for request in world.pi.changes()] == [{"outside_read": True}]
    assert (world.read_session(workspace_id) or {})["close_pending"] is False
    assert world.sessions() == []
    assert world.api("GET", f"/workspaces/{workspace_id}")[1]["awaiting_user_posts"] == 1
    assert (world.state_root / "workspaces" / workspace_id / "launch.json").read_bytes() == launch
    assert (world.folder() / RECORD_DIR / "config.yaml").read_bytes() == config


def test_normal_when_not_closed(session_world: SessionWorld) -> None:
    """配信元の行を変えず、クローズ待ちだけを解く（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id, status="stopped", pane=None, close_pending=True)
    world.pi.requests.clear()
    # 実行
    status, body = world.api("POST", f"/workspaces/{workspace_id}/reopen")
    # 検証
    assert (status, body) == (200, {"id": workspace_id, "reopened": False, "closed": False})
    assert world.pi.changes() == []
    assert (world.read_session(workspace_id) or {})["close_pending"] is False


def test_error_when_workspace_missing(session_world: SessionWorld) -> None:
    """ID の一覧に無いワークスペースは 404 を返し、何も変えない（異常系）。"""
    # 準備
    world = session_world
    world.start()
    world.pi.requests.clear()
    # 実行
    status, body = world.api("POST", "/workspaces/mindstella-x-000000/reopen")
    # 検証
    assert (status, body["stage"]) == (404, "workspace"), body
    assert world.pi.changes() == []


def test_error_when_source_failed(session_world: SessionWorld) -> None:
    """project-index が失敗したら 502 を返し、クローズ待ちを解かない（異常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _closed(world)
    world.pi.patch_status = 500
    # 実行
    status, body = world.api("POST", f"/workspaces/{workspace_id}/reopen")
    # 検証
    assert (status, body["stage"]) == (502, "source"), body
    assert (world.read_session(workspace_id) or {})["close_pending"] is True
