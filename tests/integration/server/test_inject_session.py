"""セッションの値の注入（PreToolUse のフックの inject_session.py）の結合テスト。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from workspace_fixtures import REPO_ROOT

# PreToolUse のフックが呼ぶスクリプト
INJECT_SCRIPT = (
    REPO_ROOT / "plugins" / "mindstella" / "skills" / "mindmap" / "scripts" / "inject_session.py"
)

# フックが受け継ぐ tmux のサーバーとペインの値
TMUX_VALUE = "/tmp/tmux-1000/default,1234,0"
TMUX_PANE_VALUE = "%3"

# 子プロセス 1 回を待つ上限秒数
COMMAND_TIMEOUT_SEC = 30

# Claude Code の代わりに立てるプロセスのコード。スクリプトを子として起動し、自分の PID・起動時刻（`/proc/{PID}/stat` の starttime）と子の出力を JSON で出す
CLAUDE_CODE = """\
import json, os, subprocess, sys
script, payload = sys.argv[1:3]
child = subprocess.run(
    [sys.executable, script], input=payload, capture_output=True, text=True, encoding="utf-8"
)
with open("/proc/%d/stat" % os.getpid(), encoding="utf-8") as stat:
    started = stat.read().rpartition(")")[2].split()[19]
print(json.dumps({
    "pid": os.getpid(),
    "started_at": started,
    "returncode": child.returncode,
    "stdout": child.stdout,
}))
"""


@pytest.fixture
def run_hook(tmp_path: Path) -> Any:
    """`claude` の名前のプロセスの子としてフックのスクリプトを起動し、結果を返す関数を返す。"""
    # 実行ファイルを `claude` という名前のリンクにして、`ps -o comm=` が claude になるプロセスを立てる
    claude = tmp_path / "bin" / "claude"
    claude.parent.mkdir()
    claude.symlink_to(sys.executable)
    base_env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("TMUX", "TMUX_PANE", "CLAUDE_CONFIG_DIR")
    }

    def _run(payload: str, env: dict[str, str]) -> dict[str, Any]:
        """payload を標準入力に渡してフックを起動し、Claude Code の代わりの PID と出力を返す。"""
        completed = subprocess.run(
            [str(claude), "-c", CLAUDE_CODE, str(INJECT_SCRIPT), payload],
            env={**base_env, "PYTHONUTF8": "1", **env},
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=COMMAND_TIMEOUT_SEC,
            check=True,
        )
        return json.loads(completed.stdout)

    return _run


def _payload(cwd: Path, tool_input: dict[str, Any]) -> str:
    """PreToolUse のフックの入力の JSON を返す。"""
    return json.dumps(
        {"hook_event_name": "PreToolUse", "cwd": str(cwd), "tool_input": tool_input},
        ensure_ascii=False,
    )


def test_normal(tmp_path: Path, run_hook: Any) -> None:
    """tmux の中のセッションの値を `session` に入れた入力を返す（正常系）。"""
    # 準備
    env = {"TMUX": TMUX_VALUE, "TMUX_PANE": TMUX_PANE_VALUE, "CLAUDE_CONFIG_DIR": str(tmp_path)}
    # 実行
    result = run_hook(_payload(tmp_path, {"workspace": "talk"}), env)
    # 検証
    assert result["returncode"] == 0
    output = json.loads(result["stdout"])["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse"
    assert output["updatedInput"] == {
        "workspace": "talk",
        "session": {
            "cwd": str(tmp_path),
            "tmux": TMUX_VALUE,
            "tmux_pane": TMUX_PANE_VALUE,
            "claude_config_dir": str(tmp_path),
            "claude_pid": result["pid"],
            "claude_started_at": result["started_at"],
        },
    }


def test_normal_when_outside_tmux(tmp_path: Path, run_hook: Any) -> None:
    """`TMUX`・`TMUX_PANE` が無ければ、`cwd` と `claude_config_dir` だけを入れる（正常系）。"""
    # 実行
    result = run_hook(_payload(tmp_path, {"workspace": "talk"}), {})
    # 検証
    assert result["returncode"] == 0
    session = json.loads(result["stdout"])["hookSpecificOutput"]["updatedInput"]["session"]
    assert session == {"cwd": str(tmp_path), "claude_config_dir": str(Path.home() / ".claude")}


def test_normal_when_session_given(tmp_path: Path, run_hook: Any) -> None:
    """AI が `session` を書いて呼んでも、フックの値で置き換える（正常系）。"""
    # 実行
    result = run_hook(_payload(tmp_path, {"workspace": "talk", "session": {"cwd": "/etc"}}), {})
    # 検証
    assert result["returncode"] == 0
    session = json.loads(result["stdout"])["hookSpecificOutput"]["updatedInput"]["session"]
    assert session["cwd"] == str(tmp_path)


def test_normal_when_input_invalid(run_hook: Any) -> None:
    """JSON でない入力では何も出さずに終わり、ツールの呼び出しを止めない（正常系）。"""
    # 実行
    result = run_hook("not json", {})
    # 検証
    assert (result["returncode"], result["stdout"]) == (0, "")
