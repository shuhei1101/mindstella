"""音声の文字起こし（POST /api/transcriptions）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from .fixture_types import (
    MakeItem,
    MakeWorkspace,
    McpServer,
    SnapshotTree,
    StartFakeTranscriber,
    StartVoiceServer,
)
from .http_helpers import HttpResult, http_request
from .transcriber_helpers import FAILED_REASON

# 音声の文字起こしのパス
TRANSCRIPTIONS_PATH = "/api/transcriptions"

# 録音した音声の Content-Type
AUDIO_TYPE = "audio/webm"

# テストの中で書き出した短い webm/opus（EBML のヘッダーと OpusHead を持つ）
AUDIO = bytes.fromhex("1a45dfa39f4286810142f7810142f2810442f381084282847765626d") + b"OpusHead" + bytes(32)

# 文字起こしの失敗と打ち切りの detail
FAILED_DETAIL = "文字起こしできませんでした。もう一度お試しください。"

# 文字起こしの待ちの上限を 1 秒にする差し替え
SHORT_WAIT = {"voice_paste": {"WAIT_LIMIT_SEC": 1.0}}

# 録音の大きさの上限を 1,000 バイトにする差し替え
SMALL_AUDIO_LIMIT = {"serve": {"MAX_AUDIO_BYTES": 1000}}


def _preview_url(server: McpServer, root: Path) -> str:
    """preview_url を呼び、配信の URL を返す。"""
    served = server.call("preview_url", workspace=str(root))
    assert served.data is not None, served.text
    return str(served.data["url"])


def _post_audio(url: str, audio: bytes) -> HttpResult:
    """録音した音声の Content-Type で音声を 1 回送る。"""
    return http_request(
        url, TRANSCRIPTIONS_PATH, method="POST", headers={"Content-Type": AUDIO_TYPE}, body=audio
    )


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    start_fake_transcriber: StartFakeTranscriber,
    start_voice_server: StartVoiceServer,
    snapshot_tree: SnapshotTree,
) -> None:
    """録音した音声を文字起こしのサービスへ渡し、終わるまで待って起こした文字を返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        settings={**valid_settings, "transcription": {"action": "send", "preset": "開発"}},
    )
    fake = start_fake_transcriber("done")
    url = _preview_url(start_voice_server(fake.url), root)
    before = snapshot_tree(root)
    # 実行
    result = _post_audio(url, AUDIO)
    # 検証
    assert result.status == 200
    assert result.json() == {"text": "案 A にする"}
    assert len(fake.jobs) == 1
    assert (fake.jobs[0].audio, fake.jobs[0].audio_type, fake.jobs[0].preset) == (AUDIO, AUDIO_TYPE, "開発")
    assert snapshot_tree(root) == before


def test_normal_when_no_preset(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_fake_transcriber: StartFakeTranscriber,
    start_voice_server: StartVoiceServer,
) -> None:
    """transcription.preset が無いときは、プリセットを付けずに依頼する（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    fake = start_fake_transcriber("done")
    url = _preview_url(start_voice_server(fake.url), root)
    # 実行
    result = _post_audio(url, AUDIO)
    # 検証
    assert result.status == 200
    assert [job.preset for job in fake.jobs] == [None]


def test_error_when_service_stopped(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_voice_server: StartVoiceServer,
    unreachable_transcriber_url: str,
) -> None:
    """サービスに届かないときは、依頼せずに使えない理由を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = _preview_url(start_voice_server(unreachable_transcriber_url), root)
    # 実行
    result = _post_audio(url, AUDIO)
    # 検証
    assert result.status == 503
    assert result.json()["reason"] == "stopped"
    assert result.json()["detail"] == "文字起こしのサービスが起動していないため、音声で入力できません。"


def test_error_when_service_unsupported(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_fake_transcriber: StartFakeTranscriber,
    start_voice_server: StartVoiceServer,
) -> None:
    """サービスに音声を受け付けるエンドポイントが無いときは、使えない理由を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    fake = start_fake_transcriber("unsupported")
    url = _preview_url(start_voice_server(fake.url), root)
    # 実行
    result = _post_audio(url, AUDIO)
    # 検証
    assert result.status == 503
    assert result.json()["reason"] == "unsupported"


def test_error_when_transcription_failed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_fake_transcriber: StartFakeTranscriber,
    start_voice_server: StartVoiceServer,
) -> None:
    """サービスが文字起こしの失敗を返したときは、失敗を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    fake = start_fake_transcriber("failed")
    server = start_voice_server(fake.url)
    url = _preview_url(server, root)
    # 実行
    result = _post_audio(url, AUDIO)
    # 検証
    assert result.status == 502
    assert result.json()["detail"] == FAILED_DETAIL
    assert FAILED_REASON not in result.text
    assert FAILED_REASON in server.stderr_text()


def test_error_when_transcription_timeout(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_fake_transcriber: StartFakeTranscriber,
    start_voice_server: StartVoiceServer,
) -> None:
    """待ちの上限を超えても終わらないときは、打ち切って返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    fake = start_fake_transcriber("running")
    url = _preview_url(start_voice_server(fake.url, SHORT_WAIT), root)
    # 実行
    result = _post_audio(url, AUDIO)
    # 検証
    assert result.status == 504
    assert result.json()["detail"] == FAILED_DETAIL


@pytest.mark.parametrize(
    ("audio", "status"),
    [
        pytest.param(b"", 400, id="empty"),
        pytest.param(bytes(1001), 413, id="too-large"),
    ],
)
def test_error_when_audio_empty_or_too_large(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_fake_transcriber: StartFakeTranscriber,
    start_voice_server: StartVoiceServer,
    audio: bytes,
    status: int,
) -> None:
    """空の本文と上限を超える本文を、依頼せずに断る（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    fake = start_fake_transcriber("done")
    url = _preview_url(start_voice_server(fake.url, SMALL_AUDIO_LIMIT), root)
    # 実行
    result = _post_audio(url, audio)
    # 検証
    assert result.status == status
    assert fake.jobs == []
