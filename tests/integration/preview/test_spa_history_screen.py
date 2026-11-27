"""画面設計『変更履歴.tsx』の結合テスト。"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from playwright.sync_api import Page, expect
from preview_fixture_types import WriteReviewPreview
from preview_spa_helpers import open_spa
from workspace_fixtures import RECORD_DIR


# トップバーの変更履歴のボタン（未読の件数を読み上げ名に持つ）
HISTORY_BUTTON = "header button[aria-label^=変更履歴]"


def test_select_and_clear(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """時点を選ぶと差分の表示になり、「最新」を選ぶと差分の表示をやめる（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions")
    # 実行
    page.locator(HISTORY_BUTTON).click()
    page.get_by_role("dialog", name="変更履歴").locator("button[data-sel='V-2']").click()
    # 検証
    expect(page).to_have_url(re.compile("diff=V-2"))
    # 実行
    page.locator(HISTORY_BUTTON).click()
    page.get_by_role("dialog", name="変更履歴").locator("button[data-sel='']").click()
    # 検証
    expect(page).not_to_have_url(re.compile("diff="))


# ─── 画面設計の要素の確認項目 ───


def test_points_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """時点の一覧を常に出し、最新・まだまとめていない変更・まとまりの新しい順に並べ、未読のまとまりにマーカーを付ける（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions")
    # 実行
    page.locator(HISTORY_BUTTON).click()
    dialog = page.get_by_role("dialog", name="変更履歴")
    rows = dialog.locator("button[data-sel]")
    # 検証
    assert rows.evaluate_all("rows => rows.map((r) => r.dataset.sel)") == ["", "pending", "V-2", "V-1"]
    expect(rows.first).to_contain_text("最新")
    expect(dialog.locator("button[data-sel='V-2']").get_by_text("未読", exact=True)).to_have_count(1)
    expect(dialog.locator("button[data-sel='V-1']").get_by_text("未読", exact=True)).to_have_count(1)


def test_points(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """まとまりの行を押すとモーダルを閉じて差分の表示にし、そのまとまりを既読にする（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions")
    expect(page.locator(HISTORY_BUTTON)).to_have_attribute("aria-label", "変更履歴（未読 2 件）")
    # 実行
    page.locator(HISTORY_BUTTON).click()
    page.get_by_role("dialog", name="変更履歴").locator("button[data-sel='V-2']").click()
    # 検証
    expect(page.get_by_role("dialog", name="変更履歴")).to_have_count(0)
    expect(page).to_have_url(re.compile("diff=V-2"))
    expect(page.locator(HISTORY_BUTTON)).to_have_attribute("aria-label", "変更履歴（過去の差分を表示中）（未読 1 件）")


def test_mark_read_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """サーバーの配信では、一覧の上に未読の件数と「すべて既読にする」を出す（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions")
    # 実行
    page.locator(HISTORY_BUTTON).click()
    dialog = page.get_by_role("dialog", name="変更履歴")
    # 検証
    expect(dialog.get_by_text("未読 2 件", exact=True)).to_be_visible()
    expect(dialog.get_by_role("button", name="すべて既読にする")).to_be_visible()


def test_mark_read_enabled(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """未読のまとまりが無いと「すべて既読にする」を押せない（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions")
    page.locator(HISTORY_BUTTON).click()
    dialog = page.get_by_role("dialog", name="変更履歴")
    expect(dialog.get_by_role("button", name="すべて既読にする")).to_be_enabled()
    # 実行
    dialog.get_by_role("button", name="すべて既読にする").click()
    # 検証
    expect(dialog.get_by_role("button", name="すべて既読にする")).to_be_disabled()
    expect(dialog.get_by_text("未読はありません", exact=True)).to_be_visible()


def test_mark_read(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """「すべて既読にする」で全てのまとまりを既読にし、モーダルを閉じず、選んだ時点を変えない（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions&diff=V-1")
    page.locator(HISTORY_BUTTON).click()
    dialog = page.get_by_role("dialog", name="変更履歴")
    # 実行
    dialog.get_by_role("button", name="すべて既読にする").click()
    # 検証
    expect(dialog).to_be_visible()
    expect(dialog.get_by_text("未読", exact=True)).to_have_count(0)
    expect(page).to_have_url(re.compile("diff=V-1"))
    expect(page.locator(HISTORY_BUTTON)).to_have_attribute("aria-label", "変更履歴（過去の差分を表示中）")


def test_close_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """閉じるを常に出し、押すと時点を変えずに閉じる（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions")
    page.locator(HISTORY_BUTTON).click()
    dialog = page.get_by_role("dialog", name="変更履歴")
    # 実行
    dialog.get_by_role("button", name="変更履歴を閉じる").click()
    # 検証
    expect(dialog).to_have_count(0)
    expect(page).not_to_have_url(re.compile("diff="))

def _mark_external(root: Path) -> None:
    """まとまり V-2 を、外部の変更のまとまり（`by: external`・説明「ほかのセッションの書き込み」）にする。"""
    path = root / RECORD_DIR / "changes.yaml"
    changes = yaml.safe_load(path.read_text(encoding="utf-8"))
    for change_set in changes["sets"]:
        if change_set["id"] == "V-2":
            change_set.update(by="external", summary="ほかのセッションの書き込み")
    path.write_text(yaml.safe_dump(changes, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_points_when_external(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """外部の変更のまとまりは、名前「ほかのセッションの書き込み」の横に「外部の変更」の札を付ける（正常系）。"""
    # 準備
    url, root = write_history_preview()
    _mark_external(root)
    open_spa(page, url, "?tab=decisions")
    # 実行
    page.locator(HISTORY_BUTTON).click()
    dialog = page.get_by_role("dialog", name="変更履歴")
    # 検証
    row = dialog.locator("button[data-sel='V-2']")
    expect(row).to_contain_text("ほかのセッションの書き込み")
    expect(row).to_contain_text("外部の変更")
    assert dialog.get_by_text("外部の変更", exact=True).count() == 1
