"""部品設計『差分のミニマップ』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

import re
from itertools import pairwise
from typing import Any

from playwright.sync_api import Page
from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 帯の太さ（px）と、印の最小の長さ（px）
MAP_WIDTH_PX = 20
MARK_MIN_PX = 12

# 位置の比べで許す差（px）
TOLERANCE_PX = 1

# 印ごとに、種類のクラス・読み上げの名前・形（枠の太さ・縞か）・位置と大きさを返す
_MARKS_JS = """() => [...document.querySelectorAll('.df-map .df-map-m')].map((mark) => {
    const shape = getComputedStyle(mark.querySelector('i'));
    const rect = mark.getBoundingClientRect();
    return {
        kind: [...mark.classList].find((name) => /^df-(add|del|chg)$/.test(name)) ?? null,
        label: mark.getAttribute('aria-label'),
        border: shape.borderTopWidth,
        stripes: shape.backgroundImage.startsWith('repeating-linear-gradient'),
        top: rect.top,
        bottom: rect.bottom,
        width: rect.width,
        height: rect.height,
    };
})"""

# 帯の位置と大きさを返す
_MAP_JS = """() => {
    const rect = document.querySelector('.df-map').getBoundingClientRect();
    return { top: rect.top, bottom: rect.bottom, width: rect.width };
}"""

# 見えている範囲の面の背景色を、ドラッグの見た目を付けたときと外したときで返す
_VIEW_FILL_JS = """() => {
    const map = document.querySelector('.df-map');
    const view = document.querySelector('.df-map-view');
    const dragging = getComputedStyle(view).backgroundColor;
    map.classList.remove('is-dragging');
    const idle = getComputedStyle(view).backgroundColor;
    map.classList.add('is-dragging');
    return { dragging, idle };
}"""


def _open(open_story: OpenStory, state: str) -> Page:
    """ストーリーを開き、帯の印を置き終わるまで少し待つ。"""
    page = open_story(f"preview-diffminimap--{state}")
    page.wait_for_timeout(500)
    return page


def _marks(page: Page) -> list[dict[str, Any]]:
    """帯の印を上から、種類・読み上げの名前・形・位置と大きさで返す。"""
    return page.evaluate(_MARKS_JS)


def _alpha(color: str) -> float:
    """`color(srgb r g b / a)` の形の色から、不透明度を返す（無ければ 1）。"""
    matched = re.search(r"/\s*([\d.]+)\)", color)
    return float(matched.group(1)) if matched else 1.0


def _body_width(page: Page) -> float:
    """本文のスクロール領域の幅を返す。"""
    return page.eval_on_selector(".panel-body", "e => e.getBoundingClientRect().width")


def test_kinds(open_story: OpenStory) -> None:
    """足した・消した・変わったの印。足したは塗りつぶし、消したは枠だけの中抜き、変わったは斜めの縞。前に無かったキーは足した、値が変わったキーは変わった。消した塊のすぐ後ろの足した塊は変わった 1 つにまとめる（正常系）。"""
    # 準備・実行
    page = _open(open_story, "kinds")
    marks = _marks(page)
    # 検証（文書の順に、キー 2 つ・足した塊・消した塊・消してすぐ足した塊）
    assert [mark["kind"] for mark in marks] == ["df-add", "df-chg", "df-add", "df-del", "df-chg"]
    assert [mark["label"] for mark in marks] == [
        "足した箇所（1 / 5）",
        "変わった箇所（2 / 5）",
        "足した箇所（3 / 5）",
        "消した箇所（4 / 5）",
        "変わった箇所（5 / 5）",
    ]
    # 色だけでなく形で分ける
    by_kind = {mark["kind"]: mark for mark in marks}
    assert by_kind["df-add"]["border"] == "0px"
    assert by_kind["df-add"]["stripes"] is False
    assert by_kind["df-del"]["border"] == "2px"
    assert by_kind["df-del"]["stripes"] is False
    assert by_kind["df-chg"]["stripes"] is True
    # 印は上から下へ並ぶ
    tops = [mark["top"] for mark in marks]
    assert tops == sorted(tops)
    # 帯は 1 つのタブの止まりにまとめ、見えている範囲の面は読み上げに出さない
    assert page.locator(".df-map .df-map-m[tabindex='0']").count() == 1
    assert page.get_attribute(".df-map-view", "aria-hidden") == "true"
    assert page.get_attribute(".df-map", "role") == "toolbar"


def test_single_mark(open_story: OpenStory) -> None:
    """印が 1 つ。帯を出し、印の長さは最小の 12px（正常系）。"""
    # 準備・実行
    page = _open(open_story, "single-mark")
    marks = _marks(page)
    # 検証
    assert [mark["label"] for mark in marks] == ["足した箇所（1 / 1）"]
    assert abs(marks[0]["height"] - MARK_MIN_PX) <= TOLERANCE_PX
    assert page.locator(".df-map").is_visible()


def test_not_scrollable(open_story: OpenStory) -> None:
    """本文がスクロール領域に収まる。帯と印は出し、見えている範囲の面は出さない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "not-scrollable")
    # 検証
    assert page.locator(".df-map").is_visible()
    assert len(_marks(page)) == 1
    assert page.locator(".df-map-view").is_visible() is False


def test_many_marks(open_story: OpenStory) -> None:
    """印が 30 か所。帯に収まるよう印の最小の長さを詰め（下限 4px）、重なる印は後ろへずらして全て並べる（正常系）。"""
    # 準備・実行
    page = _open(open_story, "many-marks")
    marks = _marks(page)
    band = page.evaluate(_MAP_JS)
    # 検証（30 個とも帯の中に収まり、隣の印と重ならず、押せる長さ 4px 以上を持つ）
    assert len(marks) == 30
    assert all(mark["top"] >= band["top"] - TOLERANCE_PX for mark in marks)
    assert all(mark["bottom"] <= band["bottom"] + TOLERANCE_PX for mark in marks)
    assert all(mark["height"] >= 4 - TOLERANCE_PX for mark in marks)
    assert all(
        later["top"] >= earlier["bottom"] - TOLERANCE_PX for earlier, later in pairwise(marks)
    )


def test_dragging(open_story: OpenStory) -> None:
    """見えている範囲の面をマウスでつかんで下へ動かしている間。面を 1 段濃くし、本文の文を選ばない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "dragging")
    fills = page.evaluate(_VIEW_FILL_JS)
    # 検証（面を 1 段濃くする）
    assert page.locator(".df-map.is-dragging").count() == 1
    assert _alpha(fills["dragging"]) > _alpha(fills["idle"])
    # 本文の文を選ばない
    assert page.evaluate("document.body.classList.contains('df-map-dragging')") is True
    assert page.evaluate("getComputedStyle(document.body).userSelect") == "none"


def test_no_marks(open_story: OpenStory) -> None:
    """差分の表示だが、本文に変わった箇所の印が無い。帯を出さず、本文の幅は帯の無いときと同じ（正常系）。"""
    # 準備・実行
    page = _open(open_story, "no-marks")
    width_without_marks = _body_width(page)
    # 検証（帯は隠れている）
    assert page.locator(".df-map").is_visible() is False
    assert page.locator(".df-map .df-map-m").count() == 0
    assert page.locator(".panel-scroll.has-map").count() == 0
    # 帯を置かない状態の本文の幅と同じ
    page = _open(open_story, "hidden")
    assert width_without_marks == _body_width(page)


def test_hidden(open_story: OpenStory) -> None:
    """差分の表示でないか、表示の設定で差分のミニマップを外した。本文の差分の印があっても帯を出さない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "hidden")
    # 検証
    assert page.locator(".df-map").count() == 0
    assert page.locator(".panel-scroll .panel-body").count() == 1
    assert page.locator(".panel-scroll.has-map").count() == 0
    # 本文の差分の印はある
    assert page.locator(".md ins.df-blk").count() > 0


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。帯の太さと印の押せる的は変えず、本文の幅を帯の分だけ詰める（正常系）。"""
    # 準備（広い幅の本文の幅を控える）
    page = _open(open_story, "kinds")
    wide_body = _body_width(page)
    # 実行
    page = _open(open_story, "narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_timeout(500)
    band = page.evaluate(_MAP_JS)
    marks = _marks(page)
    # 検証（帯の太さと印の幅は変えず、印は押せる長さを保つ）
    assert band["width"] == MAP_WIDTH_PX
    assert all(abs(mark["width"] - MAP_WIDTH_PX) <= TOLERANCE_PX for mark in marks)
    assert all(mark["height"] >= MARK_MIN_PX - TOLERANCE_PX for mark in marks)
    # 本文の幅は広い幅より詰まり、帯の分を除いた幅に収まる
    assert _body_width(page) < wide_body
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )


def test_side_by_side(open_story: OpenStory) -> None:
    """本文を左右に並べている。左の消した塊と右の足した塊が向かい合う箇所は変わった 1 つ、片側だけの塊はその種類の印を、高さの順に並べる（正常系）。"""
    # 準備・実行
    page = _open(open_story, "side-by-side")
    marks = _marks(page)
    # 検証（向かい合う箇所は変わった 1 つ。右だけの足した塊は足した。高さの順）
    assert [mark["kind"] for mark in marks] == ["df-chg", "df-add"]
    assert [mark["label"] for mark in marks] == ["変わった箇所（1 / 2）", "足した箇所（2 / 2）"]
    tops = [mark["top"] for mark in marks]
    assert tops == sorted(tops)
    # 検証（変わったは斜めの縞、足したは塗りつぶし）
    assert marks[0]["stripes"] is True
    assert marks[1]["stripes"] is False
    assert marks[1]["border"] == "0px"
