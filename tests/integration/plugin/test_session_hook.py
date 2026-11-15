"""MindStella のセッションのフック（session_hook.py）の結合テスト。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
from session_fixtures import HOOK_SCRIPT, SYSTEM_PATH
from workspace_fixtures import LISTEN_HOST, free_port

# フック 1 回を待つ上限秒数
HOOK_TIMEOUT_SEC = 30

# MindStella のセッションの ID と進め方の文書
SESSION_ID = "S-0123456789ab"
FLOW = "aituber#flow-script"


class _Recorder:
    """受けた要求を記録して 200 を返す、常駐サーバーの代わりの HTTP のサーバー。"""

    def __init__(self) -> None:
        """空きポートで待ち受ける。"""
        self.received: list[tuple[str, Any]] = []
        recorder = self

        class Handler(BaseHTTPRequestHandler):
            """経路と本文を記録する。"""

            def do_POST(self) -> None:
                """記録して 200 を返す。"""
                length = int(self.headers.get("Content-Length") or 0)
                recorder.received.append((self.path, json.loads(self.rfile.read(length))))
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *args: object) -> None:
                """記録を出さない。"""

        self.server = ThreadingHTTPServer((LISTEN_HOST, 0), Handler)
        self.port = int(self.server.server_address[1])
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


@pytest.fixture
def recorder() -> Iterator[_Recorder]:
    """常駐サーバーの代わりを立て、テストの後で止める。"""
    started = _Recorder()
    yield started
    started.server.shutdown()
    started.server.server_close()


def _run(event: str, port: int, *, with_session: bool = True) -> subprocess.CompletedProcess[str]:
    """システムの python3 でフックを呼ぶ。"""
    python = shutil.which("python3", path=SYSTEM_PATH)
    assert python is not None
    env = {
        "PATH": SYSTEM_PATH,
        "HOME": os.environ.get("HOME", "/tmp"),
        "MINDSTELLA_PORT": str(port),
        "TMUX_PANE": "%3",
    }
    if with_session:
        env.update({"MINDSTELLA_SESSION": SESSION_ID, "MINDSTELLA_FLOW": FLOW})
    return subprocess.run(
        [python, str(HOOK_SCRIPT), event],
        input=json.dumps({"session_id": "c-1", "source": "startup"}),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=HOOK_TIMEOUT_SEC,
        check=False,
    )


def test_normal(recorder: _Recorder) -> None:
    """SessionStart で出来事を送り、進め方の文書の場所を注入する（正常系）。"""
    # 実行
    completed = _run("session-start", recorder.port)
    # 検証
    assert completed.returncode == 0, completed.stderr
    path, body = recorder.received[0]
    assert path == f"/_admin/sessions/{SESSION_ID}/events"
    assert (body["event"], body["claude_session_id"], body["pane"], body["source"]) == (
        "session_start",
        "c-1",
        "%3",
        "startup",
    )
    output = json.loads(completed.stdout)
    assert FLOW in output["hookSpecificOutput"]["additionalContext"]


def test_normal_when_ordinary_session(recorder: _Recorder) -> None:
    """MINDSTELLA_SESSION が無ければ何もしない（正常系）。"""
    # 実行
    completed = _run("session-start", recorder.port, with_session=False)
    # 検証
    assert (completed.returncode, completed.stdout) == (0, "")
    assert recorder.received == []


def test_error_when_server_down() -> None:
    """常駐サーバーへつながらなければ、標準エラーに 1 行書いて終了コード 0（異常系）。"""
    # 実行
    completed = _run("stop", free_port())
    # 検証
    assert completed.returncode == 0
    assert "[mindstella]" in completed.stderr
