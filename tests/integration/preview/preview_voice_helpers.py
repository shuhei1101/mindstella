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
    # aria-disabled のボタンは押せる（フォーカスを受けたまま）。Playwright の操作の待ちを省いて押す
    mic.click(force=True)
    expect(form.locator(message)).to_have_text(STOPPED_REASON, timeout=STATUS_TIMEOUT_MS)


def assert_mic_ready(form: Locator) -> None:
    """マイクのボタンを押せる状態で「レビューに追加」の左に配置している。"""
    mic = form.get_by_role("button", name="音声で入力")
    expect(mic).to_be_visible()
    expect(mic).not_to_have_attribute("aria-disabled", "true")
    expect(mic).to_have_attribute("title", "音声で入力")
