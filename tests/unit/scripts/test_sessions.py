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
import sessions
import state
from errors import ApiError
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
    (plugin_root / "skills" / "mindmap" / "references").mkdir(parents=True)
    (plugin_root / "skills" / "mindmap" / "references" / "起動時の指示.md").write_text(
        "起動時の指示", encoding="utf-8"
    )
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
    previews = SimpleNamespace(start=lambda _root: ("http://127.0.0.1:9100/mindstella.html", False))
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
        """claude_session_id と PID を入れる。"""
        if count == 1:
            state.update_session(
                ctx.state_root,
                WORKSPACE_ID,
                lambda current: (
                    None
                    if current is None
                    else current.replace(
                        claude_session_id="c1", pid=PID, pid_started_at=PID_STARTED_AT
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
    ("options", "mcp_file", "balancer", "expected"),
    [
        pytest.param(
            LaunchOptions(mcp_config={"mcpServers": {}}, plugin_dirs=["p"]),
            Path("f"),
            "/usr/bin/claude-balancer",
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
                "--append-system-prompt",
                "s",
            ],
            id="balancer",
        ),
        pytest.param(
            LaunchOptions(mcp_config=None, plugin_dirs=[]),
            None,
            None,
            ["claude", "--append-system-prompt", "s"],
            id="no-balancer",
        ),
        pytest.param(None, None, None, ["claude", "--append-system-prompt", "s"], id="no-record"),
    ],
)
def test_build_command(
    options: LaunchOptions | None, mcp_file: Path | None, balancer: str | None, expected: list[str]
) -> None:
    """claude-balancer の有無と指定で並びが変わる。"""
    assert sessions.build_command(options, mcp_file, "s", balancer) == expected


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
    assert body["url"] == "http://127.0.0.1:9100/mindstella.html"
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
    monkeypatch.setattr(sessions, "is_alive", lambda *_args: True)
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


@pytest.mark.parametrize(
    ("written", "pane_alive", "expected"),
    [
        pytest.param(False, True, None, id="never-created"),
        pytest.param(True, True, "running", id="running"),
        pytest.param(True, False, "crashed", id="crashed"),
    ],
)
def test_list_sessions(
    written: bool, pane_alive: bool, expected: str | None, ctx: SimpleNamespace
) -> None:
    """最後の MindStella のセッションを 1 つ返し、落ちていれば crashed にする。"""
    if written:
        _write_session(ctx)
    ctx.tmux.pane_alive = pane_alive
    body = sessions.list_sessions(WORKSPACE_ID, ctx)
    if expected is None:
        assert body["sessions"] == []
        return
    assert [entry["status"] for entry in body["sessions"]] == [expected]
    assert body["sessions"][0]["id"] == SESSION_ID
    assert body["close_pending"] is False


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
            },
            True,
            {"claude_session_id": "c1", "pid": 7, "pid_started_at": "9"},
            id="start",
        ),
        pytest.param(
            {},
            {"event": "session_start", "claude_session_id": "c2", "source": "clear"},
            True,
            {"claude_session_id": "c2"},
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
        pytest.param(False, "crashed", "stop_requested", id="listed-while-stopping"),
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
    ctx.previews.url_of = lambda _folder: "http://127.0.0.1:9100/mindstella.html"
    received: list[tuple[str, str, Callable[[], Any]]] = []
    monkeypatch.setattr(
        notify,
        "notify_stopped",
        lambda workspace_id, reason, describe, **_kwargs: received.append(
            (workspace_id, reason, describe)
        ),
    )
    # 実行
    sessions.notify_stopped(ctx, WORKSPACE_ID, "crashed")
    # 検証
    assert len(received) == 1
    workspace_id, reason, describe = received[0]
    assert (workspace_id, reason) == (WORKSPACE_ID, "crashed")
    assert describe() == ("家計簿", "http://127.0.0.1:9100/mindstella.html")
