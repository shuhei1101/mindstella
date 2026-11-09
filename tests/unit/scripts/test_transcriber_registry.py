"""transcriber_registry.py（環境変数で文字起こしの実装を選ぶ引き当て）の単体テスト。"""

from __future__ import annotations

import pytest

import transcriber_registry
from transcriber_registry import InvalidTranscriberError
from voice_paste import VoicePasteTranscriber


@pytest.mark.parametrize(
    ("environ", "base_url"),
    [
        pytest.param({}, "http://127.0.0.1:47823", id="default"),
        pytest.param(
            {
                "MINDSTELLA_TRANSCRIBER": " voice-paste ",
                "MINDSTELLA_TRANSCRIBER_URL": "http://localhost:50000/",
            },
            "http://localhost:50000",
            id="given",
        ),
    ],
)
def test_load_transcriber(environ: dict[str, str], base_url: str) -> None:
    """既定と渡した値で voice-paste の実装を作る（正常系）。"""
    # 準備
    source = environ
    # 実行
    result = transcriber_registry.load_transcriber(source)
    # 検証
    assert isinstance(result, VoicePasteTranscriber)
    assert result.base_url == base_url


@pytest.mark.parametrize(
    ("environ", "key", "value"),
    [
        pytest.param(
            {"MINDSTELLA_TRANSCRIBER": "whisper"}, "MINDSTELLA_TRANSCRIBER", "whisper", id="name"
        ),
        pytest.param(
            {"MINDSTELLA_TRANSCRIBER_URL": "https://127.0.0.1:47823"},
            "MINDSTELLA_TRANSCRIBER_URL",
            "https://127.0.0.1:47823",
            id="https",
        ),
        pytest.param(
            {"MINDSTELLA_TRANSCRIBER_URL": "http://192.168.0.2:47823"},
            "MINDSTELLA_TRANSCRIBER_URL",
            "http://192.168.0.2:47823",
            id="other-host",
        ),
        pytest.param(
            {"MINDSTELLA_TRANSCRIBER_URL": "http://127.0.0.1:0"},
            "MINDSTELLA_TRANSCRIBER_URL",
            "http://127.0.0.1:0",
            id="port-zero",
        ),
    ],
)
def test_load_transcriber_when_invalid(environ: dict[str, str], key: str, value: str) -> None:
    """無い実装と許さない URL は起動させない（異常系）。"""
    # 実行・検証
    with pytest.raises(InvalidTranscriberError, match=f"{key} の値が誤りです") as caught:
        transcriber_registry.load_transcriber(environ)
    assert (caught.value.key, caught.value.value) == (key, value)
