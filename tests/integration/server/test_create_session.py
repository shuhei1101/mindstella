"""MindStella のセッションの作成（POST /workspaces/{id}/sessions）の結合テスト。"""

from __future__ import annotations

import time

from session_fixtures import SessionWorld, wait_until

# 進め方の文書
FLOW = {"source": "aituber", "doc": "flow-script"}

# 最初の入力
FIRST_INPUT = "[mindstella] MindStella のセッションを起動しました"

# 準備を待つ上限（テストで短くする）
READY_TIMEOUT_SEC = 3


def _workspace(world: SessionWorld, **body: object) -> str:
    """ワークスペースを作り、ID を返す。"""
    return str(world.create_workspace(**body)["id"])


def _with_options(world: SessionWorld) -> str:
    """mcp_config・plugin_dirs・flow を記録したワークスペースを作る。"""
    plugin = world.root / "plugins" / "aituber"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text('{"name": "aituber"}', encoding="utf-8")
    world.pi.rows["aituber"] = {
        "id": "aituber",
        "config": ["/repo/aituber/project-index.yaml"],
        "scope": {"read": [f"{world.allowed}/**"]},
        "outsideRead": True,
    }
    world.pi.docs["aituber"] = [{"id": "flow-script", "path": "docs/flow/flow-script.yaml"}]
    return _workspace(
        world,
        flow=FLOW,
        mcp_config={"mcpServers": {"aituber": {"command": "aituber-mcp"}}},
        plugin_dirs=[str(plugin)],
    )


def _no_session_left(world: SessionWorld, workspace_id: str) -> bool:
    """tmux のセッションと session.json が残っていないか。"""
    return workspace_id not in world.sessions() and world.read_session(workspace_id) is None


def test_normal(session_world: SessionWorld) -> None:
    """claude-balancer exec で起動し、フックの登録の後に ID・ペイン・URL を返す（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _with_options(world)
    # 実行
    status, body = world.create_session(workspace_id)
    # 検証
    assert status == 201, body
    assert body["session"].startswith("S-")
    assert body["pane"] == f"{workspace_id}:0.0"
    assert world.balancer_calls()[0][:4] == ["exec", "--client", "mindstella", "--"]
    record = world.claude_records()[0]
    for option in ("--mcp-config", "--plugin-dir", "--append-system-prompt"):
        assert option in record["args"]
    assert record["env"]["MINDSTELLA_SESSION"] == body["session"]
    assert record["env"]["MINDSTELLA_WORKSPACE"] == workspace_id
    assert record["env"]["MINDSTELLA_FLOW"] == "aituber#flow-script"
    session = world.read_session(workspace_id)
    assert session is not None
    assert session["status"] == "running"
    assert session["claude_session_id"]
    assert session["pane"]
    assert session["pid"] == record["pid"]
    wait_until(lambda: FIRST_INPUT in world.inputs())


def test_normal_when_no_balancer(session_world: SessionWorld) -> None:
    """claude を直接起動し、claude_config_dir を CLAUDE_CONFIG_DIR に入れる（正常系）。"""
    # 準備
    world = session_world
    world.remove_balancer()
    world.start()
    workspace_id = _workspace(world)
    config_dir = str(world.root / "claude-sub1")
    # 実行
    status, body = world.create_session(workspace_id, claude_config_dir=config_dir)
    # 検証
    assert status == 201, body
    assert world.claude_records()[0]["env"]["CLAUDE_CONFIG_DIR"] == config_dir


def test_error_when_session_exists(session_world: SessionWorld) -> None:
    """起動中の MindStella のセッションがあれば 409 と起動中の ID・ペインを返す（異常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _workspace(world)
    _status, first = world.create_session(workspace_id)
    # 実行
    status, body = world.create_session(workspace_id)
    # 検証
    assert (status, body["stage"]) == (409, "exists"), body
    assert (body["session"], body["pane"]) == (first["session"], first["pane"])
    assert len(world.balancer_calls()) == 1


def test_error_when_workspace_closed(session_world: SessionWorld) -> None:
    """クローズしたワークスペースは 409（異常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _workspace(world)
    assert world.api("POST", f"/workspaces/{workspace_id}/close")[0] == 200
    # 実行
    status, body = world.create_session(workspace_id)
    # 検証
    assert (status, body["stage"]) == (409, "closed"), body
    assert world.sessions() == []


def test_error_when_no_account(session_world: SessionWorld) -> None:
    """claude-balancer が借りられずに 125 で終われば、ペインを閉じて 503（異常系）。"""
    # 準備
    world = session_world
    world.set_balancer_exit(125)
    world.start({"MINDSTELLA_SESSION_READY_TIMEOUT": "20"})
    workspace_id = _workspace(world)
    started = time.monotonic()
    # 実行
    status, body = world.create_session(workspace_id)
    # 検証
    assert (status, body["stage"]) == (503, "account"), body
    assert "借りられるアカウントがありません" in body["detail"]
    assert time.monotonic() - started < 20
    assert _no_session_left(world, workspace_id)


def test_error_when_launch_exits(session_world: SessionWorld) -> None:
    """ペインのコマンドが 125 以外で先に終われば 502（異常系）。"""
    # 準備
    world = session_world
    world.set_claude_mode("exit:1")
    world.start()
    workspace_id = _workspace(world)
    # 実行
    status, body = world.create_session(workspace_id)
    # 検証
    assert (status, body["stage"]) == (502, "launch"), body
    assert "終了コード 1" in body["detail"]
    assert _no_session_left(world, workspace_id)


def test_error_when_session_not_ready(session_world: SessionWorld) -> None:
    """上限までにフックが登録しなければ、止めてペインを閉じて 504（異常系）。"""
    # 準備
    world = session_world
    world.set_claude_mode("no_hook")
    world.start({"MINDSTELLA_SESSION_READY_TIMEOUT": str(READY_TIMEOUT_SEC)})
    workspace_id = _workspace(world)
    # 実行
    status, body = world.create_session(workspace_id)
    # 検証
    assert (status, body["stage"]) == (504, "ready"), body
    assert _no_session_left(world, workspace_id)
    wait_until(lambda: world.alive_claude_pids() == [], timeout=5)
