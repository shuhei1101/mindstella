"""部品設計『トップバー』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 題名が収まりきらなくなる幅（題名を隠す幅 900px より広い）
MEDIUM_SIZE = {"width": 1000, "height": 600}

# 塗りが無いときの背景色
TRANSPARENT = "rgba(0, 0, 0, 0)"

# 要素の背景色を読む
BACKGROUND_SCRIPT = "e => getComputedStyle(e).backgroundColor"

# 検索の入口が中央に寄っているとみなす左右の余白の差（ピクセル）
CENTER_TOLERANCE_PX = 2

# 開いている画面のタブ・入口の key を読む
CURRENT_SCRIPT = """() => [...document.querySelectorAll('nav.tabbar a[aria-current="page"]')].map(a => a.dataset.tab)"""


def test_overview(open_story: OpenStory) -> None:
    """概要を開いている。開いている画面のタブだけが aria-current="page" を持つ（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--overview")
    # 検証
    assert page.evaluate(CURRENT_SCRIPT) == ["overview"]
    assert page.locator("nav.tabbar").get_attribute("aria-label") == "項目の種類"
    # トップバーのツール名が mindstella
    assert page.inner_text(".brand-name") == "mindstella"
    assert page.inner_text(".brand-sub") == "要件出しのスキル mindmap を設計する"


def test_graph(open_story: OpenStory) -> None:
    """つながりを開いている。つながりの入口だけを選んだ見た目にする（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--graph")
    # 検証
    assert page.evaluate(CURRENT_SCRIPT) == ["graph"]
    assert page.locator("nav.tabbar a.tab-special").count() == 1


def test_long_title(open_story: OpenStory) -> None:
    """題名が長いと 1 行で末尾を省略し、検索の入口とテーマの切り替えを押し出さない（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--long-title")
    page.set_viewport_size(MEDIUM_SIZE)
    page.wait_for_function("innerWidth === 1000")
    # 検証
    title = page.evaluate(
        "(() => { const t = document.querySelector('.brand-sub'); return [t.scrollWidth > t.clientWidth, getComputedStyle(t).textOverflow, t.title.length > 40]; })()"
    )
    assert title == [True, "ellipsis", True]
    viewport_width = page.evaluate("innerWidth")
    for selector in (".search-trigger", ".top-btn"):
        box = page.locator(selector).bounding_box()
        assert box is not None
        assert box["x"] + box["width"] <= viewport_width


def test_dark(open_story: OpenStory) -> None:
    """ダークのとき、ライトへ切り替えるボタンを出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--dark")
    # 検証
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    assert page.get_attribute(".top-btn", "aria-label") == "ライトに切り替え"
    assert page.get_attribute(".top-btn", "data-theme") == "light"


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px では、検索の入口を虫眼鏡だけにして題名を隠し、タブは帯の中で横に送る（正常系）。"""
    # 準備
    page = open_story("preview-topbar--narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    search_width = page.locator(".search-trigger").bounding_box()["width"]  # type: ignore[index]
    assert search_width <= 40
    assert not page.is_visible(".brand-sub")
    assert page.get_attribute(".search-trigger", "aria-label") == "すべての項目を検索"
    overflow = page.evaluate(
        "(() => { const t = document.querySelector('nav.tabbar'); return [t.scrollWidth > t.clientWidth, document.documentElement.scrollWidth <= innerWidth]; })()"
    )
    assert overflow == [True, True]


def test_offline(open_story: OpenStory) -> None:
    """サーバーにつながらない。検索の入口の左に、読んだ日時つきの接続の状態を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--offline")
    # 検証
    status = page.locator(".conn")
    assert status.get_attribute("role") == "status"
    assert status.inner_text() == "サーバーにつながりません（10/04 11:21 に読んだ記録）"
    assert status.locator("svg.icon").count() == 1
    assert page.evaluate("document.querySelector('.conn').tagName") != "BUTTON"
    status_box = status.bounding_box()
    search_box = page.locator(".search-trigger").bounding_box()
    assert status_box is not None
    assert search_box is not None
    assert status_box["x"] + status_box["width"] <= search_box["x"]


def test_offline_narrow(open_story: OpenStory) -> None:
    """幅 390px でサーバーにつながらない。「つながりません」だけを出し、読んだ日時を title に持つ（正常系）。"""
    # 準備
    page = open_story("preview-topbar--offline-narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    status = page.locator(".conn")
    assert status.get_attribute("title") == "10/04 11:21 に読んだ記録を出しています"
    assert status.inner_text() == "つながりません"


def test_comments(open_story: OpenStory) -> None:
    """コメントのボタンを右端に置き、全体の検索の入口を中央へ寄せる。件数を塗りで出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--comments")
    # 検証
    button = page.get_by_role("button", name="コメント（レビュー中 3 件）")
    assert button.count() == 1
    assert button.get_attribute("aria-expanded") == "false"
    assert button.locator(".label").inner_text() == "コメント"
    assert button.locator(".count").inner_text() == "3"
    assert page.eval_on_selector(".comments-btn .count", BACKGROUND_SCRIPT) != TRANSPARENT
    # コメントのボタンが右端、その左にテーマの切り替え
    comments_box = page.locator(".comments-btn").bounding_box()
    theme_box = page.locator(".top-btn").bounding_box()
    search_box = page.locator(".search-trigger").bounding_box()
    brand_box = page.locator(".brand-sub").bounding_box()
    assert comments_box is not None
    assert theme_box is not None
    assert search_box is not None
    assert brand_box is not None
    assert theme_box["x"] + theme_box["width"] <= comments_box["x"]
    # 検索の入口は、題名の右端とテーマの切り替えの左端の中央に寄る
    gap_before = search_box["x"] - (brand_box["x"] + brand_box["width"])
    gap_after = theme_box["x"] - (search_box["x"] + search_box["width"])
    assert abs(gap_before - gap_after) <= CENTER_TOLERANCE_PX


def test_comments_zero(open_story: OpenStory) -> None:
    """レビュー中のコメントが 0 件。押せるまま、件数の塗りを外して目立たせない（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--comments-zero")
    # 検証
    button = page.get_by_role("button", name="コメント（レビュー中 0 件）")
    assert button.is_enabled()
    assert button.locator(".count").inner_text() == "0"
    assert page.eval_on_selector(".comments-btn .count", BACKGROUND_SCRIPT) == TRANSPARENT


def test_comments_many(open_story: OpenStory) -> None:
    """100 件以上。件数を 99+ にし、読み上げの名前には実際の件数を持つ（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--comments-many")
    # 検証
    assert page.inner_text(".comments-btn .count") == "99+"
    assert page.get_attribute(".comments-btn", "aria-label") == "コメント（レビュー中 120 件）"


def test_comments_open(open_story: OpenStory) -> None:
    """コメントの一覧を開いている。ボタンを枠と面で選んだ見た目にする（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--comments-open")
    # 検証
    assert page.get_attribute(".comments-btn", "aria-expanded") == "true"
    assert page.eval_on_selector(".comments-btn", BACKGROUND_SCRIPT) != TRANSPARENT
    assert page.eval_on_selector(".comments-btn", "e => e.classList.contains('open')") is True


def test_comments_narrow(open_story: OpenStory) -> None:
    """幅 390px。コメントのボタンの文字を隠し、印と件数だけにする（正常系）。"""
    # 準備
    page = open_story("preview-topbar--comments-narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    assert not page.is_visible(".comments-btn .label")
    assert page.is_visible(".comments-btn svg.icon")
    assert page.inner_text(".comments-btn .count") == "3"
    assert page.get_attribute(".comments-btn", "aria-label") == "コメント（レビュー中 3 件）"
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
