"""core/voice.ts（録音・カーソルの位置への挿入・文字起こしの結果の組み立て）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 偽の getUserMedia・MediaRecorder・AudioContext と時計を持つ窓を作り、録音を始めて止めるかキャンセルする JavaScript
RECORDING_SCRIPT = """async ({action, failure, ticks}) => {
    const stopped = [];
    const levels = [];
    const timers = new Map();
    let nextTimer = 1;
    let closed = false;
    const track = {stop: () => stopped.push(true)};
    // 128 を無音とし、192 を 1 つ持つ値（音量 0.5）を返す
    class FakeAudioContext {
        createMediaStreamSource() { return {connect: () => {}}; }
        createAnalyser() {
            return {
                fftSize: 2048,
                getByteTimeDomainData: (values) => { values.fill(128); values[0] = 192; },
            };
        }
        close() { closed = true; return Promise.resolve(); }
    }
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
        AudioContext: FakeAudioContext,
        setInterval: (callback) => { const id = nextTimer++; timers.set(id, callback); return id; },
        clearInterval: (id) => { timers.delete(id); },
    };
    // 偽の時計を 1 間隔ぶん進める
    const tick = () => { for (const callback of [...timers.values()]) { callback(); } };
    try {
        const recording = await MindmapPreview.startRecording((level) => levels.push(level), win);
        for (let i = 0; i < ticks; i += 1) { tick(); }
        if (action === "cancel") {
            recording.cancel();
            tick();
            return {stopped: stopped.length, blob: null, levels, closed};
        }
        const blob = await recording.stop();
        tick();
        return {
            stopped: stopped.length,
            blob: {type: blob.type, text: await blob.text()},
            levels,
            closed,
        };
    } catch (error) {
        return {error: String(error)};
    }
}"""

# 偽の API と録音で finishVoice を呼ぶ JavaScript
FINISH_SCRIPT = """async ({action, transcribe, sendNow, add}) => {
    const sent = [];
    const added = [];
    const api = {
        status: async () => ({ok: true, data: null}),
        transcribe: async () => transcribe,
        sendNow: async (input) => { sent.push(input); return sendNow; },
        add: async (input) => { added.push(input); return add; },
    };
    const recording = {stop: async () => new Blob(["v"], {type: "audio/webm"}), cancel: () => {}};
    const outcome = await MindmapPreview.finishVoice(
        recording,
        {body: "確認: ", start: 4, end: 4, action, destination: {target: "D-1", loc: null}},
        api,
    );
    return {outcome, sent, added};
}"""

# 文字起こしできたときの API の結果
TRANSCRIBED = {"ok": True, "data": {"text": "案 A にする"}, "status": 200, "detail": None, "stale": []}

# レビュー中に溜められたときの API の結果
ADDED = {"ok": True, "data": {"id": "C-1", "created": "2026-11-14T00:00:00+00:00", "count": 1}}

# 偽の navigator.wakeLock で acquireWakeLock を呼び、返った関数を 2 回呼ぶ JavaScript
WAKE_LOCK_SCRIPT = """async ({mode}) => {
    const requested = [];
    let released = 0;
    const sentinel = {release: async () => { released += 1; }};
    const navigator = mode === "missing" ? {} : {wakeLock: {request: async (type) => {
        requested.push(type);
        if (mode === "denied") { throw new DOMException("x", "NotAllowedError"); }
        return sentinel;
    }}};
    try {
        const release = await MindmapPreview.acquireWakeLock({navigator});
        release();
        release();
        await Promise.resolve();
        return {requested, released, error: null};
    } catch (error) {
        return {requested, released, error: String(error)};
    }
}"""


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
    result = preview_page.evaluate(RECORDING_SCRIPT, {"action": "stop", "failure": None, "ticks": 0})
    # 検証
    assert {key: result[key] for key in ("stopped", "blob")} == {
        "stopped": 1,
        "blob": {"type": "audio/webm;codecs=opus", "text": "abcd"},
    }


def test_start_recording_when_cancelled(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """キャンセルは捨ててトラックを止める（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(RECORDING_SCRIPT, {"action": "cancel", "failure": None, "ticks": 0})
    # 検証
    assert {key: result[key] for key in ("stopped", "blob")} == {"stopped": 1, "blob": None}


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
    result = preview_page.evaluate(RECORDING_SCRIPT, {"action": "stop", "failure": failure, "ticks": 0})
    # 検証
    assert result == {"error": expected}


def test_start_recording_levels(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """間隔ごとに音量を知らせ、止めたら知らせない（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(RECORDING_SCRIPT, {"action": "stop", "failure": None, "ticks": 2})
    # 検証
    assert result["levels"] == [0.5, 0.5]
    assert result["closed"] is True


@pytest.mark.parametrize(
    ("levels", "level", "expected"),
    [
        pytest.param([], 0.5, {"length": 1, "first": 0.5, "last": 0.5}, id="empty"),
        pytest.param([0.1, 0.2], 1.4, {"length": 3, "first": 0.1, "last": 1}, id="clamped"),
        pytest.param(None, 0.3, {"length": 400, "first": 0.001, "last": 0.3}, id="full"),
    ],
)
def test_push_level(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    levels: list[float] | None,
    level: float,
    expected: dict[str, float],
) -> None:
    """末尾に足し、上限を超えた古いものを捨てる（正常系）。"""
    # 準備（None は長さ WAVE_LEVELS_MAX の並び）
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """([levels, level]) => {
            const source = levels ?? Array.from({length: MindmapPreview.WAVE_LEVELS_MAX}, (_, i) => i / 1000);
            const original = JSON.stringify(source);
            const pushed = MindmapPreview.pushLevel(source, level);
            return {
                length: pushed.length,
                first: pushed[0],
                last: pushed.at(-1),
                unchanged: JSON.stringify(source) === original,
            };
        }""",
        [levels, level],
    )
    # 検証
    assert result == {**expected, "unchanged": True}


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        pytest.param(["確認: ", 4, 4, "案 A"], {"value": "確認: 案 A", "caret": 7}, id="caret"),
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
            "review",
            {"kind": "reviewed", "body": "", "count": 1},
            [],
            id="review",
        ),
        pytest.param(
            "insert",
            {"kind": "inserted", "body": "確認: 案 A にする", "caret": 11},
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
        FINISH_SCRIPT,
        {"action": action, "transcribe": TRANSCRIBED, "sendNow": sent_now, "add": ADDED},
    )
    # 検証
    assert {key: result["outcome"][key] for key in expected_outcome} == expected_outcome
    assert result["sent"] == expected_sent
    expected_added = [{"target": "D-1", "loc": None, "body": "確認: 案 A にする"}] if action == "review" else []
    assert result["added"] == expected_added


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
        pytest.param(
            "review",
            TRANSCRIBED,
            None,
            {
                "kind": "failed",
                "detail": "レビュー中に追加できませんでした。文字起こしの結果は入力欄に残しています。",
                "body": "確認: 案 A にする",
            },
            id="review_failed",
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
    """文字起こしと追加・送信の失敗（異常系）。"""
    # 準備
    load_preview_scripts()
    add_failed = {"ok": False, "status": 500, "detail": "x", "stale": []}
    # 実行
    result = preview_page.evaluate(
        FINISH_SCRIPT,
        {"action": action, "transcribe": transcribe, "sendNow": send_now, "add": add_failed},
    )
    # 検証
    assert {key: result["outcome"][key] for key in expected} == expected


def test_acquire_wake_lock(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """求めて解く（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(WAKE_LOCK_SCRIPT, {"mode": "ok"})
    # 検証
    assert result == {"requested": ["screen"], "released": 1, "error": None}


@pytest.mark.parametrize("mode", [pytest.param("missing", id="missing"), pytest.param("denied", id="denied")])
def test_acquire_wake_lock_when_unavailable(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, mode: str
) -> None:
    """持たない・断られたときは何もしない（異常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(WAKE_LOCK_SCRIPT, {"mode": mode})
    # 検証
    assert result["error"] is None
    assert result["released"] == 0
