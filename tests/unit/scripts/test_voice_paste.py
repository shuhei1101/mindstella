"""voice_paste.py（文字起こしのインターフェースの voice-paste の実装）の単体テスト。"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from email.message import Message
from typing import Any

import pytest

from transcriber import (
    TranscriberStoppedError,
    TranscriberUnsupportedError,
    TranscriptionFailedError,
    TranscriptionTimeoutError,
)
from voice_paste import VoicePasteTranscriber

# voice-paste の既定の待ち受け
BASE_URL = "http://127.0.0.1:47823"

# 依頼に渡す音声
AUDIO = b"\x1aE\xdf\xa3voice"


class _FakeResponse:
    """urllib の応答の代わり（with で使え、status と read を持つ）。"""

    def __init__(self, status: int, payload: Any) -> None:
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        """本文を返す。"""
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _FakeOpener:
    """決めた順に応答を返すか例外を送り、受けた要求と引数を控える偽の opener。"""

    def __init__(self, *outcomes: Any) -> None:
        self._outcomes = list(outcomes)
        self.requests: list[urllib.request.Request] = []
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> _FakeResponse:
        """次の結果を取り出し、例外なら送り、4xx・5xx なら HTTPError を送り、それ以外は応答を返す。"""
        self.calls.append((args, kwargs))
        request = args[0]
        self.requests.append(request)
        outcome = self._outcomes.pop(0)
        # 例外を決めた回: そのまま送る
        if isinstance(outcome, BaseException):
            raise outcome
        status, payload = outcome
        # 4xx・5xx: urllib と同じく HTTPError を送る
        if status >= 400:
            raise urllib.error.HTTPError(
                request.full_url,
                status,
                "error",
                Message(),
                io.BytesIO(json.dumps(payload).encode("utf-8")),
            )
        return _FakeResponse(status, payload)


class _StepClock:
    """呼ぶたびに決めた秒数だけ進む時計。"""

    def __init__(self, step: float) -> None:
        self._now = 0.0
        self._step = step

    def __call__(self) -> float:
        """今の時刻を返してから進める。"""
        current = self._now
        self._now += self._step
        return current


def _refused() -> urllib.error.URLError:
    """接続を断られたときの例外を作る。"""
    return urllib.error.URLError(ConnectionRefusedError())


def _make(opener: _FakeOpener, sleeps: list[float] | None = None, clock: Any = None) -> VoicePasteTranscriber:
    """偽の opener と、待った秒数を控える sleep と時計で実装を作る。"""
    recorded = [] if sleeps is None else sleeps
    return VoicePasteTranscriber(
        base_url=BASE_URL,
        opener=opener,
        sleep=recorded.append,
        clock=clock if clock is not None else _StepClock(0.0),
    )


def test_presets() -> None:
    """一覧を返す（正常系）。"""
    # 準備
    opener = _FakeOpener((200, {"presets": ["一般", "開発"], "active": "一般"}))
    target = _make(opener)
    # 実行
    result = target.presets()
    # 検証
    assert result == ["一般", "開発"]
    request = opener.requests[0]
    assert (request.get_method(), request.full_url) == ("GET", f"{BASE_URL}/web/glossary-presets")
    assert request.get_header("Origin") is None


@pytest.mark.parametrize(
    ("outcome", "error"),
    [
        pytest.param(_refused(), TranscriberStoppedError, id="refused"),
        pytest.param(TimeoutError(), TranscriberStoppedError, id="timeout"),
        pytest.param((404, {"detail": "Not Found"}), TranscriberUnsupportedError, id="not-found"),
        pytest.param((500, {"detail": "boom"}), TranscriberStoppedError, id="server-error"),
        pytest.param((200, {"presets": "一般"}), TranscriberStoppedError, id="broken"),
    ],
)
def test_presets_when_unavailable(outcome: Any, error: type[Exception]) -> None:
    """届かない・エンドポイントが無い・崩れた応答を分ける（異常系）。"""
    # 準備
    target = _make(_FakeOpener(outcome))
    # 実行・検証
    with pytest.raises(error):
        target.presets()


def test_transcribe() -> None:
    """依頼して終わるまで待ち、起こした文字を返す（正常系）。"""
    # 準備
    opener = _FakeOpener(
        (202, {"job_id": "j1"}),
        (200, {"state": "running", "progress": 0.5}),
        (200, {"state": "done", "progress": 1.0, "text": "案 A にする"}),
    )
    sleeps: list[float] = []
    target = _make(opener, sleeps)
    # 実行
    result = target.transcribe(AUDIO, "audio/webm;codecs=opus", preset="開発")
    # 検証
    assert result == "案 A にする"
    posted = opener.requests[0]
    assert (posted.get_method(), posted.full_url) == ("POST", f"{BASE_URL}/web/transcriptions")
    assert posted.get_header("Origin") is None
    body = posted.data
    assert isinstance(body, bytes)
    assert b'filename="audio.webm"' in body
    assert AUDIO in body
    assert b'name="glossary_preset"' in body
    assert "開発".encode() in body
    assert opener.requests[1].full_url == f"{BASE_URL}/web/transcriptions/j1"
    assert sleeps == [1.0, 1.0]


def test_transcribe_when_no_preset() -> None:
    """プリセットが無ければ付けない（正常系）。"""
    # 準備
    opener = _FakeOpener((202, {"job_id": "j1"}), (200, {"state": "done", "text": ""}))
    target = _make(opener)
    # 実行
    result = target.transcribe(AUDIO, "audio/webm", preset=None)
    # 検証
    assert result == ""
    body = opener.requests[0].data
    assert isinstance(body, bytes)
    assert b'name="glossary_preset"' not in body


def test_transcribe_when_poll_timed_out() -> None:
    """待つ間の 1 回の打ち切りでは待ちを続ける（正常系）。"""
    # 準備
    opener = _FakeOpener(
        (202, {"job_id": "j1"}), TimeoutError(), (200, {"state": "done", "text": "x"})
    )
    target = _make(opener)
    # 実行
    result = target.transcribe(AUDIO, "audio/webm", preset=None)
    # 検証
    assert result == "x"


@pytest.mark.parametrize(
    ("outcomes", "error", "message"),
    [
        pytest.param([_refused()], TranscriberStoppedError, "", id="post-refused"),
        pytest.param([(404, {"detail": "Not Found"})], TranscriberUnsupportedError, "", id="post-404"),
        pytest.param([(503, {"detail": "busy"})], TranscriptionFailedError, "busy", id="post-503"),
        pytest.param([(202, {})], TranscriptionFailedError, "", id="no-job-id"),
        pytest.param(
            [(202, {"job_id": "j1"}), (404, {"detail": "Not Found"})],
            TranscriptionFailedError,
            "",
            id="job-404",
        ),
        pytest.param(
            [(202, {"job_id": "j1"}), (200, {"state": "failed", "error": "decode"})],
            TranscriptionFailedError,
            "decode",
            id="failed",
        ),
        pytest.param(
            [(202, {"job_id": "j1"}), _refused()],
            TranscriberStoppedError,
            "",
            id="poll-refused",
        ),
    ],
)
def test_transcribe_when_rejected(
    outcomes: list[Any], error: type[Exception], message: str
) -> None:
    """依頼の失敗を種類に分ける（異常系）。"""
    # 準備
    target = _make(_FakeOpener(*outcomes))
    # 実行・検証
    with pytest.raises(error, match=message):
        target.transcribe(AUDIO, "audio/webm", preset=None)


def test_transcribe_when_stalled() -> None:
    """進まないまま待ちの上限を超えたら打ち切る（異常系）。"""
    # 準備
    running = (200, {"state": "running", "progress": 0.2})
    opener = _FakeOpener((202, {"job_id": "j1"}), running, running, running, running, running)
    target = _make(opener, clock=_StepClock(61.0))
    # 実行・検証
    with pytest.raises(TranscriptionTimeoutError):
        target.transcribe(AUDIO, "audio/webm", preset=None)


def test_transcribe_when_progressing() -> None:
    """進んでいる間は上限を超えても待つ（正常系）。"""
    # 準備
    opener = _FakeOpener(
        (202, {"job_id": "j1"}),
        (200, {"state": "running", "progress": 0.1}),
        (200, {"state": "running", "progress": 0.2}),
        (200, {"state": "running", "progress": 0.3}),
        (200, {"state": "done", "progress": 1.0, "text": "進んだ"}),
    )
    target = _make(opener, clock=_StepClock(61.0))
    # 実行
    result = target.transcribe(AUDIO, "audio/webm", preset=None)
    # 検証
    assert result == "進んだ"


def test_request() -> None:
    """待ちの上限をキーワードで渡し、本文を置き換えない（正常系）。"""
    # 準備
    opener = _FakeOpener((200, {}))
    target = _make(opener)
    # 実行
    target._request("POST", "/web/transcriptions", body=b"abc", content_type="text/plain")
    # 検証
    args, kwargs = opener.calls[0]
    assert len(args) == 1
    assert kwargs == {"timeout": 66.0}
    assert opener.requests[0].data == b"abc"


def test_request_when_http_error() -> None:
    """4xx・5xx もステータスと本文で返す（正常系）。"""
    # 準備
    target = _make(_FakeOpener((400, {"detail": "x"})))
    # 実行
    result = target._request("GET", "/web/glossary-presets")
    # 検証
    assert result == (400, {"detail": "x"})


@pytest.mark.parametrize(
    ("content_type", "preset", "filename", "has_preset"),
    [
        pytest.param("audio/webm;codecs=opus", "開発", b'filename="audio.webm"', True, id="webm"),
        pytest.param("audio/x-unknown", None, b'filename="audio.bin"', False, id="unknown"),
    ],
)
def test_multipart(content_type: str, preset: str | None, filename: bytes, has_preset: bool) -> None:
    """拡張子とプリセットの部分（正常系）。"""
    # 準備
    target = _make(_FakeOpener())
    # 実行
    body, multipart_type = target._multipart(AUDIO, content_type, preset=preset)
    # 検証
    assert multipart_type.startswith("multipart/form-data; boundary=")
    assert filename in body
    assert (b'name="glossary_preset"' in body) is has_preset
