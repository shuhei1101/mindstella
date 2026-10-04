"""画面設計『詳細の全画面』と『図の拡大』（全画面の中身の切り替え）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from preview_comment_helpers import PILL, THREE_LINE_BODY, select_text_for_pill
from preview_fixture_types import (
    ID_BUTTON_MIN_SIZE_PX,
    ID_BUTTON_SIZE_JS,
    OpenPreview,
    WriteReviewPreview,
    WriteSamplePreview,
)
from workspace_fixtures import MakeComment, MakeItem

# 選んだ範囲が入口を出す判定を終えるまで待つミリ秒
SELECTION_SETTLE_MS = 400

# 図を描き終わるまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000

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
    assert page.get_attribute(panel_button, "aria-pressed") == "false"
    # 実行
    _open_full(page)
    # 検証
    # ラベルは変えず、押された状態で全画面を示す
    full_button = 'dialog.full button[data-act="full"]'
    assert page.get_attribute(full_button, "aria-label") == "全画面表示"
    assert page.get_attribute(full_button, "aria-pressed") == "true"
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
