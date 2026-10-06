"""部品設計『既定の保存の確かめ』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 320px にしたときの幅と高さ）
NARROW_SIZE = {"width": 320, "height": 720}

# モーダルが開くのを待つ上限ミリ秒
DIALOG_TIMEOUT_MS = 5_000

# 確かめのモーダル
DIALOG = "dialog.sconfirm"


def _open(open_story: OpenStory, state: str) -> Page:
    """ストーリーを開き、モーダルが `showModal()` で開くのを待つ。"""
    page = open_story(f"preview-settingssaveconfirm--{state}")
    page.wait_for_selector(f"{DIALOG}[open]", timeout=DIALOG_TIMEOUT_MS)
    return page


def _rows(page: Page) -> list[str]:
    """項目の行の文字を上から返す。"""
    return page.locator(f"{DIALOG} .sc-row").all_inner_texts()


def _focused(page: Page) -> str:
    """フォーカスのある要素の文字を返す。"""
    return page.evaluate("document.activeElement?.textContent?.trim() ?? ''")


def test_both_changed(open_story: OpenStory) -> None:
    """2 つの項目を変える。今の既定と保存する値を矢印で並べる。最初のフォーカスは取り消す（正常系）。"""
    # 準備・実行
    page = _open(open_story, "both-changed")
    # 検証
    labelled = page.get_attribute(DIALOG, "aria-labelledby")
    assert page.inner_text(f"#{labelled}") == "ワークスペースの既定を書き換えますか"
    rows = _rows(page)
    assert "星の光" in rows[0]
    assert "星屑" in rows[0]
    assert "メモを表示しない" in rows[1]
    assert "すべて表示" in rows[1]
    assert "変えない" not in page.inner_text(DIALOG)
    assert page.locator(f"{DIALOG} .sc-row svg.icon").count() == 2
    # 変える項目は、今の既定と保存する値を読み上げにだけ残す
    assert page.locator(f"{DIALOG} .sc-row .sr-only").all_text_contents() == [
        "今の既定 ",
        "保存する値 ",
        "今の既定 ",
        "保存する値 ",
    ]
    assert _focused(page) == "取り消す"
    assert page.evaluate(f"document.querySelector('{DIALOG}').matches(':modal')") is True


def test_one_unchanged(open_story: OpenStory) -> None:
    """表示する種類を変えない。今の値に「変えない」の札を付ける（正常系）。"""
    # 準備・実行
    page = _open(open_story, "one-unchanged")
    # 検証
    rows = _rows(page)
    assert "深宇宙" in rows[0]
    assert "グロウ" in rows[0]
    assert "変えない" not in rows[0]
    assert "すべて表示" in rows[1]
    assert "変えない" in rows[1]


def test_busy(open_story: OpenStory) -> None:
    """保存している途中。ボタンを押せなくし、保存するボタンに待つ印を出す。Esc でも閉じない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "busy")
    page.keyboard.press("Escape")
    # 検証
    buttons = page.locator(f"{DIALOG} .cf-row button")
    assert buttons.evaluate_all("items => items.map(b => b.disabled)") == [True, True]
    assert page.locator(f"{DIALOG} button .spinner").count() == 1
    assert "保存しています" in page.inner_text(f"{DIALOG} .cf-row")
    assert page.locator(f"{DIALOG}[open]").count() == 1


def test_error_read_only(open_story: OpenStory) -> None:
    """ワークスペースのフォルダに書き込めず保存できなかった。理由と直し方を出し、もう一度保存できる（正常系）。"""
    # 準備・実行
    page = _open(open_story, "error-read-only")
    # 検証
    alert = page.locator(f"{DIALOG} .sc-error")
    assert alert.get_attribute("role") == "alert"
    assert alert.inner_text() == (
        "保存できませんでした。ワークスペースのフォルダに書き込めません（読み取り専用）。"
        "フォルダに書き込めるようにしてから、もう一度保存してください。"
    )
    assert page.get_by_role("button", name="保存する").is_enabled()


def test_error_offline(open_story: OpenStory) -> None:
    """サーバーが止まっていて保存できなかった。コメントを送れなかったときと同じ直し方を出す（正常系）。"""
    # 準備・実行
    page = _open(open_story, "error-offline")
    # 検証
    assert page.inner_text(f"{DIALOG} .sc-error") == (
        "保存できませんでした。サーバーが止まっています。起動スクリプトで立ち上げ直し、"
        "示された新しい URL で開いてから保存してください。"
    )


def test_narrow(open_story: OpenStory) -> None:
    """幅 320px で外した種類が多い。値を折り返す（正常系）。"""
    # 準備・実行
    page = _open(open_story, "narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_timeout(300)
    # 検証
    box = page.locator(DIALOG).bounding_box()
    assert box is not None
    assert box["x"] >= 0
    assert box["x"] + box["width"] <= NARROW_SIZE["width"]
    assert "メモ" in page.inner_text(f"{DIALOG} .sc-row >> nth=1")
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )
