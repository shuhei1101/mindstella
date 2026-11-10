"""サーバーの結合テストの共通 fixture（ワークスペースと MCP サーバーの起動は tests/workspace_fixtures.py）。"""

from __future__ import annotations

import os
import shutil
import stat
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from .fixture_types import (
    CallTool,
    FindOldPython,
    LockDirs,
    McpServer,
    StartFakeTranscriber,
    StartServer,
    StartVoiceServer,
)
from .http_helpers import EventStream
from .transcriber_helpers import FakeMode, FakeTranscriber, bind_closed_port, override_sitecustomize

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


# 文字起こしのサービスの URL を渡す環境変数
TRANSCRIBER_URL_ENV = "MINDSTELLA_TRANSCRIBER_URL"


@pytest.fixture
def start_fake_transcriber() -> Iterator[StartFakeTranscriber]:
    """偽の文字起こしのサービスを立てる関数を返し、テストの後で全て止める。"""
    started: list[FakeTranscriber] = []

    def _start(mode: FakeMode) -> FakeTranscriber:
        """振る舞いの種類で偽のサーバーを空きポートに立てる。"""
        fake = FakeTranscriber(mode=mode)
        fake.start()
        started.append(fake)
        return fake

    yield _start
    for fake in started:
        fake.stop()


@pytest.fixture
def start_voice_server(start_server: StartServer, tmp_path: Path) -> StartVoiceServer:
    """文字起こしのサービスの URL を環境変数に入れて常駐サーバーを立てる関数を返す。"""

    def _start(transcriber_url: str, overrides: dict[str, dict[str, object]] | None = None) -> McpServer:
        """overrides（モジュール名 → 定数名 → 値）があれば、読み込んだ後に差し替える sitecustomize を通して立てる。"""
        extra_env = {TRANSCRIBER_URL_ENV: transcriber_url}
        # 上限を差し替える: sitecustomize を置いたフォルダを PYTHONPATH に入れる
        if overrides:
            hook_dir = tmp_path / "transcriber-overrides"
            hook_dir.mkdir(exist_ok=True)
            (hook_dir / "sitecustomize.py").write_text(override_sitecustomize(overrides), encoding="utf-8")
            extra_env["PYTHONPATH"] = os.pathsep.join(
                path for path in (str(hook_dir), os.environ.get("PYTHONPATH", "")) if path
            )
        return start_server(extra_env=extra_env)

    return _start

@pytest.fixture
def unreachable_transcriber_url() -> Iterator[str]:
    """誰も待ち受けない文字起こしのサービスの URL を返し、テストの間はそのポートを押さえておく。"""
    held = bind_closed_port()
    yield f"http://127.0.0.1:{held.getsockname()[1]}"
    held.close()
