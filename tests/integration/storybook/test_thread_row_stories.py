"""部品設計『スレッドの行』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 要約を出す行数の上限（超えたら末尾を省く）
TITLE_MAX_LINES = 2

# 行の 1 行目の題・2 行目・タグの札
STATE = "li.th-row .th-state"
TITLE = "li.th-row .th-title"
LINE2 = "li.th-row .th-line2"
TAGS = "li.th-row .th-tags button.th-tag"


def test_replied(open_story: OpenStory) -> None:
    """オープンで AI が返信した。1 行目に状態の札と要約、2 行目に向けた項目の ID・最後の書き手・日時、行の下にタグを出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadrow--replied")
    # 検証
    assert page.inner_text(STATE) == "オープン"
    assert page.inner_text(TITLE) == "D-12 の失敗時の扱いの相談。案 B（写しから戻す）で決まった"
    assert page.inner_text(f"{LINE2} .mono") == "D-12"
    assert page.inner_text(f"{LINE2} .th-author") == "AI"
    assert page.get_attribute(f"{LINE2} time", "datetime") == "2026-10-12T01:24:00+00:00"
    assert page.inner_text(TAGS) == "画面"
    assert page.get_attribute(TAGS, "aria-label") == "タグ「画面」で絞る"
    assert page.get_attribute(TAGS, "aria-pressed") == "false"
    assert page.locator(f"{LINE2} .th-pending").count() == 0


def test_pending_reply(open_story: OpenStory) -> None:
    """レビュー中の返信を持つ。2 行目の末尾に破線の枠・鉛筆の印・「レビュー中」の印を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadrow--pending-reply")
    # 検証
    assert page.inner_text(f"{LINE2} .th-pending") == "レビュー中"
    assert page.locator(f"{LINE2} .th-pending svg.icon").count() == 1
    assert page.eval_on_selector(f"{LINE2} .th-pending", "e => getComputedStyle(e).borderTopStyle") == "dashed"


def test_asking(open_story: OpenStory) -> None:
    """AI が立てたスレッド（利用者の返事待ち）。最後の書き手は「AI」（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadrow--asking")
    # 検証
    assert page.inner_text(STATE) == "オープン"
    assert page.inner_text(f"{LINE2} .th-author") == "AI"
    assert page.inner_text(f"{LINE2} .mono") == "D-16"


def test_no_summary(open_story: OpenStory) -> None:
    """要約がまだ無く、最後の書き手が利用者。題は最初の書き込みの 1 行目を太さを落として出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadrow--no-summary")
    # 検証
    assert page.inner_text(TITLE).startswith("A-1 の背景の節が長いので")
    assert "head" in (page.get_attribute(TITLE, "class") or "").split()
    assert page.inner_text(f"{LINE2} .th-author") == "あなた"


def test_pending_new_to_item(open_story: OpenStory) -> None:
    """まだ送っていない、項目へ向けた新しいスレッド。状態の札の代わりに鉛筆の印と「レビュー中」の札、行の枠を破線にする。タグは出さない（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadrow--pending-new-to-item")
    # 検証
    assert page.inner_text(STATE) == "レビュー中"
    assert page.locator(f"{STATE} svg.icon").count() == 1
    assert page.inner_text(TITLE) == "写しは git のコミットで取るほうが戻しやすいと思う"
    assert page.inner_text(f"{LINE2} .th-author") == "あなた"
    assert page.inner_text(f"{LINE2} .mono") == "D-5"
    assert page.get_attribute("li.th-row", "data-pending") == "C-41"
    assert page.locator(TAGS).count() == 0
    assert page.eval_on_selector("li.th-row", "e => getComputedStyle(e).borderTopStyle") == "dashed"


def test_pending_new_free(open_story: OpenStory) -> None:
    """まだ送っていない、項目を指さない新しいスレッド。2 行目に ID を出さない（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadrow--pending-new-free")
    # 検証
    assert page.inner_text(STATE) == "レビュー中"
    assert page.locator(f"{LINE2} .mono").count() == 0
    assert page.inner_text(f"{LINE2} .th-author") == "あなた"


def test_closed(open_story: OpenStory) -> None:
    """クローズ。状態の札をチェックの印と「クローズ」にし、薄い文字で出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadrow--closed")
    # 検証
    assert page.inner_text(STATE) == "クローズ"
    assert "closed" in (page.get_attribute(STATE, "class") or "").split()
    assert page.locator(f"{STATE} svg.icon").count() == 1


def test_long(open_story: OpenStory) -> None:
    """長い要約・タグが 2 つ・項目を指さない。要約は 2 行で末尾を省き、2 行目に ID を出さない（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadrow--long")
    # 検証
    assert page.locator(TAGS).count() == 2
    assert page.locator(f"{LINE2} .mono").count() == 0
    sizes = page.eval_on_selector(
        TITLE,
        "e => ({ clamp: getComputedStyle(e).webkitLineClamp, overflow: getComputedStyle(e).overflow })",
    )
    assert sizes == {"clamp": str(TITLE_MAX_LINES), "overflow": "hidden"}


def test_tagged(open_story: OpenStory) -> None:
    """タグ「画面」で絞っている。そのタグの札を押した状態として読み上げる（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadrow--tagged")
    # 検証
    pressed = page.locator("li.th-row .th-tags button.th-tag[aria-pressed='true']")
    assert pressed.count() == 1
    assert pressed.inner_text() == "画面"
    assert page.locator("li.th-row .th-tags button.th-tag[aria-pressed='false']").inner_text() == "調査"


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。2 行目の値は折り返さず、タグは行の下で折り返す（正常系）。"""
    # 準備
    page = open_story("preview-threadrow--narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    line2 = page.locator(LINE2).bounding_box()
    row = page.locator("li.th-row").bounding_box()
    tag = page.locator(TAGS).first.bounding_box()
    assert line2 is not None
    assert row is not None
    assert tag is not None
    assert row["width"] <= 390
    assert tag["y"] >= line2["y"] + line2["height"] - 1
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
