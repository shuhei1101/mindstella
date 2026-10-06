"""server.py（MCP サーバーの組み立て・ツールの登録・結果とエラー）の単体テスト。"""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Coroutine
from pathlib import Path
from typing import Any

import pytest
from mcp.types import CallToolResult, TextContent

import migrator
import serve
import server
import store
from errors import SchemaMismatchError, WorkspaceNotFoundError
from fixture_types import MakeItem, MakeWorkspace

# build_server が登録するツールの名前（インターフェース定義『MCP サーバーの起動』）
EXPECTED_TOOL_NAMES = (
    "init",
    "add",
    "update",
    "update_settings",
    "adopt",
    "edit_option",
    "batch",
    "changes_since_read",
    "commit",
    "pending",
    "status",
    "next",
    "impact",
    "find",
    "show",
    "attrs",
    "tags",
    "check",
    "goal",
    "migrate",
    "clear_release",
    "export",
    "preview_url",
    "submissions",
    "take_submission",
)


class _FakeServer:
    """run が呼ばれた引数を控えて、すぐ戻る偽のサーバー。"""

    def __init__(self) -> None:
        """run の引数を控える入れ物を作る。"""
        self.transports: list[str] = []

    def run(self, transport: str) -> None:
        """動かさずに、渡された通り道だけを控える。"""
        self.transports.append(transport)


class _RaisingServer(_FakeServer):
    """run が RuntimeError を送る偽のサーバー。"""

    def run(self, transport: str) -> None:
        """通り道を控えてから、例外で戻る。"""
        super().run(transport)
        raise RuntimeError("サーバーが落ちました")


def _text_of(result: CallToolResult) -> str:
    """結果の本文（最初の text）を返す。"""
    content = result.content[0]
    assert isinstance(content, TextContent)
    return content.text


def _run_async[T](coroutine: Coroutine[Any, Any, T]) -> T:
    """動いているイベントループがあっても呼べるよう、新しいスレッドで `asyncio.run` を呼んで結果を返す。"""
    outcome: list[T] = []
    errors: list[BaseException] = []

    def _target() -> None:
        """コルーチンを動かし、結果か例外を控える。"""
        try:
            outcome.append(asyncio.run(coroutine))
        except BaseException as error:  # noqa: BLE001
            # スレッドの外へ送り直すため、広く捕まえて控える
            errors.append(error)

    thread = threading.Thread(target=_target)
    thread.start()
    thread.join()
    if errors:
        raise errors[0]
    return outcome[0]


def _spy_stop_all(monkeypatch: pytest.MonkeyPatch) -> list[serve.PreviewRegistry]:
    """PreviewRegistry.stop_all を、呼ばれた台帳を控える関数に差し替え、控える入れ物を返す。"""
    stopped: list[serve.PreviewRegistry] = []

    def _stop_all(self: serve.PreviewRegistry) -> None:
        """止めずに、呼ばれた台帳だけを控える。"""
        stopped.append(self)

    monkeypatch.setattr(serve.PreviewRegistry, "stop_all", _stop_all)
    return stopped


def test_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """サーバーが戻ったら配信を止めて 0（正常系）。"""
    # 準備
    stopped = _spy_stop_all(monkeypatch)
    fake = _FakeServer()
    received: dict[str, Any] = {}

    def _build(**kwargs: Any) -> _FakeServer:
        """渡された previews を控えて、偽のサーバーを返す。"""
        received.update(kwargs)
        return fake

    # 実行
    result = server.main(build=_build)
    # 検証
    assert result == 0
    assert fake.transports == ["stdio"]
    assert stopped == [received["previews"]]


def test_main_when_server_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """サーバーが例外で戻っても配信を止める（正常系）。"""
    # 準備
    stopped = _spy_stop_all(monkeypatch)
    received: dict[str, Any] = {}

    def _build(**kwargs: Any) -> _RaisingServer:
        """渡された previews を控えて、例外を送る偽のサーバーを返す。"""
        received.update(kwargs)
        return _RaisingServer()

    # 実行・検証
    with pytest.raises(RuntimeError, match="サーバーが落ちました"):
        server.main(build=_build)
    assert stopped == [received["previews"]]


def test_build_server(tmp_path: Path) -> None:
    """登録するツールを全て workspace つきで登録する（正常系）。"""
    # 準備
    previews = serve.PreviewRegistry(threading.Lock())
    mcp_server = server.build_server(previews=previews, write_lock=threading.Lock(), cwd=tmp_path)
    # 実行
    tools = _run_async(mcp_server.list_tools())
    # 検証
    assert tuple(tool.name for tool in tools) == EXPECTED_TOOL_NAMES
    assert server.TOOL_NAMES == EXPECTED_TOOL_NAMES
    assert all("workspace" in tool.input_schema["required"] for tool in tools)


def test_build_server_when_relative_workspace(
    tmp_path: Path, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """相対パスの workspace を作業フォルダから読む（正常系）。"""
    # 準備
    make_workspace(make_item("D-1"), name="ws")
    previews = serve.PreviewRegistry(threading.Lock())
    mcp_server = server.build_server(previews=previews, write_lock=threading.Lock(), cwd=tmp_path)
    # 実行
    result = _run_async(mcp_server.call_tool("attrs", {"workspace": "ws"}))
    # 検証
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    assert result.structured_content == {"attrs": []}


def test_call_tool() -> None:
    """辞書を結果にする（正常系）。"""
    # 実行
    result = server.call_tool(lambda: {"id": "D-1"}, write_lock=threading.Lock())
    # 検証
    assert result.is_error is False
    assert result.structured_content == {"id": "D-1"}


def test_call_tool_when_mindmap_error() -> None:
    """MindmapError はツールのエラー（正常系）。"""

    def _handler() -> dict[str, Any]:
        """ワークスペースが無いエラーを送る。"""
        raise WorkspaceNotFoundError("ワークスペースがありません: /x")

    # 実行
    result = server.call_tool(_handler, write_lock=threading.Lock())
    # 検証
    assert result.is_error is True
    assert _text_of(result).startswith("エラー: ")


def test_call_tool_when_unexpected_error() -> None:
    """予期しない例外もトレースバックを出さずツールのエラー（正常系）。"""

    def _handler() -> dict[str, Any]:
        """想定していない例外を送る。"""
        raise KeyError("x")

    # 実行
    result = server.call_tool(_handler, write_lock=threading.Lock())
    # 検証
    assert result.is_error is True
    text = _text_of(result)
    assert text.startswith("エラー: 予期しないエラー（KeyError）")
    assert "Traceback" not in text


def test_call_tool_when_lock_root(tmp_path: Path) -> None:
    """書き換えるツールは鍵を取って呼ぶ（正常系）。"""
    # 準備
    (tmp_path / ".mindstella").mkdir()
    (tmp_path / ".mindstella" / "config.yaml").write_text("", encoding="utf-8")
    write_lock = threading.Lock()
    locked_in_handler: list[bool] = []

    def _handler() -> dict[str, Any]:
        """呼ばれたときに鍵を持っているかを控える。"""
        locked_in_handler.append(write_lock.locked())
        return {}

    # 実行
    server.call_tool(_handler, write_lock=write_lock, lock_root=tmp_path)
    # 検証
    assert locked_in_handler == [True]
    assert write_lock.locked() is False
    assert (tmp_path / ".mindstella" / ".mindstella.lock").exists()


def test_call_tool_when_lock_require(tmp_path: Path) -> None:
    """渡した確かめの関数で、前の版の設定ファイルだけのフォルダにも鍵を取る（正常系）。"""
    # 準備
    (tmp_path / "mindmap.yaml").write_text("", encoding="utf-8")

    def _handler() -> dict[str, Any]:
        """何もせず空の辞書を返す。"""
        return {}

    # 実行
    result = server.call_tool(
        _handler,
        write_lock=threading.Lock(),
        lock_root=tmp_path,
        lock_require=migrator.require_migratable,
    )
    # 検証
    assert result.is_error is False
    assert (tmp_path / ".mindstella.lock").exists()


def test_ok_result() -> None:
    """日本語をエスケープしない本文と構造化の結果（正常系）。"""
    # 実行
    result = server.ok_result({"title": "問い"})
    # 検証
    assert result.structured_content == {"title": "問い"}
    assert _text_of(result) == json.dumps({"title": "問い"}, ensure_ascii=False)
    assert _text_of(result) == '{"title": "問い"}'


def test_error_result() -> None:
    """合わない箇所の行を続ける（正常系）。"""
    # 準備
    error = SchemaMismatchError(lines=["decisions.yaml: items[0].status: 理由"])
    # 実行
    result = server.error_result(error)
    # 検証
    assert result.is_error is True
    lines = _text_of(result).splitlines()
    assert lines[0].startswith("エラー: ")
    assert lines[1] == "decisions.yaml: items[0].status: 理由"


def test_error_result_when_legacy_format() -> None:
    """前の版の形式には /mindstella:upgrade を案内する（正常系）。"""
    # 準備
    error = SchemaMismatchError(lines=["docs.yaml: items[0]: done は使えません"], legacy=True)
    # 実行
    result = server.error_result(error)
    # 検証
    assert _text_of(result).splitlines()[-1] == store.LEGACY_HINT


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        pytest.param("ws", "/c/ws", id="relative"),
        pytest.param("~/ws", "/h/ws", id="home"),
        pytest.param("/abs/ws", "/abs/ws", id="absolute"),
    ],
)
def test_resolve_workspace(monkeypatch: pytest.MonkeyPatch, path: str, expected: str) -> None:
    """相対パスと ~ を絶対パスにする（正常系）。"""
    # 準備
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("/h")))
    monkeypatch.setenv("HOME", "/h")
    monkeypatch.setenv("USERPROFILE", "/h")
    # 実行
    result = server.resolve_workspace(path, Path("/c"))
    # 検証
    assert result == Path(expected)
