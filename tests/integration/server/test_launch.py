"""bin/mindstella（起動スクリプト）の結合テスト。

`claude` は偽物を、`tmux` は専用のソケット（`-L`）と一時フォルダへ向けるラッパーを `PATH` の先頭に置き、
利用者の tmux のセッションに触れない。MCP の設定どおりのサーバーは、本物の MCP サーバーとして立てて確かめる。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from workspace_fixtures import REPO_ROOT, McpServer

from .fixture_types import MakeVenv

# 起動するスクリプトと、偽の `claude` が `installPath` として返す本物のプラグインのフォルダ
PLUGIN_DIR = REPO_ROOT / "plugins" / "mindstella"

# 起動スクリプト 1 回を待つ上限秒数
LAUNCH_TIMEOUT_SEC = 120

# 偽の `claude` が起動されるのを待つ上限秒数と、確かめる間隔
FAKE_CLAUDE_WAIT_SEC = 10
POLL_INTERVAL_SEC = 0.1

# セッションの名前の頭と、絶対パスのハッシュの桁数
SESSION_PREFIX = "mindstella-"
HASH_DIGITS = 6

# 起動スクリプトが使う外部コマンド（`PATH` の唯一のフォルダにリンクを置く）
REQUIRED_COMMANDS = ("bash", "dirname", "mkdir", "python3", "sleep")

# 偽の `claude`（`plugin list --json` には一覧を返し、それ以外では受け取ったものを控えて待ち続ける）
FAKE_CLAUDE = """#!/bin/sh
if [ "$1" = "plugin" ] && [ "$2" = "list" ]; then
  printf '%s\\n' '{listing}'
  exit 0
fi
record="{record_dir}/started-$$"
printf '%s\\n' "$@" > "$record.args"
printf '%s' "${{CLAUDE_CONFIG_DIR:-}}" > "$record.config"
exec sleep 600
"""

# 専用のソケットで本物の tmux を呼ぶラッパー
TMUX_WRAPPER = """#!/bin/sh
unset TMUX
exec {tmux} -u -L {socket} "$@"
"""


@dataclass
class LaunchSandbox:
    """起動スクリプトを動かす、隔離した環境（`PATH`・tmux・偽の claude・仮想環境）。"""

    root: Path
    tools_dir: Path
    record_dir: Path
    config_dir: Path
    socket: str
    tmux_tmpdir: Path
    real_tmux: str

    def write_claude(self, listing: list[dict[str, Any]]) -> None:
        """偽の `claude` を置く。listing が `plugin list --json` の出力になる。"""
        script = self.tools_dir / "claude"
        script.write_text(
            FAKE_CLAUDE.format(listing=json.dumps(listing), record_dir=self.record_dir),
            encoding="utf-8",
        )
        script.chmod(0o755)

    def remove_tool(self, name: str) -> None:
        """`PATH` のフォルダから外部コマンドを外す（無い場合の流れを作る）。"""
        (self.tools_dir / name).unlink()

    def env(self, venv: Path | None) -> dict[str, str]:
        """起動スクリプトに渡す環境変数。`PATH` はこのフォルダだけにする。"""
        env = {
            "PATH": str(self.tools_dir),
            "HOME": str(self.root),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "TMUX_TMPDIR": str(self.tmux_tmpdir),
            "CLAUDE_CONFIG_DIR": str(self.config_dir),
        }
        if venv is not None:
            env["MINDSTELLA_VENV"] = str(venv)
        return env

    def launch(
        self,
        *args: str,
        venv: Path | None,
        script: Path = PLUGIN_DIR / "bin" / "mindstella",
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """起動スクリプトを標準出力が端末でない形で動かす。終了コードが 0 以外でも例外にしない。"""
        return subprocess.run(
            [str(script), *args],
            env=self.env(venv),
            cwd=cwd or self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=LAUNCH_TIMEOUT_SEC,
            check=False,
        )

    def tmux(self, *args: str) -> subprocess.CompletedProcess[str]:
        """専用のソケットの tmux を呼ぶ。"""
        return subprocess.run(
            [str(self.tools_dir / "tmux"), *args],
            env=self.env(None),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=LAUNCH_TIMEOUT_SEC,
            check=False,
        )

    def kill_server(self) -> None:
        """このテストの専用のソケットの tmux のサーバーだけを止める（必ず `-L` を付ける）。"""
        subprocess.run(
            [self.real_tmux, "-L", self.socket, "kill-server"],
            env={key: value for key, value in self.env(None).items() if key != "PATH"},
            capture_output=True,
            check=False,
        )

    def sessions(self) -> list[str]:
        """tmux のセッションの名前の一覧を返す（サーバーが無ければ空）。"""
        result = self.tmux("list-sessions", "-F", "#{session_name}")
        return result.stdout.split() if result.returncode == 0 else []

    def session_path(self, name: str) -> Path:
        """セッションの作業フォルダを返す。"""
        return Path(
            self.tmux(
                "display-message", "-p", "-t", f"={name}:", "#{pane_current_path}"
            ).stdout.strip()
        )

    def started(self) -> list[Path]:
        """偽の `claude` が起動された記録（受け取った引数のファイル）を返す。"""
        return sorted(self.record_dir.glob("started-*.args"))

    def wait_started(self, count: int = 1) -> list[Path]:
        """偽の `claude` が count 回起動されるまで待ち、その記録を返す。"""
        deadline = time.monotonic() + FAKE_CLAUDE_WAIT_SEC
        while time.monotonic() < deadline:
            if len(self.started()) >= count:
                break
            time.sleep(POLL_INTERVAL_SEC)
        return self.started()


def _session_name(folder: Path) -> str:
    """フォルダの絶対パスの SHA-256 の先頭 6 桁から、セッションの名前を作る。"""
    digest = hashlib.sha256(str(folder.resolve()).encode("utf-8")).hexdigest()[:HASH_DIGITS]
    return f"{SESSION_PREFIX}{folder.name}-{digest}"


def _copy_plugin(destination: Path) -> Path:
    """プラグインのフォルダを複製して、その場所を返す（別の版のフォルダの代わり）。"""
    shutil.copytree(PLUGIN_DIR, destination, ignore=shutil.ignore_patterns("__pycache__"))
    return destination


@pytest.fixture
def sandbox(tmp_path: Path) -> Iterator[LaunchSandbox]:
    """隔離した環境を作り、テストの後で専用の tmux のサーバーだけを止める。"""
    real_tmux = shutil.which("tmux")
    if real_tmux is None:
        pytest.skip("tmux が無い")
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    for name in REQUIRED_COMMANDS:
        found = shutil.which(name)
        assert found is not None, name
        (tools_dir / name).symlink_to(found)
    # ソケットのパスが長いとつながらないため、短い一時フォルダに置く
    tmux_tmpdir = Path(tempfile.mkdtemp(prefix="mst", dir="/tmp"))
    socket = f"mindstella-test-{os.getpid()}-{tmux_tmpdir.name}"
    wrapper = tools_dir / "tmux"
    wrapper.write_text(TMUX_WRAPPER.format(tmux=real_tmux, socket=socket), encoding="utf-8")
    wrapper.chmod(0o755)
    record_dir = tmp_path / "records"
    record_dir.mkdir()
    config_dir = tmp_path / "claude-config"
    config_dir.mkdir()
    sandbox = LaunchSandbox(
        root=tmp_path,
        tools_dir=tools_dir,
        record_dir=record_dir,
        config_dir=config_dir,
        socket=socket,
        tmux_tmpdir=tmux_tmpdir,
        real_tmux=real_tmux,
    )
    sandbox.write_claude([{"id": "mindstella@mindstella", "installPath": str(PLUGIN_DIR)}])
    yield sandbox
    # 専用のソケットを指定して、このテストの tmux のサーバーだけを止める
    sandbox.kill_server()
    shutil.rmtree(tmux_tmpdir, ignore_errors=True)


@pytest.fixture
def ready_venv(make_venv: MakeVenv) -> Path:
    """PyYAML・jsonschema・mcp が見える仮想環境を作る。"""
    return make_venv("venv")


def _read_mcp_config(args_file: Path) -> dict[str, Any]:
    """偽の `claude` が受け取った `--mcp-config` のファイルを読む。"""
    args = args_file.read_text(encoding="utf-8").splitlines()
    assert args[0] == "--mcp-config"
    return json.loads(Path(args[1]).read_text(encoding="utf-8"))


def test_normal(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """依存がそろっていれば、今の版のサーバーを渡した Claude Code を tmux のセッションで立てる（正常系）。"""
    # 準備
    folder = sandbox.root / "家計簿アプリ"
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 0, result.stderr
    assert folder.is_dir()
    name = _session_name(folder)
    assert sandbox.sessions() == [name]
    assert sandbox.session_path(name) == folder.resolve()
    started = sandbox.wait_started()
    assert len(started) == 1
    config = _read_mcp_config(started[0])
    mindstella = config["mcpServers"]["mindstella"]
    assert mindstella["command"] == str(ready_venv / "bin" / "python")
    assert mindstella["args"] == [str(PLUGIN_DIR / "skills" / "mindmap" / "scripts" / "server.py")]
    assert started[0].with_suffix(".config").read_text(encoding="utf-8") == str(sandbox.config_dir)
    # その MCP の設定どおりにサーバーを立ててつなぐと、ツールの一覧が返る
    server = McpServer(
        python=mindstella["command"],
        env={**os.environ, "PYTHONUTF8": "1"},
        cwd=folder,
        script=Path(mindstella["args"][0]),
    )
    try:
        assert len(server.list_tools()) == 18
    finally:
        server.stop()
    assert f"tmux attach-session -t ={name}" in result.stdout


def test_normal_when_plugin_upgraded(
    sandbox: LaunchSandbox, ready_venv: Path, tmp_path: Path
) -> None:
    """古い版のフォルダのスクリプトを叩いても、新しい版のサーバーを指す（正常系）。"""
    # 準備
    old_dir = _copy_plugin(tmp_path / "plugin-old")
    new_dir = _copy_plugin(tmp_path / "plugin-new")
    sandbox.write_claude([{"id": "mindstella@mindstella", "installPath": str(new_dir)}])
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv, script=old_dir / "bin" / "mindstella")
    # 検証
    assert result.returncode == 0, result.stderr
    started = sandbox.wait_started()
    assert len(started) == 1
    config = _read_mcp_config(started[0])
    assert config["mcpServers"]["mindstella"]["args"] == [
        str(new_dir / "skills" / "mindmap" / "scripts" / "server.py")
    ]


def test_normal_when_session_exists(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """既にあるセッションには新しく立てず、つなぐコマンドを返す（正常系）。"""
    # 準備
    first = sandbox.launch("家計簿アプリ", venv=ready_venv)
    assert first.returncode == 0, first.stderr
    sandbox.wait_started()
    sessions_before = sandbox.sessions()
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 0, result.stderr
    assert sandbox.sessions() == sessions_before
    assert len(sandbox.started()) == 1
    assert "既にある" in result.stderr
    assert f"tmux attach-session -t ={sessions_before[0]}" in result.stdout


def test_error_when_dependency_missing(sandbox: LaunchSandbox, make_venv: MakeVenv) -> None:
    """ライブラリを入れていない仮想環境では、そろえるコマンドを示して何も立てない（異常系）。"""
    # 準備
    bare_venv = make_venv("bare-venv", with_libraries=False)
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=bare_venv)
    # 検証
    assert result.returncode == 1
    for package in ("PyYAML", "jsonschema", "mcp"):
        assert package in result.stderr
    assert "-m pip install" in result.stderr
    assert sandbox.sessions() == []
    assert sandbox.started() == []


def test_error_when_tmux_missing(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """tmux が無ければ、入れるよう示して Claude Code を立てない（異常系）。"""
    # 準備
    sandbox.remove_tool("tmux")
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 1
    assert "tmux" in result.stderr
    assert sandbox.started() == []


def test_error_when_claude_missing(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """claude が無ければ、入れるよう示して止まる（異常系）。"""
    # 準備
    sandbox.remove_tool("claude")
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 1
    assert "claude" in result.stderr
    assert sandbox.sessions() == []


def test_error_when_plugin_not_installed(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """プラグインの一覧に mindstella が無ければ、インストールを案内して止まる（異常系）。"""
    # 準備
    sandbox.write_claude([])
    # 実行
    result = sandbox.launch("家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 1
    assert "mindstella@mindstella" in result.stderr
    assert "インストール" in result.stderr
    assert sandbox.sessions() == []


def test_error_when_folder_missing(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """引数が無ければ、使い方を出して止まる（異常系）。"""
    # 実行
    result = sandbox.launch(venv=ready_venv)
    # 検証
    assert result.returncode == 2
    assert "使い方" in result.stderr
    assert sandbox.started() == []


def test_normal_when_same_folder_name_elsewhere(sandbox: LaunchSandbox, ready_venv: Path) -> None:
    """名前が同じでも場所が違うフォルダは、別のセッションを立てる（正常系）。"""
    # 準備
    first = sandbox.launch("仕事/家計簿アプリ", venv=ready_venv)
    assert first.returncode == 0, first.stderr
    sandbox.wait_started()
    work_folder = sandbox.root / "仕事" / "家計簿アプリ"
    personal_folder = sandbox.root / "個人" / "家計簿アプリ"
    # 実行
    result = sandbox.launch("個人/家計簿アプリ", venv=ready_venv)
    # 検証
    assert result.returncode == 0, result.stderr
    assert sorted(sandbox.sessions()) == sorted(
        [_session_name(work_folder), _session_name(personal_folder)]
    )
    assert sandbox.session_path(_session_name(work_folder)) == work_folder.resolve()
    assert sandbox.session_path(_session_name(personal_folder)) == personal_folder.resolve()
    assert f"tmux attach-session -t ={_session_name(personal_folder)}" in result.stdout
    assert "既にある" not in result.stderr
