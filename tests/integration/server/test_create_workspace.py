"""ワークスペースの作成（POST /workspaces）の結合テスト。"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import yaml
from session_fixtures import SessionWorld

# 進め方の文書
FLOW = {"source": "aituber", "doc": "flow-script"}

# 追加の MCP の定義
MCP_CONFIG = {"mcpServers": {"aituber": {"command": "aituber-mcp"}}}


def _plugin_dir(world: SessionWorld, *, manifest: bool = True) -> Path:
    """追加のプラグインのフォルダを作る。"""
    folder = world.root / "plugins" / "aituber"
    (folder / ".claude-plugin").mkdir(parents=True)
    if manifest:
        (folder / ".claude-plugin" / "plugin.json").write_text(
            '{"name": "aituber"}', encoding="utf-8"
        )
    return folder


def _serve_flow(world: SessionWorld) -> None:
    """進め方の文書の配信元を、許可するフォルダが読める scope で Mock に置く。"""
    world.pi.rows["aituber"] = {
        "id": "aituber",
        "config": ["/repo/aituber/project-index.yaml"],
        "scope": {"read": [str(world.allowed), f"{world.allowed}/**"]},
        "outsideRead": True,
    }
    world.pi.docs["aituber"] = [{"id": "flow-script", "path": "docs/flow/flow-script.yaml"}]


def _launch_json(world: SessionWorld, workspace_id: str) -> dict[str, object] | None:
    """状態のフォルダの launch.json を読む。"""
    path = world.state_root / "workspaces" / workspace_id / "launch.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _ids(world: SessionWorld) -> list[str]:
    """状態のフォルダの ID の一覧。"""
    path = world.state_root / "workspaces.yaml"
    return list(yaml.safe_load(path.read_text(encoding="utf-8"))["ids"]) if path.exists() else []


def test_normal(session_world: SessionWorld) -> None:
    """記録が無いフォルダに記録を作り、配信元に登録して ID と URL を返す（正常系）。"""
    # 準備
    world = session_world
    _serve_flow(world)
    plugin = _plugin_dir(world)
    world.start()
    folder = world.folder()
    # 実行
    status, body = world.api(
        "POST",
        "/workspaces",
        {
            "folder": str(folder),
            "flow": FLOW,
            "mcp_config": MCP_CONFIG,
            "plugin_dirs": [str(plugin)],
        },
    )
    # 検証
    assert status == 201, body
    assert (body["result"], body["launch_options_recorded"]) == ("created", True)
    config = yaml.safe_load((folder / ".mindstella" / "config.yaml").read_text(encoding="utf-8"))
    assert (config["id"], config["flow"]) == (body["id"], FLOW)
    assert _launch_json(world, body["id"]) == {
        "mcp_config": MCP_CONFIG,
        "plugin_dirs": [str(plugin)],
    }
    assert body["id"] in _ids(world)
    posts = [request[2]["source"] for request in world.pi.changes() if request[0] == "POST"]
    resolved = folder.resolve()
    assert posts == [
        {
            "id": body["id"],
            "config": f"{resolved}/.mindstella/dev-docs.yaml",
            "scope": {
                "read": [str(resolved), f"{resolved}/**"],
                "write": [str(resolved), f"{resolved}/**"],
            },
            "outside_read": True,
        }
    ]
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(body["url"], timeout=10) as response:
        assert response.status == 200


def test_normal_when_records_exist(session_world: SessionWorld) -> None:
    """残っている記録を開き、状態のフォルダに記録が無いので今回の指定を記録する（正常系）。"""
    # 準備
    world = session_world
    world.start()
    created = world.create_workspace()
    config_path = world.folder() / ".mindstella" / "config.yaml"
    before = config_path.read_bytes()
    world.pi.rows.clear()
    world.pi.requests.clear()
    (world.state_root / "workspaces" / created["id"] / "launch.json").unlink()
    # 実行
    status, body = world.api(
        "POST", "/workspaces", {"folder": str(world.folder()), "mcp_config": MCP_CONFIG}
    )
    # 検証
    assert (status, body["result"]) == (200, "opened"), body
    assert config_path.read_bytes() == before
    assert _launch_json(world, created["id"]) == {"mcp_config": MCP_CONFIG, "plugin_dirs": []}
    assert [request[0] for request in world.pi.changes()] == ["POST"]


def test_normal_when_already_open(session_world: SessionWorld) -> None:
    """記録・配信元の行・状態のフォルダの記録を変えずに、既にある ID を返す（正常系）。"""
    # 準備
    world = session_world
    world.start()
    created = world.create_workspace(mcp_config=MCP_CONFIG)
    config_path = world.folder() / ".mindstella" / "config.yaml"
    before = (config_path.read_bytes(), _launch_json(world, created["id"]))
    world.pi.requests.clear()
    # 実行
    status, body = world.api("POST", "/workspaces", {"folder": str(world.folder())})
    # 検証
    assert status == 200, body
    assert (body["id"], body["result"], body["launch_options_recorded"]) == (
        created["id"],
        "already_open",
        False,
    )
    assert (config_path.read_bytes(), _launch_json(world, created["id"])) == before
    assert world.pi.changes() == []


def test_normal_when_closed(session_world: SessionWorld) -> None:
    """配信元の行の outside_read を真に戻し、クローズ待ちを解く（正常系）。"""
    # 準備
    world = session_world
    world.start()
    created = world.create_workspace()
    world.pi.rows[created["id"]]["outsideRead"] = False
    world.write_session(created["id"], status="stopped", close_pending=True, pane=None)
    world.pi.requests.clear()
    # 実行
    status, body = world.api("POST", "/workspaces", {"folder": str(world.folder())})
    # 検証
    assert (status, body["result"]) == (200, "reopened"), body
    assert [request[2]["source"] for request in world.pi.changes()] == [{"outside_read": True}]
    session = world.read_session(created["id"])
    assert session is not None
    assert session["close_pending"] is False


def test_error_when_folder_not_allowed(session_world: SessionWorld) -> None:
    """許可するフォルダの外は 403 を返し、何も書かない（異常系）。"""
    # 準備
    world = session_world
    world.start()
    folder = world.root / "outside" / "家計簿"
    # 実行
    status, body = world.api("POST", "/workspaces", {"folder": str(folder)})
    # 検証
    assert (status, body["stage"]) == (403, "folder"), body
    assert not (folder / ".mindstella").exists()
    assert not world.state_root.exists()
    assert world.pi.changes() == []


def test_error_when_options_invalid(session_world: SessionWorld) -> None:
    """読めない mcp_config・plugin_dirs・flow は 422 を返し、何も書かない（異常系）。"""
    # 準備
    world = session_world
    _serve_flow(world)
    plugin = _plugin_dir(world, manifest=False)
    world.start()
    folder = str(world.folder())
    cases = [
        ({"mcp_config": {"mcpServers": {"mindstella": {"command": "x"}}}}, "mcp_config"),
        ({"plugin_dirs": [str(plugin)]}, "plugin_dirs"),
        ({"flow": {"source": "aituber", "doc": "no-such-doc"}}, "flow"),
    ]
    for extra, stage in cases:
        # 実行
        status, body = world.api("POST", "/workspaces", {"folder": folder, **extra})
        # 検証
        assert (status, body["stage"]) == (422, stage), body
    assert not (world.folder() / ".mindstella").exists()
    assert not (world.state_root / "workspaces").exists()
    assert world.pi.changes() == []


def test_error_when_source_registration_fails(session_world: SessionWorld) -> None:
    """配信元の登録に失敗したら 502 を返し、この依頼で作った記録と状態のフォルダの記録を消す（異常系）。"""
    # 準備
    world = session_world
    world.pi.post_status = 500
    world.start()
    # 実行
    status, body = world.api(
        "POST", "/workspaces", {"folder": str(world.folder()), "mcp_config": MCP_CONFIG}
    )
    # 検証
    assert (status, body["stage"]) == (502, "source"), body
    assert not (world.folder() / ".mindstella").exists()
    assert list((world.state_root / "workspaces").glob("*/launch.json")) == []
    assert _ids(world) == []


def test_error_when_host_not_local(session_world: SessionWorld) -> None:
    """Host が端末の中の値でなければ 403（異常系）。"""
    # 準備
    world = session_world
    world.start({"MINDSTELLA_ALLOWED_HOSTS": "example.test"})
    # 実行
    status, body = world.api(
        "POST", "/workspaces", {"folder": str(world.folder())}, host="example.test"
    )
    # 検証
    assert (status, body["stage"]) == (403, "host"), body
    assert not world.folder().exists()
    assert world.pi.requests == []
