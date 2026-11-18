"""落ちたことの見回り（常駐サーバーが running の MindStella のセッションを間隔ごとに確かめる）の結合テスト。"""

from __future__ import annotations

import time
from collections.abc import Iterator

import pytest

from session_fixtures import SessionWorld, wait_until

from .test_work_done_notify import FakeWebhook

# Webhook の設定のファイルの場所を受ける環境変数
WEBHOOK_FILE_ENV = "MINDSTELLA_DISCORD_WEBHOOK_FILE"

# 見回る間隔を上書きする環境変数とテストの値（秒）
INTERVAL_ENV = "MINDSTELLA_CRASH_WATCH_INTERVAL"
INTERVAL_SEC = 1

# 見回りが 2 回以上回るまで待つ秒数
WATCHED_WAIT_SEC = 3


@pytest.fixture
def webhook() -> Iterator[FakeWebhook]:
    """200 を返却する Webhook の Mock を起動し、テストの後で閉じる。"""
    fake = FakeWebhook()
    fake.start()
    yield fake
    fake.close()


def _start(world: SessionWorld, webhook: FakeWebhook) -> None:
    """Webhook の URL と短い見回りの間隔を指定して常駐サーバーを起動する。"""
    path = world.root / "webhook.ini"
    path.write_text(f"{webhook.url}\n", encoding="utf-8")
    world.start({WEBHOOK_FILE_ENV: str(path), INTERVAL_ENV: str(INTERVAL_SEC)})


def _status(world: SessionWorld, workspace_id: str) -> str | None:
    """session.json の status。"""
    session = world.read_session(workspace_id)
    return None if session is None else str(session["status"])


def test_normal(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """ペインが無い running の MindStella のセッションを crashed にし、異常終了を 1 件通知する（正常系）。"""
    # 準備
    world = session_world
    _start(world, webhook)
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id, status="running")
    # 実行
    wait_until(lambda: _status(world, workspace_id) == "crashed", timeout=WATCHED_WAIT_SEC + 10)
    wait_until(lambda: webhook.requests)
    time.sleep(WATCHED_WAIT_SEC)
    # 検証
    contents = [str(request["body"]["content"]) for request in webhook.requests]
    assert len(contents) == 1
    assert "異常終了" in contents[0]


def test_normal_when_restarting(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """restarting の MindStella のセッションは書き換えない（正常系）。"""
    # 準備
    world = session_world
    _start(world, webhook)
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id, status="restarting")
    # 実行
    time.sleep(WATCHED_WAIT_SEC)
    # 検証
    assert _status(world, workspace_id) == "restarting"
    assert webhook.requests == []
