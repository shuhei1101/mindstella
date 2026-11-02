"""常駐サーバーの起動と停止（Claude Code を立ち上げたときに落ちていた常駐の MCP サーバーが起動し、並行するセッションが 1 つの常駐サーバーを共有する）の E2E テスト。

本物の Claude Code は立ち上げず、SessionStart のフックが叩く起動の処理（`ensure_server.py --hook`）を叩き、
MCP のクライアントで常駐サーバーの `/mcp` につなぐ。待ち受けのポートはテストごとの空きポートを `MINDSTELLA_PORT` で渡す。
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from external_access_helpers import read_settled_hook_lines, recording_hook
from launch_fixtures import PLUGIN_DIR, read_tool_names
from workspace_fixtures import (
    LISTEN_HOST,
    MCP_PATH,
    PORT_ENV,
    MakeItem,
    MakeWorkspace,
    McpClient,
    is_listening,
    read_server_status,
)

# 常駐サーバーの入口と、SessionStart のフックが呼ぶ起動の確認のスクリプト
SERVER_SCRIPT = PLUGIN_DIR / "skills" / "mindmap" / "scripts" / "server.py"
ENSURE_SCRIPT = PLUGIN_DIR / "skills" / "mindmap" / "scripts" / "ensure_server.py"

# 起動の確認・常駐サーバー 1 回を待つ上限秒数（常駐サーバーが待ち受けるまでの上限 10 秒を含む）
COMMAND_TIMEOUT_SEC = 60

# 常駐サーバーを止めてから、プロセスが終わるのを待つ上限秒数と、確かめる間隔
STOP_WAIT_SEC = 10
POLL_INTERVAL_SEC = 0.1

# 終了時のフックを渡す環境変数
STOP_HOOK_ENV = "MINDSTELLA_PREVIEW_STOP_HOOK"

type RunHook = Callable[..., subprocess.CompletedProcess[str]]
type Connect = Callable[[], McpClient]


@pytest.fixture
def run_hook(tmp_path: Path, ready_venv: Path, resident_port: int) -> RunHook:
    """SessionStart のフックと同じく、システムの python3 で起動の確認を `--hook` で呼ぶ関数を返す。"""
    system_python = shutil.which("python3", path="/usr/bin:/bin")
    assert system_python is not None
    home = tmp_path / "home"
    home.mkdir()

    def _run(cwd: Path, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        """cwd を作業フォルダとした SessionStart のフックの入力を渡して起動の確認を呼び、終わるまで待つ。"""
        hook_input = json.dumps(
            {"hook_event_name": "SessionStart", "cwd": str(cwd), "source": "startup"}
        )
        env = {
            **os.environ,
            "HOME": str(home),
            "PYTHONUTF8": "1",
            PORT_ENV: str(resident_port),
            "MINDSTELLA_VENV": str(ready_venv),
            **(extra_env or {}),
        }
        return subprocess.run(
            [system_python, str(ENSURE_SCRIPT), "--hook"],
            input=hook_input,
            env=env,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=COMMAND_TIMEOUT_SEC,
            check=False,
        )

    return _run


@pytest.fixture
def connect(resident_port: int) -> Iterator[Connect]:
    """常駐サーバーの `/mcp` へ MCP のクライアントをつなぐ関数を返し、テストの後でつないだクライアントを閉じる。"""
    clients: list[McpClient] = []

    def _connect() -> McpClient:
        """クライアントを 1 つつないで返す。"""
        client = McpClient(f"http://{LISTEN_HOST}:{resident_port}{MCP_PATH}")
        clients.append(client)
        return client

    yield _connect
    for client in clients:
        client.close()


@pytest.fixture
def occupied_port(resident_port: int) -> Iterator[socket.socket]:
    """常駐サーバーに渡すポートを、テストが先に `127.0.0.1` で待ち受けて塞ぎ、テストの後で閉じる。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind((LISTEN_HOST, resident_port))
        listener.listen()
        yield listener


def _session(cwd: Path) -> dict[str, str]:
    """PreToolUse のフックが入れるセッションの値のうち、作業フォルダだけを持つものを返す。"""
    return {"cwd": str(cwd)}


def _preview_port(client: McpClient, root: Path) -> int:
    """root を作業フォルダとしたセッションでプレビューの URL を取得し、配信のポートを返す。"""
    served = client.call("preview_url", workspace=".", session=_session(root))
    assert served.data is not None, served.text
    port = urlsplit(str(served.data["url"])).port
    assert port is not None
    return port


def _wait_ended(pid: int) -> bool:
    """プロセスが終わるまで待ち、終わったかを返す（Linux の /proc）。"""
    deadline = time.monotonic() + STOP_WAIT_SEC
    while Path(f"/proc/{pid}").exists() and time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL_SEC)
    return not Path(f"/proc/{pid}").exists()


def test_normal(tmp_path: Path, resident_port: int, run_hook: RunHook, connect: Connect) -> None:
    """常駐サーバーが落ちていれば、SessionStart のフックが起動し、`/mcp` で mindstella のツールの一覧を返す（正常系）。"""
    # 実行
    hooked = run_hook(tmp_path)
    tools = [tool["name"] for tool in connect().list_tools()]
    # 検証
    # 常駐サーバーが 127.0.0.1 の MINDSTELLA_PORT のポートで /mcp を待ち受けている
    status = read_server_status(resident_port)
    assert status is not None
    assert (status["name"], status["port"]) == ("mindstella", resident_port)
    # MCP のクライアントでつなぐと、mindstella のツールの一覧が返る
    assert tools == read_tool_names(SERVER_SCRIPT)
    # フックが 0 の終了コードで終わり、Claude Code の立ち上げを止めない
    assert hooked.returncode == 0, hooked.stdout + hooked.stderr


def test_normal_when_two_sessions(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    resident_port: int,
    run_hook: RunHook,
    connect: Connect,
) -> None:
    """2 つ目の Claude Code を立ち上げても常駐サーバーは 1 つのままで、2 つのセッションがそれぞれの作業フォルダのワークスペースを扱う（正常系）。"""
    # 準備
    first_root = make_workspace(make_item("D-1"), name="a")
    second_root = make_workspace(make_item("D-2"), name="b")
    first_hook = run_hook(first_root)
    assert first_hook.returncode == 0, first_hook.stdout + first_hook.stderr
    before = read_server_status(resident_port)
    assert before is not None
    first_client = connect()
    # 実行
    second_hook = run_hook(second_root)
    second_client = connect()
    first_status = first_client.call("status", workspace=".", session=_session(first_root))
    second_status = second_client.call("status", workspace=".", session=_session(second_root))
    # 検証
    # 常駐サーバーのプロセスが 1 つのまま
    assert second_hook.returncode == 0, second_hook.stdout + second_hook.stderr
    after = read_server_status(resident_port)
    assert after is not None
    assert after["pid"] == before["pid"]
    # フォルダ A のセッションが受けた状況が D-1 を持ち、D-2 を持たない
    first_text = json.dumps(first_status.data, ensure_ascii=False)
    assert ("D-1" in first_text, "D-2" in first_text) == (True, False)
    # フォルダ B のセッションが受けた状況が D-2 を持ち、D-1 を持たない
    second_text = json.dumps(second_status.data, ensure_ascii=False)
    assert ("D-2" in second_text, "D-1" in second_text) == (True, False)


def test_normal_when_status_checked(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    resident_port: int,
    run_hook: RunHook,
    connect: Connect,
) -> None:
    """常駐サーバーの状態に、待ち受けのポートと、配信しているワークスペースごとのポートがある（正常系）。"""
    # 準備
    first_root = make_workspace(make_item("D-1"), name="a")
    second_root = make_workspace(make_item("D-2"), name="b")
    hooked = run_hook(first_root)
    assert hooked.returncode == 0, hooked.stdout + hooked.stderr
    client = connect()
    first_port = _preview_port(client, first_root)
    second_port = _preview_port(client, second_root)
    # 実行
    result = client.call("server_status")
    # 検証
    assert result.is_error is False, result.text
    assert result.data is not None
    # 状態に、MINDSTELLA_PORT のポートがある
    assert result.data["port"] == resident_port
    # 状態に、フォルダ A と B のそれぞれの配信のポートがある
    assert result.data["previews"] == [
        {"workspace": str(first_root), "port": first_port},
        {"workspace": str(second_root), "port": second_port},
    ]


def test_normal_when_stopped(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    resident_port: int,
    run_hook: RunHook,
    connect: Connect,
) -> None:
    """常駐サーバーを止めると、配信ごとに終了時のフックを呼び、全ての配信を止めて終わる（正常系）。"""
    # 準備
    first_root = make_workspace(make_item("D-1"), name="a")
    second_root = make_workspace(make_item("D-2"), name="b")
    record = tmp_path / "stop-hook.txt"
    hooked = run_hook(first_root, {STOP_HOOK_ENV: recording_hook(record)})
    assert hooked.returncode == 0, hooked.stdout + hooked.stderr
    status = read_server_status(resident_port)
    assert status is not None
    client = connect()
    first_port = _preview_port(client, first_root)
    second_port = _preview_port(client, second_root)
    # 実行
    stopped = client.call("server_stop")
    ended = _wait_ended(int(status["pid"]))
    # 検証
    assert stopped.is_error is False, stopped.text
    # 終了時のフックが、フォルダ A と B の配信ごとに 1 回ずつ呼ばれている
    assert sorted(read_settled_hook_lines(record, count=2)) == sorted(
        [f"{first_port} a", f"{second_port} b"]
    )
    # 常駐サーバーのプロセスと、配信のポートの待ち受けが残っていない
    assert ended is True
    assert [is_listening(port) for port in (resident_port, first_port, second_port)] == [
        False,
        False,
        False,
    ]


@pytest.mark.usefixtures("occupied_port")
def test_error_when_port_in_use(
    tmp_path: Path, ready_venv: Path, resident_port: int, run_hook: RunHook
) -> None:
    """待ち受けのポートが使われていると、常駐サーバーは使われているポートを示して終わり、フックは Claude Code の立ち上げを止めない（異常系）。"""
    # 実行
    server = subprocess.run(
        [str(ready_venv / "bin" / "python"), str(SERVER_SCRIPT)],
        env={**os.environ, "PYTHONUTF8": "1", PORT_ENV: str(resident_port)},
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=COMMAND_TIMEOUT_SEC,
        check=False,
    )
    hooked = run_hook(tmp_path)
    # 検証
    # 常駐サーバーが 1 の終了コードで終わり、出力に使われているポートがある
    assert server.returncode == 1
    assert f"ポート {resident_port}" in server.stdout + server.stderr
    # フックが 0 の終了コードで終わる
    assert hooked.returncode == 0
    # ポートを先に待ち受けていた側が、そのまま待ち受けている
    assert is_listening(resident_port) is True
