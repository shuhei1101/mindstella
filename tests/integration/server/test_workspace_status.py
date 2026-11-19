"""状態の取得（GET /workspaces/{id}）の結合テスト。"""

from __future__ import annotations

import shutil
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from session_fixtures import SessionWorld, wait_until
from workspace_fixtures import RECORD_DIR, MakePost, MakeThread, WriteThreads

from .test_work_done_notify import FakeWebhook

# 落ちたことを見回る間隔を上書きする環境変数と、テストの間に見回らない値（秒）
CRASH_WATCH_INTERVAL_ENV = "MINDSTELLA_CRASH_WATCH_INTERVAL"
NO_WATCH_INTERVAL_SEC = 3600

# Webhook の設定のファイルの場所を受ける環境変数
WEBHOOK_FILE_ENV = "MINDSTELLA_DISCORD_WEBHOOK_FILE"

# 送信しないことを確認するときに、送信のスレッドを待つ秒数
NO_SEND_WAIT_SEC = 1.0

# 状態のフォルダに書く MindStella のセッションの ID
SESSION_ID = "S-0123456789ab"


@pytest.fixture
def webhook() -> Iterator[FakeWebhook]:
    """200 を返却する Webhook の Mock を起動し、テストの後で閉じる。"""
    fake = FakeWebhook()
    fake.start()
    yield fake
    fake.close()


def _start(world: SessionWorld, webhook: FakeWebhook | None = None) -> None:
    """テストの間に見回らない間隔で（webhook があればその URL を設定して）常駐サーバーを起動する。"""
    extra = {CRASH_WATCH_INTERVAL_ENV: str(NO_WATCH_INTERVAL_SEC)}
    if webhook is not None:
        path = world.root / "webhook.ini"
        path.write_text(f"{webhook.url}\n", encoding="utf-8")
        extra[WEBHOOK_FILE_ENV] = str(path)
    world.start(extra)


def _write_unread(
    world: SessionWorld, make_post: MakePost, make_thread: MakeThread, write_threads: WriteThreads
) -> None:
    """利用者が読んでいない AI の書き込み 2 件と、取り込み待ちの利用者の書き込み 1 件を持つスレッドを書く。"""
    write_threads(
        world.folder(),
        make_thread(
            "TH-1",
            make_post("TH-1-1", author="ai", seen=False),
            make_post("TH-1-2", author="ai", seen=False),
            make_post("TH-1-3"),
        ),
    )


def _snapshot(world: SessionWorld) -> dict[str, bytes]:
    """記録の設定とスレッド・グローバルの設定のファイル・状態のフォルダの中身。"""
    paths = [
        world.folder() / RECORD_DIR / "config.yaml",
        world.folder() / RECORD_DIR / "threads.yaml",
        world.pi.settings_path,
        *sorted(path for path in world.state_root.rglob("*") if path.is_file()),
    ]
    return {str(path): path.read_bytes() for path in paths}


def _responding(world: SessionWorld, workspace_id: str) -> bool:
    """session.json の responding が真か。"""
    session = world.read_session(workspace_id)
    return session is not None and session["responding"] is True


def test_normal(
    session_world: SessionWorld,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """起動中の MindStella のセッションと、未読の数・最後の更新を返す（正常系）。"""
    # 準備
    world = session_world
    world.set_claude_mode("responding")
    _start(world)
    workspace_id = str(world.create_workspace()["id"])
    _write_unread(world, make_post, make_thread, write_threads)
    status, created = world.create_session(workspace_id)
    assert status == 201, created
    wait_until(lambda: _responding(world, workspace_id))
    before = _snapshot(world)
    # 実行
    status, body = world.api("GET", f"/workspaces/{workspace_id}")
    # 検証
    assert status == 200, body
    assert (body["status"], body["closed"]) == ("active", False)
    assert (body["unseen_ai_posts"], body["awaiting_user_posts"]) == (2, 1)
    assert body["updated"] is not None
    assert body["url"] is not None
    assert (body["sessions"][0]["status"], body["sessions"][0]["responding"]) == (
        "running",
        True,
    )
    assert body["close_pending"] is False
    assert body["launch_options_recorded"] is True
    assert body["warnings"] == []
    assert _snapshot(world) == before


def test_normal_when_stopped(session_world: SessionWorld) -> None:
    """クローズ待ちのワークスペースを stopped で返す（正常系）。"""
    # 準備
    world = session_world
    _start(world)
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id, status="stopped", close_pending=True)
    # 実行
    status, body = world.api("GET", f"/workspaces/{workspace_id}")
    # 検証
    assert status == 200, body
    assert body["status"] == "stopped"
    assert body["sessions"][0]["status"] == "stopped"
    assert body["close_pending"] is True


def test_normal_when_closed(
    session_world: SessionWorld,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """クローズしたワークスペースも記録の数と日時を返す（正常系）。"""
    # 準備
    world = session_world
    _start(world)
    workspace_id = str(world.create_workspace()["id"])
    _write_unread(world, make_post, make_thread, write_threads)
    closed, closed_body = world.api("POST", f"/workspaces/{workspace_id}/close")
    assert closed == 200, closed_body
    # 実行
    status, body = world.api("GET", f"/workspaces/{workspace_id}")
    # 検証
    assert status == 200, body
    assert (body["status"], body["closed"]) == ("closed", True)
    assert (body["unseen_ai_posts"], body["awaiting_user_posts"]) == (2, 1)
    assert body["updated"] is not None


def test_normal_when_crashed(session_world: SessionWorld, webhook: FakeWebhook) -> None:
    """ペインが無ければ crashed を返し、状態は書き換えない（正常系）。"""
    # 準備
    world = session_world
    _start(world, webhook)
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id, session=SESSION_ID, status="running")
    # 実行
    status, body = world.api("GET", f"/workspaces/{workspace_id}")
    time.sleep(NO_SEND_WAIT_SEC)
    # 検証
    assert status == 200, body
    assert body["status"] == "active"
    assert body["sessions"][0]["status"] == "crashed"
    session = world.read_session(workspace_id)
    assert session is not None
    assert session["status"] == "running"
    assert webhook.requests == []


def test_normal_when_launch_options_missing(session_world: SessionWorld) -> None:
    """launch.json が無ければ偽を返し、中身は返さない（正常系）。"""
    # 準備
    world = session_world
    _start(world)
    workspace_id = str(world.create_workspace()["id"])
    launch = world.state_root / "workspaces" / workspace_id / "launch.json"
    launch.unlink()
    # 実行
    status, body = world.api("GET", f"/workspaces/{workspace_id}")
    # 検証
    assert status == 200, body
    assert body["launch_options_recorded"] is False
    assert "mcp_config" not in body
    assert "plugin_dirs" not in body
    assert not launch.exists()


def test_error_when_unknown(session_world: SessionWorld) -> None:
    """ID の一覧に無い ID は 404（異常系）。"""
    # 準備
    world = session_world
    _start(world)
    # 実行
    status, body = world.api("GET", "/workspaces/mindstella-無い-000000")
    # 検証
    assert (status, body["stage"]) == (404, "workspace")


def test_error_when_records_missing(session_world: SessionWorld) -> None:
    """記録のフォルダが無くても、セッションの状態と警告を返す（異常系）。"""
    # 準備
    world = session_world
    _start(world)
    workspace_id = str(world.create_workspace()["id"])
    shutil.rmtree(world.folder() / RECORD_DIR)
    # 実行
    status, body = world.api("GET", f"/workspaces/{workspace_id}")
    # 検証
    assert status == 200, body
    assert [warning["stage"] for warning in body["warnings"]] == ["records"]
    assert str(world.folder()) in body["warnings"][0]["detail"]
    assert (body["unseen_ai_posts"], body["awaiting_user_posts"], body["updated"]) == (
        None,
        None,
        None,
    )
    assert body["sessions"] == []
    assert workspace_id in world.pi.settings_path.read_text(encoding="utf-8")


def test_error_when_settings_unreadable(session_world: SessionWorld) -> None:
    """グローバルの設定のファイルを読めなくても、セッションの状態と警告を返す（異常系）。"""
    # 準備
    world = session_world
    _start(world)
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(workspace_id, status="stopped")
    Path(world.pi.settings_path).write_text("sources: [", encoding="utf-8")
    # 実行
    status, body = world.api("GET", f"/workspaces/{workspace_id}")
    # 検証
    assert status == 200, body
    assert [warning["stage"] for warning in body["warnings"]] == ["settings"]
    assert (body["status"], body["closed"]) == (None, None)
    assert (body["unseen_ai_posts"], body["awaiting_user_posts"], body["updated"]) == (
        None,
        None,
        None,
    )
    assert body["sessions"][0]["status"] == "stopped"
