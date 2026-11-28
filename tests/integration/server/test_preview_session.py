"""画面の MindStella のセッションの状態（GET /w/{workspace}/api/session）の結合テスト。"""

from __future__ import annotations

from session_fixtures import SessionWorld

from .fixture_types import MakePost, MakeThread, WriteThreads

# 再起動に失敗したことにする理由
RESTART_ERROR = "account: 空いたアカウントがありません"

# 受けないホスト名
REJECTED_HOST = "attacker.example"


def _session_path(workspace_id: str) -> str:
    """画面の MindStella のセッションの状態の経路。"""
    return f"/w/{workspace_id}/api/session"


def test_normal(session_world: SessionWorld) -> None:
    """起動中の MindStella のセッションの状態を返却する（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = str(world.create_workspace()["id"])
    status, created = world.create_session(workspace_id)
    assert status == 201, created
    # 実行
    status, body = world.api("GET", _session_path(workspace_id))
    # 検証
    assert status == 200, body
    assert body == {"status": "running", "last_error": None, "waiting": 0, "warnings": []}


def test_normal_when_restart_failed(
    session_world: SessionWorld, make_post: MakePost, make_thread: MakeThread, write_threads: WriteThreads
) -> None:
    """落ちた状態と失敗の理由と、取り込み待ちの書き込みの数を返却する（正常系）。"""
    # 準備（取り込み待ちの利用者の書き込みを 2 件持つ）
    world = session_world
    world.start()
    workspace_id = str(world.create_workspace()["id"])
    write_threads(
        world.folder(),
        make_thread("TH-1", make_post("TH-1-1")),
        make_thread("TH-2", make_post("TH-2-1")),
    )
    world.write_session(workspace_id, status="crashed", last_error=RESTART_ERROR)
    # 実行
    status, body = world.api("GET", _session_path(workspace_id))
    # 検証
    assert status == 200, body
    assert (body["status"], body["last_error"], body["waiting"]) == ("crashed", RESTART_ERROR, 2)


def test_normal_when_launch_record_missing(session_world: SessionWorld) -> None:
    """launch.json が無ければ launch_record_missing を返却する（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = str(world.create_workspace()["id"])
    status, created = world.create_session(workspace_id)
    assert status == 201, created
    (world.state_root / "workspaces" / workspace_id / "launch.json").unlink()
    # 実行
    status, body = world.api("GET", _session_path(workspace_id))
    # 検証
    assert status == 200, body
    assert body["warnings"] == ["launch_record_missing"]


def test_error_when_host_rejected(session_world: SessionWorld) -> None:
    """受けないホストの要求を断る（異常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = str(world.create_workspace()["id"])
    # 実行
    status, _body = world.api("GET", _session_path(workspace_id), host=f"{REJECTED_HOST}:{world.port}")
    # 検証
    assert status == 403
