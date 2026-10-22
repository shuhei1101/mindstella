"""画面設計『詳細の全画面』と『図の拡大』（全画面の中身の切り替え）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect
from preview_edit_helpers import PENDING_BUTTON as FULL_PENDING_BUTTON, read_edits_file
from preview_fit_helpers import assert_fits_smallest, set_smallest
from preview_a11y_checks import axe_rule_results
from preview_alias_helpers import FULL_MARKS, TIP, TIP_OPEN, write_alias_preview
from preview_body_layout_helpers import (
    INLINE_NAME,
    LAYOUT_GROUP_NAME,
    LAYOUT_SWITCH,
    SIDE_NAME,
    SIDE_VIEWPORT,
    layout_buttons,
    open_side_by_side,
    rows_of_columns,
    seed_side_layout,
)
from preview_body_wrap_helpers import BODY_WIDTHS, WRAP_BODY, WRAP_ITEM_ID, WRAP_METRICS_JS
from preview_body_scroll_helpers import (
    LONG_BODY,
    LONG_LINES_BODY,
    NEW_DECISION,
    SCROLLABLE_REGION_RULE,
    SETTLED_SCROLL_TOP_JS,
    overflows_horizontally,
)
from preview_body_link_helpers import build_body_link_workspace
from preview_comment_helpers import (
    PILL,
    ROW_CORNER_GAPS_JS,
    ROW_CORNER_TOLERANCE_PX,
    THREE_LINE_BODY,
    UPDATE_TIMEOUT_MS,
    read_workspace_yaml,
    review_row,
    select_text_for_pill,
    wait_until_focused,
)
from preview_html_body_helpers import (
    drag_select_in_frame,
    frame_of,
    select_in_frame,
    text_rect_in_page,
    wait_frame_rendered,
)
from preview_fixture_types import (
    ID_BUTTON_MIN_SIZE_PX,
    ID_BUTTON_SIZE_JS,
    OpenPreview,
    WritePreview,
    WriteReviewPreview,
    WriteSamplePreview,
)
from preview_history_helpers import preselect_diff
from preview_head_title_helpers import (
    ANIMATIONS_FINISHED_JS,
    HEAD_BUTTON_WIDTH_PX,
    HEAD_LONG_TITLE,
    HEAD_METRICS_JS,
    HEAD_TITLE_HIDDEN_JS,
    HEAD_TITLE_PREFIX,
    HEAD_TITLE_SHOWN_JS,
    HEAD_TITLE_TIMEOUT_MS,
    SCROLL_BODY_TO_END_JS,
    SCROLL_BODY_TO_TOP_JS,
)
from preview_minimap_helpers import (
    FULL_SCOPE,
    MINIMAP_FULL_HASH,
    added_paragraph_in_view,
    map_metrics,
    mark_shapes,
    open_minimap,
    scroll_top,
)
from preview_removed_helpers import WITHDRAWN_BADGE, WITHDRAWN_REASONS
from workspace_fixtures import ADOPTED_OPTIONS, CallTool, MakeComment, MakeEdit, MakeItem, MakeWorkspace

# 選んだ範囲が入口を出す判定を終えるまで待つミリ秒
SELECTION_SETTLE_MS = 400

# 図を描き終わるまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000

# 全画面の本文のスクロール領域と、Tab で本文の前に来る見出しの最後のボタン
FULL_BODY = "dialog.full .panel-body"
FULL_HEAD_LAST_BUTTON = "dialog.full .panel-head button:not([disabled])"

# 全画面のモーダルの外側（後ろの幕）を押す位置（画面の左上の隅）
BACKDROP_POINT = (4, 4)

# 全画面の中のレビュー中のコメントの節
FULL_REVIEW = "dialog.full .d-review"

# D-1 へのコメントの行の「修正」「削除」の読み上げの名前
ROW_EDIT_NAME = "D-1 へのコメントを修正"
ROW_REMOVE_NAME = "D-1 へのコメントを削除"


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


def test_content(write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem) -> None:
    """全画面にも、背景・推奨の印・採用した案と理由・文字列の値の描画をパネルと同じに出す（正常系）。"""
    # 準備
    url = write_preview(
        make_item(
            "D-1",
            status="未決定",
            lead="**背景**の説明",
            options=[
                {"key": "A", "content": "案 A"},
                {"key": "B", "content": "案 B", "recommended": True},
            ],
        ),
        make_item(
            "D-2",
            status="決定済み",
            answer="**決めた**",
            reason="探しやすい",
            options=ADOPTED_OPTIONS,
        ),
    )
    page = open_preview(url, "#tab=decisions&view=table&id=D-1")
    # 実行（推奨の印と背景）
    _open_full(page)
    # 検証
    assert page.inner_text("dialog.full .d-lead") == "背景の説明"
    assert page.locator("dialog.full .d-lead strong").count() == 1
    assert page.locator("dialog.full .opt .rec-badge").inner_text() == "推奨"
    # 実行（採用した案と理由）
    page.click('dialog.full button[data-act="full"]')
    page.wait_for_selector("aside.panel.open")
    open_preview(url, "#tab=decisions&view=table&id=D-2&full=1")
    page.wait_for_selector("dialog.full[open] .d-sec")
    # 検証
    titles = page.eval_on_selector_all("dialog.full .d-sec h3", "hs => hs.map(h => h.textContent)")
    assert titles[:2] == ["案", "採用した案と理由"]
    assert page.locator("dialog.full .d-answer strong").count() == 1
    assert page.locator("dialog.full .rec-badge").count() == 0


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
    page.wait_for_selector("aside.panel .md:not(.md-value)")
    select_text_for_pill(page, "aside.panel .md:not(.md-value)", "言い換えたい文")
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
    """全画面にも、その項目へのレビュー中のコメントを行ごとの「修正」「削除」つきで出す（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("D-1"), comments=(make_comment("C-1", target="D-1", body="案 A にする"),)
    )
    # 実行
    page = open_preview(url, "#tab=decisions&id=D-1&full=1")
    page.wait_for_selector(f"{FULL_REVIEW}")
    # 検証
    assert page.inner_text(f"{FULL_REVIEW} h3") == "レビュー中のコメント1"
    assert page.inner_text(f"{FULL_REVIEW} .review-body") == "案 A にする"
    assert page.eval_on_selector_all(
        f"{FULL_REVIEW} li .row-actions button", "buttons => buttons.map(b => [b.getAttribute('aria-label'), b.title])"
    ) == [["D-1 へのコメントを修正", "修正"], ["D-1 へのコメントを削除", "削除"]]
    assert page.locator(f"{FULL_REVIEW} input").count() == 0


@pytest.mark.parametrize("width", [390, 720])
def test_review_row_actions_at_top_right_when_narrow(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview, width: int
) -> None:
    """幅 720px 以下でも、全画面の各行の「修正」「削除」を行の右上の隅から 24px 以内に置く（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1&full=1")
    page.wait_for_selector(FULL_REVIEW)
    # 実行
    page.set_viewport_size({"width": width, "height": 700})
    # 検証
    gaps = page.evaluate(ROW_CORNER_GAPS_JS, review_row("dialog.full", "C-1"))
    assert 0 <= gaps["right"] <= ROW_CORNER_TOLERANCE_PX
    assert 0 <= gaps["top"] <= ROW_CORNER_TOLERANCE_PX


def test_review_row_edit(served_review_rows: tuple[str, Path], open_preview: OpenPreview) -> None:
    """全画面でも「修正」で行の本文を直し、200 なら本文に戻して「行の修正」へフォーカスを戻す（正常系）。"""
    # 準備
    url, root = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1&full=1")
    row = review_row("dialog.full", "C-1")
    page.locator(row).get_by_role("button", name=ROW_EDIT_NAME, exact=True).click()
    field = f"{row} form.row-edit textarea"
    page.wait_for_selector(field)
    page.fill(field, "案 B にする")
    # 実行
    page.locator(f"{row} form.row-edit").get_by_role("button", name="修正", exact=True).click()
    page.wait_for_function(
        "document.querySelector(\"dialog.full li[data-comment='C-1'] .review-body\")?.textContent === '案 B にする'",
        timeout=UPDATE_TIMEOUT_MS,
    )
    # 検証
    assert page.locator(f"{row} form.row-edit").count() == 0
    assert read_workspace_yaml(root, "comments.yaml")["items"][0]["body"] == "案 B にする"
    wait_until_focused(page, f"{row} button[title='修正']")


def test_review_row_edit_when_escaped(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """書き換えの入力欄での Esc は書き換えだけを捨て、全画面を閉じない。もう一度 Esc で全画面を閉じる（正常系）。"""
    # 準備
    url, root = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1&full=1")
    row = review_row("dialog.full", "C-1")
    page.locator(row).get_by_role("button", name=ROW_EDIT_NAME, exact=True).click()
    field = f"{row} form.row-edit textarea"
    page.wait_for_selector(field)
    page.fill(field, "捨てる")
    # 実行
    page.press(field, "Escape")
    # 検証
    assert page.inner_text(f"{row} .review-body") == "案 A にする"
    assert page.locator(f"{row} form.row-edit").count() == 0
    assert page.locator("dialog.full[open]").count() == 1
    wait_until_focused(page, f"{row} button[title='修正']")
    assert read_workspace_yaml(root, "comments.yaml")["items"][0]["body"] == "案 A にする"
    # 実行（書き換えていないときの Esc）
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_function("!document.querySelector('dialog.full[open]')")


def test_review_row_remove_and_restore(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """全画面でも「削除」で確認を挟まず消して「元に戻す」を出し、「元に戻す」で元の場所へ戻す（正常系）。"""
    # 準備
    url, root = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1&full=1")
    row = review_row("dialog.full", "C-1")
    # 実行（消す）
    page.locator(row).get_by_role("button", name=ROW_REMOVE_NAME, exact=True).click()
    page.wait_for_selector(f"{row}.removed", timeout=UPDATE_TIMEOUT_MS)
    # 検証（消す）
    assert page.locator("dialog[open]:not(.full)").count() == 0
    assert page.inner_text(f"{row} .removed-msg") == "コメントを削除しました。"
    assert page.inner_text(f"{FULL_REVIEW} h3") == "レビュー中のコメント1"
    wait_until_focused(page, f"{row} button")
    assert [item["id"] for item in read_workspace_yaml(root, "comments.yaml")["items"]] == ["C-2", "C-3"]
    # 実行（戻す）
    page.locator(f"{row}.removed").get_by_role("button", name="元に戻す").click()
    page.wait_for_selector(f"{row} .review-body", timeout=UPDATE_TIMEOUT_MS)
    # 検証（戻す）
    assert page.eval_on_selector_all(f"{FULL_REVIEW} li", "rows => rows.map(r => r.dataset.comment)") == ["C-1", "C-2"]
    assert page.inner_text(f"{FULL_REVIEW} h3") == "レビュー中のコメント2"
    wait_until_focused(page, f"{row} button[title='修正']")


def test_selection_entry(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """全画面でも本文の文を選ぶと入口を出し、入口はモーダルの中に置く。押すと箇所を添える（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("A-1"), bodies={"A-1.md": THREE_LINE_BODY})
    page = open_preview(url, "#tab=docs&id=A-1&full=1")
    page.wait_for_selector("dialog.full[open] .md")
    # 実行
    select_text_for_pill(page, "dialog.full .md:not(.md-value)", "言い換えたい文")
    # 検証
    assert page.locator(f"dialog.full {PILL}").count() == 1
    page.click(PILL)
    assert page.inner_text("dialog.full .send-loc-name") == "本文 2 行目"


def test_selection_entry_when_switched_from_panel(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """詳細パネルから全画面に切り替えた後も、本文の文を選ぶと入口を全画面の中に 1 つ出す（正常系）。"""
    # 準備（詳細パネルで開き、文書に aside.panel が残る状態で全画面に切り替える）
    url, _ = write_review_preview(make_item("A-1"), bodies={"A-1.md": THREE_LINE_BODY})
    page = open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel .md")
    _open_full(page)
    page.wait_for_selector("dialog.full[open] .md")
    # 実行
    select_text_for_pill(page, "dialog.full .md:not(.md-value)", "言い換えたい文")
    # 検証
    assert page.locator(PILL).count() == 1
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


def test_body_alias_tooltip(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """本文の印のツールチップはモーダルの中に置き、その中のタイトルを押すと全画面のままその項目へ移って履歴に積む（正常系）。"""
    # 準備
    url = write_alias_preview(write_preview, make_item)
    page = open_preview(url, "#tab=docs&view=table&id=A-1&full=1")
    page.wait_for_selector(f"{FULL_MARKS}")
    history_length = page.evaluate("history.length")
    # 実行
    page.hover(f"{FULL_MARKS} >> nth=0")
    page.wait_for_selector(TIP_OPEN)
    in_modal = page.evaluate("document.getElementById('term-tip').closest('dialog.full') !== null")
    page.click(f'{TIP} a.tt-link[data-id="A-2"]')
    # 検証
    page.wait_for_function(
        "document.querySelector('dialog.full .d-title')?.textContent === '特殊効果のスキーマ'"
    )
    assert in_modal is True
    assert page.locator("dialog.full[open]").count() == 1
    assert page.evaluate("history.length") == history_length + 1


def test_body_alias_tooltip_when_escaped(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """ツールチップを出している間の Esc はツールチップだけを閉じ、全画面を閉じない。次の Esc で元の大きさ（詳細パネル）に戻る。ツールチップの中にフォーカスがあるときの Esc は、フォーカスを印へ戻す（正常系）。"""
    # 準備
    url = write_alias_preview(write_preview, make_item)
    page = open_preview(url, "#tab=docs&view=table&id=A-1&full=1")
    page.wait_for_selector(f"{FULL_MARKS}")
    mixed = f"{FULL_MARKS} >> nth=0"
    # 実行（乗せて出し、Esc）
    page.hover(mixed)
    page.wait_for_selector(TIP_OPEN)
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('#term-tip:popover-open')")
    still_full = page.locator("dialog.full[open]").count()
    full_hash = page.evaluate("location.hash.includes('full=1')")
    # 実行（フォーカスして中のリンクへ移り、Esc）
    page.mouse.move(2, 2)
    page.focus(mixed)
    page.wait_for_selector(TIP_OPEN)
    page.keyboard.press("Tab")
    in_link = page.evaluate("document.activeElement.matches('#term-tip a.tt-link')")
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('#term-tip:popover-open')")
    back_on_mark = page.evaluate("document.activeElement.matches('dialog.full a.term')")
    still_full_after_link = page.locator("dialog.full[open]").count()
    # 実行（ツールチップが無いときの Esc で、全画面を元の大きさに戻す）
    page.keyboard.press("Escape")
    # 検証
    assert still_full == 1
    assert full_hash is True
    assert in_link is True
    assert back_on_mark is True
    assert still_full_after_link == 1
    page.wait_for_selector("aside.panel.open")
    assert page.locator("dialog.full").count() == 0


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
    assert page.locator("dialog.full .md:not(.md-value) a.term").count() == 1
    assert page.locator('dialog.full .md:not(.md-value) a.idref[data-id="D-3"]').count() == 1


def test_body_change_set_link(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """全画面の本文でも、`#diff=` のリンクを押すと全画面のままそのまとまりの差分の表示に切り替え、ハッシュの diff を履歴に積まずに書く（正常系）。"""
    # 準備
    url = build_body_link_workspace(make_workspace, make_item, call_tool)
    open_preview(url, "#tab=decisions&view=table&id=D-2&full=1")
    page.wait_for_selector("dialog.full .md a")
    history_length = page.evaluate("history.length")
    # 実行
    page.locator("dialog.full .md a", has_text="V-1 へ").click()
    page.wait_for_selector(".df-chip")
    # 検証
    assert page.inner_text(".df-chip-t").endswith("D-1 を直す")
    assert page.locator("dialog.full[open]").count() == 1
    assert "full=1" in page.evaluate("location.hash")
    assert page.evaluate("location.hash").count("diff=V-1") == 1
    assert page.evaluate("history.length") == history_length


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
    for selector in ("dialog.full .md:not(.md-value) pre:not(.dg-raw)", "dialog.full pre.dg-raw"):
        assert page.is_visible(selector)
        assert not overflows_horizontally(page, selector)
        assert axe_rule_results(page, selector, SCROLLABLE_REGION_RULE)["violations"] == []


def test_withdrawn(
    write_removed_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """取り下げた項目の全画面にも、題の右の取り下げの札と「取り下げた理由」の節をパネルと同じに出す（正常系）。"""
    # 準備
    url, _ = write_removed_preview()
    preselect_diff(page, None)
    open_preview(url, "#tab=research&id=R-2")
    page.wait_for_selector("aside.panel.open .d-title")
    # 実行
    _open_full(page)
    # 検証
    assert page.locator(f"dialog.full .d-title {WITHDRAWN_BADGE}.wd-large").inner_text() == "取り下げ"
    assert "取り下げ" not in page.eval_on_selector_all("dialog.full .d-meta dt", "dts => dts.map(d => d.textContent)")
    reason = page.locator('dialog.full section.d-sec:has(> h3:text-is("取り下げた理由")) [data-key="reason"]')
    assert reason.inner_text() == WITHDRAWN_REASONS["R-2"]


def test_diff_withdrawn(
    write_removed_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """全画面にも、選んだ時点で取り下げたことを「取り下げ」の行と「取り下げた理由」の節の前後で並べる（正常系）。"""
    # 準備
    url, _ = write_removed_preview()
    preselect_diff(page, "V-1")
    open_preview(url, "#tab=research&id=R-2")
    page.wait_for_selector("aside.panel.open .d-title")
    # 実行
    _open_full(page)
    # 検証
    row = page.locator("dialog.full .d-meta dd.df-key .df-kv")
    assert row.locator("del.df-was").inner_text().endswith("（なし）")
    assert row.locator(f"ins.df-now {WITHDRAWN_BADGE}").inner_text() == "取り下げ"
    reason = page.locator('dialog.full [data-key="reason"] .df-kv')
    assert reason.locator("ins.df-now").inner_text().endswith(WITHDRAWN_REASONS["R-2"])


# 全画面の HTML の本文の枠
FULL_BODY_FRAME = "dialog.full iframe.html-frame[data-html-body]"

# HTML の本文（4 行目に選ぶ段落を置く）
FULL_HTML_BODY = (
    "<style>p { color: rgb(51, 51, 51); }</style>\n"
    "\n"
    "<h1>画面のモック</h1>\n"
    "<p>言い換えたい文</p>\n"
)


def test_html_body(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """全画面にも HTML の本文を枠で描き、枠の中の文を選んだ入口と箇所はモーダルの中に出す（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("A-1", body="A-1.html"), bodies={"A-1.html": FULL_HTML_BODY}
    )
    page = open_preview(url, "#tab=docs&id=A-1&full=1")
    page.wait_for_selector("dialog.full[open]")
    wait_frame_rendered(page, FULL_BODY_FRAME)
    # 実行
    select_in_frame(page, FULL_BODY_FRAME, "言い換えたい文", "言い換えたい文")
    page.wait_for_selector(f"dialog.full {PILL}", timeout=UPDATE_TIMEOUT_MS)
    page.click(PILL)
    # 検証
    assert page.get_attribute(FULL_BODY_FRAME, "sandbox") == "allow-same-origin"
    assert frame_of(page, FULL_BODY_FRAME).locator("h1").inner_text() == "画面のモック"
    assert page.inner_text("dialog.full .send-loc-name") == "本文 4 行目"
    assert page.inner_text("dialog.full .panel-head .fmt-badge") == "HTML"


def test_html_body_entry_position_when_mouse(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """全画面の枠の中をマウスで選んでも、入口は選んだ文の近くに出る（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("A-1", body="A-1.html"), bodies={"A-1.html": FULL_HTML_BODY}
    )
    page = open_preview(url, "#tab=docs&id=A-1&full=1")
    page.wait_for_selector("dialog.full[open]")
    wait_frame_rendered(page, FULL_BODY_FRAME)
    # 実行
    drag_select_in_frame(page, FULL_BODY_FRAME, "言い換えたい文")
    page.wait_for_selector(f"dialog.full {PILL}", timeout=UPDATE_TIMEOUT_MS)
    rect = text_rect_in_page(page, FULL_BODY_FRAME, "言い換えたい文")
    pill_box = page.locator(PILL).bounding_box()
    # 検証（入口と選んだ文の矩形との縦の差が、選んだ行の高さ以内）
    assert page.locator(f"dialog.full {PILL}").count() == 1
    assert pill_box is not None
    gap = max(
        rect["top"] - (pill_box["y"] + pill_box["height"]),
        pill_box["y"] - (rect["top"] + rect["height"]),
        0,
    )
    assert gap <= rect["height"]


def test_html_body_entry_when_switched_from_panel(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """詳細パネルから全画面に切り替えた後に枠の中の文を選ぶと、入口を全画面の中に 1 つ出す（正常系）。"""
    # 準備（詳細パネルで開き、文書に aside.panel が残る状態で全画面に切り替える）
    url, _ = write_review_preview(
        make_item("A-1", body="A-1.html"), bodies={"A-1.html": FULL_HTML_BODY}
    )
    page = open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel")
    _open_full(page)
    wait_frame_rendered(page, FULL_BODY_FRAME)
    # 実行
    select_in_frame(page, FULL_BODY_FRAME, "言い換えたい文", "言い換えたい文")
    page.wait_for_selector(f"dialog.full {PILL}", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.locator(PILL).count() == 1
    assert page.locator(f"dialog.full {PILL}").count() == 1


# 見出しの帯のタイトルを測る全画面
HEAD_FULL = "dialog.full"


def test_head_title_on_scroll(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """全画面でも、本文を送って先頭のタイトルが隠れたときだけ見出しにタイトルを出し、先頭へ戻すと隠す。ボタンは押し出されない（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1", title=HEAD_LONG_TITLE), bodies={"A-1.md": LONG_BODY})
    page = open_preview(url, "#tab=docs&id=A-1&full=1")
    page.wait_for_selector("dialog.full[open] .d-title")
    # 実行
    page.wait_for_function(HEAD_TITLE_HIDDEN_JS, arg=HEAD_FULL, timeout=HEAD_TITLE_TIMEOUT_MS)
    page.evaluate(ANIMATIONS_FINISHED_JS)
    before = page.evaluate(HEAD_METRICS_JS, HEAD_FULL)
    page.evaluate(SCROLL_BODY_TO_END_JS, HEAD_FULL)
    page.wait_for_function(HEAD_TITLE_SHOWN_JS, arg=HEAD_FULL, timeout=HEAD_TITLE_TIMEOUT_MS)
    page.evaluate(ANIMATIONS_FINISHED_JS)
    after = page.evaluate(HEAD_METRICS_JS, HEAD_FULL)
    page.evaluate(SCROLL_BODY_TO_TOP_JS, HEAD_FULL)
    page.wait_for_function(HEAD_TITLE_HIDDEN_JS, arg=HEAD_FULL, timeout=HEAD_TITLE_TIMEOUT_MS)
    back = page.evaluate(HEAD_METRICS_JS, HEAD_FULL)
    # 検証
    # 送る前は出さず、送って隠れると出し、先頭へ戻すと隠す
    assert (before["shown"], before["visibility"]) == (False, "hidden")
    assert (after["shown"], after["visibility"]) == (True, "visible")
    assert (back["shown"], back["visibility"]) == (False, "hidden")
    # 読み上げからは外し、title は全文を持つ
    assert after["text"].startswith(HEAD_TITLE_PREFIX)
    assert (after["titleAttr"], after["ariaHidden"]) == (HEAD_LONG_TITLE, "true")
    # 資料は形式の札の右に並び、種類と ID は動かない
    assert after["titleLeft"] >= after["badgeRight"]
    assert (after["titleLeft"], after["kindRight"]) == (before["titleLeft"], before["kindRight"])
    # 長いタイトルは 1 行で省略記号付きで切れ、ボタンは縮まず押し出されない
    assert (after["truncated"], after["oneLine"]) == (True, True)
    assert after["buttonWidths"] == [HEAD_BUTTON_WIDTH_PX] * len(after["buttonWidths"])
    assert after["titleRight"] <= after["firstButtonLeft"]
    assert after["lastButtonRight"] <= after["headRight"]


# ─── 差分のミニマップ ───

# ミニマップの帯の太さ（px）
MINIMAP_WIDTH_PX = 20

# 図の拡大を開いた・閉じたときに、帯が消える・戻るまで待つ上限ミリ秒
MINIMAP_TOGGLE_MS = 5_000


def test_diff_minimap(
    write_minimap_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """全画面でも、詳細パネルと同じ帯を本文のスクロール領域の右に出し、印を押すとその箇所まで本文を送る。ハッシュと履歴は変えない（正常系）。"""
    # 準備
    url, _ = write_minimap_preview()
    open_minimap(page, open_preview, url, MINIMAP_FULL_HASH)
    history_length = page.evaluate("history.length")
    metrics = map_metrics(page, FULL_SCOPE)
    shapes = mark_shapes(page, FULL_SCOPE)
    # 検証（帯は本文に重ならず、消した・足したの印が上下の順に並ぶ）
    assert metrics["mapLeft"] >= metrics["bodyRight"] - 1
    assert metrics["mapWidth"] == MINIMAP_WIDTH_PX
    assert [shape["label"] for shape in shapes] == ["消した箇所（1 / 2）", "足した箇所（2 / 2）"]
    assert shapes[0]["top"] < shapes[1]["top"]
    assert not added_paragraph_in_view(page, FULL_SCOPE)
    # 実行
    page.locator(f"{FULL_SCOPE} .df-map .df-map-m").nth(1).click()
    # 検証
    assert scroll_top(page, FULL_SCOPE) > 0
    assert added_paragraph_in_view(page, FULL_SCOPE)
    assert "full=1" in page.evaluate("location.hash")
    assert page.evaluate("history.length") == history_length


def test_diff_minimap_when_diagram_zoomed(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """図の拡大を開いている間は、帯を出さない。閉じて本文へ戻ると、帯を出す（正常系）。"""
    # 準備（差分の表示で、図を持つ D-1 を全画面で開く）
    url, _ = write_history_preview()
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=decisions&view=table&id=D-1&full=1")
    page.wait_for_selector("dialog.full figure.diagram.df-colored", timeout=DIAGRAM_TIMEOUT_MS)
    page.wait_for_selector(f"{FULL_SCOPE} .df-map .df-map-m")
    assert page.locator(f"{FULL_SCOPE} .df-map").is_visible()
    # 実行（図を拡大する）
    page.click('dialog.full button[data-act="diagram-zoom"]')
    page.wait_for_selector("dialog.full .full-viewer .v-stage svg")
    # 検証
    page.wait_for_function(
        "document.querySelector('dialog.full .df-map')?.getClientRects().length === 0",
        timeout=MINIMAP_TOGGLE_MS,
    )
    # 実行（図の拡大を閉じる）
    page.click('dialog.full button[data-act="diagram-close"]')
    page.wait_for_selector("dialog.full .panel-body", state="visible")
    # 検証
    page.wait_for_function(
        "document.querySelector('dialog.full .df-map')?.getClientRects().length > 0",
        timeout=MINIMAP_TOGGLE_MS,
    )


# ─── 本文の差分の並べ方 ───

# 検討事項 D-1 を、まとまり V-2 の差分の表示で全画面で開くハッシュ
SIDE_FULL_HASH = "#tab=decisions&view=table&id=D-1&diff=V-2&full=1"

# 本文の幅が 560px に満たない狭い画面
SIDE_NARROW_VIEWPORT = {"width": 520, "height": 800}


def test_diff_body_layout_switch(
    write_body_layout_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """全画面でも、本文の幅が足りれば本文の差分の頭に切り替えを出し、「左右に並べる」を押すと全画面のまま前後を左右に並べ、履歴に積まず URL のハッシュも変えない（正常系）。"""
    # 準備（幅 480px の詳細パネルでは切り替えを出さない検討事項 D-1 を、全画面で開く）
    url, _ = write_body_layout_preview()
    page.set_viewport_size(SIDE_VIEWPORT)
    preselect_diff(page, "V-2")
    open_preview(url, SIDE_FULL_HASH)
    page.wait_for_selector(f"{FULL_SCOPE} {LAYOUT_SWITCH}")
    history_length = page.evaluate("history.length")
    hash_before = page.evaluate("location.hash")
    # 検証（読み上げの名前の付いたボタンの組で、「インライン」を押した状態）
    assert page.get_attribute(f"{FULL_SCOPE} {LAYOUT_SWITCH}", "aria-label") == LAYOUT_GROUP_NAME
    assert [button["pressed"] for button in layout_buttons(page, FULL_SCOPE)] == ["true", "false"]
    assert page.locator(f"{FULL_SCOPE} .sbs").is_visible() is False
    # 実行（「左右に並べる」を押す）
    page.get_by_role("button", name=SIDE_NAME).click()
    open_side_by_side(page, FULL_SCOPE)
    # 検証（左に消した行、右に足した行。変えていない段落は同じ高さ）
    assert "来週" in page.inner_text(f"{FULL_SCOPE} .sbs section.sbs-before del.df-blk")
    assert "今週" in page.inner_text(f"{FULL_SCOPE} .sbs section.sbs-after ins.df-blk")
    before_rows, after_rows = rows_of_columns(page, FULL_SCOPE)
    assert [row["top"] for row in before_rows] == [row["top"] for row in after_rows]
    assert [button["pressed"] for button in layout_buttons(page, FULL_SCOPE)] == ["false", "true"]
    assert page.evaluate("document.activeElement?.getAttribute('data-layout')") == "side"
    assert page.evaluate("history.length") == history_length
    assert page.evaluate("location.hash") == hash_before
    # 実行（「インライン」を押す）
    page.get_by_role("button", name=INLINE_NAME).click()
    page.wait_for_selector(f"{FULL_SCOPE} .sbs", state="detached")
    # 検証
    assert page.locator(f"{FULL_SCOPE} .md:not(.md-value) ins.df-blk").count() == 1
    assert page.evaluate("history.length") == history_length


def test_diff_body_layout_switch_when_narrow(
    write_body_layout_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """全画面の本文の幅が 560px に満たないときは、詳細パネルと同じく、並べ方が side でも切り替えを出さずインラインで出す（正常系）。"""
    # 準備
    url, _ = write_body_layout_preview()
    page.set_viewport_size(SIDE_NARROW_VIEWPORT)
    seed_side_layout(page, "V-2")
    # 実行
    open_preview(url, SIDE_FULL_HASH)
    page.wait_for_selector(f"{FULL_SCOPE} .md:not(.md-value) ins.df-blk:visible")
    # 検証
    assert page.locator(f"{FULL_SCOPE} {LAYOUT_SWITCH}").is_visible() is False
    assert page.locator(f"{FULL_SCOPE} .sbs").is_visible() is False
    assert page.locator(f"{FULL_SCOPE} .md:not(.md-value) del.df-blk:visible").count() == 1


def test_diff_body_layout_kept_when_returned_to_panel(
    write_body_layout_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """全画面で選んだ並べ方は個人の上書きで、元の大きさに戻した幅の足りる詳細パネルにも当たる（正常系）。"""
    # 準備（資料 A-1 は幅 760px の詳細パネルで切り替えを出す）
    url, _ = write_body_layout_preview()
    page.set_viewport_size(SIDE_VIEWPORT)
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=docs&id=A-1&diff=V-2&full=1")
    page.wait_for_selector(f"{FULL_SCOPE} {LAYOUT_SWITCH}")
    page.get_by_role("button", name=SIDE_NAME).click()
    open_side_by_side(page, FULL_SCOPE)
    # 実行（元の大きさに戻す）
    page.get_by_role("button", name="元の大きさに戻す").click()
    page.wait_for_selector("aside.panel.open .sbs")
    # 検証
    assert [button["pressed"] for button in layout_buttons(page, "aside.panel")] == ["false", "true"]


@pytest.mark.parametrize("width", BODY_WIDTHS)
def test_body_wrap_when_long_words_and_tables(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem, width: int
) -> None:
    """全画面でも、本文の長い URL とインラインコードは本文の幅で折り返し（項目の ID のリンクは折り返さない）、列の多い表は包む入れ物の中だけで横に送れ、幅に収まる表は送れず、本文の区画は横に送れない（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1", body="A-1.md"), make_item(WRAP_ITEM_ID), bodies={"A-1.md": WRAP_BODY})
    page = open_preview(url, "#tab=docs&id=A-1&full=1")
    page.set_viewport_size({"width": width, "height": 800})
    page.wait_for_selector("dialog.full .md-table-wrap")
    # 実行
    result = page.evaluate(WRAP_METRICS_JS, "dialog.full")
    # 検証
    assert result["bodyScrollsHorizontally"] is False
    assert result["mdScrollsHorizontally"] is False
    assert (result["urlInside"], result["codeInside"]) == (True, True)
    assert result["urlRows"] > 1
    assert result["codeRows"] > 1
    assert result["idrefOverflowWrap"] == "normal"
    assert result["idrefRows"] == 1
    wide, narrow = result["wraps"]
    group = {"role": "group", "label": "本文の表", "tabindex": "0", "inside": True}
    assert {key: wide[key] for key in group} == group
    assert {key: narrow[key] for key in group} == group
    assert wide["scrolls"] is True
    assert wide["overflowX"] in ("auto", "scroll")
    assert narrow["scrolls"] is False
    assert narrow["tableFillsWrap"] is True


@pytest.mark.parametrize("width", [320, 1280])
def test_body_table_scroll_by_keyboard(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem, width: int
) -> None:
    """全画面でも、列の多い表を包む入れ物はキーボードのフォーカスで止まり、右の矢印で表の中だけを横に送れて、フォーカスの枠は内側に描く（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1", body="A-1.md"), make_item(WRAP_ITEM_ID), bodies={"A-1.md": WRAP_BODY})
    page = open_preview(url, "#tab=docs&id=A-1&full=1")
    page.set_viewport_size({"width": width, "height": 800})
    wrap = page.locator("dialog.full .md-table-wrap").first
    wrap.wait_for()
    # 実行
    wrap.focus()
    page.keyboard.press("ArrowRight")
    # 検証
    page.wait_for_function("selector => document.querySelector(selector).scrollLeft > 0", arg="dialog.full .md-table-wrap")
    assert wrap.evaluate("element => getComputedStyle(element).outlineOffset") == "-2px"
    assert page.evaluate("document.querySelector('dialog.full .panel-body').scrollLeft") == 0


def test_fit_smallest(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """詳細の全画面は、幅 320px で横にスクロールせず、本文の表・図・コードブロックのほかにあふれる区画が無く、閉じる・全画面のボタンが表示幅の中にある（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-3&full=1")
    page.wait_for_selector("dialog.full .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 実行
    set_smallest(page)
    # 検証
    assert_fits_smallest(page, ("dialog.full", 'dialog.full button[data-act="full"]'), scope="dialog.full")


# ===== 編集の表示（保存待ちの編集） =====

# 全画面の編集のトグルと編集の表示
FULL_EDIT_TOGGLE = "dialog.full button.pe-edit-toggle"
FULL_EDIT_FORM = "dialog.full form.pe-form"

# 編集の表示の入力欄を離れた後、編集が溜まるのを待つ上限ミリ秒
FULL_EDIT_SETTLE_MS = 10_000


def test_edit_in_full(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_edit: MakeEdit,
    open_preview: OpenPreview,
) -> None:
    """全画面の中でも詳細パネルと同じ編集の表示で編集でき、見出しとキーに保存待ちの印を置く。全画面を戻しても溜めた編集は残る（正常系）。"""
    # 準備
    url, root = write_edit_preview(
        make_item("D-1", title="最初の問い", answer="元の答え"),
        edits=(make_edit("E-1", value="編集後の答え", before="元の答え"),),
    )
    page = open_preview(url, "#tab=decisions&view=table&id=D-1&full=1")
    page.wait_for_selector("dialog.full[open]")
    # 検証（読む表示）
    assert page.locator("dialog.full .panel-head .pm.pm-compact").count() == 1
    assert "編集後の答え" in page.inner_text("dialog.full .panel-body")
    assert page.locator(FULL_EDIT_TOGGLE).get_attribute("aria-pressed") == "false"
    # 実行（編集の表示にして、別のキーを書き換える）
    page.click(FULL_EDIT_TOGGLE)
    page.wait_for_selector(FULL_EDIT_FORM)
    reason = page.locator(f"{FULL_EDIT_FORM} #pe-D1-reason")
    reason.fill("理由の文")
    reason.blur()
    expect(page.locator(FULL_PENDING_BUTTON)).to_have_attribute(
        "aria-label", "保存待ち（2 件）", timeout=FULL_EDIT_SETTLE_MS
    )
    # 検証（編集の表示）
    assert page.locator(FULL_EDIT_TOGGLE).inner_text().strip() == "編集を終える"
    assert page.locator(f"{FULL_EDIT_FORM} .pe-field[data-key='reason'] .pm").count() == 1
    assert page.locator(f"{FULL_EDIT_FORM} .pe-field[data-key='answer'] .pm").count() == 1
    assert [edit["key"] for edit in read_edits_file(root)["items"]] == ["answer", "reason"]
    # 実行（元の大きさに戻す）
    page.click('dialog.full button[data-act="full"]')
    page.wait_for_selector("aside.panel.open")
    # 検証（元の大きさに戻す）
    assert page.locator("dialog.full").count() == 0
    assert page.get_by_role("button", name="保存待ち（2 件）").count() == 1


def test_edit_full_comment_input_hidden(
    write_edit_preview: WriteReviewPreview,
    make_item: MakeItem,
    open_preview: OpenPreview,
) -> None:
    """編集の表示の間は、全画面の下端のコメントの入力を隠し、読む表示に戻すと出す（正常系）。"""
    # 準備
    url, _ = write_edit_preview(make_item("D-1", title="最初の問い"))
    page = open_preview(url, "#tab=decisions&view=table&id=D-1&full=1")
    page.wait_for_selector("dialog.full[open]")
    form = "dialog.full form.send"
    assert page.locator(form).count() >= 1
    assert page.locator(form).first.is_visible()
    # 実行
    page.click(FULL_EDIT_TOGGLE)
    page.wait_for_selector(FULL_EDIT_FORM)
    # 検証
    assert page.locator(form).count() == 0 or page.locator(form).first.is_hidden()
    # 戻す
    page.click(FULL_EDIT_TOGGLE)
    expect(page.locator(FULL_EDIT_FORM)).to_have_count(0)
    assert page.locator(form).first.is_visible()
