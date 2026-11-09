"""core/voice.ts（録音・カーソルの位置への挿入・文字起こしの結果の組み立て）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 偽の getUserMedia・MediaRecorder を持つ窓を作り、録音を始めて止めるかキャンセルする JavaScript
RECORDING_SCRIPT = """async ({action, failure}) => {
    const stopped = [];
    const track = {stop: () => stopped.push(true)};
    class FakeRecorder {
        static isTypeSupported(type) { return type === "audio/webm;codecs=opus"; }
        constructor(stream, options) { this.mimeType = options?.mimeType ?? ""; this.listeners = {}; }
        addEventListener(name, listener) { this.listeners[name] = listener; }
        start() {}
        stop() {
            this.listeners.dataavailable?.({data: new Blob(["ab"])});
            this.listeners.dataavailable?.({data: new Blob(["cd"])});
            this.listeners.stop?.();
        }
    }
    const win = {
        navigator: {mediaDevices: {getUserMedia: async () => {
            if (failure) { throw new DOMException("x", failure); }
            return {getTracks: () => [track]};
        }}},
        MediaRecorder: FakeRecorder,
    };
    try {
        const recording = await MindmapPreview.startRecording(win);
        if (action === "cancel") {
            recording.cancel();
            return {stopped: stopped.length, blob: null};
        }
        const blob = await recording.stop();
        return {stopped: stopped.length, blob: {type: blob.type, text: await blob.text()}};
    } catch (error) {
        return {error: String(error)};
    }
}"""

# 偽の API と録音で finishVoice を呼ぶ JavaScript
FINISH_SCRIPT = """async ({action, transcribe, sendNow}) => {
    const sent = [];
    const api = {
        status: async () => ({ok: true, data: null}),
        transcribe: async () => transcribe,
        sendNow: async (input) => { sent.push(input); return sendNow; },
    };
    const recording = {stop: async () => new Blob(["v"], {type: "audio/webm"}), cancel: () => {}};
    const outcome = await MindmapPreview.finishVoice(
        recording,
        {body: "確認: ", start: 4, end: 4, action, destination: {target: "D-1", loc: null}},
        api,
    );
    return {outcome, sent};
}"""

# 文字起こしできたときの API の結果
TRANSCRIBED = {"ok": True, "data": {"text": "案 A にする"}, "status": 200, "detail": None, "stale": []}


@pytest.mark.parametrize(
    ("setup", "expected"),
    [
        pytest.param("both", True, id="both"),
        pytest.param("no-media-devices", False, id="no_media_devices"),
        pytest.param("no-recorder", False, id="no_recorder"),
    ],
)
def test_mic_supported(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, setup: str, expected: bool
) -> None:
    """両方があるときだけ真（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """(setup) => MindmapPreview.micSupported({
            navigator: setup === "no-media-devices" ? {} : {mediaDevices: {getUserMedia: () => {}}},
            MediaRecorder: setup === "no-recorder" ? undefined : function () {},
        })""",
        setup,
    )
    # 検証
    assert result is expected


def test_start_recording(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """録って止めると音声を返し、トラックを止める（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(RECORDING_SCRIPT, {"action": "stop", "failure": None})
    # 検証
    assert result == {"stopped": 1, "blob": {"type": "audio/webm;codecs=opus", "text": "abcd"}}


def test_start_recording_when_cancelled(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """キャンセルは捨ててトラックを止める（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(RECORDING_SCRIPT, {"action": "cancel", "failure": None})
    # 検証
    assert result == {"stopped": 1, "blob": None}


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        pytest.param("NotAllowedError", "denied", id="denied"),
        pytest.param("NotFoundError", "no-microphone", id="no_microphone"),
    ],
)
def test_start_recording_when_rejected(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, failure: str, expected: str
) -> None:
    """許可の拒否と、それ以外を分ける（異常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(RECORDING_SCRIPT, {"action": "stop", "failure": failure})
    # 検証
    assert result == {"error": expected}


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        pytest.param(["確認: ", 4, 4, "案 A"], {"value": "確認: 案 A", "caret": 6}, id="caret"),
        pytest.param(["ab", 0, 0, "x"], {"value": "xab", "caret": 1}, id="head"),
        pytest.param(["abc", 1, 2, "x"], {"value": "axc", "caret": 2}, id="selection"),
        pytest.param(["ab", 9, 9, "x"], {"value": "abx", "caret": 3}, id="beyond"),
    ],
)
def test_insert_at_cursor(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    arguments: list[Any],
    expected: dict[str, Any],
) -> None:
    """カーソルの位置と選んだ範囲（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate("(args) => MindmapPreview.insertAtCursor(...args)", arguments)
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        pytest.param(0, "0:00", id="zero"),
        pytest.param(12, "0:12", id="seconds"),
        pytest.param(72, "1:12", id="minute"),
        pytest.param(3600, "60:00", id="hour"),
    ],
)
def test_format_elapsed(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, seconds: int, expected: str
) -> None:
    """分と秒（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate("(seconds) => MindmapPreview.formatElapsed(seconds)", seconds)
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    ("action", "expected_outcome", "expected_sent"),
    [
        pytest.param(
            "insert",
            {"kind": "inserted", "body": "確認: 案 A にする", "caret": 10},
            [],
            id="insert",
        ),
        pytest.param(
            "send",
            {"kind": "sent", "body": "", "entered": True},
            [{"target": "D-1", "loc": None, "body": "確認: 案 A にする"}],
            id="send",
        ),
    ],
)
def test_finish_voice(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    action: str,
    expected_outcome: dict[str, Any],
    expected_sent: list[dict[str, Any]],
) -> None:
    """挿入してから挙動で分ける（正常系）。"""
    # 準備
    load_preview_scripts()
    sent_now = {"ok": True, "data": {"sent": "t", "thread": "TH-1", "post": "TH-1-1", "entered": True}}
    # 実行
    result = preview_page.evaluate(
        FINISH_SCRIPT, {"action": action, "transcribe": TRANSCRIBED, "sendNow": sent_now}
    )
    # 検証
    assert {key: result["outcome"][key] for key in expected_outcome} == expected_outcome
    assert result["sent"] == expected_sent


@pytest.mark.parametrize(
    ("action", "transcribe", "send_now", "expected"),
    [
        pytest.param(
            "send",
            {"ok": False, "status": 503, "detail": "止まっています", "reason": "stopped", "stale": []},
            None,
            {"kind": "unavailable", "reason": "stopped", "detail": "止まっています"},
            id="unavailable",
        ),
        pytest.param(
            "send",
            {"ok": False, "status": 502, "detail": "失敗の理由", "stale": []},
            None,
            {"kind": "failed", "detail": "失敗の理由", "body": "確認: "},
            id="failed_detail",
        ),
        pytest.param(
            "send",
            {"ok": False, "status": None, "detail": None, "stale": []},
            None,
            {"kind": "failed", "detail": "文字起こしできませんでした。もう一度お試しください。"},
            id="unreachable",
        ),
        pytest.param(
            "send",
            {"ok": True, "data": {"text": "  "}, "status": 200, "detail": None, "stale": []},
            None,
            {
                "kind": "failed",
                "detail": "文字起こしできませんでした。もう一度お試しください。",
                "body": "確認: ",
            },
            id="empty_text",
        ),
        pytest.param(
            "send",
            TRANSCRIBED,
            {"ok": False, "status": 409, "detail": "x", "stale": []},
            {
                "kind": "failed",
                "detail": "送信できませんでした。文字起こしの結果は入力欄に残しています。",
                "body": "確認: 案 A にする",
            },
            id="send_failed",
        ),
    ],
)
def test_finish_voice_when_failed(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    action: str,
    transcribe: dict[str, Any],
    send_now: dict[str, Any] | None,
    expected: dict[str, Any],
) -> None:
    """文字起こしと送信の失敗（異常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        FINISH_SCRIPT, {"action": action, "transcribe": transcribe, "sendNow": send_now}
    )
    # 検証
    assert {key: result["outcome"][key] for key in expected} == expected
