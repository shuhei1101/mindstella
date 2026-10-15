"""サーバーの配信で端末に残した絞り込みの条件の結合テストが共有する操作と読み取り。"""

from __future__ import annotations

from playwright.sync_api import Page
from preview_fixture_types import MAIN_SELECTOR

__all__ = [
    "read_saved_filters",
    "reload_preview",
    "reopen_preview",
    "seed_saved_filters",
]

# 端末の保存領域に残した個人の上書きのキー
_PREFS_KEY = "mindmap-preview"

# 個人の上書きのうち、画面（記録の表は種類）ごとの絞り込みの条件を読む
_READ_FILTERS_SCRIPT = (
    f"JSON.parse(localStorage.getItem('{_PREFS_KEY}') ?? 'null')?.filters ?? null"
)

# 個人の上書きの絞り込みの条件だけを、渡した値に置き換えて残す（ほかの上書きは変えない）
_SEED_FILTERS_SCRIPT = f"""filters => {{
    const prefs = JSON.parse(localStorage.getItem('{_PREFS_KEY}') ?? '{{}}');
    prefs.filters = filters;
    localStorage.setItem('{_PREFS_KEY}', JSON.stringify(prefs));
}}"""


def read_saved_filters(page: Page) -> dict[str, dict[str, list[str]]] | None:
    """端末に残した画面ごとの絞り込みの条件を読む（個人の上書きが無ければ None）。"""
    return page.evaluate(_READ_FILTERS_SCRIPT)


def seed_saved_filters(page: Page, filters: dict[str, dict[str, list[str]]]) -> None:
    """端末に残す画面ごとの絞り込みの条件を、渡した値に置き換える（開いている画面は変えないので、続けて読み込み直す）。"""
    page.evaluate(_SEED_FILTERS_SCRIPT, filters)


def reload_preview(page: Page) -> Page:
    """プレビューを読み込み直し、本文の領域に中身が入るのを待つ。"""
    page.reload()
    page.wait_for_selector(f"{MAIN_SELECTOR} > *", state="attached")
    return page


def reopen_preview(page: Page, url: str, hash_text: str) -> Page:
    """空のページを挟んで配信の URL をハッシュ付きで開き直し、本文の領域に中身が入るのを待つ（ハッシュだけを替えると読み込み直さずに受けるため）。"""
    page.goto("about:blank")
    page.goto(f"{url}{hash_text}")
    page.wait_for_selector(f"{MAIN_SELECTOR} > *", state="attached")
    return page
