"""画面設計『全体の検索』の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from preview_fixture_types import OpenPreview, WritePreview, WriteSamplePreview
from workspace_fixtures import MakeItem

# 検索のダイアログ
DIALOG = "dialog.search"


def _result_ids(page: Page) -> list[str]:
    """当たった項目の ID を並びのまま返す。"""
    return page.eval_on_selector_all(f"{DIALOG} .sr-item", "items => items.map(i => i.dataset.id)")


def test_open_by_ctrl_k_and_trigger(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """`Ctrl+K` とトップバーの入口で開き、検索の言葉の欄に入力できる（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    # 実行・検証
    page.keyboard.press("Control+K")
    page.wait_for_selector(f"{DIALOG}[open]")
    assert page.evaluate(f"document.activeElement === document.querySelector('{DIALOG} input')")
    page.keyboard.press("Escape")
    page.wait_for_function(f"!document.querySelector('{DIALOG}')")
    page.click('button[data-act="search"]')
    page.wait_for_selector(f"{DIALOG}[open]")


def test_search_by_id_title_and_body(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """空白で区切った語を全て含む項目を、ID・タイトル・本文から探す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    page.keyboard.press("Control+K")
    page.wait_for_selector(f"{DIALOG}[open]")
    # 実行・検証（ID）
    page.fill(f"{DIALOG} input", "d-3")
    page.wait_for_selector(f"{DIALOG} .sr-item")
    assert _result_ids(page) == ["D-3"]
    # 本文（大文字・小文字を区別しない）
    page.fill(f"{DIALOG} input", "本文の 段落")
    page.wait_for_function(f"document.querySelectorAll('{DIALOG} .sr-item').length === 1")
    assert _result_ids(page) == ["D-3"]
    # 全ての語を含まないものは外れる
    page.fill(f"{DIALOG} input", "本文の 無い語")
    page.wait_for_function(f"document.querySelectorAll('{DIALOG} .sr-item').length === 0")
    assert "該当する項目はありません" in page.inner_text(DIALOG)


def test_open_result(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """結果を押すと、その項目のタブと詳細パネルを開いて検索を閉じる（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    page.keyboard.press("Control+K")
    page.wait_for_selector(f"{DIALOG}[open]")
    page.fill(f"{DIALOG} input", "T-1")
    page.wait_for_selector(f"{DIALOG} .sr-item")
    # 実行
    page.click(f'{DIALOG} .sr-item[data-id="T-1"]')
    # 検証
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "T-1の題"
    assert page.get_attribute('nav.tabbar a[data-tab="tasks"]', "aria-current") == "page"
    assert page.locator(DIALOG).count() == 0


def test_open_result_by_keyboard(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """下の矢印で結果へ移り、上下の矢印で選んで Enter で、その項目を開く（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    page.keyboard.press("Control+K")
    page.wait_for_selector(f"{DIALOG}[open]")
    page.fill(f"{DIALOG} input", "の題")
    page.wait_for_selector(f"{DIALOG} .sr-item")
    ids = _result_ids(page)
    # 実行（入力欄から 1 つ目へ、2 つ目へ、3 つ目へ、2 つ目へ戻って開く）
    for key in ("ArrowDown", "ArrowDown", "ArrowDown", "ArrowUp", "Enter"):
        page.keyboard.press(key)
    # 検証
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title").startswith(f"{ids[1]}の題")
    assert page.locator(DIALOG).count() == 0


def test_close(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """閉じるボタン・Esc・外側の押下で閉じる（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    # 実行・検証
    page.keyboard.press("Control+K")
    page.wait_for_selector(f"{DIALOG}[open]")
    page.click(f'{DIALOG} button[aria-label="検索を閉じる"]')
    page.wait_for_function(f"!document.querySelector('{DIALOG}')")
    page.keyboard.press("Control+K")
    page.wait_for_selector(f"{DIALOG}[open]")
    page.mouse.click(4, 4)
    page.wait_for_function(f"!document.querySelector('{DIALOG}')")


def test_slash_does_not_open(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """`/` では開かない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url)
    # 実行
    page.keyboard.press("/")
    page.wait_for_timeout(300)
    # 検証
    assert page.locator(DIALOG).count() == 0


def test_open_by_ctrl_k_when_typing(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """入力欄で文字を入れている間も `Ctrl+K` で開く。開いている間にもう一度押すと、言葉を選び直す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=map")
    page.fill("input[aria-label='タイトルで強調するキーワード']", "題")
    # 実行・検証（入力中に開く）
    page.keyboard.press("Control+K")
    page.wait_for_selector(f"{DIALOG}[open]")
    # 検索の言葉を入れてから、もう一度押すと選び直す
    page.fill(f"{DIALOG} input", "d-3")
    page.keyboard.press("Control+K")
    assert page.locator(DIALOG).count() == 1
    selected = page.evaluate(
        f"(() => {{ const i = document.querySelector('{DIALOG} input'); return i.value.slice(i.selectionStart, i.selectionEnd); }})()"
    )
    assert selected == "d-3"


def test_trigger_key_hint(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """検索の入口に、キーの案内と `aria-keyshortcuts` を持つ（正常系）。"""
    # 準備・実行
    url = write_sample_preview()
    page = open_preview(url)
    # 検証
    trigger = 'button[data-act="search"]'
    assert page.get_attribute(trigger, "aria-keyshortcuts") == "Control+K Meta+K"
    assert page.inner_text(f"{trigger} kbd") in ("Ctrl+K", "⌘K")


def test_exact_match_first(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """ID かタイトルが言葉と完全に一致する項目は、種類の見出しより上の「完全に一致」に出し、下の種類のまとまりには重ねない。Enter で開くのは完全に一致する項目（正常系）。"""
    # 準備
    url = write_preview(
        make_item("D-1", title="シナリオの依頼の受け方"),
        make_item("G-1", title="シナリオの依頼"),
    )
    page = open_preview(url)
    page.keyboard.press("Control+K")
    page.wait_for_selector(f"{DIALOG}[open]")
    # 実行
    page.fill(f"{DIALOG} input", "シナリオの依頼")
    page.wait_for_selector(f"{DIALOG} .sr-item")
    # 検証
    headings = page.eval_on_selector_all(f"{DIALOG} h3", "h => h.map(x => x.textContent)")
    assert headings == ["完全に一致", "検討事項"]
    assert _result_ids(page) == ["G-1", "D-1"]
    # 完全に一致の結果には、種類を添える
    assert page.inner_text(f'{DIALOG} .sr-item[data-id="G-1"] .sr-kind') == "用語集"
    assert page.locator(f'{DIALOG} .sr-item[data-id="D-1"] .sr-kind').count() == 0
    # 先頭の結果が完全に一致する項目なので、Enter で開く
    page.keyboard.press("Enter")
    page.wait_for_selector("aside.panel.open")
    assert "id=G-1" in page.evaluate("location.hash")


def test_exact_match_by_id(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """ID の完全一致は大文字・小文字を区別せず、ID が前方一致するだけの項目は重ねない。ID は折り返さない（正常系）。"""
    # 準備
    items = [make_item("G-1"), make_item("G-12")]
    url = write_preview(*items)
    page = open_preview(url)
    page.keyboard.press("Control+K")
    page.wait_for_selector(f"{DIALOG}[open]")
    # 実行
    page.fill(f"{DIALOG} input", "g-1")
    page.wait_for_selector(f"{DIALOG} .sr-item")
    # 検証
    headings = page.eval_on_selector_all(f"{DIALOG} h3", "h => h.map(x => x.textContent)")
    assert headings == ["完全に一致", "用語集"]
    assert _result_ids(page) == ["G-1", "G-12"]
    white_space = page.eval_on_selector(
        f'{DIALOG} .sr-item[data-id="G-1"] > .mono', "e => getComputedStyle(e).whiteSpace"
    )
    assert white_space == "nowrap"
