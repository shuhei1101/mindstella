"""mdmark の ref の解決が問い合わせる GitHub と jsDelivr の代わりの偽のサーバー（結合テストの共通の関数）。"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# 偽のサーバーの待ち受けのホスト
FAKE_HOST = "127.0.0.1"

# 偽の GitHub が返す mdmark の develop の先頭の commit の SHA
FAKE_HEAD_SHA = "0123456789abcdef0123456789abcdef01234567"

# 偽の GitHub が develop の先頭の commit を返すパス
HEAD_PATH = "/repos/shuhei1101/mdmark/commits/develop"


@dataclass
class FakeMdmarkSource:
    """GitHub か jsDelivr の代わりに、どの GET にも決めたステータスと本文を返し、受けたパスを数える偽のサーバー。"""

    # 返すステータス
    status: int
    # 返す本文
    body: bytes = b""
    # 受けた GET のパス
    paths: list[str] = field(default_factory=list)
    # 待ち受けの基点の URL（start の後に入る）
    base_url: str = ""
    _server: ThreadingHTTPServer | None = None
    _thread: threading.Thread | None = None

    def start(self) -> None:
        """127.0.0.1 の空きポートで待ち受ける。"""
        source = self

        class _Handler(BaseHTTPRequestHandler):
            """どの GET にも決めた応答を返し、パスを記録する。"""

            def do_GET(self) -> None:
                source.paths.append(self.path)
                self.send_response(source.status)
                self.send_header("Content-Length", str(len(source.body)))
                self.end_headers()
                self.wfile.write(source.body)

            def log_message(self, format: str, *args: object) -> None:
                """テストの出力に要求の記録を出さない。"""

        self._server = ThreadingHTTPServer((FAKE_HOST, 0), _Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.base_url = f"http://{FAKE_HOST}:{self._server.server_port}"

    def stop(self) -> None:
        """待ち受けを止める。"""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join()


def fake_github() -> FakeMdmarkSource:
    """develop の先頭の commit として FAKE_HEAD_SHA を返す偽の GitHub を返す（start の前）。"""
    return FakeMdmarkSource(status=HTTPStatus.OK, body=f"{FAKE_HEAD_SHA}\n".encode())


def fake_jsdelivr(status: int = HTTPStatus.PARTIAL_CONTENT) -> FakeMdmarkSource:
    """配布物の頭の 1 バイトに status を返す偽の jsDelivr を返す（start の前）。"""
    return FakeMdmarkSource(status=status, body=b"/")
