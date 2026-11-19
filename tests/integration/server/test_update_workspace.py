"""ワークスペースの設定の書き換え（PATCH /workspaces/{id}）の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from session_fixtures import SessionWorld
from workspace_fixtures import RECORD_DIR

# 作成のときの進め方の文書
FLOW = {"source": "aituber", "doc": "flow-script"}

# 書き換える進め方の文書
NEW_FLOW = {"source": "aituber", "doc": "flow-talk"}

# 作成のときの追加の MCP の定義
MCP_CONFIG = {"mcpServers": {"aituber": {"command": "aituber-mcp"}}}

# 書き換える追加の MCP の定義
NEW_MCP_CONFIG = {"mcpServers": {"aituber": {"command": "aituber-mcp", "args": ["--talk"]}}}


def _serve_flow(world: SessionWorld) -> None:
    """進め方の文書の配信元と 2 件の文書を、許可するフォルダが読める scope で Mock に置く。"""
    world.pi.rows["aituber"] = {
        "id": "aituber",
        "config": ["/repo/aituber/project-index.yaml"],
        "scope": {"read": [str(world.allowed), f"{world.allowed}/**"]},
        "outsideRead": True,
    }
    world.pi.docs["aituber"] = [
        {"id": "flow-script", "path": "docs/flow/flow-script.yaml"},
        {"id": "flow-talk", "path": "docs/flow/flow-talk.yaml"},
    ]


def _plugin_dir(world: SessionWorld, name: str) -> Path:
    """追加のプラグインのフォルダを作る。"""
    folder = world.root / "plugins" / name
    (folder / ".claude-plugin").mkdir(parents=True)
    (folder / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": name}), encoding="utf-8"
    )
    return folder


def _with_options(world: SessionWorld) -> str:
    """進め方の文書・追加の MCP・プラグインを指定してワークスペースを作り、ID を返す。"""
    _serve_flow(world)
    plugin = _plugin_dir(world, "aituber")
    created = world.create_workspace(flow=FLOW, mcp_config=MCP_CONFIG, plugin_dirs=[str(plugin)])
    return str(created["id"])


def _config_path(world: SessionWorld) -> Path:
    """ワークスペースの設定のパス。"""
    return world.folder() / RECORD_DIR / "config.yaml"


def _launch_path(world: SessionWorld, workspace_id: str) -> Path:
    """状態のフォルダの launch.json のパス。"""
    return world.state_root / "workspaces" / workspace_id / "launch.json"


def _read_config(world: SessionWorld) -> dict[str, object]:
    """ワークスペースの設定を読む。"""
    return yaml.safe_load(_config_path(world).read_text(encoding="utf-8"))


def _read_launch(world: SessionWorld, workspace_id: str) -> dict[str, object]:
    """launch.json を読む。"""
    return json.loads(_launch_path(world, workspace_id).read_text(encoding="utf-8"))


def _without_flow(config: dict[str, object]) -> dict[str, object]:
    """設定から `flow` を除いたコピーを返す。"""
    return {key: value for key, value in config.items() if key != "flow"}


def _state_files(world: SessionWorld) -> list[tuple[str, bytes]]:
    """状態のフォルダの全てのファイルのパスと中身。"""
    return sorted(
        (str(path), path.read_bytes()) for path in world.state_root.rglob("*") if path.is_file()
    )


def _doc_requests(world: SessionWorld) -> list[str]:
    """Mock が受けた文書の一覧・取得の依頼のパス。"""
    return [request[1] for request in world.pi.requests if request[1].startswith("/sources/")]


def test_normal(session_world: SessionWorld) -> None:
    """設定のキー・進め方の文書・追加の MCP・プラグインを書き換え、起動中の MindStella のセッションは止めない（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _with_options(world)
    status, created = world.create_session(workspace_id)
    assert status == 201, created
    new_plugin = _plugin_dir(world, "aituber-talk")
    config_before = _read_config(world)
    session_before = world.read_session(workspace_id)
    # 実行
    status, body = world.api(
        "PATCH",
        f"/workspaces/{workspace_id}",
        {
            "settings": {"summary": "配信の台本を作る"},
            "flow": NEW_FLOW,
            "mcp_config": NEW_MCP_CONFIG,
            "plugin_dirs": [str(new_plugin)],
        },
    )
    # 検証
    assert (status, body) == (
        200,
        {"id": workspace_id, "changed": ["summary", "flow", "mcp_config", "plugin_dirs"]},
    )
    assert _read_config(world) == {**config_before, "summary": "配信の台本を作る", "flow": NEW_FLOW}
    assert _read_launch(world, workspace_id) == {
        "mcp_config": NEW_MCP_CONFIG,
        "plugin_dirs": [str(new_plugin)],
    }
    assert len(world.claude_records()) == 1
    assert world.read_session(workspace_id) == session_before


def test_normal_when_launch_record_missing(session_world: SessionWorld) -> None:
    """プラグインだけを渡すと、追加の MCP を空の指定にして launch.json を作る（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = str(world.create_workspace()["id"])
    _launch_path(world, workspace_id).unlink(missing_ok=True)
    plugin = _plugin_dir(world, "aituber")
    config_before = _config_path(world).read_bytes()
    # 実行
    status, body = world.api(
        "PATCH", f"/workspaces/{workspace_id}", {"plugin_dirs": [str(plugin)]}
    )
    # 検証
    assert (status, body) == (200, {"id": workspace_id, "changed": ["plugin_dirs"]})
    assert _read_launch(world, workspace_id) == {
        "mcp_config": {"mcpServers": {}},
        "plugin_dirs": [str(plugin)],
    }
    assert _config_path(world).read_bytes() == config_before


def test_normal_when_closed(session_world: SessionWorld) -> None:
    """クローズしたワークスペースのプラグインだけを書き換え、追加の MCP の記録を残す（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _with_options(world)
    close_status, close_body = world.api("POST", f"/workspaces/{workspace_id}/close")
    assert close_status == 200, close_body
    new_plugin = _plugin_dir(world, "aituber-talk")
    world.pi.requests.clear()
    # 実行
    status, body = world.api(
        "PATCH", f"/workspaces/{workspace_id}", {"plugin_dirs": [str(new_plugin)]}
    )
    # 検証
    assert (status, body) == (200, {"id": workspace_id, "changed": ["plugin_dirs"]})
    assert _read_launch(world, workspace_id) == {
        "mcp_config": MCP_CONFIG,
        "plugin_dirs": [str(new_plugin)],
    }
    assert world.pi.changes() == []


def test_error_when_plugin_dir_unreadable(session_world: SessionWorld) -> None:
    """ほかの指定が読めても、読めないプラグインのフォルダがあれば何も書かずに 422 を返す（異常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _with_options(world)
    missing = world.root / "plugins" / "no-such-plugin"
    config_before = _config_path(world).read_bytes()
    launch_before = _launch_path(world, workspace_id).read_bytes()
    # 実行
    status, body = world.api(
        "PATCH",
        f"/workspaces/{workspace_id}",
        {
            "settings": {"summary": "配信の台本を作る"},
            "mcp_config": NEW_MCP_CONFIG,
            "plugin_dirs": [str(missing)],
        },
    )
    # 検証
    assert (status, body["stage"]) == (422, "plugin_dirs"), body
    assert str(missing) in body["detail"]
    assert _config_path(world).read_bytes() == config_before
    assert _launch_path(world, workspace_id).read_bytes() == launch_before


def test_error_when_flow_unreadable(session_world: SessionWorld) -> None:
    """進め方の文書が無ければ、何も書かずに 422 を返す（異常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _with_options(world)
    new_plugin = _plugin_dir(world, "aituber-talk")
    config_before = _config_path(world).read_bytes()
    launch_before = _launch_path(world, workspace_id).read_bytes()
    # 実行
    status, body = world.api(
        "PATCH",
        f"/workspaces/{workspace_id}",
        {"flow": {"source": "aituber", "doc": "no-such-doc"}, "plugin_dirs": [str(new_plugin)]},
    )
    # 検証
    assert (status, body["stage"]) == (422, "flow"), body
    assert _config_path(world).read_bytes() == config_before
    assert _launch_path(world, workspace_id).read_bytes() == launch_before


def test_error_when_settings_invalid(session_world: SessionWorld) -> None:
    """設定のキーがスキーマに合わなければ、何も書かずに 422 を返す（異常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _with_options(world)
    new_plugin = _plugin_dir(world, "aituber-talk")
    config_before = _config_path(world).read_bytes()
    launch_before = _launch_path(world, workspace_id).read_bytes()
    # 実行
    status, body = world.api(
        "PATCH",
        f"/workspaces/{workspace_id}",
        {"settings": {"summary": ""}, "plugin_dirs": [str(new_plugin)]},
    )
    # 検証
    assert (status, body["stage"]) == (422, "settings"), body
    assert "\nconfig.yaml: summary" in f"\n{body['detail']}"
    assert _config_path(world).read_bytes() == config_before
    assert _launch_path(world, workspace_id).read_bytes() == launch_before


def test_error_when_workspace_missing(session_world: SessionWorld) -> None:
    """状態のフォルダの ID の一覧に無い ID は 404 を返し、何も書かない（異常系）。"""
    # 準備
    world = session_world
    world.start()
    plugin = _plugin_dir(world, "aituber")
    world.create_workspace()
    state_before = _state_files(world)
    # 実行
    status, body = world.api(
        "PATCH", "/workspaces/mindstella-x-000000", {"plugin_dirs": [str(plugin)]}
    )
    # 検証
    assert (status, body["stage"]) == (404, "workspace"), body
    assert _state_files(world) == state_before


def test_error_when_body_empty(session_world: SessionWorld) -> None:
    """4 つのキーのどれも無い本文は、何も書かずに 400 を返す（異常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _with_options(world)
    config_before = _config_path(world).read_bytes()
    launch_before = _launch_path(world, workspace_id).read_bytes()
    # 実行
    status, body = world.api("PATCH", f"/workspaces/{workspace_id}", {})
    # 検証
    assert (status, body["stage"]) == (400, "body"), body
    assert _config_path(world).read_bytes() == config_before
    assert _launch_path(world, workspace_id).read_bytes() == launch_before


def test_normal_when_flow_removed(session_world: SessionWorld) -> None:
    """`flow: null` で、進め方の文書を確かめずに config.yaml から外す（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _with_options(world)
    expected = _without_flow(_read_config(world))
    world.pi.requests.clear()
    # 実行
    status, body = world.api("PATCH", f"/workspaces/{workspace_id}", {"flow": None})
    # 検証
    assert (status, body) == (200, {"id": workspace_id, "changed": ["flow"]})
    assert _read_config(world) == expected
    assert _doc_requests(world) == []
