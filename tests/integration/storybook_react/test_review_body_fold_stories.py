"""部品設計『本文の折りたたみ.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from .storybook_react_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 畳んだときに出す、折り返した後の見た目の行の数
FOLD_LINES = 5

# 開閉のボタンを出さない本文で、測る間の描き直しを待つミリ秒
MEASURE_WAIT_MS = 500

BODY = "[id^=review-body-]"
MORE = "button[data-part=more]"

# 本文の見た目の行の数（高さ ÷ 行の高さ）を返す
BODY_LINES_SCRIPT = """() => {
    const body = document.querySelector('[id^=review-body-]');
    return Math.round(body.getBoundingClientRect().height / parseFloat(getComputedStyle(body).lineHeight));
}"""

# 本文に畳みの切り取りがかかっているか（はみ出しを隠すか、行の数で切る -webkit-line-clamp を使っていないか）
CLAMP_SCRIPT = """() => {
    const style = getComputedStyle(document.querySelector('[id^=review-body-]'));
    return { clamp: style.webkitLineClamp, overflow: style.overflowY };
}"""

# 本文が全文を出しているか（はみ出して隠れた部分が無いか）
SHOWS_ALL_SCRIPT = """() => {
    const body = document.querySelector('[id^=review-body-]');
    return body.scrollHeight <= body.clientHeight + 1;
}"""

# 開閉の矢印の向き（畳んでいる間は下向き、開いている間は上向きに回す角度）
ARROW_ANGLE_SCRIPT = """() => {
    return parseFloat(getComputedStyle(document.querySelector('button[data-part=more] svg')).rotate);
}"""


def _wait_measured(page: Page, hidden: bool) -> None:
    """本文を測り終える（開閉のボタンの出し分けが決まる）まで待つ。"""
    # 測り終えるとボタンが出る。出さない本文は、測る間の描き直しを待ってから無いことを確かめる
    if hidden:
        page.wait_for_selector(BODY)
        page.wait_for_timeout(MEASURE_WAIT_MS)
    else:
        page.wait_for_selector(MORE)


def _lines(page: Page) -> int:
    """本文の見た目の行の数を返す。"""
    return int(page.evaluate(BODY_LINES_SCRIPT))


def test_short(open_story: OpenStory) -> None:
    """5 行以下の本文。畳まず全文を出し、開閉のボタンを出さない（`hidden`）（正常系）。"""
    # 準備・実行
    page = open_story("shared-reviewbodyfold--short")
    _wait_measured(page, hidden=True)
    # 検証
    assert page.locator(MORE).count() == 0
    assert page.eval_on_selector(BODY, "e => e.hasAttribute('data-folded')") is False
    assert _lines(page) == 2
    assert page.inner_text(BODY) == "書き直しを読みました。\n表はこれで分かりやすくなった"


def test_folded_lines(open_story: OpenStory) -> None:
    """改行で 8 行の本文。行の高さの 5 行分までを出してはみ出しを隠し、下向きの印と「続きを読む」を出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-reviewbodyfold--folded-lines")
    _wait_measured(page, hidden=False)
    # 検証
    assert _lines(page) == FOLD_LINES
    assert page.eval_on_selector(BODY, "e => e.hasAttribute('data-folded')") is True
    assert page.evaluate(CLAMP_SCRIPT) == {"clamp": "none", "overflow": "hidden"}
    assert page.evaluate(SHOWS_ALL_SCRIPT) is False
    assert page.inner_text(MORE) == "続きを読む"
    assert page.get_attribute(MORE, "aria-expanded") == "false"
    assert page.get_attribute(MORE, "aria-controls") == "review-body-C-51"
    assert page.get_attribute(MORE, "aria-label") == "項目を指さないコメントの続きを読む"
    assert page.evaluate(ARROW_ANGLE_SCRIPT) == 90
    # 畳んだ部分も DOM に残る（読み上げは飛ばさない）
    assert "変更履歴の時点の並びが分かりにくい" in page.eval_on_selector(BODY, "e => e.textContent")


def test_folded_wrap(open_story: OpenStory) -> None:
    """改行の無い長文。折り返した後の見た目の行で 5 行を超えるので畳まれ、「続きを読む」を出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-reviewbodyfold--folded-wrap")
    _wait_measured(page, hidden=False)
    # 検証
    assert _lines(page) == FOLD_LINES
    assert page.eval_on_selector(BODY, "e => e.hasAttribute('data-folded')") is True
    assert page.inner_text(MORE) == "続きを読む"
    assert page.get_attribute(MORE, "aria-label") == "A-14 へのコメントの続きを読む"


def test_opened(open_story: OpenStory) -> None:
    """開いた本文。全文を出し、上向きの印と「折りたたむ」を出す（`aria-expanded="true"`）（正常系）。"""
    # 準備・実行
    page = open_story("shared-reviewbodyfold--opened")
    _wait_measured(page, hidden=False)
    # 検証
    assert _lines(page) > FOLD_LINES
    assert page.evaluate(SHOWS_ALL_SCRIPT) is True
    assert page.eval_on_selector(BODY, "e => e.hasAttribute('data-folded')") is False
    assert page.inner_text(MORE) == "折りたたむ"
    assert page.get_attribute(MORE, "aria-expanded") == "true"
    assert page.get_attribute(MORE, "aria-label") == "項目を指さないコメントの本文を折りたたむ"
    assert page.evaluate(ARROW_ANGLE_SCRIPT) == -90


def test_narrow(open_story: OpenStory) -> None:
    """台の幅 390px。幅が狭くても見た目の 5 行で畳み、「続きを読む」の文字をボタンの中で折り返さない（正常系）。"""
    # 準備
    page = open_story("shared-reviewbodyfold--narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    _wait_measured(page, hidden=False)
    # 検証
    assert _lines(page) == FOLD_LINES
    assert page.evaluate("document.querySelector('button[data-part=more] span').getClientRects().length") == 1
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_folded_lines_when_keyboard(open_story: OpenStory) -> None:
    """開閉のボタンは Tab で止まり、Enter で本文を開き、フォーカスの輪郭を 2px で示す（正常系）。"""
    # 準備
    page = open_story("shared-reviewbodyfold--folded-lines")
    _wait_measured(page, hidden=False)
    # 実行
    page.keyboard.press("Tab")
    # 検証（フォーカスの輪郭）
    assert page.evaluate("document.activeElement?.matches('button[data-part=more]')") is True
    outline = page.eval_on_selector(MORE, "e => ({width: getComputedStyle(e).outlineWidth, style: getComputedStyle(e).outlineStyle})")
    assert outline == {"width": "2px", "style": "solid"}
    # 実行
    page.keyboard.press("Enter")
    # 検証
    assert page.inner_text(MORE) == "折りたたむ"
    assert _lines(page) > FOLD_LINES
    assert page.evaluate(SHOWS_ALL_SCRIPT) is True


def test_id_link(open_story: OpenStory) -> None:
    """`titles` を渡した本文。記録にある T-14 は項目を開くボタン、対応に無い D-99 は文字のまま出す（正常系）。"""
    # 準備・実行
    page = open_story("shared-reviewbodyfold--id-link")
    _wait_measured(page, hidden=True)
    # 検証
    assert page.get_attribute(f"{BODY} button.idlink", "title") == "移し替えの失敗の扱いを書く"
    assert page.inner_text(f"{BODY} button.idlink") == "T-14"
    assert page.locator(f"{BODY} button.idlink").count() == 1
    assert "D-99" in page.inner_text(BODY)
