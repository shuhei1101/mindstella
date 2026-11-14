"""MindStella のセッションの停止（DELETE /workspaces/{id}/sessions/{session}）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

import yaml
from session_fixtures import SessionWorld, wait_until
from workspace_fixtures import McpServer

# 待つ上限（テストで短くする）
STOP_WAIT_SEC = 2

# 停止して状態に記録されるまで待つ秒数
STOPPED_WAIT_SEC = 5


def _running(world: SessionWorld, *, responding: bool = False) -> tuple[str, str]:
    """ワークスペースを作って MindStella のセッションを起動し、ワークスペースの ID と MindStella のセッションの ID を返す。

    responding なら、偽の Claude Code の UserPromptSubmit が状態に入るまで待つ。
    """
    workspace_id = str(world.create_workspace()["id"])
    status, body = world.create_session(workspace_id)
    assert status == 201, body
    if responding:
        wait_until(lambda: (world.read_session(workspace_id) or {}).get("responding"))
    return workspace_id, str(body["session"])


def _add_pending(server: McpServer, folder: Path) -> None:
    """まだまとめていない変更を作る。"""
    result = server.call(
        "add",
        workspace=str(folder),
        kind="note",
        item={"title": "予算の上限", "content": "月 3 万円まで"},
    )
    assert result.is_error is False, result.text


def _summaries(folder: Path) -> list[str]:
    """changes.yaml のまとまりの説明。"""
    changes = yaml.safe_load((folder / ".mindstella" / "changes.yaml").read_text(encoding="utf-8"))
    return [str(entry["summary"]) for entry in changes["sets"]]


def _status(world: SessionWorld, workspace_id: str) -> str | None:
    """session.json の status。"""
    session = world.read_session(workspace_id)
    return None if session is None else str(session["status"])


def test_normal(session_world: SessionWorld) -> None:
    """すぐに 202 を返し、応答の途中でなければ止めて停止済みにする（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id, session_id = _running(world)
    # 実行
    status, body = world.api("DELETE", f"/workspaces/{workspace_id}/sessions/{session_id}")
    accepted = world.read_session(workspace_id)
    # 検証
    assert (status, body["status"]) == (202, "stopping"), body
    assert accepted is not None
    assert accepted["close_pending"] is True
    wait_until(lambda: _status(world, workspace_id) == "stopped", timeout=STOPPED_WAIT_SEC)
    wait_until(lambda: workspace_id not in world.sessions(), timeout=STOPPED_WAIT_SEC)


def test_normal_when_waiting_last_write(session_world: SessionWorld) -> None:
    """応答の途中なら Stop のフックの後に /exit を貼って止める（正常系）。"""
    # 準備
    world = session_world
    world.set_claude_mode("responding:2")
    world.start()
    workspace_id, session_id = _running(world, responding=True)
    # 実行
    status, _body = world.api("DELETE", f"/workspaces/{workspace_id}/sessions/{session_id}")
    # 検証
    assert status == 202
    exited = wait_until(lambda: world.noted("exit"), timeout=15)
    stopped = world.noted("stop")
    assert stopped is not None
    assert exited > stopped


def test_normal_when_session_crashed(session_world: SessionWorld) -> None:
    """落ちていれば止める工程を飛ばし、落ちていたことを添えて commit して 200 を返す（正常系）。"""
    # 準備
    world = session_world
    server = world.start()
    workspace_id = str(world.create_workspace()["id"])
    _add_pending(server, world.folder())
    world.write_session(workspace_id, session="S-0000000000aa")
    # 実行
    status, body = world.api("DELETE", f"/workspaces/{workspace_id}/sessions/S-0000000000aa")
    # 検証
    assert (status, body["status"]) == (200, "stopped"), body
    assert any("落ちていた" in summary for summary in _summaries(world.folder()))


def test_normal_when_forced(session_world: SessionWorld) -> None:
    """強制なら応答の途中でも止め、強制で止めたことを添えて commit する（正常系）。"""
    # 準備
    world = session_world
    world.set_claude_mode("responding")
    server = world.start()
    workspace_id, session_id = _running(world, responding=True)
    _add_pending(server, world.folder())
    # 実行
    status, _body = world.api(
        "DELETE", f"/workspaces/{workspace_id}/sessions/{session_id}?force=true"
    )
    # 検証
    assert status == 202
    wait_until(lambda: _status(world, workspace_id) == "stopped", timeout=STOPPED_WAIT_SEC + 10)
    assert world.noted("stop") is None
    wait_until(lambda: world.alive_claude_pids() == [], timeout=STOPPED_WAIT_SEC)
    assert any("強制" in summary for summary in _summaries(world.folder()))


def test_error_when_wait_exceeds_limit(session_world: SessionWorld) -> None:
    """待つ上限を過ぎたら止めずに pending_write を真にする（異常系）。"""
    # 準備
    world = session_world
    world.set_claude_mode("responding")
    world.start({"MINDSTELLA_STOP_WAIT_TIMEOUT": str(STOP_WAIT_SEC)})
    workspace_id, session_id = _running(world, responding=True)
    # 実行
    status, _body = world.api("DELETE", f"/workspaces/{workspace_id}/sessions/{session_id}")
    # 検証
    assert status == 202
    session = wait_until(
        lambda: (
            (current := world.read_session(workspace_id)) and current["pending_write"] and current
        ),
        timeout=STOP_WAIT_SEC + 10,
    )
    assert session["status"] == "running"
    assert world.alive_claude_pids() != []
