"""表示の設定の画面の結合テストが共有する値と、操作・読み取りの関数。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from playwright.sync_api import Page
from workspace_fixtures import RECORD_DIR

__all__ = [
    "CONFIRM",
    "CONFIRM_OPEN",
    "DEFAULT_KINDS",
    "LOOK_SELECT",
    "SETTINGS_BUTTON",
    "SETTINGS_PANEL",
    "SETTINGS_PANEL_OPEN",
    "open_settings",
    "panel_text",
    "pick_look",
    "read_config",
    "read_prefs",
    "tab_keys",
    "toggle_kind",
]

# トップバーの表示の設定のボタン
SETTINGS_BUTTON = "header.topbar button.settings-btn"

# 表示の設定のパネル（開いているときだけ `open` のクラスを持つ）
SETTINGS_PANEL = "aside.settings-drawer"
SETTINGS_PANEL_OPEN = f"{SETTINGS_PANEL}.open"

# ネットワークのキャンバスの右上に重ねる、見た目のドロップダウン
LOOK_SELECT = ".screen.graph .look-pick select"

# 既定の保存の確かめ（開いているときだけ `open` 属性を持つ）
CONFIRM = "dialog.sconfirm"
CONFIRM_OPEN = "dialog.sconfirm[open]"

# 表示する種類の全て（定義の順）
DEFAULT_KINDS = ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]

# 端末の保存領域の個人の上書きを読む
_PREFS_SCRIPT = "JSON.parse(localStorage.getItem('mindmap-preview') ?? 'null')"

# タブの帯に並ぶ画面の並びを読む
_TABS_SCRIPT = "[...document.querySelectorAll('nav.tabbar a')].map((a) => a.dataset.tab)"


def open_settings(page: Page) -> None:
    """トップバーの表示の設定のボタンを押して、パネルが開くのを待つ。"""
    page.click(SETTINGS_BUTTON)
    page.wait_for_selector(SETTINGS_PANEL_OPEN)


def pick_look(page: Page, value: str) -> None:
    """ネットワークの見た目のドロップダウンで、見た目を選ぶ（値は glow・starlight・constellation・deep・dust）。"""
    page.select_option(LOOK_SELECT, value)
    page.wait_for_function(
        "value => document.querySelector('.screen.graph')?.dataset.look === value", arg=value
    )


def read_prefs(page: Page) -> dict[str, Any] | None:
    """端末の保存領域に残した個人の上書きを読む（残していなければ None）。"""
    return page.evaluate(_PREFS_SCRIPT)


def tab_keys(page: Page) -> list[str]:
    """タブの帯に並ぶ画面の並びを返す（ネットワークは右端）。"""
    return page.evaluate(_TABS_SCRIPT)


def panel_text(page: Page) -> str:
    """表示の設定のパネルの文字を返す。"""
    return page.inner_text(SETTINGS_PANEL)


def toggle_kind(page: Page, label: str) -> None:
    """表示する種類のチェックを、種類の名前の行で付け外しする。"""
    page.locator(f"{SETTINGS_PANEL} .st-kinds label", has_text=label).locator("input").click()


def read_config(root: Path) -> dict[str, Any]:
    """ワークスペースの config.yaml を読む。"""
    return yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))
