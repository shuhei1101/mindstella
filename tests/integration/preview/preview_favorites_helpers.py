"""画面のお気に入りの星・星の列・「お気に入りのみ」のチップを確かめる、画面の結合テストの共通の手順。"""

from __future__ import annotations

import json

from playwright.sync_api import Page, expect

# 端末の保存領域のキー（サーバーの配信では末尾に `:{workspace}` を付ける）
PREFS_KEY_JS = "'mindmap-preview' + (location.pathname.split('/')[1] === 'w' ? ':' + decodeURIComponent(location.pathname.split('/')[2]) : '')"


def stored_favorites(page: Page) -> list[str]:
    """端末の保存領域のお気に入りの ID を返す。"""
    prefs = json.loads(page.evaluate(f"localStorage.getItem({PREFS_KEY_JS}) ?? '{{}}'"))
    favorites: list[str] = prefs.get("favorites") or []
    return favorites


def seed_prefs(page: Page, prefs: dict[str, object]) -> None:
    """画面を開く前に、端末の保存領域へ値を 1 回だけ入れる（再読み込みでは入れ直さない）。"""
    page.add_init_script(
        "try { if (!sessionStorage.getItem('favorites-seeded')) {"
        f" localStorage.setItem({PREFS_KEY_JS}, {json.dumps(json.dumps(prefs))});"
        " sessionStorage.setItem('favorites-seeded', '1'); } } catch (e) {}"
    )


def assert_card_star_toggles(page: Page, item_id: str, title: str) -> None:
    """カードの右上の星を押すと登録・解除され、カードは開かない。"""
    star = page.locator(f"[data-card='{item_id}']").get_by_role("button", name=f"{title}をお気に入りに登録")
    expect(star).to_have_attribute("aria-pressed", "false")
    star.click()
    expect(star).to_have_attribute("aria-pressed", "true")
    assert item_id in stored_favorites(page)
    expect(page.get_by_role("complementary", name="詳細")).to_have_count(0)
    star.click()
    expect(star).to_have_attribute("aria-pressed", "false")
    assert item_id not in stored_favorites(page)


def assert_star_column(page: Page, favorite_id: str) -> None:
    """表の一番左の「お気に入り」の列で、登録した行の星を塗り、見出しの昇順・降順でその行を先頭・末尾にする。"""
    header = page.get_by_role("columnheader", name="お気に入り")
    expect(header).to_be_visible()
    first_row = page.locator("tbody tr[data-id]").first
    expect(first_row.locator("td").first.locator("[data-favorite]")).to_have_count(1)
    expect(page.locator(f"tr[data-id='{favorite_id}'] [data-favorite]")).to_have_attribute("aria-pressed", "true")
    ids_js = "() => [...document.querySelectorAll('tbody tr[data-id]')].map((row) => row.dataset.id)"
    header.locator("button[data-sort]").click()
    expect(header).to_have_attribute("aria-sort", "ascending")
    assert page.evaluate(ids_js)[0] == favorite_id
    header.locator("button[data-sort]").click()
    expect(header).to_have_attribute("aria-sort", "descending")
    assert page.evaluate(ids_js)[-1] == favorite_id


def assert_favorites_only_chip(page: Page, favorite_id: str, other_id: str) -> None:
    """「お気に入りだけを表示する」の間は先頭に「お気に入りのみ」のチップを出してお気に入りだけを並べ、× で解除する。"""
    clear = page.get_by_role("button", name="お気に入りのみ の条件を解除")
    expect(clear).to_be_visible()
    expect(page.locator(f"[data-id='{favorite_id}']").first).to_be_visible()
    expect(page.locator(f"[data-id='{other_id}']")).to_have_count(0)
    clear.click()
    expect(clear).to_have_count(0)
    expect(page.locator(f"[data-id='{other_id}']").first).to_be_visible()
