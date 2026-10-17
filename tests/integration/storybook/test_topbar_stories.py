"""部品設計『トップバー』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

import itertools

import pytest
from playwright.sync_api import Page
from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 題名が収まりきらなくなる幅（題名を隠す幅 900px より広い）
MEDIUM_SIZE = {"width": 1000, "height": 600}

# サーバーにつながらないとき、接続の状態の全文が出る幅（幅 1440px 以下は短い文言になる）
WIDE_SIZE = {"width": 1441, "height": 600}

# 塗りが無いときの背景色
TRANSPARENT = "rgba(0, 0, 0, 0)"

# 要素の背景色を読む
BACKGROUND_SCRIPT = "e => getComputedStyle(e).backgroundColor"

# 検索の入口が中央に寄っているとみなす左右の余白の差（ピクセル）
CENTER_TOLERANCE_PX = 2

# コメントのボタン・テーマの切り替え・検索の入口・題名・右のボタンの群（表示の設定・絞り込み・コメントのうち一番左のもの）の左右の位置を同じ瞬間に読む
TOPBAR_BOXES_SCRIPT = """() => {
  const box = (selector) => {
    const r = document.querySelector(selector).getBoundingClientRect();
    return { left: r.left, right: r.right };
  };
  const group = [...document.querySelectorAll('.settings-btn, .filter-btn, .comments-btn')]
    .map((e) => e.getBoundingClientRect().left);
  return {
    comments: box('.comments-btn'),
    theme: box('.top-btn'),
    search: box('.search-trigger'),
    brand: box('.brand-sub'),
    group: { left: Math.min(...group) },
  };
}"""

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
    """ネットワークを開いている。ネットワークの入口だけを選んだ見た目にし、名前を「ネットワーク」、アイコンを星座の形にする（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--graph")
    # 検証
    assert page.evaluate(CURRENT_SCRIPT) == ["graph"]
    assert page.locator("nav.tabbar a.tab-special").count() == 1
    entry = page.locator("nav.tabbar a.tab-special")
    assert entry.inner_text().strip() == "ネットワーク"
    assert entry.get_attribute("aria-current") == "page"
    # アイコンは、4 つの星を線で結び端の 1 つをきらめく星にした星座の形（円 4 つ・線の組 1 つ・十字の星 1 つ）
    assert entry.locator("svg.icon circle").count() == 4
    assert entry.locator("svg.icon path").count() == 2


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
    page.set_viewport_size(WIDE_SIZE)
    page.wait_for_function("innerWidth === 1441")
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
    """幅 390px でサーバーにつながらない。接続の状態を印だけにし、「つながりません」は読み上げにだけ残して、読んだ日時を title に持つ（正常系）。"""
    # 準備
    page = open_story("preview-topbar--offline-narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行
    hidden_text = page.evaluate(ICON_ONLY_SCRIPT)
    # 検証
    status = page.locator(".conn")
    assert status.get_attribute("title") == "10/04 11:21 に読んだ記録を出しています"
    assert status.locator("svg.icon").is_visible()
    assert hidden_text == {"text": "つながりません", "width": 1, "height": 1, "longShown": False}


def test_comments(open_story: OpenStory) -> None:
    """コメントのボタンをライト / ダークの切り替えの左隣に置き、全体の検索の入口を中央へ寄せる。件数を塗りで出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--comments")
    # 検証
    button = page.get_by_role("button", name="コメント（レビュー中 3 件）")
    assert button.count() == 1
    assert button.get_attribute("aria-expanded") == "false"
    assert button.locator(".label").inner_text() == "コメント"
    assert button.locator(".count").inner_text() == "3"
    assert page.eval_on_selector(".comments-btn .count", BACKGROUND_SCRIPT) != TRANSPARENT
    # テーマの切り替えが右端、その左にコメントのボタン（位置は同じ瞬間にまとめて読む）
    boxes = page.evaluate(TOPBAR_BOXES_SCRIPT)
    assert boxes["comments"]["right"] <= boxes["theme"]["left"]
    # 検索の入口は、題名の右端と右のボタンの群の左端の中央に寄る
    gap_before = boxes["search"]["left"] - boxes["brand"]["right"]
    gap_after = boxes["group"]["left"] - boxes["search"]["right"]
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


# 未読の点が吹き出しの印のどこにあるかを読む（吹き出しの印の箱と点の箱）
DOT_BOXES_SCRIPT = """() => {
  const icon = document.querySelector('.comments-btn .cb-icon svg.icon').getBoundingClientRect();
  const dot = document.querySelector('.comments-btn .unread-dot').getBoundingClientRect();
  const button = document.querySelector('.comments-btn').getBoundingClientRect();
  return {
    iconRight: icon.right, iconTop: icon.top, iconLeft: icon.left,
    dotLeft: dot.left, dotRight: dot.right, dotTop: dot.top, dotBottom: dot.bottom,
    dotCenterX: (dot.left + dot.right) / 2, dotCenterY: (dot.top + dot.bottom) / 2,
    buttonWidth: button.width,
  };
}"""

# 点を付けたままのボタンの幅と、同じ文書で点を外したボタンの幅を読む（別の文書と比べると、文字の読み込みの有無で幅が揺れる）
DOT_WIDTH_SCRIPT = """async () => {
  await document.fonts.ready;
  const button = document.querySelector('.comments-btn');
  const withDot = button.getBoundingClientRect().width;
  button.querySelector('.unread-dot').remove();
  return { withDot, withoutDot: button.getBoundingClientRect().width };
}"""


def test_comments_unread(open_story: OpenStory) -> None:
    """オープンのスレッドに未読がある。吹き出しの印の右上に点を重ね、レビュー中の件数はそのまま出す。ボタンの幅は変えない（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--comments-unread")
    boxes = page.evaluate(DOT_BOXES_SCRIPT)
    # 検証
    button = page.get_by_role("button", name="コメント（未読あり・レビュー中 3 件）")
    assert button.count() == 1
    assert button.locator(".count").inner_text() == "3"
    # 点は吹き出しの印の右上の角に重なり、読み上げから外す
    dot = page.locator(".comments-btn .unread-dot")
    assert dot.count() == 1
    assert dot.get_attribute("aria-hidden") == "true"
    assert boxes["dotCenterX"] >= boxes["iconRight"] - 4
    assert boxes["dotCenterY"] <= boxes["iconTop"] + 4
    # 点は暗い地で読める色（--teal-400）で、数字は出さない
    assert page.eval_on_selector(".comments-btn .unread-dot", BACKGROUND_SCRIPT) == "rgb(45, 212, 191)"
    assert dot.inner_text() == ""
    # 点を足してもボタンの幅は変わらない
    widths = page.evaluate(DOT_WIDTH_SCRIPT)
    assert widths["withDot"] == widths["withoutDot"]
    # 未読の無い状態には点が無い
    plain = open_story("preview-topbar--comments")
    assert plain.locator(".comments-btn .unread-dot").count() == 0
    assert plain.get_attribute(".comments-btn", "aria-label") == "コメント（レビュー中 3 件）"


def test_comments_unread_zero(open_story: OpenStory) -> None:
    """未読があり、レビュー中は 0 件。点を出し、件数は塗りを外した 0 のまま（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--comments-unread-zero")
    # 検証
    button = page.get_by_role("button", name="コメント（未読あり・レビュー中 0 件）")
    assert button.is_enabled()
    assert page.locator(".comments-btn .unread-dot").count() == 1
    assert button.locator(".count").inner_text() == "0"
    assert page.eval_on_selector(".comments-btn .count", BACKGROUND_SCRIPT) == TRANSPARENT


def test_comments_unread_open(open_story: OpenStory) -> None:
    """未読があり、コメントの一覧を開いている。選んだ見た目の枠と面に点を重ねる（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--comments-unread-open")
    # 検証
    assert page.get_attribute(".comments-btn", "aria-expanded") == "true"
    assert page.eval_on_selector(".comments-btn", BACKGROUND_SCRIPT) != TRANSPARENT
    assert page.locator(".comments-btn.open .unread-dot").count() == 1


def test_comments_unread_narrow(open_story: OpenStory) -> None:
    """幅 390px で未読がある。印と件数だけで、点を重ねてもボタンと × を押し出さず 390px の中に収める（正常系）。"""
    # 準備
    page = open_story("preview-topbar--comments-unread-narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    assert not page.is_visible(".comments-btn .label")
    assert page.is_visible(".comments-btn .unread-dot")
    assert page.inner_text(".comments-btn .count") == "3"
    assert page.get_attribute(".comments-btn", "aria-label") == "コメント（未読あり・レビュー中 3 件）"
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    # 点まで含めて、ボタンが画面の中に収まる
    box = page.locator(".comments-btn").bounding_box()
    dot = page.locator(".comments-btn .unread-dot").bounding_box()
    assert box is not None
    assert dot is not None
    assert box["x"] >= 0
    assert dot["x"] + dot["width"] <= 390


@pytest.mark.parametrize(
    "story_id",
    [
        pytest.param("preview-topbar--filter-on", id="filter_on"),
        pytest.param("preview-topbar--filter-open", id="filter_open"),
        pytest.param("preview-topbar--settings-open", id="settings_open"),
        pytest.param("preview-topbar--comments-narrow", id="comments_narrow"),
        pytest.param("preview-topbar--comments-unread-narrow", id="comments_unread_narrow"),
        pytest.param("preview-topbar--diff-on-narrow", id="diff_on_narrow"),
    ],
)
def test_no_overflow_when_narrow(open_story: OpenStory, story_id: str) -> None:
    """幅 390px で、ボタンが並ぶ状態でも横に溢れない（正常系）。"""
    # 準備
    page = open_story(story_id)
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


# 接続の状態の文言が、見た目の上で隠れ（1px 四方に切る）、DOM には残っていることを読む
ICON_ONLY_SCRIPT = """() => {
  const short = document.querySelector('.conn .conn-short');
  const r = short.getBoundingClientRect();
  return {
    text: short.textContent,
    width: r.width,
    height: r.height,
    longShown: document.querySelector('.conn .conn-long').getClientRects().length > 0,
  };
}"""

# 絞り込みのボタン
FILTER_BUTTON = "[data-act='filter']"


def test_filter(open_story: OpenStory) -> None:
    """絞り込みのボタンをコメントのボタンの左に置き、絞っていないのでバッジを出さない。ライト / ダークの切り替えは右端に置く（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--filter")
    # 検証
    assert page.inner_text(f"{FILTER_BUTTON} .label") == "絞り込み"
    assert page.get_attribute(FILTER_BUTTON, "aria-label") == "絞り込み"
    assert page.get_attribute(FILTER_BUTTON, "aria-expanded") == "false"
    assert page.locator(f"{FILTER_BUTTON} .fbadge").count() == 0
    # 絞り込みのボタンはコメントのボタンの左隣で、重ならない
    filter_box = page.locator(FILTER_BUTTON).bounding_box()
    comments_box = page.locator(".comments-btn").bounding_box()
    assert filter_box["x"] + filter_box["width"] <= comments_box["x"]
    # ライト / ダークの切り替えは右端で、コメントのボタンの右にある
    theme_box = page.locator(".top-btn").bounding_box()
    assert comments_box["x"] + comments_box["width"] <= theme_box["x"]


def test_filter_on(open_story: OpenStory) -> None:
    """2 つの条件で絞り込み中。「絞り込み」の右に印の色のバッジ「2」を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--filter-on")
    # 検証
    assert page.inner_text(f"{FILTER_BUTTON} .fbadge") == "2"
    # 読み上げの名前は絞り込み中の条件の数を含み、バッジは読み上げから外す
    assert page.get_attribute(FILTER_BUTTON, "aria-label") == "絞り込み（2 つの条件で絞り込み中）"
    assert page.get_attribute(f"{FILTER_BUTTON} .fbadge", "aria-hidden") == "true"
    assert page.eval_on_selector(f"{FILTER_BUTTON} .fbadge", BACKGROUND_SCRIPT) != TRANSPARENT
    label_box = page.locator(f"{FILTER_BUTTON} .label").bounding_box()
    badge_box = page.locator(f"{FILTER_BUTTON} .fbadge").bounding_box()
    assert label_box["x"] + label_box["width"] <= badge_box["x"]


def test_filter_open(open_story: OpenStory) -> None:
    """絞り込みのドロワーを開いている。ボタンを枠と面で選んだ見た目にする（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--filter-open")
    # 検証
    assert page.get_attribute(FILTER_BUTTON, "aria-expanded") == "true"
    assert page.eval_on_selector(FILTER_BUTTON, BACKGROUND_SCRIPT) != TRANSPARENT
    assert page.eval_on_selector(FILTER_BUTTON, "e => e.classList.contains('open')") is True


def test_filter_narrow(open_story: OpenStory) -> None:
    """幅 390px。絞り込みのボタンの文字を隠し、アイコンとバッジだけにする（正常系）。"""
    # 準備
    page = open_story("preview-topbar--filter-narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    assert not page.is_visible(f"{FILTER_BUTTON} .label")
    assert page.is_visible(f"{FILTER_BUTTON} svg.icon")
    assert page.inner_text(f"{FILTER_BUTTON} .fbadge") == "1"
    # 文字を隠しても読み上げの名前を残す
    assert page.get_attribute(FILTER_BUTTON, "aria-label") == "絞り込み（1 つの条件で絞り込み中）"
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


# 帯の子の左右の位置（ツール名・検索の入口・変更履歴・札・コメント・テーマの切り替え）を同じ瞬間に読む
DIFF_BOXES_SCRIPT = """() => {
  const box = (selector) => {
    const element = document.querySelector(selector);
    if (!element) return null;
    const r = element.getBoundingClientRect();
    return { left: r.left, right: r.right };
  };
  return {
    brand: box('.brand'),
    search: box('.search-trigger'),
    history: box('.hist-btn'),
    chip: box('.df-chip'),
    chipText: box('.df-chip-t'),
    off: box('.df-chip button'),
    theme: box('.top-btn'),
    comments: box('.comments-btn'),
    page: { width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth },
  };
}"""

# 札の名前が読める幅の下限（ピクセル）
MIN_CHIP_TEXT_PX = 40


def test_diff_on(open_story: OpenStory) -> None:
    """変更履歴で「前回開いてから」を選んだ間。「変更履歴」の右に札と ×、検討事項・資料のタブに点を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--diff-on")
    # 検証
    history = page.get_by_role("button", name="変更履歴")
    assert history.get_attribute("aria-haspopup") == "dialog"
    assert history.locator(".label").inner_text() == "変更履歴"
    chip = page.locator(".df-chip")
    assert chip.locator(".df-chip-t").inner_text().endswith("前回開いてから")
    assert chip.locator(".df-chip-t").get_attribute("title") == "前回開いてから（10/04 13:05 より後）"
    assert chip.get_by_role("button", name="差分の表示をやめる").count() == 1
    boxes = page.evaluate(DIFF_BOXES_SCRIPT)
    assert boxes["history"]["right"] <= boxes["chip"]["left"]
    # 印の付いた種類のタブにだけ点が付き、件数は残る
    dotted = page.eval_on_selector_all(
        "nav.tabbar a.tab:has(.df-dot)", "tabs => tabs.map(t => t.dataset.tab)"
    )
    assert dotted == ["decisions", "docs"]
    assert page.inner_text("nav.tabbar a[data-tab='decisions'] .count") == "12"
    assert page.inner_text(".df-dot .sr-only") == "新規・変更・消した項目があります"


def test_diff_on_narrow(open_story: OpenStory) -> None:
    """幅 390px のサーバーの配信で、差分の表示の間。ボタンをアイコンだけにし、札の名前を省略して 390px の中に収める（正常系）。"""
    # 準備
    page = open_story("preview-topbar--diff-on-narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行
    boxes = page.evaluate(DIFF_BOXES_SCRIPT)
    # 検証
    assert not page.is_visible(".hist-btn .label")
    assert not page.is_visible(".comments-btn .label")
    assert page.inner_text(".comments-btn .count") == "3"
    assert page.get_attribute(".hist-btn", "aria-label") == "変更履歴"
    # 帯の子が左から順に並び、重ならず、画面の中に収まる
    order = ["brand", "search", "history", "chip", "comments", "theme"]
    for left, right in itertools.pairwise(order):
        assert boxes[left]["right"] <= boxes[right]["left"], (left, right)
    assert boxes["theme"]["right"] <= boxes["page"]["width"]
    assert boxes["page"]["scroll"] <= boxes["page"]["width"]
    # 札の名前は末尾を省略しても数文字が読め、× は札の中にある
    assert boxes["chipText"]["right"] - boxes["chipText"]["left"] >= MIN_CHIP_TEXT_PX
    assert boxes["off"]["right"] <= boxes["chip"]["right"]
    assert (
        page.evaluate("getComputedStyle(document.querySelector('.df-chip-t')).textOverflow")
        == "ellipsis"
    )


def test_settings_open(open_story: OpenStory) -> None:
    """表示の設定のパネルを開いている。表示の設定のボタンを枠と面で選んだ見た目にし、コメントのボタンは選んでいない見た目のまま（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--settings-open")
    # 検証
    button = page.get_by_role("button", name="表示の設定", exact=True)
    assert button.count() == 1
    assert button.get_attribute("aria-expanded") == "true"
    assert "open" in (button.get_attribute("class") or "")
    comments = page.get_by_role("button", name="コメント（レビュー中 3 件）")
    assert "open" not in (comments.get_attribute("class") or "")
    # 表示の設定のボタンは、コメントのボタンの左に置く
    boxes = page.evaluate(
        "() => ({s: document.querySelector('.settings-btn').getBoundingClientRect().right,"
        " c: document.querySelector('.comments-btn').getBoundingClientRect().left})"
    )
    assert boxes["s"] <= boxes["c"]
    # ライト / ダークの切り替えは右端で、コメントのボタンの右にある
    theme = page.locator(".top-btn").bounding_box()
    comments_box = page.locator(".comments-btn").bounding_box()
    assert comments_box["x"] + comments_box["width"] <= theme["x"]
    # 文書に無い要素を指す `aria-controls` を付けない
    assert button.get_attribute("aria-controls") is None


def test_kinds_hidden(open_story: OpenStory) -> None:
    """表示の設定でタスクと資料を外した。タブの帯からその 2 つを外し、概要とネットワークの入口は残す（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--kinds-hidden")
    # 検証
    tabs = page.eval_on_selector_all("nav.tabbar a", "links => links.map(a => a.dataset.tab)")
    assert tabs == ["overview", "decisions", "research", "terms", "notes", "logs", "graph"]


def test_export(open_story: OpenStory) -> None:
    """配る書き出し。表示の設定のボタンを出し、コメントのボタンは出さない。ライト / ダークの切り替えは表示の設定の右の右端に置く（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--export")
    # 検証
    assert page.get_by_role("button", name="表示の設定", exact=True).count() == 1
    assert page.locator(".comments-btn").count() == 0
    assert page.get_attribute(".settings-btn", "aria-expanded") == "false"
    # ライト / ダークの切り替えは表示の設定の右で、右端にある
    settings_box = page.locator(".settings-btn").bounding_box()
    theme_box = page.locator(".top-btn").bounding_box()
    assert settings_box["x"] + settings_box["width"] <= theme_box["x"]
    last = page.eval_on_selector_all(
        "header.topbar > *", "items => items[items.length - 1].classList.contains('top-btn')"
    )
    assert last is True


# 差分の札の幅の下限（em）。5.5em を、描画の丸めの 0.01em まで許して測る
CHIP_MIN_WIDTH_EM = 5.49

# `LongTitle` の題名（差分の札と同じ帯に長い題名を置く）
LONG_TITLE = "プレビューの画面（概要・検討事項・タスク・資料・ネットワーク・詳細パネル）を見本に沿って作るための話し合いの記録"

# Storybook の body が持つ左右の余白を外す（トップバーを画面の幅いっぱいに置く本物の画面と同じ幅で測る）
NO_BODY_PADDING = "body { padding: 0 !important; }"

# ページとトップバーが横にはみ出さないことと、札の幅（札の文字の大きさに対する倍率）を同じ瞬間に読む
FIT_SCRIPT = """() => {
  const bar = document.querySelector('.topbar');
  const chip = document.querySelector('.df-chip');
  return {
    pageFits: document.documentElement.scrollWidth <= innerWidth,
    barFits: bar.scrollWidth <= bar.clientWidth,
    chipEm: chip.getBoundingClientRect().width / parseFloat(getComputedStyle(chip).fontSize),
  };
}"""

# 狭い幅の作りの区切り（1100px・1440px）の前後と、報告された幅（901px・963px）
FIT_WIDTHS = [
    pytest.param(901, id="w901"),
    pytest.param(963, id="w963"),
    pytest.param(1100, id="w1100"),
    pytest.param(1101, id="w1101"),
    pytest.param(1440, id="w1440"),
    pytest.param(1441, id="w1441"),
]


def _open_story_at(open_story: OpenStory, story_id: str, width: int) -> Page:
    """ストーリーを指定の幅で開き、Storybook の body の余白を外して返す。"""
    page = open_story(story_id)
    page.set_viewport_size({"width": width, "height": 600})
    page.wait_for_function(f"innerWidth === {width}")
    page.add_style_tag(content=NO_BODY_PADDING)
    page.evaluate("document.fonts.ready")
    return page


@pytest.mark.parametrize("width", FIT_WIDTHS)
def test_filter_diff_medium_when_width(open_story: OpenStory, width: int) -> None:
    """絞り込み・表示の設定・コメントのボタンと差分の札を出しても、幅 901〜1441px でページもトップバーも横にはみ出さず、札は 5.5em 以上を取る（正常系）。"""
    # 準備・実行
    page = _open_story_at(open_story, "preview-topbar--filter-diff-medium", width)
    measured = page.evaluate(FIT_SCRIPT)
    # 検証
    assert measured["pageFits"]
    assert measured["barFits"]
    assert measured["chipEm"] >= CHIP_MIN_WIDTH_EM


@pytest.mark.parametrize("width", FIT_WIDTHS)
def test_filter_diff_offline_when_width(open_story: OpenStory, width: int) -> None:
    """サーバーにつながらず差分の札を出しても、幅 901〜1441px でページもトップバーも横にはみ出さず、札は 5.5em 以上を取る（正常系）。"""
    # 準備・実行
    page = _open_story_at(open_story, "preview-topbar--filter-diff-offline", width)
    measured = page.evaluate(FIT_SCRIPT)
    # 検証
    assert measured["pageFits"]
    assert measured["barFits"]
    assert measured["chipEm"] >= CHIP_MIN_WIDTH_EM


def test_filter_diff_medium_when_long_title(open_story: OpenStory) -> None:
    """題名が長くても、幅 1101px で札は 5.5em 以上を取り、足りない幅は題名の側を縮める（正常系）。"""
    # 準備
    page = _open_story_at(open_story, "preview-topbar--filter-diff-medium", 1101)
    page.evaluate(
        "title => { const e = document.querySelector('.brand-sub'); e.textContent = title; e.title = title; }",
        LONG_TITLE,
    )
    # 実行
    measured = page.evaluate(FIT_SCRIPT)
    # 検証
    assert measured["pageFits"]
    assert measured["barFits"]
    assert measured["chipEm"] >= CHIP_MIN_WIDTH_EM


# 幅 390〜900px で全てのボタンを出す 4 つの状態と、部品設計『トップバー』が見せ方に挙げた幅
CONNECTED_DIFF = "preview-topbar--filter-diff-narrow"
CONNECTED_HISTORY = "preview-topbar--filter-history-narrow"
OFFLINE_DIFF = "preview-topbar--filter-diff-offline-narrow"
OFFLINE_HISTORY = "preview-topbar--filter-offline-narrow"

NARROW_STORY_WIDTHS = {
    OFFLINE_DIFF: [390, 405, 480, 481, 519, 900],
    OFFLINE_HISTORY: [390, 480, 481, 616, 900],
    CONNECTED_HISTORY: [390, 480, 481, 492, 900],
    CONNECTED_DIFF: [390, 480, 481, 900],
}

NARROW_STORY_CASES = [
    pytest.param(story_id, width, id=f"{story_id.removeprefix('preview-topbar--')}-w{width}")
    for story_id, widths in NARROW_STORY_WIDTHS.items()
    for width in widths
]

DIFF_STORY_CASES = [
    pytest.param(story_id, width, id=f"{story_id.removeprefix('preview-topbar--')}-w{width}")
    for story_id in (OFFLINE_DIFF, CONNECTED_DIFF)
    for width in NARROW_STORY_WIDTHS[story_id]
]

OFFLINE_STORY_CASES = [
    pytest.param(story_id, width, id=f"{story_id.removeprefix('preview-topbar--')}-w{width}")
    for story_id in (OFFLINE_DIFF, OFFLINE_HISTORY)
    for width in NARROW_STORY_WIDTHS[story_id]
]

# 要素の間隔: 差分を出している間はどの幅でも 8px、差分を出していない間は 480px 以下で 3px・481〜900px で 8px
GAP_CASES = [
    pytest.param(
        story_id,
        width,
        "8px" if story_id in (OFFLINE_DIFF, CONNECTED_DIFF) or width > 480 else "3px",
        id=f"{story_id.removeprefix('preview-topbar--')}-w{width}",
    )
    for story_id, widths in NARROW_STORY_WIDTHS.items()
    for width in widths
]

# ページがはみ出さないことと、トップバーの表示中のボタンが表示幅の中にあることを同じ瞬間に読む
BUTTONS_FIT_SCRIPT = """() => {
  const outside = [...document.querySelectorAll('.topbar button')]
    .filter(b => b.getClientRects().length > 0)
    .filter(b => { const r = b.getBoundingClientRect(); return r.left < 0 || r.right > innerWidth; })
    .map(b => b.getAttribute('aria-label') || b.className);
  return {
    pageFits: document.documentElement.scrollWidth <= innerWidth,
    barFits: document.querySelector('.topbar').scrollWidth <= document.querySelector('.topbar').clientWidth,
    outside,
  };
}"""

# ツール名の印（.brand）が見えているか・トップバーの要素の間隔を読む
BRAND_VISIBLE_SCRIPT = "() => document.querySelector('.brand').getClientRects().length > 0"
BAR_GAP_SCRIPT = "() => getComputedStyle(document.querySelector('.topbar')).columnGap"


def _open_narrow_story_at(open_story: OpenStory, story_id: str, width: int) -> Page:
    """狭い幅のストーリーを指定の幅で開く（ストーリーが持つ余白のままで、画面と同じ幅で測る）。"""
    page = open_story(story_id)
    page.set_viewport_size({"width": width, "height": 844})
    page.wait_for_function(f"innerWidth === {width}")
    page.evaluate("document.fonts.ready")
    return page


@pytest.mark.parametrize(("story_id", "width"), NARROW_STORY_CASES)
def test_filter_narrow_states_when_width(open_story: OpenStory, story_id: str, width: int) -> None:
    """幅 390〜900px で全てのボタンを出しても、ページもトップバーも横にはみ出さず、全てのボタンが表示幅の中にある（正常系）。"""
    # 準備
    page = _open_narrow_story_at(open_story, story_id, width)
    # 実行
    measured = page.evaluate(BUTTONS_FIT_SCRIPT)
    # 検証
    assert measured == {"pageFits": True, "barFits": True, "outside": []}


@pytest.mark.parametrize(("story_id", "width"), DIFF_STORY_CASES)
def test_filter_narrow_chip_when_width(open_story: OpenStory, story_id: str, width: int) -> None:
    """差分を出している間は、幅 390〜900px で札の幅が 5.5em 以上ある（正常系）。"""
    # 準備
    page = _open_narrow_story_at(open_story, story_id, width)
    # 実行
    measured = page.evaluate(FIT_SCRIPT)
    # 検証
    assert measured["chipEm"] >= CHIP_MIN_WIDTH_EM


@pytest.mark.parametrize(("story_id", "width"), OFFLINE_STORY_CASES)
def test_filter_narrow_offline_icon_only_when_width(open_story: OpenStory, story_id: str, width: int) -> None:
    """サーバーにつながらない間は、幅 390〜900px で接続の状態が印だけになり、「つながりません」は読み上げに残る（正常系）。"""
    # 準備
    page = _open_narrow_story_at(open_story, story_id, width)
    # 実行
    hidden_text = page.evaluate(ICON_ONLY_SCRIPT)
    # 検証
    assert page.locator(".conn svg.icon").is_visible()
    assert hidden_text == {"text": "つながりません", "width": 1, "height": 1, "longShown": False}


@pytest.mark.parametrize(
    ("width", "visible"),
    [
        pytest.param(390, False, id="w390"),
        pytest.param(405, False, id="w405"),
        pytest.param(480, False, id="w480"),
        pytest.param(481, True, id="w481"),
        pytest.param(519, True, id="w519"),
        pytest.param(900, True, id="w900"),
    ],
)
def test_filter_diff_offline_narrow_brand_when_width(open_story: OpenStory, width: int, visible: bool) -> None:
    """つながらない＋差分では、幅 480px 以下でツール名の印を隠し、481px 以上で出す（正常系）。"""
    # 準備
    page = _open_narrow_story_at(open_story, OFFLINE_DIFF, width)
    # 実行
    shown = page.evaluate(BRAND_VISIBLE_SCRIPT)
    # 検証
    assert shown is visible


@pytest.mark.parametrize(("story_id", "width", "gap"), GAP_CASES)
def test_filter_narrow_gap_when_width(open_story: OpenStory, story_id: str, width: int, gap: str) -> None:
    """トップバーの要素の間隔は、差分を出している間はどの幅でも 8px、出していない間は 480px 以下で 3px・481〜900px で 8px にする（正常系）。"""
    # 準備
    page = _open_narrow_story_at(open_story, story_id, width)
    # 実行
    measured = page.evaluate(BAR_GAP_SCRIPT)
    # 検証
    assert measured == gap


def test_search_key_hint(open_story: OpenStory) -> None:
    """検索の入口は `aria-keyshortcuts="Control+K Meta+K"` を持ち、右端の kbd にキーの案内（macOS は ⌘K）を出す。読み上げ名は「すべての項目を検索」（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--overview")
    # 検証
    trigger = page.locator('button[data-act="search"]')
    assert trigger.get_attribute("aria-keyshortcuts") == "Control+K Meta+K"
    assert trigger.get_attribute("aria-label") == "すべての項目を検索"
    assert trigger.locator("kbd").inner_text() in ("Ctrl+K", "⌘K")


# 幅 320〜389px で全てのボタンを出す 4 つの状態
FIT_NARROWEST = "preview-topbar--fit-narrowest"
FIT_NARROWEST_DIFF = "preview-topbar--fit-narrowest-diff"
FIT_NARROWEST_OFFLINE = "preview-topbar--fit-narrowest-offline"
FIT_NARROWEST_OFFLINE_DIFF = "preview-topbar--fit-narrowest-offline-diff"

# 部品設計『トップバー』が見せ方に挙げた、幅 389px 以下の幅
NARROWEST_WIDTHS = [320, 361, 389]

# 幅 389px 以下の状態と幅の組
NARROWEST_CASES = [
    pytest.param(story_id, width, id=f"{story_id.removeprefix('preview-topbar--')}-w{width}")
    for story_id in (FIT_NARROWEST, FIT_NARROWEST_DIFF, FIT_NARROWEST_OFFLINE, FIT_NARROWEST_OFFLINE_DIFF)
    for width in NARROWEST_WIDTHS
]

# 差分の札を出している状態と幅の組
NARROWEST_DIFF_CASES = [
    pytest.param(story_id, width, id=f"{story_id.removeprefix('preview-topbar--')}-w{width}")
    for story_id in (FIT_NARROWEST_DIFF, FIT_NARROWEST_OFFLINE_DIFF)
    for width in NARROWEST_WIDTHS
]

# 状態と幅と、ツール名の印を隠すか（差分の札を出している状態だけ隠す）の組
NARROWEST_PACKING_CASES = [
    pytest.param(story_id, width, brand_hidden, id=f"{story_id.removeprefix('preview-topbar--')}-w{width}")
    for story_id, brand_hidden in (
        (FIT_NARROWEST, False),
        (FIT_NARROWEST_DIFF, True),
        (FIT_NARROWEST_OFFLINE, False),
        (FIT_NARROWEST_OFFLINE_DIFF, True),
    )
    for width in NARROWEST_WIDTHS
]

# トップバーの要素の間隔・左右の余白、表示の設定・絞り込み・コメントのボタンの左右の余白と印と件数の間隔、ツール名の文字と印が隠れているかを同じ瞬間に読む
BAR_SHAPE_SCRIPT = """() => {
  const bar = getComputedStyle(document.querySelector('.topbar'));
  const buttons = ['.settings-btn', '.filter-btn', '.comments-btn'].map((selector) => {
    const style = getComputedStyle(document.querySelector(selector));
    return [style.paddingLeft, style.paddingRight, style.columnGap];
  });
  const hidden = (selector) => document.querySelector(selector).getClientRects().length === 0;
  return {
    gap: bar.columnGap,
    padding: [bar.paddingLeft, bar.paddingRight],
    buttons,
    nameHidden: hidden('.brand-name'),
    brandHidden: hidden('.brand'),
  };
}"""

# 印だけのボタン（検索・変更履歴・ライト / ダーク）の幅と高さを読む
ICON_BUTTON_SIZES_SCRIPT = """() => ['.search-trigger', '.hist-btn', '.top-btn'].map((selector) => {
  const r = document.querySelector(selector).getBoundingClientRect();
  return [r.width, r.height];
})"""

# 幅 389px 以下の印だけのボタンの幅と高さ
NARROWEST_ICON_BUTTON_SIZE = [28, 32]

# 幅 389px 以下の印だけのボタンの幅と高さ。つながらず差分を出している間だけ幅 26px にする
NARROWEST_ICON_BUTTON_CASES = [
    pytest.param(story_id, width, size, id=f"{story_id.removeprefix('preview-topbar--')}-w{width}")
    for story_id, size in (
        (FIT_NARROWEST, [28, 32]),
        (FIT_NARROWEST_DIFF, [28, 32]),
        (FIT_NARROWEST_OFFLINE, [28, 32]),
        (FIT_NARROWEST_OFFLINE_DIFF, [26, 32]),
    )
    for width in NARROWEST_WIDTHS
]


@pytest.mark.parametrize(("story_id", "width"), NARROWEST_CASES)
def test_fit_narrowest_states_when_width(open_story: OpenStory, story_id: str, width: int) -> None:
    """幅 320・361・389px で全てのボタンを出しても、ページもトップバーも横にはみ出さず、全てのボタンと札の × が表示幅の中にある（正常系）。"""
    # 準備
    page = _open_narrow_story_at(open_story, story_id, width)
    # 実行
    measured = page.evaluate(BUTTONS_FIT_SCRIPT)
    # 検証
    assert measured == {"pageFits": True, "barFits": True, "outside": []}


@pytest.mark.parametrize(("story_id", "width"), NARROWEST_DIFF_CASES)
def test_fit_narrowest_chip_when_width(open_story: OpenStory, story_id: str, width: int) -> None:
    """差分を出している間は、幅 320・361・389px で札の幅が 5.5em 以上ある（正常系）。"""
    # 準備
    page = _open_narrow_story_at(open_story, story_id, width)
    # 実行
    measured = page.evaluate(FIT_SCRIPT)
    # 検証
    assert measured["chipEm"] >= CHIP_MIN_WIDTH_EM


@pytest.mark.parametrize(("story_id", "width", "brand_hidden"), NARROWEST_PACKING_CASES)
def test_fit_narrowest_packing_when_width(open_story: OpenStory, story_id: str, width: int, brand_hidden: bool) -> None:
    """幅 389px 以下では、要素の間隔 1px・左右の余白 8px、表示の設定・絞り込み・コメントのボタンの左右の余白と印と件数の間隔 2px（差分ありでも）に詰め、ツール名の文字を隠し、差分の札を出している間だけ印も隠す（正常系）。"""
    # 準備
    page = _open_narrow_story_at(open_story, story_id, width)
    # 実行
    measured = page.evaluate(BAR_SHAPE_SCRIPT)
    # 検証
    assert measured == {
        "gap": "1px",
        "padding": ["8px", "8px"],
        "buttons": [["2px", "2px", "2px"], ["2px", "2px", "2px"], ["2px", "2px", "2px"]],
        "nameHidden": True,
        "brandHidden": brand_hidden,
    }


@pytest.mark.parametrize(("story_id", "width", "size"), NARROWEST_ICON_BUTTON_CASES)
def test_fit_narrowest_icon_buttons_when_width(open_story: OpenStory, story_id: str, width: int, size: list[int]) -> None:
    """幅 389px 以下では、印だけのボタン（検索・変更履歴・ライト / ダーク）を高さ 32px・幅 28px に揃えて縮ませない。つながらず差分を出している間だけ幅 26px にする（正常系）。"""
    # 準備
    page = _open_narrow_story_at(open_story, story_id, width)
    # 実行
    sizes = page.evaluate(ICON_BUTTON_SIZES_SCRIPT)
    # 検証
    assert sizes == [size] * 3


def test_fit_narrowest_offline_diff_max_content(open_story: OpenStory) -> None:
    """つながらず差分を出す状態は、収める最大の中身（絞り込みのバッジ 2 桁・コメントの件数 99+）を出す（正常系）。"""
    # 準備・実行
    page = open_story(FIT_NARROWEST_OFFLINE_DIFF)
    # 検証
    assert page.locator(".filter-btn .fbadge").inner_text() == "12"
    assert page.locator(".comments-btn .count").inner_text() == "99+"


# 幅 390px の見た目（幅 389px 以下の詰め方が効かない既存の狭い幅の作り）の期待値
DEFAULT_BUTTON_PADDING = [["6px", "6px", "4px"]] * 3
DIFF_BUTTON_PADDING = [["4px", "4px", "4px"], ["6px", "6px", "4px"], ["6px", "6px", "4px"]]
WIDTH_390_SHAPES = [
    pytest.param(
        FIT_NARROWEST,
        {"gap": "3px", "buttons": DEFAULT_BUTTON_PADDING, "nameHidden": False, "brandHidden": False},
        id="fit-narrowest",
    ),
    pytest.param(
        FIT_NARROWEST_DIFF,
        {"gap": "8px", "buttons": DIFF_BUTTON_PADDING, "nameHidden": True, "brandHidden": False},
        id="fit-narrowest-diff",
    ),
    pytest.param(
        FIT_NARROWEST_OFFLINE,
        {"gap": "3px", "buttons": DEFAULT_BUTTON_PADDING, "nameHidden": False, "brandHidden": False},
        id="fit-narrowest-offline",
    ),
    pytest.param(
        OFFLINE_DIFF,
        {"gap": "8px", "buttons": DIFF_BUTTON_PADDING, "nameHidden": True, "brandHidden": True},
        id="filter-diff-offline-narrow",
    ),
]


@pytest.mark.parametrize(("story_id", "expected"), WIDTH_390_SHAPES)
def test_fit_narrowest_unchanged_when_width_390(open_story: OpenStory, story_id: str, expected: dict[str, object]) -> None:
    """幅 390px は既存の狭い幅の見た目のままで、幅 389px 以下の詰め方（間隔 1px・余白 2px）は効かない（正常系）。"""
    # 準備
    page = _open_narrow_story_at(open_story, story_id, 390)
    # 実行
    measured = page.evaluate(BAR_SHAPE_SCRIPT)
    # 検証
    assert measured == {"padding": ["10px", "10px"], **expected}


# 1px ずつ通す幅（既定の中身は 320〜1440px、最大の中身は 320〜389px。最大の中身の 390px 以上は FitWide 系の確かめが持つ）と、そのときの画面の高さ
DEFAULT_CONTENT_EVERY_WIDTH = range(320, 1441)
MAX_CONTENT_EVERY_WIDTH = range(320, 390)
NARROWEST_HEIGHT = 844

# ストーリーの引数の上書き: 既定の中身（絞り込みのバッジ 2・コメントの件数 3。FitNarrowestOfflineDiff は既定が最大の中身のため明示する）と、収める最大の中身（絞り込みのバッジ 12・コメントの件数 99+）
STORY_DEFAULT_CONTENT = "&args=filterCount:2;commentCount:3"
STORY_MAX_CONTENT = "&args=filterCount:12;commentCount:120"

# 4 つの状態を、既定の中身と最大の中身で開く組（引数の上書きと、1px ずつ通す幅）
NARROWEST_CONTENT_CASES = [
    pytest.param(story_id, args, widths, id=f"{story_id.removeprefix('preview-topbar--')}-{content}")
    for story_id in (FIT_NARROWEST, FIT_NARROWEST_DIFF, FIT_NARROWEST_OFFLINE, FIT_NARROWEST_OFFLINE_DIFF)
    for content, args, widths in (
        ("default", STORY_DEFAULT_CONTENT, DEFAULT_CONTENT_EVERY_WIDTH),
        ("max", STORY_MAX_CONTENT, MAX_CONTENT_EVERY_WIDTH),
    )
]

# 全てのボタンが収まっているときの BUTTONS_FIT_SCRIPT の結果
BUTTONS_ALL_FIT = {"pageFits": True, "barFits": True, "outside": []}


def _overflowing_widths(page: Page, widths: range) -> list[int]:
    """表示幅を 1px ずつ変えながらトップバーを測り、横にはみ出した幅（ボタンが幅の外に出た幅を含む）を返す。"""
    overflowing = []
    for width in widths:
        # 幅を変え、画面がその幅になってから測る
        page.set_viewport_size({"width": width, "height": NARROWEST_HEIGHT})
        page.wait_for_function(f"innerWidth === {width}")
        if page.evaluate(BUTTONS_FIT_SCRIPT) != BUTTONS_ALL_FIT:
            overflowing.append(width)
    return overflowing


@pytest.mark.parametrize(("story_id", "args", "widths"), NARROWEST_CONTENT_CASES)
def test_fit_narrowest_every_width(open_story: OpenStory, story_id: str, args: str, widths: range) -> None:
    """幅を 1px ずつ変えても（既定の中身は 320〜1440px、最大の中身は 320〜389px）、ページもトップバーも横にはみ出さず、全てのボタンと札の × が表示幅の中にある（正常系）。"""
    # 準備（ストーリーは 1 回だけ開き、表示幅を変えながら測る）
    page = open_story(f"{story_id}{args}")
    page.evaluate("document.fonts.ready")
    # 実行
    overflowing = _overflowing_widths(page, widths)
    # 検証（はみ出した幅をまとめて出す）
    assert overflowing == []


# 幅 390〜480px で全てのボタンを出す 4 つの状態（既定の引数が最大の中身: 絞り込みのバッジ 2 桁・コメントの件数 99+）
FIT_WIDE = "preview-topbar--fit-wide"
FIT_WIDE_DIFF = "preview-topbar--fit-wide-diff"
FIT_WIDE_OFFLINE = "preview-topbar--fit-wide-offline"
FIT_WIDE_OFFLINE_DIFF = "preview-topbar--fit-wide-offline-diff"

# 1px ずつ通す幅（最大の中身の 390px 以上）
FIT_WIDE_EVERY_WIDTH = range(390, 1441)

# 幅 389px 以下と同じ詰め方が効く幅（幅 480px 以下の両端）
FIT_WIDE_PACKED_WIDTHS = [390, 480]

# 差分の札か接続の状態を出している状態と、ツール名の印を隠すか（差分の札を出している状態だけ隠す）の組
FIT_WIDE_PACKED_CASES = [
    pytest.param(story_id, width, brand_hidden, id=f"{story_id.removeprefix('preview-topbar--')}-w{width}")
    for story_id, brand_hidden in (
        (FIT_WIDE_DIFF, True),
        (FIT_WIDE_OFFLINE, False),
        (FIT_WIDE_OFFLINE_DIFF, True),
    )
    for width in FIT_WIDE_PACKED_WIDTHS
]

# 詰め方が効く状態と幅の組
FIT_WIDE_PACKED_ICON_CASES = [
    pytest.param(story_id, width, id=f"{story_id.removeprefix('preview-topbar--')}-w{width}")
    for story_id in (FIT_WIDE_DIFF, FIT_WIDE_OFFLINE, FIT_WIDE_OFFLINE_DIFF)
    for width in FIT_WIDE_PACKED_WIDTHS
]

# 詰め方が効かないとき、同じ状態の既定の中身（絞り込みのバッジ 2・コメントの件数 3）と見た目が一致する組（最大の中身の状態、既定の中身の状態、幅）
FIT_WIDE_UNPACKED_CASES = [
    pytest.param(wide_story, default_story, width, id=f"{wide_story.removeprefix('preview-topbar--')}-w{width}")
    for wide_story, default_story, widths in (
        (FIT_WIDE, CONNECTED_HISTORY, [390, 435, 480, 481, 900]),
        (FIT_WIDE_DIFF, CONNECTED_DIFF, [481, 900]),
        (FIT_WIDE_OFFLINE, OFFLINE_HISTORY, [481, 900]),
        (FIT_WIDE_OFFLINE_DIFF, OFFLINE_DIFF, [481, 900]),
    )
    for width in widths
]


def _narrow_chip_widths(page: Page, widths: range) -> list[int]:
    """表示幅を 1px ずつ変えながら差分の札を測り、5.5em に届かなかった幅を返す。"""
    short = []
    for width in widths:
        # 幅を変え、画面がその幅になってから測る
        page.set_viewport_size({"width": width, "height": NARROWEST_HEIGHT})
        page.wait_for_function(f"innerWidth === {width}")
        if page.evaluate(FIT_SCRIPT)["chipEm"] < CHIP_MIN_WIDTH_EM:
            short.append(width)
    return short


@pytest.mark.parametrize("story_id", [FIT_WIDE, FIT_WIDE_DIFF, FIT_WIDE_OFFLINE, FIT_WIDE_OFFLINE_DIFF])
def test_fit_wide_every_width(open_story: OpenStory, story_id: str) -> None:
    """最大の中身（絞り込みのバッジ 2 桁・コメントの件数 99+）を、幅を 1px ずつ変えて 390〜1440px で開いても、ページもトップバーも横にはみ出さず、全てのボタンと札の × が表示幅の中にある（正常系）。"""
    # 準備（ストーリーは 1 回だけ開き、表示幅を変えながら測る）
    page = open_story(story_id)
    page.evaluate("document.fonts.ready")
    # 実行
    overflowing = _overflowing_widths(page, FIT_WIDE_EVERY_WIDTH)
    # 検証（はみ出した幅をまとめて出す）
    assert overflowing == []


@pytest.mark.parametrize("story_id", [FIT_WIDE_DIFF, FIT_WIDE_OFFLINE_DIFF])
def test_fit_wide_chip_every_width(open_story: OpenStory, story_id: str) -> None:
    """差分を出している間は、幅を 1px ずつ変えて 390〜1440px で開いても札の幅が 5.5em 以上ある（正常系）。"""
    # 準備（ストーリーは 1 回だけ開き、表示幅を変えながら測る）
    page = open_story(story_id)
    page.evaluate("document.fonts.ready")
    # 実行
    short = _narrow_chip_widths(page, FIT_WIDE_EVERY_WIDTH)
    # 検証（届かなかった幅をまとめて出す）
    assert short == []


@pytest.mark.parametrize(("story_id", "width", "brand_hidden"), FIT_WIDE_PACKED_CASES)
def test_fit_wide_packing_when_width(open_story: OpenStory, story_id: str, width: int, brand_hidden: bool) -> None:
    """件数の札が最大の中身で、差分の札か接続の状態を出している間は、幅 390・480px でも幅 389px 以下と同じ詰め方（間隔 1px・左右の余白 8px・3 つのボタンの余白と印と件数の間隔 2px）にし、ツール名の文字を隠す。差分の札を出している状態だけ印も隠す（正常系）。"""
    # 準備
    page = _open_narrow_story_at(open_story, story_id, width)
    # 実行
    measured = page.evaluate(BAR_SHAPE_SCRIPT)
    # 検証
    assert measured == {
        "gap": "1px",
        "padding": ["8px", "8px"],
        "buttons": [["2px", "2px", "2px"], ["2px", "2px", "2px"], ["2px", "2px", "2px"]],
        "nameHidden": True,
        "brandHidden": brand_hidden,
    }


@pytest.mark.parametrize(("story_id", "width"), FIT_WIDE_PACKED_ICON_CASES)
def test_fit_wide_icon_buttons_when_width(open_story: OpenStory, story_id: str, width: int) -> None:
    """件数の札が最大の中身で、差分の札か接続の状態を出している間は、幅 390・480px でも印だけのボタン（検索・変更履歴・ライト / ダーク）を高さ 32px・幅 28px に揃えて縮ませない（正常系）。"""
    # 準備
    page = _open_narrow_story_at(open_story, story_id, width)
    # 実行
    sizes = page.evaluate(ICON_BUTTON_SIZES_SCRIPT)
    # 検証
    assert sizes == [NARROWEST_ICON_BUTTON_SIZE] * 3


@pytest.mark.parametrize(("wide_story", "default_story", "width"), FIT_WIDE_UNPACKED_CASES)
def test_fit_wide_unpacked_when_width(open_story: OpenStory, wide_story: str, default_story: str, width: int) -> None:
    """詰め方が効かない組み合わせ（差分の札も接続の状態も出していない間の幅 390〜480px、全ての状態の幅 481px 以上）は、件数の札に `data-wide` が付いても、間隔・余白・ボタンの余白が既定の中身の同じ状態と一致する（正常系）。"""
    # 準備・実行
    wide = _open_narrow_story_at(open_story, wide_story, width).evaluate(BAR_SHAPE_SCRIPT)
    default = _open_narrow_story_at(open_story, default_story, width).evaluate(BAR_SHAPE_SCRIPT)
    # 検証
    assert wide == default


@pytest.mark.parametrize(
    ("filter_count", "comment_count", "filter_mark", "comments_mark"),
    [
        pytest.param(9, 99, None, None, id="filter9-comments99"),
        pytest.param(10, 99, "", None, id="filter10-comments99"),
        pytest.param(9, 100, None, "", id="filter9-comments100"),
        pytest.param(10, 100, "", "", id="filter10-comments100"),
    ],
)
def test_fit_wide_mark_when_count(
    open_story: OpenStory, filter_count: int, comment_count: int, filter_mark: str | None, comments_mark: str | None
) -> None:
    """絞り込みのバッジは 10 以上、コメントの件数は 99 を超えたときだけ、値を持たない `data-wide` を付ける（正常系）。"""
    # 準備・実行
    page = open_story(f"{FIT_WIDE}&args=filterCount:{filter_count};commentCount:{comment_count}")
    # 検証
    assert page.locator(".filter-btn .fbadge").get_attribute("data-wide") == filter_mark
    assert page.locator(".comments-btn .count").get_attribute("data-wide") == comments_mark
