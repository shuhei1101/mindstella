"""ワークスペースのクローズ（POST /workspaces/{id}/close）の結合テスト。"""

from __future__ import annotations

import threading
import time

from session_fixtures import SessionWorld, wait_until

# クローズの変更を Mock で遅らせる秒数（同時に届いた作成が鍵を待つ間）
PATCH_DELAY_SEC = 1.0


def _stopped(world: SessionWorld) -> str:
    """MindStella のセッションを起動して止めたワークスペースの ID を返す。"""
    workspace_id = str(world.create_workspace()["id"])
    status, body = world.create_session(workspace_id)
    assert status == 201, body
    assert world.api("DELETE", f"/workspaces/{workspace_id}/sessions/{body['session']}")[0] == 202
    wait_until(lambda: (world.read_session(workspace_id) or {}).get("status") == "stopped")
    wait_until(lambda: workspace_id not in world.sessions())
    return workspace_id


def test_normal(session_world: SessionWorld) -> None:
    """配信元の行を outside_read: false にする（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _stopped(world)
    world.pi.requests.clear()
    # 実行
    status, body = world.api("POST", f"/workspaces/{workspace_id}/close")
    # 検証
    assert (status, body) == (200, {"id": workspace_id, "closed": True})
    assert [request[2]["source"] for request in world.pi.changes()] == [{"outside_read": False}]
    assert (world.folder() / ".mindstella" / "config.yaml").exists()
    assert (world.state_root / "workspaces" / workspace_id / "launch.json").exists()


def test_error_when_session_running(session_world: SessionWorld) -> None:
    """MindStella のセッションがあれば 409 を返し、配信元の行を変えない（異常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = str(world.create_workspace()["id"])
    assert world.create_session(workspace_id)[0] == 201
    world.pi.requests.clear()
    # 実行
    status, body = world.api("POST", f"/workspaces/{workspace_id}/close")
    # 検証
    assert (status, body["stage"]) == (409, "session"), body
    assert world.pi.changes() == []


def test_error_when_create_during_close(session_world: SessionWorld) -> None:
    """クローズが先に終わり、同時に届いた作成はクローズ済みで断られる（異常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _stopped(world)
    world.pi.patch_delay_sec = PATCH_DELAY_SEC
    results: dict[str, tuple[int, dict[str, object]]] = {}

    def close() -> None:
        """クローズを送る。"""
        results["close"] = world.api("POST", f"/workspaces/{workspace_id}/close")

    # 実行
    closer = threading.Thread(target=close)
    closer.start()
    time.sleep(PATCH_DELAY_SEC / 2)
    results["create"] = world.create_session(workspace_id)
    closer.join()
    # 検証
    assert results["close"][0] == 200
    assert (results["create"][0], results["create"][1]["stage"]) == (409, "closed")
    assert world.sessions() == []
