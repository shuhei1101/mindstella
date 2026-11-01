"""画面で項目を編集・追加・削除して保存する E2E テストが共有する値と、操作・読み取りの関数。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from playwright.sync_api import Page, expect
from workspace_fixtures import RECORD_DIR

__all__ = [
    "DETAIL_PANEL",
    "EDIT_TOGGLE",
    "PENDING_BUTTON",
    "PENDING_PANEL",
    "SAVE_BUTTON",
    "SETTLE_MS",
    "TOAST",
    "open_pending",
    "read_edits",
    "read_items",
    "save_pending",
    "wait_pending_count",
]

# 画面の反映や保存が終わるまで待つ上限ミリ秒
SETTLE_MS = 10_000

# トップバーの保存待ちのボタンと、保存待ちのパネル・その中の「まとめて保存する」
PENDING_BUTTON = "header.topbar button.pending-btn"
PENDING_PANEL = "aside.pending-panel"
SAVE_BUTTON = f"{PENDING_PANEL} button.pe-save"

# 詳細パネルと、その見出しの「編集する」
DETAIL_PANEL = "aside.panel:not(.pe-add-panel)"
EDIT_TOGGLE = f"{DETAIL_PANEL} button.pe-edit-toggle"

# まとめて保存できたときの知らせ
TOAST = ".pe-toast"


def wait_pending_count(page: Page, count: int) -> None:
    """トップバーの保存待ちの件数が揃うのを待つ。0 件のときはボタンが無くなるのを待つ。"""
    if count == 0:
        expect(page.locator(PENDING_BUTTON)).to_have_count(0, timeout=SETTLE_MS)
        return
    expect(page.locator(PENDING_BUTTON)).to_have_attribute(
        "aria-label", f"保存待ち（{count} 件）", timeout=SETTLE_MS
    )


def open_pending(page: Page) -> None:
    """トップバーの保存待ちのボタンを押して、パネルが開くのを待つ。"""
    page.click(PENDING_BUTTON)
    page.wait_for_selector(PENDING_PANEL)


def save_pending(page: Page) -> None:
    """保存待ちのパネルの「まとめて保存する」を押して、保存した知らせが出るのを待つ。"""
    page.click(SAVE_BUTTON)
    page.wait_for_selector(TOAST, timeout=SETTLE_MS)


def read_items(root: Path, file_name: str) -> list[dict[str, Any]]:
    """種類ごとの YAML の項目の並びを読む（ファイルが無ければ 0 件）。"""
    path = root / RECORD_DIR / file_name
    if not path.exists():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8"))["items"]


def read_edits(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの edits.yaml に溜まっている編集の並びを読む（ファイルが無ければ 0 件）。"""
    path = root / RECORD_DIR / "edits.yaml"
    if not path.exists():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8"))["items"]
