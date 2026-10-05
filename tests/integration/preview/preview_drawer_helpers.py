"""絞り込みのドロワーの結合テストが共有する操作と値（トップバーの絞り込みのボタン・件数のバッジ・ドロワー）。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

__all__ = [
    "ALL_DECISION_STATUSES_HASH",
    "DEFAULT_DECISION_STATUSES",
    "DRAWER",
    "DRAWER_OPEN",
    "FILTER_BADGE",
    "FILTER_BUTTON",
    "badge_text",
    "checked_values",
    "click_value",
    "drawer_groups",
    "drawer_head",
    "open_drawer",
    "value_selector",
]

# トップバーの絞り込みのボタンと、値を選んでいる条件の数のバッジ
FILTER_BUTTON = "[data-act='filter']"
FILTER_BADGE = f"{FILTER_BUTTON} .fbadge"

# 絞り込みのドロワー（開いているときだけ `open` 属性を持つ）
DRAWER = "dialog.drawer"
DRAWER_OPEN = "dialog.drawer[open]"

# 検討事項を開いたときの、状態の条件の値
DEFAULT_DECISION_STATUSES = ["要見直し", "未決定", "未整理", "保留"]

# 検討事項の全ての状態を選ぶハッシュの絞り込み（開いたときの既定に代えて、決定済みなども出す）
ALL_DECISION_STATUSES_HASH = "&f.status=要見直し|未決定|未整理|保留|決定済み|対象外|取り下げ"

# ドロワーの条件の並び（見出し・選んだ数の文言・値ごとの `[値, 件数, チェック]`）を読む
_DRAWER_GROUPS_SCRIPT = """() => [...document.querySelectorAll('dialog.drawer .fd-group')].map((group) => ({
    label: group.querySelector('legend').childNodes[0].textContent,
    sel: group.querySelector('.fd-sel')?.textContent ?? null,
    clear: group.querySelector('.fd-clear') !== null,
    values: [...group.querySelectorAll('.fd-opt')].map((opt) => [
        opt.querySelector('.fd-v').textContent,
        Number(opt.querySelector('.n').textContent),
        opt.querySelector('input').checked,
    ]),
}))"""

# ドロワーの見出しの右の件数と、下端のボタンの文字を読む
_DRAWER_HEAD_SCRIPT = """() => ({
    count: document.querySelector('dialog.drawer .fd-count').textContent,
    foot: [...document.querySelectorAll('dialog.drawer .fd-foot button')].map((b) => b.textContent),
})"""


def open_drawer(page: Page) -> None:
    """トップバーの絞り込みのボタンを押し、ドロワーが開くのを待つ。"""
    page.click(FILTER_BUTTON)
    page.wait_for_selector(DRAWER_OPEN)


def drawer_groups(page: Page) -> list[dict[str, Any]]:
    """ドロワーの条件を並びの順に返す（`label`・`sel`・`clear`・`values`）。"""
    return page.evaluate(_DRAWER_GROUPS_SCRIPT)


def drawer_head(page: Page) -> dict[str, Any]:
    """ドロワーの見出しの右の件数（`count`）と、下端のボタンの文字（`foot`）を返す。"""
    return page.evaluate(_DRAWER_HEAD_SCRIPT)


def badge_text(page: Page) -> str | None:
    """絞り込みのボタンのバッジの数を返す。バッジが無ければ None。"""
    if page.locator(FILTER_BADGE).count() == 0:
        return None
    return page.inner_text(FILTER_BADGE)


def value_selector(key: str, value: str) -> str:
    """条件 `key` の値 `value` の行（ラベル）を指すセレクターを返す。"""
    return f'{DRAWER} label.fd-opt:has(input[data-key="{key}"][value="{value}"])'


def click_value(page: Page, key: str, value: str) -> None:
    """条件 `key` の値 `value` の行を押す。"""
    page.click(value_selector(key, value))


def checked_values(page: Page, key: str) -> list[str]:
    """条件 `key` のチェックの入った値を並びの順に返す。"""
    return page.eval_on_selector_all(
        f'{DRAWER} input[data-key="{key}"]:checked', "inputs => inputs.map(i => i.value)"
    )
