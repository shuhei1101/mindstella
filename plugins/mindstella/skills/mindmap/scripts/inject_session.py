"""PreToolUse のフックで、mindstella のツールを呼んだセッションの値をツールの入力の `session` に入れて返す。

ツールを呼ぶたびにシステムの `python3` で起動するため、Python 3.8 で読める構文と標準ライブラリだけで書く。
使い方（Claude Code がフックの入力の JSON を標準入力へ渡す）:
python3 inject_session.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, TextIO

# 親をたどるときに Claude Code とみなす `ps -o comm=` の値
CLAUDE_COMMAND = "claude"

# フックのプロセスの親から `ps` でたどる段の上限
PARENT_DEPTH_MAX = 32

# `CLAUDE_CONFIG_DIR` が無いか空のときの Claude Code の設定のフォルダ
DEFAULT_CONFIG_DIR = Path.home() / ".claude"

# `ps -o lstart=` の語の数（曜日・月・日・時刻・年）
LSTART_WORDS = 5

# これ以下の PID に着いたら、親をたどるのをやめる（init）
INIT_PID = 1


def main(
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    environ: Mapping[str, str] | None = None,
    find_claude: Callable[[int], tuple[int, str] | None] | None = None,
) -> int:
    """フックの入力の `tool_input` の `session` を、このセッションの値で上書きした `updatedInput` を出す。"""
    env = os.environ if environ is None else environ
    search = find_claude_process if find_claude is None else find_claude
    try:
        hook_input = json.loads((sys.stdin if stdin is None else stdin).read())
    except ValueError:
        hook_input = None
    # 読めない入力: ツールの呼び出しを止めないよう、何も出さずに終える
    if not isinstance(hook_input, dict):
        return 0
    cwd = hook_input.get("cwd")
    tool_input = hook_input.get("tool_input")
    if not isinstance(cwd, str) or not isinstance(tool_input, dict):
        return 0

    # tmux の中だけ、入力を貼る先の Claude Code のプロセスを探す
    claude = search(os.getppid()) if _inside_tmux(env) else None
    updated = dict(tool_input)
    updated["session"] = build_session(cwd, env, claude)
    output = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": updated}}
    print(json.dumps(output, ensure_ascii=False), file=sys.stdout if stdout is None else stdout)
    return 0


def _inside_tmux(environ: Mapping[str, str]) -> bool:
    """`TMUX`・`TMUX_PANE` がどちらも空でなければ真を返す。"""
    return bool(environ.get("TMUX")) and bool(environ.get("TMUX_PANE"))


def build_session(
    cwd: str, environ: Mapping[str, str], claude: tuple[int, str] | None
) -> dict[str, Any]:
    """作業フォルダ・環境変数・Claude Code のプロセスから、ツールの引数 `session` の辞書を作る。"""
    config_dir = environ.get("CLAUDE_CONFIG_DIR") or ""
    session: dict[str, Any] = {
        "cwd": cwd,
        "claude_config_dir": str(Path(config_dir).expanduser().absolute())
        if config_dir
        else str(DEFAULT_CONFIG_DIR),
    }
    # tmux の外: 入力を貼る先を持たない
    if not _inside_tmux(environ):
        return session
    session["tmux"] = environ["TMUX"]
    session["tmux_pane"] = environ["TMUX_PANE"]
    # Claude Code のプロセスが見つかった: 終わったかを見分けるための PID と起動時刻を入れる
    if claude is not None:
        session["claude_pid"] = claude[0]
        session["claude_started_at"] = claude[1]
    return session


def find_claude_process(
    pid: int, run: Callable[..., Any] = subprocess.run
) -> tuple[int, str] | None:
    """渡した PID から親へたどり、最初に名前が `CLAUDE_COMMAND` のプロセスの PID と起動時刻を返す。"""
    current = pid
    for _ in range(PARENT_DEPTH_MAX):
        result = run(
            ["ps", "-o", "ppid=,lstart=,comm=", "-p", str(current)],
            capture_output=True,
            text=True,
            check=False,
        )
        words = (result.stdout or "").split() if result.returncode == 0 else []
        # 親の PID・起動時刻の 5 語・コマンドの名前がそろわない: 読めない
        if len(words) < LSTART_WORDS + 2 or not words[0].isdigit():
            return None
        parent = int(words[0])
        command = Path(words[-1]).name
        if command == CLAUDE_COMMAND:
            return current, " ".join(words[1 : 1 + LSTART_WORDS])
        # init に着いた: Claude Code の外から呼ばれている
        if parent <= INIT_PID:
            return None
        current = parent
    return None


if __name__ == "__main__":
    sys.exit(main())
