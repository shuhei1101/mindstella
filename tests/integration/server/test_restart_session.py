"""MindStella のセッションの起動し直し（POST /workspaces/{id}/sessions/{session}/restart）の結合テスト。"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from session_fixtures import FakeBalancerApi, SessionWorld, wait_until

from .test_work_done_notify import FakeWebhook

# 起動し直しが終わるまで待つ秒数
RESTARTED_WAIT_SEC = 30.0

# 状態に書く MindStella のセッションの ID（落ちていることにする）
CRASHED_SESSION_ID = "S-0123456789ab"

# 状態に書く Claude Code の session_id
RECORDED_CLAUDE_SESSION_ID = "c-recorded"

# Webhook の設定のファイルの場所を受ける環境変数
WEBHOOK_FILE_ENV = "MINDSTELLA_DISCORD_WEBHOOK_FILE"

# 見回る間隔を上書きする環境変数とテストの値（秒）
USAGE_WATCH_INTERVAL_ENV = "MINDSTELLA_USAGE_WATCH_INTERVAL"
USAGE_WATCH_INTERVAL_SEC = 1

# 停止の通知の本文の止まった理由の文言
USAGE_THRESHOLD_TEXT = "利用枠の残りが少ないため切り替え"
RATE_LIMITED_TEXT = "（利用上限）"


@pytest.fixture
def webhook() -> Iterator[FakeWebhook]:
    """200 を返却する Webhook の Mock を起動し、テストの後で閉じる。"""
    fake = FakeWebhook()
    fake.start()
    yield fake
    fake.close()


def _transcript(config_dir: Path, folder: Path, claude_session_id: str) -> Path:
    """Claude Code と同じ名前の作り方で、会話の記録のファイルを作る。"""
    name = re.sub(
        r"[^A-Za-z0-9]",
        "-",
        "".join("--" if ord(char) > 0xFFFF else char for char in str(folder.resolve())),
    )
    path = config_dir / "projects" / name / f"{claude_session_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n", encoding="utf-8")
    return path


def _restart(world: SessionWorld, workspace_id: str, session_id: str) -> tuple[int, dict[str, Any]]:
    """起動し直しの API を呼ぶ。"""
    return world.api("POST", f"/workspaces/{workspace_id}/sessions/{session_id}/restart")


def _session(world: SessionWorld, workspace_id: str) -> dict[str, Any]:
    """session.json を読む（無ければテストを止める）。"""
    session = world.read_session(workspace_id)
    assert session is not None
    return session


def _running(world: SessionWorld, config_dir: Path | None = None) -> tuple[str, str, str]:
    """MindStella のセッションを起動し、ワークスペースの ID・MindStella のセッションの ID・Claude Code の session_id を返す。

    config_dir があれば、そのアカウントを指定して起動する。
    """
    workspace_id = str(world.create_workspace()["id"])
    body_args = {} if config_dir is None else {"claude_config_dir": str(config_dir)}
    status, body = world.create_session(workspace_id, **body_args)
    assert status == 201, body
    claude_session_id = str(_session(world, workspace_id)["claude_session_id"])
    return workspace_id, str(body["session"]), claude_session_id


def _crashed(world: SessionWorld, config_dir: Path, **values: Any) -> str:
    """ワークスペースを作り、落ちた MindStella のセッションの状態を書いて、ワークスペースの ID を返す。"""
    workspace_id = str(world.create_workspace()["id"])
    world.write_session(
        workspace_id,
        session=CRASHED_SESSION_ID,
        status="crashed",
        claude_session_id=RECORDED_CLAUDE_SESSION_ID,
        claude_config_dir=str(config_dir),
        **values,
    )
    return workspace_id


def _webhook_env(world: SessionWorld, webhook: FakeWebhook) -> dict[str, str]:
    """Webhook の URL を記載した設定のファイルを作り、常駐サーバーに渡す環境変数を返す。"""
    path = world.root / "webhook.ini"
    path.write_text(f"{webhook.url}\n", encoding="utf-8")
    return {WEBHOOK_FILE_ENV: str(path)}


def _contents(webhook: FakeWebhook) -> list[str]:
    """Webhook が受けた本文の content。"""
    return [str(request["body"]["content"]) for request in webhook.requests]


def test_normal(session_world: SessionWorld) -> None:
    """起動中の MindStella のセッションを止め、前の会話を引き継いで同じ ID のまま起動し直す（正常系）。"""
    # 準備
    world = session_world
    config_dir = world.root / "account"
    # アカウントを指定せずに起動する（Claude Code の設定のフォルダは常駐サーバーから受け継ぐ）
    world.start({"CLAUDE_CONFIG_DIR": str(config_dir)})
    workspace_id, session_id, first_claude = _running(world)
    _transcript(config_dir, world.folder(), first_claude)
    # 実行
    status, body = _restart(world, workspace_id, session_id)
    wait_until(lambda: len(world.balancer_calls()) == 2, timeout=RESTARTED_WAIT_SEC)
    session = wait_until(
        lambda: (
            (current := world.read_session(workspace_id))
            and current["status"] == "running"
            and current["claude_session_id"] != first_claude
            and current
        ),
        timeout=RESTARTED_WAIT_SEC,
    )
    # 検証
    assert (status, body["session"], body["status"]) == (202, session_id, "restarting"), body
    second = world.balancer_calls()[1]
    assert second[second.index("--") + 1 :][-2:] == ["--resume", first_claude]
    assert "--account" not in second
    assert session["session"] == session_id


def test_normal_when_responding(session_world: SessionWorld) -> None:
    """応答の終わりを待ってから止め、待つ間の一覧は restarting を返す（正常系）。"""
    # 準備
    world = session_world
    world.set_claude_mode("responding:2")
    world.start()
    workspace_id, session_id, _claude = _running(world, world.root / "account")
    wait_until(lambda: _session(world, workspace_id).get("responding"))
    # 実行
    status, _body = _restart(world, workspace_id, session_id)
    listed_status, listed = world.api("GET", f"/workspaces/{workspace_id}/sessions")
    exited = wait_until(lambda: world.noted("exit"), timeout=RESTARTED_WAIT_SEC)
    # 検証
    assert status == 202
    assert (listed_status, listed["sessions"][0]["status"]) == (200, "restarting"), listed
    stopped = world.noted("stop")
    assert stopped is not None
    assert exited > stopped


def test_normal_when_transcript_missing(session_world: SessionWorld) -> None:
    """会話の記録のファイルが無ければ --resume を付けずに起動する（正常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = _crashed(world, world.root / "account")
    # 実行
    status, _body = _restart(world, workspace_id, CRASHED_SESSION_ID)
    wait_until(
        lambda: _session(world, workspace_id)["status"] == "running", timeout=RESTARTED_WAIT_SEC
    )
    # 検証
    assert status == 202
    calls = world.balancer_calls()
    assert len(calls) == 1
    assert "--resume" not in calls[0]


def test_error_when_plugin_dir_missing(session_world: SessionWorld) -> None:
    """記録したプラグインのフォルダが無ければ起動せず、last_error に記録する（異常系）。"""
    # 準備
    world = session_world
    world.start()
    plugin = world.root / "plugin"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
    workspace_id = str(world.create_workspace(plugin_dirs=[str(plugin)])["id"])
    world.write_session(workspace_id, session=CRASHED_SESSION_ID, status="crashed")
    (plugin / ".claude-plugin" / "plugin.json").unlink()
    (plugin / ".claude-plugin").rmdir()
    plugin.rmdir()
    # 実行
    status, _body = _restart(world, workspace_id, CRASHED_SESSION_ID)
    session = wait_until(
        lambda: (
            (current := world.read_session(workspace_id))
            and current["status"] == "crashed"
            and current["last_error"]
            and current
        ),
        timeout=RESTARTED_WAIT_SEC,
    )
    listed_status, listed = world.api("GET", f"/workspaces/{workspace_id}/sessions")
    # 検証
    assert status == 202
    assert world.balancer_calls() == []
    assert session["last_error"].startswith("launch_options:")
    assert str(plugin) in session["last_error"]
    assert (listed_status, listed["sessions"][0]["last_error"]) == (200, session["last_error"])


def test_error_when_no_account(session_world: SessionWorld) -> None:
    """exec が 125 で終わればペインを閉じ、last_error に記録する（異常系）。"""
    # 準備
    world = session_world
    world.set_balancer_exit(125)
    world.start()
    workspace_id = _crashed(world, world.root / "account")
    # 実行
    status, _body = _restart(world, workspace_id, CRASHED_SESSION_ID)
    session = wait_until(
        lambda: (
            (current := world.read_session(workspace_id))
            and current["status"] == "crashed"
            and current["last_error"]
            and current
        ),
        timeout=RESTARTED_WAIT_SEC,
    )
    # 検証
    assert status == 202
    assert session["last_error"].startswith("account:")
    assert "借りられるアカウントがありません" in session["last_error"]
    assert workspace_id not in world.sessions()


def test_error_when_closed(session_world: SessionWorld) -> None:
    """クローズ済みなら 409 を返し、状態を変えない（異常系）。"""
    # 準備
    world = session_world
    world.start()
    workspace_id = str(world.create_workspace()["id"])
    close_status, close_body = world.api("POST", f"/workspaces/{workspace_id}/close")
    assert close_status == 200, close_body
    before = world.write_session(workspace_id, session=CRASHED_SESSION_ID, status="stopped")
    # 実行
    status, body = _restart(world, workspace_id, CRASHED_SESSION_ID)
    # 検証
    assert (status, body.get("stage")) == (409, "closed"), body
    assert world.read_session(workspace_id) == before


def test_normal_when_usage_over_threshold(
    session_world: SessionWorld, balancer_api: FakeBalancerApi, webhook: FakeWebhook
) -> None:
    """応答の終わりを待って止め、usage_threshold で通知してから前の会話を引き継いで起動し直す（正常系）。"""
    # 準備（応答の途中で、起動し直した後はしきい値の下のアカウント B を借りる）
    world = session_world
    config_dir = world.root / "account"
    world.set_claude_mode("responding:2")
    world.set_balancer_accounts("A", "B")
    balancer_api.accounts = [
        {"account": "A", "unavailableReason": "five_hour_over_threshold"},
        {"account": "B", "unavailableReason": None},
    ]
    world.write_home_settings(f"claude_balancer:\n  url: {balancer_api.url}\n")
    world.start(
        {
            "CLAUDE_CONFIG_DIR": str(config_dir),
            USAGE_WATCH_INTERVAL_ENV: str(USAGE_WATCH_INTERVAL_SEC),
            **_webhook_env(world, webhook),
        }
    )
    workspace_id, _session_id, first_claude = _running(world)
    _transcript(config_dir, world.folder(), first_claude)
    # 実行（見回りが契機 usage_threshold で起動し直す）
    wait_until(lambda: len(world.balancer_calls()) == 2, timeout=RESTARTED_WAIT_SEC)
    wait_until(
        lambda: (
            (current := world.read_session(workspace_id))
            and current["status"] == "running"
            and current["balancer_account"] == "B"
        ),
        timeout=RESTARTED_WAIT_SEC,
    )
    # 検証
    stopped = world.noted("stop")
    exited = world.noted("exit")
    assert stopped is not None
    assert exited is not None
    assert exited > stopped
    contents = _contents(webhook)
    assert len([content for content in contents if USAGE_THRESHOLD_TEXT in content]) == 1, contents
    second = world.balancer_calls()[1]
    assert "--resume" in second
    assert "--account" not in second


def test_normal_with_specified_account(session_world: SessionWorld) -> None:
    """specified_account があれば、そのアカウントを --account で借りて起動し直す（正常系）。"""
    # 準備
    world = session_world
    world.start()
    config_dir = world.root / "account-a"
    workspace_id, session_id, _claude = _running(world, config_dir)
    # 実行
    status, _body = _restart(world, workspace_id, session_id)
    wait_until(lambda: len(world.balancer_calls()) == 2, timeout=RESTARTED_WAIT_SEC)
    session = wait_until(
        lambda: (
            (current := world.read_session(workspace_id))
            and current["status"] == "running"
            and current["claude_session_id"]
            and current
        ),
        timeout=RESTARTED_WAIT_SEC,
    )
    # 検証
    assert status == 202
    second = world.balancer_calls()[1]
    assert second[second.index("--account") + 1] == str(config_dir)
    assert session["specified_account"] == str(config_dir)


def test_normal_when_specified_account_unavailable(session_world: SessionWorld) -> None:
    """--account 付きの exec が 125 で終われば、指定を解除して --account を付けずに 1 回だけ起動し直す（正常系）。"""
    # 準備
    world = session_world
    world.set_balancer_account_exit(125)
    world.start()
    config_dir = world.root / "account-a"
    workspace_id = _crashed(world, config_dir, specified_account=str(config_dir))
    # 実行
    status, _body = _restart(world, workspace_id, CRASHED_SESSION_ID)
    session = wait_until(
        lambda: (
            (current := world.read_session(workspace_id))
            and current["status"] == "running"
            and current
        ),
        timeout=RESTARTED_WAIT_SEC,
    )
    # 検証
    assert status == 202
    calls = world.balancer_calls()
    assert len(calls) == 2, calls
    assert "--account" in calls[0]
    assert "--account" not in calls[1]
    assert session["specified_account"] is None


def test_error_when_rate_limited_with_release_off(
    session_world: SessionWorld, webhook: FakeWebhook
) -> None:
    """release_on_limit が偽で利用上限の契機なら、止めて通知し、起動し直さずに crashed にする（異常系）。"""
    # 準備
    world = session_world
    world.write_home_settings("account:\n  release_on_limit: false\n")
    world.start(_webhook_env(world, webhook))
    config_dir = world.root / "account-a"
    workspace_id, session_id, claude_session_id = _running(world, config_dir)
    # 実行（Claude Code が利用上限のエラーで応答を終える）
    status, _body = world.api(
        "POST",
        f"/_admin/sessions/{session_id}/events",
        {"event": "stop_failure", "claude_session_id": claude_session_id, "error": "rate_limit"},
    )
    session = wait_until(
        lambda: (
            (current := world.read_session(workspace_id))
            and current["status"] == "crashed"
            and current["last_error"]
            and current
        ),
        timeout=RESTARTED_WAIT_SEC,
    )
    wait_until(lambda: webhook.requests)
    # 検証
    assert status == 200
    assert len(world.balancer_calls()) == 1
    assert session["last_error"].startswith("account:")
    contents = _contents(webhook)
    assert len([content for content in contents if RATE_LIMITED_TEXT in content]) == 1, contents
    assert workspace_id not in world.sessions()
