"""usage_watch.py（利用枠の見回り）の単体テスト。"""

from __future__ import annotations

import dataclasses
import io
import json
import logging
import threading
import time
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import state
import usage_watch
from home_settings import HomeSettings
from state import SessionState
from usage_watch import BalancerUnavailableError

# claude-balancer の常駐の待ち受け先
BASE_URL = "http://127.0.0.1:8770"


class FakeResponse(io.BytesIO):
    """urlopen の戻り値の偽。"""

    def __init__(self, body: bytes, status: int = 200) -> None:
        """本文と状態のコードを持つ。"""
        super().__init__(body)
        self.status = status

    def __enter__(self) -> FakeResponse:
        """with で使う。"""
        return self

    def __exit__(self, *_args: object) -> None:
        """何もしない。"""


def _session(workspace: str, **changes: object) -> SessionState:
    """running の MindStella のセッションの状態を作る。"""
    values: dict[str, Any] = {
        "session": f"S-{workspace}",
        "status": "running",
        "started_at": "2026-11-19T00:00:00+00:00",
        "balancer_account": "A",
    }
    values.update(changes)
    return SessionState(**values)


def _accounts(a_reason: str | None, b_reason: str | None) -> list[dict[str, Any]]:
    """アカウント A・B の行を作る。"""
    return [
        {"account": "A", "unavailableReason": a_reason},
        {"account": "B", "unavailableReason": b_reason},
    ]


def test_fetch_accounts(monkeypatch: pytest.MonkeyPatch) -> None:
    """accounts を返す（正常系）。"""
    # 準備
    called: list[tuple[str, float]] = []

    def _urlopen(url: str, timeout: float) -> FakeResponse:
        """URL と上限を控えて本文を返す。"""
        called.append((url, timeout))
        return FakeResponse(json.dumps({"accounts": [{"account": "a"}]}).encode())

    monkeypatch.setattr(usage_watch.urllib.request, "urlopen", _urlopen)
    # 実行
    result = usage_watch.fetch_accounts(BASE_URL)
    # 検証
    assert result == [{"account": "a"}]
    assert called == [(f"{BASE_URL}/accounts", usage_watch.USAGE_QUERY_TIMEOUT_SEC)]


def _raise_url_error(_url: str, timeout: float) -> FakeResponse:
    """つながらない。"""
    raise urllib.error.URLError("refused")


def _raise_timeout(_url: str, timeout: float) -> FakeResponse:
    """上限を過ぎた。"""
    raise TimeoutError("timed out")


def _raise_http_error(url: str, timeout: float) -> FakeResponse:
    """500 を返す。"""
    raise urllib.error.HTTPError(url, 500, "error", {}, None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "urlopen",
    [
        pytest.param(_raise_url_error, id="url-error"),
        pytest.param(_raise_timeout, id="timeout"),
        pytest.param(_raise_http_error, id="http-500"),
        pytest.param(lambda _url, timeout: FakeResponse(b"x"), id="not-json"),
        pytest.param(lambda _url, timeout: FakeResponse(b'{"accounts": 1}'), id="not-list"),
    ],
)
def test_fetch_accounts_when_unavailable(urlopen: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """つながらない・読めないときは BalancerUnavailableError（異常系）。"""
    # 準備
    monkeypatch.setattr(usage_watch.urllib.request, "urlopen", urlopen)
    # 実行・検証
    with pytest.raises(BalancerUnavailableError):
        usage_watch.fetch_accounts(BASE_URL)


@pytest.mark.parametrize(
    ("session", "accounts", "release_on_limit", "expected"),
    [
        pytest.param(
            _session("w"),
            _accounts("five_hour_over_threshold", None),
            True,
            ["w"],
            id="five-hour",
        ),
        pytest.param(
            _session("w"),
            _accounts("seven_day_over_threshold", None),
            True,
            ["w"],
            id="seven-day",
        ),
        pytest.param(
            _session("w"),
            _accounts("five_hour_over_threshold", "seven_day_over_threshold"),
            True,
            [],
            id="no-other-account",
        ),
        pytest.param(
            _session("w"), _accounts("quota_unknown", None), True, [], id="quota-unknown"
        ),
        pytest.param(_session("w"), _accounts(None, None), True, [], id="under-threshold"),
        pytest.param(
            _session("w", balancer_account="C"),
            _accounts("five_hour_over_threshold", None),
            True,
            [],
            id="account-not-listed",
        ),
        pytest.param(
            _session("w", specified_account="/c/a"),
            _accounts("five_hour_over_threshold", None),
            False,
            [],
            id="specified-release-off",
        ),
        pytest.param(
            _session("w", specified_account="/c/a"),
            _accounts("five_hour_over_threshold", None),
            True,
            ["w"],
            id="specified-release-on",
        ),
    ],
)
def test_choose_restarts(
    session: SessionState,
    accounts: list[dict[str, Any]],
    release_on_limit: bool,
    expected: list[str],
) -> None:
    """しきい値と切り替え先と指定で選ぶかが決まる（正常系）。"""
    # 実行
    result = usage_watch.choose_restarts(
        {"w": dataclasses.asdict(session)}, accounts, release_on_limit
    )
    # 検証
    assert result == expected


@pytest.fixture
def ctx(tmp_path: Path) -> SimpleNamespace:
    """状態のフォルダとホームの設定を持つ、入口が渡す値。"""
    return SimpleNamespace(state_root=tmp_path / "state", home=HomeSettings(None, True))


def _write(ctx: SimpleNamespace, workspace: str, session: SessionState) -> None:
    """ID の一覧へ足して session.json を書く。"""
    state.add_id(ctx.state_root, workspace)
    state.update_session(ctx.state_root, workspace, lambda _current: session)


def test_watch_usage_once(ctx: SimpleNamespace) -> None:
    """見回る対象だけを照らし、選んだものを起動し直す（正常系）。"""
    # 準備
    _write(ctx, "w1", _session("w1"))
    _write(ctx, "w2", _session("w2", status="restarting"))
    _write(ctx, "w3", _session("w3", close_pending=True))
    _write(ctx, "w4", _session("w4", balancer_account=None))
    _write(ctx, "w5", _session("w5", pending_write=True))
    fetched: list[str] = []
    restarted: list[str] = []

    def _fetch(base_url: str) -> list[dict[str, Any]]:
        """問い合わせ先を控えて A をしきい値以上で返す。"""
        fetched.append(base_url)
        return _accounts("five_hour_over_threshold", None)

    # 実行
    result = usage_watch.watch_usage_once(
        ctx, fetch=_fetch, restart=lambda workspace: restarted.append(workspace) or True
    )
    # 検証
    assert result == 1
    assert restarted == ["w1"]
    assert fetched == [BASE_URL]


def test_watch_usage_once_when_no_target(ctx: SimpleNamespace) -> None:
    """見回る対象が無ければ問い合わせない（正常系）。"""
    # 準備
    _write(ctx, "w1", _session("w1", status="crashed"))
    fetched: list[str] = []
    # 実行
    result = usage_watch.watch_usage_once(
        ctx,
        fetch=lambda base_url: fetched.append(base_url) or [],
        restart=lambda _workspace: True,
    )
    # 検証
    assert result == 0
    assert fetched == []


def test_watch_usage_once_when_unavailable(ctx: SimpleNamespace) -> None:
    """問い合わせに失敗したら起動し直さない（異常系）。"""
    # 準備
    _write(ctx, "w1", _session("w1"))
    restarted: list[str] = []

    def _fetch(_base_url: str) -> list[dict[str, Any]]:
        """つながらない。"""
        raise BalancerUnavailableError("refused")

    # 実行
    result = usage_watch.watch_usage_once(
        ctx, fetch=_fetch, restart=lambda workspace: restarted.append(workspace) or True
    )
    # 検証
    assert result is None
    assert restarted == []


def test_start_usage_watch(ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    """間隔ごとに見回り、stop で終わる（正常系）。"""
    # 準備
    monkeypatch.setenv("MINDSTELLA_USAGE_WATCH_INTERVAL", "0.01")
    monkeypatch.setattr(usage_watch.shutil, "which", lambda _name: "/usr/bin/claude-balancer")
    calls: list[int] = []
    monkeypatch.setattr(usage_watch, "watch_usage_once", lambda _ctx: calls.append(1) or 0)
    stop = threading.Event()
    # 実行
    thread = usage_watch.start_usage_watch(ctx, stop)
    time.sleep(0.2)
    stop.set()
    # 検証
    assert thread is not None
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert len(calls) >= 2


def test_start_usage_watch_without_balancer(
    ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """claude-balancer が無ければスレッドを始めない（正常系）。"""
    # 準備
    monkeypatch.setattr(usage_watch.shutil, "which", lambda _name: None)
    # 実行
    result = usage_watch.start_usage_watch(ctx, threading.Event())
    # 検証
    assert result is None


def test_start_usage_watch_when_unavailable(
    ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """問い合わせの失敗は失敗し始めた回だけ記録する（正常系）。"""
    # 準備
    monkeypatch.setenv("MINDSTELLA_USAGE_WATCH_INTERVAL", "0.01")
    monkeypatch.setattr(usage_watch.shutil, "which", lambda _name: "/usr/bin/claude-balancer")
    results = [None, None, 0, None]
    done = threading.Event()

    def _once(_ctx: Any) -> int | None:
        """決めた順に返し、使い切ったら done を立てて 0 を返す。"""
        if results:
            return results.pop(0)
        done.set()
        return 0

    monkeypatch.setattr(usage_watch, "watch_usage_once", _once)
    stop = threading.Event()
    caplog.set_level(logging.WARNING, logger="mindstella.usage_watch")
    # 実行
    thread = usage_watch.start_usage_watch(ctx, stop)
    done.wait(timeout=2)
    stop.set()
    # 検証
    assert thread is not None
    thread.join(timeout=2)
    failures = [r for r in caplog.records if r.getMessage() == "mindstella.usage.query_failed"]
    assert len(failures) == 2
