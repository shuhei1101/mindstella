"""画面からの MindStella のセッションの再起動（POST /w/{workspace}/api/session/restart）の結合テスト。"""

from __future__ import annotations

from session_fixtures import SessionWorld, wait_until

# 起動し直しが終わるまで待つ秒数
RESTARTED_WAIT_SEC = 30.0

# 状態に書く MindStella のセッションの ID（落ちていることにする）
CRASHED_SESSION_ID = "S-0123456789ab"

# 落ちたときの理由
RESTART_ERROR = "account: 空いたアカウントがありません"

# 別のオリジン
REJECTED_ORIGIN = "http://attacker.example"


def _crashed(world: SessionWorld) -> str:
    """ワークスペースを作り、失敗して落ちた MindStella のセッションの状態を書いて、ワークスペースの ID を返す。"""
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(
        workspace_id,
        session=CRASHED_SESSION_ID,
        status="crashed",
        claude_config_dir=str(world.root / "account"),
        last_error=RESTART_ERROR,
    )
    return workspace_id


def test_normal(session_world: SessionWorld) -> None:
    """失敗して落ちた MindStella のセッションの再起動を受け付ける（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _crashed(world)
    # 実行
    status, body = world.api("POST", f"/w/{workspace_id}/api/session/restart")
    after = wait_until(
        lambda: (
            (current := world.api("GET", f"/w/{workspace_id}/api/session")[1])
            and current["status"] == "running"
            and current
        ),
        timeout=RESTARTED_WAIT_SEC,
    )
    # 検証
    assert (status, body["status"]) == (202, "restarting"), body
    assert after["last_error"] is None


def test_error_when_restarting(session_world: SessionWorld) -> None:
    """再起動の途中なら二重に依頼しない（異常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id, session=CRASHED_SESSION_ID, status="restarting")
    # 実行
    status, body = world.api("POST", f"/w/{workspace_id}/api/session/restart")
    # 検証
    assert (status, body.get("stage")) == (409, "restarting"), body


def test_error_when_origin_rejected(session_world: SessionWorld) -> None:
    """別のオリジンからの依頼を断る（異常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _crashed(world)
    # 実行
    status, _body = world.api(
        "POST", f"/w/{workspace_id}/api/session/restart", origin=REJECTED_ORIGIN
    )
    # 検証
    assert status == 403
    assert world.balancer_calls() == []
