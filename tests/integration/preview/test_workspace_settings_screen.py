"""画面設計『設定の画面』の結合テスト。"""

from __future__ import annotations

import re

from preview_fixture_types import StartVoicePreview as _StartVoicePreview
from preview_voice_helpers import wait_transcription_status

from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect
from preview_edit_helpers import PENDING_BUTTON, read_edits_file, wait_edits_match, wait_saved_edit
from preview_fixture_types import OpenPreview, WriteReviewPreview
from preview_settings_helpers import SETTINGS_PANEL_OPEN, open_settings
from workspace_fixtures import RECORD_DIR, MakeItem

# 設定の画面
WS = ".pe-ws"

# 設定のキー 1 つの入力欄の外枠
FIELD = f"{WS} .pe-field"

# 一覧の画面
DECISIONS_HASH = "#tab=decisions&view=board"

# 溜めた編集を待つ上限ミリ秒
EDIT_TIMEOUT_MS = 10_000

def _settings(valid_settings: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    """説明つきの設定を返す。"""
    return {**valid_settings, "description": "元の説明", **overrides}


def _open_workspace(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
    **overrides: Any,
) -> tuple[Page, Path]:
    """検討事項 D-1 を持つワークスペースで、設定の画面を開いたページとフォルダを返す。"""
    url, root = write_edit_preview(
        make_item("D-1"),
        settings=_settings(valid_settings, **overrides),
    )
    page = open_preview(url, DECISIONS_HASH)
    open_settings(page)
    page.get_by_role("button", name="設定を編集する").click()
    page.wait_for_selector(WS)
    return page, root


def _commit(page: Page, label: str, value: str) -> None:
    """名前で引いた入力欄に値を入れて離れ、編集が溜まって画面が描き直されるのを待つ。"""
    field = page.get_by_label(label, exact=True)
    field.fill(value)
    field.blur()


def _edit_of(root: Path, key: str) -> dict[str, Any]:
    """edits.yaml に溜めた、設定のキーの編集を返す（溜まるまで待たない）。"""
    return next(
        edit
        for edit in read_edits_file(root)["items"]
        if edit["target"] == "settings" and edit["key"] == key
    )


def _wait_edits(page: Page, count: int) -> None:
    """トップバーの保存待ちの件数が揃うのを待つ。"""
    expect(page.locator(PENDING_BUTTON)).to_have_attribute(
        "aria-label", f"保存待ち（{count} 件）", timeout=EDIT_TIMEOUT_MS
    )


def test_open_and_close(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """表示の設定のパネルの「設定を編集する」で開き、本文の区画を置き換える。見出しへフォーカスを移し、閉じると元の画面に戻る（正常系）。"""
    # 準備・実行
    page, _ = _open_workspace(write_edit_preview, make_item, valid_settings, open_preview)
    # 検証
    assert page.locator(f"{WS} h1").inner_text() == "設定"
    assert page.evaluate("document.activeElement.tagName") == "H1"
    assert page.locator("main#main").is_hidden()
    assert page.locator(SETTINGS_PANEL_OPEN).count() == 0
    # 実行（閉じる）
    page.get_by_role("button", name="閉じる").click()
    # 検証（閉じる）
    expect(page.locator(WS)).to_have_count(0)
    assert page.locator("main#main").is_visible()


def test_groups(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """設定のキーを「話し合い」「関連」「変更履歴」「音声入力」の fieldset に分けて並べる（正常系）。"""
    # 準備・実行
    page, _ = _open_workspace(write_edit_preview, make_item, valid_settings, open_preview)
    # 検証
    assert page.locator(f"{WS} form").get_attribute("aria-label") == "ワークスペースの設定"
    assert page.locator(f"{WS} fieldset legend").all_inner_texts() == [
        "話し合い",
        "関連",
        "変更履歴",
        "音声入力",
    ]
    keys = page.locator(f"{WS} fieldset").evaluate_all(
        "sets => sets.map(set => [...set.querySelectorAll(':scope > .pe-field')].map(f => f.dataset.key))"
    )
    assert keys == [
        ["summary", "description"],
        ["links"],
        ["history_limit"],
        ["transcription.action", "transcription.preset"],
    ]


def test_text_inputs(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """題名は、入力欄を離れたときに保存待ちに溜め、溜めたキーに印を付ける。元の値に戻すと外れる（正常系）。"""
    # 準備
    page, root = _open_workspace(write_edit_preview, make_item, valid_settings, open_preview)
    original = valid_settings["summary"]
    # 実行（題名を直す）
    _commit(page, "題名", "画面の編集")
    _wait_edits(page, 1)
    wait_saved_edit(page, "summary", "画面の編集")
    # 検証
    assert _edit_of(root, "summary")["value"] == "画面の編集"
    assert _edit_of(root, "summary")["before"] == original
    assert page.get_by_label("題名", exact=True).input_value() == "画面の編集"
    summary = page.locator(f"{FIELD}[data-key='summary']")
    assert "is-pending" in summary.get_attribute("class")
    assert summary.locator(".pm.pm-compact").count() == 1
    assert page.locator(f"{FIELD}[data-key='description'] .pm").count() == 0
    # 実行（元の値に戻す）
    _commit(page, "題名", original)
    expect(page.locator(PENDING_BUTTON)).to_have_count(0, timeout=EDIT_TIMEOUT_MS)
    # 検証（元の値に戻す）
    assert read_edits_file(root)["items"] == []
    assert page.locator(f"{FIELD}[data-key='summary'] .pm").count() == 0


def test_description(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """説明は何行も書く欄で、空にして離れると説明を消す編集（値が null）を溜める（正常系）。"""
    # 準備
    page, root = _open_workspace(write_edit_preview, make_item, valid_settings, open_preview)
    area = page.get_by_label("説明", exact=True)
    assert area.evaluate("e => e.tagName") == "TEXTAREA"
    assert area.input_value() == "元の説明"
    # 実行
    _commit(page, "説明", "")
    _wait_edits(page, 1)
    wait_saved_edit(page, "description", None)
    # 検証
    edit = _edit_of(root, "description")
    assert edit["value"] is None
    assert edit["before"] == "元の説明"


def test_history_limit(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """保持する回数は数字だけの入力で、補助文を持つ。整数を書いて離れたときに溜め、1 未満は溜めない（正常系）。"""
    # 準備
    page, root = _open_workspace(
        write_edit_preview, make_item, valid_settings, open_preview, history_limit=20
    )
    field = page.get_by_label("保持する回数", exact=True)
    assert field.get_attribute("inputmode") == "numeric"
    assert page.locator(f"{FIELD}[data-key='history_limit'] .pe-hint").inner_text() == (
        "変更履歴に残す書き換えのまとまりの数"
    )
    # 実行（1 未満）
    _commit(page, "保持する回数", "0")
    page.wait_for_timeout(500)
    # 検証（1 未満）
    assert not (root / RECORD_DIR / "edits.yaml").exists()
    # 実行
    _commit(page, "保持する回数", "50")
    _wait_edits(page, 1)
    wait_saved_edit(page, "history_limit", 50)
    # 検証
    assert _edit_of(root, "history_limit")["value"] == 50


def test_tables(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    open_preview: OpenPreview,
) -> None:
    """関連する場所は 1 行ずつの表で、行の削除と、表の下の「関連する場所を追加」を持つ（正常系）。"""
    # 準備
    page, root = _open_workspace(write_edit_preview, make_item, valid_settings, open_preview)
    assert page.locator(f"{WS} table").count() == 1
    assert page.locator(f"{FIELD}[data-key='links'] table").count() == 1
    # 実行（関連する場所を足す）
    page.get_by_role("button", name="関連する場所を追加").click()
    _wait_edits(page, 1)
    wait_saved_edit(page, "links", [{"title": "", "url": ""}])
    # 検証（関連する場所を足す）
    assert _edit_of(root, "links")["value"] == [{"title": "", "url": ""}]
    _commit(page, "1 行目の表示名", "仕様")
    wait_saved_edit(page, "links", [{"title": "仕様", "url": ""}])
    # 溜めた編集で描き直した画面に表示名が入ってから、次の入力へ進む
    expect(page.get_by_label("1 行目の表示名")).to_have_value("仕様", timeout=EDIT_TIMEOUT_MS)
    _commit(page, "1 行目のURL", "https://example.test/spec")
    wait_saved_edit(page, "links", [{"title": "仕様", "url": "https://example.test/spec"}])
    expect(page.get_by_label("1 行目の表示名")).to_have_value("仕様", timeout=EDIT_TIMEOUT_MS)
    expect(page.get_by_label("1 行目のURL")).to_have_value(
        "https://example.test/spec", timeout=EDIT_TIMEOUT_MS
    )
    assert _edit_of(root, "links")["value"] == [{"title": "仕様", "url": "https://example.test/spec"}]
    # 実行（行を削除する）
    page.get_by_role("button", name="1 行目を削除").last.click()
    page.wait_for_function(
        "() => document.querySelectorAll('.pe-ws [data-key=links] tbody tr').length === 0"
    )
    # 検証（行を削除する）
    assert page.locator(f"{FIELD}[data-key='links'] tbody tr").count() == 0


# 保存待ちの編集に、文字起こしの設定の編集が溜まったか（arg は action と preset）
TRANSCRIPTION_EDIT_MATCH_JS = (
    "(items, arg) => items.some(e => e.key === 'transcription'"
    " && e.value.action === arg.action && e.value.preset === arg.preset)"
)

# 用語集のプリセットの入力の外枠
PRESET_FIELD = f"{WS} .pe-field[data-key='transcription.preset']"


def _open_voice_settings(
    open_preview: OpenPreview,
    start_voice_preview: _StartVoicePreview,
    transcriber_url: str,
    settings: dict[str, Any],
) -> tuple[Page, Path]:
    """文字起こしのサービスの URL を渡して配信し、文字起こしの可否を取得し終えた設定の画面を開いたページとフォルダを返す。"""
    url, root = start_voice_preview(transcriber_url, settings=settings)
    page = open_preview(url, DECISIONS_HASH)
    open_settings(page)
    with wait_transcription_status(page):
        page.get_by_role("button", name="設定を編集する").click()
    page.wait_for_selector(WS)
    return page, root


def test_transcription(
    open_preview: OpenPreview,
    start_voice_preview: _StartVoicePreview,
    start_fake_transcriber: Any,
    valid_settings: dict[str, Any],
) -> None:
    """文字起こし後の挙動と用語集のプリセットを選ぶと、もう一方の値を保った transcription を 1 件溜める。挙動を持たない設定では既定の「レビュー中に追加する」を選び、選択肢は「レビュー中に追加する」「入力欄へ挿入する」「送信する」の順。候補は文字起こしの可否の presets（正常系）。"""
    # 準備
    fake = start_fake_transcriber("done")
    page, root = _open_voice_settings(
        open_preview,
        start_voice_preview,
        fake.url,
        {**valid_settings, "transcription": {"preset": "開発"}},
    )
    preset = page.get_by_label("用語集のプリセット", exact=True)
    # 検証（今の値と候補）
    expect(page.get_by_role("radio", name="レビュー中に追加する")).to_be_checked()
    radios = page.get_by_role("radio", name=re.compile("^(レビュー中に追加する|入力欄へ挿入する|送信する)$"))
    assert [radios.nth(i).get_attribute("value") for i in range(radios.count())] == ["review", "insert", "send"]
    expect(preset).to_have_value("開発")
    expect(preset.locator("option")).to_have_text(["サービスの既定", "一般", "開発"])
    assert "文字起こしの結果を挿入した全文をレビュー中に追加し、送信しません。" in page.inner_text(f"{WS} .pe-field[data-key='transcription.action'] .pe-hint")
    assert page.inner_text(f"{PRESET_FIELD} .pe-hint") == "文字起こしの補正に使用する用語集です。候補は文字起こしのサービスから取得します。"
    # 実行（文字起こし後の挙動）
    page.get_by_role("radio", name="送信").check()
    # 検証
    wait_edits_match(page, TRANSCRIPTION_EDIT_MATCH_JS, {"action": "send", "preset": "開発"})
    # 実行（用語集のプリセット）
    preset.select_option("一般")
    # 検証
    wait_edits_match(page, TRANSCRIPTION_EDIT_MATCH_JS, {"action": "send", "preset": "一般"})
    assert _edit_of(root, "transcription")["value"] == {"action": "send", "preset": "一般"}


def test_transcription_when_service_stopped(
    open_preview: OpenPreview,
    start_voice_preview: _StartVoicePreview,
    unreachable_transcriber_url: str,
    valid_settings: dict[str, Any],
) -> None:
    """文字起こしのサービスが使えないときは、用語集のプリセットを今の値だけにして押せなくし、理由の文を出す。文字起こし後の挙動は書き換えられるまま（正常系）。"""
    # 準備・実行
    page, _ = _open_voice_settings(
        open_preview,
        start_voice_preview,
        unreachable_transcriber_url,
        {**valid_settings, "transcription": {"action": "send", "preset": "開発"}},
    )
    # 検証
    preset = page.get_by_label("用語集のプリセット", exact=True)
    expect(preset).to_be_disabled()
    assert preset.locator("option").all_inner_texts() == ["開発"]
    assert page.inner_text(f"{PRESET_FIELD} .pe-hint") == (
        "文字起こしのサービスが起動していないため、候補を取得できません。サービスを起動してから設定の画面を再度開いてください。"
    )
    expect(page.get_by_role("radio", name="入力欄へ挿入する")).to_be_enabled()
