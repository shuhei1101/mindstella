"""画面設計『詳細の全画面』と『図の拡大』（全画面の中身の切り替え）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from preview_a11y_checks import axe_rule_results
from preview_body_scroll_helpers import (
    LONG_BODY,
    LONG_LINES_BODY,
    NEW_DECISION,
    SCROLLABLE_REGION_RULE,
    SETTLED_SCROLL_TOP_JS,
    overflows_horizontally,
)
from preview_comment_helpers import PILL, THREE_LINE_BODY, UPDATE_TIMEOUT_MS, select_text_for_pill
from preview_fixture_types import (
    ID_BUTTON_MIN_SIZE_PX,
    ID_BUTTON_SIZE_JS,
    OpenPreview,
    WritePreview,
    WriteReviewPreview,
    WriteSamplePreview,
)
from workspace_fixtures import CallTool, MakeComment, MakeItem, MakeWorkspace

# 選んだ範囲が入口を出す判定を終えるまで待つミリ秒
SELECTION_SETTLE_MS = 400

# 図を描き終わるまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000

# 全画面の本文のスクロール領域と、Tab で本文の前に来る見出しの最後のボタン
FULL_BODY = "dialog.full .panel-body"
FULL_HEAD_LAST_BUTTON = "dialog.full .panel-head button:not([disabled])"

# 全画面のモーダルの外側（後ろの幕）を押す位置（画面の左上の隅）
BACKDROP_POINT = (4, 4)


def _open_full(page: Page) -> None:
    """全画面に切り替えるボタンを押し、全画面が開くのを待つ。"""
    page.click('aside.panel button[data-act="full"]')
    page.wait_for_selector("dialog.full[open]")


def test_open_and_restore(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """全画面に切り替えても履歴に積まず、元の大きさに戻すとパネルへ戻る（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2")
    history_length = page.evaluate("history.length")
    panel_button = 'aside.panel button[data-act="full"]'
    assert page.get_attribute(panel_button, "aria-label") == "全画面表示"
    assert page.get_attribute(panel_button, "aria-pressed") is None
    # 実行
    _open_full(page)
    # 検証
    # 全画面の間は読み上げ名を「元の大きさに戻す」にし、押された状態は持たない
    full_button = 'dialog.full button[data-act="full"]'
    assert page.get_attribute(full_button, "aria-label") == "元の大きさに戻す"
    assert page.get_attribute(full_button, "aria-pressed") is None
    assert "full=1" in page.evaluate("location.hash")
    assert page.evaluate("history.length") == history_length
    assert page.inner_text("dialog.full .d-title") == "D-2の題"
    # 全てを閉じるボタンは置かない
    assert page.locator('dialog.full button[data-act="close"]').count() == 0
    page.click('dialog.full button[data-act="full"]')
    page.wait_for_selector("aside.panel.open")
    assert page.locator("dialog.full").count() == 0
    assert "full=" not in page.evaluate("location.hash")


def test_restore_by_escape(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """Esc で元の大きさ（詳細パネル）に戻る（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2&full=1")
    page.wait_for_selector("dialog.full[open]")
    # 実行
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_selector("aside.panel.open")
    assert page.locator("dialog.full").count() == 0
    assert "id=D-2" in page.evaluate("location.hash")


def test_restore_by_backdrop(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """後ろの幕（外側）を押すと、元の大きさに戻る（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2&full=1")
    page.wait_for_selector("dialog.full[open]")
    # 実行
    page.mouse.click(*BACKDROP_POINT)
    # 検証
    page.wait_for_selector("aside.panel.open")
    assert page.locator("dialog.full").count() == 0


def test_navigate_inside(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """全画面の中で項目を移ると履歴に積み、戻る・進むで行き来できる（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2&full=1")
    page.wait_for_selector("dialog.full[open]")
    history_length = page.evaluate("history.length")
    # 実行
    page.click("dialog.full .d-sec:has(h3:text-is('前提')) button.idlink")
    page.wait_for_function(
        "document.querySelector('dialog.full .d-title')?.textContent === 'D-1の題'"
    )
    # 検証
    assert page.evaluate("history.length") == history_length + 1
    page.click('dialog.full button[data-act="back"]')
    page.wait_for_function(
        "document.querySelector('dialog.full .d-title')?.textContent === 'D-2の題'"
    )


def test_diagram_zoom_switches_content(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """全画面の中で図を拡大すると、モーダルを重ねずに中身を図の拡大へ切り替え、閉じると本文へ戻る（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-3&full=1")
    page.wait_for_selector("dialog.full .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 実行
    page.click('dialog.full button[data-act="diagram-zoom"]')
    page.wait_for_selector("dialog.full .full-viewer .v-stage svg")
    # 検証
    assert page.locator("dialog[open]").count() == 1
    assert not page.is_visible("dialog.full .panel-body")
    page.click('dialog.full button[data-act="diagram-close"]')
    page.wait_for_selector("dialog.full .panel-body", state="visible")
    assert page.locator("dialog.full .full-viewer").count() == 0


def test_id_button_size(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """関係する項目（前提・後続の項目・関連タスク）の ID のボタンは、見えている枠が縦横 24px 以上である（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2&full=1")
    page.wait_for_selector("dialog.full[open]")
    # 実行
    sizes = page.eval_on_selector_all("dialog.full .d-sec button.idlink", ID_BUTTON_SIZE_JS)
    # 検証
    assert sizes["count"] > 0
    assert sizes["smallest"] >= ID_BUTTON_MIN_SIZE_PX


def test_comment_input(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """サーバーの配信で開くと、コメントの入力を全画面の下端に出す。パネルと行き来しても書きかけを保つ（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2")
    page.fill("aside.panel form.send textarea", "書きかけ")
    # 実行
    _open_full(page)
    # 検証
    assert page.get_attribute("dialog.full form.send", "data-id") == "D-2"
    assert page.inner_text("dialog.full form.send label.send-label") == "D-2 へのコメント"
    assert page.input_value("dialog.full form.send textarea") == "書きかけ"
    dialog_box = page.locator("dialog.full").bounding_box()
    form_box = page.locator("dialog.full form.send").bounding_box()
    assert dialog_box is not None
    assert form_box is not None
    assert abs((dialog_box["y"] + dialog_box["height"]) - (form_box["y"] + form_box["height"])) <= 2
    # 全画面から戻しても書きかけを保つ
    page.click('dialog.full button[data-act="full"]')
    page.wait_for_selector("aside.panel.open")
    assert page.input_value("aside.panel form.send textarea") == "書きかけ"


def test_comment_input_keeps_location(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """パネルで添えた箇所は、全画面へ切り替えても保つ（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("A-1"), bodies={"A-1.md": THREE_LINE_BODY})
    page = open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel .md")
    select_text_for_pill(page, "aside.panel .md", "言い換えたい文")
    page.click(PILL)
    # 実行
    _open_full(page)
    # 検証
    assert page.inner_text("dialog.full .send-loc-name") == "本文 2 行目"
    assert page.inner_text("dialog.full .send-quote") == "言い換えたい文"


def test_review_comments(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
) -> None:
    """全画面にも、その項目へのレビュー中のコメントを読むだけの形で出す（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("D-1"), comments=(make_comment("C-1", target="D-1", body="案 A にする"),)
    )
    # 実行
    page = open_preview(url, "#tab=decisions&id=D-1&full=1")
    page.wait_for_selector("dialog.full[open] .d-review")
    # 検証
    assert page.inner_text("dialog.full .d-review h3") == "レビュー中のコメント1"
    assert page.inner_text("dialog.full .d-review .review-body") == "案 A にする"
    assert page.locator("dialog.full .d-review button").count() == 0


def test_selection_entry(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """全画面でも本文の文を選ぶと入口を出し、入口はモーダルの中に置く。押すと箇所を添える（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("A-1"), bodies={"A-1.md": THREE_LINE_BODY})
    page = open_preview(url, "#tab=docs&id=A-1&full=1")
    page.wait_for_selector("dialog.full[open] .md")
    # 実行
    select_text_for_pill(page, "dialog.full .md", "言い換えたい文")
    # 検証
    assert page.locator(f"dialog.full {PILL}").count() == 1
    page.click(PILL)
    assert page.inner_text("dialog.full .send-loc-name") == "本文 2 行目"


def test_selection_entry_when_diagram_zoomed(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """図の拡大を開いている間は、選んだ箇所のコメントの入口を出さない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-3&full=1")
    page.wait_for_selector("dialog.full .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    page.click('dialog.full button[data-act="diagram-zoom"]')
    page.wait_for_selector("dialog.full .full-viewer .v-stage svg")
    # 実行
    page.evaluate(
        "(() => { const range = document.createRange(); range.selectNodeContents(document.querySelector('dialog.full .full-viewer')); getSelection().removeAllRanges(); getSelection().addRange(range); })()"
    )
    page.wait_for_timeout(SELECTION_SETTLE_MS)
    # 検証
    assert page.locator(PILL).count() == 0


def _open_long_body_full(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> Page:
    """フォーカスできる要素を持たない、縦にあふれる本文の項目を全画面で開く。"""
    url = write_preview(make_item("A-1"), bodies={"A-1.md": LONG_BODY})
    page = open_preview(url, "#tab=docs&id=A-1&full=1")
    page.wait_for_selector(f"{FULL_BODY} .md")
    # 前提: 本文の中にフォーカスできる要素は無く、縦にあふれている
    assert page.locator(f"{FULL_BODY} :is(a[href], button, input, textarea, select, [tabindex])").count() == 0
    assert page.eval_on_selector(FULL_BODY, "e => e.scrollHeight > e.clientHeight")
    return page


def test_body_scroll_region_attributes(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """全画面の本文のスクロール領域は、フォーカスでき、読み上げの名前「詳細の本文」の領域になる（正常系）。"""
    # 準備・実行
    page = _open_long_body_full(write_preview, open_preview, make_item)
    # 検証
    assert page.get_attribute(FULL_BODY, "tabindex") == "0"
    assert page.get_attribute(FULL_BODY, "role") == "region"
    assert page.get_attribute(FULL_BODY, "aria-label") == "詳細の本文"


def test_body_scroll_by_keyboard(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """全画面でも、見出しのボタンの後の Tab で本文のスクロール領域にフォーカスが移り、PageDown で本文が送れる（正常系）。"""
    # 準備
    page = _open_long_body_full(write_preview, open_preview, make_item)
    page.locator(FULL_HEAD_LAST_BUTTON).last.focus()
    # 実行
    page.keyboard.press("Tab")
    page.keyboard.press("PageDown")
    # 検証
    assert page.evaluate("document.activeElement?.matches('dialog.full .panel-body')")
    page.wait_for_function("document.querySelector('dialog.full .panel-body').scrollTop > 0")


def test_body_scroll_region_when_axe(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """全画面でも、axe の `scrollable-region-focusable` に本文のスクロール領域が当たらない（正常系）。"""
    # 準備
    page = _open_long_body_full(write_preview, open_preview, make_item)
    # 実行
    result = axe_rule_results(page, FULL_BODY, SCROLLABLE_REGION_RULE)
    # 検証（規則が本文のスクロール領域に当たったうえで、通る）
    assert result["violations"] == []
    assert result["passes"] == [".panel-body"]


def test_body_focus_outline_inside(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """全画面でも、本文のスクロール領域にフォーカスしたとき、輪郭は領域の内側に描く（正常系）。"""
    # 準備
    page = _open_long_body_full(write_preview, open_preview, make_item)
    page.locator(FULL_HEAD_LAST_BUTTON).last.focus()
    # 実行
    page.keyboard.press("Tab")
    # 検証
    outline = page.eval_on_selector(
        FULL_BODY, "e => { const s = getComputedStyle(e); return [s.outlineOffset, s.outlineStyle]; }"
    )
    assert outline == ["-2px", "solid"]


def test_body_focus_when_redrawn(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    open_preview: OpenPreview,
    make_item: MakeItem,
) -> None:
    """詳細パネルから全画面へ移った後、本文のスクロール領域にフォーカスして送り、書き換えの知らせで描き直しても、フォーカスとスクロールの位置が残る（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1"), bodies={"A-1.md": LONG_BODY})
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    page = open_preview(str(served.data["url"]), "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel .panel-body .md")
    _open_full(page)
    page.locator(FULL_HEAD_LAST_BUTTON).last.focus()
    page.keyboard.press("Tab")
    page.keyboard.press("PageDown")
    page.wait_for_function("document.querySelector('dialog.full .panel-body').scrollTop > 0")
    scrolled = page.evaluate(SETTLED_SCROLL_TOP_JS, FULL_BODY)
    page.evaluate("document.querySelector('dialog.full .panel-body').dataset.drawn = 'before'")
    # 実行（項目を足して、書き換えの知らせで描き直させる）
    added = call_tool("add", workspace=str(root), kind="decision", item=NEW_DECISION)
    assert added.is_error is False, added.text
    page.wait_for_function(
        "document.querySelector('dialog.full .panel-body')?.dataset.drawn !== 'before'",
        timeout=UPDATE_TIMEOUT_MS,
    )
    # 検証
    assert page.evaluate("document.activeElement?.matches('dialog.full .panel-body')")
    assert page.evaluate(SETTLED_SCROLL_TOP_JS, FULL_BODY) == scrolled


def test_body_escape_returns_to_panel(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """本文のスクロール領域にフォーカスがあっても、Esc で詳細パネルに戻る（正常系）。"""
    # 準備
    page = _open_long_body_full(write_preview, open_preview, make_item)
    page.locator(FULL_HEAD_LAST_BUTTON).last.focus()
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement?.matches('dialog.full .panel-body')")
    # 実行
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_selector("aside.panel.open")
    assert page.locator("dialog.full").count() == 0
    assert "id=A-1" in page.evaluate("location.hash")


def test_size(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """モーダルは窓から 32px 内側で、幅の上限は 1600px。幅 720px 以下は 8px 内側にする（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2")
    box_js = """() => {
        const box = document.querySelector('dialog.full').getBoundingClientRect();
        return {left: box.left, top: box.top, width: box.width, height: box.height, innerWidth, innerHeight};
    }"""
    results = {}
    # 実行
    for name, size in {
        "normal": {"width": 1280, "height": 800},
        "wide": {"width": 2000, "height": 900},
        "narrow": {"width": 600, "height": 800},
    }.items():
        page.set_viewport_size(size)
        _open_full(page)
        results[name] = page.evaluate(box_js)
        page.click('dialog.full button[data-act="full"]')
        page.wait_for_selector("aside.panel.open")
    # 検証
    normal, wide, narrow = results["normal"], results["wide"], results["narrow"]
    assert (normal["left"], normal["top"]) == (32, 32)
    assert normal["width"] == normal["innerWidth"] - 64
    assert normal["height"] == normal["innerHeight"] - 64
    assert wide["width"] == 1600
    assert (narrow["left"], narrow["top"]) == (8, 8)
    assert narrow["width"] == narrow["innerWidth"] - 16
    assert narrow["height"] == narrow["innerHeight"] - 16


def test_body_fills_width(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """本文の領域と下端の入力は、幅の上限を外してモーダルの幅いっぱいに広げ、モーダルの中のスクロールを後ろへ伝えない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2")
    page.set_viewport_size({"width": 1600, "height": 800})
    # 実行
    _open_full(page)
    sizes = page.evaluate(
        """() => ({
            dialog: document.querySelector('dialog.full').getBoundingClientRect().width,
            body: document.querySelector('dialog.full .panel-body').getBoundingClientRect().width,
            footer: document.querySelector('dialog.full .send-footer').getBoundingClientRect().width,
            overscroll: getComputedStyle(document.querySelector('dialog.full .panel-body')).overscrollBehaviorY,
            behindOverflow: getComputedStyle(document.querySelector('.content')).overflowY,
        })"""
    )
    # 検証
    assert sizes["body"] >= sizes["dialog"] - 2
    assert sizes["footer"] >= sizes["dialog"] - 2
    assert sizes["overscroll"] == "contain"
    # 開いている間、後ろの領域のスクロールを止める
    assert sizes["behindOverflow"] == "hidden"


def test_restore_button_icon(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """全画面の間のボタンは縮小のアイコンに替わり、ボタンの色は詳細パネルのときと同じで変えない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2")
    read_js = """(selector) => {
        const button = document.querySelector(selector);
        return {path: button.querySelector('svg path').getAttribute('d'), color: getComputedStyle(button).color, background: getComputedStyle(button).backgroundColor};
    }"""
    panel = page.evaluate(read_js, 'aside.panel button[data-act="full"]')
    # 実行
    _open_full(page)
    full = page.evaluate(read_js, 'dialog.full button[data-act="full"]')
    # 検証
    assert full["path"] != panel["path"]
    assert (full["color"], full["background"]) == (panel["color"], panel["background"])


def test_body_heading_link(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """全画面の本文でも、見出しの # を押すと本文の領域の中でその見出しまで送り、ハッシュの h を置き換える。用語の印と ID のリンクも出す（正常系）。"""
    # 準備
    body = "## 保存先\n\n" + "\n\n".join(f"段落 {n}" for n in range(1, 40)) + "\n\n## 決め方\n\n用語の保存先と D-3\n"
    url = write_preview(
        make_item("A-1"),
        make_item("D-3"),
        make_item("G-1", title="保存先"),
        bodies={"A-1.md": body},
    )
    page = open_preview(url, "#tab=docs&view=table&id=A-1&full=1")
    page.wait_for_selector("dialog.full [data-heading]")
    # 実行
    page.click('dialog.full [data-heading="決め方"] .h-link')
    page.wait_for_function("new URLSearchParams(location.hash.slice(1)).get('h') === '決め方'")
    # 検証
    assert page.evaluate("document.querySelector('dialog.full .panel-body').scrollTop") > 0
    assert "full=1" in page.evaluate("location.hash")
    assert page.locator("dialog.full .md a.term").count() == 1
    assert page.locator('dialog.full .md a.idref[data-id="D-3"]').count() == 1


def test_code_block_and_diagram_raw_when_long_line(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """全画面でも、本文のコードブロックと図の Raw は、長い行を折り返して横にあふれず、axe の `scrollable-region-focusable` に当たらない（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1"), bodies={"A-1.md": LONG_LINES_BODY})
    page = open_preview(url, "#tab=docs&id=A-1&full=1")
    page.wait_for_selector("dialog.full .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 実行
    page.click('dialog.full button[data-act="diagram-raw"]')
    # 検証
    for selector in ("dialog.full .md pre:not(.dg-raw)", "dialog.full pre.dg-raw"):
        assert page.is_visible(selector)
        assert not overflows_horizontally(page, selector)
        assert axe_rule_results(page, selector, SCROLLABLE_REGION_RULE)["violations"] == []
