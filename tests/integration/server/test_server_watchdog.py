"""テストが起動した常駐サーバーを、pytest のプロセスが無くなったら止める見張り（tests/server_watchdog.py）の結合テスト。

pytest の代わりの親と、常駐サーバーの代わりの子を眠るだけのプロセスで起動し、見張りを実際に切り離して起動する。
"""

from __future__ import annotations

import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from server_watchdog import POLL_SEC, TERM_WAIT_SEC, spawn
from workspace_fixtures import McpServer

# 眠り続けるだけのプロセス（SIGTERM を受けると終わる）
SLEEPER = [sys.executable, "-c", "import time; time.sleep(3600)"]

# SIGTERM を無視して眠り続けるプロセス
TERM_IGNORING_SLEEPER = [sys.executable, "-c", "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(3600)"]

# 子のプロセスを 1 つ起動し、その PID を記載してから眠るプロセス（常駐サーバーが子を持つ場合）
PARENT_OF_SLEEPER = [
    sys.executable,
    "-c",
    "import subprocess, sys, time; child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(3600)']); "
    "open(sys.argv[1], 'w').write(str(child.pid)); time.sleep(3600)",
]

# 見張りが止めるまで待つ上限（秒）。確認の間隔の 2 回分と、SIGKILL までの待ちを合わせた長さ
STOP_TIMEOUT_SEC = POLL_SEC * 2 + TERM_WAIT_SEC + POLL_SEC * 2

# 生きているかを確認する間隔（秒）
CHECK_SEC = 0.1


def _alive(pid: int) -> bool:
    """プロセスが残っていて、ゾンビでないか。"""
    status = Path(f"/proc/{pid}/status")
    return status.exists() and "zombie" not in status.read_text(encoding="utf-8")


def _wait_gone(pid: int, timeout: float) -> bool:
    """プロセスが無くなるまで待ち、上限までに無くなったかを返却する。"""
    deadline = time.monotonic() + timeout
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(CHECK_SEC)
    return not _alive(pid)


def _wait_file(path: Path, timeout: float) -> str:
    """ファイルに中身が記載されるまで待ち、中身を返却する。"""
    deadline = time.monotonic() + timeout
    while (not path.exists() or not path.read_text(encoding="utf-8")) and time.monotonic() < deadline:
        time.sleep(CHECK_SEC)
    return path.read_text(encoding="utf-8")


@pytest.fixture
def processes() -> Iterator[list[subprocess.Popen[bytes]]]:
    """テストで起動したプロセスを集め、終わりに残っていれば止める。"""
    started: list[subprocess.Popen[bytes]] = []
    yield started
    for process in started:
        if process.poll() is None:
            process.kill()
            process.wait()


def _start(processes: list[subprocess.Popen[bytes]], command: list[str], *, detached: bool) -> subprocess.Popen[bytes]:
    """プロセスを起動して後片付けの対象に加える。"""
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, start_new_session=detached)
    processes.append(process)
    return process


def test_normal_when_parent_killed(processes: list[subprocess.Popen[bytes]]) -> None:
    """親（pytest）が SIGKILL で終わると、同じプロセスグループの常駐サーバーへ SIGTERM を送信して止める（正常系）。"""
    # 準備
    parent = _start(processes, SLEEPER, detached=False)
    server = _start(processes, SLEEPER, detached=False)
    watchdog = spawn(server.pid, parent=parent.pid)
    processes.append(watchdog)
    # 実行
    parent.send_signal(signal.SIGKILL)
    parent.wait()
    # 検証
    assert server.wait(timeout=STOP_TIMEOUT_SEC) == -signal.SIGTERM
    assert watchdog.wait(timeout=STOP_TIMEOUT_SEC) == 0


def test_normal_when_server_detached(processes: list[subprocess.Popen[bytes]], tmp_path: Path) -> None:
    """切り離して起動した常駐サーバーは、親が終わるとその子のプロセスごと止める（正常系）。"""
    # 準備
    child_pid_file = tmp_path / "child.pid"
    parent = _start(processes, SLEEPER, detached=False)
    server = _start(processes, [*PARENT_OF_SLEEPER, str(child_pid_file)], detached=True)
    child_pid = int(_wait_file(child_pid_file, STOP_TIMEOUT_SEC))
    processes.append(spawn(server.pid, parent=parent.pid))
    # 実行
    parent.kill()
    parent.wait()
    # 検証
    assert server.wait(timeout=STOP_TIMEOUT_SEC) == -signal.SIGTERM
    assert _wait_gone(child_pid, STOP_TIMEOUT_SEC) is True


def test_normal_when_term_ignored(processes: list[subprocess.Popen[bytes]]) -> None:
    """SIGTERM で終わらない常駐サーバーは、待つ上限を過ぎたら SIGKILL で止める（正常系）。"""
    # 準備
    parent = _start(processes, SLEEPER, detached=False)
    server = _start(processes, TERM_IGNORING_SLEEPER, detached=True)
    processes.append(spawn(server.pid, parent=parent.pid))
    # 実行
    parent.kill()
    parent.wait()
    # 検証
    assert server.wait(timeout=STOP_TIMEOUT_SEC) == -signal.SIGKILL


def test_normal_when_server_stopped_first(processes: list[subprocess.Popen[bytes]]) -> None:
    """常駐サーバーが先に止まれば（テストの後片付け）、見張りは親に触れずに終わる（正常系）。"""
    # 準備
    parent = _start(processes, SLEEPER, detached=False)
    server = _start(processes, SLEEPER, detached=False)
    watchdog = spawn(server.pid, parent=parent.pid)
    processes.append(watchdog)
    # 実行
    server.terminate()
    server.wait()
    # 検証
    assert watchdog.wait(timeout=STOP_TIMEOUT_SEC) == 0
    assert parent.poll() is None


def _watchdog_targets() -> list[str]:
    """動いている見張りのプロセスが見張る常駐サーバーの PID を返却する。"""
    targets: list[str] = []
    for cmdline in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            args = cmdline.read_bytes().split(b"\0")
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if any(arg.endswith(b"server_watchdog.py") for arg in args):
            targets.append(args[-2].decode())
    return targets


def test_normal_when_mcp_server(mcp_server: McpServer) -> None:
    """テストの常駐サーバー（McpServer）を起動すると、その PID の見張りが動いている（正常系）。"""
    # 準備・実行（fixture が常駐サーバーを起動する）
    # 検証
    assert str(mcp_server.process.pid) in _watchdog_targets()
