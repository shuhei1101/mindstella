"""inject_session.py（PreToolUse のフックでツールの引数 session にセッションの値を入れる）の単体テスト。"""

from __future__ import annotations

import ast
import io
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

import inject_session

# tmux の中のセッションの環境変数
TMUX_ENVIRON = {
    "TMUX": "/tmp/tmux-1000/default,1234,0",
    "TMUX_PANE": "%3",
    "CLAUDE_CONFIG_DIR": "/c",
}

# 見つけた Claude Code のプロセスの PID と起動時刻
CLAUDE_PROCESS = (42, "Mon Nov 2 10:00:00 2026")

# フックが受け取るツールの呼び出し（session は Claude が書いた値で、フックが置き換える）
HOOK_INPUT = {"cwd": "/w", "tool_input": {"workspace": "talk", "session": {"cwd": "/etc"}}}


class _FindRecorder:
    """呼ばれた PID を控え、決めたプロセスを返す偽の find_claude。"""

    def __init__(self, result: tuple[int, str] | None) -> None:
        """返すプロセス（見つからなければ None）を受け取る。"""
        self.calls: list[int] = []
        self._result = result

    def __call__(self, pid: int) -> tuple[int, str] | None:
        """PID を控えて、決めたプロセスを返す。"""
        self.calls.append(pid)
        return self._result


class _PsRunner:
    """`ps -o ppid=,lstart=,comm= -p {PID}` に、PID ごとに決めた行を返す偽の run。"""

    def __init__(self, rows: dict[str, str], *, returncode: int = 0) -> None:
        """PID（文字列）→ 出力の行と、終了コードを受け取る。"""
        self.commands: list[list[str]] = []
        self._rows = rows
        self._returncode = returncode

    def __call__(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        """引数を控え、`-p` の次の PID の行を返す（text か encoding があれば文字列、無ければバイト列）。"""
        self.commands.append(command)
        line = self._rows.get(command[-1], "")
        is_text = bool(kwargs.get("text") or kwargs.get("encoding") or kwargs.get("universal_newlines"))
        stdout: Any = line if is_text else line.encode("utf-8")
        return subprocess.CompletedProcess(args=command, returncode=self._returncode, stdout=stdout)


def _run_main(
    text: str, environ: dict[str, str], find_claude: _FindRecorder
) -> tuple[int, str]:
    """main を呼び、終了コードと標準出力を返す。"""
    stdout = io.StringIO()
    code = inject_session.main(
        stdin=io.StringIO(text), stdout=stdout, environ=environ, find_claude=find_claude
    )
    return code, stdout.getvalue()


def test_main() -> None:
    """session を入れた updatedInput を出す（正常系）。"""
    # 準備
    find_claude = _FindRecorder(CLAUDE_PROCESS)
    # 実行
    code, out = _run_main(json.dumps(HOOK_INPUT), TMUX_ENVIRON, find_claude)
    # 検証
    output = json.loads(out)["hookSpecificOutput"]
    assert code == 0
    assert output["hookEventName"] == "PreToolUse"
    assert output["updatedInput"]["workspace"] == "talk"
    assert output["updatedInput"]["session"] == {
        "cwd": "/w",
        "claude_config_dir": "/c",
        "tmux": "/tmp/tmux-1000/default,1234,0",
        "tmux_pane": "%3",
        "claude_pid": 42,
        "claude_started_at": "Mon Nov 2 10:00:00 2026",
    }


def test_main_when_outside_tmux() -> None:
    """tmux の外では Claude Code のプロセスを探さない（正常系）。"""
    # 準備
    find_claude = _FindRecorder(CLAUDE_PROCESS)
    # 実行
    code, out = _run_main(json.dumps(HOOK_INPUT), {"CLAUDE_CONFIG_DIR": "/c"}, find_claude)
    # 検証
    session = json.loads(out)["hookSpecificOutput"]["updatedInput"]["session"]
    assert code == 0
    assert set(session) == {"cwd", "claude_config_dir"}
    assert find_claude.calls == []


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("not json", id="not_json"),
        pytest.param("[]", id="not_object"),
        pytest.param('{"cwd": "/w"}', id="no_tool_input"),
        pytest.param('{"cwd": 1, "tool_input": {}}', id="cwd_not_string"),
    ],
)
def test_main_when_input_invalid(text: str) -> None:
    """読めない入力では何も出さない（正常系）。"""
    # 準備
    find_claude = _FindRecorder(CLAUDE_PROCESS)
    # 実行
    code, out = _run_main(text, TMUX_ENVIRON, find_claude)
    # 検証
    assert code == 0
    assert out == ""


def test_main_when_old_syntax(scripts_dir: Path) -> None:
    """Python 3.8 の構文で読め、型注釈を実行時に評価しない（正常系）。"""
    # 準備
    source = (scripts_dir / "inject_session.py").read_text(encoding="utf-8")
    # 実行
    tree = ast.parse(source, feature_version=(3, 8))
    # 検証
    # 先頭は docstring で、その次の文が `from __future__ import annotations`
    statement = tree.body[1]
    assert isinstance(statement, ast.ImportFrom)
    assert statement.module == "__future__"
    assert len(statement.names) == 1
    assert statement.names[0].name == "annotations"


@pytest.mark.parametrize(
    ("environ", "claude", "expected"),
    [
        pytest.param(
            TMUX_ENVIRON,
            CLAUDE_PROCESS,
            {
                "cwd": "/w",
                "claude_config_dir": "/c",
                "tmux": "/tmp/tmux-1000/default,1234,0",
                "tmux_pane": "%3",
                "claude_pid": 42,
                "claude_started_at": "Mon Nov 2 10:00:00 2026",
            },
            id="inside_tmux",
        ),
        pytest.param(
            TMUX_ENVIRON,
            None,
            {
                "cwd": "/w",
                "claude_config_dir": "/c",
                "tmux": "/tmp/tmux-1000/default,1234,0",
                "tmux_pane": "%3",
            },
            id="claude_not_found",
        ),
        pytest.param(
            {**TMUX_ENVIRON, "TMUX_PANE": ""},
            CLAUDE_PROCESS,
            {"cwd": "/w", "claude_config_dir": "/c"},
            id="pane_empty",
        ),
        pytest.param({}, None, {"cwd": "/w", "claude_config_dir": "/h/.claude"}, id="nothing_set"),
    ],
)
def test_build_session(
    monkeypatch: pytest.MonkeyPatch,
    environ: dict[str, str],
    claude: tuple[int, str] | None,
    expected: dict[str, Any],
) -> None:
    """tmux の中と外で入れるキーを分ける（正常系）。"""
    # 準備（既定の設定のフォルダは読み込んだ時点のホームで決まるため、ホームと合わせて差し替える）
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("/h")))
    monkeypatch.setattr(inject_session, "DEFAULT_CONFIG_DIR", Path("/h") / ".claude")
    # 実行
    result = inject_session.build_session("/w", environ, claude)
    # 検証
    assert result == expected


def test_find_claude_process() -> None:
    """間に別のコマンドが挟まっても claude で止まる（正常系）。"""
    # 準備
    run = _PsRunner(
        {
            "100": "   90 Mon Nov  2 10:00:00 2026 bash\n",
            "90": "   80 Mon Nov  2 09:59:00 2026 claude-balancer\n",
            "80": "   70 Mon Nov  2 09:58:00 2026 /usr/bin/claude\n",
        }
    )
    # 実行
    result = inject_session.find_claude_process(100, run=run)
    # 検証
    assert result == (80, "Mon Nov 2 09:58:00 2026")


@pytest.mark.parametrize(
    ("rows", "returncode", "expected_calls"),
    [
        pytest.param({"100": "    1 Mon Nov  2 10:00:00 2026 bash\n"}, 0, 1, id="reached_init"),
        pytest.param({}, 1, 1, id="ps_failed"),
        pytest.param(
            {"100": "  100 Mon Nov  2 10:00:00 2026 bash\n"},
            0,
            inject_session.PARENT_DEPTH_MAX,
            id="depth_limit",
        ),
    ],
)
def test_find_claude_process_when_not_found(
    rows: dict[str, str], returncode: int, expected_calls: int
) -> None:
    """見つからなければ None（正常系）。"""
    # 準備
    run = _PsRunner(rows, returncode=returncode)
    # 実行
    result = inject_session.find_claude_process(100, run=run)
    # 検証
    assert result is None
    assert len(run.commands) == expected_calls
