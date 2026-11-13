"""画面設計『ネットワーク.tsx』（キャンバスは項目 ID `graph-canvas`）の結合テスト。"""

from __future__ import annotations

import re
from typing import Any

from playwright.sync_api import Page, ViewportSize, expect
from preview_fixture_types import WriteReviewPreview, WriteSamplePreview
from preview_network_helpers import (
    blank_point,
    canvas_center,
    canvas_hash,
    changed_pixels,
    click_at,
    install_key_spy,
    install_status_mark_spy,
    key_draws,
    remember_pixels,
    settle,
    status_marks,
)
from preview_spa_helpers import open_spa

# キャンバスに描かれた画素のうち、背景以外が 1 つでもあるかを調べる
HAS_DRAWING_SCRIPT = """() => {
    const canvas = document.getElementById('graph-canvas');
    const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    for (let i = 3; i < data.length; i += 4) if (data[i] !== 0) return true;
    return false;
}"""

# キャンバスに重ねる層（キャンバスの次の要素）で、見せている名前の横の印があるか
HAS_VISIBLE_MARK_SCRIPT = (
    "[...document.getElementById('graph-canvas').nextElementSibling.children]"
    ".some((mark) => mark.style.visibility !== 'hidden')"
)

# キャンバスに重ねる層で見せている名前の横の印と、キャンバスの外形を返す
VISIBLE_MARKS_SCRIPT = """() => {
    const canvas = document.getElementById('graph-canvas');
    const box = canvas.getBoundingClientRect();
    const marks = [...canvas.nextElementSibling.children].filter((mark) => mark.style.visibility !== 'hidden').map((mark) => {
        const rect = mark.getBoundingClientRect();
        return {left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom};
    });
    return {canvas: {left: box.left, top: box.top, right: box.right, bottom: box.bottom}, marks};
}"""

# ページ全体の縦・横のはみ出しと、キャンバスの下端から窓の下端までの隙間を返す
REGION_SCRIPT = """() => {
    const scroller = document.scrollingElement;
    const canvas = document.getElementById('graph-canvas').getBoundingClientRect();
    return {
        overflowY: scroller.scrollHeight - innerHeight,
        overflowX: scroller.scrollWidth - innerWidth,
        canvasBottomGap: Math.round(innerHeight - canvas.bottom),
    };
}"""

# 詳細パネル
DETAIL = 'aside[aria-label="詳細"]'

# 絞り込みの条件に合う項目が無いときに出す文
NO_MATCH_TEXT = "表示する項目はありません。"

# 鍵を描く領域（キャンバスの中心まわり）で、鍵の有無を区別できる違う画素の数の下限
KEY_PIXELS_AT_LEAST = 30

# 同じ絵と見なす、違う画素の数の上限
UNCHANGED_AT_MOST = 20

# 状態の印・鍵を数える前に待つミリ秒（玉が広がり、印の画像が読み込まれるまで）
MARK_WAIT_MS = 3_000

# 名前の横の印が出るまで待つ上限ミリ秒
MARK_TIMEOUT_MS = 15_000

# 幅 900px 以下（ロックしない幅）の画面の大きさ
NARROW: ViewportSize = {"width": 800, "height": 700}


def _open_still(page: Page, url: str, search: str) -> None:
    """動きを減らす設定で項目を開いたネットワークを、マウスを余白に置いたまま静止するまで待つ。"""
    page.emulate_media(reduced_motion="reduce")
    open_spa(page, url, search)
    page.wait_for_selector(DETAIL)
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    page.mouse.move(*blank_point(page))
    settle(page)


def _press(page: Page, x: float, y: float) -> None:
    """玉（か余白）を押し、マウスを余白へ戻して、画が静止するまで待つ。"""
    click_at(page, x, y)
    page.mouse.move(*blank_point(page))
    settle(page)


def _search(page: Page) -> str:
    """URL の search を、値を戻して返す。"""
    value: str = page.evaluate("decodeURIComponent(location.search)")
    return value


def test_canvas(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """3D のキャンバスに項目と関連を描き、タブの帯のネットワークの入口を選んだ状態で出す（正常系）。"""
    # 準備
    url = write_sample_preview()
    # 実行
    open_spa(page, url, "?tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    # 検証
    assert page.get_attribute("#graph-canvas", "role") == "img"
    assert "L キーで、詳細を開いている項目をロック・解除" in str(page.get_attribute("#graph-canvas", "aria-label"))
    assert page.get_attribute('nav[aria-label="項目の種類"] a[aria-current="page"]', "data-tab") == "graph"


def test_canvas_when_item(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """`id` の項目を選んだ項目として開き、注目しているときだけ起点とつながる項目に状態の印を描く（正常系）。"""
    # 準備
    install_status_mark_spy(page)
    url = write_sample_preview()
    open_spa(page, url, "?tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    page.wait_for_timeout(MARK_WAIT_MS)
    idle = status_marks(page)
    # 実行
    open_spa(page, url, "?tab=graph&id=D-2")
    page.wait_for_selector(DETAIL)
    page.wait_for_timeout(MARK_WAIT_MS)
    focused = status_marks(page)
    # 検証
    assert idle == []
    assert len(focused) >= 1
    assert all(mark["width"] == mark["height"] > 0 for mark in focused)
    expect(page.locator(DETAIL)).to_contain_text("D-2の題")


def test_chips(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """選んでいる条件をチップで並べ、× で解除すると URL の `f.{列}` を外す（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url, "?tab=graph&f.type=%E6%A4%9C%E8%A8%8E%E4%BA%8B%E9%A0%85")
    chip = page.get_by_role("button", name="種類: 検討事項 の条件を解除")
    expect(chip).to_be_visible()
    # 実行
    chip.click()
    # 検証
    page.wait_for_url("**/spa/?tab=graph")
    expect(chip).to_be_hidden()


def test_drawer(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """トップバーの絞り込みのボタンでドロワーを開き、値を選ぶと URL の `f.{列}` を置き換え、履歴に積まない（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url, "?tab=graph")
    before = page.evaluate("history.length")
    # 実行
    page.get_by_role("button", name="絞り込み").click()
    page.get_by_role("dialog", name="絞り込み").get_by_role("checkbox", name=re.compile("^タスク")).click()
    # 検証
    page.wait_for_url(re.compile("f.type="))
    assert _search(page) == "?tab=graph&f.type=タスク"
    assert page.evaluate("history.length") == before
    expect(page.get_by_role("button", name="絞り込み（1 つの条件で絞り込み中）")).to_be_visible()


def test_no_match(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """絞り込みの条件に合う項目が無いときは、その旨の文を出す（正常系）。"""
    # 準備
    url = write_sample_preview()
    # 実行
    open_spa(page, url, "?tab=graph&f.tags=%E7%84%A1%E3%81%84%E3%82%BF%E3%82%B0")
    # 検証
    expect(page.get_by_text(NO_MATCH_TEXT)).to_be_visible()


def test_look_pick(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """見た目を選ぶと端末の保存領域に残し、キャンバスを作り直さずにその見た目で描く。URL は変えない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page.emulate_media(reduced_motion="reduce")
    open_spa(page, url, "?tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    page.mouse.move(*blank_point(page))
    settle(page)
    before = canvas_hash(page)
    page.evaluate("window.__canvasBefore = document.getElementById('graph-canvas')")
    # 実行
    page.get_by_role("combobox", name="ネットワークの見た目").select_option("constellation")
    settle(page)
    # 検証
    prefs: dict[str, Any] = page.evaluate("JSON.parse(localStorage.getItem('mindmap-preview'))")
    assert prefs["look"] == "constellation"
    assert canvas_hash(page) != before
    assert page.evaluate("window.__canvasBefore === document.getElementById('graph-canvas')")
    assert _search(page) == "?tab=graph"


def test_lock_toggle(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """詳細を開いている項目の玉を押すとロックして閉じた鍵を出し、もう一度押すとロックを外す。どちらも詳細は開いたまま（正常系）。"""
    # 準備
    url = write_sample_preview()
    _open_still(page, url, "?tab=graph&id=D-2")
    remember_pixels(page, "free")
    cx, cy = canvas_center(page)
    # 実行（ロックする）
    _press(page, cx, cy)
    locked = changed_pixels(page, "free")
    # 実行（ロックを外す）
    _press(page, cx, cy)
    unlocked = changed_pixels(page, "free")
    # 検証
    assert locked >= KEY_PIXELS_AT_LEAST
    assert unlocked <= UNCHANGED_AT_MOST
    assert _search(page) == "?tab=graph&id=D-2"
    expect(page.locator(DETAIL)).to_be_visible()


def test_blank_press_when_unlocked(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """ロックしていないとき、余白を押すと詳細を閉じて URL の `id` を外す（正常系）。"""
    # 準備
    url = write_sample_preview()
    _open_still(page, url, "?tab=graph&id=D-2")
    # 実行
    click_at(page, *blank_point(page))
    # 検証
    page.wait_for_url("**/spa/?tab=graph")
    expect(page.locator(DETAIL)).to_be_hidden()


def test_lock_key(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """`L` キーで、詳細を開いている項目の玉をもう一度押したのと同じ規則でロックを付け外しする（正常系）。"""
    # 準備
    url = write_sample_preview()
    _open_still(page, url, "?tab=graph&id=D-2")
    remember_pixels(page, "free")
    # 実行（ロックする）
    page.keyboard.press("l")
    settle(page)
    locked = changed_pixels(page, "free")
    # 実行（ロックを外す）
    page.keyboard.press("l")
    settle(page)
    unlocked = changed_pixels(page, "free")
    # 検証
    assert locked >= KEY_PIXELS_AT_LEAST
    assert unlocked <= UNCHANGED_AT_MOST
    assert _search(page) == "?tab=graph&id=D-2"


def test_lock_key_when_drawer_open(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """重ねる面（絞り込みのドロワー）を開いている間は `L` キーを受けず、閉じた鍵を出さない（正常系）。"""
    # 準備
    install_key_spy(page)
    url = write_sample_preview()
    _open_still(page, url, "?tab=graph&id=D-2")
    page.get_by_role("button", name="絞り込み").click()
    page.get_by_role("dialog", name="絞り込み").wait_for()
    # 実行
    page.keyboard.press("l")
    settle(page)
    # 検証
    assert [draw for draw in key_draws(page) if draw["closed"]] == []


def test_lock_when_narrow(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """幅 900px 以下ではロックせず、鍵を出さない（正常系）。"""
    # 準備
    install_key_spy(page)
    page.set_viewport_size(NARROW)
    url = write_sample_preview()
    page.emulate_media(reduced_motion="reduce")
    open_spa(page, url, "?tab=graph&id=D-2")
    page.wait_for_selector(DETAIL)
    # 実行
    page.keyboard.press("l")
    page.wait_for_timeout(MARK_WAIT_MS)
    # 検証
    assert key_draws(page) == []


def test_comment_marks_when_near(write_commented_preview: WriteReviewPreview, page: Page) -> None:
    """名前が読める大きさまで寄ると、件数のある玉の名前の右にコメントの印を出し、印はキャンバスに収まる（正常系）。"""
    # 準備
    url, _ = write_commented_preview()
    # 実行
    open_spa(page, url, "?tab=graph&id=D-2")
    page.wait_for_function(HAS_VISIBLE_MARK_SCRIPT, timeout=MARK_TIMEOUT_MS)
    # 検証
    shown: dict[str, Any] = page.evaluate(VISIBLE_MARKS_SCRIPT)
    box = shown["canvas"]
    assert len(shown["marks"]) >= 1
    assert all(box["left"] <= mark["left"] and mark["right"] <= box["right"] for mark in shown["marks"])
    assert all(box["top"] <= mark["top"] and mark["bottom"] <= box["bottom"] for mark in shown["marks"])


def test_region(write_sample_preview: WriteSamplePreview, page: Page) -> None:
    """ページ全体は縦にも横にもスクロールさせず、3D のキャンバスを領域の高さいっぱいに広げる（正常系）。"""
    # 準備
    url = write_sample_preview()
    # 実行
    open_spa(page, url, "?tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    # 検証
    region: dict[str, float] = page.evaluate(REGION_SCRIPT)
    assert region == {"overflowY": 0, "overflowX": 0, "canvasBottomGap": 0}
