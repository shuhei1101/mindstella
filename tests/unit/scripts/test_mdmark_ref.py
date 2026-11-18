"""mdmark_ref.py（mdmark のバージョンの ref への解決と GitHub への問い合わせ）の単体テスト。"""

from __future__ import annotations

import http.server
import logging
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

import pytest

import mdmark_ref
# 問い合わせは conftest の offline_mdmark_ref が差し替えるため、差し替える前の関数を取っておく
from mdmark_ref import MdmarkRefResolver, RefLookupError, fetch_head_sha

# 問い合わせが返す develop の先頭の commit の SHA
SHA_A = "0123456789abcdef0123456789abcdef01234567"
SHA_B = "89abcdef0123456789abcdef0123456789abcdef"


@dataclass
class FakeResponse:
    """偽の GitHub が返す応答。"""

    status: int
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class FakeGitHub:
    """立てた偽の GitHub の基点の URL と、受けた要求の記録。"""

    base_url: str
    paths: list[str] = field(default_factory=list)
    accepts: list[str | None] = field(default_factory=list)


# 偽の GitHub を立てる関数（応答を受け、基点の URL と記録を返す）
StartFakeGitHub = Callable[[FakeResponse], FakeGitHub]


@pytest.fixture
def start_fake_github(monkeypatch: pytest.MonkeyPatch) -> Iterator[StartFakeGitHub]:
    """渡した応答を返す偽の GitHub を 127.0.0.1 の空きポートで立て、`GITHUB_API_BASE_URL` を向ける。"""
    # 環境のプロキシを通さずに、手元のサーバーへ届かせる
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    servers: list[tuple[http.server.ThreadingHTTPServer, threading.Thread]] = []

    def _start(response: FakeResponse) -> FakeGitHub:
        record = FakeGitHub(base_url="")

        class _Handler(http.server.BaseHTTPRequestHandler):
            """どの GET にも渡した応答を返し、パスと Accept を記録する。"""

            def do_GET(self) -> None:
                record.paths.append(self.path)
                record.accepts.append(self.headers.get("Accept"))
                self.send_response(response.status)
                for name, value in response.headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(response.body)))
                self.end_headers()
                self.wfile.write(response.body)

            def log_message(self, format: str, *args: object) -> None:  # noqa: A002
                """テストの出力に要求の記録を出さない。"""

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append((server, thread))
        record.base_url = f"http://127.0.0.1:{server.server_port}"
        monkeypatch.setattr(mdmark_ref, "GITHUB_API_BASE_URL", record.base_url)
        return record

    yield _start
    for server, thread in servers:
        server.shutdown()
        server.server_close()
        thread.join()


class Clock:
    """テストが進める時計（monotonic と wall の両方に使う）。"""

    def __init__(self, start: float) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


class CountingFetch:
    """呼ばれた数を数え、並べた結果を順に返す（例外は送る）問い合わせ。"""

    def __init__(self, results: list[str | RefLookupError]) -> None:
        self.results = results
        self.calls = 0

    def __call__(self) -> str:
        result = self.results[min(self.calls, len(self.results) - 1)]
        self.calls += 1
        if isinstance(result, RefLookupError):
            raise result
        return result


def test_resolve_tag() -> None:
    """タグは問い合わせずにそのまま返す（正常系）。"""
    # 準備
    fetch = CountingFetch([SHA_A])
    resolver = MdmarkRefResolver(fetch=fetch)
    # 実行
    ref = resolver.resolve("v0.13.0")
    # 検証
    assert ref == "v0.13.0"
    assert fetch.calls == 0


def test_resolve_latest_held() -> None:
    """latest と None は SHA にし、保持している間は問い合わせない（正常系）。"""
    # 準備
    fetch = CountingFetch([SHA_A, SHA_B])
    clock = Clock(1000.0)
    resolver = MdmarkRefResolver(fetch=fetch, monotonic=clock)
    # 実行
    first = resolver.resolve("latest")
    second = resolver.resolve(None)
    clock.now = 1149.0
    third = resolver.resolve("latest")
    calls_while_held = fetch.calls
    clock.now = 1150.0
    fourth = resolver.resolve("latest")
    # 検証
    assert (first, second, third) == (SHA_A, SHA_A, SHA_A)
    assert calls_while_held == 1
    assert fourth == SHA_B
    assert fetch.calls == 2


@pytest.mark.parametrize(
    ("results", "warmup_times", "fail_time", "expected"),
    [
        pytest.param(
            [RefLookupError("届かない", retry_at=None)], [], 1000.0, "develop", id="no_previous_sha"
        ),
        pytest.param(
            [SHA_A, RefLookupError("届かない", retry_at=None)],
            [1000.0],
            1150.0,
            SHA_A,
            id="previous_sha_expired",
        ),
    ],
)
def test_resolve_lookup_failed(
    results: list[str | RefLookupError],
    warmup_times: list[float],
    fail_time: float,
    expected: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """問い合わせられないときは前の SHA か develop を返し、失敗も保持する（異常系）。"""
    # 準備
    fetch = CountingFetch(results)
    clock = Clock(1000.0)
    resolver = MdmarkRefResolver(fetch=fetch, monotonic=clock)
    for warmup_time in warmup_times:
        clock.now = warmup_time
        resolver.resolve("latest")
    clock.now = fail_time
    caplog.set_level(logging.WARNING)
    # 実行
    failed = resolver.resolve("latest")
    right_after = resolver.resolve("latest")
    # 検証
    assert (failed, right_after) == (expected, expected)
    assert fetch.calls == len(results)
    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1


def test_resolve_retry_at() -> None:
    """上限を超えた応答が示した時刻が保持より遅ければ、その時刻まで問い合わせない（異常系）。"""
    # 準備
    monotonic = Clock(1000.0)
    wall = Clock(2_000_000_000.0)
    fetch = CountingFetch([RefLookupError("HTTP 403", retry_at=2_000_000_600.0), SHA_A])
    resolver = MdmarkRefResolver(fetch=fetch, monotonic=monotonic, wall=wall)
    resolver.resolve("latest")
    # 実行
    monotonic.now, wall.now = 1300.0, 2_000_000_300.0
    at_300 = resolver.resolve("latest")
    calls_at_300 = fetch.calls
    monotonic.now, wall.now = 1600.0, 2_000_000_600.0
    at_600 = resolver.resolve("latest")
    # 検証
    assert at_300 == "develop"
    assert calls_at_300 == 1
    assert at_600 == SHA_A
    assert fetch.calls == 2


def test_fetch_head_sha(start_fake_github: StartFakeGitHub) -> None:
    """200 の本文の SHA を返し、Accept と User-Agent を付ける（正常系）。"""
    # 準備
    github = start_fake_github(FakeResponse(200, f"{SHA_A}\n".encode()))
    # 実行
    sha = fetch_head_sha()
    # 検証
    assert sha == SHA_A
    assert github.paths == ["/repos/shuhei1101/mdmark/commits/develop"]
    assert github.accepts == ["application/vnd.github.sha"]


@pytest.mark.parametrize(
    ("response", "expected_retry_at"),
    [
        pytest.param(
            FakeResponse(403, b"", {"X-RateLimit-Reset": "2000000000"}),
            2_000_000_000.0,
            id="forbidden_reset",
        ),
        pytest.param(
            FakeResponse(429, b"", {"Retry-After": "60"}),
            1_700_000_060.0,
            id="too_many_retry_after",
        ),
    ],
)
def test_fetch_head_sha_rate_limited(
    start_fake_github: StartFakeGitHub,
    monkeypatch: pytest.MonkeyPatch,
    response: FakeResponse,
    expected_retry_at: float,
) -> None:
    """403 と X-RateLimit-Reset、429 と Retry-After は retry_at を持つ例外にする（異常系）。"""
    # 準備
    start_fake_github(response)
    monkeypatch.setattr(mdmark_ref.time, "time", lambda: 1_700_000_000.0)
    # 実行・検証
    with pytest.raises(RefLookupError, match="mdmark の develop の commit を問い合わせられません") as exc_info:
        fetch_head_sha()
    assert exc_info.value.retry_at == expected_retry_at


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(FakeResponse(500, b"error"), id="server_error"),
        pytest.param(FakeResponse(200, b"develop"), id="not_sha"),
    ],
)
def test_fetch_head_sha_invalid(
    start_fake_github: StartFakeGitHub, response: FakeResponse
) -> None:
    """500・SHA の形でない本文は retry_at の無い例外にする（異常系）。"""
    # 準備
    start_fake_github(response)
    # 実行・検証
    with pytest.raises(RefLookupError, match="mdmark の develop の commit を問い合わせられません") as exc_info:
        fetch_head_sha()
    assert exc_info.value.retry_at is None


def test_fetch_head_sha_invalid_when_unreachable(
    free_port: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """誰も待ち受けないポートへは retry_at の無い例外にする（異常系）。"""
    # 準備
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    monkeypatch.setattr(mdmark_ref, "GITHUB_API_BASE_URL", f"http://127.0.0.1:{free_port}")
    # 実行・検証
    with pytest.raises(RefLookupError, match="mdmark の develop の commit を問い合わせられません") as exc_info:
        fetch_head_sha()
    assert exc_info.value.retry_at is None


def test_resolve_ref_shared(monkeypatch: pytest.MonkeyPatch) -> None:
    """2 回呼んでも同じ解決器の保持を使う（正常系）。"""
    # 準備
    fetch = CountingFetch([SHA_A, SHA_B])
    monkeypatch.setattr(mdmark_ref, "fetch_head_sha", fetch)
    monkeypatch.setattr(mdmark_ref, "_resolver", None)
    # 実行
    first = mdmark_ref.resolve_ref("latest")
    second = mdmark_ref.resolve_ref("latest")
    # 検証
    assert (first, second) == (SHA_A, SHA_A)
    assert fetch.calls == 1
