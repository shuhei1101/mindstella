"""停止の通知（MindStella のセッションが止まったことを Discord の Webhook へ送信する）の結合テスト。"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from record_write_helpers import write_items
from session_fixtures import SessionWorld, wait_until
from workspace_fixtures import MDMARK_COMMAND_ENV, NOOP_MDMARK_COMMAND, MakeItem, McpServer

from .test_work_done_notify import FakeWebhook

# Webhook の設定のファイルの場所を受ける環境変数
WEBHOOK_FILE_ENV = "MINDSTELLA_DISCORD_WEBHOOK_FILE"

# 送信しないことを確認するときに、送信のスレッドを待つ秒数
NO_SEND_WAIT_SEC = 1.0

# 停止して状態に記録されるまで待つ秒数
STOPPED_WAIT_SEC = 15.0

# 落ちたことを見回る間隔を上書きする環境変数とテストの値（秒）
CRASH_WATCH_INTERVAL_ENV = "MINDSTELLA_CRASH_WATCH_INTERVAL"
CRASH_WATCH_INTERVAL_SEC = 1

# 状態に無い MindStella のセッションの ID（落ちていることにする）
CRASHED_SESSION_ID = "S-0000000000aa"


@pytest.fixture
def webhook() -> Iterator[FakeWebhook]:
    """200 を返却する Webhook の Mock を起動し、テストの後で閉じる。"""
    fake = FakeWebhook()
    fake.start()
    yield fake
    fake.close()


def _start(
    world: SessionWorld, webhook: FakeWebhook | None, extra_env: dict[str, str] | None = None
) -> McpServer:
    """Webhook の URL を記載した設定のファイルを指定して（webhook が None なら指定せずに）常駐サーバーを起動する。"""
    extra = {MDMARK_COMMAND_ENV: NOOP_MDMARK_COMMAND, **(extra_env or {})}
    if webhook is not None:
        path = world.root / "webhook.ini"
        path.write_text(f"{webhook.url}\n", encoding="utf-8")
        extra[WEBHOOK_FILE_ENV] = str(path)
    return world.start(extra)


def _running(
    world: SessionWorld, *, responding: bool = False, before: Callable[[str], None] | None = None
) -> tuple[str, str]:
    """ワークスペースを作って MindStella のセッションを起動し、ワークスペースの ID と MindStella のセッションの ID を返す。

    before は、ワークスペースを作った後・MindStella のセッションを起動する前に呼ぶ。
    """
    workspace_id = str(world.create_workspace()["id"])
    if before is not None:
        before(workspace_id)
    status, body = world.create_session(workspace_id)
    assert status == 201, body
    if responding:
        wait_until(lambda: (world.read_session(workspace_id) or {}).get("responding"))
    return workspace_id, str(body["session"])


def _status(world: SessionWorld, workspace_id: str) -> str | None:
    """session.json の status。"""
    session = world.read_session(workspace_id)
    return None if session is None else str(session["status"])


def _contents(webhook: FakeWebhook) -> list[str]:
    """Webhook が受けた本文の content。"""
    return [str(request["body"]["content"]) for request in webhook.requests]


def _add_pending(
    world: SessionWorld, server: McpServer, make_item: MakeItem, workspace_id: str
) -> None:
    """まだまとめていない変更を作る。

    MCP の呼び出しが書いたテストの MindStella のセッションの状態は、起動の前の判定で落ちたとみなされないように停止済みにする。
    """
    item = make_item("D-1")
    item.pop("id")
    write_items(server.call, str(world.folder()), add=[("decision", item)])
    world.write_session(workspace_id, status="stopped")


def _event(world: SessionWorld, session_id: str, name: str, **extra: object) -> int:
    """MindStella のセッションの出来事を送信し、ステータスを返す。"""
    body: dict[str, object] = {"event": name, "claude_session_id": "c-1", **extra}
    status, _body = world.api("POST", f"/_admin/sessions/{session_id}/events", body)
    return status


def test_normal(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """停止の依頼で止め終えたときに、停止の依頼を理由に 1 件送信する（正常系）。"""
    # 準備
    world = session_world
    server = _start(world, webhook)
    workspace_id, session_id = _running(world)
    page_url = server.call("preview_url", workspace=str(world.folder())).data["url"]
    # 実行
    status, _body = world.api("DELETE", f"/workspaces/{workspace_id}/sessions/{session_id}")
    wait_until(lambda: _status(world, workspace_id) == "stopped", timeout=STOPPED_WAIT_SEC)
    wait_until(lambda: webhook.requests)
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert status == 202
    assert len(webhook.requests) == 1
    assert webhook.requests[0]["query"] == {"wait": ["true"]}
    assert _contents(webhook) == [f"家計簿: 停止しました（停止の依頼）\n{page_url}"]
    log = wait_until(
        lambda: "Webhook への送信が成功した" in server.stderr_text() and server.stderr_text()
    )
    assert "secret-token" not in log
    assert webhook.url not in log


def test_normal_when_forced(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """強制を指定した停止で止め終えたときに、強制停止を理由に 1 件送信する（正常系）。"""
    # 準備
    world = session_world
    world.set_claude_mode("responding")
    _start(world, webhook)
    workspace_id, session_id = _running(world, responding=True)
    # 実行
    status, _body = world.api(
        "DELETE", f"/workspaces/{workspace_id}/sessions/{session_id}?force=true"
    )
    wait_until(lambda: _status(world, workspace_id) == "stopped", timeout=STOPPED_WAIT_SEC)
    wait_until(lambda: webhook.requests)
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert status == 202
    assert len(webhook.requests) == 1
    assert _contents(webhook)[0].split("\n")[0] == "家計簿: 停止しました（強制停止）"


def test_normal_when_session_crashed(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """見回りでペインが無いことを検知して異常終了を 1 件送信し、その後の停止では送信しない（正常系）。"""
    # 準備
    world = session_world
    _start(world, webhook, {CRASH_WATCH_INTERVAL_ENV: str(CRASH_WATCH_INTERVAL_SEC)})
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id, session=CRASHED_SESSION_ID)
    # 実行
    wait_until(lambda: _status(world, workspace_id) == "crashed", timeout=STOPPED_WAIT_SEC)
    wait_until(lambda: webhook.requests)
    stopped, stop_body = world.api(
        "DELETE", f"/workspaces/{workspace_id}/sessions/{CRASHED_SESSION_ID}"
    )
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert (stopped, stop_body["status"]) == (200, "stopped")
    assert len(webhook.requests) == 1
    assert _contents(webhook)[0].split("\n")[0] == "家計簿: 停止しました（異常終了）"


def test_normal_when_session_ended(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """停止の依頼なしに SessionEnd を受けて停止済みにしたときに、Claude Code の終了を 1 件送信する（正常系）。"""
    # 準備
    world = session_world
    _start(world, webhook)
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id)
    # 実行
    status = _event(world, "S-0123456789ab", "session_end", reason="prompt_input_exit")
    wait_until(lambda: webhook.requests)
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert status == 200
    assert _status(world, workspace_id) == "stopped"
    assert len(webhook.requests) == 1
    assert _contents(webhook)[0].split("\n")[0] == "家計簿: 停止しました（Claude Code の終了）"


def test_normal_when_cleared(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """SessionEnd の reason が clear なら送信しない（正常系）。"""
    # 準備
    world = session_world
    _start(world, webhook)
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id)
    # 実行
    status = _event(world, "S-0123456789ab", "session_end", reason="clear")
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert status == 200
    assert _status(world, workspace_id) == "running"
    assert webhook.requests == []


def test_normal_when_webhook_not_configured(session_world: SessionWorld) -> None:
    """環境変数が無いときは送信せず、停止は変わらない（正常系）。"""
    # 準備
    world = session_world
    server = _start(world, None)
    workspace_id, session_id = _running(world)
    # 実行
    status, _body = world.api("DELETE", f"/workspaces/{workspace_id}/sessions/{session_id}")
    wait_until(lambda: _status(world, workspace_id) == "stopped", timeout=STOPPED_WAIT_SEC)
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert status == 202
    assert "Webhook への送信" not in server.stderr_text()


def test_normal_when_closed_while_stopping(
    session_world: SessionWorld, webhook: FakeWebhook
) -> None:
    """停止の依頼の途中にクローズがペインの無いことを検知しても送信せず、止め終えたときに停止の依頼を 1 件送信する（正常系）。"""
    # 準備
    world = session_world
    world.set_claude_mode("exit_without_end")
    _start(world, webhook)
    workspace_id, session_id = _running(world)
    # 実行
    status, _body = world.api("DELETE", f"/workspaces/{workspace_id}/sessions/{session_id}")
    wait_until(lambda: world.noted("exit"), timeout=STOPPED_WAIT_SEC)
    wait_until(lambda: world.alive_claude_pids() == [], timeout=STOPPED_WAIT_SEC)
    closed, _closed_body = world.api("POST", f"/workspaces/{workspace_id}/close")
    wait_until(lambda: _status(world, workspace_id) == "stopped", timeout=STOPPED_WAIT_SEC)
    wait_until(lambda: webhook.requests)
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert status == 202
    assert closed == 200
    assert len(webhook.requests) == 1
    assert _contents(webhook)[0].split("\n")[0] == "家計簿: 停止しました（停止の依頼）"


def _set_mode(records: Path, folder_mode: int, file_mode: int) -> None:
    """記録のフォルダと配下のファイルの権限を変える。"""
    for path in records.rglob("*"):
        path.chmod(folder_mode if path.is_dir() else file_mode)
    records.chmod(folder_mode)


@pytest.fixture
def unwritable_records(session_world: SessionWorld) -> Iterator[Callable[[], None]]:
    """ワークスペースの記録のフォルダを書き込めなくする関数を渡し、テストの後で書き込めるように戻す。"""
    records = session_world.folder() / ".mindstella"
    yield lambda: _set_mode(records, 0o555, 0o444)
    if records.exists():
        _set_mode(records, 0o755, 0o644)


def test_error_when_stop_failed(
    session_world: SessionWorld,
    webhook: FakeWebhook,
    unwritable_records: Callable[[], None],
    make_item: MakeItem,
) -> None:
    """止める間に失敗して crashed に戻したときに、停止処理の失敗を 1 件送信する（異常系）。"""
    # 準備
    world = session_world
    world.set_claude_mode("responding_then_exit:2")
    server = _start(world, webhook)
    workspace_id, session_id = _running(
        world, responding=True, before=lambda workspace_id: _add_pending(world, server, make_item, workspace_id)
    )
    unwritable_records()
    # 実行
    status, _body = world.api("DELETE", f"/workspaces/{workspace_id}/sessions/{session_id}")
    session = wait_until(
        lambda: (
            (current := world.read_session(workspace_id)) and current.get("last_error") and current
        ),
        timeout=STOPPED_WAIT_SEC,
    )
    wait_until(lambda: webhook.requests)
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert status == 202
    assert session["status"] == "crashed"
    assert len(webhook.requests) == 1
    assert _contents(webhook)[0].split("\n")[0] == "家計簿: 停止しました（停止処理の失敗）"


def test_error_when_stop_failed_but_alive(
    session_world: SessionWorld,
    webhook: FakeWebhook,
    unwritable_records: Callable[[], None],
    make_item: MakeItem,
) -> None:
    """止める間に失敗しても生きていて running に戻したときは送信しない（異常系）。"""
    # 準備
    world = session_world
    world.set_claude_mode("responding:2")
    server = _start(world, webhook)
    workspace_id, session_id = _running(
        world, responding=True, before=lambda workspace_id: _add_pending(world, server, make_item, workspace_id)
    )
    unwritable_records()
    # 実行
    status, _body = world.api("DELETE", f"/workspaces/{workspace_id}/sessions/{session_id}")
    session = wait_until(
        lambda: (
            (current := world.read_session(workspace_id)) and current.get("last_error") and current
        ),
        timeout=STOPPED_WAIT_SEC,
    )
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert status == 202
    assert session["status"] == "running"
    assert webhook.requests == []


def test_error_when_send_failed(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """Webhook が 500 を返却しても停止は成功し、失敗を URL を含めずに記録する（異常系）。"""
    # 準備
    world = session_world
    webhook.status = 500
    server = _start(world, webhook)
    workspace_id, session_id = _running(world)
    # 実行
    status, _body = world.api("DELETE", f"/workspaces/{workspace_id}/sessions/{session_id}")
    wait_until(lambda: _status(world, workspace_id) == "stopped", timeout=STOPPED_WAIT_SEC)
    log = wait_until(
        lambda: "Webhook への送信が失敗した: 500" in server.stderr_text() and server.stderr_text()
    )
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert status == 202
    assert len(webhook.requests) == 1
    assert "secret-token" not in log
    assert webhook.url not in log
