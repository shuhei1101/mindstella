"""ワークスペースの作成（POST /workspaces）の結合テスト。"""

from __future__ import annotations

import json
import shutil
import urllib.request
from pathlib import Path

import yaml
from launch_fixtures import PLUGIN_DIR
from session_fixtures import SessionWorld

from tests.integration.plugin.test_agent_flows import AgentFlowWorld, agent_flow_world  # noqa: F401

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
    # 記録を配信する設定は種類ごとの 7 つの文書の行と関連の種類を持ち、行が指すスキーマが schemas/ にある
    source = yaml.safe_load((folder / ".mindstella" / "dev-docs.yaml").read_text(encoding="utf-8"))
    documents = source["documents"]
    assert len(documents) == 7
    assert {(row["records"], row["body_file"]) for row in documents} == {("items", "body")}
    assert source["related"]["types"]
    assert all((folder / ".mindstella" / row["schema"]).is_file() for row in documents)
    assert _launch_json(world, body["id"]) == {
        "mcp_config": MCP_CONFIG,
        "plugin_dirs": [str(plugin)],
    }
    assert body["id"] in _ids(world)
    # 行の追加は、GET /settings/sources が返した version を expectedVersion に添える（ワークスペースの行・エージェントフローの行の順）
    assert [request[2]["expectedVersion"] for request in world.pi.changes()] == ["1", "2"]
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
        },
        # エージェントフローの配信元（行が無いので足す。書き込みの範囲を持たない）
        {
            "id": "mindstella-agent-flows",
            "config": str(PLUGIN_DIR / "agent-flows" / "dev-docs.yaml"),
            "scope": {"read": [str(world.allowed), f"{world.allowed}/**"]},
            "outside_read": True,
        },
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
    # ワークスペースの行と、エージェントフローの配信元の行
    assert [request[0] for request in world.pi.changes()] == ["POST", "POST"]


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


def test_normal_when_folder_moved(session_world: SessionWorld) -> None:
    """配信元の行が記録の無い前のフォルダを指していれば、行の config・scope を移した先へ変える（正常系）。"""
    # 準備
    world = session_world
    world.start()
    created = world.create_workspace(mcp_config=MCP_CONFIG)
    moved = world.folder("家計簿-移動後")
    world.folder().rename(moved)
    launch_before = _launch_json(world, created["id"])
    world.pi.requests.clear()
    # 実行
    status, body = world.api("POST", "/workspaces", {"folder": str(moved)})
    # 検証
    assert (status, body["id"], body["result"]) == (200, created["id"], "opened"), body
    resolved = moved.resolve()
    assert [(request[0], request[2]["source"]) for request in world.pi.changes()] == [
        (
            "PATCH",
            {
                "config": f"{resolved}/.mindstella/dev-docs.yaml",
                "scope": {
                    "read": [str(resolved), f"{resolved}/**"],
                    "write": [str(resolved), f"{resolved}/**"],
                },
            },
        )
    ]
    assert _launch_json(world, created["id"]) == launch_before


def test_error_when_duplicate_id(session_world: SessionWorld) -> None:
    """配信元の行が指す別のフォルダに同じ ID の記録が残っていれば 409 を返し、行を変えない（異常系）。"""
    # 準備
    world = session_world
    world.start()
    world.create_workspace()
    original = world.folder()
    copied = world.folder("家計簿-コピー")
    shutil.copytree(original, copied)
    before = {
        folder: (folder / ".mindstella" / "config.yaml").read_bytes()
        for folder in (original, copied)
    }
    world.pi.requests.clear()
    # 実行
    status, body = world.api("POST", "/workspaces", {"folder": str(copied)})
    # 検証
    assert (status, body["stage"]) == (409, "duplicate"), body
    assert str(original.resolve()) in body["detail"]
    assert world.pi.changes() == []
    assert {
        folder: (folder / ".mindstella" / "config.yaml").read_bytes()
        for folder in (original, copied)
    } == before


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


def test_normal_when_schema_copy_rewritten(session_world: SessionWorld) -> None:
    """今のバージョンの記録のスキーマの複製を書き直し、端末の設定の行をそのまま送る PUT で project-index に配信元を読み直させる（正常系）。"""
    # 準備
    world = session_world
    world.start()
    world.create_workspace()
    (world.folder() / ".mindstella" / "schemas" / "docs.schema.json").write_text("{}\n", encoding="utf-8")
    plugin_schema = PLUGIN_DIR / "skills" / "mindmap" / "schemas" / "docs.schema.json"
    settings_rows = yaml.safe_load(world.pi.settings_path.read_text(encoding="utf-8"))["sources"]
    world.pi.requests.clear()
    # 実行
    status, body = world.api("POST", "/workspaces", {"folder": str(world.folder())})
    # 検証
    assert status == 200, body
    assert (world.folder() / ".mindstella" / "schemas" / "docs.schema.json").read_bytes() == plugin_schema.read_bytes()
    puts = [request for request in world.pi.requests if request[0] == "PUT"]
    assert [(path, request["sources"]) for _method, path, request in puts] == [("/settings/sources", settings_rows)]
    assert "expectedVersion" in puts[0][2]
    assert world.pi.changes() == []


def _call(world: AgentFlowWorld, folder: Path, tool: str, **arguments: object) -> dict[str, object]:
    """project-index の文書の MCP のツールを、ワークスペースのフォルダを作業場所にして呼び、JSON の結果を返す。"""
    client = world.pi_client()
    result = client.call(tool, cwd=str(folder), format="json", **arguments)
    client.close()
    assert result.is_error is False, result.text
    return json.loads(result.text)


def _reload_pi(world: AgentFlowWorld) -> None:
    """端末の設定のファイルの行をそのまま `PUT /settings/sources` に送り、project-index に全ての配信元を読み直させる。"""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    url = f"http://127.0.0.1:{world.pi_port}/settings/sources"
    with opener.open(url, timeout=30) as response:
        settings = json.loads(response.read())
    rows = yaml.safe_load(Path(settings["settingsPath"]).read_text(encoding="utf-8"))["sources"]
    request = urllib.request.Request(
        url,
        data=json.dumps({"expectedVersion": settings["version"], "sources": rows}).encode("utf-8"),
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    with opener.open(request, timeout=30) as response:
        assert response.status == 200


def test_normal_when_real_project_index(agent_flow_world: AgentFlowWorld) -> None:  # noqa: F811 - 読み込んだ fixture を引数で受ける
    """作った Git 管理外のワークスペースを実際の project-index で配信し、記録の作成・更新、本文を持たない項目の検索・更新、スキーマの複製を更新前に戻した後の開き直しを通す（正常系）。"""
    # 準備
    world = agent_flow_world
    # 日本語のフォルダ名は project-index の配信元の ID の検査に違反する（#544）
    folder = world.allowed / "kakeibo"
    status, body = world.api("POST", "/workspaces", {"folder": str(folder)})
    assert status == 201, body
    source = body["id"]
    records = folder / ".mindstella"
    (records / "terms.yaml").write_text(
        yaml.safe_dump({"items": [{"id": "G-1", "title": "用語", "meaning": "意味"}]}, allow_unicode=True),
        encoding="utf-8",
    )
    # 実行（不具合 1: 検討事項の作成と更新）
    _call(
        world,
        folder,
        "write_docs",
        source=source,
        operations=[
            {"op": "create", "kind": "decisions", "id": "D-1", "data": {"title": "確認", "status": "未整理"}},
            {
                "op": "create",
                "kind": "docs",
                "id": "A-1",
                "data": {"title": "資料", "kind": "文書", "status": "下書き", "body": "docs/A-1.md", "@body": "本文"},
            },
        ],
    )
    decision = _call(
        world,
        folder,
        "search_docs",
        source=source,
        filter={"field": "id", "op": "eq", "values": ["D-1"]},
    )
    _call(
        world,
        folder,
        "write_docs",
        source=source,
        operations=[
            {"op": "update", "id": "D-1", "expected_version": decision["items"][0]["values"]["version"], "set": {"status": "未決定"}}
        ],
    )
    # 実行（不具合 3: 本文を持たない G-1 の検索と更新）
    term = _call(
        world,
        folder,
        "search_docs",
        source=source,
        filter={"field": "id", "op": "eq", "values": ["G-1"]},
    )
    _call(
        world,
        folder,
        "write_docs",
        source=source,
        operations=[{"op": "update", "id": "G-1", "expected_version": term["items"][0]["values"]["version"], "set": {"meaning": "意味 2"}}],
    )
    # 実行（不具合 2: スキーマの複製を更新前に戻して開き直す）
    (records / "schemas" / "docs.schema.json").write_text(
        json.dumps(
            {
                "type": "object",
                "properties": {"items": {"type": "array", "items": {"type": "object", "required": ["deliverable"]}}},
            }
        ),
        encoding="utf-8",
    )
    # 古いスキーマを project-index に読み込ませる
    _reload_pi(world)
    stale = _call(world, folder, "search_docs", source=source, filter={"field": "id", "op": "eq", "values": ["A-1"]})
    reopened_status, reopened = world.api("POST", "/workspaces", {"folder": str(folder)})
    doc = _call(world, folder, "search_docs", source=source, filter={"field": "id", "op": "eq", "values": ["A-1"]})
    # 検証
    items = yaml.safe_load((records / "decisions.yaml").read_text(encoding="utf-8"))["items"]
    assert [(item["id"], item["status"]) for item in items] == [("D-1", "未決定")]
    assert {"created", "updated"} & set(items[0]) == set()
    assert [item["id"] for item in term["items"]] == ["G-1"]
    assert "読み込めない" not in json.dumps(term, ensure_ascii=False)
    terms = yaml.safe_load((records / "terms.yaml").read_text(encoding="utf-8"))["items"]
    assert terms == [{"id": "G-1", "title": "用語", "meaning": "意味 2"}]
    assert "deliverable" in json.dumps(stale, ensure_ascii=False)
    assert reopened_status == 200, reopened
    assert [item["id"] for item in doc["items"]] == ["A-1"]
    assert "deliverable" not in json.dumps(doc, ensure_ascii=False)
