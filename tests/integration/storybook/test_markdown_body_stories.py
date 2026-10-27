"""部品設計『Markdownの本文』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page
from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 位置の比べで許す差（px）
TOLERANCE_PX = 2

# 長文の列の幅（em）
LONG_COLUMN_EM = 24

# ストーリーが描き終わるまで待つ上限ミリ秒
STORY_TIMEOUT_MS = 15_000

# 見せ方を当て終わり、操作の後の描き直しが済むまで待つミリ秒
SETTLE_MS = 500

# 表の見出しのセルごとに、名前・列の種類・本体の最初の行のセルが折り返さないか・幅（px）を返す
_COLUMNS_JS = """() => [...document.querySelectorAll('.md thead th')].map((cell, index) => ({
    name: cell.firstChild.textContent.trim(),
    size: cell.dataset.colSize,
    nowrap: getComputedStyle(document.querySelectorAll('.md tbody tr:first-child td')[index]).whiteSpace === 'nowrap',
    width: cell.getBoundingClientRect().width,
}))"""

# 表の入れ物・枠・本文の横の送りの状態と、表の中身（本体）の幅を返す
_SCROLL_JS = """() => {
    const wrap = document.querySelector('.md .md-table-wrap');
    const frame = wrap.parentElement;
    const md = document.querySelector('.md');
    return {
        wrapScrolls: wrap.scrollWidth > wrap.clientWidth,
        mdScrolls: md.scrollWidth > md.clientWidth,
        fade: frame.hasAttribute('data-fade'),
        fadeShown: getComputedStyle(frame, '::after').content !== 'none',
        tableWidth: wrap.querySelector('tbody').getBoundingClientRect().width,
        mdWidth: md.getBoundingClientRect().width,
    };
}"""

# 本体の行ごとに、先頭のセルの背景色を返す
_ROW_COLORS_JS = """() => [...document.querySelectorAll('.md tbody tr')].map(
    (row) => getComputedStyle(row.firstElementChild).backgroundColor
)"""

# 見出しの行の上端と、本文のスクロール領域の上端（px）を返す
_HEAD_TOP_JS = """() => ({
    area: document.querySelector('.panel-body').getBoundingClientRect().top,
    head: document.querySelector('.md thead th').getBoundingClientRect().top,
})"""


def _open(open_story: OpenStory, state: str) -> Page:
    """ストーリーを開き、見せ方を当て終わるまで少し待つ。"""
    page = open_story(f"preview-markdownbody--{state}")
    page.wait_for_selector(".md > *", state="attached", timeout=STORY_TIMEOUT_MS)
    page.wait_for_timeout(SETTLE_MS)
    return page


def _columns(page: Page) -> dict[str, dict[str, Any]]:
    """表の列を、見出しの名前ごとの種類・折り返し・幅で返す。"""
    return {column["name"]: column for column in page.evaluate(_COLUMNS_JS)}


def test_column_widths(open_story: OpenStory) -> None:
    """8 列の表。短い列は折り返さず、長文の列は 24em で折り返し、中くらいの列は文節の区切りで折り返す。表は本文より広く、表の中だけで横に送れ、右端がフェードする（正常系）。"""
    # 準備・実行
    page = _open(open_story, "column-widths")
    columns = _columns(page)
    scroll = page.evaluate(_SCROLL_JS)
    font_size = page.eval_on_selector(".md thead th:last-child", "e => parseFloat(getComputedStyle(e).fontSize)")
    # 検証（列の種類と折り返し）
    assert (columns["ID"]["size"], columns["ID"]["nowrap"]) == ("short", True)
    assert columns["優先度"]["size"] == "short"
    assert columns["名前"]["size"] == "medium"
    assert (columns["説明"]["size"], columns["説明"]["nowrap"]) == ("long", False)
    # 検証（長文の列は 24em で折り返す。セルの余白の分だけ広い）
    assert LONG_COLUMN_EM * font_size <= columns["説明"]["width"] <= LONG_COLUMN_EM * font_size + 40
    # 検証（表は本文より広く、入れ物の中だけで送れ、右端がフェードする）
    assert scroll["tableWidth"] > scroll["mdWidth"]
    assert scroll["wrapScrolls"] is True
    assert scroll["mdScrolls"] is False
    assert scroll["fade"] is True
    assert scroll["fadeShown"] is True
    assert page.get_attribute(".md .md-table-wrap", "aria-label") == "本文の表"


def test_small_table(open_story: OpenStory) -> None:
    """2 列の表。本文の幅いっぱいに広げず、中身の幅で描き、フェードを出さない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "small-table")
    scroll = page.evaluate(_SCROLL_JS)
    # 検証
    assert scroll["tableWidth"] < scroll["mdWidth"]
    assert scroll["wrapScrolls"] is False
    assert scroll["fade"] is False


def test_pin_hover(open_story: OpenStory) -> None:
    """列の見出しにポインターを載せた。最後の列を除く見出しに固定のボタンが出る（正常系）。"""
    # 準備・実行
    page = _open(open_story, "pin-hover")
    buttons = page.locator(".md thead button.md-pin")
    # 検証（最後の列には無く、読み上げの名前は「{列名}まで固定」）
    assert buttons.count() == 7
    assert page.locator(".md thead th:last-child button.md-pin").count() == 0
    assert buttons.first.get_attribute("aria-label") == "IDまで固定"
    # 検証（フォーカスで出る。まだどの列も固定しない）
    assert page.eval_on_selector(".md thead button.md-pin:focus-visible", "e => getComputedStyle(e).opacity") == "1"
    assert page.locator(".md thead button.md-pin[aria-pressed=true]").count() == 0
    assert page.locator(".md .md-pinned").count() == 0


def test_pinned(open_story: OpenStory) -> None:
    """「名前」の固定のボタンを押して右へ送った。「名前」より左の列が左端に残り、固定した列の右端に影が付く（正常系）。"""
    # 準備・実行
    page = _open(open_story, "pinned")
    pressed = page.locator(".md thead button.md-pin[aria-pressed=true]")
    names = page.evaluate(
        "() => [...document.querySelectorAll('.md thead th.md-pinned')].map((cell) => cell.firstChild.textContent.trim())"
    )
    metrics = page.evaluate(
        """() => {
            const wrap = document.querySelector('.md .md-table-wrap');
            const edge = wrap.getBoundingClientRect().left;
            return {
                scrolled: wrap.scrollLeft > 0,
                lefts: [...document.querySelectorAll('.md thead th.md-pinned')].map((cell) => cell.getBoundingClientRect().left - edge),
            };
        }"""
    )
    # 検証（押した列だけ aria-pressed が true）
    assert pressed.count() == 1
    assert pressed.get_attribute("aria-label") == "名前まで固定"
    # 検証（ID・状態・名前の 3 列が固定され、右端の列に影が付く）
    assert names == ["ID", "状態", "名前"]
    assert page.locator(".md thead th.md-pin-edge").count() == 1
    assert page.eval_on_selector(".md thead th.md-pin-edge", "e => getComputedStyle(e).boxShadow") != "none"
    # 検証（右へ送っても、固定した列は入れ物の左端から並ぶ）
    assert metrics["scrolled"] is True
    assert abs(metrics["lefts"][0]) <= TOLERANCE_PX
    assert metrics["lefts"] == sorted(metrics["lefts"])


def test_pin_off(open_story: OpenStory) -> None:
    """表示の設定で列の固定をオフにした。見出しに固定のボタンを置かない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "pin-off")
    # 検証（見出しの固定は残る）
    assert page.locator(".md button.md-pin").count() == 0
    assert page.locator(".md .md-pinned").count() == 0
    assert page.locator(".md table.md-head-stick").count() == 1


def test_head_stuck(open_story: OpenStory) -> None:
    """縦に高さを限った本文の区画の中で、長い表の途中まで送った。見出しの行が区画の上端に残り、下の境に影が付く。表の下端を越えては残らない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "head-stuck")
    page.wait_for_selector(".md table.md-head-stuck")
    top = page.evaluate(_HEAD_TOP_JS)
    shadow = page.eval_on_selector(".md thead th", "e => getComputedStyle(e).boxShadow")
    page.eval_on_selector(".panel-body", "e => { e.scrollTop = e.scrollHeight; }")
    page.wait_for_timeout(SETTLE_MS)
    bounds = page.evaluate(
        """() => ({
            head: document.querySelector('.md thead th').getBoundingClientRect().bottom,
            table: document.querySelector('.md table').getBoundingClientRect().bottom,
        })"""
    )
    # 検証（見出しの行が区画の上端に見え、下の境に影が付く）
    assert abs(top["head"] - top["area"]) <= TOLERANCE_PX
    assert shadow != "none"
    # 検証（最後まで送ると、見出しの行は表の下端を越えない）
    assert bounds["head"] <= bounds["table"] + TOLERANCE_PX


def test_head_off(open_story: OpenStory) -> None:
    """表示の設定で見出しの固定をオフにした。見出しの行も本文と一緒に送られる（正常系）。"""
    # 準備・実行
    page = _open(open_story, "head-off")
    top = page.evaluate(_HEAD_TOP_JS)
    # 検証
    assert page.locator(".md table.md-head-stick").count() == 0
    assert top["head"] < top["area"] - TOLERANCE_PX


def test_stripes(open_story: OpenStory) -> None:
    """表示の設定でしま模様をオンにした。本体の行を 1 行おきに塗り分ける（正常系）。"""
    # 準備・実行
    page = _open(open_story, "stripes")
    colors = page.evaluate(_ROW_COLORS_JS)
    # 検証
    assert colors[0] == colors[2] == colors[4]
    assert colors[1] == colors[3] == colors[5]
    assert colors[0] != colors[1]


def test_stripes_in_diff(open_story: OpenStory) -> None:
    """本文の差分でしま模様をオンにした。足した行と消した行は差分の面のままで、開閉を置かない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "stripes-in-diff")
    colors = page.evaluate(_ROW_COLORS_JS)
    # 検証（足した行・消した行は、しま模様の面にならない）
    assert colors[1] != colors[0]
    assert colors[2] != colors[0]
    assert colors[1] != colors[2]
    assert page.locator(".md table.md-stripes").count() == 1
    assert page.locator(".md button.md-fold").count() == 0


def test_sections(open_story: OpenStory) -> None:
    """上位 2 つの階層の見出しの頭に開閉の矢印を置き、開いた状態で描く。中身の無い見出しには置かない。見出しの文言は選べる（正常系）。"""
    # 準備・実行
    page = _open(open_story, "sections")
    labels = page.evaluate("() => [...document.querySelectorAll('button.md-fold')].map((b) => b.getAttribute('aria-label'))")
    box = page.locator("button.md-fold").first.bounding_box()
    # 検証（候補・料金・まとめに矢印があり、内訳・付録には無い。全て開いている）
    assert labels == ["候補を開閉", "料金を開閉", "まとめを開閉"]
    assert page.locator("button.md-fold[aria-expanded=true]").count() == 3
    assert page.locator(".md-section-body[hidden]").count() == 0
    # 検証（矢印は 24px 以上。見出しの文言は矢印の外にあり、選べる）
    assert box is not None
    assert box["width"] >= 24
    assert box["height"] >= 24
    assert page.eval_on_selector("[data-heading=候補]", "e => getComputedStyle(e).userSelect") != "none"
    assert "候補" not in page.inner_text("[data-heading=候補] button.md-fold")


def test_folded(open_story: OpenStory) -> None:
    """「料金」の矢印を押して畳んだ。次の同じか上の階層の見出しまでを隠し、下の階層の見出しも一緒に隠す（正常系）。"""
    # 準備・実行
    page = _open(open_story, "folded")
    opened = page.eval_on_selector("[data-heading=候補] button.md-fold svg", "e => getComputedStyle(e).transform")
    closed = page.eval_on_selector("[data-heading=料金] button.md-fold svg", "e => getComputedStyle(e).transform")
    # 検証
    assert page.get_attribute("[data-heading=料金] button.md-fold", "aria-expanded") == "false"
    assert page.get_attribute("[data-heading=候補] button.md-fold", "aria-expanded") == "true"
    assert page.get_attribute("[data-heading=料金] + .md-section-body", "hidden") == "until-found"
    assert page.locator("[data-heading=内訳]").is_visible() is False
    assert page.locator("[data-heading=まとめ]").is_visible() is True
    # 検証（矢印の向きが変わる）
    assert opened != closed


def test_fold_off(open_story: OpenStory) -> None:
    """表示の設定でセクションの折りたたみをオフにした。見出しに開閉を置かない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "fold-off")
    # 検証
    assert page.locator("button.md-fold").count() == 0
    assert page.locator(".md-section-body").count() == 0


def test_code_block(open_story: OpenStory) -> None:
    """言語を書いたコードブロックは左上に言語の札を出し、ホバーで右上にコピーのボタンを出す。言語を書かないコードブロックには札を出さない。長い行は折り返す（正常系）。"""
    # 準備・実行
    page = _open(open_story, "code-block")
    blocks = page.locator(".md .md-code")
    button = blocks.nth(0).locator("button.code-copy")
    hidden = button.evaluate("e => getComputedStyle(e).opacity")
    blocks.nth(0).hover()
    shown = button.evaluate("e => getComputedStyle(e).opacity")
    # 検証（札は言語を書いたものだけ。札とボタンは `pre` の外）
    assert blocks.count() == 2
    assert blocks.nth(0).locator(".code-lang").inner_text() == "bash"
    assert blocks.nth(1).locator(".code-lang").count() == 0
    assert page.locator(".md .md-code > pre .code-copy, .md .md-code > pre .code-lang").count() == 0
    assert button.get_attribute("aria-label") == "コードをコピー"
    # 検証（ホバーで出る）
    assert (hidden, shown) == ("0", "1")
    # 検証（長い行は折り返し、横に送らない）
    assert page.eval_on_selector(".md .md-code > pre", "e => e.scrollWidth <= e.clientWidth")


def test_code_copied(open_story: OpenStory) -> None:
    """コピーのボタンを押した直後。ボタンがチェックのマーカーに変わり、クリップボードには札とボタンを含まないコードだけが入る（正常系）。"""
    # 準備・実行
    page = _open(open_story, "code-copied")
    first = page.locator(".md .md-code button.code-copy").nth(0)
    second = page.locator(".md .md-code button.code-copy").nth(1)
    # 検証（押した方だけアイコンが替わり、コピーしたことを伝える領域がある）
    assert first.locator("svg").count() == 1
    assert first.inner_html() != second.inner_html()
    assert page.locator(".md .md-code").first.locator("[role=status]").count() == 1


def test_callouts(open_story: OpenStory) -> None:
    """Alert の 5 種類の引用は、mdmark が種類の色の薄い面と細い枠の囲みと見出しで描き、見出しの頭に種類のアイコンを足す。マーカーの無い引用は囲みにならない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "callouts")
    titles = page.evaluate("() => [...document.querySelectorAll('.md .markdown-alert .markdown-alert-title')].map((e) => e.textContent.trim())")
    kinds = page.evaluate("() => [...document.querySelectorAll('.md .markdown-alert')].map((e) => e.className)")
    borders = page.evaluate("() => [...document.querySelectorAll('.md .markdown-alert')].map((e) => getComputedStyle(e).borderTopColor)")
    fills = page.evaluate("() => [...document.querySelectorAll('.md .markdown-alert')].map((e) => getComputedStyle(e).backgroundColor)")
    plain = page.locator(".md blockquote")
    # 検証（種類ごとの見出しとアイコン。マーカーの文字は残らない）
    assert titles == ["補足", "ヒント", "重要", "警告", "注意"]
    assert kinds == [f"markdown-alert markdown-alert-{kind}" for kind in ("note", "tip", "important", "warning", "caution")]
    assert page.locator(".md .markdown-alert .markdown-alert-title svg.icon").count() == 5
    assert "[!" not in page.inner_text(".md")
    # 検証（種類ごとに枠と面の色が違い、枠は細い）
    assert len(set(borders)) == 5
    assert len(set(fills)) == 5
    assert page.eval_on_selector(".md .markdown-alert", "e => getComputedStyle(e).borderTopWidth") == "1px"
    # 検証（マーカーの無い引用は囲みにならず、引用のまま残る）
    assert plain.count() == 1
    assert plain.evaluate("e => e.closest('.markdown-alert') === null")


def test_narrow(open_story: OpenStory) -> None:
    """画面の幅 390px。列の固定と固定のボタンを出さず、見出しの固定は残す。表は表の中だけで横に送れる（正常系）。"""
    # 準備・実行
    page = _open(open_story, "narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_timeout(SETTLE_MS)
    scroll = page.evaluate(_SCROLL_JS)
    # 検証（固定のボタンは隠れ、見出しの固定は残る）
    assert page.locator(".md button.md-pin:visible").count() == 0
    assert page.locator(".md table.md-head-stick").count() == 1
    # 検証（表は入れ物の中だけで送れ、ページは横に送らない）
    assert scroll["wrapScrolls"] is True
    assert scroll["mdScrolls"] is False
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def test_in_thread_post(open_story: OpenStory) -> None:
    """スレッドの書き込みの本文。コードブロックの言語の札とコピーのボタン、Alert の見出しのアイコンを当て、表の列の幅・フェード・固定・見出しの固定とセクションの開閉は当てない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "in-thread-post")
    # 検証（コードブロックの言語の札とコピーのボタンは当てる）
    assert page.locator(".md .md-code .code-lang").count() == 1
    assert page.locator(".md .md-code button.code-copy").count() == 2
    # 検証（Alert の見出しのアイコンは当てる）
    assert page.locator(".md .markdown-alert .markdown-alert-title svg.icon").count() == 5
    # 検証（表は mdmark のスタイルのまま。列の種類・固定・見出しの固定・フェードを当てない）
    assert page.locator(".md [data-col-size]").count() == 0
    assert page.locator(".md button.md-pin").count() == 0
    assert page.locator(".md table.md-head-stick").count() == 0
    assert page.locator(".md .md-table-frame[data-fade]").count() == 0
    # 検証（セクションの開閉は置かない）
    assert page.locator(".md button.md-fold").count() == 0
    assert page.locator(".md .md-section-body").count() == 0


# 範囲の外と中で、見せ方を当てた要素の数を返す（列の幅の印・フェード・固定のボタン・見出しの固定・しま模様・開閉の矢印。外は表の入れ物と開閉の矢印の数）
_DECORATED_JS = """() => {
    const decorated = [...document.querySelectorAll('.md th[data-col-size], .md [data-fade], .md button.md-pin, .md table.md-head-stick, .md table.md-stripes, .md button.md-fold')];
    const inside = (element) => element.closest('.mdmark-html') !== null;
    return {
        inside: decorated.filter(inside).length,
        outsideWraps: [...document.querySelectorAll('.md .md-table-wrap')].filter((e) => !inside(e)).length,
        outsideFolds: decorated.filter((e) => !inside(e) && e.matches('button.md-fold')).length,
    };
}"""


def test_embedded_html(open_story: OpenStory) -> None:
    """本文の `<!-- html -->` の範囲の中の表・見出しには、列の幅・フェード・固定・見出しの固定・しま模様・開閉を当てず、書いた HTML と mdmark の部品の見た目のまま描く。範囲の前後の表と見出しには今までどおり当てる（正常系）。"""
    # 準備・実行
    page = _open(open_story, "embedded-html")
    page.wait_for_selector(".md .mdmark-html figure", timeout=STORY_TIMEOUT_MS)
    decorated = page.evaluate(_DECORATED_JS)
    # 検証（範囲の中には、表・見出し・チャート・スライダーがあり、見せ方は当たっていない）
    assert page.locator(".md .mdmark-html table").count() >= 1
    assert page.locator(".md .mdmark-html :is(h1, h2, h3, h4)").count() >= 1
    assert page.locator(".md .mdmark-html figure.mdmark-diagram").count() >= 1
    assert page.locator(".md .mdmark-html input[type=range]").count() == 1
    assert decorated["inside"] == 0
    # 検証（範囲の中の表は、横に送る入れ物にも包まない）
    assert page.locator(".md .mdmark-html table").evaluate_all("tables => tables.map(t => t.closest('.md-table-wrap') === null)") == [True]
    # 検証（範囲の前後の表と見出しには当たっている）
    assert decorated["outsideWraps"] >= 1
    assert decorated["outsideFolds"] >= 1
