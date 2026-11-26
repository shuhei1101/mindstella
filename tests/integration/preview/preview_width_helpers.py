"""横幅の確かめ（モジュール構成『React』の補足「横幅」）の結合テストが使う場面と検証。"""

from __future__ import annotations

from playwright.sync_api import Locator, Page

# 動作環境の最も狭い画面の幅
NARROWEST_SIZE = {"width": 360, "height": 800}

# 左のパネルを下限まで狭めて開く広い幅
WIDE_SIZE = {"width": 1440, "height": 800}

# 左のパネルの下限の幅（px）
LEFT_PANEL_MIN_PX = 320

# 3000 文字を超える、改行の無い長い URL を含む書き込みの本文
LONG_POST_BODY = f"{'長い書き込みの文です。' * 320}\nhttps://example.com/{'very-long-path-segment-without-breaks-' * 12}end"

# 改行の無い長いタイトル（長い URL を含む）
LONG_TITLE = f"{'改行の無い長いタイトル' * 8}https://example.com/{'segment' * 20}"

# 左のパネルの幅を残す sessionStorage のキー（ワークスペースの配信ではワークスペースの ID を付ける）
_LEFT_WIDTH_KEY_JS = "'mindmap-left-panel-width' + (location.pathname.split('/')[1] === 'w' ? ':' + decodeURIComponent(location.pathname.split('/')[2]) : '')"

# 要素が自分の幅の中に収まっているか（横にスクロールしない）
_FITS_JS = "(e) => e.scrollWidth <= e.clientWidth + 1"


def narrow_left_panel(page: Page) -> None:
    """そのタブに残す左のパネルの幅を下限にして、開き直す。"""
    page.evaluate(f"sessionStorage.setItem({_LEFT_WIDTH_KEY_JS}, '{LEFT_PANEL_MIN_PX}')")
    page.reload()


def assert_no_horizontal_scroll(page: Page, panel: Locator) -> None:
    """ページとパネルが横にスクロールしないことを確かめる。"""
    page.wait_for_timeout(500)
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), page.evaluate(
        "[document.documentElement.scrollWidth, document.documentElement.clientWidth]"
    )
    assert panel.evaluate(_FITS_JS), panel.evaluate("(e) => [e.scrollWidth, e.clientWidth]")
