"""claude_input.py（まとめて送った後の Claude Code への入力：送り先・tmux への貼り付け・会話の記録での確かめ）の単体テスト。"""

from __future__ import annotations

import json
import logging
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import claude_input

# 会話の記録の user の行に入る作業フォルダと、そのフォルダに当たる会話の記録のフォルダ名
WORK_DIR = Path("/work/ws")
WORK_FOLDER_NAME = "-work-ws"

# 届いたかの判定で探す、入力した文字列
TEXT = "[mindstella] ユーザーからのコメントが 3 件届きました。読み直してください。"

# 件数 2 で入力する文字列と、その UTF-8 のバイト列
INPUT_TEXT_2 = "[mindstella] ユーザーからのコメントが 2 件届きました。読み直してください。"
INPUT_BYTES_2 = INPUT_TEXT_2.encode("utf-8")

# 名前が 230 文字になる作業フォルダと、その名前の先頭 200 文字（`-` を含む）
LONG_CWD = Path("/" + "a" * 229)
LONG_PREFIX = "-" + "a" * 199

# tmux の送り先（セッションの TMUX と、その最初の , より前のソケット）
TMUX = "/s,1,0"
SOCKET = "/s"
PANE = "%3"

# 宛先の Claude Code のプロセスの PID と、空白を 1 つにつめた起動時刻
CLAUDE_PID = 40
STARTED_AT = "Mon Nov 2 10:00:00 2026"

# 生きている宛先に ps・tmux が返す値（`ps -o lstart=` は空白の並びを含む）
ALIVE_RESPONSES: dict[tuple[str, ...], tuple[int, str]] = {
    ("ps", "-o", "lstart=", "-p", "40"): (0, "Mon Nov  2 10:00:00 2026\n"),
    ("tmux", "-S", "/s", "display-message", "-p", "-t", "%3", "#{pane_pid}"): (0, "10\n"),
    ("ps", "-o", "ppid=", "-p", "40"): (0, "   20\n"),
    ("ps", "-o", "ppid=", "-p", "20"): (0, "   10\n"),
}

# ペインで直に Claude Code を動かした宛先に ps・tmux が返す値
DIRECT_RESPONSES: dict[tuple[str, ...], tuple[int, str]] = {
    ("ps", "-o", "lstart=", "-p", "40"): (0, "Mon Nov  2 10:00:00 2026\n"),
    ("tmux", "-S", "/s", "display-message", "-p", "-t", "%3", "#{pane_pid}"): (0, "40\n"),
}

# 宛先が生きているかを確かめるコマンドの鍵
LSTART_KEY = ("ps", "-o", "lstart=", "-p", "40")
DISPLAY_KEY = ("tmux", "-S", "/s", "display-message", "-p", "-t", "%3", "#{pane_pid}")
PPID_40_KEY = ("ps", "-o", "ppid=", "-p", "40")
PPID_20_KEY = ("ps", "-o", "ppid=", "-p", "20")

# 呼び出しの打ち切り時刻と、その手前の時刻・過ぎた時刻
DEADLINE = 1.0
CLOCK_BEFORE = 0.0
CLOCK_AFTER = 2.0

# 会話の記録の行（jsonl の 1 行。改行で終わる）
USER_LINE = (
    json.dumps(
        {
            "type": "user",
            "cwd": "/work/ws",
            "message": {"role": "user", "content": TEXT},
        },
        ensure_ascii=False,
    )
    + "\n"
)
USER_LINE_BLOCKS = (
    json.dumps(
        {
            "type": "user",
            "cwd": "/work/ws",
            "message": {"role": "user", "content": [{"type": "text", "text": TEXT}]},
        },
        ensure_ascii=False,
    )
    + "\n"
)
USER_LINE_OTHER_CWD = (
    json.dumps(
        {"type": "user", "cwd": "/other", "message": {"role": "user", "content": TEXT}},
        ensure_ascii=False,
    )
    + "\n"
)
USER_LINE_OTHER_TEXT = (
    json.dumps(
        {
            "type": "user",
            "cwd": "/work/ws",
            "message": {"role": "user", "content": "別の発言"},
        },
        ensure_ascii=False,
    )
    + "\n"
)
ENQUEUE_LINE = json.dumps({"type": "queue-operation", "operation": "enqueue"}) + "\n"
DEQUEUE_LINE = json.dumps({"type": "queue-operation", "operation": "dequeue"}) + "\n"
PARTIAL_USER_LINE = USER_LINE.rstrip("\n")


def _target(tmp_path: Path) -> claude_input.InputTarget:
    """作業フォルダが `/work/ws`・設定のフォルダが tmp_path の下の送り先を作る。"""
    return claude_input.InputTarget(
        socket=SOCKET,
        pane=PANE,
        config_dir=tmp_path / "cfg",
        cwd=WORK_DIR,
        claude_pid=CLAUDE_PID,
        claude_started_at=STARTED_AT,
    )


def _target_at(config_dir: Path, cwd: Path) -> claude_input.InputTarget:
    """設定のフォルダと作業フォルダを決めた送り先を作る。"""
    return claude_input.InputTarget(
        socket=SOCKET,
        pane=PANE,
        config_dir=config_dir,
        cwd=cwd,
        claude_pid=CLAUDE_PID,
        claude_started_at=STARTED_AT,
    )


def _session(**values: Any) -> claude_input.Session:
    """作業フォルダが `/work/ws`・設定のフォルダが `/c` で、values を足したセッションを作る。"""
    return claude_input.Session(cwd=WORK_DIR, claude_config_dir=Path("/c"), **values)


def _tmux_session(pane: str) -> claude_input.Session:
    """ペインへ入力するのに要る値がそろったセッションを作る。"""
    return _session(tmux=TMUX, tmux_pane=pane, claude_pid=CLAUDE_PID, claude_started_at=STARTED_AT)


def _work_folder(tmp_path: Path) -> Path:
    """作業フォルダに当たる会話の記録のフォルダ（まだ作らない）を返す。"""
    return tmp_path / "cfg" / "projects" / WORK_FOLDER_NAME


class _FakeTime:
    """時刻を控え、待つと待った分だけ進む偽の時計と待ち。"""

    def __init__(self) -> None:
        """時刻を 0 から始め、待った秒を控える入れ物を作る。"""
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        """今の時刻を返す。"""
        return self.now

    def sleep(self, seconds: float) -> None:
        """待たずに、待った秒を控えて時刻を進める。"""
        self.sleeps.append(seconds)
        self.now += seconds


class _Runner:
    """ps・tmux の呼び出しを控え、決めた結果を返す偽の `run`。

    `responses` にあるコマンドはその終了コードと標準出力を返す。
    無い tmux のコマンドはサブコマンドの名前ごとの `outcomes`（既定 0）、無い ps は終了コード 1 を返す。
    """

    def __init__(
        self,
        *,
        responses: dict[tuple[str, ...], tuple[int, str]] | None = None,
        outcomes: dict[str, int | Exception] | None = None,
        on_call: Callable[[list[str]], None] | None = None,
    ) -> None:
        """コマンドごとの応答・tmux のサブコマンドごとの結果・呼ばれたときに動かす処理を受け取る。"""
        self.commands: list[list[str]] = []
        self.kwargs: list[dict[str, Any]] = []
        self._responses = ALIVE_RESPONSES if responses is None else responses
        self._outcomes = {} if outcomes is None else outcomes
        self._on_call = on_call

    def __call__(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        """呼ばれた引数を控え、決めた結果（終了コードと標準出力・例外）を返す。"""
        self.commands.append(command)
        self.kwargs.append(kwargs)
        if self._on_call is not None:
            self._on_call(command)
        returncode, stdout = self._result_of(command)
        return subprocess.CompletedProcess(
            args=command, returncode=returncode, stdout=_as_output(stdout, kwargs)
        )

    def _result_of(self, command: list[str]) -> tuple[int, str]:
        """コマンドの終了コードと標準出力を決める（tmux の決めた例外は送る）。"""
        # 応答を決めたコマンド: その値
        if tuple(command) in self._responses:
            return self._responses[tuple(command)]
        # 応答を決めていない ps: プロセスが無い
        if command[0] == "ps":
            return 1, ""
        # tmux の書き込みのコマンド: サブコマンドごとの結果
        outcome = self._outcomes.get(command[3], 0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome, ""

    def tmux_subcommands(self) -> list[str]:
        """呼ばれた tmux のサブコマンドの名前を順に返す。"""
        return [command[3] for command in self.commands if command[0] == "tmux"]

    def kwargs_of(self, subcommand: str) -> dict[str, Any]:
        """最初に呼ばれた tmux のサブコマンドのキーワード引数を返す。"""
        for command, kwargs in zip(self.commands, self.kwargs, strict=True):
            if command[0] == "tmux" and command[3] == subcommand:
                return kwargs
        raise AssertionError(f"{subcommand} が呼ばれていません")

    def called_with(self, word: str) -> bool:
        """word を引数に持つコマンドが呼ばれたかを返す。"""
        return any(word in command for command in self.commands)


def _as_output(text: str, kwargs: dict[str, Any]) -> Any:
    """text か encoding で呼ばれたら文字列、無ければバイト列で標準出力を返す。"""
    is_text = bool(kwargs.get("text") or kwargs.get("encoding") or kwargs.get("universal_newlines"))
    return text if is_text else text.encode("utf-8")


def _write_jsonl(path: Path, text: str) -> None:
    """jsonl に text をそのまま書く（フォルダが無ければ作る）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _append_jsonl(path: Path, text: str) -> None:
    """jsonl の末尾に text をそのまま書き足す（フォルダが無ければ作る）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(text)


def _make_folders(projects: Path, names: list[str] | None) -> None:
    """projects の下に、名前ごとのフォルダを作る（names が None なら projects も作らない）。"""
    if names is None:
        return
    for name in names:
        (projects / name).mkdir(parents=True)


def _names(paths: list[Path]) -> set[str]:
    """パスの最後の名前の集合を返す。"""
    return {path.name for path in paths}


def _prepare_transcripts(
    folder: Path, existing: str, appended: str, *, folder_exists: bool
) -> dict[Path, int]:
    """会話の記録のフォルダに、控えの前の行を書いて大きさを控え、後ろの行を書き足す。フォルダが無いときは何も作らず空の控えを返す。"""
    if not folder_exists:
        return {}
    _write_jsonl(folder / "a.jsonl", existing)
    sizes = {folder / "a.jsonl": (folder / "a.jsonl").stat().st_size}
    _append_jsonl(folder / "a.jsonl", appended)
    return sizes


def test_remember() -> None:
    """後から呼んだセッションの宛先にする（正常系）。"""
    # 準備
    targets = claude_input.InputTargets()
    root = Path("/work/ws")
    # 実行・検証
    targets.remember(root, _tmux_session("%3"))
    first = targets.target_of(root)
    assert first is not None
    assert first.pane == "%3"
    targets.remember(root, _tmux_session("%5"))
    second = targets.target_of(root)
    assert second is not None
    assert second.pane == "%5"
    targets.remember(root, _session())
    assert targets.target_of(root) is None


def test_enter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """セッションを受けていないワークスペースには入力しない（正常系）。"""
    # 準備
    run = _Runner()
    monkeypatch.setattr(claude_input.subprocess, "run", run)
    targets = claude_input.InputTargets()
    # 実行
    result = targets.enter(tmp_path, 1)
    # 検証
    assert result is False
    assert run.commands == []


def test_parse_session() -> None:
    """全ての値を読む（正常系）。"""
    # 準備
    raw = {
        "cwd": "/w",
        "claude_config_dir": "/c",
        "tmux": "/s,1,0",
        "tmux_pane": "%3",
        "claude_pid": 42,
        "claude_started_at": "Mon Nov  2 10:00:00 2026",
    }
    # 実行
    session = claude_input.parse_session(raw)
    # 検証
    assert session is not None
    assert session.cwd == Path("/w")
    assert session.claude_config_dir == Path("/c")
    assert session.tmux == "/s,1,0"
    assert session.tmux_pane == "%3"
    assert session.claude_pid == 42
    assert session.claude_started_at == "Mon Nov 2 10:00:00 2026"


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param({"cwd": "/w"}, id="cwd_only"),
        pytest.param({"cwd": "/w", "tmux": "", "claude_pid": "42"}, id="empty_and_string_pid"),
        pytest.param({"cwd": "/w", "claude_pid": True}, id="bool_pid"),
    ],
)
def test_parse_session_when_partial(raw: dict[str, Any]) -> None:
    """足りない値・形の違う値は None にする（正常系）。"""
    # 実行
    session = claude_input.parse_session(raw)
    # 検証
    assert session is not None
    assert session.cwd == Path("/w")
    assert session.claude_config_dir == claude_input.DEFAULT_CONFIG_DIR
    assert session.tmux is None
    assert session.tmux_pane is None
    assert session.claude_pid is None
    assert session.claude_started_at is None


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(None, id="none"),
        pytest.param({}, id="empty"),
        pytest.param({"cwd": "w"}, id="relative_cwd"),
        pytest.param({"cwd": 1}, id="cwd_not_string"),
    ],
)
def test_parse_session_when_invalid(raw: dict[str, Any] | None) -> None:
    """作業フォルダが読めなければ None（正常系）。"""
    # 実行
    session = claude_input.parse_session(raw)
    # 検証
    assert session is None


def test_input_target() -> None:
    """ソケットは TMUX の最初の , より前（正常系）。"""
    # 準備
    session = _session(
        tmux="/tmp/tmux-1000/default,1234,0",
        tmux_pane="%3",
        claude_pid=CLAUDE_PID,
        claude_started_at=STARTED_AT,
    )
    # 実行
    target = claude_input.input_target(session)
    # 検証
    assert target is not None
    assert target.socket == "/tmp/tmux-1000/default"
    assert target.pane == "%3"


@pytest.mark.parametrize(
    "values",
    [
        pytest.param(
            {"tmux_pane": "%3", "claude_pid": CLAUDE_PID, "claude_started_at": STARTED_AT},
            id="no_tmux",
        ),
        pytest.param(
            {"tmux": TMUX, "claude_pid": CLAUDE_PID, "claude_started_at": STARTED_AT},
            id="no_pane",
        ),
        pytest.param(
            {"tmux": TMUX, "tmux_pane": "%3", "claude_started_at": STARTED_AT}, id="no_pid"
        ),
        pytest.param(
            {"tmux": TMUX, "tmux_pane": "%3", "claude_pid": CLAUDE_PID}, id="no_started_at"
        ),
    ],
)
def test_input_target_when_missing(values: dict[str, Any]) -> None:
    """値が欠けていれば None（正常系）。"""
    # 実行
    target = claude_input.input_target(_session(**values))
    # 検証
    assert target is None


@pytest.mark.parametrize(
    ("responses", "calls_ppid"),
    [
        pytest.param(ALIVE_RESPONSES, True, id="descendant"),
        pytest.param(DIRECT_RESPONSES, False, id="pane_process"),
    ],
)
def test_is_session_alive(
    tmp_path: Path, responses: dict[tuple[str, ...], tuple[int, str]], calls_ppid: bool
) -> None:
    """起動時刻が一致し、ペインのプロセスの子孫なら生きている（正常系）。"""
    # 準備
    run = _Runner(responses=responses)
    # 実行
    result = claude_input.is_session_alive(
        _target(tmp_path), deadline=DEADLINE, run=run, clock=lambda: CLOCK_BEFORE
    )
    # 検証
    assert result is None
    assert run.called_with("ppid=") is calls_ppid


@pytest.mark.parametrize(
    ("responses", "clock_now", "expected", "runs"),
    [
        pytest.param(
            {**ALIVE_RESPONSES, LSTART_KEY: (1, "")},
            CLOCK_BEFORE,
            "Claude Code のプロセス 40 が無い",
            True,
            id="process_missing",
        ),
        pytest.param(
            {**ALIVE_RESPONSES, LSTART_KEY: (0, "Mon Nov  2 11:00:00 2026\n")},
            CLOCK_BEFORE,
            "PID 40 が別のプロセスに使い回された",
            True,
            id="pid_reused",
        ),
        pytest.param(
            {**ALIVE_RESPONSES, DISPLAY_KEY: (1, "")},
            CLOCK_BEFORE,
            "ペイン %3 が無い",
            True,
            id="pane_missing",
        ),
        pytest.param(
            {**ALIVE_RESPONSES, PPID_20_KEY: (0, "    1\n")},
            CLOCK_BEFORE,
            "Claude Code がペイン %3 の中に無い",
            True,
            id="reached_init",
        ),
        pytest.param(
            {**ALIVE_RESPONSES, PPID_40_KEY: (0, "   40\n")},
            CLOCK_BEFORE,
            "Claude Code がペイン %3 の中に無い",
            True,
            id="depth_limit",
        ),
        pytest.param(ALIVE_RESPONSES, CLOCK_AFTER, "時間切れ", False, id="deadline_passed"),
    ],
)
def test_is_session_alive_when_ended(
    tmp_path: Path,
    responses: dict[tuple[str, ...], tuple[int, str]],
    clock_now: float,
    expected: str,
    runs: bool,
) -> None:
    """プロセス・起動時刻・ペイン・親子のどれかが違えば理由を返す（異常系）。"""
    # 準備
    run = _Runner(responses=responses)
    # 実行
    result = claude_input.is_session_alive(
        _target(tmp_path), deadline=DEADLINE, run=run, clock=lambda: clock_now
    )
    # 検証
    assert result == expected
    assert (run.commands != []) is runs


@pytest.mark.parametrize(
    ("cwd", "expected"),
    [
        pytest.param(
            Path("/home/u/repo/my_ws.v2"),
            [Path("/c/projects/-home-u-repo-my-ws-v2")],
            id="symbols",
        ),
        pytest.param(Path("/home/u/話し合い"), [Path("/c/projects/-home-u-----")], id="japanese"),
        pytest.param(
            Path("/home/u/a😀b"),
            [Path("/c/projects/-home-u-a--b")],
            id="surrogate_pair",
        ),
    ],
)
def test_transcript_dirs(cwd: Path, expected: list[Path]) -> None:
    """英数字以外を - にした名前のフォルダ（正常系）。"""
    # 準備
    target = _target_at(Path("/c"), cwd)
    # 実行
    result = claude_input.transcript_dirs(target)
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    ("created", "expected_names"),
    [
        pytest.param(
            [f"{LONG_PREFIX}-abc", f"{LONG_PREFIX}-def", LONG_PREFIX[:-1] + "x-ghi"],
            {f"{LONG_PREFIX}-abc", f"{LONG_PREFIX}-def"},
            id="prefixed_folders",
        ),
        pytest.param(None, set(), id="no_projects"),
    ],
)
def test_transcript_dirs_when_long(
    tmp_path: Path, created: list[str] | None, expected_names: set[str]
) -> None:
    """名前が上限を超えると先頭で始まるフォルダを全て引く（正常系）。"""
    # 準備
    _make_folders(tmp_path / "cfg" / "projects", created)
    target = _target_at(tmp_path / "cfg", LONG_CWD)
    # 実行
    result = claude_input.transcript_dirs(target)
    # 検証
    assert _names(result) == expected_names


def test_input_text() -> None:
    """件数を入れた 1 行（正常系）。"""
    # 準備・実行
    result = claude_input.input_text(3)
    # 検証
    assert result == TEXT


def test_snapshot_sizes(tmp_path: Path) -> None:
    """jsonl だけの大きさを控える（正常系）。"""
    # 準備
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_jsonl(first / "a.jsonl", "0123456789")
    _write_jsonl(first / "c.txt", "not jsonl")
    _write_jsonl(second / "b.jsonl", "")
    # 実行
    result = claude_input.snapshot_sizes([first, second])
    # 検証
    assert result == {first / "a.jsonl": 10, second / "b.jsonl": 0}


@pytest.mark.parametrize(
    "folders",
    [
        pytest.param([Path("/no/such/folder")], id="missing_folder"),
        pytest.param([], id="no_folders"),
    ],
)
def test_snapshot_sizes_when_missing(folders: list[Path]) -> None:
    """無いフォルダは飛ばす（正常系）。"""
    # 準備・実行
    result = claude_input.snapshot_sizes(folders)
    # 検証
    assert result == {}


@pytest.mark.parametrize(
    ("existing", "appended", "new_file"),
    [
        pytest.param("", USER_LINE, "", id="user_line_text"),
        pytest.param("", USER_LINE_BLOCKS, "", id="user_line_blocks"),
        pytest.param("", ENQUEUE_LINE, "", id="enqueue"),
        pytest.param("", "", USER_LINE, id="new_file"),
    ],
)
def test_find_delivery(tmp_path: Path, existing: str, appended: str, new_file: str) -> None:
    """会話か待ち行列に入った行を届いたと数える（正常系）。"""
    # 準備
    folder = tmp_path / "folder"
    sizes = _prepare_transcripts(folder, existing, appended, folder_exists=True)
    _write_jsonl(folder / "b.jsonl", new_file)
    # 実行
    result = claude_input.find_delivery([folder], sizes, cwd=WORK_DIR, text=TEXT)
    # 検証
    assert result is True


@pytest.mark.parametrize(
    ("existing", "appended", "folder_exists"),
    [
        pytest.param(USER_LINE, "", True, id="only_before_snapshot"),
        pytest.param("", USER_LINE_OTHER_CWD, True, id="other_cwd"),
        pytest.param("", USER_LINE_OTHER_TEXT, True, id="other_text"),
        pytest.param("", DEQUEUE_LINE, True, id="dequeue"),
        pytest.param("", PARTIAL_USER_LINE, True, id="partial_line"),
        pytest.param("", "読めない行\n", True, id="unreadable_line"),
        pytest.param("", "", False, id="no_folder"),
    ],
)
def test_find_delivery_when_not_found(
    tmp_path: Path, existing: str, appended: str, folder_exists: bool
) -> None:
    """当たらない行だけなら届いていない（正常系）。"""
    # 準備
    folder = tmp_path / "folder"
    sizes = _prepare_transcripts(folder, existing, appended, folder_exists=folder_exists)
    # 実行
    result = claude_input.find_delivery([folder], sizes, cwd=WORK_DIR, text=TEXT)
    # 検証
    assert result is False


def test_paste_to_pane(tmp_path: Path) -> None:
    """3 つのコマンドを順に呼ぶ（正常系）。"""
    # 準備
    run = _Runner()
    # 実行
    result = claude_input.paste_to_pane(
        _target(tmp_path), "x", deadline=DEADLINE, run=run, clock=lambda: CLOCK_BEFORE
    )
    # 検証
    assert result is None
    assert run.commands == [
        ["tmux", "-S", "/s", "load-buffer", "-b", "mindstella-input", "-"],
        ["tmux", "-S", "/s", "paste-buffer", "-p", "-d", "-b", "mindstella-input", "-t", "%3"],
        ["tmux", "-S", "/s", "send-keys", "-t", "%3", "Enter"],
    ]
    assert run.kwargs[0]["input"] == b"x"


@pytest.mark.parametrize(
    ("outcomes", "clock_now", "expected_called", "expected_reason"),
    [
        pytest.param(
            {"paste-buffer": 1},
            CLOCK_BEFORE,
            ["load-buffer", "paste-buffer"],
            "paste-buffer",
            id="exit_code",
        ),
        pytest.param(
            {"load-buffer": subprocess.TimeoutExpired(cmd="tmux", timeout=0.1)},
            CLOCK_BEFORE,
            ["load-buffer"],
            "時間内に終わらない",
            id="timeout",
        ),
        pytest.param(
            {"load-buffer": OSError("tmux が無い")},
            CLOCK_BEFORE,
            ["load-buffer"],
            "load-buffer",
            id="os_error",
        ),
        pytest.param({}, CLOCK_AFTER, [], "時間切れ", id="deadline_passed"),
    ],
)
def test_paste_to_pane_when_failed(
    tmp_path: Path,
    outcomes: dict[str, int | Exception],
    clock_now: float,
    expected_called: list[str],
    expected_reason: str,
) -> None:
    """失敗したら残りを呼ばずに理由を返す（異常系）。"""
    # 準備
    run = _Runner(outcomes=outcomes)
    # 実行
    result = claude_input.paste_to_pane(
        _target(tmp_path), "x", deadline=DEADLINE, run=run, clock=lambda: clock_now
    )
    # 検証
    assert result is not None
    assert expected_reason in result
    assert run.tmux_subcommands() == expected_called


def test_enter_to_claude(tmp_path: Path) -> None:
    """貼った後に会話の記録に入れば真（正常系）。"""
    # 準備
    transcript = _work_folder(tmp_path) / "session.jsonl"

    def _on_call(command: list[str]) -> None:
        """`send-keys` を受けたら、入力した文字列の user の行を会話の記録へ書き足す。"""
        if command[0] == "tmux" and command[3] == "send-keys":
            _append_jsonl(
                transcript,
                json.dumps(
                    {
                        "type": "user",
                        "cwd": "/work/ws",
                        "message": {"role": "user", "content": INPUT_TEXT_2},
                    },
                    ensure_ascii=False,
                )
                + "\n",
            )

    run = _Runner(on_call=_on_call)
    fake = _FakeTime()
    # 実行
    result = claude_input.enter_to_claude(
        _target(tmp_path), 2, lock=threading.Lock(), run=run, clock=fake.clock, sleep=fake.sleep
    )
    # 検証
    assert result is True
    assert run.kwargs_of("load-buffer")["input"] == INPUT_BYTES_2


def test_enter_to_claude_when_outside_tmux() -> None:
    """送り先が無ければ ps・tmux を呼ばずに偽（正常系）。"""
    # 準備
    run = _Runner()
    fake = _FakeTime()
    # 実行
    result = claude_input.enter_to_claude(
        None, 2, lock=threading.Lock(), run=run, clock=fake.clock, sleep=fake.sleep
    )
    # 検証
    assert result is False
    assert run.commands == []


def test_enter_to_claude_when_session_ended(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """宛先のセッションが終わっていれば貼らずに偽（異常系）。"""
    # 準備
    run = _Runner(responses={**ALIVE_RESPONSES, LSTART_KEY: (1, "")})
    fake = _FakeTime()
    caplog.set_level(logging.WARNING)
    # 実行
    result = claude_input.enter_to_claude(
        _target(tmp_path), 2, lock=threading.Lock(), run=run, clock=fake.clock, sleep=fake.sleep
    )
    # 検証
    assert result is False
    assert "WARNING" in caplog.text
    assert "Claude Code のプロセス" in caplog.text
    assert "load-buffer" not in run.tmux_subcommands()


def test_enter_to_claude_when_paste_failed(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """貼れなければ偽と理由の記録（異常系）。"""
    # 準備
    run = _Runner(outcomes={"paste-buffer": 1})
    fake = _FakeTime()
    caplog.set_level(logging.WARNING)
    # 実行
    result = claude_input.enter_to_claude(
        _target(tmp_path), 2, lock=threading.Lock(), run=run, clock=fake.clock, sleep=fake.sleep
    )
    # 検証
    assert result is False
    assert "WARNING" in caplog.text
    assert "paste-buffer" in caplog.text
    assert fake.sleeps == []


def test_enter_to_claude_when_not_delivered(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """上限までに入らなければ偽（正常系）。"""
    # 準備
    run = _Runner()
    fake = _FakeTime()
    caplog.set_level(logging.WARNING)
    # 実行
    result = claude_input.enter_to_claude(
        _target(tmp_path), 2, lock=threading.Lock(), run=run, clock=fake.clock, sleep=fake.sleep
    )
    # 検証
    assert result is False
    assert sum(fake.sleeps) <= claude_input.INPUT_DEADLINE_SEC
    assert "WARNING" in caplog.text


def test_enter_to_claude_when_concurrent(tmp_path: Path) -> None:
    """同時の入力を重ねない（正常系）。"""
    # 準備（ペインで直に Claude Code を動かした宛先にして、1 回の入力の呼び出しを 5 つにする）
    target = _target(tmp_path)
    lock = threading.Lock()
    fake = _FakeTime()
    owners: list[int] = []
    first_call_started = threading.Event()
    second_about_to_call = threading.Event()

    def _on_call(command: list[str]) -> None:
        """呼んだスレッドを控え、最初の呼び出しでは他方のスレッドが鍵を待ち始めるまで待つ。"""
        owners.append(threading.get_ident())
        if len(owners) == 1:
            first_call_started.set()
            second_about_to_call.wait(timeout=5)
            # 他方のスレッドが鍵を待ち始める猶予
            time.sleep(0.1)

    run = _Runner(responses=DIRECT_RESPONSES, on_call=_on_call)

    def _first() -> None:
        """先に入力する。"""
        claude_input.enter_to_claude(
            target, 2, lock=lock, run=run, clock=fake.clock, sleep=fake.sleep
        )

    def _second() -> None:
        """先の入力が始まった後に入力する。"""
        first_call_started.wait(timeout=5)
        second_about_to_call.set()
        claude_input.enter_to_claude(
            target, 2, lock=lock, run=run, clock=fake.clock, sleep=fake.sleep
        )

    threads = [threading.Thread(target=_first), threading.Thread(target=_second)]
    # 実行
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    # 検証（ps・display-message・3 つの tmux のコマンドの 5 つずつが、スレッドごとにまとまる）
    assert len(owners) == 10
    assert len(set(owners[:5])) == 1
    assert len(set(owners[5:])) == 1
    assert owners[0] != owners[5]
