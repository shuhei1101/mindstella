"""起動スクリプト（bin/mindstella）を、隔離した環境で動かす共通の fixture と関数（結合テストと E2E テストが共有する）。

`claude` は偽物を、`tmux` は専用のソケット（`-L`）と一時フォルダへ向けるラッパーを `PATH` の先頭に置き、
利用者の tmux のセッションに触れない。fixture は `tests/conftest.py` が読み込む。
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
from workspace_fixtures import REPO_ROOT, MakeVenv

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

    def env(
        self,
        venv: Path | None,
        extra_env: dict[str, str] | None = None,
        *,
        with_config: bool = True,
    ) -> dict[str, str]:
        """起動スクリプトに渡す環境変数。`PATH` はこのフォルダだけにし、extra_env があれば足す。

        with_config が偽なら `CLAUDE_CONFIG_DIR` を渡さない（extra_env で渡したものは残る）。
        """
        env = {
            "PATH": str(self.tools_dir),
            "HOME": str(self.root),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "TMUX_TMPDIR": str(self.tmux_tmpdir),
        }
        # 設定のフォルダ（アカウント）を渡すか
        if with_config:
            env["CLAUDE_CONFIG_DIR"] = str(self.config_dir)
        if venv is not None:
            env["MINDSTELLA_VENV"] = str(venv)
        return {**env, **(extra_env or {})}

    def launch(
        self,
        *args: str,
        venv: Path | None,
        script: Path = PLUGIN_DIR / "bin" / "mindstella",
        cwd: Path | None = None,
        extra_env: dict[str, str] | None = None,
        with_config: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """起動スクリプトを標準出力が端末でない形で動かす。終了コードが 0 以外でも例外にしない。"""
        return subprocess.run(
            [str(script), *args],
            env=self.env(venv, extra_env, with_config=with_config),
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


def session_name(folder: Path, config_dir: Path | None = None) -> str:
    """フォルダの絶対パス（と、あれば設定のフォルダの絶対パス）の SHA-256 の先頭 6 桁から、セッションの名前を作る。"""
    hashed = str(folder.resolve())
    # 設定のフォルダ（アカウント）があれば、改行を挟んでつなぐ
    if config_dir is not None:
        hashed += "\n" + str(config_dir.resolve())
    digest = hashlib.sha256(hashed.encode("utf-8")).hexdigest()[:HASH_DIGITS]
    return f"{SESSION_PREFIX}{folder.name}-{digest}"


def copy_plugin(destination: Path) -> Path:
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


def read_mcp_config(args_file: Path) -> dict[str, Any]:
    """偽の `claude` が受け取った `--mcp-config` のファイルを読む。"""
    args = args_file.read_text(encoding="utf-8").splitlines()
    assert args[0] == "--mcp-config"
    return json.loads(Path(args[1]).read_text(encoding="utf-8"))
