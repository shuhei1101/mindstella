"""画面設計『詳細パネル』の結合テスト。"""

from __future__ import annotations

import json

import pytest
from playwright.sync_api import Page
from preview_comment_helpers import (
    COMMENTS_BUTTON,
    COMMENTS_PANEL,
    DETAIL_MESSAGE,
    DETAIL_TEXTAREA,
    DRAFT_WAIT_MS,
    PILL,
    THREE_LINE_BODY,
    UPDATE_TIMEOUT_MS,
    read_workspace_yaml,
    select_text,
    select_text_for_pill,
)
from preview_fixture_types import (
    ID_BUTTON_MIN_SIZE_PX,
    ID_BUTTON_SIZE_JS,
    OpenPreview,
    WritePreview,
    WriteReviewPreview,
    WriteSamplePreview,
)
from preview_style_checks import TRANSPARENT, animated_properties, pin_id_column, row_backgrounds
from workspace_fixtures import MakeComment, MakeDraft, MakeItem

# 入力が止まるのを待たずに保つ書きかけが、ファイルに届くまで待つミリ秒
DRAFT_FLUSH_WAIT_MS = 400

# 選んだ範囲が入口を出す判定を終えるまで待つミリ秒
SELECTION_SETTLE_MS = 400

# パネルを別画面として積む幅（これ以下）
NARROW_WIDTH = 800

# 狭い幅の画面の高さ
NARROW_HEIGHT = 700

# 図を描き終わるまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000


def _panel_title(page: Page) -> str:
    """パネルのタイトル（項目の題）を返す。"""
    return page.inner_text("aside.panel .d-title")


def test_content(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """項目の種類・ID・状態・タイトル・案・本文（見出しと図）を出す（正常系）。"""
    # 準備
    url = write_sample_preview()
    # 実行
    page = open_preview(url, "#tab=decisions&view=table&id=D-3")
    page.wait_for_selector("aside.panel.open .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証
    assert page.inner_text("aside.panel .panel-kind") == "検討事項 D-3"
    assert page.get_attribute("aside.panel .detail .st", "data-st") == "要見直し"
    options = page.eval_on_selector_all(
        "aside.panel .opt",
        "opts => opts.map(o => [o.querySelector('.key').textContent, o.querySelector('.res').textContent, o.classList.contains('adopted')])",
    )
    assert options == [["A", "採用", True], ["B", "検討中", False]]
    # 本文の見出しはパネルの節の見出し（h3）より下の段
    headings = page.eval_on_selector_all(
        "aside.panel .detail h2, aside.panel .detail h3, aside.panel .detail h4, aside.panel .detail h5",
        "hs => hs.map(h => h.tagName + ':' + h.textContent)",
    )
    assert headings == [
        "H2:D-3の題",
        "H3:案",
        "H3:本文",
        "H4:要件",
        "H5:流れ",
        "H3:レビュー中のコメント0",
    ]
    assert page.locator("aside.panel .mermaid svg").count() == 1


def test_related_items(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """前提・後続の項目・関連タスクを出し、押すとその項目へ移る（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2")
    # 実行
    sections = page.eval_on_selector_all(
        "aside.panel .d-sec h3", "hs => hs.map(h => h.textContent)"
    )
    page.click("aside.panel .d-sec:has(h3:text-is('前提')) button.idlink")
    page.wait_for_function(
        "document.querySelector('aside.panel .d-title')?.textContent === 'D-1の題'"
    )
    # 検証
    assert sections == ["前提", "後続の項目", "関連タスク", "レビュー中のコメント0"]
    assert "id=D-1" in page.evaluate("location.hash")


def test_referenced_by(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """関連で指している項目から、参照元の節で指されている項目を開ける（正常系）。"""
    # 準備
    url = write_preview(
        make_item("D-1", status="決定済み"),
        make_item("D-2", status="決定済み", related=["D-1"]),
    )
    page = open_preview(url, "#tab=decisions&view=table&id=D-1")
    # 実行
    sections = page.eval_on_selector_all(
        "aside.panel .d-sec h3", "hs => hs.map(h => h.textContent)"
    )
    page.click("aside.panel .d-sec:has(h3:text-is('参照元')) button.idlink")
    page.wait_for_function(
        "document.querySelector('aside.panel .d-title')?.textContent === 'D-2の題'"
    )
    # 検証
    assert "参照元" in sections
    assert "id=D-2" in page.evaluate("location.hash")


def test_back_and_forward(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """パネルの中で移った項目を、戻る・進むで行き来する（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2")
    back = 'aside.panel button[data-act="back"]'
    forward = 'aside.panel button[data-act="forward"]'
    assert page.is_disabled(back)
    assert page.is_disabled(forward)
    assert page.get_attribute(back, "aria-label") == "前の項目へ戻る"
    assert page.get_attribute(forward, "aria-label") == "次の項目へ進む"
    page.click("aside.panel .d-sec:has(h3:text-is('前提')) button.idlink")
    page.wait_for_function(
        "document.querySelector('aside.panel .d-title')?.textContent === 'D-1の題'"
    )
    # 実行・検証
    assert page.is_enabled(back)
    page.click(back)
    page.wait_for_function(
        "document.querySelector('aside.panel .d-title')?.textContent === 'D-2の題'"
    )
    assert page.is_enabled(forward)
    page.click(forward)
    page.wait_for_function(
        "document.querySelector('aside.panel .d-title')?.textContent === 'D-1の題'"
    )


def test_selected_row(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """開いている項目の行に「選択中」の印を付け、閉じると外す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2")
    # 実行・検証
    selected = page.eval_on_selector_all(
        "main tr[data-id].selected", "rows => rows.map(r => r.dataset.id)"
    )
    assert selected == ["D-2"]
    page.click('aside.panel button[data-act="close"]')
    page.wait_for_function("document.querySelectorAll('main tr[data-id].selected').length === 0")


def test_close(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """閉じるボタンと Esc でパネルを閉じ、ハッシュから id を外す（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2")
    # 実行・検証
    page.click('aside.panel button[data-act="close"]')
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    assert "id=" not in page.evaluate("location.hash")
    page.click('table.grid button.row-open[data-id="D-1"]')
    page.wait_for_selector("aside.panel.open")
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    assert "id=" not in page.evaluate("location.hash")


def test_side_by_side_when_wide(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """幅が広いと本文を寄せて並べる（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    before = page.evaluate("document.querySelector('main#main').getBoundingClientRect().width")
    # 実行
    page.click('table.grid button.row-open[data-id="D-1"]')
    page.wait_for_selector("aside.panel.open")
    # 検証
    assert page.evaluate("document.body.classList.contains('panel-open')")
    after = page.evaluate("document.querySelector('main#main').getBoundingClientRect().width")
    assert after < before


def test_overlay_when_narrow(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """幅が狭いと、パネルを別画面として積み、一覧へ戻る操作で戻る（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table")
    page.set_viewport_size({"width": NARROW_WIDTH, "height": NARROW_HEIGHT})
    history_length = page.evaluate("history.length")
    # 実行
    page.click('table.grid button.row-open[data-id="D-1"]')
    page.wait_for_selector("aside.panel.open")
    # 検証
    assert page.evaluate("history.length") == history_length + 1
    panel_width = page.evaluate(
        "document.querySelector('aside.panel').getBoundingClientRect().width"
    )
    assert panel_width == pytest.approx(NARROW_WIDTH, abs=1)
    page.click("aside.panel button.panel-back")
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    assert "id=" not in page.evaluate("location.hash")


def test_diagram_raw(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """図の Raw で、図と mermaid の原文を切り替える（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-3")
    page.wait_for_selector("aside.panel .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 実行
    page.click('aside.panel button[data-act="diagram-raw"]')
    # 検証
    assert (
        page.get_attribute('aside.panel button[data-act="diagram-raw"]', "aria-pressed") == "true"
    )
    assert page.is_visible("aside.panel pre.dg-raw")
    assert not page.is_visible("aside.panel .mermaid")
    assert "flowchart LR" in page.inner_text("aside.panel pre.dg-raw")
    page.click('aside.panel button[data-act="diagram-raw"]')
    assert page.is_visible("aside.panel .mermaid")


def test_content_transition(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """本文の寄せは動かさず、パネルだけが transform ですべり込む（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2")
    page.wait_for_selector("aside.panel.open")
    # 実行
    content = animated_properties(page, "main#main")
    panel = animated_properties(page, "aside.panel")
    # 検証
    assert content == []
    assert panel == ["transform"]


def test_selected_row_hover(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """表で選んだ行は、ホバー中も選んだ行の色のままで、ほかの行はホバーで色が変わる（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2")
    page.wait_for_selector("aside.panel.open")
    pin_id_column(page)
    selected_row = 'table.grid tbody tr[data-id="D-2"]'
    other_row = 'table.grid tbody tr[data-id="D-4"]'
    at_rest = row_backgrounds(page, selected_row)
    # 実行
    page.hover(selected_row)
    selected_hovered = row_backgrounds(page, selected_row)
    page.hover(other_row)
    other_hovered = row_backgrounds(page, other_row)
    # 検証
    assert selected_hovered == at_rest
    assert at_rest["row"] != TRANSPARENT
    assert at_rest["cells"] == [TRANSPARENT]
    assert at_rest["pinned"] == [at_rest["row"]]
    assert other_hovered["row"] == TRANSPARENT
    assert TRANSPARENT not in other_hovered["cells"]
    assert other_hovered["pinned"] == other_hovered["cells"]
    assert at_rest["row"] not in other_hovered["cells"]


def test_id_button_size(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """関係する項目（前提・後続の項目・関連タスク）の ID のボタンは、見えている枠が縦横 24px 以上である（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2")
    # 実行
    sizes = page.eval_on_selector_all("aside.panel .d-sec button.idlink", ID_BUTTON_SIZE_JS)
    # 検証
    assert sizes["count"] > 0
    assert sizes["smallest"] >= ID_BUTTON_MIN_SIZE_PX


def test_comment_input(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """サーバーの配信で開くと、コメントの入力をパネルの下端に出し、その上の本文だけをスクロールする（正常系）。"""
    # 準備
    url = write_sample_preview()
    # 実行
    page = open_preview(url, "#tab=decisions&view=table&id=D-3")
    page.wait_for_selector("aside.panel.open form.send")
    # 検証
    assert page.get_attribute("aside.panel form.send", "data-id") == "D-3"
    assert page.inner_text("aside.panel form.send label.send-label") == "D-3 へのコメント"
    panel_box = page.locator("aside.panel").bounding_box()
    form_box = page.locator("aside.panel form.send").bounding_box()
    assert panel_box is not None
    assert form_box is not None
    # コメントの入力は、パネルの下端に留まる
    assert abs((panel_box["y"] + panel_box["height"]) - (form_box["y"] + form_box["height"])) <= 2
    # スクロールするのは入力の上の本文の領域で、入力はその外にある
    assert page.eval_on_selector("aside.panel .panel-body", "e => getComputedStyle(e).overflowY") in (
        "auto",
        "scroll",
    )
    assert page.locator("aside.panel .panel-body form.send").count() == 0


def test_comment_input_when_saved(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
) -> None:
    """「レビューに追加」を押すと、入力欄を空にして溜めた旨を出し、コメントのボタンの件数とレビュー中のコメントを描き直す（正常系）。"""
    # 準備
    url, root = write_review_preview(make_item("D-1"))
    page = open_preview(url, "#tab=decisions&id=D-1")
    page.fill(DETAIL_TEXTAREA, "案 A にする")
    # 実行
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.saved", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.get_attribute(DETAIL_MESSAGE, "role") == "status"
    assert page.inner_text(DETAIL_MESSAGE) == "レビューに追加しました（レビュー中 1 件）。"
    assert page.input_value(DETAIL_TEXTAREA) == ""
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "1"
    assert page.inner_text("aside.panel .d-review h3 .count") == "1"
    assert page.inner_text("aside.panel .d-review .review-body") == "案 A にする"
    saved = read_workspace_yaml(root, "comments.yaml")["items"]
    assert [(item["target"], item["body"]) for item in saved] == [("D-1", "案 A にする")]
    assert not (root / "submissions.yaml").exists()


def test_comment_input_when_ctrl_enter(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
) -> None:
    """入力欄で Ctrl+Enter を押しても溜める（正常系）。"""
    # 準備
    url, root = write_review_preview(make_item("D-1"))
    page = open_preview(url, "#tab=decisions&id=D-1")
    page.fill(DETAIL_TEXTAREA, "案 B も見たい")
    # 実行
    page.press(DETAIL_TEXTAREA, "Control+Enter")
    page.wait_for_selector(f"{DETAIL_MESSAGE}.saved", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.input_value(DETAIL_TEXTAREA) == ""
    saved = read_workspace_yaml(root, "comments.yaml")["items"]
    assert [item["body"] for item in saved] == ["案 B も見たい"]


def test_comment_input_when_body_empty(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    page: Page,
) -> None:
    """空白だけの本文は溜めず、入力欄を要見直しにして理由を出し、入力欄へフォーカスを戻す（異常系）。"""
    # 準備
    url, root = write_review_preview(make_item("D-1"))
    posts: list[str] = []
    page.on(
        "request",
        lambda request: posts.append(request.url) if request.method == "POST" else None,
    )
    open_preview(url, "#tab=decisions&id=D-1")
    page.fill(DETAIL_TEXTAREA, "   ")
    # 実行
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.empty", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert posts == []
    assert page.inner_text(DETAIL_MESSAGE) == "コメントを入れてから追加してください。"
    assert page.get_attribute(DETAIL_TEXTAREA, "aria-invalid") == "true"
    assert page.evaluate("document.activeElement.matches('form.send textarea')") is True
    assert not (root / "comments.yaml").exists()


def test_comment_input_when_server_refuses(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    page: Page,
) -> None:
    """サーバーが溜めなかった理由を返すと、本文を残して理由を出す（異常系）。"""
    # 準備
    url, root = write_review_preview(make_item("D-1"))
    page.route(
        "**/api/comments",
        lambda route: (
            route.fulfill(
                status=404,
                content_type="application/problem+json",
                body=json.dumps(
                    {
                        "type": "about:blank",
                        "title": "Not Found",
                        "status": 404,
                        "detail": "項目 D-1 がワークスペースにありません",
                    },
                    ensure_ascii=False,
                ),
            )
            if route.request.method == "POST"
            else route.continue_()
        ),
    )
    open_preview(url, "#tab=decisions&id=D-1")
    page.fill(DETAIL_TEXTAREA, "案 A にする")
    # 実行
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.failed", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert (
        page.inner_text(DETAIL_MESSAGE)
        == "レビューに追加できませんでした。項目 D-1 がワークスペースにありません"
    )
    assert page.input_value(DETAIL_TEXTAREA) == "案 A にする"
    assert page.get_by_role("button", name="本文を写す").count() == 0
    assert not (root / "comments.yaml").exists()


def test_comment_input_draft(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_draft: MakeDraft,
) -> None:
    """書きかけは入力が止まったときに保ち、開き直すと入力欄へ戻す（正常系）。"""
    # 準備
    url, root = write_review_preview(
        make_item("D-1"), make_item("D-2"), drafts=(make_draft(target="D-2", body="D-2 の書きかけ"),)
    )
    page = open_preview(url, "#tab=decisions&id=D-1")
    # 実行
    page.fill(DETAIL_TEXTAREA, "D-1 の書きかけ")
    page.wait_for_timeout(DRAFT_WAIT_MS)
    page.reload()
    page.wait_for_selector(DETAIL_TEXTAREA)
    # 検証
    drafts = read_workspace_yaml(root, "drafts.yaml")["items"]
    assert sorted((item["target"], item["body"]) for item in drafts) == [
        ("D-1", "D-1 の書きかけ"),
        ("D-2", "D-2 の書きかけ"),
    ]
    assert page.input_value(DETAIL_TEXTAREA) == "D-1 の書きかけ"


def test_comment_input_draft_when_closed(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
) -> None:
    """入力が止まるのを待たずにパネルを閉じても、書きかけを保つ（正常系）。"""
    # 準備
    url, root = write_review_preview(make_item("D-1"))
    page = open_preview(url, "#tab=decisions&id=D-1")
    page.fill(DETAIL_TEXTAREA, "閉じる前の書きかけ")
    # 実行
    page.click('aside.panel button[data-act="close"]')
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    page.wait_for_timeout(DRAFT_FLUSH_WAIT_MS)
    # 検証
    drafts = read_workspace_yaml(root, "drafts.yaml")["items"]
    assert [(item["target"], item["body"]) for item in drafts] == [("D-1", "閉じる前の書きかけ")]


def test_comment_input_draft_when_saved_at_once(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
) -> None:
    """入力の直後（書きかけを保つ待ちより前）に溜めても、drafts.yaml に書きかけが残らない（正常系）。"""
    # 準備
    url, root = write_review_preview(make_item("D-1"))
    page = open_preview(url, "#tab=decisions&id=D-1")
    page.fill(DETAIL_TEXTAREA, "すぐ溜める")
    # 実行
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.saved", timeout=UPDATE_TIMEOUT_MS)
    page.wait_for_timeout(DRAFT_WAIT_MS)
    # 検証
    drafts = (
        read_workspace_yaml(root, "drafts.yaml")["items"] if (root / "drafts.yaml").exists() else []
    )
    assert [item for item in drafts if item["target"] == "D-1"] == []
    saved = read_workspace_yaml(root, "comments.yaml")["items"]
    assert [item["body"] for item in saved] == ["すぐ溜める"]


def test_comment_input_draft_when_saved_with_location(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_draft: MakeDraft,
) -> None:
    """箇所を持つ入力を溜めても、箇所を持たない入力の書きかけは残る（正常系）。"""
    # 準備
    url, root = write_review_preview(
        make_item("A-1"),
        bodies={"A-1.md": THREE_LINE_BODY},
        drafts=(make_draft(target="A-1", body="項目への書きかけ"),),
    )
    page = open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel .md")
    select_text_for_pill(page, "aside.panel .md", "言い換えたい文")
    page.click(PILL)
    page.fill(DETAIL_TEXTAREA, "ここは言い換える")
    # 実行
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.saved", timeout=UPDATE_TIMEOUT_MS)
    page.wait_for_timeout(DRAFT_WAIT_MS)
    # 検証
    saved = read_workspace_yaml(root, "comments.yaml")["items"]
    assert [(item["target"], item["loc"]["start"], item["body"]) for item in saved] == [
        ("A-1", 2, "ここは言い換える")
    ]
    drafts = read_workspace_yaml(root, "drafts.yaml")["items"]
    assert [(item["target"], item.get("loc"), item["body"]) for item in drafts] == [
        ("A-1", None, "項目への書きかけ")
    ]
    assert page.locator(".send-loc").count() == 0
    assert page.input_value(DETAIL_TEXTAREA) == "項目への書きかけ"


def test_review_comments(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
) -> None:
    """その項目へのレビュー中のコメントを溜めた順に、箇所（名前と選んだ文）と本文つきで読むだけの形で並べる（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("D-1"),
        make_item("D-2"),
        comments=(
            make_comment("C-1", target="D-1", body="案 A にする"),
            make_comment("C-2", target="D-2", body="別の項目へのコメント"),
            make_comment(
                "C-3",
                target="D-1",
                body="ここは別の言い方にしたい",
                loc={"kind": "value", "key": "options[C].cons", "text": "表の密度が下がる"},
            ),
        ),
    )
    # 実行
    page = open_preview(url, "#tab=decisions&id=D-1")
    # 検証
    assert page.inner_text("aside.panel .d-review h3") == "レビュー中のコメント2"
    assert page.eval_on_selector_all(
        "aside.panel .d-review li",
        "rows => rows.map(r => [r.querySelector('.review-loc-name')?.textContent ?? null, r.querySelector('.send-quote')?.textContent ?? null, r.querySelector('.review-body').textContent])",
    ) == [
        [None, None, "案 A にする"],
        ["案 C のデメリット", "表の密度が下がる", "ここは別の言い方にしたい"],
    ]
    # 読むだけ（直す・消す・チェックを持たない）
    assert page.locator("aside.panel .d-review button, aside.panel .d-review input").count() == 0
    # レビュー中のコメントは関係する項目の後に出る
    sections = page.eval_on_selector_all("aside.panel .d-sec h3", "hs => hs.map(h => h.firstChild.textContent)")
    assert sections[-1] == "レビュー中のコメント"


def test_review_comments_when_empty(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """レビュー中のコメントが 0 件のときは「レビュー中のコメントはありません。」を出す（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("D-1"))
    # 実行
    page = open_preview(url, "#tab=decisions&id=D-1")
    # 検証
    assert page.inner_text("aside.panel .d-review h3") == "レビュー中のコメント0"
    assert "レビュー中のコメントはありません。" in page.inner_text("aside.panel .d-review")


def test_selection_entry_when_body(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """本文の文を選ぶと入口を出し、押すと入口を閉じて、本文の行の範囲の箇所をコメントの入力に添えて入力欄へフォーカスを移す（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("A-1"), bodies={"A-1.md": THREE_LINE_BODY})
    page = open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel .md")
    history_length = page.evaluate("history.length")
    # 実行
    select_text_for_pill(page, "aside.panel .md", "言い換えたい文")
    page.get_by_role("button", name="選んだ箇所にコメント").click()
    # 検証
    assert page.locator(PILL).count() == 0
    assert page.inner_text("aside.panel .send-loc-name") == "本文 2 行目"
    assert page.inner_text("aside.panel .send-quote") == "言い換えたい文"
    assert page.evaluate("document.activeElement.matches('form.send textarea')") is True
    assert page.evaluate("history.length") == history_length


def test_selection_entry_when_value(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """案の中の値を選んでも入口を出し、押すと値のキーの箇所をコメントの入力に添える（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-3")
    page.wait_for_selector("aside.panel .opt")
    # 実行
    select_text_for_pill(page, 'aside.panel dd[data-key="options[A].pros"]', "並べやすい")
    page.click(PILL)
    # 検証
    assert page.inner_text("aside.panel .send-loc-name") == "案 A のメリット"
    assert page.inner_text("aside.panel .send-quote") == "並べやすい"


def test_selection_entry_when_outside_body(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """関係する項目の中の選択や、空の選択では入口を出さない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-2")
    page.wait_for_selector("aside.panel .d-sec")
    # 実行
    select_text(page, "aside.panel .d-sec button.idlink", "D-1")
    page.wait_for_timeout(SELECTION_SETTLE_MS)
    # 検証
    assert page.locator(PILL).count() == 0


def test_selection_entry_when_closed_by_escape(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """入口は Esc で閉じ、選んだ範囲は残す（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("A-1"), bodies={"A-1.md": THREE_LINE_BODY})
    page = open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel .md")
    select_text_for_pill(page, "aside.panel .md", "言い換えたい文")
    page.focus(PILL)
    # 実行
    page.keyboard.press("Escape")
    # 検証
    assert page.locator(PILL).count() == 0
    assert page.evaluate("getSelection().toString()") == "言い換えたい文"


def test_highlight_location(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
) -> None:
    """コメントの一覧の行から開くと、そのコメントの箇所（本文は行のブロック）を印の色の地で示し、別の項目へ移ると消す（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("A-1"),
        make_item("D-1"),
        bodies={"A-1.md": THREE_LINE_BODY},
        comments=(
            make_comment(
                "C-1",
                target="A-1",
                body="ここは言い換える",
                loc={"kind": "body", "start": 2, "end": 2, "text": "言い換えたい文"},
            ),
        ),
    )
    page = open_preview(url)
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(COMMENTS_PANEL)
    # 実行
    page.click(f"{COMMENTS_PANEL} li[data-comment='C-1'] button.row-target")
    page.wait_for_selector("aside.panel.open .md .loc-hit")
    # 検証
    assert page.inner_text("aside.panel .md .loc-hit") == "最初の文 言い換えたい文 最後の文"
    assert page.eval_on_selector(
        "aside.panel .md .loc-hit", "e => getComputedStyle(e).backgroundColor"
    ) != "rgba(0, 0, 0, 0)"
    # 別の項目へ移ると示す箇所を消す
    page.evaluate("location.hash = '#tab=decisions&id=D-1'")
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === 'D-1の題'")
    assert page.locator(".loc-hit").count() == 0


def test_highlight_location_when_value(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
) -> None:
    """値の箇所は、そのキーの要素を示す（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item(
            "D-3",
            status="要見直し",
            options=[{"key": "A", "content": "表で見せる", "pros": "並べやすい", "adopted": True}],
        ),
        comments=(
            make_comment(
                "C-1",
                target="D-3",
                body="ここは別の言い方にしたい",
                loc={"kind": "value", "key": "options[A].pros", "text": "並べやすい"},
            ),
        ),
    )
    page = open_preview(url)
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(COMMENTS_PANEL)
    # 実行
    page.click(f"{COMMENTS_PANEL} li[data-comment='C-1'] button.row-target")
    page.wait_for_selector("aside.panel.open .loc-hit")
    # 検証
    assert page.eval_on_selector_all(
        "aside.panel .loc-hit", "es => es.map(e => e.dataset.key)"
    ) == ["options[A].pros"]


def test_highlight_location_when_mismatched(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
) -> None:
    """箇所が今の本文に合わなければ示さず、項目の先頭を出す（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("A-1"),
        bodies={"A-1.md": THREE_LINE_BODY},
        comments=(
            make_comment(
                "C-1",
                target="A-1",
                body="消えた箇所",
                loc={"kind": "value", "key": "options[Z].pros", "text": "無い値"},
            ),
        ),
    )
    page = open_preview(url)
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(COMMENTS_PANEL)
    # 実行
    page.click(f"{COMMENTS_PANEL} li[data-comment='C-1'] button.row-target")
    page.wait_for_selector("aside.panel.open .md")
    # 検証
    assert page.locator(".loc-hit").count() == 0
    assert page.eval_on_selector("aside.panel .panel-body", "e => e.scrollTop") == 0
