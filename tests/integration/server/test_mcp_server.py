"""MCP サーバーの起動（常駐サーバーとして起動したときの、ツールの一覧・結果とエラー・相対パス・終わり方・排他・待ち受けのポート）の結合テスト。"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest
import yaml
from external_access_helpers import read_hook_lines, read_settled_hook_lines, recording_hook
from workspace_fixtures import (
    LISTEN_HOST,
    PORT_ENV,
    RECORD_DIR,
    SERVER_SCRIPT,
    McpServer,
    free_port,
    is_listening,
    read_server_status,
)

from .fixture_types import MakeItem, MakeWorkspace, StartServer
from .http_helpers import http_request

# サーバーが名乗る名前
SERVER_NAME = "mindstella"

# 登録するツールの名前（インターフェース定義『MCP サーバーの起動』）
TOOL_NAMES = [
    "init",
    "add",
    "update",
    "remove",
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
    "tags",
    "check",
    "goal",
    "migrate",
    "clear_release",
    "export",
    "preview_url",
    "readme",
    "threads",
    "thread",
    "new_thread",
    "reply",
    "set_thread_status",
    "update_thread",
    "server_status",
    "server_stop",
]

# 待ち受けられずに終わる常駐サーバーを待つ上限秒数
EXIT_WAIT_SEC = 30

# プレビューの画面のパス
PREVIEW_PAGE = "/mindstella.html"

# 終了時のフックを渡す環境変数
STOP_HOOK_ENV = "MINDSTELLA_PREVIEW_STOP_HOOK"

# 2 つのプロセスがそれぞれ足す検討事項の件数
ADDS_PER_PROCESS = 20

# 足す検討事項
NEW_DECISION: dict[str, Any] = {
    "title": "並べて足す問い",
    "target": "mindmap",
    "category": "データ構造",
    "phase": "要件",
    "status": "未決定",
    "options": [{"key": "A", "content": "案 A"}],
}


def _run_server(port: str) -> subprocess.CompletedProcess[str]:
    """`MINDSTELLA_PORT` に port を渡して常駐サーバーを起動し、終わるまで待つ。"""
    return subprocess.run(
        [sys.executable, str(SERVER_SCRIPT)],
        env={**os.environ, "PYTHONUTF8": "1", PORT_ENV: port},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=EXIT_WAIT_SEC,
        check=False,
    )


def _add_many(server: McpServer, root: Path, errors: list[str]) -> None:
    """検討事項を ADDS_PER_PROCESS 件足し、エラーになった本文を errors に集める。"""
    for _ in range(ADDS_PER_PROCESS):
        result = server.call("add", workspace=str(root), kind="decision", item=NEW_DECISION)
        if result.is_error:
            errors.append(result.text)


def test_normal(start_server: StartServer) -> None:
    """起動したサーバーがツールの一覧を返す（正常系）。"""
    # 準備
    server = start_server()
    # 実行
    tools = server.list_tools()
    # 検証
    assert server.server_name == SERVER_NAME
    assert [tool["name"] for tool in tools] == TOOL_NAMES
    assert all("session" in tool["inputSchema"]["properties"] for tool in tools)
    assert all("session" not in tool["inputSchema"].get("required", []) for tool in tools)
    assert [
        tool["name"]
        for tool in tools
        if "workspace" not in tool["inputSchema"].get("required", [])
    ] == ["server_status", "server_stop"]


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


def test_normal_when_relative_path_with_session(
    tmp_path: Path, make_workspace: MakeWorkspace, make_item: MakeItem, start_server: StartServer
) -> None:
    """2 つのクライアントが別々の作業フォルダを `session` で渡すと、同じ相対パスがそれぞれの作業フォルダのワークスペースを指す（正常系）。"""
    # 準備
    make_workspace(make_item("D-1"), name="a/talk")
    make_workspace(make_item("D-2"), name="b/talk")
    server = start_server()
    first = server.client
    second = server.connect()
    # 実行
    first_result = first.call("status", workspace="talk", session={"cwd": str(tmp_path / "a")})
    second_result = second.call("status", workspace="talk", session={"cwd": str(tmp_path / "b")})
    # 検証
    assert first_result.is_error is False, first_result.text
    assert ("D-1" in first_result.text, "D-2" in first_result.text) == (True, False)
    assert second_result.is_error is False, second_result.text
    assert ("D-1" in second_result.text, "D-2" in second_result.text) == (False, True)


def test_normal_when_relative_path_without_session(
    tmp_path: Path, make_workspace: MakeWorkspace, make_item: MakeItem, start_server: StartServer
) -> None:
    """`session` を渡さずに相対パスを渡すと、引数の誤りのツールのエラーで返す（正常系）。"""
    # 準備
    make_workspace(make_item("D-1"), name="talk")
    server = start_server(cwd=tmp_path)
    # 実行
    result = server.call("status", workspace="talk")
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: 引数の誤り: workspace: ")
    assert "絶対パスで渡してください" in result.text
    assert "D-1" not in result.text


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
    items = yaml.safe_load((root / RECORD_DIR / "decisions.yaml").read_text(encoding="utf-8"))[
        "items"
    ]
    assert [item["id"] for item in items] == [f"D-{number}" for number in range(1, 41)]


def test_normal_when_sigterm(
    tmp_path: Path, make_workspace: MakeWorkspace, start_server: StartServer
) -> None:
    """SIGTERM を受けると、終了時のフックを呼び、配信を止めて終わる（正常系）。"""
    # 準備
    root = make_workspace(name="家計簿")
    record = tmp_path / "stop-hook.txt"
    server = start_server(extra_env={STOP_HOOK_ENV: recording_hook(record)})
    url = server.call("preview_url", workspace=str(root)).data["url"]
    port = int(url.split(":")[2].split("/")[0])
    # 実行
    server.process.send_signal(signal.SIGTERM)
    exit_code = server.wait_exit()
    # 検証
    assert exit_code == 0
    assert is_listening(server.port) is False
    with pytest.raises(OSError, match=r"."):
        http_request(url)
    assert read_settled_hook_lines(record) == [f"{port} 家計簿"]
    assert read_hook_lines(record) == [f"{port} 家計簿"]


def test_normal_when_client_disconnects(
    make_workspace: MakeWorkspace, start_server: StartServer
) -> None:
    """プレビューの URL を受けたクライアントが切れても、常駐サーバーと配信は止まらない（正常系）。"""
    # 準備
    root = make_workspace()
    server = start_server()
    url = server.call("preview_url", workspace=str(root)).data["url"]
    # 実行
    server.client.close()
    page = http_request(url, PREVIEW_PAGE)
    # 検証
    assert server.process.poll() is None
    assert read_server_status(server.port) is not None
    assert page.status == 200


def test_error_when_port_in_use() -> None:
    """`MINDSTELLA_PORT` のポートで待ち受けられないと、使われているポートを示して終わる（異常系）。"""
    # 準備
    port = free_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as holder:
        holder.bind((LISTEN_HOST, port))
        holder.listen()
        # 実行
        completed = _run_server(str(port))
        # 検証
        assert completed.returncode == 1
        assert f"ポート {port} は別のプロセスが使っています" in completed.stderr
        assert "MINDSTELLA_PORT で別のポートを渡してください" in completed.stderr
        assert is_listening(port) is True


def test_error_when_port_invalid() -> None:
    """`MINDSTELLA_PORT` が 1〜65535 の整数でないと、値を示して終わる（異常系）。"""
    # 実行
    completed = _run_server("abc")
    # 検証
    assert completed.returncode == 1
    assert "MINDSTELLA_PORT の値 abc は誤りです" in completed.stderr
