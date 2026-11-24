"""画面設計『詳細の全画面.tsx』の結合テスト。"""

from __future__ import annotations

from preview_fixture_types import StartVoicePreview as _StartVoicePreview
from preview_voice_helpers import (
    assert_mic_blocked_after_click,
)
from workspace_fixtures import MakeItem as _MakeItem

import re

from playwright.sync_api import Page, expect
from preview_spa_helpers import assert_bottom_aligned, open_spa

import pytest


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

@pytest.mark.parametrize(
    "size",
    [pytest.param({"width": 1280, "height": 800}, id="wide"), pytest.param({"width": 390, "height": 844}, id="phone")],
)
def test_comment_input_at_bottom(page: Page, spa_preview: str, size: dict[str, int]) -> None:
    """全画面のコメントの入力は、モーダルの下端に間を空けずに出す（正常系）。"""
    # 準備
    page.set_viewport_size(size)
    # 実行
    open_spa(page, spa_preview, "?tab=decisions&id=D-1&full=1")
    # 検証
    dialog = page.get_by_role("dialog", name="記録の形")
    form = dialog.locator("form[data-id='D-1']")
    expect(form).to_be_visible()
    assert_bottom_aligned(form, dialog)


def test_supplement_tabs_and_toc(page: Page, spa_preview: str) -> None:
    """全画面にも本文の切り替えのタブと本文の目次を出し、目次の項目を押すと「本文」を選んで見出しへ移る（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=decisions&id=D-1&full=1")
    dialog = page.get_by_role("dialog", name="記録の形")
    expect(dialog.get_by_role("tablist", name="詳細の表示").get_by_role("tab")).to_have_text(["本文", "関連", "コメント"])
    dialog.get_by_role("tab", name="関連").click()
    # 実行
    dialog.get_by_role("button", name="本文の目次").click()
    page.get_by_role("navigation", name="本文の目次").get_by_role("button", name="決め方").click()
    # 検証
    page.wait_for_url("**h=*")
    expect(dialog.get_by_role("tab", name="本文")).to_have_attribute("aria-selected", "true")
    expect(dialog.get_by_role("heading", name="決め方")).to_be_visible()
