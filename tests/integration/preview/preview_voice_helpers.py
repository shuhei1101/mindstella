"""コメント・返信の入力の音声入力を、画面の結合テストで確認する関数。"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from playwright.sync_api import Locator, Page, expect

# 文字起こしのサービスが起動していないときの理由（『文字起こしの可否』の detail）
STOPPED_REASON = "文字起こしのサービスが起動していないため、音声で入力できません。"

# 文字起こしの可否のパス
TRANSCRIPTION_PATH = "/api/transcription"

# 文字起こしの可否を取得して描き直すまで待つ上限ミリ秒
STATUS_TIMEOUT_MS = 10_000

# 要素とその祖先で動いているアニメーション（パネルのすべり込みの transition）が終わるまで待つ
SETTLE_ANIMATIONS_JS = """async (element) => {
  const running = document.getAnimations().filter((animation) => {
    const target = animation.effect?.target;
    return target instanceof Element && target.contains(element);
  });
  await Promise.all(running.map((animation) => animation.finished));
}"""


@contextmanager
def wait_transcription_status(page: Page) -> Iterator[None]:
    """ブロックの中で開いた画面が、文字起こしの可否を取得し終えるまで待つ。"""
    with page.expect_response(
        lambda response: response.url.split("?")[0].endswith(TRANSCRIPTION_PATH), timeout=STATUS_TIMEOUT_MS
    ):
        yield


def assert_mic_blocked_after_click(form: Locator, message: str) -> None:
    """マイクのボタンを押せない見た目にして理由をツールチップに出し、押すと結果の行に理由を出す。"""
    mic = form.get_by_role("button", name="音声で入力")
    expect(mic).to_have_attribute("aria-disabled", "true", timeout=STATUS_TIMEOUT_MS)
    expect(mic).to_have_attribute("title", STOPPED_REASON)
    expect(form.get_by_role("button", name="レビューに追加")).to_be_visible()
    # 操作の待ちを省いて押すため、パネルのすべり込みが済んでボタンが画面に収まるまで先に待つ
    expect(mic).to_be_in_viewport(ratio=1)
    form.evaluate(SETTLE_ANIMATIONS_JS)
    # aria-disabled のボタンは押せる（フォーカスを受けたまま）。Playwright の操作の待ちを省いて押す
    mic.click(force=True)
    expect(form.locator(message)).to_have_text(STOPPED_REASON, timeout=STATUS_TIMEOUT_MS)


def assert_mic_ready(form: Locator) -> None:
    """マイクのボタンを押せる状態で「レビューに追加」の左に配置している。"""
    mic = form.get_by_role("button", name="音声で入力")
    expect(mic).to_be_visible()
    expect(mic).not_to_have_attribute("aria-disabled", "true")
    expect(mic).to_have_attribute("title", "音声で入力")


# 偽のマイク: getUserMedia を、Web Audio の発振器の音を流すトラックに差し替える（MediaRecorder と AnalyserNode は本物のまま動く）
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

# 録音を止めるまでの間（録った音声が空にならず、波形の棒が出る長さ）
RECORD_MS = 600

# 文字起こしの結果が画面に出るまで待つ上限ミリ秒
VOICE_TIMEOUT_MS = 20_000

# 入力欄の中身・選んだ範囲と、フォーカスのある要素の読み上げの名前を読む
FIELD_STATE_JS = """(field) => ({
  value: field.value,
  start: field.selectionStart,
  end: field.selectionEnd,
  focused: document.activeElement === field,
  active: document.activeElement?.getAttribute('aria-label') ?? document.activeElement?.tagName ?? null,
})"""


def put_caret(field: Locator, value: str, caret: int) -> None:
    """入力欄に中身を入れ、カーソルを位置 caret に置く。"""
    field.fill(value)
    field.evaluate("(element, caret) => element.setSelectionRange(caret, caret)", caret)


def start_recording(form: Locator) -> None:
    """マイクのボタンで録音を始め、✓ の「文字起こし」が出て波形に棒が出るまで待つ。"""
    form.get_by_role("button", name="音声で入力").click()
    expect(form.get_by_role("button", name="文字起こし", exact=True)).to_be_visible(timeout=VOICE_TIMEOUT_MS)
    form.page.wait_for_timeout(RECORD_MS)


def assert_recording_wave(form: Locator) -> None:
    """録音中は入力欄を隠し、入力欄の場所に読み上げない波形の棒を出し、✓ の「文字起こし」にフォーカスがある。"""
    expect(form.locator("textarea")).to_be_hidden()
    wave = form.locator(".send-wave, [data-part='voice-wave']")
    expect(wave).to_be_visible()
    expect(wave).to_have_attribute("aria-hidden", "true")
    assert wave.locator("i").count() > 0
    expect(form.get_by_role("button", name="文字起こし", exact=True)).to_be_focused()
