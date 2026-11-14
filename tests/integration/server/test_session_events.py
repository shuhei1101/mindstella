"""MindStella のセッションの出来事の受け取り（POST /_admin/sessions/{session}/events）の結合テスト。"""

from __future__ import annotations

from session_fixtures import SessionWorld

# 状態に書く MindStella のセッションの ID
SESSION_ID = "S-0123456789ab"


def _prepare(world: SessionWorld, **values: object) -> str:
    """ワークスペースを作り、session.json を書いて、ワークスペースの ID を返す。"""
    world.start()
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id, session=SESSION_ID, **values)
    return workspace_id


def _send(
    world: SessionWorld, body: dict[str, object], session_id: str = SESSION_ID
) -> tuple[int, dict[str, object]]:
    """出来事を送る。"""
    return world.api("POST", f"/_admin/sessions/{session_id}/events", body)


def test_normal(session_world: SessionWorld) -> None:
    """SessionStart で claude_session_id とペインを記録する（正常系）。"""
    # 準備
    world = session_world
    workspace_id = _prepare(world, claude_session_id=None)
    # 実行
    status, body = _send(
        world,
        {
            "event": "session_start",
            "claude_session_id": "c-9",
            "source": "startup",
            "pane": "%7",
            "pid": 4242,
            "pid_started_at": "99",
        },
    )
    # 検証
    assert (status, body) == (200, {"recorded": True})
    session = world.read_session(workspace_id)
    assert session is not None
    assert (session["claude_session_id"], session["pane"], session["pid"]) == ("c-9", "%7", 4242)


def test_normal_when_responding(session_world: SessionWorld) -> None:
    """prompt_submit で responding が真、stop_failure で偽（正常系）。"""
    # 準備
    world = session_world
    workspace_id = _prepare(world)
    # 実行
    _send(world, {"event": "prompt_submit", "claude_session_id": "c-1"})
    during = world.read_session(workspace_id)
    _send(world, {"event": "stop_failure", "claude_session_id": "c-1"})
    after = world.read_session(workspace_id)
    # 検証
    assert during is not None
    assert after is not None
    assert (during["responding"], after["responding"]) == (True, False)


def test_normal_when_cleared(session_world: SessionWorld) -> None:
    """SessionEnd の reason が clear なら停止済みにしない（正常系）。"""
    # 準備
    world = session_world
    workspace_id = _prepare(world)
    # 実行
    status, _body = _send(
        world, {"event": "session_end", "claude_session_id": "c-1", "reason": "clear"}
    )
    # 検証
    assert status == 200
    session = world.read_session(workspace_id)
    assert session is not None
    assert session["status"] == "running"


def test_normal_when_unknown_session(session_world: SessionWorld) -> None:
    """状態に無い MindStella のセッションには記録せず 200 を返す（正常系）。"""
    # 準備
    world = session_world
    workspace_id = _prepare(world)
    before = world.session_file(workspace_id).read_bytes()
    # 実行
    status, body = _send(
        world, {"event": "prompt_submit", "claude_session_id": "c-1"}, session_id="S-ffffffffffff"
    )
    # 検証
    assert (status, body) == (200, {"recorded": False})
    assert world.session_file(workspace_id).read_bytes() == before
