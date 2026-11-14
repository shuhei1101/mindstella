"""project_index.py（project-index の端末の設定の API と読み取り API の呼び出し）の単体テスト。"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

import project_index
from project_index import ProjectIndexError

# 1 つの要求への応答（ステータスと JSON の本文）
Reply = tuple[int, dict[str, Any]]


class FakeProjectIndex:
    """受けた要求を記録し、メソッドとパスごとに決めた応答を順に返す HTTP のサーバー。"""

    def __init__(self, replies: dict[tuple[str, str], list[Reply]]) -> None:
        """応答の並びを持ち、空きポートで待ち受ける。"""
        self.replies = replies
        self.requests: list[tuple[str, str, Any]] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            """決めた応答を返す。"""

            def _reply(self) -> None:
                """本文を読んで記録し、応答を返す。"""
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                body = json.loads(raw) if raw else None
                fake.requests.append((self.command, self.path, body))
                queue = fake.replies.get((self.command, self.path.split("?")[0])) or [(404, {})]
                status, payload = queue.pop(0) if len(queue) > 1 else queue[0]
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = do_PATCH = _reply

            def log_message(self, *args: object) -> None:
                """記録を出さない。"""

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        """待ち受けを閉じる。"""
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def fake_pi() -> Iterator[Callable[[dict[tuple[str, str], list[Reply]]], FakeProjectIndex]]:
    """応答を決めた偽の project-index を作る関数を返し、テストの後に閉じる。"""
    servers: list[FakeProjectIndex] = []

    def make(replies: dict[tuple[str, str], list[Reply]]) -> FakeProjectIndex:
        """偽の project-index を立てる。"""
        server = FakeProjectIndex(replies)
        servers.append(server)
        return server

    yield make
    for server in servers:
        server.close()


def _unused_port() -> int:
    """待ち受けていないポートを返す。"""
    server = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    port = server.server_address[1]
    server.server_close()
    return port


def test_get_settings(fake_pi: Callable[..., FakeProjectIndex]) -> None:
    """応答の JSON をそのまま返す。"""
    payload = {"settingsPath": "/s.yaml", "sources": [], "version": "v1"}
    server = fake_pi({("GET", "/settings/sources"): [(200, payload)]})
    assert project_index.get_settings(server.port) == payload


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        pytest.param((201, {"result": "added"}), "added", id="added"),
        pytest.param((409, {"result": "exists", "same": True}), "exists_same", id="same"),
        pytest.param(
            (409, {"result": "exists", "same": False}), "exists_different", id="different"
        ),
    ],
)
def test_add_source(reply: Reply, expected: str, fake_pi: Callable[..., FakeProjectIndex]) -> None:
    """201 と 409 の same で結果を分け、本文を {source: row} で送る。"""
    server = fake_pi({("POST", "/settings/sources"): [reply]})
    row = {"id": "w", "config": "/w/.mindstella/dev-docs.yaml"}
    assert project_index.add_source(server.port, row) == expected
    assert server.requests[-1][2] == {"source": row}


def test_add_source_error(fake_pi: Callable[..., FakeProjectIndex]) -> None:
    """422・500 と、待ち受けていないポートは ProjectIndexError を送る。"""
    for status in (422, 500):
        server = fake_pi({("POST", "/settings/sources"): [(status, {"detail": "x"})]})
        with pytest.raises(ProjectIndexError) as caught:
            project_index.add_source(server.port, {"id": "w"})
        assert caught.value.status == status
    with pytest.raises(ProjectIndexError) as caught:
        project_index.add_source(_unused_port(), {"id": "w"})
    assert caught.value.status is None


def test_patch_source(fake_pi: Callable[..., FakeProjectIndex]) -> None:
    """版を付けて送り、409 なら 1 回だけ版を引き直して送り直す。"""
    server = fake_pi(
        {
            ("GET", "/settings/sources"): [(200, {"version": "v1"}), (200, {"version": "v2"})],
            ("PATCH", "/settings/sources/w"): [(409, {"current": "v2"}), (200, {"version": "v3"})],
        }
    )
    project_index.patch_source(server.port, "w", {"outside_read": False})
    patches = [body for method, _path, body in server.requests if method == "PATCH"]
    assert patches == [
        {"expectedVersion": "v1", "source": {"outside_read": False}},
        {"expectedVersion": "v2", "source": {"outside_read": False}},
    ]


def test_patch_source_conflict_twice(fake_pi: Callable[..., FakeProjectIndex]) -> None:
    """2 回続けて 409 なら status が 409 の ProjectIndexError を送る。"""
    server = fake_pi(
        {
            ("GET", "/settings/sources"): [(200, {"version": "v1"})],
            ("PATCH", "/settings/sources/w"): [(409, {})],
        }
    )
    with pytest.raises(ProjectIndexError) as caught:
        project_index.patch_source(server.port, "w", {"outside_read": False})
    assert caught.value.status == 409


@pytest.mark.parametrize(
    ("docs", "expected"),
    [
        pytest.param([{"id": "flow-1", "path": "docs/flow.yaml"}], "docs/flow.yaml", id="found"),
        pytest.param([{"id": "other", "path": "docs/o.yaml"}], None, id="missing"),
    ],
)
def test_find_doc_path(
    docs: list[dict[str, str]], expected: str | None, fake_pi: Callable[..., FakeProjectIndex]
) -> None:
    """一覧から文書の ID でパスを引く。"""
    server = fake_pi({("GET", "/sources/aituber/docs"): [(200, {"docs": docs})]})
    assert project_index.find_doc_path(server.port, "aituber", "flow-1") == expected


@pytest.mark.parametrize(
    ("status", "expected"), [pytest.param(200, True, id="200"), pytest.param(404, False, id="404")]
)
def test_doc_exists(status: int, expected: bool, fake_pi: Callable[..., FakeProjectIndex]) -> None:
    """200 は真、404 は偽を返す。"""
    server = fake_pi({("GET", "/sources/aituber/docs/docs/flow.yaml"): [(status, {})]})
    assert project_index.doc_exists(server.port, "aituber", "docs/flow.yaml", "flow-1") is expected


@pytest.mark.parametrize(
    ("patterns", "folder", "expected"),
    [
        pytest.param(["/a/**"], "/a/b", True, id="glob"),
        pytest.param(["/a"], "/a", True, id="exact"),
        pytest.param(["/a"], "/a/b", False, id="exact-child"),
        pytest.param([], "/a", False, id="empty"),
    ],
)
def test_scope_includes(patterns: list[str], folder: str, expected: bool) -> None:
    """/** はその下に、/** の無いパスはそのフォルダだけに当たる。"""
    assert project_index.scope_includes(patterns, Path(folder)) is expected


def test_read_allowed_dirs(tmp_path: Path) -> None:
    """キーがあれば絶対パスの並び、キーもファイルも無ければ空の並びを返す。"""
    settings = tmp_path / "settings.yaml"
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    settings.write_text(
        f"mindstella:\n  allowed_dirs:\n    - {allowed}\nsources: []\n", encoding="utf-8"
    )
    assert project_index.read_allowed_dirs(settings) == [allowed.resolve()]
    settings.write_text("sources: []\n", encoding="utf-8")
    assert project_index.read_allowed_dirs(settings) == []
    assert project_index.read_allowed_dirs(tmp_path / "none.yaml") == []
