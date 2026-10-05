"""表示の設定の E2E テストが共有する値と、操作・読み取りの関数。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from playwright.sync_api import Page

__all__ = [
    "CONFIRM",
    "CONFIRM_OPEN",
    "DEFAULT_KINDS",
    "ERROR_ALERT",
    "KINDS_WITHOUT_TERMS",
    "SAVE_DEFAULT_BUTTON",
    "SETTINGS_BUTTON",
    "SETTINGS_PANEL",
    "SETTINGS_PANEL_OPEN",
    "checked_kind_count",
    "graph_look",
    "open_in",
    "open_settings",
    "pick_look",
    "read_config",
    "read_prefs",
    "seed_prefs",
    "tab_keys",
    "table_headers",
    "toggle_kind",
]

# 画面が描き終わるまで待つ上限ミリ秒
RENDER_TIMEOUT_MS = 20_000

# トップバーの表示の設定のボタン
SETTINGS_BUTTON = "header.topbar button.settings-btn"

# 表示の設定のパネル（開いているときだけ `open` のクラスを持つ）
SETTINGS_PANEL = "aside.settings-drawer"
SETTINGS_PANEL_OPEN = f"{SETTINGS_PANEL}.open"

# 既定の保存の確かめ（開いているときだけ `open` 属性を持つ）
CONFIRM = "dialog.sconfirm"
CONFIRM_OPEN = "dialog.sconfirm[open]"

# 「ワークスペースの既定にする」のボタン
SAVE_DEFAULT_BUTTON = f"{SETTINGS_PANEL} button:has-text('ワークスペースの既定にする')"

# 保存できなかったときの確かめの中の理由
ERROR_ALERT = f"{CONFIRM} .sc-error"

# 表示する種類の全て（定義の順）
DEFAULT_KINDS = ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]

# 用語集を除いた表示する種類
KINDS_WITHOUT_TERMS = ["decisions", "tasks", "research", "docs", "notes", "logs"]

# 端末の保存領域の個人の上書きを読む
_PREFS_SCRIPT = "JSON.parse(localStorage.getItem('mindmap-preview') ?? 'null')"

# 端末の保存領域に個人の上書きを置く
_SEED_PREFS_SCRIPT = "prefs => localStorage.setItem('mindmap-preview', JSON.stringify(prefs))"

# タブの帯に並ぶ画面の並びを読む
_TABS_SCRIPT = "[...document.querySelectorAll('nav.tabbar a')].map((a) => a.dataset.tab)"

# 表のヘッダーの並びを読む
_HEADERS_SCRIPT = "buttons => buttons.map(b => b.textContent)"


def open_in(page: Page, url: str, hash_text: str = "") -> Page:
    """配信の URL をハッシュ付きで開き、画面が描き終わるまで待つ。別のブラウザのコンテキストのページでも使う。"""
    page.goto(f"{url}{hash_text}")
    page.wait_for_selector("main#main > *", state="attached", timeout=RENDER_TIMEOUT_MS)
    # 文字（Web フォント）の読み込みで行の高さが変わる前に、画面を操作し始めない
    page.evaluate("document.fonts.ready.then(() => true)")
    return page


def open_settings(page: Page) -> None:
    """トップバーの表示の設定のボタンを押して、パネルが開くのを待つ。"""
    page.click(SETTINGS_BUTTON)
    page.wait_for_selector(SETTINGS_PANEL_OPEN)


def pick_look(page: Page, label: str) -> None:
    """表示の設定のパネルで、見た目を名前の行で選ぶ。"""
    page.locator(f"{SETTINGS_PANEL} .st-look", has_text=label).locator("input").click()


def toggle_kind(page: Page, label: str) -> None:
    """表示する種類のチェックを、種類の名前の行で付け外しする。"""
    page.locator(f"{SETTINGS_PANEL} .st-kinds label", has_text=label).locator("input").click()


def checked_kind_count(page: Page) -> int:
    """表示の設定のパネルで、印が付いている表示する種類の数を返す。"""
    return page.locator(f"{SETTINGS_PANEL} .st-kinds input:checked").count()


def read_prefs(page: Page) -> dict[str, Any] | None:
    """端末の保存領域に残した個人の上書きを読む（残していなければ None）。"""
    return page.evaluate(_PREFS_SCRIPT)


def seed_prefs(page: Page, prefs: dict[str, Any]) -> None:
    """端末の保存領域に個人の上書きを置く（置いた後は、画面を読み込み直して効かせる）。"""
    page.evaluate(_SEED_PREFS_SCRIPT, prefs)


def tab_keys(page: Page) -> list[str]:
    """タブの帯に並ぶ画面の並びを返す（つながりは右端）。"""
    return page.evaluate(_TABS_SCRIPT)


def graph_look(page: Page) -> str | None:
    """つながりの画面に渡っている見た目を返す。"""
    return page.get_attribute(".screen.graph", "data-look")


def table_headers(page: Page) -> list[str]:
    """表のヘッダーの名前を並びのまま返す。"""
    return page.eval_on_selector_all("table.grid thead .th-sort", _HEADERS_SCRIPT)


def read_config(root: Path) -> dict[str, Any]:
    """ワークスペースの config.yaml を読む。"""
    return yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
