"""画面設計『詳細の全画面.tsx』の結合テスト。"""

from __future__ import annotations

from preview_fixture_types import StartVoicePreview as _StartVoicePreview
from preview_voice_helpers import (
    assert_mic_blocked_after_click,
)
from workspace_fixtures import MakeItem as _MakeItem

import re

from playwright.sync_api import Page, expect
from preview_spa_helpers import open_spa


def test_opens_and_returns(page: Page, spa_preview: str) -> None:
    """全画面で開き、元の大きさへ戻す（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&id=D-1&full=1")
    dialog = page.get_by_role("dialog", name="記録の形")
    expect(dialog.get_by_role("heading", name="決め方")).to_be_visible()
    expect(page.get_by_role("complementary", name="詳細")).to_have_count(0)
    dialog.get_by_role("button", name="元の大きさに戻す").click()
    expect(page.get_by_role("complementary", name="詳細")).to_be_visible()
    expect(page).not_to_have_url(re.compile("full=1"))


def test_comment_input_visible(page: Page, spa_preview: str) -> None:
    """サーバーの配信で開いたときは、全画面の下端にも詳細パネルと同じコメントの入力を出す（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions&id=D-1&full=1")
    # 検証
    dialog = page.get_by_role("dialog", name="記録の形")
    expect(dialog.get_by_role("textbox", name="D-1 へのコメント")).to_be_visible()
    expect(dialog.get_by_role("button", name="レビューに追加")).to_be_visible()


def test_voice_input_when_service_stopped(
    page: Page,
    make_item: _MakeItem,
    start_voice_preview: _StartVoicePreview,
    unreachable_transcriber_url: str,
) -> None:
    """文字起こしのサービスが起動していないときは、マイクのボタンを押せなくし、押すと理由を結果の行に出す（正常系）。"""
    # 準備
    url, _ = start_voice_preview(unreachable_transcriber_url, make_item("D-1"))
    # 実行
    open_spa(page, url, "?tab=decisions&id=D-1&full=1")
    # 検証
    assert_mic_blocked_after_click(page.locator("[role=dialog] form[data-id='D-1']"), "[role=status]")
