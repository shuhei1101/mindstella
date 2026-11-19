"""ワークスペースの設定の mdmark のバージョンを、画面が読み込む jsDelivr の ref に解決する。

`latest`（と未設定）は GitHub に mdmark の develop の先頭の commit の SHA を問い合わせ、jsDelivr がその配布物を配ることを
確かめてから、常駐サーバーの中で保持する。
"""

from __future__ import annotations

import http.client
import logging
import re
import threading
import time
from collections.abc import Callable
from http import HTTPStatus
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

# 問い合わせる GitHub の API の基点（問い合わせるたびに読む。結合テストは偽のサーバーに差し替える）
GITHUB_API_BASE_URL = "https://api.github.com"

# 問い合わせる mdmark のリポジトリ（`{owner}/{repo}`）
MDMARK_REPO = "shuhei1101/mdmark"

# 設定の `mdmark.version` のうち、develop の先頭の commit に解決する値
MDMARK_LATEST = "latest"

# 先頭の commit を問い合わせるブランチ。問い合わせられず、前に問い合わせた SHA も無いときの ref にもする
MDMARK_LATEST_BRANCH = "develop"

# 問い合わせた SHA と、問い合わせられなかったことを保持し、その間は問い合わせない秒数（認証なしの上限 60 回/時 ÷ 2 × 0.8）
REF_HOLD_SEC = 150

# 1 回の問い合わせで接続を待つ秒数（1,000 回の実測の接続の p99.9 7.10 秒 + 余裕 50%）
CONNECT_TIMEOUT_SEC = 11

# 接続した後、応答を読み終えるまでの 1 回の読み取りを待つ秒数（実測の読み取りの p99.9 1.17 秒 + 余裕 50%）
READ_TIMEOUT_SEC = 2

# 応答の本文が commit の SHA かを確かめる正規表現
COMMIT_SHA = re.compile(r"[0-9a-f]{40}")

# 問い合わせた SHA の配布物を jsDelivr が配るかを確認する基点（確認するたびに読む。結合テストは偽のサーバーに差し替える）
JSDELIVR_BASE_URL = "https://cdn.jsdelivr.net"

# jsDelivr の確認で接続を待つ秒数（Range の GET を 1,000 回測った接続の p99.9 0.038 秒 + 余裕 50% を秒に切り上げ）
DIST_CONNECT_TIMEOUT_SEC = 1

# jsDelivr の確認で、接続した後に応答の頭を読み終えるまでを待つ秒数（同じ実測の読み取りの p99.9 1.30 秒 + 余裕 50%）
DIST_READ_TIMEOUT_SEC = 2

# jsDelivr が配布物を配っていることを示すステータス
_SERVED_STATUSES = (HTTPStatus.OK, HTTPStatus.PARTIAL_CONTENT)

# 上限を超えたことを示すステータス
_RATE_LIMITED_STATUSES = (HTTPStatus.FORBIDDEN, HTTPStatus.TOO_MANY_REQUESTS)

# 例外のメッセージの頭
_LOOKUP_FAILED = "mdmark の develop の commit を問い合わせられません"


class RefLookupError(Exception):
    """GitHub に develop の先頭の commit を問い合わせられなかった。"""

    def __init__(self, reason: str, *, retry_at: float | None) -> None:
        super().__init__(f"{_LOOKUP_FAILED}: {reason}")
        # 問い合わせられなかった理由（標準エラーの 1 行に使う）
        self.reason = reason
        # 上限を超えた応答が示した、問い合わせ直せる時刻（UNIX 時刻の秒）。示さないときは None
        self.retry_at = retry_at


class MdmarkRefResolver:
    """設定の mdmark のバージョンを ref に解決し、`latest` の問い合わせの結果を `REF_HOLD_SEC` 保持する。

    配信の要求ごとのスレッドから呼ばれるので、問い合わせと保持をロックで守る。
    """

    def __init__(
        self,
        *,
        fetch: Callable[[], str] | None = None,
        check: Callable[[str], None] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        wall: Callable[[], float] = time.time,
    ) -> None:
        self._fetch = fetch_head_sha if fetch is None else fetch
        self._check = check_dist_served if check is None else check
        self._monotonic = monotonic
        self._wall = wall
        # 前に問い合わせた SHA
        self._held_ref: str | None = None
        # 保持の期限（monotonic の値）。この時刻より前は問い合わせない
        self._held_until = 0.0
        self._lock = threading.Lock()

    def resolve(self, version: str | None) -> str:
        """設定の mdmark のバージョンを ref にする。"""
        # タグを指定している: 問い合わせずにそのまま使う
        if version is not None and version != MDMARK_LATEST:
            return version
        with self._lock:
            now = self._monotonic()
            # 保持している間: 前の結果（問い合わせられなかったときは前の SHA か develop）を返す
            if now < self._held_until:
                return self._held_ref or MDMARK_LATEST_BRANCH
            try:
                sha = self._fetch()
                # 保持している SHA と違う: jsDelivr が配ることを確かめてから切り替える
                if sha != self._held_ref:
                    self._check(sha)
            except RefLookupError as error:
                # 問い合わせられない: 失敗も保持し、上限を超えた応答が示した時刻が遅ければその時刻まで問い合わせない
                logger.warning(
                    "mdmark の ref を問い合わせられないため %s を使います: %s",
                    self._held_ref or MDMARK_LATEST_BRANCH,
                    error.reason,
                )
                held_until = now + REF_HOLD_SEC
                if error.retry_at is not None:
                    held_until = max(held_until, now + (error.retry_at - self._wall()))
                self._held_until = held_until
                return self._held_ref or MDMARK_LATEST_BRANCH
            self._held_ref = sha
            self._held_until = now + REF_HOLD_SEC
            return sha


def _connect(base_url: str, connect_timeout: float, read_timeout: float) -> tuple[
    http.client.HTTPConnection, str
]:
    """基点の URL に接続し、読み取りの待ちを短くした接続と、基点のパス（末尾の `/` を除く）を返す。"""
    parts = urlsplit(base_url)
    connection_class = (
        http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    )
    connection = connection_class(parts.netloc, timeout=connect_timeout)
    try:
        connection.connect()
    except BaseException:
        connection.close()
        raise
    if connection.sock is not None:
        connection.sock.settimeout(read_timeout)
    return connection, parts.path.rstrip("/")


def fetch_head_sha() -> str:
    """GitHub の `GET /repos/{MDMARK_REPO}/commits/{MDMARK_LATEST_BRANCH}` で develop の先頭の commit の SHA を返す。"""
    connection: http.client.HTTPConnection | None = None
    try:
        connection, base_path = _connect(GITHUB_API_BASE_URL, CONNECT_TIMEOUT_SEC, READ_TIMEOUT_SEC)
        connection.request(
            "GET",
            f"{base_path}/repos/{MDMARK_REPO}/commits/{MDMARK_LATEST_BRANCH}",
            headers={"Accept": "application/vnd.github.sha", "User-Agent": "mindstella"},
        )
        response = connection.getresponse()
        body = response.read().decode("utf-8", errors="replace").strip()
        # 上限を超えた: 問い合わせ直せる時刻を添える
        if response.status in _RATE_LIMITED_STATUSES:
            raise RefLookupError(
                f"HTTP {response.status}",
                retry_at=_retry_at(
                    response.getheader("Retry-After"), response.getheader("X-RateLimit-Reset")
                ),
            )
        # 200 以外・SHA の形でない本文: 問い合わせられないとする
        if response.status != HTTPStatus.OK:
            raise RefLookupError(f"HTTP {response.status}", retry_at=None)
        if COMMIT_SHA.fullmatch(body) is None:
            raise RefLookupError(f"SHA ではない本文: {body[:40]}", retry_at=None)
        return body
    except (OSError, http.client.HTTPException) as error:
        raise RefLookupError(f"{type(error).__name__}: {error}", retry_at=None) from error
    finally:
        if connection is not None:
            connection.close()


def check_dist_served(ref: str) -> None:
    """jsDelivr が `ref` の mdmark の `dist/index.js` を配るかを、`Range: bytes=0-0` の GET で確かめる。

    200 か 206 でなければ `RefLookupError` を送る。応答の頭だけを読み、本文は読まない。
    """
    connection: http.client.HTTPConnection | None = None
    try:
        connection, base_path = _connect(
            JSDELIVR_BASE_URL, DIST_CONNECT_TIMEOUT_SEC, DIST_READ_TIMEOUT_SEC
        )
        connection.request(
            "GET",
            f"{base_path}/gh/{MDMARK_REPO}@{ref}/dist/index.js",
            headers={"Range": "bytes=0-0", "User-Agent": "mindstella"},
        )
        status = connection.getresponse().status
        # 200・206 以外: jsDelivr がまだ配らないとする
        if status not in _SERVED_STATUSES:
            raise RefLookupError(f"jsDelivr が配らない: HTTP {status}", retry_at=None)
    except (OSError, http.client.HTTPException) as error:
        raise RefLookupError(f"{type(error).__name__}: {error}", retry_at=None) from error
    finally:
        if connection is not None:
            connection.close()


def _retry_at(retry_after: str | None, rate_limit_reset: str | None) -> float | None:
    """`Retry-After`（秒）か `X-RateLimit-Reset`（UNIX 時刻）から、問い合わせ直せる時刻を返す。"""
    # Retry-After が秒: いまからその秒後
    if retry_after is not None and retry_after.strip().isdigit():
        return time.time() + int(retry_after.strip())
    # X-RateLimit-Reset がある: その UNIX 時刻
    if rate_limit_reset is not None and rate_limit_reset.strip().isdigit():
        return float(rate_limit_reset.strip())
    return None


# 常駐サーバーに 1 つの解決器（初めて呼ばれたときに作る）
_resolver: MdmarkRefResolver | None = None
_resolver_lock = threading.Lock()


def resolve_ref(version: str | None) -> str:
    """常駐サーバーに 1 つの解決器で、設定の mdmark のバージョンを ref にする（配信と配る書き出しが同じ保持を使う）。"""
    global _resolver
    with _resolver_lock:
        # 解決器が無い: 作る時点のモジュールの fetch_head_sha・check_dist_served を指定して作る
        if _resolver is None:
            _resolver = MdmarkRefResolver(fetch=fetch_head_sha, check=check_dist_served)
        resolver = _resolver
    return resolver.resolve(version)
