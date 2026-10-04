"""サーバーの結合テストの共通 fixture（ワークスペースと MCP サーバーの起動は tests/workspace_fixtures.py）。"""

from __future__ import annotations

import os
import shutil
import stat
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from .fixture_types import CallTool, FindOldPython, LockDirs
from .http_helpers import EventStream

# 下限より古い Python を探す候補（下限は 3.12）
OLD_PYTHON_NAMES = ("python3.8", "python3.9", "python3.10", "python3.11")

# 読み取りだけにするフォルダの権限
READ_ONLY_MODE = 0o500


@pytest.fixture
def lock_dirs() -> Iterator[LockDirs]:
    """フォルダを読み取りだけにする関数を返し、テストの後で元に戻す。"""
    # 権限を外しても書けてしまう環境（root・Windows）では、書き込めない場合を作れない
    if sys.platform == "win32" or os.geteuid() == 0:
        pytest.skip("書き込みの権限を外せない環境（root か Windows）")
    locked: list[Path] = []

    def _lock(*paths: Path) -> None:
        """渡したフォルダを読み取りだけにして、後で戻せるよう記録する。"""
        for path in paths:
            path.chmod(READ_ONLY_MODE)
            locked.append(path)

    yield _lock
    # 一時フォルダを片付けられるよう、権限を戻す
    for path in locked:
        path.chmod(stat.S_IRWXU)


@pytest.fixture
def find_old_python() -> FindOldPython:
    """下限（3.12）より古い Python を探す関数を返す。無ければ skip する。"""

    def _find() -> str:
        """手元にある 3.8〜3.11 の Python のうち最初のものを返す。無ければ skip する。"""
        for name in OLD_PYTHON_NAMES:
            found = shutil.which(name)
            if found is not None:
                return found
        pytest.skip("手元に 3.8〜3.11 の Python が無い")

    return _find


@pytest.fixture
def serve_preview(call_tool: CallTool) -> Callable[[Path], str]:
    """ワークスペースの配信を立てて（立っていればそのまま）、URL を返す関数を返す。"""

    def _serve(root: Path) -> str:
        """`preview_url` を呼び、配信の URL を返す。エラーならテストを止める。"""
        result = call_tool("preview_url", workspace=str(root))
        assert result.is_error is False, result.text
        assert result.data is not None
        return str(result.data["url"])

    return _serve


@pytest.fixture
def open_events() -> Iterator[Callable[[str], EventStream]]:
    """書き換えの知らせにつなぐ関数を返し、テストの後でつないだものを全て閉じる。"""
    opened: list[EventStream] = []

    def _open(base_url: str) -> EventStream:
        """配信の `/api/events` につなぐ。"""
        stream = EventStream(base_url)
        opened.append(stream)
        return stream

    yield _open
    for stream in opened:
        stream.close()
