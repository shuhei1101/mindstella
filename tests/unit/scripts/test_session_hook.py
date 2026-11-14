"""session_hook.py（MindStella のセッションのフック）の単体テスト。"""

from __future__ import annotations

import io
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import session_hook

# 常駐サーバーのポート（post を差し替えるテストでは使わない）
PORT = 8784

# MindStella のセッションの環境変数
ENVIRON = {
    "MINDSTELLA_SESSION": "S-0123456789ab",
    "MINDSTELLA_FLOW": "aituber#flow-1",
    "MINDSTELLA_PORT": str(PORT),
    "TMUX_PANE": "%3",
    "TMUX": "/tmp/tmux-1000/default,123,0",
}


def test_main() -> None:
    """SessionStart で出来事を送り、進め方の文書の場所を注入する。"""
    sent: list[tuple[int, str, dict[str, Any]]] = []
    stdout = io.StringIO()
    code = session_hook.main(
        ["session-start"],
        environ=ENVIRON,
        stdin=io.StringIO(json.dumps({"session_id": "c1", "source": "startup"})),
        stdout=stdout,
        post=lambda port, session, body: sent.append((port, session, body)),
    )
    assert code == 0
    assert sent[0][0] == PORT
    assert sent[0][1] == "S-0123456789ab"
    body = sent[0][2]
    assert body["event"] == "session_start"
    assert body["claude_session_id"] == "c1"
    assert body["source"] == "startup"
    assert body["pane"] == "%3"
    assert body["socket"] == "/tmp/tmux-1000/default"
    output = json.loads(stdout.getvalue())
    assert "aituber#flow-1" in output["hookSpecificOutput"]["additionalContext"]


def test_main_ordinary_session() -> None:
    """MINDSTELLA_SESSION が無ければ送らず、何も出さない。"""
    sent: list[Any] = []
    stdout = io.StringIO()
    code = session_hook.main(
        ["session-start"],
        environ={"MINDSTELLA_PORT": str(PORT)},
        stdin=io.StringIO(json.dumps({"session_id": "c1", "source": "startup"})),
        stdout=stdout,
        post=lambda *args: sent.append(args),
    )
    assert code == 0
    assert sent == []
    assert stdout.getvalue() == ""


def test_main_server_down(capsys: Any) -> None:
    """送れなくても 0 を返し、標準エラーに 1 行書く。"""

    def fail(*_args: object) -> None:
        """つながらない送信。"""
        raise OSError("refused")

    code = session_hook.main(
        ["stop"],
        environ=ENVIRON,
        stdin=io.StringIO(json.dumps({"session_id": "c1"})),
        stdout=io.StringIO(),
        post=fail,
    )
    assert code == 0
    assert "[mindstella]" in capsys.readouterr().err


def test_post_event() -> None:
    """経路と本文を送る。"""
    received: list[tuple[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        """受けた経路と本文を記録して 200 を返す。"""

        def do_POST(self) -> None:
            """記録して 200 を返す。"""
            length = int(self.headers.get("Content-Length") or 0)
            received.append((self.path, json.loads(self.rfile.read(length))))
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *args: object) -> None:
            """記録を出さない。"""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        session_hook.post_event(server.server_address[1], "S-1", {"event": "stop"})
    finally:
        server.shutdown()
        server.server_close()
    assert received == [("/_admin/sessions/S-1/events", {"event": "stop"})]
