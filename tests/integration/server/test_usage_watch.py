"""利用枠の見回り（常駐サーバーの中で claude-balancer の GET /accounts を確かめて起動し直す）の結合テスト。"""

from __future__ import annotations

import time
from typing import Any

from session_fixtures import FakeBalancerApi, SessionWorld, wait_until
from workspace_fixtures import McpServer, free_port

# 見回る間隔を上書きする環境変数とテストの値（秒）
USAGE_WATCH_INTERVAL_ENV = "MINDSTELLA_USAGE_WATCH_INTERVAL"
USAGE_WATCH_INTERVAL_SEC = 1

# 起動し直しが終わるまで待つ秒数
RESTARTED_WAIT_SEC = 30.0

# 起動し直さないことを確かめるときに見回りを待つ回数
NO_RESTART_ROUNDS = 3

# 問い合わせの失敗を記録するイベント名
QUERY_FAILED_EVENT = "mindstella.usage.query_failed"


def _accounts(a_reason: str | None, b_reason: str | None) -> list[dict[str, Any]]:
    """アカウント A・B の行を作る。"""
    return [
        {"account": "A", "unavailableReason": a_reason},
        {"account": "B", "unavailableReason": b_reason},
    ]


def _start(world: SessionWorld, url: str, *, release_on_limit: bool = True) -> McpServer:
    """ホームの設定に claude-balancer の待ち受け先を書き、見回りの間隔を縮めて常駐サーバーを起動する。"""
    world.write_home_settings(
        f"claude_balancer:\n  url: {url}\n"
        f"account:\n  release_on_limit: {'true' if release_on_limit else 'false'}\n"
    )
    return world.start({USAGE_WATCH_INTERVAL_ENV: str(USAGE_WATCH_INTERVAL_SEC)})


def _running(world: SessionWorld, **body: Any) -> str:
    """アカウント A を借りて MindStella のセッションを起動し、ワークスペースの ID を返す。"""
    workspace_id = str(world.create_workspace()["id"])
    status, created = world.create_session(workspace_id, **body)
    assert status == 201, created
    session = wait_until(lambda: world.read_session(workspace_id))
    assert session["balancer_account"] == "A", session
    return workspace_id


def _status(world: SessionWorld, workspace_id: str) -> str | None:
    """session.json の status。"""
    session = world.read_session(workspace_id)
    return None if session is None else str(session["status"])


def test_normal(session_world: SessionWorld, balancer_api: FakeBalancerApi) -> None:
    """使用中のアカウントがしきい値以上で切り替え先があれば、契機 usage_threshold で起動し直す（正常系）。"""
    # 準備（起動し直した後はアカウント B を借りる）
    world = session_world
    world.set_balancer_accounts("A", "B")
    balancer_api.accounts = _accounts("five_hour_over_threshold", None)
    _start(world, balancer_api.url)
    workspace_id = _running(world)
    # 実行
    wait_until(lambda: len(world.balancer_calls()) == 2, timeout=RESTARTED_WAIT_SEC)
    session = wait_until(
        lambda: (
            (current := world.read_session(workspace_id))
            and current["status"] == "running"
            and current["balancer_account"] == "B"
            and current
        ),
        timeout=RESTARTED_WAIT_SEC,
    )
    # 検証
    assert "/accounts" in balancer_api.requests
    assert world.noted("exit") is not None
    assert session["status"] == "running"


def test_normal_when_no_other_account(
    session_world: SessionWorld, balancer_api: FakeBalancerApi
) -> None:
    """ほかに貸せるアカウントが無ければ起動し直さない（正常系）。"""
    # 準備
    world = session_world
    world.set_balancer_accounts("A")
    balancer_api.accounts = _accounts("five_hour_over_threshold", "seven_day_over_threshold")
    _start(world, balancer_api.url)
    workspace_id = _running(world)
    # 実行
    wait_until(lambda: len(balancer_api.requests) >= NO_RESTART_ROUNDS)
    # 検証
    assert world.noted("exit") is None
    assert len(world.balancer_calls()) == 1
    assert _status(world, workspace_id) == "running"


def test_normal_when_release_off(
    session_world: SessionWorld, balancer_api: FakeBalancerApi
) -> None:
    """指定したアカウントで起動し、自動解除がオフなら起動し直さない（正常系）。"""
    # 準備
    world = session_world
    world.set_balancer_accounts("A")
    balancer_api.accounts = _accounts("five_hour_over_threshold", None)
    _start(world, balancer_api.url, release_on_limit=False)
    config_dir = world.root / "account-a"
    workspace_id = _running(world, claude_config_dir=str(config_dir))
    # 実行
    wait_until(lambda: len(balancer_api.requests) >= NO_RESTART_ROUNDS)
    # 検証
    assert world.noted("exit") is None
    assert len(world.balancer_calls()) == 1
    session = world.read_session(workspace_id)
    assert session is not None
    assert (session["status"], session["specified_account"]) == ("running", str(config_dir))


def test_normal_when_balancer_unreachable(session_world: SessionWorld) -> None:
    """つながらなければ起動し直さず、標準エラーに 1 行だけ記録して次の間隔を待つ（正常系）。"""
    # 準備
    world = session_world
    world.set_balancer_accounts("A")
    server = _start(world, f"http://127.0.0.1:{free_port()}")
    workspace_id = _running(world)
    # 実行（見回りが複数回回るまで待つ）
    wait_until(lambda: QUERY_FAILED_EVENT in server.stderr_text())
    time.sleep(USAGE_WATCH_INTERVAL_SEC * NO_RESTART_ROUNDS)
    # 検証
    assert server.stderr_text().count(QUERY_FAILED_EVENT) == 1
    assert _status(world, workspace_id) == "running"
    status, _body = world.api("GET", f"/workspaces/{workspace_id}/sessions")
    assert status == 200
