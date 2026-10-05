"""MCP サーバーの起動（stdio のサーバーとして立てたときの、ツールの一覧・結果とエラー・終わり方・排他）の結合テスト。"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest
import yaml
from workspace_fixtures import McpServer

from .fixture_types import MakeWorkspace, StartServer
from .http_helpers import http_request

# サーバーが名乗る名前
SERVER_NAME = "mindstella"

# 登録するツールの名前（インターフェース定義『MCP サーバーの起動』）
TOOL_NAMES = [
    "init",
    "add",
    "update",
    "update_settings",
    "adopt",
    "edit_option",
    "batch",
    "changes_since_read",
    "commit",
    "pending",
    "status",
    "next",
    "impact",
    "find",
    "show",
    "attrs",
    "check",
    "goal",
    "migrate",
    "clear_release",
    "export",
    "preview_url",
    "submissions",
    "take_submission",
]

# 2 つのプロセスがそれぞれ足す検討事項の件数
ADDS_PER_PROCESS = 20

# 足す検討事項
NEW_DECISION: dict[str, Any] = {
    "title": "並べて足す問い",
    "target": "mindmap",
    "category": "データ構造",
    "phase": "要件",
    "status": "未決定",
}


def _add_many(server: McpServer, root: Path, errors: list[str]) -> None:
    """検討事項を ADDS_PER_PROCESS 件足し、エラーになった本文を errors に集める。"""
    for _ in range(ADDS_PER_PROCESS):
        result = server.call("add", workspace=str(root), kind="decision", item=NEW_DECISION)
        if result.is_error:
            errors.append(result.text)


def test_normal(start_server: StartServer) -> None:
    """立てたサーバーがツールの一覧を返す（正常系）。"""
    # 準備
    server = start_server()
    # 実行
    tools = server.list_tools()
    # 検証
    assert server.server_name == SERVER_NAME
    assert [tool["name"] for tool in tools] == TOOL_NAMES
    assert all("workspace" in tool["inputSchema"]["required"] for tool in tools)


def test_normal_when_tool_fails(tmp_path: Path, start_server: StartServer) -> None:
    """ワークスペースが無いフォルダを渡すと、ツールのエラーで返してサーバーは動き続ける（正常系）。"""
    # 準備
    server = start_server()
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = server.call("status", workspace=str(root))
    tools = server.list_tools()
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert str(root) in result.text
    assert "Traceback" not in result.text
    assert [tool["name"] for tool in tools] == TOOL_NAMES


def test_normal_when_argument_missing(start_server: StartServer) -> None:
    """要る引数が無いと、引数の誤りのツールのエラーで返す（正常系）。"""
    # 準備
    server = start_server()
    # 実行
    result = server.call("status")
    # 検証
    assert result.is_error is True
    assert "workspace" in result.text


def test_normal_when_stdin_closed(make_workspace: MakeWorkspace, start_server: StartServer) -> None:
    """Claude Code が閉じたら、配信を止めて終わる（正常系）。"""
    # 準備
    root = make_workspace()
    server = start_server()
    url = server.call("preview_url", workspace=str(root)).data["url"]
    # 実行
    server.close_stdin()
    exit_code = server.wait_exit()
    # 検証
    assert exit_code == 0
    with pytest.raises(OSError, match=r"."):
        http_request(url)


def test_normal_when_two_processes_write(
    make_workspace: MakeWorkspace, start_server: StartServer
) -> None:
    """2 つのプロセスが同じワークスペースへ同時に書いても、どちらの書き換えも失わず ID も重ならない（正常系）。"""
    # 準備
    root = make_workspace()
    first = start_server()
    second = start_server()
    errors: list[str] = []
    threads = [
        threading.Thread(target=_add_many, args=(server, root, errors))
        for server in (first, second)
    ]
    # 実行
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    # 検証
    assert errors == []
    items = yaml.safe_load((root / "decisions.yaml").read_text(encoding="utf-8"))["items"]
    assert [item["id"] for item in items] == [f"D-{number}" for number in range(1, 41)]
