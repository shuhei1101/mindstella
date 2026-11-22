"""MindStella のセッションの一覧（GET /workspaces/{id}/sessions）の結合テスト。"""

from __future__ import annotations

from session_fixtures import SessionWorld


def test_normal(session_world: SessionWorld) -> None:
    """起動中の MindStella のセッションを返す（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = str(world.create_workspace()["id"])
    status, created = world.create_session(workspace_id)
    assert status == 201, created
    # 実行
    status, body = world.api("GET", f"/workspaces/{workspace_id}/sessions")
    # 検証
    assert status == 200, body
    assert len(body["sessions"]) == 1
    entry = body["sessions"][0]
    assert (entry["id"], entry["status"], entry["responding"]) == (
        created["session"],
        "running",
        False,
    )
    assert body["close_pending"] is False


def test_normal_when_crashed(session_world: SessionWorld) -> None:
    """状態が running でもペインが無ければ crashed を返し、状態は書き換えない（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id)
    # 同じ tmux のサーバーにほかのセッションがある（無いペインを指した display-message が終了コード 0 で空の出力を返す条件）
    other = world.tmux("new-session", "-d", "-s", "other", "sleep", "600")
    assert other.returncode == 0, other.stderr
    # 実行
    status, body = world.api("GET", f"/workspaces/{workspace_id}/sessions")
    # 検証
    assert status == 200, body
    assert body["sessions"][0]["status"] == "crashed"
    session = world.read_session(workspace_id)
    assert session is not None
    assert session["status"] == "running"


def test_normal_when_never_created(session_world: SessionWorld) -> None:
    """一度も作っていなければ sessions が空の並び（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = str(world.create_workspace()["id"])
    # 実行
    status, body = world.api("GET", f"/workspaces/{workspace_id}/sessions")
    # 検証
    assert (status, body["sessions"]) == (200, [])
