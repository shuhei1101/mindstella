"""画面設計『変更履歴.tsx』の結合テスト。"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from playwright.sync_api import Page, expect
from preview_fixture_types import WriteReviewPreview
from preview_spa_helpers import open_spa
from workspace_fixtures import RECORD_DIR


def test_select_and_clear(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """時点を選ぶと差分の表示になり、札の解除で戻す（正常系）。"""
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions")
    page.get_by_role("button", name="変更履歴").click()
    page.get_by_role("dialog").get_by_role("button").filter(has_text="前回開いてから").click()
    expect(page).to_have_url(re.compile("diff=since"))
    open_spa(page, url, "?tab=decisions&diff=V-2&id=D-1")
    expect(page.get_by_role("complementary", name="詳細")).to_contain_text("新しい段落を足しました")


# ─── 画面設計の要素の確認項目 ───


def test_points_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """時点の一覧を常に出し、差分を出さない・まだまとめていない変更・前回開いてから・まとまりの新しい順に並べる（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions")
    # 実行
    page.get_by_role("button", name="変更履歴").click()
    rows = page.get_by_role("dialog", name="変更履歴").locator("button[data-sel]")
    # 検証
    assert rows.evaluate_all("rows => rows.map((r) => r.dataset.sel)") == ["", "pending", "since", "V-2", "V-1"]
    expect(rows.first).to_contain_text("差分を出さない（今の内容）")


def test_close_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """閉じるを常に出し、押すと時点を変えずに閉じる（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions")
    page.get_by_role("button", name="変更履歴").click()
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
    page.get_by_role("button", name="変更履歴").click()
    dialog = page.get_by_role("dialog", name="変更履歴")
    # 検証
    row = dialog.locator("button[data-sel='V-2']")
    expect(row).to_contain_text("ほかのセッションの書き込み")
    expect(row).to_contain_text("外部の変更")
    assert dialog.get_by_text("外部の変更", exact=True).count() == 1
