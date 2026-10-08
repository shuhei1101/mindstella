"""プレビューを外から見る設定の結合・E2E テストの共通の部品。

受け取った引数を記録するフックのコマンドと記録を読む関数、空きポート、外の入口（トンネル・リバースプロキシ）の代わりの転送。
"""

from __future__ import annotations

import http.client
import shlex
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import TracebackType
from typing import Self

# 記録を待つ上限秒数
HOOK_WAIT_SEC = 10

# 記録を読み直す間隔の秒数
HOOK_POLL_SEC = 0.05

# 記録が増えないことを確かめるために待つ秒数
HOOK_SETTLE_SEC = 0.5

# 受け取った引数（先頭の記録先を除く）を 1 行にして、記録先へ書き足す Python のコード
RECORD_CODE = (
    "import sys; "
    "open(sys.argv[1], 'a', encoding='utf-8').write(' '.join(sys.argv[2:]) + '\\n')"
)


def free_port() -> int:
    """127.0.0.1 の空きポートを 1 つ取って閉じ、その番号を返す。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def recording_hook(record: Path) -> str:
    """末尾に足された引数を 1 行ずつ record へ書き足すフックのコマンドを、環境変数に入れる形で返す。"""
    return " ".join(
        shlex.quote(part) for part in (sys.executable, "-c", RECORD_CODE, str(record))
    )


def read_hook_lines(record: Path, *, count: int = 1) -> list[str]:
    """record に count 行以上が書かれるのを待ち、書かれた行を返す。上限を過ぎても足りなければ今ある行を返す。"""
    deadline = time.monotonic() + HOOK_WAIT_SEC
    lines: list[str] = []
    while time.monotonic() < deadline:
        if record.exists():
            lines = record.read_text(encoding="utf-8").splitlines()
            if len(lines) >= count:
                break
        time.sleep(HOOK_POLL_SEC)
    return lines


def read_settled_hook_lines(record: Path, *, count: int = 1) -> list[str]:
    """count 行が書かれた後も少し待ち、増えていないことを含めた行を返す。"""
    read_hook_lines(record, count=count)
    time.sleep(HOOK_SETTLE_SEC)
    return record.read_text(encoding="utf-8").splitlines() if record.exists() else []


# 転送が配信へ渡さない、1 つの接続ごとの見出し（Host と Origin は付け替え、残りは転送の側で決め直す）
HOP_HEADERS = frozenset({"host", "origin", "connection", "keep-alive", "transfer-encoding"})

# 転送が配信の応答を読み進める 1 回の大きさ（バイト）
RELAY_CHUNK_BYTES = 8192

# 転送が配信の応答を待つ上限秒数
RELAY_TIMEOUT_SEC = 30


class ForwardProxy:
    """外の入口の代わりに、外のホスト名の Host と Origin を付けて、127.0.0.1 の配信のポートへ要求を渡す転送。

    ブラウザは転送の 127.0.0.1 のポートを開く。配信には、Host を外のホスト名、Origin（付いている要求だけ）を
    外のホスト名の https に付け替えた要求が届く。書き換えの知らせのように長く続く応答も、届いた順に返す。
    """

    def __init__(self, *, upstream_port: int, external_host: str) -> None:
        """配信のポートと、付ける外のホスト名を受け取り、転送を空きポートで立ち上げる。"""
        forwarder = self

        class Handler(BaseHTTPRequestHandler):
            """届いた要求を配信へ渡し、応答を返す。"""

            def _relay(self) -> None:
                """Host と Origin を付け替えた要求を配信へ渡し、応答を状態・見出し・本文の順に返す。"""
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else None
                headers = {
                    name: value
                    for name, value in self.headers.items()
                    if name.lower() not in HOP_HEADERS
                }
                headers["Host"] = forwarder.external_host
                # Origin は付いている要求だけ付け替える（付いていない要求には足さない）
                if self.headers.get("Origin") is not None:
                    headers["Origin"] = f"https://{forwarder.external_host}"
                upstream = http.client.HTTPConnection(
                    "127.0.0.1", forwarder.upstream_port, timeout=RELAY_TIMEOUT_SEC
                )
                try:
                    upstream.request(self.command, self.path, body=body, headers=headers)
                    response = upstream.getresponse()
                    self.send_response(response.status)
                    for name, value in response.getheaders():
                        if name.lower() not in HOP_HEADERS:
                            self.send_header(name, value)
                    # 長さを決めずに、配信が閉じるまで届いた順に返す
                    self.send_header("Connection", "close")
                    self.end_headers()
                    while chunk := response.read1(RELAY_CHUNK_BYTES):
                        self.wfile.write(chunk)
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    # 画面が閉じた
                    return
                finally:
                    upstream.close()

            do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _relay

            def log_message(self, format: str, *args: object) -> None:  # noqa: A002
                """転送の記録は出さない。"""

        self.upstream_port = upstream_port
        self.external_host = external_host
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._httpd.daemon_threads = True
        self.port: int = self._httpd.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """転送を止めて閉じる。"""
        self._httpd.shutdown()
        self._httpd.server_close()

    def __enter__(self) -> Self:
        """with 文に入る。"""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """with 文を出るときに止める。"""
        self.stop()
