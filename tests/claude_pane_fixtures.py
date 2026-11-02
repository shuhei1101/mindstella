"""Claude Code の代わりに偽のコマンドを動かす tmux のペインを、専用のサーバーで立てる共通の fixture と関数（結合テストと E2E テストが共有する）。

偽のコマンドは、貼られて確定した文字列を会話の記録（jsonl）へ書き足す（または書かない）。
tmux は専用のソケット（`-L`）と一時フォルダで動かし、利用者の tmux のセッションに触れない。
fixture は `tests/conftest.py` が読み込む。
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

# tmux の 1 コマンドを待つ上限秒数
TMUX_TIMEOUT_SEC = 10

# `/proc/{PID}/stat` のコマンドの名前を閉じる最後の `)` より後ろの、starttime の位置（0 始まり）
STAT_STARTTIME_INDEX = 19

# 偽のコマンドが入力を待つ状態になるのを待つ上限秒数と、確かめる間隔
READY_WAIT_SEC = 10
POLL_INTERVAL_SEC = 0.05

# 偽のコマンドが貼られた文字列を受けたときの動き。user は user の行を、queue は待ち行列に入った行を、silent は何も書かない
type PaneMode = str

# 偽のコマンド（ブラケットペーストを受け付ける印を出して 1 行を読み、モードに応じた行を会話の記録へ書き足す）
FAKE_CLAUDE_SCRIPT = """\
import json
import os
import sys
import time

mode, transcript, ready, cwd = sys.argv[1:5]
# ブラケットペーストを受け付ける（tmux は貼る文字列を ESC[200~ と ESC[201~ で包む）
sys.stdout.write("\\x1b[?2004h")
sys.stdout.flush()
# 自分の PID を書いてから、入力を待つ状態になったことを知らせる
with open(ready + ".tmp", "w") as stream:
    stream.write(str(os.getpid()))
os.replace(ready + ".tmp", ready)
line = sys.stdin.readline()
text = line.rstrip("\\n").replace("\\x1b[200~", "").replace("\\x1b[201~", "")
record = None
if mode == "user":
    record = {"type": "user", "cwd": cwd, "message": {"role": "user", "content": text}}
elif mode == "queue":
    record = {"type": "queue-operation", "operation": "enqueue"}
if record is not None:
    with open(transcript, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\\n")
time.sleep(600)
"""


@dataclass(frozen=True)
class ClaudePane:
    """偽のコマンドを動かす tmux のペイン。session をツールの引数に渡すと、常駐サーバーがそのペインへ入力する。"""

    # ツールの引数 `session`（PreToolUse のフックが入れる値と同じキー。偽のコマンドを Claude Code のプロセスとする）
    session: dict[str, Any]
    # 偽のコマンドが書き足す会話の記録
    transcript: Path
    # ペインの画面の中身を返す
    capture: Callable[[], str]

    def end_claude(self) -> None:
        """偽のコマンドのプロセスを終わらせる（ペインではシェルが動き続ける）。"""
        os.kill(self.session["claude_pid"], signal.SIGTERM)
        deadline = time.monotonic() + READY_WAIT_SEC
        while _is_running(self.session["claude_pid"]):
            assert time.monotonic() < deadline, "偽のコマンドが終わりません"
            time.sleep(POLL_INTERVAL_SEC)

    def lines(self) -> list[str]:
        """会話の記録の行を返す（まだ無ければ空）。"""
        if not self.transcript.exists():
            return []
        return self.transcript.read_text(encoding="utf-8").splitlines()


type StartClaudePane = Callable[..., ClaudePane]


def transcript_folder_name(cwd: Path) -> str:
    """作業フォルダに当たる会話の記録のフォルダ名（英数字以外を `-` にした名前）を返す。"""
    return re.sub(r"[^A-Za-z0-9]", "-", str(cwd.resolve()))


def _is_running(pid: int) -> bool:
    """プロセスが動いているか（終わってゾンビになったものは動いていないとみなす）を返す。"""
    completed = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(pid)],
        capture_output=True,
        text=True,
        timeout=TMUX_TIMEOUT_SEC,
        check=False,
    )
    return completed.returncode == 0 and not completed.stdout.strip().startswith("Z")


def _started_at(pid: int) -> str:
    """プロセスの起動時刻（`/proc/{PID}/stat` の 22 番目の欄 starttime）を返す。"""
    stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    return stat.rpartition(")")[2].split()[STAT_STARTTIME_INDEX]


@pytest.fixture
def start_claude_pane(tmp_path: Path) -> Iterator[StartClaudePane]:
    """偽のコマンドを動かすペインを専用の tmux のサーバーで立てる関数を返し、テストの後で立てたセッションを落とす。"""
    real_tmux = shutil.which("tmux")
    if real_tmux is None:
        pytest.skip("tmux が無い")
    # ソケットのパスが長いとつながらないため、短い一時フォルダに置く
    tmux_tmpdir = Path(tempfile.mkdtemp(prefix="mst", dir="/tmp"))
    socket = f"mindstella-pane-{os.getpid()}-{tmux_tmpdir.name}"
    env = {key: value for key, value in os.environ.items() if key not in ("TMUX", "TMUX_PANE")}
    env["TMUX_TMPDIR"] = str(tmux_tmpdir)
    sessions: list[str] = []

    def _tmux(*args: str) -> str:
        """専用のソケットで tmux を呼び、標準出力を返す。"""
        completed = subprocess.run(
            [real_tmux, "-u", "-L", socket, *args],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=TMUX_TIMEOUT_SEC,
            check=True,
        )
        return completed.stdout.strip()

    def _start(*, mode: PaneMode, cwd: Path, config_name: str = "claude-config") -> ClaudePane:
        """cwd を作業フォルダとして、設定のフォルダ config_name に会話の記録のフォルダを作り、偽のコマンドが入力を待つまで待って返す。"""
        config_dir = tmp_path / config_name
        transcript = config_dir / "projects" / transcript_folder_name(cwd) / "session.jsonl"
        transcript.parent.mkdir(parents=True, exist_ok=True)
        script = tmp_path / "fake_claude.py"
        script.write_text(FAKE_CLAUDE_SCRIPT, encoding="utf-8")
        ready = tmp_path / "pane-ready"
        name = f"pane{len(sessions)}"
        fake = shlex.join(
            [sys.executable, str(script), mode, str(transcript), str(ready), str(cwd.resolve())]
        )
        # 偽のコマンドをシェルの子として動かし、終わってもペインにシェルを残す
        command = shlex.join(["sh", "-c", f"{fake}; exec sh"])
        pane = _tmux(
            "new-session",
            "-d",
            "-s",
            name,
            "-x",
            "120",
            "-y",
            "30",
            "-P",
            "-F",
            "#{pane_id}",
            command,
        )
        sessions.append(name)
        socket_path = _tmux("display-message", "-p", "-t", name, "#{socket_path}")
        deadline = time.monotonic() + READY_WAIT_SEC
        while not ready.exists():
            assert time.monotonic() < deadline, "偽のコマンドが入力を待つ状態になりません"
            time.sleep(POLL_INTERVAL_SEC)
        claude_pid = int(ready.read_text(encoding="utf-8"))
        ready.unlink()
        return ClaudePane(
            session={
                "cwd": str(cwd.resolve()),
                "tmux": f"{socket_path},0,0",
                "tmux_pane": pane,
                "claude_config_dir": str(config_dir),
                "claude_pid": claude_pid,
                "claude_started_at": _started_at(claude_pid),
            },
            transcript=transcript,
            capture=lambda: _tmux("capture-pane", "-p", "-t", pane),
        )

    yield _start
    # 専用のサーバーは、最後のセッションを落とすと終わる
    for name in sessions:
        subprocess.run(
            [real_tmux, "-u", "-L", socket, "kill-session", "-t", name],
            env=env,
            capture_output=True,
            timeout=TMUX_TIMEOUT_SEC,
            check=False,
        )
    shutil.rmtree(tmux_tmpdir, ignore_errors=True)
