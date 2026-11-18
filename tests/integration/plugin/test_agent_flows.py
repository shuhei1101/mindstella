"""エージェントフローの参照（plugins/mindstella/agent-flows/ を project-index の配信元として配る）の結合テスト。

project-index は、手元のクローンの `project-index serve` をテストごとの一時フォルダの端末の設定で起動する。
常駐サーバーは、git の外へ写したプラグインのフォルダ（インストールしたプラグインと同じく git の作業ツリーでない）の
`server.py` で起動する。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml
from launch_fixtures import PLUGIN_DIR
from workspace_fixtures import (
    LISTEN_HOST,
    MDMARK_COMMAND_ENV,
    NOOP_MDMARK_COMMAND,
    PORT_ENV,
    STATE_HOME_ENV,
    McpClient,
    McpServer,
    free_port,
)

# project-index のクローンを指す環境変数（無ければ利用者の端末の設定の `clone` を読む）
CLONE_ENV = "MINDSTELLA_TEST_PROJECT_INDEX_CLONE"

# エージェントフローの配信元の ID
SOURCE_ID = "mindstella-agent-flows"

# プラグインに同梱するエージェントフローの ID
FLOW_IDS = ["mindstella/on-comment", "mindstella/record", "mindstella/startup"]

# エージェントフローの必須のキー
REQUIRED_KEYS = {"id", "title", "summary", "condition", "steps"}

# 削除したツール（工程が指してはいけない）
REMOVED_TOOLS = {"next", "goal", "write_release", "clear_release", "status", "migrate"}

# project-index が待ち受けるまで待つ上限秒数と、確かめる間隔
PI_START_TIMEOUT_SEC = 60
PI_POLL_SEC = 0.5

# project-index を止めるのを待つ上限秒数
PI_STOP_TIMEOUT_SEC = 10

# 1 回の HTTP を待つ上限秒数
HTTP_TIMEOUT_SEC = 30


@dataclass
class AgentFlowWorld:
    """実際の project-index と、写したプラグインの常駐サーバー。"""

    pi_port: int
    server: McpServer
    allowed: Path
    plugin_dir: Path

    def api(self, method: str, path: str, body: Any = None) -> tuple[int, dict[str, Any]]:
        """常駐サーバーの API を呼ぶ。"""
        request = urllib.request.Request(
            f"http://{LISTEN_HOST}:{self.server.port}{path}",
            data=None if body is None else json.dumps(body).encode("utf-8"),
            method=method,
            headers={"Content-Type": "application/json", "Host": f"{LISTEN_HOST}:{self.server.port}"},
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(request, timeout=HTTP_TIMEOUT_SEC) as response:
                return response.status, json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"{}")

    def pi_sources(self) -> list[dict[str, Any]]:
        """project-index の端末の設定の配信元の行を返す。"""
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://{LISTEN_HOST}:{self.pi_port}/settings/sources", timeout=HTTP_TIMEOUT_SEC) as response:
            return json.loads(response.read())["sources"]

    def pi_client(self) -> McpClient:
        """project-index の文書の MCP へつなぐ。"""
        return McpClient(f"http://{LISTEN_HOST}:{self.pi_port}/mcp")


def _project_index_command() -> Path:
    """project-index のクローンの `project-index` を返す。見つからなければ skip する。"""
    clone = os.environ.get(CLONE_ENV)
    if not clone:
        config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        settings = config_home / "project-index" / "settings.yaml"
        loaded = yaml.safe_load(settings.read_text(encoding="utf-8")) if settings.is_file() else None
        clone = loaded.get("clone") if isinstance(loaded, dict) else None
    command = Path(str(clone)) / ".venv" / "bin" / "project-index" if clone else None
    if command is None or not command.is_file():
        pytest.skip(f"project-index のクローンが無い（{CLONE_ENV} か端末の設定の clone で指す）")
    return command


def _wait_pi(port: int, process: subprocess.Popen[str]) -> None:
    """project-index の `GET /settings/sources` が返るまで待つ。"""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + PI_START_TIMEOUT_SEC
    while True:
        assert process.poll() is None, "project-index が終わりました"
        try:
            with opener.open(f"http://{LISTEN_HOST}:{port}/settings/sources", timeout=PI_POLL_SEC):
                return
        except OSError:
            assert time.monotonic() < deadline, "project-index が待ち受けません"
            time.sleep(PI_POLL_SEC)


@pytest.fixture
def agent_flow_world(tmp_path: Path) -> Iterator[AgentFlowWorld]:
    """実際の project-index と、git の外へ写したプラグインの常駐サーバーを立て、テストの後で止める。"""
    command = _project_index_command()
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    plugin_dir = tmp_path / "plugin" / "mindstella"
    shutil.copytree(PLUGIN_DIR, plugin_dir)
    settings = tmp_path / "pi" / "settings.yaml"
    settings.parent.mkdir()
    settings.write_text(
        yaml.safe_dump(
            {
                "version": "1",
                "clone": str(command.parents[2]),
                "sources": [],
                "mindstella": {"allowed_dirs": [str(allowed)]},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    pi_port = free_port()
    pi_log = (tmp_path / "pi" / "serve.log").open("w", encoding="utf-8")
    process = subprocess.Popen(
        [str(command), "serve"],
        env={
            **os.environ,
            "PROJECT_INDEX_CONFIG": str(settings),
            "PROJECT_INDEX_PORT": str(pi_port),
            "XDG_STATE_HOME": str(tmp_path / "pi-state"),
        },
        stdout=pi_log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    server: McpServer | None = None
    try:
        _wait_pi(pi_port, process)
        server = McpServer(
            python=sys.executable,
            env={
                **os.environ,
                "PYTHONUTF8": "1",
                PORT_ENV: str(free_port()),
                STATE_HOME_ENV: str(tmp_path / "state"),
                MDMARK_COMMAND_ENV: NOOP_MDMARK_COMMAND,
                "PROJECT_INDEX_PORT": str(pi_port),
            },
            cwd=tmp_path,
            script=plugin_dir / "skills" / "mindmap" / "scripts" / "server.py",
        )
        yield AgentFlowWorld(pi_port=pi_port, server=server, allowed=allowed, plugin_dir=plugin_dir)
    finally:
        if server is not None:
            server.stop()
        process.terminate()
        process.wait(timeout=PI_STOP_TIMEOUT_SEC)
        pi_log.close()


def _flow_files() -> list[dict[str, Any]]:
    """プラグインの `agent-flows/` のエージェントフローを、ファイルの名前の順に読む。"""
    return [
        yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted((PLUGIN_DIR / "agent-flows").glob("*.yaml"))
        if path.name != "dev-docs.yaml"
    ]


def test_normal(agent_flow_world: AgentFlowWorld) -> None:
    """MindStella のセッションが、起動と再開のエージェントフローを ID で参照する（正常系）。"""
    # 準備
    world = agent_flow_world
    # 日本語のフォルダ名は project-index の配信元の ID の検査に違反する（#544）
    folder = world.allowed / "kakeibo"
    status, body = world.api("POST", "/workspaces", {"folder": str(folder)})
    assert status == 201, body
    client = world.pi_client()
    # 実行
    found = {
        flow_id: client.call(
            "search_docs",
            source=SOURCE_ID,
            filter={"field": "id", "op": "eq", "values": [flow_id]},
            view="full",
            format="json",
            cwd=str(folder),
        )
        for flow_id in FLOW_IDS
    }
    client.close()
    # 検証
    for flow_id, result in found.items():
        assert result.is_error is False, result.text
        items = json.loads(result.text)["items"]
        assert [item["id"] for item in items] == [flow_id]
    row = next(row for row in world.pi_sources() if row["id"] == SOURCE_ID)
    assert row["config"] == [str(world.plugin_dir / "agent-flows" / "dev-docs.yaml")]
    assert row["scope"] == {"read": [str(world.allowed), f"{world.allowed}/**"], "write": None}
    # どのエージェントフローも必須のキーを持ち、進み具合を持たない
    for flow in _flow_files():
        assert set(flow) >= REQUIRED_KEYS
        assert len(flow["steps"]) >= 1
        assert "progress" not in flow


def test_normal_when_calls_exist(agent_flow_world: AgentFlowWorld) -> None:
    """どの工程の calls も今の MCP のツールを指す（正常系）。"""
    # 準備
    world = agent_flow_world
    client = world.pi_client()
    tools = {
        "mindstella": {tool["name"] for tool in world.server.list_tools()},
        "project-index": {tool["name"] for tool in client.list_tools()},
    }
    client.close()
    # 実行
    calls = [
        (call["server"], call["tool"])
        for flow in _flow_files()
        for step in flow["steps"]
        for call in step.get("calls", [])
    ]
    # 検証
    assert calls
    assert [(server, tool) for server, tool in calls if tool not in tools[server]] == []
    assert {tool for _server, tool in calls} & REMOVED_TOOLS == set()
