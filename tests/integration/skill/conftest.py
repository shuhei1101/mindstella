"""スキルの結合テストの共通 fixture（登録のスクリプトを動かす隔離した環境）。"""

from __future__ import annotations

import os
import stat
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from .register_helpers import BASHRC_USER_LINE, LockFiles, RegisterSandbox

# 書き込みの権限を外したファイルの権限
READ_ONLY_FILE_MODE = 0o400


@pytest.fixture
def register_sandbox(tmp_path: Path) -> RegisterSandbox:
    """空のホームのフォルダ（`~/.bashrc` に利用者の行を 1 行持つ）と、偽の `claude`・起動スクリプトを置く場所を作る。"""
    home = tmp_path / "home"
    tools_dir = tmp_path / "tools"
    records_dir = tmp_path / "records"
    for folder in (home, tools_dir, records_dir):
        folder.mkdir()
    (home / ".bashrc").write_text(f"{BASHRC_USER_LINE}\n", encoding="utf-8")
    return RegisterSandbox(
        root=tmp_path, home=home, tools_dir=tools_dir, records_dir=records_dir
    )


@pytest.fixture
def lock_files() -> Iterator[LockFiles]:
    """ファイルを読み取りだけにする関数を返し、テストの後で元に戻す。"""
    # 権限を外しても書けてしまう環境（root・Windows）では、書き込めない場合を作れない
    if sys.platform == "win32" or os.geteuid() == 0:
        pytest.skip("書き込みの権限を外せない環境（root か Windows）")
    locked: list[Path] = []

    def _lock(*paths: Path) -> None:
        """渡したファイルを読み取りだけにして、後で戻せるよう記録する。"""
        for path in paths:
            path.chmod(READ_ONLY_FILE_MODE)
            locked.append(path)

    yield _lock
    # 一時フォルダを片付けられるよう、権限を戻す
    for path in locked:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
