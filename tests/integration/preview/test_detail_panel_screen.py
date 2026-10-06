"""画面設計『詳細パネル』の結合テスト。"""

from __future__ import annotations

import json

import pytest
from playwright.sync_api import APIResponse, Page, Route
from preview_a11y_checks import axe_rule_results
from preview_body_scroll_helpers import (
    LONG_BODY,
    NEW_DECISION,
    SCROLLABLE_REGION_RULE,
    SETTLED_SCROLL_TOP_JS,
)
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
from preview_history_helpers import preselect_diff
from preview_style_checks import TRANSPARENT, animated_properties, pin_id_column, row_backgrounds
from workspace_fixtures import RECORD_DIR, CallTool, MakeComment, MakeDraft, MakeItem, MakeWorkspace

# 入力が止まるのを待たずに保つ書きかけが、ファイルに届くまで待つミリ秒
DRAFT_FLUSH_WAIT_MS = 400

# 溜める POST の応答を止めるミリ秒（書きかけを保つ待ち `DRAFT_SAVE_DELAY_MS` の 500 より長く）
POST_HOLD_MS = 1_000

# 選んだ範囲が入口を出す判定を終えるまで待つミリ秒
SELECTION_SETTLE_MS = 400

# パネルを別画面として積む幅（これ以下）
NARROW_WIDTH = 800

# 狭い幅の画面の高さ
NARROW_HEIGHT = 700

# 図を描き終わるまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000

# 本文のスクロール領域と、Tab で本文の前に来る見出しの最後のボタン
PANEL_BODY = "aside.panel .panel-body"
PANEL_HEAD_LAST_BUTTON = "aside.panel .panel-head button:not([disabled])"


def _hold_post_response(route: Route, held: list[tuple[Route, APIResponse]]) -> None:
    """溜める POST はサーバーへ流して応答を控え（画面へは返さない）、GET はそのまま流す。"""
    if route.request.method == "POST":
        held.append((route, route.fetch()))
    else:
        route.continue_()


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


@pytest.mark.parametrize(
    ("item_id", "tab", "panel_kind"),
    [
        pytest.param("T-1", "tasks", "タスク T-1", id="task"),
        pytest.param("G-1", "terms", "用語集 G-1", id="term"),
        pytest.param("N-1", "notes", "メモ N-1", id="note"),
    ],
)
def test_content_when_body_in_other_kinds(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    item_id: str,
    tab: str,
    panel_kind: str,
) -> None:
    """タスク・用語集・メモの本文も、ほかの種類と同じ本文の節に出す（正常系）。"""
    # 準備
    url = write_preview(
        make_item(item_id, body=f"{item_id}.md"),
        bodies={f"{item_id}.md": "## 経緯\n\n会話で持ち越した\n"},
    )
    # 実行
    page = open_preview(url, f"#tab={tab}&view=table&id={item_id}")
    page.wait_for_selector("aside.panel.open .detail .md")
    # 検証
    assert page.inner_text("aside.panel .panel-kind") == panel_kind
    assert page.locator("aside.panel .d-sec h3", has_text="本文").count() == 1
    assert "会話で持ち越した" in page.inner_text("aside.panel .detail .md")


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
    page.click('table.grid button.row-open[data-id="D-2"]')
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
    page.click('table.grid button.row-open[data-id="D-2"]')
    page.wait_for_selector("aside.panel.open")
    # 検証
    assert page.evaluate("document.body.classList.contains('panel-open')")
    after = page.evaluate("document.querySelector('main#main').getBoundingClientRect().width")
    assert after < before


@pytest.mark.parametrize(
    ("hash_text", "frame", "item", "width"),
    [
        pytest.param("#tab=decisions&view=table", ".table-wrap", "D-2", 1280, id="table_1280"),
        pytest.param("#tab=decisions&view=table", ".table-wrap", "D-2", 1440, id="table_1440"),
        pytest.param("#tab=decisions&view=table", ".table-wrap", "D-2", 1920, id="table_1920"),
        pytest.param("#tab=decisions&view=map", ".map-wrap", "D-2", 1440, id="map_1440"),
        pytest.param("#tab=docs&view=table", ".table-wrap", "A-1", 1920, id="docs_wide_1920"),
    ],
)
def test_side_by_side_moves_content_left(
    write_sample_preview: WriteSamplePreview,
    open_preview: OpenPreview,
    hash_text: str,
    frame: str,
    item: str,
    width: int,
) -> None:
    """窓が本文の幅の上限（1320px）より広くても、パネルを開くと本文の中身の枠が左の余白（32px）まで寄り、パネルに重ならない（正常系）。"""
    # 準備
    url = write_sample_preview()
    page = open_preview(url, hash_text)
    page.set_viewport_size({"width": width, "height": 800})
    page.wait_for_selector(frame)
    box_js = f"""() => {{
        const box = document.querySelector('{frame}').getBoundingClientRect();
        return {{left: box.left, right: box.right}};
    }}"""
    before = page.evaluate(box_js)
    # 実行
    if frame == ".map-wrap":
        page.click(f'#decision-map button[data-node="{item}"]')
    else:
        page.click(f'table.grid button.row-open[data-id="{item}"]')
    page.wait_for_selector("aside.panel.open")
    # パネルがすべり込んで、窓の右端に着くまで待つ（動きの間は位置が動く）
    page.wait_for_function(
        "Math.abs(document.querySelector('aside.panel').getBoundingClientRect().right - innerWidth) < 1"
    )
    after = page.evaluate(box_js)
    panel_left = page.evaluate("document.querySelector('aside.panel').getBoundingClientRect().left")
    # 検証
    assert after["left"] == 32
    assert after["left"] <= before["left"]
    assert after["right"] <= panel_left
    # 本文の幅の上限より広い窓では、開く前に中央にあった枠が、開いた後は左へ寄る
    if width > 1320 + 64:
        assert after["left"] < before["left"]


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
    page.click('table.grid button.row-open[data-id="D-2"]')
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
    assert not (root / RECORD_DIR / "submissions.yaml").exists()


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
        lambda request: (
            posts.append(request.url)
            if request.method == "POST" and not request.url.endswith("/api/opened")
            else None
        ),
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
    assert not (root / RECORD_DIR / "comments.yaml").exists()


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
    assert not (root / RECORD_DIR / "comments.yaml").exists()


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
    page: Page,
) -> None:
    """入力の直後（書きかけを保つ待ちより前）に溜め、溜める応答が待ちより遅れても、drafts.yaml に書きかけが残らない（正常系）。"""
    # 準備（溜める POST はサーバーへ流して処理させ、その応答を書きかけを保つ待ちより長く画面へ止める。GET はそのまま流す）
    url, root = write_review_preview(make_item("D-1"))
    held: list[tuple[Route, APIResponse]] = []
    page.route("**/api/comments", lambda route: _hold_post_response(route, held))
    open_preview(url, "#tab=decisions&id=D-1")
    page.fill(DETAIL_TEXTAREA, "すぐ溜める")
    # 実行
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_timeout(POST_HOLD_MS)
    held[0][0].fulfill(response=held[0][1])
    page.wait_for_selector(f"{DETAIL_MESSAGE}.saved", timeout=UPDATE_TIMEOUT_MS)
    page.wait_for_timeout(DRAFT_WAIT_MS)
    # 検証
    drafts = (
        read_workspace_yaml(root, "drafts.yaml")["items"]
        if (root / RECORD_DIR / "drafts.yaml").exists()
        else []
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
    assert page.locator("aside.panel.open").count() == 1


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


def _open_long_body(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> Page:
    """フォーカスできる要素を持たない、縦にあふれる本文の項目を詳細パネルで開く。"""
    url = write_preview(make_item("A-1"), bodies={"A-1.md": LONG_BODY})
    page = open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector(f"{PANEL_BODY} .md")
    # 前提: 本文の中にフォーカスできる要素は無く、縦にあふれている
    assert page.locator(f"{PANEL_BODY} :is(a[href], button, input, textarea, select, [tabindex])").count() == 0
    assert page.eval_on_selector(PANEL_BODY, "e => e.scrollHeight > e.clientHeight")
    return page


def test_body_scroll_region_attributes(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """本文のスクロール領域は、フォーカスでき、読み上げの名前「詳細の本文」の領域になる（正常系）。"""
    # 準備・実行
    page = _open_long_body(write_preview, open_preview, make_item)
    # 検証
    assert page.get_attribute(PANEL_BODY, "tabindex") == "0"
    assert page.get_attribute(PANEL_BODY, "role") == "region"
    assert page.get_attribute(PANEL_BODY, "aria-label") == "詳細の本文"


def test_body_scroll_by_keyboard(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """見出しのボタンの後の Tab で本文のスクロール領域にフォーカスが移り、PageDown で本文が送れる（正常系）。"""
    # 準備
    page = _open_long_body(write_preview, open_preview, make_item)
    page.locator(PANEL_HEAD_LAST_BUTTON).last.focus()
    # 実行
    page.keyboard.press("Tab")
    page.keyboard.press("PageDown")
    # 検証
    assert page.evaluate("document.activeElement?.matches('aside.panel .panel-body')")
    page.wait_for_function("document.querySelector('aside.panel .panel-body').scrollTop > 0")


def test_body_scroll_region_when_axe(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """axe の `scrollable-region-focusable` に、本文のスクロール領域が当たらない（正常系）。"""
    # 準備
    page = _open_long_body(write_preview, open_preview, make_item)
    # 実行
    result = axe_rule_results(page, PANEL_BODY, SCROLLABLE_REGION_RULE)
    # 検証（規則が本文のスクロール領域に当たったうえで、通る）
    assert result["violations"] == []
    assert result["passes"] == [".panel-body"]


def test_body_focus_outline_inside(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """本文のスクロール領域にフォーカスしたとき、輪郭は領域の内側に描く（正常系）。"""
    # 準備
    page = _open_long_body(write_preview, open_preview, make_item)
    page.locator(PANEL_HEAD_LAST_BUTTON).last.focus()
    # 実行
    page.keyboard.press("Tab")
    # 検証
    outline = page.eval_on_selector(
        PANEL_BODY, "e => { const s = getComputedStyle(e); return [s.outlineOffset, s.outlineStyle]; }"
    )
    assert outline == ["-2px", "solid"]


def test_body_focus_when_redrawn(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    open_preview: OpenPreview,
    make_item: MakeItem,
) -> None:
    """本文のスクロール領域にフォーカスして送った後、書き換えの知らせで描き直しても、フォーカスとスクロールの位置が残る（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1"), bodies={"A-1.md": LONG_BODY})
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    page = open_preview(str(served.data["url"]), "#tab=docs&id=A-1")
    page.wait_for_selector(f"{PANEL_BODY} .md")
    page.locator(PANEL_HEAD_LAST_BUTTON).last.focus()
    page.keyboard.press("Tab")
    page.keyboard.press("PageDown")
    page.wait_for_function("document.querySelector('aside.panel .panel-body').scrollTop > 0")
    scrolled = page.evaluate(SETTLED_SCROLL_TOP_JS, PANEL_BODY)
    page.evaluate("document.querySelector('aside.panel .panel-body').dataset.drawn = 'before'")
    # 実行（項目を足して、書き換えの知らせで描き直させる）
    added = call_tool("add", workspace=str(root), kind="decision", item=NEW_DECISION)
    assert added.is_error is False, added.text
    page.wait_for_function(
        "document.querySelector('aside.panel .panel-body')?.dataset.drawn !== 'before'",
        timeout=UPDATE_TIMEOUT_MS,
    )
    # 検証
    assert page.evaluate("document.activeElement?.matches('aside.panel .panel-body')")
    assert page.evaluate(SETTLED_SCROLL_TOP_JS, PANEL_BODY) == scrolled


def test_body_escape_closes_panel(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """本文のスクロール領域にフォーカスがあっても、Esc で詳細パネルを閉じる（正常系）。"""
    # 準備
    page = _open_long_body(write_preview, open_preview, make_item)
    page.locator(PANEL_HEAD_LAST_BUTTON).last.focus()
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement?.matches('aside.panel .panel-body')")
    # 実行
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_selector("aside.panel.open", state="detached")
    assert "id=" not in page.evaluate("location.hash")


# ─── 差分の表示 ───

# 差分の表示で詳細パネルを開く URL のハッシュ
DIFF_D1_HASH = "#tab=decisions&view=table&id=D-1"

# 図の差分の色付けが終わるまで待つ上限ミリ秒
DIFF_DIAGRAM_TIMEOUT_MS = 20_000

# 差分を出せない旨・出せない理由の文言
NOTE_TRIMMED = "このまとまりの前後を組み立てられません。保持する回数を超えた古い変更履歴は消えています。今の内容を出しています。"
NOTE_BODY_UNAVAILABLE = "本文の差分を出せません。書き換えの後に、本文のファイルが直接書き換えられています。今の本文を出しています。"
NOTE_BODY_TOO_LARGE = "本文の差分を出せません。書き換えが大きく、差分を計算しきれませんでした。今の本文を出しています。"

# 全ての行が違う本文の行数（差分の計算を打ち切らせる大きさ）
LARGE_LINE_COUNT = 5000

# 差分のライブラリ jsdiff を配る URL（これだけ止める）
JSDIFF_URL_PATTERN = "https://cdn.jsdelivr.net/npm/diff@*/**"


def _open_diff_panel(
    page: Page, open_preview: OpenPreview, url: str, sel: str, hash_text: str = DIFF_D1_HASH
) -> Page:
    """選んだ時点を入れてから開き、詳細パネルが開くのを待つ。"""
    preselect_diff(page, sel)
    open_preview(url, hash_text)
    page.wait_for_selector("aside.panel.open .d-title")
    return page


def test_diff_head(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """差分の表示の間、本文の冒頭に選んだ時点の名前と日時を出す。変わっていない項目には出さない（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    _open_diff_panel(page, open_preview, url, "V-2")
    # 検証（変わった項目）
    assert page.inner_text("aside.panel .df-head-t") == "決める"
    assert page.inner_text("aside.panel .df-when") == "10/02 09:00"
    # 「前回開いてから」は範囲の始まりを添える
    page.evaluate("localStorage.setItem('mindmap-preview', JSON.stringify({diffSel: 'since'}))")
    page.reload()
    page.wait_for_selector("aside.panel .df-head")
    assert page.inner_text("aside.panel .df-head-t") == "前回開いてから"
    assert page.inner_text("aside.panel .df-when") == "10/01 21:00 より後"
    # 変わっていない項目（V-2 で足した・変えたものに入らない T-1）には出さない
    page.evaluate("localStorage.setItem('mindmap-preview', JSON.stringify({diffSel: 'V-2'}))")
    page.goto(f"{url}#tab=tasks&view=table&id=T-1")
    page.reload()
    page.wait_for_selector("aside.panel.open .d-title")
    assert page.locator("aside.panel .df-head").count() == 0
    assert page.locator("aside.panel .df-kv").count() == 0


def test_diff_new_badge(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """その時点で足された項目は、タイトルの横に「新規」の札を置き、前後の差分は出さない（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    _open_diff_panel(page, open_preview, url, "V-1")
    # 検証
    badge = page.locator("aside.panel .d-title .df-badge.df-new")
    assert badge.inner_text() == "新規"
    assert page.locator("aside.panel .df-kv").count() == 0
    assert page.locator("aside.panel .md ins.df-blk, aside.panel .md del.df-blk").count() == 0
    # 変えただけの項目（V-2 の D-1）には札を置かない
    page.evaluate("localStorage.setItem('mindmap-preview', JSON.stringify({diffSel: 'V-2'}))")
    page.reload()
    page.wait_for_selector("aside.panel .df-head")
    assert page.locator("aside.panel .d-title .df-badge").count() == 0


def test_diff_keys(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """変わったキーの前の値と今の値を並べる。状態だけは面を塗らず、変わっていないキーは今の値のまま出す（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    _open_diff_panel(page, open_preview, url, "V-2")
    # 検証
    status = page.locator('aside.panel [data-key="status"] .df-kv')
    assert status.get_attribute("class") == "df-kv df-plain"
    assert status.locator("del.df-was").inner_text().endswith("未決定")
    assert status.locator("ins.df-now").inner_text().endswith("決定済み")
    answer = page.locator('aside.panel [data-key="answer"] .df-kv')
    assert answer.locator("del.df-was").inner_text().endswith("旧い答え")
    assert answer.locator("ins.df-now").inner_text().endswith("新しい答え")
    # 前の値は取り消し線、今の値は下線
    assert page.eval_on_selector(
        'aside.panel [data-key="answer"] del.df-was', "e => getComputedStyle(e).textDecorationLine"
    ) == "line-through"
    assert page.eval_on_selector(
        'aside.panel [data-key="answer"] ins.df-now', "e => getComputedStyle(e).textDecorationLine"
    ) == "underline"
    # 変わっていない影響度は今の値のまま
    assert page.locator("aside.panel .d-meta .df-key").count() == 0 or "影響度" not in page.inner_text(
        "aside.panel .d-meta dt.df-key"
    )
    assert "大" in page.inner_text("aside.panel .d-meta")


def test_diff_body(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """本文を描いたまま、足した部分と消した部分に印を付けて元の位置へ出す。変えていない部分には付けない（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    _open_diff_panel(page, open_preview, url, "V-2")
    page.wait_for_selector("aside.panel .md ins.df-blk")
    # 検証
    added = page.inner_text("aside.panel .md ins.df-blk")
    removed = page.inner_text("aside.panel .md del.df-blk")
    assert "新しい段落を足しました。" in added
    assert "次の段落を消します。" in removed
    # 足した塊・消した塊の頭に記号と、読み上げの名前がある
    assert page.inner_text("aside.panel .md ins.df-blk > .df-sign") == "+"
    assert page.inner_text("aside.panel .md del.df-blk > .df-sign") == "−"
    # 表は行ごとに印を付ける
    assert "7" in page.inner_text("aside.panel .md tr.df-add")
    assert "3" in page.inner_text("aside.panel .md tr.df-del")
    assert page.locator("aside.panel .md tr.df-add").count() == 1
    assert page.locator("aside.panel .md tr.df-del").count() == 1
    # 変えていない段落は印の外で、今の本文の行（1・14 行目の段落など）を持つ
    unchanged = page.eval_on_selector_all(
        "aside.panel .md > p[data-line-start]", "ps => ps.map(p => [p.dataset.lineStart, p.textContent])"
    )
    assert ["3", "最初の段落です。"] in unchanged or ["3", "最初の段落です。"] in [
        [line, text] for line, text in unchanged
    ]
    assert page.locator("aside.panel .md del.df-blk [data-line-start]").count() == 0


def test_diff_diagram(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """flowchart は足した・変えたノードと辺に色を付け、図の下に凡例と「消したもの」を並べる。色を付けない種類は枠に色を付け、Raw で見るよう案内する（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    _open_diff_panel(page, open_preview, url, "V-2")
    page.wait_for_selector("aside.panel figure.diagram.df-colored", timeout=DIFF_DIAGRAM_TIMEOUT_MS)
    # 検証（flowchart）
    figure = page.locator("aside.panel figure.diagram.df-colored")
    assert figure.locator("g.df-n-add").count() == 1
    assert (figure.locator("g.df-n-add").text_content() or "").strip() == "追加"
    assert figure.locator("g.df-n-chg").count() == 1
    assert "処理を変えた" in (figure.locator("g.df-n-chg").text_content() or "")
    assert figure.locator(".df-lg-add").count() == 1
    assert figure.locator(".df-lg-chg").count() == 1
    removed = figure.locator(".df-removed li").all_inner_texts()
    assert any("終了" in text for text in removed)
    # 色を付けない種類（gantt）は枠に色を付ける
    page.goto(f"{url}#tab=docs&view=table&id=A-1")
    page.reload()
    page.wait_for_selector("aside.panel figure.diagram.df-frame", timeout=DIFF_DIAGRAM_TIMEOUT_MS)
    assert "図の中の変更は Raw で見られます" in page.inner_text("aside.panel figure.diagram .df-notes")
    assert page.locator("aside.panel figure.diagram .df-n-add, aside.panel figure.diagram .df-n-chg").count() == 0


def test_diff_diagram_raw(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """図の Raw は、記法の行ごとに足した行（+）と消した行（−）を印つきで出す（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    _open_diff_panel(page, open_preview, url, "V-2")
    page.wait_for_selector("aside.panel figure.diagram.df-changed", timeout=DIFF_DIAGRAM_TIMEOUT_MS)
    # 実行
    page.click('aside.panel figure.diagram [data-act="diagram-raw"]')
    # 検証
    raw = page.locator("aside.panel figure.diagram > .dg-raw.df-raw")
    assert raw.is_visible()
    added = raw.locator(".df-line.df-add").all_inner_texts()
    removed = raw.locator(".df-line.df-del").all_inner_texts()
    assert any("処理を変えた" in line and line.startswith("+") for line in added)
    assert any("終了" in line and line.startswith("−") for line in removed)
    assert raw.locator(".df-line.df-add .df-sign").first.inner_text() == "+"


def test_diff_note_when_trimmed(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """選んだ時点の変更履歴が保持する回数を超えて消えているとき、本文の頭にその旨を出し、今の内容を差分なしで出す（正常系）。"""
    # 準備（保持する回数 1: D-2 は V-2 の回と、まとめる前の回のうち、新しい 1 回だけを持つ）
    url, _ = write_history_preview(history_limit=1)
    _open_diff_panel(page, open_preview, url, "V-2", "#tab=decisions&view=table&id=D-2")
    # 検証
    assert page.inner_text("aside.panel .df-note") == NOTE_TRIMMED
    assert page.locator("aside.panel .df-kv").count() == 0
    assert page.locator("aside.panel .md ins.df-blk, aside.panel .md del.df-blk").count() == 0
    # 印は付く
    page.goto(f"{url}#tab=decisions&view=table")
    page.wait_for_selector("table.grid tbody tr")
    assert page.locator("table.grid tbody tr[data-id='D-2'] .df-mark").count() == 1


def test_diff_note_when_body_rewritten(
    write_history_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """書き換えの後に本文のファイルが直接書き換えられていると、その旨を出して今の本文を差分なしで描き、キーの差分は出す（正常系）。"""
    # 準備
    url, root = write_history_preview()
    (root / RECORD_DIR / "docs" / "D-1.md").write_text("手で書いた A\n\n手で書いた B\n", encoding="utf-8")
    _open_diff_panel(page, open_preview, url, "V-2")
    page.wait_for_selector("aside.panel .df-note")
    # 検証
    assert page.inner_text("aside.panel .df-note") == NOTE_BODY_UNAVAILABLE
    assert "手で書いた A" in page.inner_text("aside.panel .md")
    assert page.locator("aside.panel .md ins.df-blk, aside.panel .md del.df-blk").count() == 0
    assert page.locator('aside.panel [data-key="status"] .df-kv').count() == 1


def test_diff_note_when_body_too_large(
    write_history_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    call_tool: CallTool,
    page: Page,
) -> None:
    """本文の行の差分を打ち切ったとき、その旨を出して今の本文を差分なしで描き、キーの差分は出す（正常系）。"""
    # 準備（大きな本文をまとめ、全ての行が違う大きな本文へまとめる前に書き換えて、まとめていない変更を選ぶ）
    url, root = write_history_preview()
    before = "".join(f"前の行 {index}\n" for index in range(LARGE_LINE_COUNT))
    after = "".join(f"後の行 {index}\n" for index in range(LARGE_LINE_COUNT))
    for body, summary in ((before, "大きな本文にする"), (after, None)):
        result = call_tool(
            "update", workspace=str(root), id="D-1", item={"body_markdown": body, "answer": f"答え {body[:5]}"}
        )
        assert result.is_error is False, result.text
        if summary is not None:
            assert call_tool("commit", workspace=str(root), summary=summary).is_error is False
    _open_diff_panel(page, open_preview, url, "pending")
    page.wait_for_selector("aside.panel .df-note", timeout=DIFF_DIAGRAM_TIMEOUT_MS)
    # 検証
    assert page.inner_text("aside.panel .df-note") == NOTE_BODY_TOO_LARGE
    assert page.locator("aside.panel .md ins.df-blk, aside.panel .md del.df-blk").count() == 0
    assert page.locator("aside.panel .df-kv").count() >= 1


def test_diff_note_when_library_unavailable(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """jsdiff を読めないとき、本文の頭にその旨を出し、本文・図・Raw を今の版で差分なしで描き、キーの差分は出す（異常系）。"""
    # 準備
    url, _ = write_history_preview()
    page.route(JSDIFF_URL_PATTERN, lambda route: route.abort())
    _open_diff_panel(page, open_preview, url, "V-2")
    page.wait_for_selector("aside.panel .lib-error")
    # 検証
    notice = page.inner_text("aside.panel .lib-error[role=alert]")
    assert "本文と図の差分を表示できません。読み込めなかったライブラリ: jsdiff" in notice
    assert "通信を確認して、ページを再読み込みしてください。" in notice
    assert page.locator("aside.panel .md ins.df-blk, aside.panel .md del.df-blk").count() == 0
    assert "最初の段落です。" in page.inner_text("aside.panel .md")
    assert page.locator('aside.panel [data-key="status"] .df-kv').count() == 1
    assert page.locator("aside.panel figure.diagram.df-changed").count() == 0


def test_selection_entry_when_diff(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """差分の表示の間も、変えていない文を選べば入口を出し、今の本文の行をコメントに添える。消した部分を含む選択では出さない（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    _open_diff_panel(page, open_preview, url, "V-2")
    page.wait_for_selector("aside.panel .md del.df-blk")
    # 実行（変えていない段落を選ぶ）
    select_text_for_pill(page, "aside.panel .md", "最初の段落です。")
    page.click(PILL)
    # 検証（今の本文の 3 行目）
    assert page.inner_text("aside.panel .send-loc-name") == "本文 3 行目"
    # 消した部分を含む選択では出さない
    page.keyboard.press("Escape")
    select_text(page, "aside.panel .md del.df-blk", "次の段落を消します。")
    page.wait_for_timeout(SELECTION_SETTLE_MS)
    assert page.locator(PILL).count() == 0


def test_selection_entry_when_old_set_after_body_edit(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """古いまとまりを選び、その後に本文を直した項目では、本文の行の印を外し、本文を選んでも入口を出さない（正常系）。"""
    # 準備（D-2 は V-2 の後にも本文を直している）
    url, _ = write_history_preview()
    _open_diff_panel(page, open_preview, url, "V-2", "#tab=decisions&view=table&id=D-2")
    page.wait_for_selector("aside.panel .md")
    # 検証
    assert page.locator("aside.panel .md [data-line-start]").count() == 0
    select_text(page, "aside.panel .md", "1 行目の段落")
    page.wait_for_timeout(SELECTION_SETTLE_MS)
    assert page.locator(PILL).count() == 0
    # 値（案・キー）の選択は今まで通り出る
    select_text_for_pill(page, 'aside.panel [data-key="answer"]', "答え")


# 見出しのリンクと用語・ID の印を確かめる本文（見出し「保存先」「決め方」「決め方」、用語・ID を並べた段落、コードブロック）
LINKED_BODY = (
    "## 保存先\n\n"
    "保存先と AIM と AI と D-3 と `D-5` と D-99 と XD-3 と A-1\n\n"
    "```\n保存先 D-3\n```\n\n"
    "## 決め方\n\n"
    "[決め方](#決め方) と [無い](#無い)\n\n"
    "## 決め方\n\n"
    "2 つ目の決め方の段落\n"
)


def _write_linked_preview(write_preview: WritePreview, make_item: MakeItem) -> str:
    """用語 G-1「保存先」・G-3「AI」、検討事項 D-3・D-5 と、本文を持つ資料 A-1 の配信の URL を返す。"""
    return write_preview(
        make_item("A-1"),
        make_item("D-3"),
        make_item("D-5"),
        make_item("G-1", title="保存先", meaning="記録を置く場所"),
        make_item("G-3", title="AI", meaning="人工知能"),
        bodies={"A-1.md": LINKED_BODY},
    )


def test_body_heading_links(write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem) -> None:
    """本文の見出しの右に # のリンクを置き、乗せるまで見えず、乗せると見える。読み上げの名前は「見出し「{見出し}」へのリンク」（正常系）。"""
    # 準備
    url = _write_linked_preview(write_preview, make_item)
    page = open_preview(url, "#tab=docs&view=table&id=A-1")
    page.wait_for_selector("aside.panel [data-heading]")
    # 実行
    slugs = page.eval_on_selector_all("aside.panel [data-heading]", "h => h.map(x => x.dataset.heading)")
    labels = page.eval_on_selector_all(
        "aside.panel [data-heading] .h-link", "l => l.map(x => x.getAttribute('aria-label'))"
    )
    link = 'aside.panel [data-heading="保存先"] .h-link'
    opacity_before = page.eval_on_selector(link, "e => getComputedStyle(e).opacity")
    page.hover('aside.panel [data-heading="保存先"]')
    opacity_hover = page.eval_on_selector(link, "e => getComputedStyle(e).opacity")
    # 検証
    assert slugs == ["保存先", "決め方", "決め方-1"]
    assert labels == [
        "見出し「保存先」へのリンク",
        "見出し「決め方」へのリンク",
        "見出し「決め方」へのリンク",
    ]
    assert opacity_before == "0"
    assert opacity_hover == "1"


def test_body_heading_link_press(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """見出しの # を押すと、その見出しを指す h をハッシュに置き換え、履歴に積まない。本文の中の `[文言](#見出し)` も同じ見出しへ送り、本文に無い見出しなら何もしない（正常系）。"""
    # 準備
    url = _write_linked_preview(write_preview, make_item)
    page = open_preview(url, "#tab=docs&view=table&id=A-1")
    page.wait_for_selector("aside.panel [data-heading]")
    history_length = page.evaluate("history.length")
    # 実行（# を押す）
    page.click('aside.panel [data-heading="決め方-1"] .h-link')
    page.wait_for_function("new URLSearchParams(location.hash.slice(1)).get('h') === '決め方-1'")
    after_hash = page.evaluate("location.hash")
    # 実行（本文の中のリンク。marked が日本語の href をパーセントエンコードして描く）
    page.click("aside.panel .md p a:has-text('決め方')")
    page.wait_for_function("new URLSearchParams(location.hash.slice(1)).get('h') === '決め方'")
    # 実行（本文に無い見出しへのリンク）
    hash_before = page.evaluate("location.hash")
    page.click("aside.panel .md p a:has-text('無い')")
    page.wait_for_timeout(200)
    # 検証
    assert "h=" in after_hash
    assert page.evaluate("history.length") == history_length
    assert page.evaluate("location.hash") == hash_before
    assert "%E7%84%A1" not in page.evaluate("location.hash")


def test_body_term_marks(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """文中の用語だけに印を付け（「保存」に分けず、「AIM」には付けない）、見出しとコードブロックには付けない。印は文字の色を変えず点線の下線で、押すとその用語の詳細へ移り履歴に積む（正常系）。"""
    # 準備
    url = _write_linked_preview(write_preview, make_item)
    page = open_preview(url, "#tab=docs&view=table&id=A-1")
    page.wait_for_selector("aside.panel .md a.term")
    history_length = page.evaluate("history.length")
    # 実行
    terms = page.eval_on_selector_all(
        "aside.panel .md a.term", "a => a.map(x => [x.textContent, x.dataset.id])"
    )
    in_heading_or_code = page.locator(
        "aside.panel .md :is(h2, pre) :is(a.term, a.idref)"
    ).count()
    style = page.eval_on_selector(
        "aside.panel .md a.term",
        "e => ({line: getComputedStyle(e).textDecorationLine, style: getComputedStyle(e).textDecorationStyle, color: getComputedStyle(e).color, parent: getComputedStyle(e.parentElement).color})",
    )
    page.click("aside.panel .md a.term >> nth=0")
    page.wait_for_function("location.hash.includes('id=G-1')")
    # 検証
    assert terms == [["保存先", "G-1"], ["AI", "G-3"]]
    assert in_heading_or_code == 0
    assert style["line"] == "underline"
    assert style["style"] == "dotted"
    assert style["color"] == style["parent"]
    assert page.evaluate("history.length") == history_length + 1


def test_body_id_links(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """文中の記録にある ID だけをリンクにし（インラインコードは中身が ID のときだけ）、記録に無い ID・前後が英数字の ID・開いている項目自身の ID・コードブロックの中には付けない。折り返さず、押すとその項目へ移り履歴に積む（正常系）。"""
    # 準備
    url = _write_linked_preview(write_preview, make_item)
    page = open_preview(url, "#tab=docs&view=table&id=A-1")
    page.wait_for_selector("aside.panel .md a.idref")
    history_length = page.evaluate("history.length")
    # 実行
    refs = page.eval_on_selector_all(
        "aside.panel .md a.idref", "a => a.map(x => [x.textContent, x.dataset.id])"
    )
    white_space = page.eval_on_selector("aside.panel .md a.idref", "e => getComputedStyle(e).whiteSpace")
    in_code_block = page.locator("aside.panel .md pre a").count()
    page.click('aside.panel .md a.idref[data-id="D-3"]')
    page.wait_for_function("location.hash.includes('id=D-3')")
    # 検証
    assert refs == [["D-3", "D-3"], ["D-5", "D-5"]]
    assert white_space == "nowrap"
    assert in_code_block == 0
    assert page.evaluate("history.length") == history_length + 1


def test_body_term_tooltip(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """用語の印に乗せるとツールチップで用語・ID・意味を出し、印は aria-describedby でツールチップを指す。印から外れて少し待つと消え、Esc でも消え、ツールチップに乗せている間は消えない（正常系）。"""
    # 準備
    url = _write_linked_preview(write_preview, make_item)
    page = open_preview(url, "#tab=docs&view=table&id=A-1")
    mark = "aside.panel .md a.term >> nth=0"
    page.wait_for_selector("aside.panel .md a.term")
    described = page.get_attribute(mark, "aria-describedby")
    # 実行（乗せる）
    page.hover(mark)
    page.wait_for_selector("#term-tip:popover-open")
    tip = page.evaluate(
        """() => {
            const tip = document.getElementById('term-tip');
            return {role: tip.getAttribute('role'), head: tip.querySelector('.tt-head').textContent, body: tip.querySelector('.tt-body').textContent};
        }"""
    )
    # 実行（印から外れて待つと消える）
    page.mouse.move(2, 2)
    page.wait_for_function("!document.querySelector('#term-tip:popover-open')")
    # 実行（フォーカスで出し、Esc で消す）
    page.focus(mark)
    page.wait_for_selector("#term-tip:popover-open")
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('#term-tip:popover-open')")
    # 実行（乗せて、ツールチップへ動かすと消えない）
    page.hover(mark)
    page.wait_for_selector("#term-tip:popover-open")
    tip_box = page.locator("#term-tip").bounding_box()
    assert tip_box is not None
    page.mouse.move(tip_box["x"] + tip_box["width"] / 2, tip_box["y"] + tip_box["height"] / 2, steps=5)
    page.wait_for_timeout(400)
    kept = page.evaluate("document.querySelector('#term-tip').matches(':popover-open')")
    # 検証
    assert described == "term-tip"
    assert tip == {"role": "tooltip", "head": "保存先G-1", "body": "記録を置く場所"}
    assert kept is True
