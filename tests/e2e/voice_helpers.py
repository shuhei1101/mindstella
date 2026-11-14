"""音声でコメントする E2E テストの、偽のマイクと録音・文字起こしの操作の関数。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from integration.server.transcriber_helpers import FakeMode, FakeTranscriber
from playwright.sync_api import Locator, Page, expect
from workspace_fixtures import RECORD_DIR

# 偽の文字起こしのサービスを振る舞いの種類で起動する関数
type StartFakeTranscriber = Callable[[FakeMode], FakeTranscriber]

# 文字起こしのサービスの URL を渡して常駐サーバーを起動し、ワークスペースの配信の URL とフォルダを返す関数
type ServeVoiceWorkspace = Callable[..., tuple[str, Path]]

# 偽のマイク: getUserMedia を、Web Audio の発振器の音を流すトラックに差し替える（MediaRecorder は本物のまま録る）
FAKE_MIC_SCRIPT = """
(() => {
  const devices = navigator.mediaDevices;
  if (devices === undefined) return;
  devices.getUserMedia = async () => {
    const audio = new AudioContext();
    const tone = audio.createOscillator();
    const destination = audio.createMediaStreamDestination();
    tone.connect(destination);
    tone.start();
    return destination.stream;
  };
})();
"""

# マイクの機能を持たないページ: HTTPS でも localhost でもない経路で開いた形にする
NO_MIC_SCRIPT = "Object.defineProperty(navigator, 'mediaDevices', { value: undefined, configurable: true });"

# マイクの許可を拒否したブラウザ: getUserMedia が NotAllowedError で断る
DENIED_MIC_SCRIPT = """
(() => {
  navigator.mediaDevices.getUserMedia = async () => {
    throw new DOMException("Permission denied", "NotAllowedError");
  };
})();
"""

# 録音を止めるまでの間（録った音声が空にならない長さ）
RECORD_MS = 600

# 文字起こしの可否・文字起こし・送信の結果が画面に出るまで待つ上限ミリ秒
VOICE_TIMEOUT_MS = 20_000

# 文字起こしの可否のパス
TRANSCRIPTION_PATH = "/api/transcription"

# マイクのボタンのツールチップと結果の行の文
STOPPED_REASON = "文字起こしのサービスが起動していないため、音声で入力できません。"
UNSUPPORTED_REASON = "文字起こしのサービスが音声の受け付けに対応していないため、音声で入力できません。"
NO_MIC_REASON = "このページではマイクを使用できません。HTTPS か localhost の URL で開いてください。"
DENIED_REASON = "マイクを使用できませんでした。ブラウザの設定でこのページのマイクを許可してください。"
SENT_TEXT = "送信しました。Claude Code へは入力していません。"

# 既定の挙動（review）でレビュー中に溜めたときの結果の行の文
REVIEWED_TEXT = "文字起こしの結果をレビュー中に追加しました。"

# 偽の画面の消灯の抑止: navigator.wakeLock.request を、求めた種類と release の呼び出しを window.__wakeLock に記録する偽に差し替える
FAKE_WAKE_LOCK_SCRIPT = """
(() => {
  const log = { requested: [], released: 0 };
  window.__wakeLock = log;
  Object.defineProperty(navigator, 'wakeLock', {
    configurable: true,
    value: {
      request: async (type) => {
        log.requested.push(type);
        return { released: false, release: async () => { log.released += 1; } };
      },
    },
  });
})();
"""

# 画面の消灯の抑止を持たないページにする
NO_WAKE_LOCK_SCRIPT = "Object.defineProperty(navigator, 'wakeLock', { value: undefined, configurable: true });"

# 偽の画面の消灯の抑止の記録を読む
WAKE_LOCK_LOG_JS = "() => window.__wakeLock"


def open_with_status(page: Page, url: str) -> None:
    """URL を開き、文字起こしの可否を読み終えて描き直すまで待つ。"""
    with page.expect_response(
        lambda response: response.url.split("?")[0].endswith(TRANSCRIPTION_PATH), timeout=VOICE_TIMEOUT_MS
    ):
        page.goto(url)
    page.wait_for_selector("main#main > *", state="attached", timeout=VOICE_TIMEOUT_MS)


def record(form: Locator) -> None:
    """マイクのボタンで録音を始め、録音中の × と ✓ が出るまで待って、少し録る。"""
    form.get_by_role("button", name="音声で入力").click()
    expect(form.get_by_role("button", name="文字起こし")).to_be_visible(timeout=VOICE_TIMEOUT_MS)
    form.page.wait_for_timeout(RECORD_MS)


def expect_idle(form: Locator) -> None:
    """マイクのボタンと「レビューに追加」が元の位置に戻り、録音中の × と ✓ が無い。"""
    expect(form.get_by_role("button", name="音声で入力")).to_be_visible(timeout=VOICE_TIMEOUT_MS)
    expect(form.get_by_role("button", name="レビューに追加")).to_be_visible()
    expect(form.get_by_role("button", name="キャンセル")).to_have_count(0)


def expect_mic_blocked(form: Locator, reason: str) -> None:
    """マイクのボタンを押せない見た目にし、理由をツールチップに出し、「レビューに追加」は押せる。"""
    mic = form.get_by_role("button", name="音声で入力")
    expect(mic).to_have_attribute("aria-disabled", "true", timeout=VOICE_TIMEOUT_MS)
    expect(mic).to_have_attribute("title", reason)
    expect(form.get_by_role("button", name="レビューに追加")).to_be_enabled()


def read_items(root: Path, file_name: str) -> list[dict[str, Any]]:
    """ワークスペースの YAML の items を読む（ファイルが無ければ 0 件）。"""
    path = root / RECORD_DIR / file_name
    return yaml.safe_load(path.read_text(encoding="utf-8"))["items"] if path.exists() else []
