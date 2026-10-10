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

# tmux の送り先
SOCKET = "/s,1,0"
PANE = "%3"

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


def _target(
    tmp_path: Path, *, socket: str | None = SOCKET, pane: str | None = PANE
) -> claude_input.InputTarget:
    """作業フォルダが `/work/ws`・設定のフォルダが tmp_path の下の送り先を作る。"""
    return claude_input.InputTarget(
        socket=socket, pane=pane, config_dir=tmp_path / "cfg", cwd=WORK_DIR
    )


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
    """tmux の呼び出しを控え、コマンドごとに決めた結果を返す偽の `run`。"""

    def __init__(
        self,
        *,
        outcomes: dict[str, int | Exception] | None = None,
        on_call: Callable[[list[str]], None] | None = None,
    ) -> None:
        """コマンド名（`tmux` の次の語）ごとの結果と、呼ばれたときに動かす処理を受け取る。"""
        self.commands: list[list[str]] = []
        self.kwargs: list[dict[str, Any]] = []
        self._outcomes = {} if outcomes is None else outcomes
        self._on_call = on_call

    def __call__(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        """呼ばれた引数を控え、決めた結果（終了コード・例外）を返す。"""
        self.commands.append(command)
        self.kwargs.append(kwargs)
        if self._on_call is not None:
            self._on_call(command)
        outcome = self._outcomes.get(command[1], 0)
        if isinstance(outcome, Exception):
            raise outcome
        return subprocess.CompletedProcess(args=command, returncode=outcome)


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


def test_load_input_target(tmp_path: Path) -> None:
    """3 つの環境変数と作業フォルダを持つ（正常系）。"""
    # 準備
    environ = {
        "TMUX": SOCKET,
        "TMUX_PANE": PANE,
        "CLAUDE_CONFIG_DIR": str(tmp_path / "cfg"),
    }
    # 実行
    target = claude_input.load_input_target(environ, tmp_path)
    # 検証
    assert target.socket == SOCKET
    assert target.pane == PANE
    assert target.config_dir == tmp_path / "cfg"
    assert target.cwd == tmp_path.resolve()


@pytest.mark.parametrize(
    "environ",
    [
        pytest.param({}, id="empty_dict"),
        pytest.param({"TMUX": "", "TMUX_PANE": "", "CLAUDE_CONFIG_DIR": ""}, id="empty_values"),
    ],
)
def test_load_input_target_when_outside_tmux(tmp_path: Path, environ: dict[str, str]) -> None:
    """tmux の外では送り先が無く、設定のフォルダは既定（正常系）。"""
    # 準備・実行
    target = claude_input.load_input_target(environ, tmp_path)
    # 検証
    assert target.socket is None
    assert target.pane is None
    assert target.config_dir == claude_input.DEFAULT_CONFIG_DIR


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
    target = claude_input.InputTarget(socket=None, pane=None, config_dir=Path("/c"), cwd=cwd)
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
    target = claude_input.InputTarget(
        socket=None, pane=None, config_dir=tmp_path / "cfg", cwd=LONG_CWD
    )
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
        ["tmux", "load-buffer", "-b", "mindstella-input", "-"],
        ["tmux", "paste-buffer", "-p", "-d", "-b", "mindstella-input", "-t", "%3"],
        ["tmux", "send-keys", "-t", "%3", "Enter"],
    ]
    assert run.kwargs[0]["input"] == b"x"
    assert run.kwargs[0]["env"]["TMUX"] == SOCKET
    assert run.kwargs[1]["env"]["TMUX"] == SOCKET
    assert run.kwargs[2]["env"]["TMUX"] == SOCKET


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
    assert [command[1] for command in run.commands] == expected_called


def test_enter_to_claude(tmp_path: Path) -> None:
    """貼った後に会話の記録に入れば真（正常系）。"""
    # 準備
    transcript = _work_folder(tmp_path) / "session.jsonl"

    def _on_call(command: list[str]) -> None:
        """`send-keys` を受けたら、入力した文字列の user の行を会話の記録へ書き足す。"""
        if command[1] == "send-keys":
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
        _target(tmp_path), 2, run=run, clock=fake.clock, sleep=fake.sleep
    )
    # 検証
    assert result is True
    assert run.kwargs[0]["input"] == INPUT_BYTES_2


@pytest.mark.parametrize(
    ("socket", "pane"),
    [
        pytest.param(None, PANE, id="no_socket"),
        pytest.param(SOCKET, None, id="no_pane"),
    ],
)
def test_enter_to_claude_when_outside_tmux(
    tmp_path: Path, socket: str | None, pane: str | None
) -> None:
    """送り先が無ければ tmux を呼ばずに偽（正常系）。"""
    # 準備
    run = _Runner()
    fake = _FakeTime()
    # 実行
    result = claude_input.enter_to_claude(
        _target(tmp_path, socket=socket, pane=pane),
        2,
        run=run,
        clock=fake.clock,
        sleep=fake.sleep,
    )
    # 検証
    assert result is False
    assert run.commands == []


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
        _target(tmp_path), 2, run=run, clock=fake.clock, sleep=fake.sleep
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
        _target(tmp_path), 2, run=run, clock=fake.clock, sleep=fake.sleep
    )
    # 検証
    assert result is False
    assert fake.now <= claude_input.INPUT_DEADLINE_SEC
    assert "WARNING" in caplog.text


def test_enter_to_claude_when_concurrent(tmp_path: Path) -> None:
    """同時の入力を重ねない（正常系）。"""
    # 準備
    target = _target(tmp_path)
    fake = _FakeTime()
    owners: list[int] = []
    first_call_started = threading.Event()
    second_about_to_call = threading.Event()

    def _run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        """呼んだスレッドを控え、最初の呼び出しでは他方のスレッドが鍵を待ち始めるまで待つ。"""
        owners.append(threading.get_ident())
        if len(owners) == 1:
            first_call_started.set()
            second_about_to_call.wait(timeout=5)
            # 他方のスレッドが鍵を待ち始める猶予
            time.sleep(0.1)
        return subprocess.CompletedProcess(args=command, returncode=0)

    def _first() -> None:
        """先に入力する。"""
        claude_input.enter_to_claude(target, 2, run=_run, clock=fake.clock, sleep=fake.sleep)

    def _second() -> None:
        """先の入力が始まった後に入力する。"""
        first_call_started.wait(timeout=5)
        second_about_to_call.set()
        claude_input.enter_to_claude(target, 2, run=_run, clock=fake.clock, sleep=fake.sleep)

    threads = [threading.Thread(target=_first), threading.Thread(target=_second)]
    # 実行
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    # 検証
    assert len(owners) == 6
    assert owners[0] == owners[1] == owners[2]
    assert owners[3] == owners[4] == owners[5]
    assert owners[0] != owners[3]
