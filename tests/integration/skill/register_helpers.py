"""起動スクリプトの登録（register.py）の結合テストが共有する、隔離したホームと偽の `claude`・偽の起動スクリプト。

ホームのフォルダは空の一時フォルダを `HOME` にして差し替え、`PATH` の先頭に置いた偽の `claude` が
`plugin list --json` に決めた `installPath` を返す。偽の `bin/mindstella` は、受け取った引数と
`CLAUDE_CONFIG_DIR` をファイルに書く。alias の動作は `bash -ic` で確かめる。
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .skill_files import PLUGIN_DIR

__all__ = [
    "BASHRC_USER_LINE",
    "CONFIG_UNSET",
    "LockFiles",
    "MARK_BEGIN",
    "REGISTER_SCRIPT",
    "RegisterSandbox",
    "read_report",
]

type LockFiles = Callable[..., None]

# 登録のスクリプト
REGISTER_SCRIPT = PLUGIN_DIR / "skills" / "setup" / "scripts" / "register.py"

# `~/.bashrc` に置いておく、印の範囲の外にある利用者の行
BASHRC_USER_LINE = "export EDITOR=vim"

# 印の範囲の頭の行
MARK_BEGIN = "# >>> mindstella >>>"

# 偽の起動スクリプトが `CLAUDE_CONFIG_DIR` を受け取らなかったときに控える値
CONFIG_UNSET = "__unset__"

# 登録のスクリプトと `bash -ic` を待つ上限秒数
COMMAND_TIMEOUT_SEC = 60

# 偽の `claude`（`plugin list --json` には設定のフォルダごとの一覧を返し、それ以外は失敗する）
FAKE_CLAUDE = """#!/bin/sh
if [ "$1" = "plugin" ] && [ "$2" = "list" ]; then
  case "${{CLAUDE_CONFIG_DIR:-}}" in
{cases}
    *) printf '[]\\n' ;;
  esac
  exit 0
fi
exit 1
"""

# 偽の `bin/mindstella`（引数と `CLAUDE_CONFIG_DIR` を `{records}/{name}.args`・`.config` に書く）
FAKE_LAUNCH = """#!/bin/sh
printf '%s\\n' "$@" > "{records}/{name}.args"
if [ "${{CLAUDE_CONFIG_DIR+set}}" = set ]; then
  printf '%s' "$CLAUDE_CONFIG_DIR" > "{records}/{name}.config"
else
  printf '%s' '{unset}' > "{records}/{name}.config"
fi
"""


@dataclass
class RegisterSandbox:
    """登録のスクリプトを動かす、隔離した環境（ホーム・偽の `claude`・偽の起動スクリプトの記録）。"""

    root: Path
    home: Path
    tools_dir: Path
    records_dir: Path

    @property
    def bashrc(self) -> Path:
        """ログインシェルの設定ファイル（`SHELL=/bin/bash` のとき印の範囲を足す先）。"""
        return self.home / ".bashrc"

    @property
    def registration_dir(self) -> Path:
        """登録の中身と `shell.sh` を置くフォルダ（`XDG_CONFIG_HOME` を消しているので `~/.config/mindstella`）。"""
        return self.home / ".config" / "mindstella"

    def env(self) -> dict[str, str]:
        """登録のスクリプトと `bash -ic` に渡す環境変数。`XDG_CONFIG_HOME`・`CLAUDE_CONFIG_DIR` は持たない。"""
        return {
            "HOME": str(self.home),
            "SHELL": "/bin/bash",
            "PATH": f"{self.tools_dir}{os.pathsep}{os.environ['PATH']}",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "HISTFILE": "/dev/null",
            "TERM": "dumb",
        }

    def write_claude(self, listings: dict[str, str]) -> None:
        """偽の `claude` を置く。listings は `CLAUDE_CONFIG_DIR`（既定は空文字）→ `installPath` の対応。"""
        cases = "\n".join(
            f"    '{config_dir}') printf '%s\\n' '{json.dumps([{'id': 'mindstella@mindstella', 'installPath': install}])}' ;;"
            for config_dir, install in listings.items()
        )
        script = self.tools_dir / "claude"
        script.write_text(FAKE_CLAUDE.format(cases=cases), encoding="utf-8")
        script.chmod(0o755)

    def make_install(self, name: str) -> Path:
        """偽の起動スクリプトを持つ `installPath` を作って返す。受け取った引数と環境変数は `launch_record` で読む。"""
        install = self.root / f"install-{name}"
        (install / "bin").mkdir(parents=True)
        launch = install / "bin" / "mindstella"
        launch.write_text(
            FAKE_LAUNCH.format(records=self.records_dir, name=name, unset=CONFIG_UNSET),
            encoding="utf-8",
        )
        launch.chmod(0o755)
        return install

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        """登録のスクリプトをシステムの `python3` で動かす。終了コードが 0 以外でも例外にしない。"""
        return subprocess.run(
            ["python3", str(REGISTER_SCRIPT), *args],
            env=self.env(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=COMMAND_TIMEOUT_SEC,
            check=False,
        )

    def bash(self, command: str) -> subprocess.CompletedProcess[str]:
        """対話のシェル（`bash -ic`）でコマンドを動かし、ログインシェルの設定ファイルを読ませる。"""
        return subprocess.run(
            ["bash", "-ic", command],
            env=self.env(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=COMMAND_TIMEOUT_SEC,
            check=False,
        )

    def launch_record(self, name: str) -> tuple[list[str], str]:
        """偽の起動スクリプトが受け取った引数と `CLAUDE_CONFIG_DIR`（受け取らなければ `CONFIG_UNSET`）を返す。"""
        args = (self.records_dir / f"{name}.args").read_text(encoding="utf-8").splitlines()
        config = (self.records_dir / f"{name}.config").read_text(encoding="utf-8")
        return args, config


def read_report(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    """登録のスクリプトが標準出力に出した JSON を読む。"""
    return json.loads(result.stdout)  # type: ignore[no-any-return]
