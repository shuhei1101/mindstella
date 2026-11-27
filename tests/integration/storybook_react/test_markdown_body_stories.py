"""部品設計『Markdownの本文.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from .storybook_react_fixture_types import OpenStory

# 狭い幅（動作環境の最も狭い画面の幅 320px）
NARROW_SIZE = {"width": 320, "height": 844}

# 位置の比べで許す差（px）
TOLERANCE_PX = 2

# ストーリーが描き終わるまで待つ上限ミリ秒
STORY_TIMEOUT_MS = 15_000

# 見せ方を当て終わり、操作の後の描き直しが済むまで待つミリ秒
SETTLE_MS = 500

# mdmark の表の入れ物・横のスクロールの区画・本文の区画の状態と、ピン止めした列の見出しを返す
_TABLE_JS = """() => {
    const scroll = document.querySelector('.mdmark .mdmark-table .mdmark-table-scroll');
    const md = document.querySelector('.mdmark');
    const edge = scroll.getBoundingClientRect().left;
    return {
        scrolls: scroll.scrollWidth > scroll.clientWidth,
        scrolled: scroll.scrollLeft > 0,
        mdScrolls: md.scrollWidth > md.clientWidth,
        pinned: [...scroll.querySelectorAll('thead th.is-pinned-col')].map((cell) => cell.textContent.trim()),
        pinnedLefts: [...scroll.querySelectorAll('thead th.is-pinned-col')].map((cell) => cell.getBoundingClientRect().left - edge),
    };
}"""

# 本文の区画・表の入れ物・セルのうち、画面の CSS が当てた見た目の規則（MindStella の表の見せ方の印）の数を返す
_OVERRIDES_JS = """() => document.querySelectorAll(
    '.mdmark [data-col-size], .mdmark [data-fade], .mdmark .md-table-wrap, .mdmark .md-table-frame, .mdmark button.md-pin, .mdmark .md-pinned, .mdmark table.md-head-stick, .mdmark table.md-stripes'
).length"""


def _open(open_story: OpenStory, state: str) -> Page:
    """ストーリーを開き、見せ方を当て終わるまで少し待つ。"""
    page = open_story(f"shared-markdownbody--{state}")
    page.wait_for_selector(".md > *", state="attached", timeout=STORY_TIMEOUT_MS)
    page.wait_for_timeout(SETTLE_MS)
    return page


def _pin_pressed(page: Page) -> dict[str, str | None]:
    """ピン止めのボタンの読み上げの名前ごとの aria-pressed を返す。"""
    return page.evaluate(
        "() => Object.fromEntries([...document.querySelectorAll('.mdmark button.mdmark-pin')].map((b) => [b.getAttribute('aria-label'), b.getAttribute('aria-pressed')]))"
    )


def test_mdmark_table(open_story: OpenStory) -> None:
    """8 列の表を mdmark の表で描く。並べ替え・ピン止め・列の幅の変更のボタンは mdmark のまま。表の中だけが横にスクロールし、描いた直後はどの列も左端に留まらない。画面の CSS の見せ方は無い（正常系）。"""
    # 準備・実行
    page = _open(open_story, "mdmark-table")
    table = page.evaluate(_TABLE_JS)
    pressed = _pin_pressed(page)
    # 検証（mdmark の表の部品で描き、列ごとのピン止めと列の幅の変更、並べ替えのボタンを持つ）
    assert page.locator(".mdmark .mdmark-table").count() == 1
    assert len(pressed) == 8
    assert page.locator(".mdmark .mdmark-table .mdmark-col-resize").count() == 8
    assert page.locator(".mdmark .mdmark-table button.mdmark-sort").count() >= 1
    # 検証（描いた直後はどの列もピン止めしない。mdmark の既定）
    assert [label for label, value in pressed.items() if value == "true"] == []
    assert table["pinned"] == []
    # 検証（表の中だけが横にスクロールし、本文の区画はスクロールしない）
    assert table["scrolls"] is True
    assert table["mdScrolls"] is False
    # 検証（画面の CSS の列の幅・フェード・固定・しま模様は無い）
    assert page.evaluate(_OVERRIDES_JS) == 0


def test_pinned_columns(open_story: OpenStory) -> None:
    """「ID」と「名前」のピン止めのボタンを押して右へスクロールした。ID と名前の 2 列が左端に留まり、状態の列は留まらない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "pinned-columns")
    table = page.evaluate(_TABLE_JS)
    pressed = _pin_pressed(page)
    # 検証（ID と名前のピン止めのボタンが押された状態）
    assert [label for label, value in pressed.items() if value == "true"] == ["「ID」の列をピン止め", "「名前」の列をピン止め"]
    assert table["pinned"] == ["ID", "名前"]
    # 検証（右へスクロールしても、2 列は表の左端から並んで見えている）
    assert table["scrolled"] is True
    assert abs(table["pinnedLefts"][0]) <= TOLERANCE_PX
    assert table["pinnedLefts"] == sorted(table["pinnedLefts"])
    status_left = page.evaluate(
        "() => { const s = document.querySelector('.mdmark .mdmark-table-scroll'); return [...s.querySelectorAll('thead th')][1].getBoundingClientRect().left - s.getBoundingClientRect().left; }"
    )
    assert status_left < 0


def test_opaque_background(open_story: OpenStory) -> None:
    """本文の背景は透明で、ピン止めのボタンで留めた列は周りの面の色（`--card` を指定した `--mdmark-color-bg-opaque`）で塗られる（正常系）。"""
    # 準備・実行
    page = _open(open_story, "opaque-background")
    colors = page.evaluate(
        """() => {
            const md = document.querySelector('.mdmark');
            const probe = document.createElement('div');
            probe.style.backgroundColor = 'var(--card)';
            md.appendChild(probe);
            const surface = getComputedStyle(probe).backgroundColor;
            probe.remove();
            return {
                md: getComputedStyle(md).backgroundColor,
                pinned: getComputedStyle(document.querySelector('.mdmark td.is-pinned-col')).backgroundColor,
                surface,
            };
        }"""
    )
    # 検証
    assert colors["md"] == "rgba(0, 0, 0, 0)"
    assert colors["pinned"] == colors["surface"]
    assert page.evaluate(_TABLE_JS)["scrolled"] is True


def test_sections(open_story: OpenStory) -> None:
    """上位 2 つの階層の見出しの頭に開閉の矢印を置き、開いた状態で描く。中身の無い見出しには置かない。見出しの文言は選べる（正常系）。"""
    # 準備・実行
    page = _open(open_story, "sections")
    labels = page.evaluate(
        "() => [...document.querySelectorAll('button.md-fold')].map((b) => b.getAttribute('aria-label'))"
    )
    box = page.locator("button.md-fold").first.bounding_box()
    # 検証（候補・料金・まとめに矢印があり、内訳・付録には無い。全て開いている）
    assert labels == ["候補を開閉", "料金を開閉", "まとめを開閉"]
    assert page.locator("button.md-fold[aria-expanded=true]").count() == 3
    assert page.locator(".md-section-body[hidden]").count() == 0
    # 検証（矢印は 24px 以上。見出しの文言は矢印の外にあり、選べる）
    assert box is not None
    assert box["width"] >= 24
    assert box["height"] >= 24
    assert (
        page.eval_on_selector(
            "h2:has(> button.md-fold[aria-label=候補を開閉])", "e => getComputedStyle(e).userSelect"
        )
        != "none"
    )
    assert "候補" not in page.inner_text("button.md-fold[aria-label=候補を開閉]")


def test_folded(open_story: OpenStory) -> None:
    """「料金」の矢印を押して畳んだ。次の同じか上の階層の見出しまでを隠し、下の階層の見出しも一緒に隠す（正常系）。"""
    # 準備・実行
    page = _open(open_story, "folded")
    opened = page.eval_on_selector(
        "button.md-fold[aria-label=候補を開閉] svg", "e => getComputedStyle(e).transform"
    )
    closed = page.eval_on_selector(
        "button.md-fold[aria-label=料金を開閉] svg", "e => getComputedStyle(e).transform"
    )
    # 検証
    assert page.get_attribute("button.md-fold[aria-label=料金を開閉]", "aria-expanded") == "false"
    assert page.get_attribute("button.md-fold[aria-label=候補を開閉]", "aria-expanded") == "true"
    assert (
        page.get_attribute(
            "h3:has(> button.md-fold[aria-label=料金を開閉]) + .md-section-body", "hidden"
        )
        == "until-found"
    )
    assert page.locator("h4:text-is('内訳')").is_visible() is False
    assert page.locator("h2:has(> button.md-fold[aria-label=まとめを開閉])").is_visible() is True
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
    """言語を書いたコードブロックは mdmark のコードブロックのバー（言語の札・コピー）と行の部品と色分けで描き、画面の言語の札とコピーのボタンを重ねない。長い行は折り返さず、コードブロックの中だけで横にスクロールできる。言語の札とコピーのボタンは横にスクロールしても同じ位置に残る（正常系）。"""
    # 準備・実行
    page = _open(open_story, "code-block")
    blocks = page.locator(".md .mdmark-code")
    # 検証（札は言語を書いたものだけ。コピーのボタンはコードブロック 1 つに 1 つ。画面の札とボタンは無い）
    assert blocks.count() == 2
    assert blocks.nth(0).locator(".mdmark-code-lang").inner_text() == "bash"
    assert blocks.nth(1).locator(".mdmark-code-lang").count() == 0
    assert [blocks.nth(i).locator("button.mdmark-code-copy").count() for i in range(2)] == [1, 1]
    assert page.locator(".md .md-code, .md .code-lang, .md button.code-copy").count() == 0
    # 検証（長い行は折り返さず、コードブロックの中で横にスクロールする。札とボタンはスクロールしても動かない）
    pre = blocks.nth(0).locator("pre")
    before = blocks.nth(0).evaluate(LABEL_AND_BUTTON_POSITIONS_JS)
    pre.evaluate("e => { e.scrollLeft = e.scrollWidth; }")
    after = blocks.nth(0).evaluate(LABEL_AND_BUTTON_POSITIONS_JS)
    assert pre.evaluate("e => e.scrollWidth > e.clientWidth && e.scrollLeft > 0")
    assert pre.get_attribute("tabindex") == "0"
    assert before == after


# 言語の札とコピーのボタンの位置（コードブロックの枠からの距離）を読む
LABEL_AND_BUTTON_POSITIONS_JS = """(block) => {
    const box = block.getBoundingClientRect();
    return [".mdmark-code-lang", "button.mdmark-code-copy"].map((selector) => {
        const rect = block.querySelector(selector).getBoundingClientRect();
        return [rect.left - box.left, rect.top - box.top];
    });
}"""


def test_code_copied(open_story: OpenStory) -> None:
    """mdmark のコピーのボタンを押した直後。ボタンの見た目は mdmark のままで、コピーしたことを伝える領域がある（正常系）。"""
    # 準備・実行
    page = _open(open_story, "code-copied")
    first = page.locator(".md .mdmark-code").nth(0)
    # 検証（mdmark のボタンと状態の領域がある。画面のボタンは無い）
    assert first.locator("button.mdmark-code-copy").count() == 1
    assert first.locator("[role=status]").count() == 1
    assert page.locator(".md button.code-copy").count() == 0


def test_code_markdown_raw(open_story: OpenStory) -> None:
    """言語 markdown のコードブロック。描いた結果で出し、バーの「Raw」を押すと元の Markdown のコードに切り替わる（正常系）。"""
    # 準備・実行（ストーリーの play で「Raw」を押す）
    page = _open(open_story, "code-markdown-raw")
    raw = page.locator(".md .mdmark-code button.mdmark-code-raw")
    raw.wait_for(timeout=STORY_TIMEOUT_MS)
    page.wait_for_timeout(SETTLE_MS)
    # 検証
    assert raw.get_attribute("aria-pressed") == "true"
    assert "## 見出し" in page.locator(".md .mdmark-code pre").first.inner_text()


def test_code_indent_guides(open_story: OpenStory) -> None:
    """言語 python の 2 階層の字下げを持つコードブロック。字下げの縦線と行の開閉のボタンがあり、キーワードが色分けされる（正常系）。"""
    # 準備・実行
    page = _open(open_story, "code-indent-guides")
    block = page.locator(".md .mdmark-code").first
    block.locator(".mdmark-code-line").first.wait_for(timeout=STORY_TIMEOUT_MS)
    # 検証（字下げの行と縦線の背景・開閉のボタン・色分け）
    assert block.locator('.mdmark-code-line[data-indent="2"]').count() >= 1
    assert block.locator('.mdmark-code-line[data-indent="1"]').first.evaluate("e => getComputedStyle(e).backgroundImage") != "none"
    assert block.locator("button.mdmark-code-fold").count() >= 1
    assert block.locator(".hljs-keyword").count() >= 1


# 見出しごとに包む要素の直下の子の要素名と上の間（px）を読む
SECTION_GAPS_JS = """() => {
    const body = document.querySelector('.md .md-section-body');
    const space = parseFloat(getComputedStyle(document.querySelector('.mdmark')).getPropertyValue('--mdmark-space')) * parseFloat(getComputedStyle(document.documentElement).fontSize);
    return { space, children: [...body.children].map((e) => [e.tagName, parseFloat(getComputedStyle(e).marginBlockStart)]) };
}"""


def test_section_spacing(open_story: OpenStory) -> None:
    """見出しの下に段落・表・map の図・リストと小見出しを並べた本文。見出しごとに包む要素の直下のブロック同士に mdmark の本文と同じ間が空き、小見出しの上の間は mdmark の見出しの間のまま（正常系）。"""
    # 準備・実行
    page = _open(open_story, "section-spacing")
    page.wait_for_selector(".md .md-section-body h3", timeout=STORY_TIMEOUT_MS)
    gaps = page.evaluate(SECTION_GAPS_JS)
    # 検証（先頭の後のブロックは mdmark の間。h3 は mdmark の h3 の 1.75 倍）
    blocks = [(tag, gap) for tag, gap in gaps["children"][1:] if tag != "H3"]
    heading = [gap for tag, gap in gaps["children"] if tag == "H3"]
    assert len(blocks) >= 4
    assert all(abs(gap - gaps["space"]) <= TOLERANCE_PX for _, gap in blocks)
    assert len(heading) == 1
    assert abs(heading[0] - gaps["space"] * 1.75) <= TOLERANCE_PX


def test_external_link(open_story: OpenStory) -> None:
    """本文に外部の URL へのリンクと、同じオリジン・# で始まるリンクを持つ。外部の URL へのリンクだけが target="_blank" と rel="noopener noreferrer" を持つ（正常系）。"""
    # 準備・実行
    page = _open(open_story, "external-link")
    links = page.evaluate("() => [...document.querySelectorAll('.md a[href]')].map((a) => [a.textContent, a.getAttribute('target'), a.getAttribute('rel')])")
    # 検証
    assert ["外部のページ", "_blank", "noopener noreferrer"] in links
    assert ["同じオリジン", None, None] in links
    assert ["D-1", None, None] in links


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
    """画面の幅 320px。表は mdmark の表のまま表の中だけで横にスクロールし、本文の区画もページも横にスクロールしない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_timeout(SETTLE_MS)
    table = page.evaluate(_TABLE_JS)
    # 検証
    assert page.locator(".mdmark .mdmark-table").count() == 1
    assert table["scrolls"] is True
    assert table["mdScrolls"] is False
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def test_in_thread_post(open_story: OpenStory) -> None:
    """スレッドの書き込みの本文。コードブロックは mdmark のバー・行の部品・色分けのまま描き、Alert の見出しのアイコンを当て、表は mdmark の表の機能をオフにした共通のスタイルのまま描き、セクションの開閉は当てない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "in-thread-post")
    # 検証（コードブロックは mdmark のバーのまま。画面の札とボタンは無い）
    assert page.locator(".md .mdmark-code .mdmark-code-lang").count() == 1
    assert page.locator(".md .mdmark-code button.mdmark-code-copy").count() == 2
    assert page.locator(".md .md-code, .md button.code-copy").count() == 0
    # 検証（Alert の見出しのアイコンは当てる）
    assert page.locator(".md .markdown-alert .markdown-alert-title svg.icon").count() == 5
    # 検証（表は mdmark の表の部品にせず、ピン止め・並べ替えを持たない。画面の CSS の見せ方も無い）
    assert page.locator(".md table").count() >= 1
    assert page.locator(".md .mdmark-table").count() == 0
    assert page.locator(".md button.mdmark-pin").count() == 0
    assert page.evaluate(_OVERRIDES_JS) == 0
    # 検証（セクションの開閉は置かない）
    assert page.locator(".md button.md-fold").count() == 0
    assert page.locator(".md .md-section-body").count() == 0


def test_embedded_html(open_story: OpenStory) -> None:
    """本文の `<!-- html -->` の範囲の中の見出しには開閉を当てず、書いた HTML と mdmark の部品の見た目のまま描く。範囲の前後の見出しには開閉を当てる（正常系）。"""
    # 準備・実行
    page = _open(open_story, "embedded-html")
    page.wait_for_selector(".md .mdmark-html figure", timeout=STORY_TIMEOUT_MS)
    folds = page.evaluate(
        "() => [...document.querySelectorAll('.md button.md-fold')].map((e) => e.closest('.mdmark-html') !== null)"
    )
    # 検証（範囲の中には、表・見出し・チャート・スライダーがある）
    assert page.locator(".md .mdmark-html table").count() >= 1
    assert page.locator(".md .mdmark-html :is(h1, h2, h3, h4)").count() >= 1
    assert page.locator(".md .mdmark-html figure.mdmark-diagram").count() >= 1
    assert page.locator(".md .mdmark-html input[type=range]").count() == 1
    # 検証（開閉は範囲の外の見出しにだけ置き、画面の CSS の表の見せ方はどこにも無い）
    assert folds != []
    assert all(inside is False for inside in folds)
    assert page.evaluate(_OVERRIDES_JS) == 0


def test_table_in_diff(open_story: OpenStory) -> None:
    """本文の差分の中の表。足した行・消した行の面の色と消した行の取り消し線が、ピン止めのボタンで留めた列のセルにも付き、開閉を置かない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "table-in-diff")
    cells = page.evaluate(
        """() => {
            const style = (selector) => {
                const cell = document.querySelector(selector);
                return [getComputedStyle(cell).backgroundColor, getComputedStyle(cell).textDecorationLine];
            };
            return {
                plain: style('.mdmark tbody tr:not(.df-row) td.is-pinned-col'),
                added: style('.mdmark tr.df-add td.is-pinned-col'),
                removed: style('.mdmark tr.df-del td.is-pinned-col'),
            };
        }"""
    )
    # 検証（ピン止めした列のセルにも、足した行・消した行の面の色が付き、消した行は取り消し線を持つ）
    assert cells["added"][0] != cells["plain"][0]
    assert cells["removed"][0] != cells["plain"][0]
    assert cells["added"][0] != cells["removed"][0]
    assert cells["removed"][1] == "line-through"
    assert cells["plain"][1] == "none"
    # 検証（開閉を置かない）
    assert page.locator(".md button.md-fold").count() == 0


def test_diff_rendered(open_story: OpenStory) -> None:
    """差分の表示で「描いた結果」。書き換えた段落と追加した箇条書きの項目は追加、削除した段落は削除の差分のブロックで出し、変わった単語は出さない（正常系）。"""
    # 準備・実行
    page = _open(open_story, "diff-rendered")
    page.wait_for_selector(".md .mdmark-diff-block", timeout=STORY_TIMEOUT_MS)
    # 検証（追加と削除のブロックがあり、削除した段落は変更前の位置に出る）
    added = page.locator('.md .mdmark-diff-block[data-kind="add"]')
    removed = page.locator('.md .mdmark-diff-block[data-kind="del"]')
    assert added.count() >= 2
    assert removed.count() >= 1
    assert "保持する回数を超えたものから削除する" in removed.first.inner_text()
    assert page.locator(".md .mdmark-diff-word").count() == 0
    # 検証（記号は本文の区画の中に見える）
    sign = page.locator(".md .mdmark-diff-block-sign").first.bounding_box()
    body = page.locator(".md").first.bounding_box()
    assert sign is not None and body is not None
    assert sign["x"] >= body["x"] - TOLERANCE_PX


def test_diff_source(open_story: OpenStory) -> None:
    """差分の表示で「原文の差分」。mdmark の「変更表示」のボタンとリビジョンの欄を配置せず（`diffControls: false`）、選んだ時点と今の行の差分を出し、書き換えた行の変わった単語を濃い色にする（正常系）。"""
    # 準備・実行
    page = _open(open_story, "diff-source")
    page.wait_for_selector(".mdmark-diff-line", timeout=STORY_TIMEOUT_MS)
    # 検証（削除した行と追加した行）
    assert page.locator('.mdmark-diff-line[data-kind="del"]').count() >= 1
    assert page.locator('.mdmark-diff-line[data-kind="add"]').count() >= 1
    assert page.locator(".mdmark-diff-word").count() >= 1
    # 検証（前と後のリビジョンの欄を配置しない）
    assert page.locator(".mdmark-diff-picker").count() == 0


def test_diff_unchanged(open_story: OpenStory) -> None:
    """差分の表示で、選んだ時点から変わっていない本文。色を付けずに今の本文だけを出す（正常系）。"""
    # 準備・実行
    page = _open(open_story, "diff-unchanged")
    # 検証
    assert page.locator(".md .mdmark-diff-block").count() == 0
    assert page.locator(".mdmark-diff-line").count() == 0
    assert "まとめて配置する" in page.inner_text(".md")


# 部品設計の状態
STATES = (
    "mdmark-table",
    "pinned-columns",
    "opaque-background",
    "sections",
    "folded",
    "fold-off",
    "code-block",
    "code-copied",
    "code-markdown-raw",
    "code-indent-guides",
    "section-spacing",
    "external-link",
    "callouts",
    "narrow",
    "in-thread-post",
    "embedded-html",
    "table-in-diff",
    "diff-rendered",
    "diff-source",
    "diff-unchanged",
    "wide-table-in-narrow-pane",
    "audio-embed",
    "audio-embed-narrow",
)


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = _open(open_story, state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


# 音声の再生バーの高さと、上下を切る祖先の有無を読む
AUDIO_JS = """() => {
  const audio = document.querySelector('.md audio');
  const box = audio.getBoundingClientRect();
  let clipped = false;
  for (let e = audio.parentElement; e && e !== document.body; e = e.parentElement) {
    const r = e.getBoundingClientRect();
    if (getComputedStyle(e).overflowY !== 'visible' && (r.top > box.top + 0.5 || r.bottom < box.bottom - 0.5)) clipped = true;
  }
  return { height: box.height, clipped, controls: audio.controls };
}"""


def test_audio_embed(open_story: OpenStory) -> None:
    """本文に埋め込んだ音声。再生バーを、祖先の高さ・overflow で上下を切らずに全体を表示する（正常系）。"""
    # 準備・実行
    page = _open(open_story, "audio-embed")
    page.wait_for_selector(".md audio", timeout=STORY_TIMEOUT_MS)
    measured = page.evaluate(AUDIO_JS)
    # 検証
    assert measured["controls"] is True
    assert measured["height"] > 0
    assert measured["clipped"] is False


def test_audio_embed_narrow(open_story: OpenStory) -> None:
    """幅 390px で埋め込んだ音声。再生バーを本文の幅に収め、上下を切らず、本文の区画を横にスクロールさせない（正常系）。"""
    # 準備
    page = _open(open_story, "audio-embed-narrow")
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_selector(".md audio", timeout=STORY_TIMEOUT_MS)
    # 実行
    measured = page.evaluate(AUDIO_JS)
    audio_right = page.locator(".md audio").evaluate("e => e.getBoundingClientRect().right")
    body_right = page.locator(".md").evaluate("e => e.getBoundingClientRect().right")
    # 検証
    assert measured["clipped"] is False
    assert audio_right <= body_right + 0.5
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
