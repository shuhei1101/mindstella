"""作業の完了の通知（応答の終わりに Discord の Webhook へ送信する）の結合テスト。"""

from __future__ import annotations

import json
import threading
import time
import urllib.parse
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from record_write_helpers import write_items
from session_fixtures import SessionWorld, wait_until
from workspace_fixtures import (
    LISTEN_HOST,
    MDMARK_COMMAND_ENV,
    NOOP_MDMARK_COMMAND,
    TEST_SESSION_ID,
    MakeItem,
    McpServer,
)

# Webhook の設定のファイルの場所を受ける環境変数
WEBHOOK_FILE_ENV = "MINDSTELLA_DISCORD_WEBHOOK_FILE"

# 送信しないことを確認するときに、送信のスレッドを待つ秒数
NO_SEND_WAIT_SEC = 1.0

# 送信を待つ上限（10 秒）より長く応答しない Mock の待ち秒数
SLOW_RESPONSE_SEC = 15.0

# 上限を過ぎた失敗の記録を待つ秒数（上限 10 秒に余裕を足す）
TIMEOUT_LOG_WAIT_SEC = 20.0

# stop の応答が送信を待たずに返ったとみなす秒数
QUICK_RESPONSE_SEC = 3.0


@dataclass
class FakeWebhook:
    """Discord の Webhook の Mock。受けた要求を記録し、決めたステータスを返却する。"""

    status: int = 200
    delay_sec: float = 0.0
    requests: list[dict[str, Any]] = field(default_factory=list)
    server: ThreadingHTTPServer | None = None

    @property
    def url(self) -> str:
        """Webhook の URL（Discord と同じく ID とトークンをパスに持つ）。"""
        assert self.server is not None
        return f"http://{LISTEN_HOST}:{self.server.server_address[1]}/api/webhooks/1/secret-token"

    def start(self) -> None:
        """空きポートで待ち受ける。"""
        fake = self

        class Handler(BaseHTTPRequestHandler):
            """要求を記録して応答する。"""

            def do_POST(self) -> None:
                """本文とクエリとヘッダーを記録し、決めたステータスを返却する。"""
                length = int(self.headers.get("Content-Length") or 0)
                parsed = urllib.parse.urlsplit(self.path)
                fake.requests.append(
                    {
                        "query": urllib.parse.parse_qs(parsed.query),
                        "body": json.loads(self.rfile.read(length) or b"{}"),
                        "user_agent": self.headers.get("User-Agent"),
                    }
                )
                time.sleep(fake.delay_sec)
                data = b"{}"
                self.send_response(fake.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args: object) -> None:
                """記録を出さない。"""

        self.server = ThreadingHTTPServer((LISTEN_HOST, 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        """待ち受けを閉じる。"""
        assert self.server is not None
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def webhook() -> Iterator[FakeWebhook]:
    """200 を返却する Webhook の Mock を起動し、テストの後で閉じる。"""
    fake = FakeWebhook()
    fake.start()
    yield fake
    fake.close()


def _start(world: SessionWorld, webhook: FakeWebhook | None) -> McpServer:
    """Webhook の URL を記載した設定のファイルを指定して（webhook が None なら指定せずに）常駐サーバーを起動する。"""
    extra = {MDMARK_COMMAND_ENV: NOOP_MDMARK_COMMAND}
    if webhook is not None:
        path = world.root / "webhook.ini"
        path.write_text(f"{webhook.url}\n", encoding="utf-8")
        extra[WEBHOOK_FILE_ENV] = str(path)
    return world.start(extra)


def _prepare(world: SessionWorld, server: McpServer) -> Path:
    """ワークスペースと MindStella のセッションの状態を作り、ワークスペースのフォルダを返す。"""
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(
        workspace_id, session=TEST_SESSION_ID, claude_session_id="c-mindstella-test"
    )
    return world.folder()


def _event(world: SessionWorld, name: str, **extra: object) -> tuple[int, dict[str, Any]]:
    """MindStella のセッションの出来事を送信する。"""
    body: dict[str, object] = {"event": name, "claude_session_id": "c-mindstella-test", **extra}
    return world.api("POST", f"/_admin/sessions/{TEST_SESSION_ID}/events", body)


def _new_thread(server: McpServer, root: Path) -> str:
    """MindStella のセッションとしてスレッドを作成し、ID を返却する。"""
    result = server.call("new_thread", workspace=str(root), body="質問です", summary="質問")
    assert result.is_error is False, result.text
    assert result.data is not None
    return str(result.data["id"])


def test_normal(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """応答の間に AI がスレッドに返信したので、応答の終わりに 1 件送信する（正常系）。"""
    # 準備
    world = session_world
    server = _start(world, webhook)
    root = _prepare(world, server)
    page_url = server.call("preview_url", workspace=str(root)).data["url"]
    thread_id = _new_thread(server, root)
    # 実行
    _event(world, "prompt_submit")
    replied = server.call(
        "reply", workspace=str(root), id=thread_id, body="回答します", summary="質問"
    )
    status, body = _event(world, "stop")
    wait_until(lambda: webhook.requests)
    # 検証
    assert replied.is_error is False, replied.text
    assert (status, body) == (200, {"recorded": True})
    assert len(webhook.requests) == 1
    assert webhook.requests[0]["query"] == {"wait": ["true"]}
    assert webhook.requests[0]["body"] == {"content": f"家計簿: 作業が完了しました\n{page_url}"}
    assert (
        webhook.requests[0]["user_agent"]
        == "DiscordBot (https://github.com/shuhei1101/mindstella, 1.0)"
    )
    log = wait_until(
        lambda: "Webhook への送信が成功した" in server.stderr_text() and server.stderr_text()
    )
    assert "secret-token" not in log
    assert webhook.url not in log


def test_normal_when_commit_only(
    session_world: SessionWorld, webhook: FakeWebhook, make_item: MakeItem
) -> None:
    """応答の間に AI が commit だけしたときも 1 件送信する（正常系）。"""
    # 準備
    world = session_world
    server = _start(world, webhook)
    root = _prepare(world, server)
    # 実行
    _event(world, "prompt_submit")
    item = make_item("D-1")
    item.pop("id")
    write_items(server.call, str(root), add=[("decision", item)])
    committed = server.call("commit", workspace=str(root), summary="決めたことを追加した")
    _event(world, "stop")
    wait_until(lambda: webhook.requests)
    # 検証
    assert committed.is_error is False, committed.text
    assert committed.data is not None
    assert committed.data["id"] is not None
    assert len(webhook.requests) == 1


def test_normal_when_nothing_written(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """MindStella のセッションが commit・new_thread・reply を呼ばなかった応答では送信しない（正常系）。"""
    # 準備
    world = session_world
    server = _start(world, webhook)
    root = _prepare(world, server)
    _new_thread(server, root)
    # 実行
    _event(world, "prompt_submit")
    status, _body = _event(world, "stop")
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert status == 200
    assert webhook.requests == []


def test_normal_when_response_failed(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """stop_failure で終わった応答では送信せず、書き込みのマーカーを解除する（正常系）。"""
    # 準備
    world = session_world
    server = _start(world, webhook)
    root = _prepare(world, server)
    thread_id = _new_thread(server, root)
    _event(world, "prompt_submit")
    server.call("reply", workspace=str(root), id=thread_id, body="回答します", summary="質問")
    # 実行
    failed, _body = _event(world, "stop_failure")
    stopped, _body = _event(world, "stop")
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert (failed, stopped) == (200, 200)
    assert webhook.requests == []


def test_normal_when_webhook_not_configured(session_world: SessionWorld) -> None:
    """環境変数が無いときは送信しない（正常系）。"""
    # 準備
    world = session_world
    server = _start(world, None)
    root = _prepare(world, server)
    thread_id = _new_thread(server, root)
    _event(world, "prompt_submit")
    server.call("reply", workspace=str(root), id=thread_id, body="回答します", summary="質問")
    # 実行
    status, body = _event(world, "stop")
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert (status, body) == (200, {"recorded": True})
    assert "Webhook への送信" not in server.stderr_text()


def test_error_when_send_failed(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """Webhook が 500 を返却しても出来事の受け取りは成功し、失敗を URL を含めずに記録する（異常系）。"""
    # 準備
    world = session_world
    webhook.status = 500
    server = _start(world, webhook)
    root = _prepare(world, server)
    thread_id = _new_thread(server, root)
    _event(world, "prompt_submit")
    server.call("reply", workspace=str(root), id=thread_id, body="回答します", summary="質問")
    # 実行
    status, body = _event(world, "stop")
    log = wait_until(
        lambda: "Webhook への送信が失敗した: 500" in server.stderr_text() and server.stderr_text()
    )
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert (status, body) == (200, {"recorded": True})
    assert len(webhook.requests) == 1
    assert "secret-token" not in log
    assert webhook.url not in log


def test_error_when_send_timed_out(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """Webhook が上限まで応答しないときは打ち切り、出来事の受け取りを待たせない（異常系）。"""
    # 準備
    world = session_world
    webhook.delay_sec = SLOW_RESPONSE_SEC
    server = _start(world, webhook)
    root = _prepare(world, server)
    thread_id = _new_thread(server, root)
    _event(world, "prompt_submit")
    server.call("reply", workspace=str(root), id=thread_id, body="回答します", summary="質問")
    # 実行
    started = time.monotonic()
    status, body = _event(world, "stop")
    elapsed = time.monotonic() - started
    log = wait_until(
        lambda: (
            "Webhook への送信が失敗した: TimeoutError" in server.stderr_text()
            and server.stderr_text()
        ),
        timeout=TIMEOUT_LOG_WAIT_SEC,
    )
    # 検証
    assert (status, body) == (200, {"recorded": True})
    assert elapsed < QUICK_RESPONSE_SEC
    assert "secret-token" not in log
    assert webhook.url not in log
