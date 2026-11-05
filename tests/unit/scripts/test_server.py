"""server.py（MCP サーバーの組み立て・ツールの登録・結果とエラー）の単体テスト。"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import threading
from collections.abc import Callable, Coroutine, Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest
from mcp.types import CallToolResult, TextContent
from starlette.testclient import TestClient

import claude_input
import migrator
import serve
import server
import store
from errors import ArgumentError, SchemaMismatchError, WorkspaceNotFoundError
from fixture_types import MakeItem, MakeWorkspace

# build_server が登録するツールの名前（インターフェース定義『MCP サーバーの起動』）
EXPECTED_TOOL_NAMES = (
    "init",
    "add",
    "update",
    "remove",
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
    "readme",
    "threads",
    "thread",
    "new_thread",
    "reply",
    "set_thread_status",
    "update_thread",
    "server_status",
    "server_stop",
)

# workspace を受けない管理のツール
ADMIN_TOOL_NAMES = ("server_status", "server_stop")


class _FakeHttpServer:
    """run が呼ばれた引数を控えて、すぐ戻る偽の HTTP のサーバー（uvicorn.Server の代わり）。"""

    def __init__(self, *, on_run: Callable[[], None] | None = None) -> None:
        """終わり始めの印と、run の引数を控える入れ物を作る。"""
        self.should_exit = False
        self.socket_names: list[list[tuple[str, int]]] = []
        self._on_run = on_run

    def run(self, sockets: list[socket.socket] | None = None) -> None:
        """動かさずに、渡されたソケットの待ち受けの場所だけを控える。"""
        self.socket_names.append([sock.getsockname() for sock in sockets or []])
        if self._on_run is not None:
            self._on_run()


class _FakeMcpServer:
    """streamable_http_app の引数を控え、決めたアプリを返す偽の MCP サーバー。"""

    def __init__(self) -> None:
        """アプリの代わりの値と、受け取った引数を控える入れ物を作る。"""
        self.app = object()
        self.app_kwargs: list[dict[str, Any]] = []

    def streamable_http_app(self, **kwargs: Any) -> object:
        """受け取った引数を控えて、アプリの代わりを返す。"""
        self.app_kwargs.append(kwargs)
        return self.app


class _MainSpy:
    """main へ渡す build と make_server の代わりを作り、受け取った値を控える。"""

    def __init__(self, http_server: _FakeHttpServer) -> None:
        """make_server が返す偽の HTTP のサーバーを受け取る。"""
        self.http_server = http_server
        self.mcp_server = _FakeMcpServer()
        self.build_kwargs: dict[str, Any] = {}
        self.build_calls = 0
        self.make_server_calls = 0

    def build(self, **kwargs: Any) -> _FakeMcpServer:
        """渡された previews・status・request_stop を控えて、偽の MCP サーバーを返す。"""
        self.build_calls += 1
        self.build_kwargs.update(kwargs)
        return self.mcp_server

    def make_server(self, app: Any) -> _FakeHttpServer:
        """受け取ったアプリを確かめずに、偽の HTTP のサーバーを返す。"""
        self.make_server_calls += 1
        return self.http_server


class _RaisingHttpServer(_FakeHttpServer):
    """run が RuntimeError を送る偽の HTTP のサーバー。"""

    def run(self, sockets: list[socket.socket] | None = None) -> None:
        """ソケットを控えてから、例外で戻る。"""
        super().run(sockets)
        raise RuntimeError("サーバーが落ちました")


class _SessionRecorder:
    """remember_session に渡された値を控える偽の配信の台帳。"""

    def __init__(self) -> None:
        """渡された値を控える入れ物を作る。"""
        self.remembered: list[tuple[Path, claude_input.Session]] = []

    def remember_session(self, root: Path, session: claude_input.Session) -> None:
        """宛先を書き換えずに、渡されたワークスペースとセッションを控える。"""
        self.remembered.append((root, session))


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


@pytest.fixture
def registry() -> Iterator[serve.PreviewRegistry]:
    """配信の台帳を作り、使い終わったら立てた配信を全て止める。"""
    created = serve.PreviewRegistry(threading.Lock())
    yield created
    created.stop_all()


def _build(previews: Any, *, status: Callable[[], dict[str, Any]] | None = None) -> Any:
    """status と request_stop を何もしない関数にしてサーバーを組み立てる。"""
    return server.build_server(
        previews=previews,
        write_lock=threading.Lock(),
        status=(lambda: {}) if status is None else status,
        request_stop=lambda: None,
    )


def _session_of(cwd: Path) -> dict[str, str]:
    """作業フォルダが cwd の、tmux の外のセッションの値を返す。"""
    return {"cwd": str(cwd), "claude_config_dir": str(cwd / "cfg")}


def _listing_of(started: list[tuple[Path, str]]) -> list[dict[str, Any]]:
    """start したワークスペースと URL から、配信の一覧に出るはずの要素を返す。"""
    return [
        {"workspace": str(root.resolve()), "port": urlparse(url).port} for root, url in started
    ]


def test_main(monkeypatch: pytest.MonkeyPatch, free_port: int) -> None:
    """空きポートで動かし、戻ったら配信を止めて 0（正常系）。"""
    # 準備
    stopped = _spy_stop_all(monkeypatch)
    spy = _MainSpy(_FakeHttpServer())
    # 実行
    result = server.main(
        build=spy.build, make_server=spy.make_server, environ={"MINDSTELLA_PORT": str(free_port)}
    )
    # 検証
    assert result == 0
    assert spy.http_server.socket_names == [[("127.0.0.1", free_port)]]
    assert stopped == [spy.build_kwargs["previews"]]


def test_main_when_server_raises(monkeypatch: pytest.MonkeyPatch, free_port: int) -> None:
    """HTTP のサーバーが例外で戻っても配信を止める（正常系）。"""
    # 準備
    stopped = _spy_stop_all(monkeypatch)
    spy = _MainSpy(_RaisingHttpServer())
    # 実行・検証
    with pytest.raises(RuntimeError, match="サーバーが落ちました"):
        server.main(
            build=spy.build,
            make_server=spy.make_server,
            environ={"MINDSTELLA_PORT": str(free_port)},
        )
    assert stopped == [spy.build_kwargs["previews"]]


def test_main_when_external_access_set(monkeypatch: pytest.MonkeyPatch, free_port: int) -> None:
    """環境変数の外から見る設定を台帳へ渡す（正常系）。"""
    # 準備
    _spy_stop_all(monkeypatch)
    spy = _MainSpy(_FakeHttpServer())
    environ = {
        "MINDSTELLA_PORT": str(free_port),
        "MINDSTELLA_ALLOWED_HOSTS": "preview.example.test",
    }
    # 実行
    server.main(build=spy.build, make_server=spy.make_server, environ=environ)
    # 検証
    previews = spy.build_kwargs["previews"]
    assert previews._external.allowed_hosts == frozenset({"preview.example.test"})


def test_main_when_stop_requested(monkeypatch: pytest.MonkeyPatch, free_port: int) -> None:
    """request_stop で HTTP のサーバーを終わらせる（正常系）。"""
    # 準備（run の中で、build が受け取った request_stop を呼ぶ）
    _spy_stop_all(monkeypatch)
    received: dict[str, Any] = {}
    http_server = _FakeHttpServer(on_run=lambda: received["request_stop"]())
    spy = _MainSpy(http_server)

    def _build(**kwargs: Any) -> _FakeMcpServer:
        """request_stop を控えてから、偽の MCP サーバーを返す。"""
        received.update(kwargs)
        return spy.build(**kwargs)

    # 実行
    result = server.main(
        build=_build, make_server=spy.make_server, environ={"MINDSTELLA_PORT": str(free_port)}
    )
    # 検証
    assert http_server.should_exit is True
    assert result == 0


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("abc", id="not_integer"),
        pytest.param("0", id="zero"),
        pytest.param("70000", id="too_large"),
    ],
)
def test_main_when_port_invalid(caplog: pytest.LogCaptureFixture, value: str) -> None:
    """ポートの値が誤りなら待ち受けずに 1（異常系）。"""
    # 準備
    spy = _MainSpy(_FakeHttpServer())
    caplog.set_level(logging.ERROR)
    # 実行
    result = server.main(
        build=spy.build, make_server=spy.make_server, environ={"MINDSTELLA_PORT": value}
    )
    # 検証
    assert result == 1
    assert "ERROR" in caplog.text
    assert value in caplog.text
    assert spy.build_calls == 0
    assert spy.make_server_calls == 0


def test_main_when_port_in_use(caplog: pytest.LogCaptureFixture, listening_port: int) -> None:
    """ポートが使われていれば待ち受けずに 1（異常系）。"""
    # 準備
    spy = _MainSpy(_FakeHttpServer())
    caplog.set_level(logging.ERROR)
    # 実行
    result = server.main(
        build=spy.build,
        make_server=spy.make_server,
        environ={"MINDSTELLA_PORT": str(listening_port)},
    )
    # 検証
    assert result == 1
    assert "ERROR" in caplog.text
    assert str(listening_port) in caplog.text
    assert "MINDSTELLA_PORT" in caplog.text
    assert spy.build_calls == 0
    assert spy.make_server_calls == 0


@pytest.mark.parametrize(
    ("environ", "expected"),
    [
        pytest.param({}, 8784, id="unset"),
        pytest.param({"MINDSTELLA_PORT": ""}, 8784, id="empty"),
        pytest.param({"MINDSTELLA_PORT": "9000"}, 9000, id="set"),
    ],
)
def test_read_port(environ: dict[str, str], expected: int) -> None:
    """無ければ既定、あればその値（正常系）。"""
    # 実行
    result = server.read_port(environ)
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("abc", id="not_integer"),
        pytest.param("0", id="zero"),
        pytest.param("65536", id="too_large"),
        pytest.param("-1", id="negative"),
    ],
)
def test_read_port_when_invalid(value: str) -> None:
    """整数でないか範囲の外なら InvalidPortError（異常系）。"""
    # 実行・検証
    with pytest.raises(server.InvalidPortError) as raised:
        server.read_port({"MINDSTELLA_PORT": value})
    assert raised.value.value == value


def test_bind_socket(free_port: int) -> None:
    """127.0.0.1 の空きポートに bind する（正常系）。"""
    # 実行
    with server.bind_socket(free_port) as bound:
        # 検証
        assert bound.getsockname() == ("127.0.0.1", free_port)


def test_bind_socket_when_in_use(listening_port: int) -> None:
    """待ち受けているポートなら PortInUseError（異常系）。"""
    # 実行・検証
    with pytest.raises(server.PortInUseError) as raised:
        server.bind_socket(listening_port)
    assert raised.value.port == listening_port


def test_build_status(
    registry: serve.PreviewRegistry, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """台帳の配信を並べた状態（正常系）。"""
    # 準備
    second = make_workspace(make_item("D-1"), name="b")
    first = make_workspace(make_item("D-1"), name="a")
    second_url, _ = registry.start(second)
    first_url, _ = registry.start(first)
    # 実行
    result = server.build_status(
        registry,
        port=8784,
        started_at="2026-11-02T01:00:00+00:00",
        plugin_root=Path("/p"),
        version="v0.12.0",
    )
    # 検証
    assert result["name"] == "mindstella"
    assert result["pid"] == os.getpid()
    assert result["previews"] == _listing_of([(first, first_url), (second, second_url)])


def test_run_server_stop(
    registry: serve.PreviewRegistry, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """配信を返して止めるよう頼む（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), name="ws")
    url, _ = registry.start(root)
    requests: list[bool] = []
    # 実行
    result = server.run_server_stop(registry, request_stop=lambda: requests.append(True))
    # 検証
    assert result["stopping"] is True
    assert result["previews"] == _listing_of([(root, url)])
    assert requests == [True]


def _tool_schemas(tools: list[Any]) -> dict[str, dict[str, Any]]:
    """ツールの名前 → 入力のスキーマを返す。"""
    return {tool.name: tool.input_schema for tool in tools}


def _not_requiring(schemas: dict[str, dict[str, Any]], key: str) -> list[str]:
    """入力のスキーマの required に key を持たないツールの名前を返す。"""
    return [name for name, schema in schemas.items() if key not in schema.get("required", [])]


def _requiring(schemas: dict[str, dict[str, Any]], key: str) -> list[str]:
    """入力のスキーマの required に key を持つツールの名前を返す。"""
    return [name for name, schema in schemas.items() if key in schema.get("required", [])]


def _lacking_property(schemas: dict[str, dict[str, Any]], key: str) -> list[str]:
    """入力のスキーマの properties に key を持たないツールの名前を返す。"""
    return [name for name, schema in schemas.items() if key not in schema["properties"]]


def test_build_server() -> None:
    """管理のツールの他は全てのツールを workspace つきで登録する（正常系）。"""
    # 準備
    mcp_server = _build(serve.PreviewRegistry(threading.Lock()))
    # 実行
    tools = _run_async(mcp_server.list_tools())
    # 検証
    schemas = _tool_schemas(tools)
    assert tuple(schemas) == EXPECTED_TOOL_NAMES
    assert server.TOOL_NAMES == EXPECTED_TOOL_NAMES
    assert _not_requiring(schemas, "workspace") == list(ADMIN_TOOL_NAMES)
    assert _lacking_property(schemas, "session") == []
    assert _requiring(schemas, "session") == []


def test_build_server_when_relative_workspace(
    tmp_path: Path, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """相対パスの workspace をセッションの作業フォルダから読む（正常系）。"""
    # 準備
    make_workspace(make_item("D-1"), name="ws")
    mcp_server = _build(serve.PreviewRegistry(threading.Lock()))
    # 実行
    result = _run_async(
        mcp_server.call_tool("attrs", {"workspace": "ws", "session": _session_of(tmp_path)})
    )
    # 検証
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    assert result.structured_content == {"attrs": []}


def test_build_server_when_relative_without_session() -> None:
    """セッションが無い相対パスは引数の誤り（異常系）。"""
    # 準備
    mcp_server = _build(serve.PreviewRegistry(threading.Lock()))
    # 実行
    result = _run_async(mcp_server.call_tool("attrs", {"workspace": "ws"}))
    # 検証
    assert isinstance(result, CallToolResult)
    assert result.is_error is True
    assert _text_of(result).startswith("エラー: 引数の誤り: workspace:")


def test_build_server_when_session_given(
    tmp_path: Path, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """セッションを受けたらそのワークスペースの宛先を書き換える（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), name="ws")
    raw_session = {
        "cwd": str(tmp_path),
        "claude_config_dir": str(tmp_path / "cfg"),
        "tmux": "/s,1,0",
        "tmux_pane": "%3",
        "claude_pid": 40,
        "claude_started_at": "Mon Nov 2 10:00:00 2026",
    }
    previews = _SessionRecorder()
    mcp_server = _build(previews)
    # 実行
    _run_async(mcp_server.call_tool("attrs", {"workspace": str(root), "session": raw_session}))
    # 検証
    assert previews.remembered == [(root, claude_input.parse_session(raw_session))]


def test_build_server_when_status_route() -> None:
    """GET /_admin/status が status の結果を返す（正常系）。"""
    # 準備
    mcp_server = _build(
        serve.PreviewRegistry(threading.Lock()), status=lambda: {"name": "mindstella"}
    )
    # 実行
    with TestClient(mcp_server.streamable_http_app()) as client:
        response = client.get("/_admin/status")
    # 検証
    assert response.status_code == 200
    assert response.json() == {"name": "mindstella"}


@pytest.mark.parametrize(
    ("extra_arguments", "expected_text_head", "expected_first_id"),
    [
        pytest.param({}, "全 1 件・合計", None, id="markdown"),
        pytest.param({"format": "json"}, None, "D-1", id="json"),
    ],
)
def test_build_server_when_find_format(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    extra_arguments: dict[str, str],
    expected_text_head: str | None,
    expected_first_id: str | None,
) -> None:
    """find は既定で Markdown の本文、json で構造化の結果を返す（正常系）。"""
    # 準備
    make_workspace(make_item("D-1"), name="ws")
    mcp_server = _build(serve.PreviewRegistry(threading.Lock()))
    arguments = {"workspace": "ws", "session": _session_of(tmp_path), **extra_arguments}
    # 実行
    result = _run_async(mcp_server.call_tool("find", arguments))
    # 検証
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    assert _find_summary(result) == (expected_text_head, expected_first_id)


def _find_summary(result: CallToolResult) -> tuple[str | None, str | None]:
    """find の結果を（Markdown の本文の先頭 7 文字、構造化の結果の最初の ID）にする。持たない方は None。"""
    # 構造化の結果が無い: Markdown の本文だけを返した
    if result.structured_content is None:
        return _text_of(result)[: len("全 1 件・合計")], None
    # 構造化の結果がある: JSON で返した
    return None, result.structured_content["items"][0]["id"]


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


def test_call_tool_when_render() -> None:
    """render を渡すと本文だけの結果にする（正常系）。"""
    # 実行
    result = server.call_tool(
        lambda: {"total": 1},
        write_lock=threading.Lock(),
        render=lambda payload: f"全 {payload['total']} 件",
    )
    # 検証
    assert result.is_error is False
    assert _text_of(result) == "全 1 件"
    assert result.structured_content is None


def test_ok_result() -> None:
    """日本語をエスケープしない本文と構造化の結果（正常系）。"""
    # 実行
    result = server.ok_result({"title": "問い"})
    # 検証
    assert result.structured_content == {"title": "問い"}
    assert _text_of(result) == json.dumps({"title": "問い"}, ensure_ascii=False)
    assert _text_of(result) == '{"title": "問い"}'


def test_text_result() -> None:
    """本文だけを持つ（正常系）。"""
    # 実行
    result = server.text_result("全 2 件・合計 300 文字")
    # 検証
    assert _text_of(result) == "全 2 件・合計 300 文字"
    assert result.structured_content is None
    assert result.is_error is False


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
    session = claude_input.Session(cwd=Path("/c"), claude_config_dir=Path("/cfg"))
    # 実行
    result = server.resolve_workspace(path, session)
    # 検証
    assert result == Path(expected)


def _resolve_or_message(path: str) -> str:
    """セッション無しで絶対パスにした結果か、送られた ArgumentError のメッセージを返す。"""
    try:
        return str(server.resolve_workspace(path, None))
    except ArgumentError as error:
        # 相対パス: 引数の誤りのメッセージ
        return str(error)


@pytest.mark.parametrize(
    ("path", "expected_head"),
    [
        pytest.param("ws", "引数の誤り: workspace:", id="relative"),
        pytest.param("/abs/ws", "/abs/ws", id="absolute"),
    ],
)
def test_resolve_workspace_when_no_session(path: str, expected_head: str) -> None:
    """セッションが無ければ相対パスだけ誤り（異常系）。"""
    # 実行
    result = _resolve_or_message(path)
    # 検証
    assert result.startswith(expected_head)
