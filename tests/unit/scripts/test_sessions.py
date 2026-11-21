"""sessions.py（MindStella のセッションの作成・一覧・停止と出来事の記録）の単体テスト。"""

from __future__ import annotations

import logging
import re
import signal
import threading
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import commands
import notify
import project_index
import read_point
import resume
import sessions
import state
from errors import ApiError
from home_settings import HomeSettings
from state import LaunchOptions, SessionState
from workspaces import WorkspaceLocks

# テストのワークスペースの ID
WORKSPACE_ID = "mindstella-家計簿-3f2a9c"

# テストの MindStella のセッションの ID
SESSION_ID = "S-0123456789ab"

# ペイン
PANE = f"{WORKSPACE_ID}:0.0"

# Claude Code のプロセスの PID と起動時刻
PID = 4242
PID_STARTED_AT = "12345"


class FakeTmux:
    """tmux の呼び出しを記録し、決めた値を返す。"""

    def __init__(self, log: list[Any]) -> None:
        """生きているペインで始める。"""
        self.log = log
        self.pane_dead = "0 0"
        self.pane_alive = True
        self.capture = "最後の行"
        self.fail_on_exit_paste = False
        self.exit_pasted = False
        self.session_exists = False

    @property
    def calls(self) -> list[list[str]]:
        """記録した tmux の呼び出し。"""
        return [entry[1] for entry in self.log if entry[0] == "tmux"]

    def run(self, args: list[str], stdin: bytes | None = None) -> tuple[int, str]:
        """呼び出しを記録して答える。"""
        self.log.append(("tmux", list(args), stdin))
        command = args[0]
        if command == "load-buffer" and stdin == b"/exit":
            if self.fail_on_exit_paste:
                raise OSError("tmux が見つかりません")
            self.exit_pasted = True
        if command == "display-message":
            if "#{pane_dead}" in args[-1]:
                return 0, self.pane_dead
            return (0, str(PID)) if self.pane_alive else (1, "")
        if command == "capture-pane":
            return 0, self.capture
        if command == "has-session":
            return (0, "") if self.session_exists else (1, "")
        return 0, ""


class FakeProc:
    """/exit が貼られるまで生きているプロセス。"""

    def __init__(self, tmux: FakeTmux) -> None:
        """tmux の偽を見て終わりを決める。"""
        self.tmux = tmux
        self.exit_on_paste = True

    def started_at(self, pid: int) -> str | None:
        """/exit が貼られた後は None を返す。"""
        if self.exit_on_paste and self.tmux.exit_pasted:
            return None
        return PID_STARTED_AT if self.tmux.pane_alive else None


class FakeClock:
    """sleep で進む時計。sleep のたびに決めた関数を呼ぶ。"""

    def __init__(self, log: list[Any]) -> None:
        """0 秒から始める。"""
        self.now = 0.0
        self.sleeps = 0
        self.log = log
        self.on_sleep: Callable[[int], None] = lambda _count: None

    def monotonic(self) -> float:
        """今の時刻。"""
        return self.now

    def sleep(self, seconds: float) -> None:
        """時刻を進める。"""
        self.now += seconds
        self.sleeps += 1
        self.log.append(("sleep", self.sleeps))
        self.on_sleep(self.sleeps)


@pytest.fixture
def log() -> list[Any]:
    """tmux と sleep の呼び出しの順の記録。"""
    return []


@pytest.fixture
def tmux(log: list[Any]) -> FakeTmux:
    """tmux の偽。"""
    return FakeTmux(log)


@pytest.fixture
def clock(log: list[Any], monkeypatch: pytest.MonkeyPatch) -> FakeClock:
    """sessions の time を差し替えた時計。"""
    fake = FakeClock(log)
    monkeypatch.setattr(
        sessions, "time", SimpleNamespace(monotonic=fake.monotonic, sleep=fake.sleep)
    )
    return fake


@pytest.fixture(autouse=True)
def stopped_notices(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """停止の通知の代わりにワークスペースの ID と止まった理由を控える。"""
    notices: list[tuple[str, str]] = []
    monkeypatch.setattr(
        notify,
        "notify_stopped",
        lambda workspace_id, reason, _describe, **_kwargs: notices.append((workspace_id, reason)),
        raising=False,
    )
    return notices


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    """ワークスペースのフォルダ。"""
    path = tmp_path / "家計簿"
    (path / ".mindstella").mkdir(parents=True)
    (path / ".mindstella" / "config.yaml").write_text(
        f"id: {WORKSPACE_ID}\nflow:\n  source: aituber\n  doc: flow-1\nsummary: 家計簿\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def ctx(
    tmp_path: Path, folder: Path, tmux: FakeTmux, monkeypatch: pytest.MonkeyPatch
) -> SimpleNamespace:
    """ID の一覧と launch.json を持つ状態のフォルダと、入口が渡す値。"""
    root = tmp_path / "state"
    state.add_id(root, WORKSPACE_ID)
    state.write_launch(root, WORKSPACE_ID, LaunchOptions(mcp_config=None, plugin_dirs=[]))
    plugin_root = tmp_path / "plugin"
    plugin_root.mkdir()
    row = {
        "id": WORKSPACE_ID,
        "config": [f"{folder}/.mindstella/dev-docs.yaml"],
        "outsideRead": True,
    }
    monkeypatch.setattr(
        project_index, "get_settings", lambda _port: {"version": "v1", "sources": [row]}
    )
    monkeypatch.setattr(sessions.shutil, "which", lambda _name: None)
    monkeypatch.setattr(
        commands, "run_pending", lambda _root: {"added": [], "changed": [], "removed": []}
    )
    previews = SimpleNamespace(start=lambda _root: ("http://127.0.0.1:9100/w/mindstella-x-1/", False))
    return SimpleNamespace(
        port=8784,
        pi_port=8786,
        state_root=root,
        locks=WorkspaceLocks(),
        previews=previews,
        plugin_root=plugin_root,
        tmux=tmux,
        proc=FakeProc(tmux),
        write_lock=threading.Lock(),
        row=row,
        home=HomeSettings(None, True),
    )


def _write_session(ctx: SimpleNamespace, **changes: object) -> None:
    """生きている MindStella のセッションの状態を書く。"""
    values: dict[str, Any] = {
        "session": SESSION_ID,
        "status": "running",
        "claude_session_id": "c1",
        "pane": PANE,
        "pid": PID,
        "pid_started_at": PID_STARTED_AT,
        "started_at": "2026-11-15T00:00:00+00:00",
    }
    values.update(changes)
    state.update_session(ctx.state_root, WORKSPACE_ID, lambda _current: SessionState(**values))


def _session(ctx: SimpleNamespace) -> SessionState:
    """今の状態を読む。"""
    current = state.read_session(ctx.state_root, WORKSPACE_ID)
    assert current is not None
    return current


def _register_on_sleep(ctx: SimpleNamespace, clock: FakeClock) -> None:
    """1 回目の sleep で SessionStart のフックが登録したことにする。"""

    def register(count: int) -> None:
        """claude_session_id・PID・claude_config_dir を入れる。"""
        if count == 1:
            state.update_session(
                ctx.state_root,
                WORKSPACE_ID,
                lambda current: (
                    None
                    if current is None
                    else current.replace(
                        claude_session_id="c1",
                        pid=PID,
                        pid_started_at=PID_STARTED_AT,
                        claude_config_dir="/c",
                    )
                ),
            )

    clock.on_sleep = register


def test_new_session_id() -> None:
    """S- に続く 12 桁の 16 進で、重ならない。"""
    ids = [sessions.new_session_id() for _ in range(1000)]
    assert all(re.fullmatch(r"S-[0-9a-f]{12}", value) for value in ids)
    assert len(set(ids)) == len(ids)


@pytest.mark.parametrize(
    ("options", "mcp_file", "balancer", "config_dir", "expected"),
    [
        pytest.param(
            LaunchOptions(mcp_config={"mcpServers": {}}, plugin_dirs=["p"]),
            Path("f"),
            "/usr/bin/claude-balancer",
            None,
            [
                "/usr/bin/claude-balancer",
                "exec",
                "--client",
                "mindstella",
                "--",
                "claude",
                "--mcp-config",
                "f",
                "--plugin-dir",
                "p",
            ],
            id="balancer",
        ),
        pytest.param(
            LaunchOptions(mcp_config=None, plugin_dirs=[]),
            None,
            None,
            None,
            ["claude"],
            id="no-balancer",
        ),
        pytest.param(None, None, None, None, ["claude"], id="no-record"),
        pytest.param(
            None,
            None,
            "/usr/bin/claude-balancer",
            "/c",
            [
                "/usr/bin/claude-balancer",
                "exec",
                "--client",
                "mindstella",
                "--account",
                "/c",
                "--",
                "claude",
            ],
            id="balancer-account",
        ),
        pytest.param(
            None,
            None,
            None,
            "/c",
            ["claude"],
            id="no-balancer-account",
        ),
    ],
)
def test_build_command(
    options: LaunchOptions | None,
    mcp_file: Path | None,
    balancer: str | None,
    config_dir: str | None,
    expected: list[str],
) -> None:
    """claude-balancer の有無と指定で並びが変わる。"""
    assert sessions.build_command(options, mcp_file, balancer, config_dir) == expected


@pytest.mark.parametrize(
    ("flow", "has_balancer", "present", "absent"),
    [
        pytest.param(
            {"source": "src", "doc": "doc"},
            True,
            {"MINDSTELLA_FLOW": "src#doc"},
            "CLAUDE_CONFIG_DIR",
            id="balancer",
        ),
        pytest.param(None, False, {"CLAUDE_CONFIG_DIR": "/c"}, "MINDSTELLA_FLOW", id="no-balancer"),
    ],
)
def test_build_env(
    flow: dict[str, str] | None, has_balancer: bool, present: dict[str, str], absent: str
) -> None:
    """進め方の文書と CLAUDE_CONFIG_DIR の入り方。"""
    env = sessions.build_env(SESSION_ID, WORKSPACE_ID, 8784, flow, "/c", has_balancer)
    assert env["MINDSTELLA_SESSION"] == SESSION_ID
    assert env["MINDSTELLA_WORKSPACE"] == WORKSPACE_ID
    assert env["MINDSTELLA_PORT"] == "8784"
    assert present.items() <= env.items()
    assert absent not in env


@pytest.mark.parametrize(
    ("status", "pane_alive", "started_at", "expected", "final_status"),
    [
        pytest.param("running", True, PID_STARTED_AT, True, "running", id="alive"),
        pytest.param("running", False, PID_STARTED_AT, False, "crashed", id="no-pane"),
        pytest.param("running", True, "999", False, "crashed", id="other-process"),
        pytest.param("stopped", True, PID_STARTED_AT, False, "stopped", id="stopped"),
    ],
)
def test_is_alive(
    status: str,
    pane_alive: bool,
    started_at: str,
    expected: bool,
    final_status: str,
    ctx: SimpleNamespace,
) -> None:
    """ペインとプロセスで判定し、落ちていれば crashed にする。"""
    _write_session(ctx, status=status, pid_started_at=started_at)
    ctx.tmux.pane_alive = pane_alive
    assert sessions.is_alive(ctx.state_root, WORKSPACE_ID, ctx.tmux, ctx.proc) is expected
    assert _session(ctx).status == final_status


def test_create_session(ctx: SimpleNamespace, clock: FakeClock) -> None:
    """登録が入れば 201 を返し、最初の入力を貼る。"""
    _register_on_sleep(ctx, clock)
    status, body = sessions.create_session(WORKSPACE_ID, None, ctx)
    assert status == 201
    assert re.fullmatch(r"S-[0-9a-f]{12}", body["session"])
    assert body["pane"] == PANE
    assert body["url"] == "http://127.0.0.1:9100/w/mindstella-x-1/"
    assert body["account"] == "/c"
    names = [call[0] for call in ctx.tmux.calls if call[0] != "display-message"]
    assert names == [
        "has-session",
        "new-session",
        "set-option",
        "respawn-pane",
        "set-option",
        "load-buffer",
        "paste-buffer",
        "send-keys",
    ]
    set_options = [call for call in ctx.tmux.calls if call[0] == "set-option"]
    assert [call[-2:] for call in set_options] == [
        ["remain-on-exit", "on"],
        ["remain-on-exit", "off"],
    ]
    respawn = next(call for call in ctx.tmux.calls if call[0] == "respawn-pane")
    assert "-k" in respawn
    assert f"MINDSTELLA_SESSION={body['session']}" in respawn
    assert "MINDSTELLA_FLOW=aituber#flow-1" in respawn
    first_input = next(
        entry[2] for entry in ctx.tmux.log if entry[0] == "tmux" and entry[1][0] == "load-buffer"
    )
    assert first_input == sessions.FIRST_INPUT.encode("utf-8")
    current = _session(ctx)
    assert (current.session, current.status, current.close_pending) == (
        body["session"],
        "running",
        False,
    )


@pytest.mark.parametrize(
    "status", [pytest.param("stopped", id="stopped"), pytest.param("crashed", id="crashed")]
)
def test_create_session_stale(status: str, ctx: SimpleNamespace, clock: FakeClock) -> None:
    """止まった・落ちた後に同じ名前の tmux のセッションが残っていれば、閉じてから作る。"""
    _write_session(ctx, status=status)
    ctx.tmux.session_exists = True
    _register_on_sleep(ctx, clock)
    status_code, _body = sessions.create_session(WORKSPACE_ID, None, ctx)
    assert status_code == 201
    names = [call[0] for call in ctx.tmux.calls if call[0] != "display-message"]
    assert names[:3] == ["has-session", "kill-session", "new-session"]


def test_create_session_exists(ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    """生きている MindStella のセッションがあれば 409 で、tmux を呼ばない。"""
    _write_session(ctx)
    monkeypatch.setattr(sessions, "is_alive", lambda *_args, **_kwargs: True)
    with pytest.raises(ApiError) as caught:
        sessions.create_session(WORKSPACE_ID, None, ctx)
    assert (caught.value.status, caught.value.stage) == (409, "exists")
    assert caught.value.extra == {"session": SESSION_ID, "pane": PANE}
    assert ctx.tmux.calls == []


def test_create_session_closed(ctx: SimpleNamespace) -> None:
    """クローズ済みなら 409。"""
    ctx.row["outsideRead"] = False
    with pytest.raises(ApiError) as caught:
        sessions.create_session(WORKSPACE_ID, None, ctx)
    assert (caught.value.status, caught.value.stage) == (409, "closed")
    assert ctx.tmux.calls == []


def test_create_session_no_account(ctx: SimpleNamespace, clock: FakeClock) -> None:
    """claude-balancer が 125 で終われば 503 で、ペインを閉じて状態を消す。"""
    ctx.tmux.pane_dead = "1 125"
    ctx.tmux.capture = "claude-balancer: 借りられるアカウントがありません"
    with pytest.raises(ApiError) as caught:
        sessions.create_session(WORKSPACE_ID, None, ctx)
    assert (caught.value.status, caught.value.stage) == (503, "account")
    assert "借りられるアカウントがありません" in caught.value.detail
    assert any(call[0] == "kill-session" for call in ctx.tmux.calls)
    assert state.read_session(ctx.state_root, WORKSPACE_ID) is None


def test_create_session_launch_exit(ctx: SimpleNamespace, clock: FakeClock) -> None:
    """125 以外で終われば 502。"""
    ctx.tmux.pane_dead = "1 1"
    with pytest.raises(ApiError) as caught:
        sessions.create_session(WORKSPACE_ID, None, ctx)
    assert (caught.value.status, caught.value.stage) == (502, "launch")
    assert state.read_session(ctx.state_root, WORKSPACE_ID) is None


def test_create_session_not_ready(
    ctx: SimpleNamespace, clock: FakeClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """上限までに登録が入らなければ 504 で、ペインを閉じる。"""
    monkeypatch.setenv("MINDSTELLA_SESSION_READY_TIMEOUT", "1")
    with pytest.raises(ApiError) as caught:
        sessions.create_session(WORKSPACE_ID, None, ctx)
    assert (caught.value.status, caught.value.stage) == (504, "ready")
    assert any(call[0] == "kill-session" for call in ctx.tmux.calls)
    assert state.read_session(ctx.state_root, WORKSPACE_ID) is None


def test_list_sessions_when_never_created(
    ctx: SimpleNamespace, stopped_notices: list[tuple[str, str]]
) -> None:
    """一度も作っていなければ空の並びを返し、何も書き換えない（正常系）。"""
    # 実行
    body = sessions.list_sessions(WORKSPACE_ID, ctx)
    # 検証
    assert body == {"sessions": [], "close_pending": False}
    assert state.read_session(ctx.state_root, WORKSPACE_ID) is None
    assert stopped_notices == []


@pytest.mark.parametrize(
    ("status", "pane_alive", "expected_status", "expected_pane"),
    [
        pytest.param("running", True, "running", PANE, id="running"),
        pytest.param("running", False, "crashed", None, id="crashed"),
        pytest.param("stopping", False, "stopping", PANE, id="stopping"),
    ],
)
def test_list_sessions(
    status: str,
    pane_alive: bool,
    expected_status: str,
    expected_pane: str | None,
    ctx: SimpleNamespace,
    stopped_notices: list[tuple[str, str]],
) -> None:
    """落ちていれば crashed を返して書き換えない（正常系）。"""
    # 準備
    _write_session(ctx, status=status)
    ctx.tmux.pane_alive = pane_alive
    before = _session(ctx)
    # 実行
    body = sessions.list_sessions(WORKSPACE_ID, ctx)
    # 検証
    assert body["sessions"][0]["id"] == SESSION_ID
    assert body["sessions"][0]["status"] == expected_status
    assert body["sessions"][0]["pane"] == expected_pane
    assert body["close_pending"] is False
    assert _session(ctx) == before
    assert stopped_notices == []


def _spawn(
    ctx: SimpleNamespace, observed: list[SessionState]
) -> Callable[[Callable[[], None]], None]:
    """止める処理を同じスレッドで走らせ、走らせる前の状態を控える。"""

    def spawn(body: Callable[[], None]) -> None:
        """控えてから走らせる。"""
        observed.append(_session(ctx))
        body()

    return spawn


def _exit_pastes(log: list[Any]) -> list[int]:
    """/exit を貼った位置。"""
    return [index for index, entry in enumerate(log) if entry[0] == "tmux" and entry[2] == b"/exit"]


def test_stop_session(ctx: SimpleNamespace, clock: FakeClock, log: list[Any]) -> None:
    """すぐに 202 を返し、/exit を貼って止める。"""
    _write_session(ctx)
    observed: list[SessionState] = []
    status, body = sessions.stop_session(
        WORKSPACE_ID, SESSION_ID, False, ctx, spawn=_spawn(ctx, observed)
    )
    assert (status, body) == (202, {"session": SESSION_ID, "status": "stopping"})
    assert observed[0].close_pending is True
    assert observed[0].status == "stopping"
    assert _exit_pastes(log)
    assert any(call[0] == "kill-session" for call in ctx.tmux.calls)
    assert _session(ctx).status == "stopped"


def test_stop_session_waits(ctx: SimpleNamespace, clock: FakeClock, log: list[Any]) -> None:
    """応答の途中なら、responding が偽になってから /exit を貼る。"""
    _write_session(ctx, responding=True)

    def finish(count: int) -> None:
        """2 回目の確認の後に応答を終える。"""
        if count == 2:
            state.update_session(
                ctx.state_root,
                WORKSPACE_ID,
                lambda current: None if current is None else current.replace(responding=False),
            )

    clock.on_sleep = finish
    sessions.stop_session(WORKSPACE_ID, SESSION_ID, False, ctx, spawn=_spawn(ctx, []))
    second_sleep = log.index(("sleep", 2))
    assert _exit_pastes(log)[0] > second_sleep


def test_stop_session_wait_limit(
    ctx: SimpleNamespace, clock: FakeClock, log: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """上限を過ぎたら止めずに pending_write を真にし、running に戻す。"""
    monkeypatch.setenv("MINDSTELLA_STOP_WAIT_TIMEOUT", "2")
    _write_session(ctx, responding=True)
    sessions.stop_session(WORKSPACE_ID, SESSION_ID, False, ctx, spawn=_spawn(ctx, []))
    assert _exit_pastes(log) == []
    current = _session(ctx)
    assert (current.pending_write, current.status, current.close_pending) == (True, "running", True)


def _record_commits(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """まとめていない変更があることにし、commit の説明を控える。"""
    summaries: list[str] = []
    monkeypatch.setattr(
        commands,
        "run_pending",
        lambda _root: {"added": [{"id": "Q-1", "title": "t"}], "changed": [], "removed": []},
    )
    monkeypatch.setattr(
        commands, "run_commit", lambda _root, summary, *_args: summaries.append(summary) or {}
    )
    return summaries


def test_stop_session_crashed(
    ctx: SimpleNamespace, clock: FakeClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """落ちていれば 200 で停止済みにし、落ちていた旨を添えて commit する。"""
    summaries = _record_commits(monkeypatch)
    _write_session(ctx)
    ctx.tmux.pane_alive = False
    status, body = sessions.stop_session(
        WORKSPACE_ID, SESSION_ID, False, ctx, spawn=_spawn(ctx, [])
    )
    assert (status, body) == (200, {"session": SESSION_ID, "status": "stopped"})
    assert len(summaries) == 1
    assert "落ち" in summaries[0]
    assert _session(ctx).status == "stopped"


def test_stop_session_forced(
    ctx: SimpleNamespace, clock: FakeClock, log: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """強制なら応答の終わりを待たずに SIGTERM と kill-session で止め、強制の旨を添えて commit する。"""
    summaries = _record_commits(monkeypatch)
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(sessions.os, "kill", lambda pid, sig: killed.append((pid, sig)))
    _write_session(ctx, responding=True)
    status, _body = sessions.stop_session(
        WORKSPACE_ID, SESSION_ID, True, ctx, spawn=_spawn(ctx, [])
    )
    assert status == 202
    assert _exit_pastes(log) == []
    assert killed == [(PID, signal.SIGTERM)]
    assert any(call[0] == "kill-session" for call in ctx.tmux.calls)
    assert len(summaries) == 1
    assert "強制" in summaries[0]


def test_stop_session_thread_error(
    ctx: SimpleNamespace, clock: FakeClock, caplog: pytest.LogCaptureFixture
) -> None:
    """止める間の例外は記録し、running に戻して last_error に段階を入れる。"""
    _write_session(ctx)
    ctx.tmux.fail_on_exit_paste = True
    with caplog.at_level(logging.ERROR):
        sessions.stop_session(WORKSPACE_ID, SESSION_ID, False, ctx, spawn=_spawn(ctx, []))
    records = [
        record
        for record in caplog.records
        if record.getMessage() == "mindstella.session.stop_failed"
    ]
    assert len(records) == 1
    assert getattr(records[0], "workspace_id", None) == WORKSPACE_ID
    assert getattr(records[0], "stage", None) == "exit"
    current = _session(ctx)
    assert current.status == "running"
    assert current.last_error is not None
    assert "exit" in current.last_error
    assert current.close_pending is True


@pytest.mark.parametrize(
    ("before", "event", "recorded", "check"),
    [
        pytest.param(
            {"claude_session_id": None},
            {
                "event": "session_start",
                "claude_session_id": "c1",
                "source": "startup",
                "pane": "%3",
                "pid": 7,
                "pid_started_at": "9",
                "claude_config_dir": "/c",
            },
            True,
            {"claude_session_id": "c1", "pid": 7, "pid_started_at": "9", "claude_config_dir": "/c"},
            id="start",
        ),
        pytest.param(
            {"claude_config_dir": "/c"},
            {
                "event": "session_start",
                "claude_session_id": "c2",
                "source": "clear",
                "claude_config_dir": "/d",
            },
            True,
            {"claude_session_id": "c2", "claude_config_dir": "/d"},
            id="start-clear",
        ),
        pytest.param(
            {},
            {"event": "session_start", "claude_session_id": "c3", "source": "fork"},
            True,
            {"claude_session_id": "c3"},
            id="start-fork",
        ),
        pytest.param(
            {},
            {"event": "session_end", "claude_session_id": "c1", "reason": "clear"},
            True,
            {"status": "running"},
            id="end-clear",
        ),
        pytest.param(
            {"responding": True},
            {"event": "session_end", "claude_session_id": "c1", "reason": "logout"},
            True,
            {"status": "stopped", "responding": False},
            id="end-logout",
        ),
        pytest.param(
            {},
            {"event": "prompt_submit", "claude_session_id": "c1"},
            True,
            {"responding": True},
            id="prompt",
        ),
        pytest.param(
            {"responding": True},
            {"event": "stop_failure", "claude_session_id": "c1"},
            True,
            {"responding": False},
            id="stop-failure",
        ),
    ],
)
def test_record_event(
    before: dict[str, Any],
    event: dict[str, Any],
    recorded: bool,
    check: dict[str, Any],
    ctx: SimpleNamespace,
) -> None:
    """出来事ごとに状態を書き換える。"""
    _write_session(ctx, **before)
    assert sessions.record_event(SESSION_ID, event, ctx) is recorded
    current = _session(ctx)
    for key, value in check.items():
        assert getattr(current, key) == value


def test_record_event_unknown(ctx: SimpleNamespace) -> None:
    """状態に無い MindStella のセッションは記録せず False を返す。"""
    _write_session(ctx)
    before = _session(ctx)
    assert (
        sessions.record_event(
            "S-ffffffffffff", {"event": "prompt_submit", "claude_session_id": "x"}, ctx
        )
        is False
    )
    assert _session(ctx) == before


def test_record_event_when_stop(ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    """stop で書き込んだ応答の通知を呼ぶ（正常系）。"""
    # 準備
    _write_session(ctx, responding=True)
    called: list[str] = []
    monkeypatch.setattr(
        notify,
        "notify_if_written",
        lambda workspace_id, _describe, **_kwargs: called.append(workspace_id),
    )
    # 実行
    recorded = sessions.record_event(SESSION_ID, {"event": "stop", "claude_session_id": "c1"}, ctx)
    # 検証
    assert recorded is True
    assert called == [WORKSPACE_ID]
    assert _session(ctx).responding is False


@pytest.mark.parametrize(
    "event",
    [
        pytest.param({"event": "prompt_submit", "claude_session_id": "c1"}, id="prompt"),
        pytest.param({"event": "stop_failure", "claude_session_id": "c1"}, id="stop-failure"),
        pytest.param(
            {"event": "session_end", "claude_session_id": "c1", "reason": "logout"},
            id="session-end",
        ),
    ],
)
def test_record_event_when_clearing(
    event: dict[str, Any],
    ctx: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """prompt_submit・stop_failure・session_end では通知せずにマーカーを解除する（正常系）。"""
    # 準備
    _write_session(ctx, responding=True)
    monkeypatch.setattr(notify, "MARKERS", notify.WriteMarkers())
    notify.MARKERS.mark(WORKSPACE_ID)
    called: list[str] = []
    monkeypatch.setattr(
        notify,
        "notify_if_written",
        lambda workspace_id, _describe, **_kwargs: called.append(workspace_id),
    )
    # 実行
    sessions.record_event(SESSION_ID, event, ctx)
    # 検証
    assert notify.MARKERS.take(WORKSPACE_ID) is False
    assert called == []


@pytest.mark.parametrize(
    ("status", "notified"),
    [
        pytest.param("running", 1, id="running"),
        pytest.param("stopping", 0, id="stopping"),
    ],
)
def test_is_alive_when_crashed_from_running(
    status: str, notified: int, ctx: SimpleNamespace
) -> None:
    """running から落ちたときだけ on_crashed を呼ぶ（正常系）。"""
    # 準備
    _write_session(ctx, status=status)
    ctx.tmux.pane_alive = False
    calls: list[bool] = []
    # 実行
    alive = sessions.is_alive(
        ctx.state_root, WORKSPACE_ID, ctx.tmux, ctx.proc, on_crashed=lambda: calls.append(True)
    )
    # 検証
    assert alive is False
    assert _session(ctx).status == "crashed"
    assert len(calls) == notified


def _spawn_after(
    ctx: SimpleNamespace, before_body: Callable[[], None]
) -> Callable[[Callable[[], None]], None]:
    """止める処理を同じスレッドで走らせ、走らせる直前に決めた処理を挟む。"""

    def spawn(body: Callable[[], None]) -> None:
        """挟んでから走らせる。"""
        before_body()
        body()

    return spawn


def _set_status(ctx: SimpleNamespace, status: str | None) -> Callable[[], None]:
    """止める間に別の経路が状態を書き換えたことにする関数を作る。"""

    def apply() -> None:
        """status を書き換える（None なら何もしない）。"""
        if status is None:
            return
        state.update_session(
            ctx.state_root,
            WORKSPACE_ID,
            lambda current: None if current is None else current.replace(status=status),
        )

    return apply


@pytest.mark.parametrize(
    ("force", "written", "reason"),
    [
        pytest.param(False, None, "stop_requested", id="stopping"),
        pytest.param(False, "stopped", "stop_requested", id="session-end-first"),
        pytest.param(False, "crashed", "stop_requested", id="closed-while-stopping"),
        pytest.param(True, None, "force_stopped", id="forced"),
    ],
)
def test_stop_session_when_notifying(
    force: bool,
    written: str | None,
    reason: str,
    ctx: SimpleNamespace,
    clock: FakeClock,
    monkeypatch: pytest.MonkeyPatch,
    stopped_notices: list[tuple[str, str]],
) -> None:
    """止め終えたときに停止の依頼か強制停止を 1 回通知する（正常系）。"""
    # 準備
    monkeypatch.setattr(sessions.os, "kill", lambda _pid, _sig: None)
    _write_session(ctx)
    # 実行
    sessions.stop_session(
        WORKSPACE_ID, SESSION_ID, force, ctx, spawn=_spawn_after(ctx, _set_status(ctx, written))
    )
    # 検証
    assert _session(ctx).status == "stopped"
    assert stopped_notices == [(WORKSPACE_ID, reason)]


@pytest.mark.parametrize(
    ("pane_alive", "final_status", "notices"),
    [
        pytest.param(False, "crashed", [(WORKSPACE_ID, "stop_failed")], id="crashed"),
        pytest.param(True, "running", [], id="alive"),
    ],
)
def test_stop_session_when_stop_failed(
    pane_alive: bool,
    final_status: str,
    notices: list[tuple[str, str]],
    ctx: SimpleNamespace,
    clock: FakeClock,
    stopped_notices: list[tuple[str, str]],
) -> None:
    """止める間の失敗で crashed に戻したときだけ停止処理の失敗を通知する（異常系）。"""
    # 準備
    _write_session(ctx)
    ctx.tmux.fail_on_exit_paste = True

    def die() -> None:
        """止める処理の前にペインの生死を決める。"""
        ctx.tmux.pane_alive = pane_alive

    # 実行
    sessions.stop_session(WORKSPACE_ID, SESSION_ID, False, ctx, spawn=_spawn_after(ctx, die))
    # 検証
    current = _session(ctx)
    assert current.status == final_status
    assert current.last_error is not None
    assert stopped_notices == notices


def test_stop_session_when_crashed_before(
    ctx: SimpleNamespace, clock: FakeClock, stopped_notices: list[tuple[str, str]]
) -> None:
    """落ちていた MindStella のセッションへの停止は異常終了だけを通知する（正常系）。"""
    # 準備
    _write_session(ctx)
    ctx.tmux.pane_alive = False
    # 実行
    status, body = sessions.stop_session(
        WORKSPACE_ID, SESSION_ID, False, ctx, spawn=_spawn(ctx, [])
    )
    # 検証
    assert (status, body) == (200, {"session": SESSION_ID, "status": "stopped"})
    assert stopped_notices == [(WORKSPACE_ID, "crashed")]


@pytest.mark.parametrize(
    ("status", "reason", "notices"),
    [
        pytest.param(
            "running", "prompt_input_exit", [(WORKSPACE_ID, "session_ended")], id="running"
        ),
        pytest.param("stopping", "prompt_input_exit", [], id="stopping"),
        pytest.param("running", "clear", [], id="clear"),
    ],
)
def test_record_event_when_session_ended(
    status: str,
    reason: str,
    notices: list[tuple[str, str]],
    ctx: SimpleNamespace,
    stopped_notices: list[tuple[str, str]],
) -> None:
    """running からの session_end だけ Claude Code の終了を通知する（正常系）。"""
    # 準備
    _write_session(ctx, status=status)
    # 実行
    sessions.record_event(
        SESSION_ID, {"event": "session_end", "claude_session_id": "c1", "reason": reason}, ctx
    )
    # 検証
    assert stopped_notices == notices


def test_notify_stopped(ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    """ワークスペースの名前と画面の URL を添えて通知を呼ぶ（正常系）。"""
    # 準備
    ctx.previews.url_of = lambda _folder: "http://127.0.0.1:9100/w/mindstella-x-1/"
    received: list[tuple[str, str, Callable[[], Any]]] = []
    monkeypatch.setattr(
        notify,
        "notify_stopped",
        lambda workspace_id, reason, describe, **_kwargs: received.append(
            (workspace_id, reason, describe)
        ),
        raising=False,
    )
    # 実行
    sessions.notify_stopped(ctx, WORKSPACE_ID, "crashed")
    # 検証
    assert len(received) == 1
    workspace_id, reason, describe = received[0]
    assert (workspace_id, reason) == (WORKSPACE_ID, "crashed")
    assert describe() == ("家計簿", "http://127.0.0.1:9100/w/mindstella-x-1/")


def test_resume_status(ctx: SimpleNamespace, folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """セッションのワークスペースの状況を返す（正常系）。"""
    # 準備
    _write_session(ctx)
    monkeypatch.setattr(
        sessions.workspaces, "find_workspace_row", lambda *_args, **_kwargs: ctx.row
    )
    called: list[tuple[Path, str]] = []
    status = {"trigger": "resume", "until_seq": 7}

    def _summarize(root: Path, source: str, **_kwargs: Any) -> dict[str, Any]:
        """呼ばれたフォルダと契機を控えて、決めた状況を返す。"""
        called.append((root, source))
        return status

    monkeypatch.setattr(resume, "summarize_resume", _summarize)
    # 実行
    result = sessions.resume_status(SESSION_ID, {"source": "compact"}, ctx)
    # 検証
    assert called == [(folder, "compact")]
    assert result == status


def test_resume_status_when_unknown(ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    """知らないセッションは 404（異常系）。"""
    # 準備
    _write_session(ctx)
    monkeypatch.setattr(
        sessions.workspaces, "find_workspace_row", lambda *_args, **_kwargs: ctx.row
    )
    called: list[str] = []
    monkeypatch.setattr(
        resume, "summarize_resume", lambda *_args, **_kwargs: called.append("called")
    )
    # 実行・検証
    with pytest.raises(ApiError) as raised:
        sessions.resume_status("S-999999999999", {"source": "compact"}, ctx)
    assert raised.value.status == 404
    assert called == []


def _write_changes(folder: Path, last_seq: int) -> None:
    """ワークスペースの changes.yaml を、まとまり 0 件・まだまとめていない変更なしの last_seq で書く。"""
    (folder / ".mindstella" / "changes.yaml").write_text(
        f"last_seq: {last_seq}\nsets: []\npending: {{added: [], changed: []}}\n", encoding="utf-8"
    )


def test_advance_read_point(
    ctx: SimpleNamespace, folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """前回参照した時点を進める（正常系）。"""
    # 準備
    _write_session(ctx)
    monkeypatch.setattr(
        sessions.workspaces, "find_workspace_row", lambda *_args, **_kwargs: ctx.row
    )
    _write_changes(folder, 5)
    read_point.save_read_seq(folder, 3, state_root=ctx.state_root)
    # 実行
    result = sessions.advance_read_point(SESSION_ID, {"until_seq": 5}, ctx)
    # 検証
    assert result == {"read_seq": 5}


@pytest.mark.parametrize(
    "until_seq",
    [
        pytest.param("5", id="not_integer"),
        pytest.param(9, id="beyond_last_seq"),
    ],
)
def test_advance_read_point_when_invalid(
    ctx: SimpleNamespace, folder: Path, monkeypatch: pytest.MonkeyPatch, until_seq: object
) -> None:
    """通し番号でない値・範囲の外は 400（異常系）。"""
    # 準備
    _write_session(ctx)
    monkeypatch.setattr(
        sessions.workspaces, "find_workspace_row", lambda *_args, **_kwargs: ctx.row
    )
    _write_changes(folder, 5)
    read_point.save_read_seq(folder, 3, state_root=ctx.state_root)
    # 実行・検証
    with pytest.raises(ApiError) as raised:
        sessions.advance_read_point(SESSION_ID, {"until_seq": until_seq}, ctx)
    assert raised.value.status == 400
    assert read_point.load_read_seq(folder, state_root=ctx.state_root) == 3


def test_build_command_when_resume() -> None:
    """resume_id があれば --resume を付ける（正常系）。"""
    # 実行
    command = sessions.build_command(None, None, "balancer", None, resume_id="abc")
    # 検証
    assert command == [
        "balancer",
        "exec",
        "--client",
        "mindstella",
        "--",
        "claude",
        "--resume",
        "abc",
    ]


def test_build_env_when_compact() -> None:
    """圧縮の契機を渡す（正常系）。"""
    # 実行
    env = sessions.build_env(
        SESSION_ID, WORKSPACE_ID, 8784, None, None, True, launch_reason="compact"
    )
    # 検証
    assert env["MINDSTELLA_LAUNCH_REASON"] == "compact"


def _transcript(config_dir: Path, folder: Path, claude_session_id: str) -> Path:
    """会話の記録のファイルを Claude Code と同じ名前の作り方で作る。"""
    two_units = "".join("--" if ord(char) > 0xFFFF else char for char in str(folder))
    name = re.sub(r"[^A-Za-z0-9]", "-", two_units)
    path = config_dir / "projects" / name / f"{claude_session_id}.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("{}\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        pytest.param("recorded", "c1", id="recorded"),
        pytest.param("missing", None, id="transcript-missing"),
        pytest.param("no-id", None, id="no-claude-session-id"),
        pytest.param("no-state", None, id="no-state"),
    ],
)
def test_resume_id_for(case: str, expected: str | None, tmp_path: Path, folder: Path) -> None:
    """会話の記録のファイルの有無で決まる（正常系）。"""
    # 準備
    config_dir = tmp_path / "config"
    if case != "missing":
        _transcript(config_dir, folder, "c1")
    current: SessionState | None = SessionState(
        session=SESSION_ID,
        status="stopped",
        started_at="2026-11-15T00:00:00+00:00",
        claude_session_id=None if case == "no-id" else "c1",
        claude_config_dir=str(config_dir),
    )
    if case == "no-state":
        current = None
    # 実行・検証
    assert sessions.resume_id_for(current, folder) == expected


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        pytest.param("ok", None, id="readable"),
        pytest.param("plugin-missing", "plugin", id="plugin-missing"),
        pytest.param("mcp-invalid", "mcp", id="mcp-invalid"),
    ],
)
def test_check_launch_options(case: str, expected: str | None, tmp_path: Path) -> None:
    """プラグインのフォルダと MCP の定義を確かめる（正常系）。"""
    # 準備
    plugin = tmp_path / "plugin"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
    plugin_dirs = [str(plugin)]
    mcp_config: dict[str, Any] | None = {"mcpServers": {"extra": {"command": "x"}}}
    if case == "plugin-missing":
        plugin_dirs = [str(tmp_path / "gone")]
    if case == "mcp-invalid":
        mcp_config = {"servers": []}
    # 実行
    result = sessions.check_launch_options(
        LaunchOptions(mcp_config=mcp_config, plugin_dirs=plugin_dirs)
    )
    # 検証
    if expected is None:
        assert result is None
    elif expected == "plugin":
        assert result is not None
        assert str(tmp_path / "gone") in result
    else:
        assert result is not None
        assert "mcp" in result.lower()


def test_create_session_when_resume(
    ctx: SimpleNamespace, clock: FakeClock, tmp_path: Path, folder: Path
) -> None:
    """停止済みの記録の会話を引き継ぐ（正常系）。"""
    # 準備
    config_dir = tmp_path / "config"
    _transcript(config_dir, folder, "c0")
    _write_session(ctx, status="stopped", claude_session_id="c0", claude_config_dir=str(config_dir))
    _register_on_sleep(ctx, clock)
    # 実行
    status, body = sessions.create_session(WORKSPACE_ID, None, ctx)
    # 検証
    assert status == 201
    assert body["session"] != SESSION_ID
    respawn = next(call for call in ctx.tmux.calls if call[0] == "respawn-pane")
    assert respawn[-2:] == ["--resume", "c0"]


def test_create_session_when_launch_record_missing(ctx: SimpleNamespace, clock: FakeClock) -> None:
    """launch.json が無ければ指定なしで起動して警告を返す（正常系）。"""
    # 準備
    (state.workspace_dir(ctx.state_root, WORKSPACE_ID) / "launch.json").unlink()
    _register_on_sleep(ctx, clock)
    # 実行
    status, body = sessions.create_session(WORKSPACE_ID, None, ctx)
    # 検証
    assert status == 201
    assert body["warnings"] == ["launch_record_missing"]
    respawn = next(call for call in ctx.tmux.calls if call[0] == "respawn-pane")
    assert "--mcp-config" not in respawn
    assert "--plugin-dir" not in respawn


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        pytest.param(
            {"event": "stop_failure", "claude_session_id": "c1", "error": "rate_limit"},
            ["rate_limit"],
            id="rate-limit",
        ),
        pytest.param(
            {"event": "stop_failure", "claude_session_id": "c1", "error": "server_error"},
            [],
            id="server-error",
        ),
        pytest.param(
            {"event": "pre_compact", "claude_session_id": "c1"}, ["compact"], id="pre-compact"
        ),
    ],
)
def test_record_event_when_rate_limit(
    event: dict[str, Any],
    expected: list[str],
    ctx: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """stop_failure の rate_limit と pre_compact で起動し直しを始める（正常系）。"""
    # 準備
    _write_session(ctx)
    reasons: list[str] = []
    monkeypatch.setattr(
        sessions,
        "request_restart",
        lambda _workspace_id, reason, _ctx: reasons.append(reason) or True,
    )
    monkeypatch.setattr(sessions, "_start_thread", lambda body: body())
    # 実行
    assert sessions.record_event(SESSION_ID, event, ctx) is True
    # 検証
    assert reasons == expected


def test_record_event_when_restarting(
    ctx: SimpleNamespace, stopped_notices: list[tuple[str, str]]
) -> None:
    """起動し直しの途中の session_end は状態を変えず通知しない（正常系）。"""
    # 準備
    _write_session(ctx, status="restarting", responding=True)
    # 実行
    sessions.record_event(
        SESSION_ID, {"event": "session_end", "claude_session_id": "c1", "reason": "other"}, ctx
    )
    # 検証
    current = _session(ctx)
    assert (current.status, current.responding) == ("restarting", False)
    assert stopped_notices == []


class RestartTmux(FakeTmux):
    """/exit が貼られたら tmux のセッションを閉じる（exec が終わる）tmux の偽。"""

    def __init__(self, log: list[Any]) -> None:
        """セッションがある状態で始める。"""
        super().__init__(log)
        self.session_exists = True
        self.close_on_exit = True

    def run(self, args: list[str], stdin: bytes | None = None) -> tuple[int, str]:
        """/exit で閉じ、kill-session・new-session でセッションの有無を変える。"""
        result = super().run(args, stdin)
        if args[0] == "load-buffer" and stdin == b"/exit" and self.close_on_exit:
            self.session_exists = False
        if args[0] == "kill-session":
            self.session_exists = False
        if args[0] == "new-session":
            self.session_exists = True
        return result


@pytest.fixture
def restart_ctx(
    ctx: SimpleNamespace, log: list[Any], monkeypatch: pytest.MonkeyPatch
) -> SimpleNamespace:
    """起動し直しの tmux の偽を持ち、別のスレッドを同じスレッドで走らせる ctx。"""
    ctx.tmux = RestartTmux(log)
    ctx.proc = FakeProc(ctx.tmux)
    monkeypatch.setattr(sessions, "_start_thread", lambda body: body())
    monkeypatch.setattr(sessions.os, "kill", lambda _pid, _sig: None)
    return ctx


def _register_new_on_sleep(ctx: SimpleNamespace, clock: FakeClock, claude_session_id: str) -> None:
    """/exit の後の sleep で、起動し直した Claude Code の SessionStart が登録したことにする。"""

    def register(_count: int) -> None:
        """起動のコマンドを打った後だけ登録する。"""
        if not any(call[0] == "respawn-pane" for call in ctx.tmux.calls):
            return
        state.update_session(
            ctx.state_root,
            WORKSPACE_ID,
            lambda current: (
                None
                if current is None
                else current.replace(
                    claude_session_id=claude_session_id,
                    pid=PID + 1,
                    pid_started_at="67890",
                    claude_config_dir=current.claude_config_dir,
                )
            ),
        )

    clock.on_sleep = register


def test_restart_session(
    restart_ctx: SimpleNamespace, clock: FakeClock, tmp_path: Path, folder: Path
) -> None:
    """起動中を止めて --resume で起動し直す（正常系）。"""
    # 準備
    ctx = restart_ctx
    config_dir = tmp_path / "config"
    _transcript(config_dir, folder, "c1")
    _write_session(ctx, claude_config_dir=str(config_dir))
    ctx.proc.exit_on_paste = False
    _register_new_on_sleep(ctx, clock, "c2")
    # 実行
    status, body = sessions.restart_session(WORKSPACE_ID, SESSION_ID, "api", False, ctx)
    # 検証
    assert (status, body) == (202, {"session": SESSION_ID, "status": "restarting", "warnings": []})
    respawn = next(call for call in ctx.tmux.calls if call[0] == "respawn-pane")
    assert respawn[-2:] == ["--resume", "c1"]
    current = _session(ctx)
    assert (current.status, current.session, current.restart_reason) == (
        "running",
        SESSION_ID,
        None,
    )


@pytest.mark.parametrize(
    ("case", "stage"),
    [
        pytest.param("closed", "closed", id="closed"),
        pytest.param("stopping", "stopping", id="stopping"),
        pytest.param("restarting", "restarting", id="restarting"),
    ],
)
def test_restart_session_when_rejected(case: str, stage: str, restart_ctx: SimpleNamespace) -> None:
    """クローズ済み・停止の途中・起動し直しの途中は 409（異常系）。"""
    # 準備
    ctx = restart_ctx
    _write_session(ctx, status="running" if case == "closed" else case)
    if case == "closed":
        ctx.row["outsideRead"] = False
    # 実行・検証
    with pytest.raises(ApiError) as caught:
        sessions.restart_session(WORKSPACE_ID, SESSION_ID, "api", False, ctx)
    assert (caught.value.status, caught.value.stage) == (409, stage)


@pytest.mark.parametrize(
    ("reason", "case", "error_prefix", "notices"),
    [
        pytest.param("api", "no-account", "account:", [(WORKSPACE_ID, "restart_failed")], id="api"),
        pytest.param("comment", "no-account", "account:", [], id="comment"),
        pytest.param(
            "api",
            "plugin-missing",
            "launch_options:",
            [(WORKSPACE_ID, "restart_failed")],
            id="plugin-missing",
        ),
    ],
)
def test_restart_session_when_launch_failed(
    reason: str,
    case: str,
    error_prefix: str,
    notices: list[tuple[str, str]],
    restart_ctx: SimpleNamespace,
    clock: FakeClock,
    tmp_path: Path,
    stopped_notices: list[tuple[str, str]],
) -> None:
    """起動に失敗すると crashed と last_error、契機で通知を呼び分ける（異常系）。"""
    # 準備
    ctx = restart_ctx
    _write_session(ctx, status="crashed")
    ctx.tmux.session_exists = False
    if case == "no-account":
        ctx.tmux.pane_dead = "1 125"
    else:
        state.write_launch(
            ctx.state_root,
            WORKSPACE_ID,
            LaunchOptions(mcp_config=None, plugin_dirs=[str(tmp_path / "gone")]),
        )
    # 実行
    sessions.restart_session(WORKSPACE_ID, SESSION_ID, reason, False, ctx)
    # 検証
    current = _session(ctx)
    assert current.status == "crashed"
    assert current.last_error is not None
    assert current.last_error.startswith(error_prefix)
    assert stopped_notices == notices
    if case == "plugin-missing":
        assert not any(call[0] == "respawn-pane" for call in ctx.tmux.calls)


def test_restart_session_when_rate_limited(
    restart_ctx: SimpleNamespace,
    clock: FakeClock,
    monkeypatch: pytest.MonkeyPatch,
    stopped_notices: list[tuple[str, str]],
) -> None:
    """利用上限の契機では止めた後に rate_limited を通知し、report-limit を呼ばない（正常系）。"""
    # 準備
    ctx = restart_ctx
    _write_session(ctx, responding=True)
    ctx.proc.exit_on_paste = False
    _register_new_on_sleep(ctx, clock, "c2")
    commands_run: list[list[str]] = []
    monkeypatch.setattr(
        sessions.subprocess, "run", lambda args, **_kwargs: commands_run.append(list(args))
    )
    # 実行
    sessions.restart_session(WORKSPACE_ID, SESSION_ID, "rate_limit", False, ctx)
    # 検証
    assert stopped_notices == [(WORKSPACE_ID, "rate_limited")]
    assert not any("report-limit" in args for args in commands_run)
    assert _session(ctx).status == "running"


def test_restart_session_when_exec_slow(restart_ctx: SimpleNamespace, clock: FakeClock) -> None:
    """exec が上限までに終わらなければ kill-session してから起動する（正常系）。"""
    # 準備
    ctx = restart_ctx
    ctx.tmux.close_on_exit = False
    _write_session(ctx)
    _register_new_on_sleep(ctx, clock, "c2")
    # 実行
    sessions.restart_session(WORKSPACE_ID, SESSION_ID, "api", False, ctx)
    # 検証
    names = [call[0] for call in ctx.tmux.calls]
    kill = names.index("kill-session")
    assert kill < names.index("new-session")
    assert clock.now >= sessions.EXEC_EXIT_WAIT_SEC


def test_restart_session_when_write_timeout(
    restart_ctx: SimpleNamespace, clock: FakeClock, log: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """最後の書き込みを待つ上限を過ぎたら起動し直さず running に戻す（異常系）。"""
    # 準備
    ctx = restart_ctx
    monkeypatch.setenv("MINDSTELLA_STOP_WAIT_TIMEOUT", "2")
    _write_session(ctx, responding=True)
    # 実行
    sessions.restart_session(WORKSPACE_ID, SESSION_ID, "api", False, ctx)
    # 検証
    assert _exit_pastes(log) == []
    current = _session(ctx)
    assert (current.status, current.pending_write, current.restart_reason) == (
        "running",
        True,
        None,
    )


@pytest.mark.parametrize(
    ("status", "close_pending", "reason", "expected", "calls"),
    [
        pytest.param("crashed", False, "comment", True, 1, id="crashed-comment"),
        pytest.param("restarting", False, "comment", True, 0, id="restarting-comment"),
        pytest.param("crashed", True, "comment", False, 0, id="close-pending-comment"),
        pytest.param("running", False, "rate_limit", True, 1, id="running-rate-limit"),
    ],
)
def test_request_restart(
    status: str,
    close_pending: bool,
    reason: str,
    expected: bool,
    calls: int,
    ctx: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """契機と状態で始めるかが決まる（正常系）。"""
    # 準備
    _write_session(ctx, status=status, close_pending=close_pending)
    called: list[tuple[str, str | None, str, bool]] = []

    def _restart(
        workspace_id: str, session_id: str | None, reason: str, force: bool, _ctx: Any
    ) -> tuple[int, dict[str, Any]]:
        """呼ばれた引数を控える。"""
        called.append((workspace_id, session_id, reason, force))
        return 202, {"session": SESSION_ID, "status": "restarting", "warnings": []}

    monkeypatch.setattr(sessions, "restart_session", _restart)
    # 実行・検証
    assert sessions.request_restart(WORKSPACE_ID, reason, ctx) is expected
    assert len(called) == calls


@pytest.mark.parametrize(
    ("after", "expected"),
    [pytest.param("running", True, id="running"), pytest.param("crashed", False, id="crashed")],
)
def test_wait_until_running(
    after: str, expected: bool, ctx: SimpleNamespace, clock: FakeClock
) -> None:
    """restarting の後の状態で返り値が決まる（正常系）。"""
    # 準備
    _write_session(ctx, status="restarting")

    def finish(count: int) -> None:
        """2 回目の確認の前に状態を変える。"""
        if count == 1:
            state.update_session(
                ctx.state_root,
                WORKSPACE_ID,
                lambda current: None if current is None else current.replace(status=after),
            )

    clock.on_sleep = finish
    # 実行・検証
    assert sessions.wait_until_running(WORKSPACE_ID, ctx) is expected


def test_watch_crashes_once(ctx: SimpleNamespace, stopped_notices: list[tuple[str, str]]) -> None:
    """running で落ちているものだけ crashed にして通知する（正常系）。"""
    # 準備
    others = ["mindstella-b-000001", "mindstella-c-000002"]
    for workspace_id in others:
        state.add_id(ctx.state_root, workspace_id)
    _write_session(ctx, pane="%dead")
    state.update_session(
        ctx.state_root,
        others[0],
        lambda _current: SessionState(
            session="S-000000000001", status="restarting", started_at="t", pane="%dead"
        ),
    )
    state.update_session(
        ctx.state_root,
        others[1],
        lambda _current: SessionState(
            session="S-000000000002",
            status="running",
            started_at="t",
            pane="%alive",
            pid=PID,
            pid_started_at=PID_STARTED_AT,
        ),
    )
    original = ctx.tmux.run

    def run(args: list[str], stdin: bytes | None = None) -> tuple[int, str]:
        """%dead のペインだけ無いことにする。"""
        if args[0] == "display-message" and "%dead" in args:
            return 1, ""
        return original(args, stdin)

    ctx.tmux.run = run
    # 実行
    count = sessions.watch_crashes_once(ctx)
    # 検証
    assert count == 1
    assert _session(ctx).status == "crashed"
    restarting = state.read_session(ctx.state_root, others[0])
    alive = state.read_session(ctx.state_root, others[1])
    assert restarting is not None
    assert alive is not None
    assert (restarting.status, alive.status) == ("restarting", "running")
    assert stopped_notices == [(WORKSPACE_ID, "crashed")]


def test_start_crash_watch(ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    """間隔ごとに見回り、stop で終わる（正常系）。"""
    # 準備
    monkeypatch.setenv("MINDSTELLA_CRASH_WATCH_INTERVAL", "0.01")
    calls: list[int] = []
    twice = threading.Event()

    def _watch(_ctx: Any) -> int:
        """呼ばれた回数を数える。"""
        calls.append(1)
        if len(calls) >= 2:
            twice.set()
        return 0

    monkeypatch.setattr(sessions, "watch_crashes_once", _watch)
    stop = threading.Event()
    # 実行
    thread = sessions.start_crash_watch(ctx, stop)
    assert twice.wait(5)
    stop.set()
    thread.join(5)
    # 検証
    assert len(calls) >= 2
    assert not thread.is_alive()


@pytest.mark.parametrize(
    ("balancer_url", "expected"),
    [
        pytest.param("http://127.0.0.1:8780", "http://127.0.0.1:8780", id="url"),
        pytest.param(None, None, id="none"),
    ],
)
def test_build_env_when_balancer_url(balancer_url: str | None, expected: str | None) -> None:
    """ホームの設定の待ち受け先を渡す（正常系）。"""
    # 実行
    env = sessions.build_env(
        SESSION_ID, WORKSPACE_ID, 8784, None, None, True, balancer_url=balancer_url
    )
    # 検証
    assert env.get("CLAUDE_BALANCER_URL") == expected


@pytest.mark.parametrize(
    ("config_dir", "expected"),
    [pytest.param("~/c", "{home}/c", id="specified"), pytest.param(None, None, id="none")],
)
def test_create_session_records_specified_account(
    config_dir: str | None,
    expected: str | None,
    ctx: SimpleNamespace,
    clock: FakeClock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """依頼の claude_config_dir を specified_account に記録する（正常系）。"""
    # 準備
    monkeypatch.setenv("HOME", str(tmp_path))
    _register_on_sleep(ctx, clock)
    # 実行
    sessions.create_session(WORKSPACE_ID, config_dir, ctx)
    # 検証
    assert _session(ctx).specified_account == (
        expected.format(home=tmp_path) if expected else None
    )


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        pytest.param(
            {"event": "session_start", "claude_session_id": "c2", "balancer_account": "a"},
            "a",
            id="account",
        ),
        pytest.param({"event": "session_start", "claude_session_id": "c2"}, None, id="none"),
    ],
)
def test_record_event_balancer_account(
    event: dict[str, Any], expected: str | None, ctx: SimpleNamespace
) -> None:
    """session_start の balancer_account を記録する（正常系）。"""
    # 準備
    _write_session(ctx)
    # 実行
    sessions.record_event(SESSION_ID, event, ctx)
    # 検証
    assert _session(ctx).balancer_account == expected


def test_restart_session_when_usage_threshold(
    restart_ctx: SimpleNamespace,
    clock: FakeClock,
    log: list[Any],
    stopped_notices: list[tuple[str, str]],
) -> None:
    """しきい値の契機では応答の終わりを待ち、usage_threshold を通知する（正常系）。"""
    # 準備
    ctx = restart_ctx
    _write_session(ctx, responding=True)
    ctx.proc.exit_on_paste = False

    def finish_then_register(count: int) -> None:
        """3 回目の sleep で応答を終え、起動のコマンドの後に登録する。"""
        if count == 3:
            state.update_session(
                ctx.state_root,
                WORKSPACE_ID,
                lambda current: None if current is None else current.replace(responding=False),
            )
        if any(call[0] == "respawn-pane" for call in ctx.tmux.calls):
            state.update_session(
                ctx.state_root,
                WORKSPACE_ID,
                lambda current: (
                    None
                    if current is None
                    else current.replace(
                        claude_session_id="c2", pid=PID + 1, pid_started_at="67890"
                    )
                ),
            )

    clock.on_sleep = finish_then_register
    # 実行
    sessions.restart_session(WORKSPACE_ID, SESSION_ID, "usage_threshold", False, ctx)
    # 検証
    exit_at = next(
        index for index, entry in enumerate(log) if entry[0] == "tmux" and entry[2] == b"/exit"
    )
    assert ("sleep", 3) in log[:exit_at]
    assert stopped_notices == [(WORKSPACE_ID, "usage_threshold")]
    assert _session(ctx).status == "running"


@pytest.mark.parametrize(
    ("reason", "has_account", "expected_specified"),
    [
        pytest.param("api", True, "/c", id="api"),
        pytest.param("rate_limit", False, None, id="rate-limit"),
        pytest.param("usage_threshold", False, None, id="usage-threshold"),
        pytest.param("compact", True, "/c", id="compact"),
    ],
)
def test_restart_session_with_specified_account(
    reason: str,
    has_account: bool,
    expected_specified: str | None,
    restart_ctx: SimpleNamespace,
    clock: FakeClock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """specified_account と契機と release_on_limit で --account が決まる（正常系）。"""
    # 準備
    ctx = restart_ctx
    monkeypatch.setattr(sessions.shutil, "which", lambda _name: "/usr/bin/claude-balancer")
    _write_session(ctx, specified_account="/c")
    ctx.proc.exit_on_paste = False
    _register_new_on_sleep(ctx, clock, "c2")
    # 実行
    sessions.restart_session(WORKSPACE_ID, SESSION_ID, reason, False, ctx)
    # 検証
    respawn = next(call for call in ctx.tmux.calls if call[0] == "respawn-pane")
    assert ("--account" in respawn) is has_account
    assert _session(ctx).specified_account == expected_specified


def test_restart_session_when_release_off(
    restart_ctx: SimpleNamespace,
    clock: FakeClock,
    monkeypatch: pytest.MonkeyPatch,
    stopped_notices: list[tuple[str, str]],
) -> None:
    """release_on_limit が偽で利用上限なら起動し直さない（異常系）。"""
    # 準備
    ctx = restart_ctx
    ctx.home = HomeSettings(None, False)
    monkeypatch.setattr(sessions.shutil, "which", lambda _name: "/usr/bin/claude-balancer")
    _write_session(ctx, specified_account="/c")
    # 実行
    sessions.restart_session(WORKSPACE_ID, SESSION_ID, "rate_limit", False, ctx)
    # 検証
    assert not any(call[0] == "respawn-pane" for call in ctx.tmux.calls)
    current = _session(ctx)
    assert current.status == "crashed"
    assert (current.last_error or "").startswith("account:")
    assert stopped_notices == [(WORKSPACE_ID, "rate_limited")]


class AccountTmux(RestartTmux):
    """--account を付けた起動は 125 で終わる tmux の偽。"""

    def run(self, args: list[str], stdin: bytes | None = None) -> tuple[int, str]:
        """respawn-pane の引数でペインの終わり方を決める。"""
        if args[0] == "respawn-pane":
            self.pane_dead = "1 125" if "--account" in args else "0 0"
        return super().run(args, stdin)


@pytest.mark.parametrize(
    ("release_on_limit", "respawns", "last_has_account", "status", "specified"),
    [
        pytest.param(True, 2, False, "running", None, id="release-on"),
        pytest.param(False, 1, True, "crashed", "/c", id="release-off"),
    ],
)
def test_restart_session_when_specified_account_unavailable(
    release_on_limit: bool,
    respawns: int,
    last_has_account: bool,
    status: str,
    specified: str | None,
    restart_ctx: SimpleNamespace,
    clock: FakeClock,
    log: list[Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--account 付きの起動が account の段階で失敗したら、指定を解除して 1 回だけ起動し直す（正常系）。"""
    # 準備
    ctx = restart_ctx
    ctx.tmux = AccountTmux(log)
    ctx.proc = FakeProc(ctx.tmux)
    ctx.home = HomeSettings(None, release_on_limit)
    monkeypatch.setattr(sessions.shutil, "which", lambda _name: "/usr/bin/claude-balancer")
    _write_session(ctx, status="crashed", specified_account="/c")
    ctx.tmux.session_exists = False

    def register_without_account(_count: int) -> None:
        """--account の無い起動の後だけ登録する。"""
        respawned = [call for call in ctx.tmux.calls if call[0] == "respawn-pane"]
        if respawned and "--account" not in respawned[-1]:
            state.update_session(
                ctx.state_root,
                WORKSPACE_ID,
                lambda current: (
                    None
                    if current is None
                    else current.replace(
                        claude_session_id="c2", pid=PID + 1, pid_started_at="67890"
                    )
                ),
            )

    clock.on_sleep = register_without_account
    # 実行
    sessions.restart_session(WORKSPACE_ID, SESSION_ID, "api", False, ctx)
    # 検証
    respawned = [call for call in ctx.tmux.calls if call[0] == "respawn-pane"]
    assert len(respawned) == respawns
    assert ("--account" in respawned[-1]) is last_has_account
    current = _session(ctx)
    assert (current.status, current.specified_account) == (status, specified)


def test_request_restart_when_usage_threshold(
    ctx: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """usage_threshold の契機を受け付ける（正常系）。"""
    # 準備
    _write_session(ctx)
    called: list[str] = []
    monkeypatch.setattr(
        sessions,
        "restart_session",
        lambda _workspace_id, _session_id, reason, _force, _ctx: called.append(reason)
        or (202, {}),
    )
    # 実行
    result = sessions.request_restart(WORKSPACE_ID, "usage_threshold", ctx)
    # 検証
    assert result is True
    assert called == ["usage_threshold"]
