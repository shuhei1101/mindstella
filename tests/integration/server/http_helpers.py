"""配信への HTTP と Server-Sent Events のクライアント（結合テストの共通の関数）。"""

from __future__ import annotations

import http.client
import json
import queue
import socket
import threading
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

# 1 回の HTTP を待つ上限秒数
HTTP_TIMEOUT_SEC = 10

# 書き換えの知らせを待つ間に、ソケットを読み直す間隔の下限秒数
MIN_READ_TIMEOUT_SEC = 0.05


@dataclass(frozen=True)
class HttpResult:
    """HTTP の応答。ヘッダー名は小文字で引く。"""

    status: int
    headers: dict[str, str]
    text: str

    def json(self) -> dict[str, Any]:
        """本文を JSON のオブジェクトとして読む。"""
        return json.loads(self.text)


def http_request(
    base_url: str,
    path: str = "/",
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: str | bytes | None = None,
) -> HttpResult:
    """配信の URL にパスを足して 1 回つなぐ。Host を headers で渡すと、その値を付けてつなぐ。body の bytes はそのまま送る。"""
    parts = urlsplit(base_url)
    connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=HTTP_TIMEOUT_SEC)
    try:
        connection.request(
            method,
            path,
            body=body.encode("utf-8") if isinstance(body, str) else body,
            headers=headers or {},
        )
        response = connection.getresponse()
        text = response.read().decode("utf-8")
        return HttpResult(
            status=response.status,
            headers={name.lower(): value for name, value in response.getheaders()},
            text=text,
        )
    finally:
        connection.close()


def post_json(
    base_url: str,
    path: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
) -> HttpResult:
    """JSON のオブジェクトを `application/json` で POST する。"""
    return http_request(
        base_url,
        path,
        method="POST",
        headers={"Content-Type": "application/json", **(headers or {})},
        body=json.dumps(payload, ensure_ascii=False),
    )


def send_json(
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
) -> HttpResult:
    """JSON のオブジェクトを `application/json` で、渡したメソッド（PUT・PATCH など）で送る。"""
    return http_request(
        base_url,
        path,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
        body=json.dumps(payload, ensure_ascii=False),
    )


class EventStream:
    """書き換えの知らせ（`/api/events`）につなぎ、`event: changed` が届くのを待つ。"""

    def __init__(self, base_url: str) -> None:
        """つないでリクエストを送り、ステータスとヘッダーを読んで控える（本文は読み進めない）。"""
        parts = urlsplit(base_url)
        assert parts.hostname is not None
        assert parts.port is not None
        self._socket = socket.create_connection(
            (parts.hostname, parts.port), timeout=HTTP_TIMEOUT_SEC
        )
        self._reader = self._socket.makefile("rb")
        request = f"GET /api/events HTTP/1.1\r\nHost: {parts.hostname}:{parts.port}\r\n\r\n"
        self._socket.sendall(request.encode("ascii"))
        status_line = self._reader.readline().decode("ascii")
        self.status = int(status_line.split()[1])
        self.headers: dict[str, str] = {}
        while True:
            line = self._reader.readline().decode("ascii").strip()
            if not line:
                break
            name, _, value = line.partition(":")
            self.headers[name.lower()] = value.strip()
        # collect が読み始めてから溜める行（読み始める前は None）
        self._lines: queue.Queue[str] | None = None

    def wait_for_changed(self, timeout: float) -> bool:
        """`event: changed` が timeout 秒以内に届けば真、届かなければ偽を返す。"""
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            self._socket.settimeout(max(remaining, MIN_READ_TIMEOUT_SEC))
            try:
                line = self._reader.readline()
            except TimeoutError:
                return False
            if not line:
                return False
            if line.startswith(b"event: changed"):
                return True

    def collect(self, timeout: float) -> list[tuple[str, str]]:
        """timeout 秒の間に届いた知らせを、（`event` の名前・`data` の文字列）の並びで返す。

        行は別のスレッドで読み続けて溜め（読み取りを時間切れで止めると、その後に読めなくなるため）、
        前回の呼び出しより後に届いた分を返す。
        """
        if self._lines is None:
            self._lines = queue.Queue()
            self._socket.settimeout(None)
            threading.Thread(target=self._read_lines, daemon=True).start()
        events: list[tuple[str, str]] = []
        name = ""
        deadline = time.monotonic() + timeout
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                line = self._lines.get(timeout=remaining)
            except queue.Empty:
                break
            # 名前の行: 次の data の行と組にする
            if line.startswith("event: "):
                name = line.removeprefix("event: ")
            # data の行: 直前の名前と組にして残す
            elif line.startswith("data: ") and name:
                events.append((name, line.removeprefix("data: ")))
                name = ""
        return events

    def _read_lines(self) -> None:
        """つなぎが閉じるまで行を読み、溜める。"""
        assert self._lines is not None
        try:
            for raw in self._reader:
                self._lines.put(raw.decode("utf-8").rstrip("\r\n"))
        except (OSError, ValueError):
            return

    def close(self) -> None:
        """つなぎを閉じる。"""
        self._reader.close()
        self._socket.close()
