"""文字起こしの可否（GET /api/transcription）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .fixture_types import MakeItem, MakeWorkspace, StartFakeTranscriber, StartVoiceServer
from .http_helpers import HttpResult, http_request

# 文字起こしの可否のパス
TRANSCRIPTION_PATH = "/api/transcription"


def _get_status(start_voice_server: StartVoiceServer, transcriber_url: str, root: Path) -> HttpResult:
    """文字起こしのサービスの URL を渡して常駐サーバーを立て、配信の GET /api/transcription を 1 回送る。"""
    server = start_voice_server(transcriber_url)
    served = server.call("preview_url", workspace=str(root))
    assert served.data is not None, served.text
    return http_request(str(served.data["url"]), TRANSCRIPTION_PATH)


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    start_fake_transcriber: StartFakeTranscriber,
    start_voice_server: StartVoiceServer,
) -> None:
    """文字起こしのサービスに届き、使えることと用語集のプリセットの候補を返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        settings={**valid_settings, "transcription": {"action": "insert", "preset": "開発"}},
    )
    fake = start_fake_transcriber("done")
    # 実行
    result = _get_status(start_voice_server, fake.url, root)
    # 検証
    assert result.status == 200
    body = result.json()
    assert (body["available"], body["reason"]) == (True, None)
    assert body["presets"] == ["一般", "開発"]
    assert (body["action"], body["preset"]) == ("insert", "開発")


def test_normal_when_not_configured(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_fake_transcriber: StartFakeTranscriber,
    start_voice_server: StartVoiceServer,
) -> None:
    """config.yaml が transcription を持たないときは既定の挙動を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    fake = start_fake_transcriber("done")
    # 実行
    result = _get_status(start_voice_server, fake.url, root)
    # 検証
    assert result.status == 200
    assert (result.json()["action"], result.json()["preset"]) == ("send", None)


def test_normal_when_service_stopped(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_voice_server: StartVoiceServer,
    unreachable_transcriber_url: str,
) -> None:
    """サービスに届かないときは、使えない理由を 200 で返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = _get_status(start_voice_server, unreachable_transcriber_url, root)
    # 検証
    assert result.status == 200
    body = result.json()
    assert (body["available"], body["reason"], body["presets"]) == (False, "stopped", [])
    assert body["detail"] == "文字起こしのサービスが起動していないため、音声で入力できません。"
    assert "voice-paste" not in result.text


def test_normal_when_service_unsupported(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_fake_transcriber: StartFakeTranscriber,
    start_voice_server: StartVoiceServer,
) -> None:
    """サービスには届くが音声を受け付けるエンドポイントが無いときは、理由を 200 で返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    fake = start_fake_transcriber("unsupported")
    # 実行
    result = _get_status(start_voice_server, fake.url, root)
    # 検証
    assert result.status == 200
    body = result.json()
    assert (body["available"], body["reason"], body["presets"]) == (False, "unsupported", [])
    assert body["detail"] == "文字起こしのサービスが音声の受け付けに対応していないため、音声で入力できません。"
