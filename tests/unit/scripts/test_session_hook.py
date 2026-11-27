"""session_hook.py（MindStella のセッションのフック）の単体テスト。"""

from __future__ import annotations

import io
import json
import threading
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

import session_hook

# 常駐サーバーのポート（post を差し替えるテストでは使わない）
PORT = 8784

# MindStella のセッションの環境変数
ENVIRON = {
    "MINDSTELLA_SESSION": "S-0123456789ab",
    "MINDSTELLA_PORT": str(PORT),
    "TMUX_PANE": "%3",
    "TMUX": "/tmp/tmux-1000/default,123,0",
}

# 再開の状況として返す注入文
CONTEXT = "再開しました。取り込み待ちのコメントが 1 件あります。mindstella/startup を参照して先に進めてください。"

type ServeJson = Callable[[dict[str, Any]], tuple[int, list[tuple[str, Any]]]]


@pytest.fixture
def serve_json() -> Iterator[ServeJson]:
    """受けた経路と本文を記録し、決めた JSON を 200 で返す HTTP のサーバーを空きポートで立てる関数を返す。"""
    servers: list[ThreadingHTTPServer] = []

    def _serve(response: dict[str, Any]) -> tuple[int, list[tuple[str, Any]]]:
        """サーバーを立て、ポートと受けた要求の記録を返す。"""
        received: list[tuple[str, Any]] = []
        payload = json.dumps(response).encode("utf-8")

        class Handler(BaseHTTPRequestHandler):
            """受けた経路と本文を記録して 200 を返す。"""

            def do_POST(self) -> None:
                """記録して 200 を返す。"""
                length = int(self.headers.get("Content-Length") or 0)
                received.append((self.path, json.loads(self.rfile.read(length))))
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args: object) -> None:
                """記録を出さない。"""

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return server.server_address[1], received

    yield _serve
    for server in servers:
        server.shutdown()
        server.server_close()


def _resume_status(**changes: Any) -> dict[str, Any]:
    """注入文と until_seq を持ち、超えた件数が 0 の再開の状況に渡したキーを重ねて返す。"""
    status: dict[str, Any] = {
        "trigger": "resume",
        "awaiting_threads": 1,
        "changed_more": 0,
        "removed_more": 0,
        "until_seq": 7,
        "context": CONTEXT,
    }
    status.update(changes)
    return status


def _context_of(stdout: io.StringIO) -> str:
    """標準出力の JSON から additionalContext を取り出す。"""
    return json.loads(stdout.getvalue())["hookSpecificOutput"]["additionalContext"]


def test_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SessionStart で設定のフォルダとともに送り、状況を注入してから時点を進める（正常系）。"""
    # 準備
    monkeypatch.setenv("HOME", str(tmp_path))
    calls: list[tuple[str, Any]] = []
    stdout = io.StringIO()

    def _advance(port: int, session: str, until_seq: int) -> None:
        """時点を進めた順と、その時点で書き終えていた標準出力を控える。"""
        calls.append(("advance", (until_seq, stdout.getvalue())))

    # 実行
    code = session_hook.main(
        ["session-start"],
        environ={**ENVIRON, "HOME": str(tmp_path), "CLAUDE_CONFIG_DIR": "~/c"},
        stdin=io.StringIO(json.dumps({"session_id": "c1", "source": "compact"})),
        stdout=stdout,
        post=lambda port, session, body: calls.append(("post", body)),
        resume=lambda port, session, source: calls.append(("resume", source)) or _resume_status(),
        advance=_advance,
    )
    # 検証
    assert code == 0
    assert [name for name, _value in calls] == ["post", "resume", "advance"]
    body = calls[0][1]
    assert body["event"] == "session_start"
    assert body["claude_session_id"] == "c1"
    assert body["source"] == "compact"
    assert body["pane"] == "%3"
    assert body["socket"] == "/tmp/tmux-1000/default"
    assert body["claude_config_dir"] == f"{tmp_path}/c"
    assert calls[1][1] == "compact"
    until_seq, written = calls[2][1]
    assert until_seq == 7
    assert json.loads(written)["hookSpecificOutput"]["additionalContext"] == CONTEXT


def test_main_without_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLAUDE_CONFIG_DIR が無ければ ~/.claude の絶対パスを送る（正常系）。"""
    # 準備
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    sent: list[tuple[int, str, dict[str, Any]]] = []
    # 実行
    session_hook.main(
        ["session-start"],
        environ={**ENVIRON, "HOME": str(tmp_path)},
        stdin=io.StringIO(json.dumps({"session_id": "c1", "source": "startup"})),
        stdout=io.StringIO(),
        post=lambda port, session, body: sent.append((port, session, body)),
        resume=lambda port, session, source: _resume_status(),
        advance=lambda port, session, until_seq: None,
    )
    # 検証
    assert sent[0][2]["claude_config_dir"] == f"{tmp_path}/.claude"


def test_main_ordinary_session() -> None:
    """MINDSTELLA_SESSION が無ければ何もしない（正常系）。"""
    # 準備
    calls: list[Any] = []
    stdout = io.StringIO()
    # 実行
    code = session_hook.main(
        ["session-start"],
        environ={"MINDSTELLA_PORT": str(PORT)},
        stdin=io.StringIO(json.dumps({"session_id": "c1", "source": "startup"})),
        stdout=stdout,
        post=lambda *args: calls.append(("post", args)),
        resume=lambda *args: calls.append(("resume", args)),
        advance=lambda *args: calls.append(("advance", args)),
    )
    # 検証
    assert code == 0
    assert calls == []
    assert stdout.getvalue() == ""


def test_main_server_down(capsys: pytest.CaptureFixture[str]) -> None:
    """送れなくても 0（異常系）。"""

    # 準備
    def fail(*_args: object) -> None:
        """つながらない送信。"""
        raise OSError("refused")

    # 実行
    code = session_hook.main(
        ["stop"],
        environ=ENVIRON,
        stdin=io.StringIO(json.dumps({"session_id": "c1"})),
        stdout=io.StringIO(),
        post=fail,
    )
    # 検証
    assert code == 0
    assert "[mindstella]" in capsys.readouterr().err


def test_main_when_resume_unavailable(capsys: pytest.CaptureFixture[str]) -> None:
    """状況を引けなければ状況なしで注入し、時点を進めない（正常系）。"""
    # 準備
    advanced: list[int] = []
    stdout = io.StringIO()

    def unavailable(*_args: object) -> dict[str, Any]:
        """つながらない再開の状況。"""
        raise OSError("refused")

    # 実行
    code = session_hook.main(
        ["session-start"],
        environ=ENVIRON,
        stdin=io.StringIO(json.dumps({"session_id": "c1", "source": "compact"})),
        stdout=stdout,
        post=lambda *_args: None,
        resume=unavailable,
        advance=lambda port, session, until_seq: advanced.append(until_seq),
    )
    # 検証
    assert code == 0
    assert _context_of(stdout) == session_hook.fallback_context("compact", None)
    assert advanced == []
    assert "[mindstella]" in capsys.readouterr().err


def test_main_when_changes_overflow() -> None:
    """収まらない変更があれば時点を進めない（正常系）。"""
    # 準備
    advanced: list[int] = []
    stdout = io.StringIO()
    # 実行
    code = session_hook.main(
        ["session-start"],
        environ=ENVIRON,
        stdin=io.StringIO(json.dumps({"session_id": "c1", "source": "compact"})),
        stdout=stdout,
        post=lambda *_args: None,
        resume=lambda *_args: _resume_status(changed_more=5),
        advance=lambda port, session, until_seq: advanced.append(until_seq),
    )
    # 検証
    assert code == 0
    assert advanced == []
    assert _context_of(stdout) == CONTEXT


def test_main_when_fork() -> None:
    """fork では注入しない（正常系）。"""
    # 準備
    calls: list[str] = []
    stdout = io.StringIO()
    # 実行
    code = session_hook.main(
        ["session-start"],
        environ=ENVIRON,
        stdin=io.StringIO(json.dumps({"session_id": "c1", "source": "fork"})),
        stdout=stdout,
        post=lambda *_args: calls.append("post"),
        resume=lambda *_args: calls.append("resume") or _resume_status(),
        advance=lambda *_args: calls.append("advance"),
    )
    # 検証
    assert code == 0
    assert calls == ["post"]
    assert stdout.getvalue() == ""


def test_post_event(serve_json: ServeJson) -> None:
    """経路と本文（正常系）。"""
    # 準備
    port, received = serve_json({})
    # 実行
    session_hook.post_event(port, "S-1", {"event": "stop"})
    # 検証
    assert received == [("/_admin/sessions/S-1/events", {"event": "stop"})]


def test_request_resume(serve_json: ServeJson) -> None:
    """経路と本文（正常系）。"""
    # 準備
    port, received = serve_json({"trigger": "resume"})
    # 実行
    result = session_hook.request_resume(port, "S-1", "compact")
    # 検証
    assert received == [("/_admin/sessions/S-1/resume", {"source": "compact"})]
    assert result == {"trigger": "resume"}


def test_post_read_point(serve_json: ServeJson) -> None:
    """経路と本文（正常系）。"""
    # 準備
    port, received = serve_json({"read_seq": 7})
    # 実行
    session_hook.post_read_point(port, "S-1", 7)
    # 検証
    assert received == [("/_admin/sessions/S-1/read_point", {"until_seq": 7})]


@pytest.mark.parametrize(
    ("source", "flow", "contained", "absent"),
    [
        pytest.param(
            "compact",
            "src#doc",
            ["再開", "src#doc", "mindstella/startup"],
            ["/mindstella:"],
            id="resume_flow",
        ),
        pytest.param(
            "startup",
            None,
            ["起動", "mindstella/startup"],
            ["進め方の文書", "/mindstella:"],
            id="startup",
        ),
    ],
)
def test_fallback_context(
    source: str, flow: str | None, contained: list[str], absent: list[str]
) -> None:
    """契機と進め方の文書を埋める（正常系）。"""
    # 実行
    result = session_hook.fallback_context(source, flow)
    # 検証
    assert all(word in result for word in contained)
    assert not any(word in result for word in absent)


def test_main_when_rate_limit() -> None:
    """stop-failure で error を送る（正常系）。"""
    # 準備
    sent: list[dict[str, Any]] = []
    stdout = io.StringIO()
    # 実行
    code = session_hook.main(
        ["stop-failure"],
        environ=ENVIRON,
        stdin=io.StringIO(json.dumps({"session_id": "c1", "error": "rate_limit"})),
        stdout=stdout,
        post=lambda _port, _session, body: sent.append(body),
    )
    # 検証
    assert code == 0
    assert [(body["event"], body.get("error")) for body in sent] == [("stop_failure", "rate_limit")]
    assert stdout.getvalue() == ""


def _refuse(_port: int, _session: str, _body: dict[str, Any]) -> None:
    """つながらない常駐サーバー。"""
    raise OSError("connection refused")


def test_main_when_pre_compact() -> None:
    """pre-compact の出来事は受け付けず、圧縮を止めない（異常系）。"""
    # 準備
    stdout = io.StringIO()
    sent: list[dict[str, Any]] = []
    # 実行
    with pytest.raises(SystemExit) as caught:
        session_hook.main(
            ["pre-compact"],
            environ=ENVIRON,
            stdin=io.StringIO(json.dumps({"session_id": "c1", "trigger": "auto"})),
            stdout=stdout,
            post=lambda _port, _session, body: sent.append(body),
        )
    # 検証
    assert caught.value.code == 2
    assert stdout.getvalue() == ""
    assert sent == []


@pytest.mark.parametrize(
    ("environ", "expected"),
    [
        pytest.param(
            {
                "OTEL_RESOURCE_ATTRIBUTES": "ai_monitor_project=x,claude_balancer.client=mindstella,"
                "claude_balancer.account=sub6,claude_balancer.lease_id=l"
            },
            "sub6",
            id="account",
        ),
        pytest.param(
            {"OTEL_RESOURCE_ATTRIBUTES": "claude_balancer.client=mindstella"}, None, id="no-item"
        ),
        pytest.param({}, None, id="no-variable"),
        pytest.param({"OTEL_RESOURCE_ATTRIBUTES": "claude_balancer.account="}, None, id="empty"),
    ],
)
def test_balancer_account_from(environ: dict[str, str], expected: str | None) -> None:
    """OTEL_RESOURCE_ATTRIBUTES からアカウント名を取り出す（正常系）。"""
    # 実行
    result = session_hook.balancer_account_from(environ)
    # 検証
    assert result == expected


def test_main_when_balancer_account(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SessionStart で借りたアカウント名を balancer_account で送る（正常系）。"""
    # 準備
    monkeypatch.setenv("HOME", str(tmp_path))
    sent: list[dict[str, Any]] = []
    # 実行
    session_hook.main(
        ["session-start"],
        environ={
            **ENVIRON,
            "HOME": str(tmp_path),
            "OTEL_RESOURCE_ATTRIBUTES": "claude_balancer.account=sub6",
        },
        stdin=io.StringIO(json.dumps({"session_id": "c1", "source": "startup"})),
        stdout=io.StringIO(),
        post=lambda port, session, body: sent.append(body),
        resume=lambda port, session, source: _resume_status(),
        advance=lambda port, session, until_seq: None,
    )
    # 検証
    assert sent[0]["balancer_account"] == "sub6"
