"""transcriber.py（文字起こしのインターフェース・失敗の種類・使えるかの確かめ）の単体テスト。"""

from __future__ import annotations

import pytest

import transcriber
from transcriber import (
    Availability,
    TranscriberStoppedError,
    TranscriberUnsupportedError,
)


class _FakeTranscriber:
    """presets() が決めた一覧を返すか、決めた例外を送る偽の実装。"""

    def __init__(self, presets: list[str] | None = None, error: Exception | None = None) -> None:
        self._presets = presets or []
        self._error = error

    def presets(self) -> list[str]:
        """決めた例外があれば送り、無ければ決めた一覧を返す。"""
        if self._error is not None:
            raise self._error
        return self._presets

    def transcribe(self, audio: bytes, content_type: str, *, preset: str | None) -> str:
        """このテストでは呼ばない。"""
        raise AssertionError("transcribe は呼ばれない")


def test_check_availability() -> None:
    """一覧が返れば使える（正常系）。"""
    # 準備
    fake = _FakeTranscriber(presets=["一般", "開発"])
    # 実行
    result = transcriber.check_availability(fake)
    # 検証
    assert result == Availability(available=True, reason=None, detail=None, presets=["一般", "開発"])


@pytest.mark.parametrize(
    ("fake", "reason", "detail"),
    [
        pytest.param(
            _FakeTranscriber(error=TranscriberStoppedError("refused")),
            "stopped",
            "文字起こしのサービスが起動していないため、音声で入力できません。",
            id="stopped",
        ),
        pytest.param(
            _FakeTranscriber(error=TranscriberUnsupportedError("404")),
            "unsupported",
            "文字起こしのサービスが音声の受け付けに対応していないため、音声で入力できません。",
            id="unsupported",
        ),
        pytest.param(
            None,
            "stopped",
            "文字起こしのサービスが起動していないため、音声で入力できません。",
            id="none",
        ),
    ],
)
def test_check_availability_when_unavailable(
    fake: _FakeTranscriber | None, reason: str, detail: str
) -> None:
    """届かない・対応していない・持たないは理由つきで使えない（正常系）。"""
    # 準備
    target = fake
    # 実行
    result = transcriber.check_availability(target)
    # 検証
    assert result == Availability(available=False, reason=reason, detail=detail, presets=[])
    assert transcriber.UNAVAILABLE_DETAILS[reason] == detail
