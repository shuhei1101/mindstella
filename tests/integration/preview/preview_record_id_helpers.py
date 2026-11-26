"""記録の文字の中の ID（部品『記録の文字』）を確かめる画面の結合テストが共有する値と関数。"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

__all__ = ["LINKED_TITLE", "TARGET_TITLE", "assert_described", "assert_tip"]

# 記録にある D-1 と記録に無い D-99 を持つタイトル
LINKED_TITLE = "D-1 の見直し（D-99 は除く）"

# タイトルの中の ID が指す D-1 のタイトル
TARGET_TITLE = "保存先の決め方"


def assert_tip(page: Page, title: str = TARGET_TITLE) -> None:
    """ID の項目・スレッドのタイトルを持つツールチップが出ている。"""
    tip = page.locator(".term-tip")
    expect(tip).to_be_visible()
    expect(tip).to_contain_text(title)


def assert_described(page: Page, host: Locator, title: str = TARGET_TITLE) -> None:
    """押す要素の aria-describedby が、ID の項目・スレッドのタイトルを持つ説明を指す。"""
    described = host.get_attribute("aria-describedby")
    assert described is not None
    descriptions = page.locator(", ".join(f"[id='{name}']" for name in described.split()))
    expect(descriptions.filter(has_text=f"{title}（")).to_have_count(1)
