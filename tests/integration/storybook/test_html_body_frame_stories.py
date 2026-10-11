"""部品設計『HTMLの本文の枠』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory
from storybook_frame_helpers import (
    FRAME_SELECTOR,
    FRAME_SETTLE_MS,
    frame_fit,
    frame_of,
    wait_frame_rendered,
)

# 描く前の枠の高さ
LOADING_HEIGHT = "120px"

# 描く前の枠の高さ（px の数値）
LOADING_HEIGHT_PX = 120

# 幅の狭い画面の幅と高さ
NARROW_VIEWPORT = {"width": 390, "height": 844}

# 枠の中の文書が横にはみ出していないかを返す
OVERFLOWS_X_SCRIPT = """() => {
    const doc = document.querySelector('iframe.html-frame').contentDocument.documentElement;
    return doc.scrollWidth > doc.clientWidth;
}"""

# 差分の印を付けた要素の本文・印の種類・輪郭の線の種類を返す
MARKS_SCRIPT = """() => [...document.querySelector('iframe.html-frame').contentDocument.querySelectorAll('p')].map((p) => [
    p.textContent,
    p.getAttribute('data-df'),
    getComputedStyle(p).outlineStyle,
])"""

# 枠を 2 つ作り、選んだ文を知らせる受け手が呼ばれた回数を返す（selectable の真偽で比べる）
SELECT_NOTICE_SCRIPT = """async ([selectable, source]) => {
    let calls = 0;
    const frame = MindmapPreview.htmlBodyFrame({ source, selectable, on: { select: () => { calls += 1; } } });
    document.body.append(frame);
    await new Promise((resolve) => frame.addEventListener('load', resolve, { once: true }));
    const doc = frame.contentDocument;
    const range = doc.createRange();
    range.selectNodeContents(doc.querySelector('p'));
    const selection = doc.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    doc.dispatchEvent(new Event('pointerup'));
    return calls;
}"""


def test_rendered(open_story: OpenStory) -> None:
    """見出し・段落・表・図を描き、枠の高さが中身に合って、枠の中にスクロールの帯が出ない（正常系）。"""
    # 準備・実行
    page = open_story("preview-htmlbodyframe--rendered")
    wait_frame_rendered(page)
    frame = frame_of(page)
    # 検証
    assert page.get_attribute(FRAME_SELECTOR, "sandbox") == "allow-same-origin"
    assert frame.locator("h1").inner_text() == "画面の流れ"
    assert frame.locator("table").count() == 1
    assert frame.locator("svg").count() == 1
    fit = frame_fit(page)
    assert fit["bottom"] <= fit["height"]
    assert fit["later_height"] == fit["height"]
    assert frame.evaluate("document.documentElement.style.overflowY") == "hidden"
    # 地は白で、資料の色のまま
    assert page.eval_on_selector(FRAME_SELECTOR, "e => getComputedStyle(e).backgroundColor") == "rgb(255, 255, 255)"


def test_style_isolated(open_story: OpenStory) -> None:
    """本文の `<style>` が `*`・`body`・`p` を塗っても、枠の外の見出し・段落は変わらない（正常系）。"""
    # 準備・実行
    page = open_story("preview-htmlbodyframe--style-isolated")
    wait_frame_rendered(page)
    # 検証
    outside = page.evaluate(
        """() => {
            const p = document.querySelector('#storybook-root > div > p');
            const h2 = document.querySelector('#storybook-root > div > h2');
            const style = getComputedStyle(p);
            return {
                color: style.color,
                bodyColor: getComputedStyle(document.body).color,
                background: style.backgroundColor,
                pMargin: style.marginTop,
                h2Margin: getComputedStyle(h2).marginTop,
            };
        }"""
    )
    assert outside["color"] == outside["bodyColor"]
    assert outside["background"] == "rgba(0, 0, 0, 0)"
    assert outside["pMargin"] != "40px"
    assert outside["h2Margin"] != "40px"
    # 枠の中では本文の CSS が効く
    inside = frame_of(page).eval_on_selector("p", "e => getComputedStyle(e).color")
    assert inside == "rgb(255, 0, 0)"


def test_loading(open_story: OpenStory) -> None:
    """描く前の枠は 120px の高さを取り、まだ描き終えていない（正常系）。"""
    # 準備・実行
    page = open_story("preview-htmlbodyframe--loading")
    # 検証
    assert page.locator(FRAME_SELECTOR).count() == 1
    assert page.eval_on_selector(FRAME_SELECTOR, "e => getComputedStyle(e).height") == LOADING_HEIGHT
    assert page.locator(f"{FRAME_SELECTOR}[data-rendered]").count() == 0


def test_with_scripts(open_story: OpenStory) -> None:
    """スクリプト・`onerror` の画像・`onclick` のボタンを持つ本文は、見出し・段落を描き、ボタンを押しても何も起きない（正常系）。"""
    # 準備
    page = open_story("preview-htmlbodyframe--with-scripts")
    wait_frame_rendered(page)
    frame = frame_of(page)
    # 実行
    frame.click("button")
    page.wait_for_timeout(FRAME_SETTLE_MS)
    # 検証
    assert frame.locator("h1").inner_text() == "保存のボタンの見本"
    assert frame.locator("p").inner_text() == "下のボタンを押しても何も起きません。"
    body_text = frame.inner_text("body")
    assert "動きました" not in body_text


def test_code_block(open_story: OpenStory) -> None:
    """`html` のコードブロックは、枠の中で選んでも「選び終えた」を知らせず、短い本文では枠が縮む（正常系）。"""
    # 準備・実行
    page = open_story("preview-htmlbodyframe--code-block")
    wait_frame_rendered(page)
    # 検証
    assert page.get_attribute(FRAME_SELECTOR, "title") == "html のコードブロック"
    assert frame_of(page).locator("p").inner_text() == "コードブロックの HTML"
    # 描く前の 120px より短い本文なので、枠が縮み、中身が切れず、伸び続けない
    fit = frame_fit(page)
    assert fit["height"] < LOADING_HEIGHT_PX
    assert fit["bottom"] <= fit["height"]
    assert fit["later_height"] == fit["height"]
    source = '<p data-line="1">選ぶ文</p>'
    assert page.evaluate(SELECT_NOTICE_SCRIPT, [False, source]) == 0
    # 選べる枠なら、同じ操作で知らせる
    assert page.evaluate(SELECT_NOTICE_SCRIPT, [True, source]) >= 1


def test_diff_marks(open_story: OpenStory) -> None:
    """変えた段落に破線、足した段落に実線の印を付け、ほかの段落には付けない（正常系）。"""
    # 準備・実行
    page = open_story("preview-htmlbodyframe--diff-marks")
    wait_frame_rendered(page)
    # 検証（段落の本文・印の種類・輪郭の線）
    marks = page.evaluate(MARKS_SCRIPT)
    assert [mark[0] for mark in marks] == [
        "一つ目の段落",
        "変えた二つ目の段落",
        "三つ目の段落",
        "足した四つ目の段落",
    ]
    assert [mark[1] for mark in marks] == [None, "chg", None, "add"]
    assert [mark[2] for mark in marks] == ["none", "dashed", "none", "solid"]


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px でも、本文の図・表が枠の幅に収まる（正常系）。"""
    # 準備
    page = open_story("preview-htmlbodyframe--narrow")
    page.set_viewport_size(NARROW_VIEWPORT)
    page.wait_for_function("innerWidth === 390")
    wait_frame_rendered(page)
    # 検証
    assert page.evaluate(OVERFLOWS_X_SCRIPT) is False
    fit = frame_fit(page)
    assert fit["bottom"] <= fit["height"]
    assert fit["later_height"] == fit["height"]


def test_viewport_relative(open_story: OpenStory) -> None:
    """本文が枠の高さを基準にする CSS（`100%`・`vh`）を持っても、枠は伸び続けず、中身が切れない（正常系）。"""
    # 準備・実行
    page = open_story("preview-htmlbodyframe--viewport-relative")
    wait_frame_rendered(page)
    # 検証
    fit = frame_fit(page)
    assert fit["bottom"] <= fit["height"]
    assert fit["later_height"] == fit["height"]
