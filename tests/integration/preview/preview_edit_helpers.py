"""編集・保存待ちの画面の結合テストが共有する値と、操作・読み取りの関数。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from playwright.sync_api import Page
from workspace_fixtures import RECORD_DIR

__all__ = [
    "ADD_BUTTON",
    "DETAIL_PANEL",
    "PENDING_BUTTON",
    "PENDING_PANEL",
    "SAVE_BUTTON",
    "SAVE_PATTERN",
    "open_pending",
    "read_edits_file",
    "read_items_file",
]

# トップバーの保存待ちのボタン
PENDING_BUTTON = "header.topbar button.pending-btn"

# 保存待ちのパネル
PENDING_PANEL = "aside.pending-panel"

# 保存待ちのパネルの「まとめて保存する」
SAVE_BUTTON = f"{PENDING_PANEL} button.pe-save"

# 種類ごとの画面の「項目を追加」
ADD_BUTTON = "button.pe-add"

# 詳細パネル
DETAIL_PANEL = "aside.panel"

# 保存の要求のパターン
SAVE_PATTERN = "**/api/edits/save"


def open_pending(page: Page) -> None:
    """トップバーの保存待ちのボタンを押して、パネルが開くのを待つ。"""
    page.click(PENDING_BUTTON)
    page.wait_for_selector(PENDING_PANEL)


def read_edits_file(root: Path) -> dict[str, Any]:
    """ワークスペースの edits.yaml を読む。"""
    return yaml.safe_load((root / RECORD_DIR / "edits.yaml").read_text(encoding="utf-8"))


def read_items_file(root: Path, file_name: str) -> list[dict[str, Any]]:
    """種類ごとの YAML の項目の並びを読む。"""
    return yaml.safe_load((root / RECORD_DIR / file_name).read_text(encoding="utf-8"))["items"]
