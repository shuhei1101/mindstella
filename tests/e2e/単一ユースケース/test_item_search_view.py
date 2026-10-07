"""項目を検索する（全体の検索で ID・タイトル・本文から探し、結果からその項目を開く）の E2E テスト。"""

from __future__ import annotations

from typing import Any

from preview_helpers import OpenPreview, ServePreview
from workspace_fixtures import MakeItem

# 検索のダイアログ
DIALOG = "dialog.search"


def test_normal(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """`/` では開かず、Ctrl+K で開いて、タイトルと本文の語で探し、結果の資料を押すと、資料のタブと詳細パネルを開く（正常系）。"""
    # 準備
    url = serve_preview(
        make_item("D-2", title="保存先を決める"),
        make_item("A-1", title="仕様の資料"),
        make_item("T-1"),
        settings=valid_settings,
        bodies={"A-1.md": "保存先は利用者のフォルダにする\n"},
    )
    page = open_preview(url)
    hash_before = page.evaluate("location.hash")
    # 実行（/ では開かず、Ctrl+K で開く）
    page.keyboard.press("/")
    page.wait_for_timeout(300)
    slash_opened = page.locator(DIALOG).count()
    page.keyboard.press("Control+K")
    page.wait_for_selector(f"{DIALOG}[open]")
    focused = page.evaluate(f"document.activeElement === document.querySelector('{DIALOG} input')")
    page.fill(f"{DIALOG} input", "保存先")
    page.wait_for_selector(f"{DIALOG} .sr-item")
    # 検証
    assert slash_opened == 0
    assert page.evaluate("location.hash") == hash_before
    assert focused is True
    ids = page.eval_on_selector_all(f"{DIALOG} .sr-item", "items => items.map(i => i.dataset.id)")
    assert sorted(ids) == ["A-1", "D-2"]
    page.click(f'{DIALOG} .sr-item[data-id="A-1"]')
    page.wait_for_selector("aside.panel.open")
    assert page.locator(DIALOG).count() == 0
    assert page.get_attribute('nav.tabbar a[data-tab="docs"]', "aria-current") == "page"
    assert page.inner_text("aside.panel .d-title") == "仕様の資料"
    hash_text = page.evaluate("location.hash")
    assert "tab=docs" in hash_text
    assert "id=A-1" in hash_text


def test_normal_when_no_match(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """どの項目にも合わない語では、該当なしを出し、Esc で開く前の画面のままに戻る（正常系）。"""
    # 準備
    url = serve_preview(make_item("D-1"), make_item("T-1"), settings=valid_settings)
    page = open_preview(url)
    hash_before = page.evaluate("location.hash")
    # 実行
    page.click('button[data-act="search"]')
    page.wait_for_selector(f"{DIALOG}[open]")
    page.fill(f"{DIALOG} input", "存在しない語")
    page.wait_for_selector(f"{DIALOG} .no-match")
    # 検証
    assert (
        page.inner_text(f"{DIALOG} .no-match")
        == "該当する項目はありません。別の条件を試してください。"
    )
    page.keyboard.press("Escape")
    page.wait_for_function(f"!document.querySelector('{DIALOG}')")
    assert page.get_attribute('nav.tabbar a[data-tab="overview"]', "aria-current") == "page"
    assert page.evaluate("location.hash") == hash_before


def test_normal_when_exact_match(
    serve_preview: ServePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """入力欄にフォーカスしたままでも Ctrl+K で開き、ID かタイトルが言葉と完全に一致する項目を種類の見出しより上に出し、Enter で開く（正常系）。"""
    # 準備
    url = serve_preview(
        make_item("G-1", title="シナリオの依頼"),
        make_item("D-1", title="シナリオの依頼の受け方"),
        make_item("A-1", title="仕様の資料"),
        settings=valid_settings,
        bodies={"A-1.md": "シナリオの依頼は、受け方を先に決める\n"},
    )
    page = open_preview(url, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map button.n-item")
    # 実行（検討事項のマップのキーワードの入力欄にフォーカスしたまま Ctrl+K を押す）
    page.focus("input[aria-label='タイトルで強調するキーワード']")
    page.keyboard.press("Control+K")
    page.wait_for_selector(f"{DIALOG}[open]")
    # 末尾に空白を付けて入れても、前後の空白を区別せず完全に一致する
    page.fill(f"{DIALOG} input", "シナリオの依頼 ")
    page.wait_for_selector(f"{DIALOG} .sr-item")
    # 検証
    headings = page.eval_on_selector_all(f"{DIALOG} h3", "h => h.map(x => x.textContent)")
    ids = page.eval_on_selector_all(f"{DIALOG} .sr-item", "items => items.map(i => i.dataset.id)")
    assert headings == ["完全に一致", "検討事項", "資料"]
    # G-1 が一番上で、その下の用語集のまとまりには重ねて出ない。D-1・A-1 はそれぞれの種類の見出しの下にある
    assert ids == ["G-1", "D-1", "A-1"]
    page.keyboard.press("Enter")
    page.wait_for_selector("aside.panel.open")
    assert page.locator(DIALOG).count() == 0
    assert page.get_attribute('nav.tabbar a[data-tab="terms"]', "aria-current") == "page"
    assert "id=G-1" in page.evaluate("location.hash")
