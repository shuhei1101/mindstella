"""画面設計『コメントの一覧.tsx』の結合テスト。"""

from __future__ import annotations

from preview_fixture_types import StartVoicePreview as _StartVoicePreview
from preview_voice_helpers import (
    assert_mic_blocked_after_click,
)
from workspace_fixtures import MakeItem as _MakeItem

import json
from pathlib import Path

from playwright.sync_api import Locator, Page, Route, expect
from preview_comment_helpers import read_workspace_yaml
from preview_spa_helpers import open_spa

# パネルを画面いっぱいに出す幅（これ以下）と、画面の高さ
NARROW_SIZE = {"width": 800, "height": 700}

# 書き換えの知らせ・保存を待つ上限ミリ秒
UPDATE_TIMEOUT_MS = 10_000


def _panel(page: Page) -> Locator:
    """コメントの一覧のパネルを返す。"""
    return page.get_by_role("dialog", name="コメント")


def _rows(page: Page) -> Locator:
    """スレッドの行を上から返す。"""
    return _panel(page).locator("li[data-thread], li[data-pending]")


def _open(page: Page, spa_comments_preview: tuple[str, Path], search: str = "") -> Page:
    """コメントの一覧を開いた画面を返す。"""
    url, _ = spa_comments_preview
    return open_spa(page, url, f"?tab=decisions&panel=comments{search}")


def test_heading(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """見出し「コメント」を、スレッドの一覧とスレッドの画面の両方で出す（正常系）。"""
    # 準備・実行
    _open(page, spa_comments_preview)
    # 検証
    expect(_panel(page).get_by_role("heading", level=2, name="コメント")).to_be_visible()
    _rows(page).filter(has_text="二つ目の要約").locator("> button").click()
    expect(_panel(page).get_by_role("heading", level=2, name="コメント")).to_be_visible()


def test_review_entry(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """「レビュー中」の入口は件数を出し、押すとレビュー中の書き込みの画面に切り替えて入口を出さない（正常系）。"""
    # 準備
    _open(page, spa_comments_preview)
    entry = _panel(page).get_by_role("button", name="レビュー中の書き込みを確かめる（2 件）")
    # 実行
    expect(entry).to_have_text("レビュー中2")
    entry.click()
    # 検証
    page.wait_for_url("**review=1**")
    expect(_panel(page).get_by_role("button", name="レビュー中の書き込みを確かめる（2 件）")).to_have_count(0)


def test_close(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """閉じるボタン・Esc・グレーアウトのどれでもパネルを閉じ、search params から `panel` を外す（正常系）。"""
    # 準備
    _open(page, spa_comments_preview)
    # 実行（閉じるボタン）
    _panel(page).get_by_role("button", name="コメントの一覧を閉じる").click()
    # 検証
    expect(_panel(page)).to_have_count(0)
    assert "panel=" not in page.url
    # 実行（Esc）
    _open(page, spa_comments_preview)
    page.keyboard.press("Escape")
    # 検証
    expect(_panel(page)).to_have_count(0)
    # 実行（グレーアウト）
    _open(page, spa_comments_preview)
    page.mouse.click(1200, 400)
    # 検証
    expect(_panel(page)).to_have_count(0)


def test_status_filter(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """状態の絞り込みは件数つきの 3 つのボタンで、押した状態を `aria-pressed` で持ち、押すと行を絞る（正常系）。"""
    # 準備
    _open(page, spa_comments_preview)
    group = _panel(page).get_by_role("group", name="スレッドの状態で絞る")
    # 検証（件数と押した状態）
    expect(group.get_by_role("button")).to_have_text(["オープン2", "クローズ1", "すべて3"])
    expect(group.get_by_role("button", name="オープン")).to_have_attribute("aria-pressed", "true")
    # 実行
    group.get_by_role("button", name="クローズ").click()
    # 検証
    page.wait_for_url("**tstatus=closed**")
    expect(group.get_by_role("button", name="クローズ")).to_have_attribute("aria-pressed", "true")
    expect(_rows(page)).to_have_count(1)
    expect(_rows(page).first).to_contain_text("閉じた話")


def test_tag_filter(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """行のタグを押すとそのタグで絞り、チップに件数を出し、× で外す（正常系）。"""
    # 準備
    _open(page, spa_comments_preview)
    # 実行
    _rows(page).filter(has_text="D-1 の案の相談").get_by_role("button", name="タグ「画面」で絞る").click()
    # 検証（タグで絞ると、まだ送っていない新しいスレッドは並べない）
    page.wait_for_url("**ttag=**")
    expect(_rows(page)).to_have_count(1)
    expect(_panel(page)).to_contain_text("1 / 2 件")
    # 実行
    _panel(page).get_by_role("button", name="タグ「画面」の絞り込みを外す").click()
    # 検証
    expect(_rows(page)).to_have_count(3)
    assert "ttag=" not in page.url


def test_thread_rows(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """まだ送っていない新しいスレッドを先頭に、続けてスレッドを最後の書き込みの新しい順に並べ、行を押すとスレッドの画面を開く（正常系）。"""
    # 準備
    _open(page, spa_comments_preview)
    # 検証（並び）
    expect(_rows(page)).to_have_count(3)
    assert _rows(page).evaluate_all("rows => rows.map(r => r.dataset.thread ?? r.dataset.pending)") == ["C-41", "TH-2", "TH-1"]
    # 検証（未読の札）
    expect(_rows(page).filter(has_text="D-1 の案の相談").locator("[data-part=unread]")).to_have_text("未読")
    # 実行
    _rows(page).filter(has_text="二つ目の要約").locator("> button").click()
    # 検証
    page.wait_for_url("**thread=TH-2**")
    expect(_panel(page).get_by_role("heading", level=2, name="二つ目の要約")).to_be_visible()


def test_empty_state(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """並べる行が無いとき、絞り込みを含めた文言を出す（正常系）。"""
    # 準備・実行
    _open(page, spa_comments_preview, "&tstatus=closed&ttag=調査")
    # 検証
    expect(_rows(page)).to_have_count(0)
    expect(_panel(page)).to_contain_text("タグ「調査」のクローズのスレッドはありません。")


def test_threads_unreadable(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """スレッドを読めないとき、理由を `role="alert"` で出し、まだ送っていない新しいスレッドは並べる（異常系）。"""
    # 準備
    page.route("**/api/threads", lambda route: route.abort())
    # 実行
    _open(page, spa_comments_preview)
    # 検証
    alert = _panel(page).get_by_role("alert")
    expect(alert).to_have_text("スレッドを読めませんでした。サーバーが止まっています。立ち上げ直してから開いてください。")
    expect(_rows(page)).to_have_count(1)
    expect(_rows(page).first).to_have_attribute("data-pending", "C-41")


def test_threads_unreadable_with_detail(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """スレッドの読み取りが 422 のとき、`detail` を続けて出す（異常系）。"""
    # 準備
    body = {"type": "about:blank", "title": "Unprocessable Entity", "status": 422, "detail": "threads.yaml が壊れています"}

    def _refuse(route: Route) -> None:
        """スレッドの読み取りを 422 で断る。"""
        route.fulfill(status=422, content_type="application/problem+json", body=json.dumps(body))

    page.route("**/api/threads", _refuse)
    # 実行
    _open(page, spa_comments_preview)
    # 検証
    expect(_panel(page).get_by_role("alert")).to_have_text("スレッドを読めませんでした。threads.yaml が壊れています")


def test_new_thread(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """「新しいスレッド」を押すと入力を出して入力欄へフォーカスを移し、溜めると一覧の先頭と入口の件数に足す（正常系）。"""
    # 準備
    _, root = spa_comments_preview
    _open(page, spa_comments_preview)
    # 実行
    _panel(page).get_by_role("button", name="新しいスレッド").click()
    field = _panel(page).get_by_role("textbox", name="新しいスレッド")
    # 検証（入力欄へフォーカス）
    expect(field).to_be_focused()
    # 実行
    field.fill("全体を見直したい")
    _panel(page).get_by_role("button", name="レビューに追加").click()
    # 検証
    expect(field).to_have_value("")
    expect(_panel(page).get_by_role("button", name="レビュー中の書き込みを確かめる（3 件）")).to_be_visible()
    # まだ送っていない新しいスレッドは、溜めた順に一覧の先頭へ並べる
    expect(_panel(page).locator("li[data-pending]")).to_have_count(2)
    expect(_panel(page).locator("li[data-pending]").last).to_contain_text("全体を見直したい")
    items = read_workspace_yaml(root, "comments.yaml")["items"]
    assert [item["body"] for item in items if "target" not in item and "thread" not in item] == ["全体を見直したい"]


def test_new_thread_close(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """新しいスレッドの入力を閉じると「新しいスレッド」に戻し、書きかけは残す（正常系）。"""
    # 準備
    _open(page, spa_comments_preview)
    _panel(page).get_by_role("button", name="新しいスレッド").click()
    _panel(page).get_by_role("textbox", name="新しいスレッド").fill("書きかけの文")
    # 実行
    _panel(page).get_by_role("button", name="新しいスレッドの入力を閉じる").click()
    # 検証
    expect(_panel(page).get_by_role("textbox", name="新しいスレッド")).to_have_count(0)
    _panel(page).get_by_role("button", name="新しいスレッド").click()
    expect(_panel(page).get_by_role("textbox", name="新しいスレッド")).to_have_value("書きかけの文")


def test_pin(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """ピン止めを押すと `aria-pressed` を切り替えてグレーアウトを外し、開き直しても当てる（正常系）。"""
    # 準備
    _open(page, spa_comments_preview)
    pin = _panel(page).get_by_role("button", name="ピン止めする（外側を押しても閉じない）")
    expect(pin).to_have_attribute("aria-pressed", "false")
    expect(page.locator("[data-scrim]")).to_have_count(1)
    # 実行
    pin.click()
    # 検証
    pinned = _panel(page).get_by_role("button", name="ピン止めを外す（外側を押したら閉じる）")
    expect(pinned).to_have_attribute("aria-pressed", "true")
    expect(page.locator("[data-scrim]")).to_have_count(0)
    page.reload()
    expect(_panel(page).get_by_role("button", name="ピン止めを外す（外側を押したら閉じる）")).to_be_visible()


def test_scrim(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """幅 901px 以上はパネル以外をグレーアウトし、幅 900px 以下はグレーアウトせずパネルを画面の幅いっぱいに出す（正常系）。"""
    # 準備・実行
    _open(page, spa_comments_preview)
    # 検証（広い幅）
    expect(page.locator("[data-scrim]")).to_be_visible()
    # 実行（狭い幅）
    page.set_viewport_size(NARROW_SIZE)
    # 検証
    expect(page.locator("[data-scrim]")).to_be_hidden()
    box = _panel(page).bounding_box()
    assert box is not None
    assert box["width"] == NARROW_SIZE["width"]


def test_voice_input_when_service_stopped(
    page: Page,
    make_item: _MakeItem,
    start_voice_preview: _StartVoicePreview,
    unreachable_transcriber_url: str,
) -> None:
    """新しいスレッドの入力で、文字起こしのサービスが起動していないときはマイクのボタンを押せなくし、押すと理由を結果の行に出す（正常系）。"""
    # 準備
    url, _ = start_voice_preview(unreachable_transcriber_url, make_item("D-1"))
    open_spa(page, url, "?tab=decisions&panel=comments")
    # 実行
    _panel(page).get_by_role("button", name="新しいスレッド").click()
    # 検証
    field = page.get_by_role("textbox", name="新しいスレッド")
    assert_mic_blocked_after_click(_panel(page).locator("form").filter(has=field), "[role=status]")
