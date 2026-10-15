"""画面設計『詳細パネル』の結合テスト。"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from integration.browser_tab_helpers import LINK_PAGE_TITLE, new_tab_after, opened_tabs
from playwright.sync_api import APIResponse, Locator, Page, Route
from preview_a11y_checks import axe_rule_results
from preview_alias_helpers import (
    MARK_IN_PANEL_BODY_JS,
    MARK_MARGIN_PX,
    MIXED_IDS,
    PANEL_MARKS,
    SCROLL_MARK_NEAR_TOP_JS,
    SHARED_TERM_IDS,
    TIP,
    TIP_OPEN,
    write_alias_preview,
    write_term_alias_preview,
)
from preview_body_scroll_helpers import (
    HANGING_LINES_JS,
    LONG_BODY,
    LONG_LINE,
    LONG_LINES_BODY,
    NEW_DECISION,
    SCROLLABLE_REGION_RULE,
    SETTLED_SCROLL_TOP_JS,
    overflows_horizontally,
)
from preview_comment_helpers import (
    COMMENTS_BUTTON,
    COMMENTS_PANEL,
    DETAIL_MESSAGE,
    DETAIL_TEXTAREA,
    DRAFT_WAIT_MS,
    PANEL_REVIEW,
    PILL,
    ROW_CORNER_GAPS_JS,
    ROW_CORNER_TOLERANCE_PX,
    THREE_LINE_BODY,
    UPDATE_TIMEOUT_MS,
    fulfill_problem,
    open_list,
    open_review,
    read_workspace_yaml,
    review_row,
    select_text,
    select_text_for_pill,
    wait_until_focused,
)
from preview_html_body_helpers import (
    BODY_FRAME,
    BODY_WITH_HTML_CODE_BLOCK,
    FRAME_SETTLE_MS,
    MARKED_FRAME,
    frame_fit,
    frame_of,
    select_in_frame,
    wait_frame_rendered,
)
from preview_body_link_helpers import build_body_link_workspace
from preview_html_link_helpers import frame_location
from preview_fixture_types import (
    ID_BUTTON_MIN_SIZE_PX,
    ID_BUTTON_SIZE_JS,
    OpenPreview,
    WritePreview,
    WriteReviewPreview,
    WriteSamplePreview,
)
from preview_history_helpers import build_long_line_diff_workspace, preselect_diff
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
from preview_mark_helpers import MARK_TIMEOUT_MS, marks_of
from preview_minimap_helpers import (
    MINIMAP_HASH,
    MINIMAP_VIEWPORT,
    PANEL_SCOPE,
    added_paragraph_in_view,
    drag_view,
    map_metrics,
    mark_shapes,
    open_minimap,
    press_empty_area,
    scroll_top,
)
from preview_removed_helpers import WITHDRAWN_BADGE, WITHDRAWN_REASONS
from preview_style_checks import TRANSPARENT, animated_properties, pin_id_column, row_backgrounds
from preview_word_diff_helpers import (
    MIN_TEXT_CONTRAST,
    WORD_COLORS_JS,
    WORD_MARKS_JS,
    colour_distance,
    contrast_ratio,
    serve_key_word_diff_workspace,
    serve_word_diff_workspace,
)
from preview_settings_helpers import SETTINGS_PANEL, SETTINGS_PANEL_OPEN, open_settings
from preview_stack_helpers import (
    DETAIL_HASH,
    WIDE_VIEWPORT,
    has_left_front,
    is_inert,
    open_narrow,
    wait_front,
)
from workspace_fixtures import ADOPTED_OPTIONS, RECORD_DIR, CallTool, MakeComment, MakeDraft, MakeItem, MakeWorkspace

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

# D-1 へのコメントの行の「修正」「削除」の読み上げの名前
ROW_EDIT_NAME = "D-1 へのコメントを修正"
ROW_REMOVE_NAME = "D-1 へのコメントを削除"

# 行の操作と見出しの操作が重なるかを数える（パネルの動きが終わってから）
ROW_ACTIONS_OVERLAP_JS = """async (selector) => {
    await Promise.all(document.getAnimations().map(animation => animation.finished));
    const actions = document.querySelector(`${selector} .row-actions`).getBoundingClientRect();
    const overlaps = [...document.querySelectorAll('aside.panel .panel-head button')].filter(button => {
        const box = button.getBoundingClientRect();
        return box.left < actions.right && box.right > actions.left && box.top < actions.bottom && box.bottom > actions.top;
    });
    return overlaps.length;
}"""

# 書き換えの入力欄が、行の本文の幅から欠けてよい上限（px）
FIELD_WIDTH_TOLERANCE_PX = 2

# 行の操作のアイコンを、行ごとに並びのまま読む
ROW_ICONS_JS = "row => [...row.querySelectorAll('.row-actions button svg')].map(svg => svg.innerHTML)"


def _hold_post_response(route: Route, held: list[tuple[Route, APIResponse]]) -> None:
    """溜める POST はサーバーへ流して応答を控え（画面へは返さない）、GET はそのまま流す。"""
    if route.request.method == "POST":
        held.append((route, route.fetch()))
    else:
        route.continue_()


def _row_button(page: Page, comment_id: str, name: str) -> Locator:
    """詳細パネルのコメントの行の中の、読み上げの名前が name のボタンを返す。"""
    return page.locator(review_row("aside.panel", comment_id)).get_by_role("button", name=name, exact=True)


def _open_detail_from_list(page: Page, comment_id: str) -> None:
    """コメントの一覧を開き、行の向けた項目を押して、一覧を開いたまま詳細パネルを開く。"""
    open_review(page)
    page.click(f"{review_row(COMMENTS_PANEL, comment_id)} button.row-target")
    page.wait_for_selector("aside.panel.open")


def _start_edit(page: Page, comment_id: str, body: str) -> str:
    """行の「修正」を押して書き換えの入力欄に body を入れ、その入力欄の選択子を返す。"""
    _row_button(page, comment_id, ROW_EDIT_NAME).click()
    field = f"{review_row('aside.panel', comment_id)} form.row-edit textarea"
    page.wait_for_selector(field)
    page.fill(field, body)
    return field


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
        "opts => opts.map(o => [o.querySelector('.key').textContent, o.querySelector('.res')?.textContent ?? null, o.classList.contains('adopted')])",
    )
    # 採用でも不採用でもない案には、結果の印を出さない
    assert options == [["A", "採用", True], ["B", None, False]]
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


# Markdown で書いた値（太字・コード・箇条書きを持つ）
MARKDOWN_VALUE = "**太字**と`コード`\n\n- 箇条書き"


def _section_titles(page: Page) -> list[str]:
    """パネルの節の見出しを上から並べて返す。"""
    return page.eval_on_selector_all("aside.panel .d-sec h3", "hs => hs.map(h => h.textContent)")


def test_lead_before_options(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """背景（問い）をタイトルの下・案の節の前に出す（正常系）。"""
    # 準備
    url = write_sample_preview()
    # 実行
    page = open_preview(url, "#tab=decisions&view=table&id=D-2")
    # 検証
    order = page.evaluate(
        """() => {
          const lead = document.querySelector('aside.panel .d-lead');
          const title = document.querySelector('aside.panel .d-title');
          const options = [...document.querySelectorAll('aside.panel .d-sec')]
            .find(section => section.querySelector('h3').textContent === '案');
          const after = (a, b) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
          return [lead.textContent.trim(), after(title, lead), after(lead, options)];
        }"""
    )
    assert order == ["キーをどう持つか", True, True]


def test_recommended_mark(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """どの案も採用でないとき、推奨の案の見出しの右に星と「推奨」のバッジを出し、ほかの案には出さない（正常系）。"""
    # 準備
    url = write_preview(
        make_item(
            "D-1",
            status="未決定",
            options=[
                {"key": "A", "content": "案 A"},
                {"key": "B", "content": "案 B", "recommended": True},
            ],
        )
    )
    # 実行
    page = open_preview(url, "#tab=decisions&view=table&id=D-1")
    page.wait_for_selector("aside.panel .opt")
    # 検証
    marks = page.eval_on_selector_all(
        "aside.panel .opt",
        """opts => opts.map(o => [
          o.querySelector('.key').textContent,
          o.querySelector('.o-head .rec-badge')?.textContent ?? null,
          o.classList.contains('recommended'),
          o.querySelector('.res')?.textContent ?? null,
        ])""",
    )
    assert marks == [["A", None, False, None], ["B", "推奨", True, None]]
    assert page.locator("aside.panel .opt .rec-badge svg").count() == 1


def test_recommended_mark_when_adopted(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """採用した案があれば、推奨の印は出さず、採用の印だけを出す（正常系）。"""
    # 準備
    url = write_preview(
        make_item(
            "D-1",
            status="決定済み",
            options=[
                {"key": "A", "content": "案 A", "adopted": True},
                {"key": "B", "content": "案 B", "recommended": True},
            ],
        )
    )
    # 実行
    page = open_preview(url, "#tab=decisions&view=table&id=D-1")
    page.wait_for_selector("aside.panel .opt")
    # 検証
    assert page.locator("aside.panel .rec-badge").count() == 0
    assert page.locator("aside.panel .opt.adopted .res").inner_text() == "採用"


def test_adopted_section(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """決定内容と理由を「採用した案と理由」の節に、案の後・本文の前に並べる（正常系）。"""
    # 準備
    url = write_preview(
        make_item(
            "D-1",
            status="決定済み",
            answer="種類ごとに分ける",
            reason="探しやすい",
            options=ADOPTED_OPTIONS,
            body="D-1.md",
        ),
        bodies={"D-1.md": "## 経緯\n\n本文の段落\n"},
    )
    # 実行
    page = open_preview(url, "#tab=decisions&view=table&id=D-1")
    page.wait_for_selector("aside.panel .md:not(.md-value)")
    # 検証
    assert _section_titles(page) == ["案", "採用した案と理由", "本文", "レビュー中のコメント0"]
    rows = page.eval_on_selector_all(
        "aside.panel .d-sec:has(h3:text-is('採用した案と理由')) .d-answer",
        "rows => rows.map(r => [r.querySelector('b').textContent, r.querySelector('.d-value').textContent.trim()])",
    )
    assert rows == [["決定内容", "種類ごとに分ける"], ["理由", "探しやすい"]]


@pytest.mark.parametrize(
    ("values", "labels"),
    [
        pytest.param({"answer": "種類ごとに分ける"}, ["決定内容"], id="answer_only"),
        pytest.param({"reason": "探しやすい"}, ["理由"], id="reason_only"),
        pytest.param({}, [], id="none"),
    ],
)
def test_adopted_section_when_partial(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    values: dict[str, str],
    labels: list[str],
) -> None:
    """決定内容と理由は値のあるものだけを並べ、どちらも無ければ節ごと出さない（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1", status="決定済み", options=ADOPTED_OPTIONS, **values))
    # 実行
    page = open_preview(url, "#tab=decisions&view=table&id=D-1")
    page.wait_for_selector("aside.panel .opt")
    # 検証
    rows = page.eval_on_selector_all(
        "aside.panel .d-sec:has(h3:text-is('採用した案と理由')) .d-answer b",
        "bs => bs.map(b => b.textContent)",
    )
    assert rows == labels
    assert ("採用した案と理由" in _section_titles(page)) is (labels != [])


def test_value_markdown(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """検討事項の文字列の値（背景・決定内容・理由・案の各値）を Markdown で描き、配列の値は「、」でつなぐ（正常系）。"""
    # 準備
    url = write_preview(
        make_item(
            "D-1",
            status="決定済み",
            lead=MARKDOWN_VALUE,
            answer=MARKDOWN_VALUE,
            reason=MARKDOWN_VALUE,
            options=[
                {
                    "key": "A",
                    "content": MARKDOWN_VALUE,
                    "pros": MARKDOWN_VALUE,
                    "cons": ["一つ目", "二つ目"],
                    "note": MARKDOWN_VALUE,
                    "reason": MARKDOWN_VALUE,
                    "adopted": True,
                }
            ],
        )
    )
    # 実行
    page = open_preview(url, "#tab=decisions&view=table&id=D-1")
    page.wait_for_selector("aside.panel .opt")
    # 検証
    drawn = page.eval_on_selector_all(
        "aside.panel .md-value",
        "els => els.map(e => [e.querySelectorAll('strong').length, e.querySelectorAll('code').length, e.querySelectorAll('li').length])",
    )
    assert drawn.count([1, 1, 1]) == 7
    assert drawn.count([0, 0, 0]) == 1
    assert page.inner_text('aside.panel dd[data-key="options[A].cons"]') == "一つ目、二つ目"
    # 値の要素は、本文と違い行の印を持たない
    assert page.locator("aside.panel .md-value [data-line-start]").count() == 0


@pytest.mark.parametrize(
    ("item_id", "tab", "values"),
    [
        pytest.param("T-1", "tasks", {"reason": MARKDOWN_VALUE}, id="task_reason"),
        pytest.param(
            "R-1",
            "research",
            {"question": MARKDOWN_VALUE, "conclusion": MARKDOWN_VALUE},
            id="research",
        ),
        pytest.param("G-1", "terms", {"meaning": MARKDOWN_VALUE}, id="term_meaning"),
        pytest.param("N-1", "notes", {"content": MARKDOWN_VALUE}, id="note_content"),
    ],
)
def test_value_markdown_when_other_kinds(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    item_id: str,
    tab: str,
    values: dict[str, str],
) -> None:
    """タスクの理由・調査の問いと結論・用語の意味・メモの中身も Markdown で描く（正常系）。"""
    # 準備
    url = write_preview(make_item(item_id, **values))
    # 実行
    page = open_preview(url, f"#tab={tab}&view=table&id={item_id}")
    page.wait_for_selector("aside.panel .md-value")
    # 検証
    drawn = page.eval_on_selector_all(
        "aside.panel .md-value",
        "els => els.map(e => [e.querySelectorAll('strong').length, e.querySelectorAll('code').length, e.querySelectorAll('li').length])",
    )
    assert drawn == [[1, 1, 1]] * len(values)


def test_value_markdown_when_library_unavailable(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem, page: Page
) -> None:
    """marked か DOMPurify を読めないときは、値を文字のまま出す（異常系）。"""
    # 準備
    url = write_preview(make_item("D-1", status="未決定", lead="**太字**", options=[{"key": "A", "content": "案 A"}]))
    page.route("https://cdn.jsdelivr.net/**", lambda route: route.abort())
    # 実行
    open_preview(url, "#tab=decisions&view=table&id=D-1")
    page.wait_for_selector("aside.panel .d-lead")
    # 検証
    assert page.inner_text("aside.panel .d-lead") == "**太字**"
    assert page.locator("aside.panel .d-lead strong").count() == 0


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
    page.wait_for_selector("aside.panel.open .detail .md:not(.md-value)")
    # 検証
    assert page.inner_text("aside.panel .panel-kind") == panel_kind
    assert page.locator("aside.panel .d-sec h3", has_text="本文").count() == 1
    assert "会話で持ち越した" in page.inner_text("aside.panel .detail .md:not(.md-value)")


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
    assert sections == ["案", "前提", "後続の項目", "関連タスク", "レビュー中のコメント0"]
    assert "id=D-1" in page.evaluate("location.hash")


def test_referenced_by(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """関連で指している項目から、参照元の節で指されている項目を開ける（正常系）。"""
    # 準備
    url = write_preview(
        make_item("D-1", status="決定済み", options=ADOPTED_OPTIONS),
        make_item("D-2", status="決定済み", options=ADOPTED_OPTIONS, related=["D-1"]),
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


def _open_diagram(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> Page:
    """D-3 の詳細パネルを開き、本文の図を描き終わるまで待つ。"""
    url = write_sample_preview()
    page = open_preview(url, "#tab=decisions&view=table&id=D-3")
    page.wait_for_selector("aside.panel .diagram .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    return page


def test_diagram_surface_cursor(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """通常の表示の図の面は、虫眼鏡ではなく既定のカーソルを出す（正常系）。"""
    # 準備
    page = _open_diagram(write_sample_preview, open_preview)
    # 実行
    cursors = page.eval_on_selector_all(
        "aside.panel .diagram .mermaid, aside.panel .diagram .mermaid svg",
        "elements => elements.map(e => getComputedStyle(e).cursor)",
    )
    # 検証
    assert cursors == ["auto", "auto"]


def test_diagram_text_cursor(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """通常の表示の図の文字は、文字を選ぶカーソルで選べる（正常系）。"""
    # 準備
    page = _open_diagram(write_sample_preview, open_preview)
    # 実行
    styles = page.eval_on_selector_all(
        "aside.panel .diagram .mermaid svg .nodeLabel",
        "elements => elements.map(e => [getComputedStyle(e).cursor, getComputedStyle(e).userSelect])",
    )
    # 検証
    assert styles == [["text", "text"], ["text", "text"]]


def test_diagram_text_drag_select(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """通常の表示の図の文字を、ドラッグで選べる（正常系）。"""
    # 準備
    page = _open_diagram(write_sample_preview, open_preview)
    labels = page.locator("aside.panel .diagram .mermaid svg .nodeLabel")
    labels.first.scroll_into_view_if_needed()
    first = labels.first.bounding_box()
    last = labels.last.bounding_box()
    assert first is not None
    assert last is not None
    # 実行
    page.mouse.move(first["x"] + 1, first["y"] + first["height"] / 2)
    page.mouse.down()
    page.mouse.move(last["x"] + last["width"] - 1, last["y"] + last["height"] / 2, steps=5)
    page.mouse.up()
    # 検証
    selected = page.evaluate("getSelection().toString()")
    assert "A" in selected
    assert "B" in selected


def test_diagram_press_does_not_open_viewer(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """通常の表示の図は、面も文字も押して図の拡大を開かない（正常系）。"""
    # 準備
    page = _open_diagram(write_sample_preview, open_preview)
    # 実行
    page.locator("aside.panel .diagram .mermaid").click(position={"x": 5, "y": 5})
    page.locator("aside.panel .diagram .mermaid svg .nodeLabel").first.click()
    page.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    # 検証
    assert page.locator("dialog.viewer[open]").count() == 0


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
    page.wait_for_selector("aside.panel .md:not(.md-value)")
    select_text_for_pill(page, "aside.panel .md:not(.md-value)", "言い換えたい文")
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
    """その項目へのレビュー中のコメントを溜めた順に、箇所（名前と選んだ文）と本文つきで並べ、行ごとに「修正」「削除」を置く（正常系）。"""
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
    # 行ごとの「修正」「削除」（読み上げの名前と `title`）。チェックは持たない（まとめて送るは一覧で行う）
    assert page.eval_on_selector_all(
        "aside.panel .d-review li",
        "rows => rows.map(r => [...r.querySelectorAll('.row-actions button')].map(b => [b.getAttribute('aria-label'), b.title]))",
    ) == [
        [["D-1 へのコメントを修正", "修正"], ["D-1 へのコメントを削除", "削除"]],
        [["D-1 へのコメントを修正", "修正"], ["D-1 へのコメントを削除", "削除"]],
    ]
    assert page.locator("aside.panel .d-review input").count() == 0
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


def test_review_row_actions_at_top_right(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """各行の右上に「修正」「削除」のボタンを、乗せなくても見える形で常に置く（正常系）。"""
    # 準備
    url, _ = served_review_rows
    # 実行
    page = open_preview(url, "#tab=decisions&id=D-1")
    # 検証
    row = review_row("aside.panel", "C-1")
    gaps = page.evaluate(ROW_CORNER_GAPS_JS, row)
    assert gaps["right"] <= ROW_CORNER_TOLERANCE_PX
    assert gaps["top"] <= ROW_CORNER_TOLERANCE_PX
    assert _row_button(page, "C-1", ROW_EDIT_NAME).is_visible() is True
    assert _row_button(page, "C-1", ROW_REMOVE_NAME).is_visible() is True


@pytest.mark.parametrize("width", [390, 720])
def test_review_row_actions_at_top_right_when_narrow(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview, width: int
) -> None:
    """幅 720px 以下でも、各行の「修正」「削除」を行の右上の隅から 24px 以内に置き、パネルの見出しの操作と重ねない（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1")
    # 実行
    page.set_viewport_size({"width": width, "height": NARROW_HEIGHT})
    # 検証
    row = review_row("aside.panel", "C-1")
    gaps = page.evaluate(ROW_CORNER_GAPS_JS, row)
    assert 0 <= gaps["right"] <= ROW_CORNER_TOLERANCE_PX
    assert 0 <= gaps["top"] <= ROW_CORNER_TOLERANCE_PX
    assert page.evaluate(ROW_ACTIONS_OVERLAP_JS, row) == 0


def test_review_row_edit_button(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """行の「修正」は鉛筆の印だけのボタンで、読み上げの名前は「{項目の ID} へのコメントを修正」、`title` は「修正」にする（正常系）。"""
    # 準備
    url, _ = served_review_rows
    # 実行
    page = open_preview(url, "#tab=decisions&id=D-1")
    # 検証
    button = _row_button(page, "C-1", ROW_EDIT_NAME)
    assert button.get_attribute("title") == "修正"
    assert button.locator("svg").count() == 1
    assert button.inner_text() == ""


def test_review_row_remove_button(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """行の「削除」はごみ箱の印だけのボタンで、読み上げの名前は「{項目の ID} へのコメントを削除」、`title` は「削除」にする（正常系）。"""
    # 準備
    url, _ = served_review_rows
    # 実行
    page = open_preview(url, "#tab=decisions&id=D-1")
    # 検証
    button = _row_button(page, "C-1", ROW_REMOVE_NAME)
    assert button.get_attribute("title") == "削除"
    assert button.locator("svg").count() == 1
    assert button.inner_text() == ""


def test_review_row_actions_same_icons_as_list(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """行の「修正」「削除」は、コメントの一覧の行と同じアイコンにする（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url)
    # 実行
    _open_detail_from_list(page, "C-1")
    # 検証
    in_detail = page.eval_on_selector(review_row("aside.panel", "C-1"), ROW_ICONS_JS)
    in_list = page.eval_on_selector(review_row(COMMENTS_PANEL, "C-1"), ROW_ICONS_JS)
    assert len(in_detail) == 2
    assert in_detail == in_list


def test_review_row_edit_start(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """「修正」で行の本文を行の幅いっぱいの入力欄に切り替えて入力欄へフォーカスを移し、その行には「修正」「削除」を出さない（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1")
    row = review_row("aside.panel", "C-1")
    # 実行
    _row_button(page, "C-1", ROW_EDIT_NAME).click()
    # 検証
    field = f"{row} form.row-edit textarea"
    wait_until_focused(page, field)
    assert page.input_value(field) == "案 A にする"
    assert page.locator(f"{row} .review-body").count() == 0
    assert page.locator(f"{row} .row-actions").count() == 0
    assert page.locator(f"{review_row('aside.panel', 'C-2')} .row-actions").count() == 1
    field_box = page.locator(field).bounding_box()
    main_box = page.locator(f"{row} .review-main").bounding_box()
    assert field_box is not None
    assert main_box is not None
    assert main_box["width"] - field_box["width"] <= FIELD_WIDTH_TOLERANCE_PX


def test_review_row_remove(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """「削除」で確認を挟まず消し、行を「コメントを削除しました。」と「元に戻す」に置き換えて「元に戻す」へフォーカスを移す（正常系）。"""
    # 準備
    url, root = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1")
    row = review_row("aside.panel", "C-1")
    # 実行
    _row_button(page, "C-1", ROW_REMOVE_NAME).click()
    page.wait_for_selector(f"{row}.removed", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.locator("dialog[open]").count() == 0
    assert page.inner_text(f"{row} .removed-msg") == "コメントを削除しました。"
    assert page.get_attribute(f"{row} .removed-msg", "role") == "status"
    wait_until_focused(page, f"{row} button")
    assert page.get_by_role("button", name="元に戻す").count() == 1
    assert [item["id"] for item in read_workspace_yaml(root, "comments.yaml")["items"]] == ["C-2", "C-3"]


def test_review_row_remove_updates_counts(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """削除した後、見出しの件数とトップバーのコメントのボタンの件数を、消した行を数えずに描き直し、消した行は溜めた順の元の場所に残す（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1")
    # 実行
    _row_button(page, "C-1", ROW_REMOVE_NAME).click()
    page.wait_for_selector(f"{review_row('aside.panel', 'C-1')}.removed", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.inner_text(f"{PANEL_REVIEW} h3") == "レビュー中のコメント1"
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "2"
    assert page.eval_on_selector_all(
        f"{PANEL_REVIEW} li", "rows => rows.map(r => [r.dataset.comment, r.classList.contains('removed')])"
    ) == [["C-1", True], ["C-2", False]]


def test_review_row_remove_updates_mark(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """削除した後、本文の領域のコメントの印の件数を描き直す（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url, "#tab=decisions&view=table&id=D-1")
    assert marks_of(page) == {"D-1": "2", "D-2": "1"}
    # 実行
    _row_button(page, "C-1", ROW_REMOVE_NAME).click()
    page.wait_for_function(
        "document.querySelector(\"main#main [data-comment-target='D-1'] .cmk-n\")?.textContent === '1'",
        timeout=MARK_TIMEOUT_MS,
    )
    # 検証
    assert marks_of(page) == {"D-1": "1", "D-2": "1"}


def test_review_row_remove_when_list_open(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """コメントの一覧を開いているときは、詳細パネルで消した行を一覧も同じ消した行に描き直す（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url)
    _open_detail_from_list(page, "C-1")
    # 実行
    _row_button(page, "C-1", ROW_REMOVE_NAME).click()
    page.wait_for_selector(f"{review_row('aside.panel', 'C-1')}.removed", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    in_list = review_row(COMMENTS_PANEL, "C-1")
    page.wait_for_selector(f"{in_list}.removed")
    assert page.inner_text(f"{in_list} .removed-msg") == "コメントを削除しました。"
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "2"


def test_review_row_edit(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """「修正」で `PATCH /api/comments/{id}` へ `body` だけを送り、200 なら本文に戻して「行の修正」へフォーカスを戻す（正常系）。"""
    # 準備
    url, root = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1")
    sent: list[Any] = []
    page.on(
        "request",
        lambda request: sent.append(request.post_data_json) if request.method == "PATCH" else None,
    )
    row = review_row("aside.panel", "C-1")
    _start_edit(page, "C-1", "案 B にする")
    # 実行
    page.locator(f"{row} form.row-edit").get_by_role("button", name="修正", exact=True).click()
    page.wait_for_function(
        "document.querySelector(\"aside.panel li[data-comment='C-1'] .review-body\")?.textContent === '案 B にする'",
        timeout=UPDATE_TIMEOUT_MS,
    )
    # 検証
    assert page.locator(f"{row} form.row-edit").count() == 0
    assert sent == [{"body": "案 B にする"}]
    assert read_workspace_yaml(root, "comments.yaml")["items"][0]["body"] == "案 B にする"
    wait_until_focused(page, f"{row} button[title='修正']")


def test_review_row_edit_when_body_empty(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """空白だけの本文は送らず、入力欄を要見直しにして「コメントを入れてから直してください。」を出す（異常系）。"""
    # 準備
    url, root = served_review_rows
    patches: list[str] = []
    page.on(
        "request",
        lambda request: patches.append(request.url) if request.method == "PATCH" else None,
    )
    open_preview(url, "#tab=decisions&id=D-1")
    row = review_row("aside.panel", "C-1")
    field = _start_edit(page, "C-1", "   ")
    # 実行
    page.locator(f"{row} form.row-edit").get_by_role("button", name="修正", exact=True).click()
    # 検証
    assert page.inner_text(f"{row} form.row-edit .send-msg") == "コメントを入れてから直してください。"
    assert page.get_attribute(f"{row} form.row-edit .send-msg", "role") == "alert"
    assert page.get_attribute(field, "aria-invalid") == "true"
    assert patches == []
    assert read_workspace_yaml(root, "comments.yaml")["items"][0]["body"] == "案 A にする"


def test_review_row_edit_when_server_refuses(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """サーバーが断ったときは、入力を残してエラーの `detail` を印のアイコンと共に出す（異常系）。"""
    # 準備
    url, root = served_review_rows
    page.route(
        "**/api/comments/C-1",
        lambda route: (
            fulfill_problem(route, 500, "comments.yaml を書けません")
            if route.request.method == "PATCH"
            else route.continue_()
        ),
    )
    open_preview(url, "#tab=decisions&id=D-1")
    row = review_row("aside.panel", "C-1")
    field = _start_edit(page, "C-1", "案 B にする")
    # 実行
    page.locator(f"{row} form.row-edit").get_by_role("button", name="修正", exact=True).click()
    page.wait_for_selector(f"{row} form.row-edit .send-msg svg.icon", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.inner_text(f"{row} form.row-edit .send-msg") == "comments.yaml を書けません"
    assert page.input_value(field) == "案 B にする"
    assert read_workspace_yaml(root, "comments.yaml")["items"][0]["body"] == "案 A にする"


def test_review_row_edit_when_unreachable(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """サーバーに届かないときは、入力を残して「サーバーが止まっています。立ち上げ直してから直してください。」を出す（異常系）。"""
    # 準備
    url, _ = served_review_rows
    page.route(
        "**/api/comments/C-1",
        lambda route: route.abort() if route.request.method == "PATCH" else route.continue_(),
    )
    open_preview(url, "#tab=decisions&id=D-1")
    row = review_row("aside.panel", "C-1")
    field = _start_edit(page, "C-1", "案 B にする")
    # 実行
    page.locator(f"{row} form.row-edit").get_by_role("button", name="修正", exact=True).click()
    page.wait_for_selector(f"{row} form.row-edit .send-msg svg.icon", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert (
        page.inner_text(f"{row} form.row-edit .send-msg")
        == "サーバーが止まっています。立ち上げ直してから直してください。"
    )
    assert page.input_value(field) == "案 B にする"


def test_review_row_edit_when_cancelled(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """「キャンセル」で書き換えを捨てて本文に戻し、「行の修正」へフォーカスを戻す（正常系）。"""
    # 準備
    url, root = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1")
    row = review_row("aside.panel", "C-1")
    _start_edit(page, "C-1", "捨てる")
    # 実行
    page.locator(f"{row} form.row-edit").get_by_role("button", name="キャンセル").click()
    # 検証
    assert page.inner_text(f"{row} .review-body") == "案 A にする"
    assert page.locator(f"{row} form.row-edit").count() == 0
    wait_until_focused(page, f"{row} button[title='修正']")
    assert read_workspace_yaml(root, "comments.yaml")["items"][0]["body"] == "案 A にする"


def test_review_row_edit_when_escaped(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """入力欄の Esc で書き換えを捨てて本文に戻し、「行の修正」へフォーカスを戻す。Esc ではパネルを閉じない（正常系）。"""
    # 準備
    url, root = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1")
    row = review_row("aside.panel", "C-1")
    field = _start_edit(page, "C-1", "捨てる")
    # 実行
    page.press(field, "Escape")
    # 検証
    assert page.inner_text(f"{row} .review-body") == "案 A にする"
    assert page.locator(f"{row} form.row-edit").count() == 0
    wait_until_focused(page, f"{row} button[title='修正']")
    assert page.locator("aside.panel.open").count() == 1
    assert read_workspace_yaml(root, "comments.yaml")["items"][0]["body"] == "案 A にする"


def test_review_row_edit_when_other_row_started(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """別の行の「修正」を押すと、前の書き換えを捨てる。書き換える行は 1 行だけ（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1")
    _start_edit(page, "C-1", "捨てる")
    # 実行
    _row_button(page, "C-2", ROW_EDIT_NAME).click()
    page.wait_for_selector(f"{review_row('aside.panel', 'C-2')} form.row-edit")
    # 検証
    assert page.locator(f"{review_row('aside.panel', 'C-1')} form.row-edit").count() == 0
    assert page.inner_text(f"{review_row('aside.panel', 'C-1')} .review-body") == "案 A にする"
    assert page.locator(f"{PANEL_REVIEW} form.row-edit").count() == 1


def test_review_row_edit_max_length(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """書き換えの入力欄の最大長は 10000 文字にする（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1")
    # 実行
    field = _start_edit(page, "C-1", "案 A にする")
    # 検証
    assert page.get_attribute(field, "maxlength") == "10000"


def test_review_row_restore(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """「元に戻す」で消した中身を同じ ID と日時で元の場所に戻し、戻した行の「行の修正」へフォーカスを移す（正常系）。"""
    # 準備
    url, root = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1")
    row = review_row("aside.panel", "C-1")
    created = read_workspace_yaml(root, "comments.yaml")["items"][0]["created"]
    _row_button(page, "C-1", ROW_REMOVE_NAME).click()
    page.wait_for_selector(f"{row}.removed", timeout=UPDATE_TIMEOUT_MS)
    # 実行
    page.locator(f"{row}.removed").get_by_role("button", name="元に戻す").click()
    page.wait_for_selector(f"{row} .review-body", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.inner_text(f"{row} .review-body") == "案 A にする"
    assert page.eval_on_selector_all(f"{PANEL_REVIEW} li", "rows => rows.map(r => r.dataset.comment)") == [
        "C-1",
        "C-2",
    ]
    assert page.inner_text(f"{PANEL_REVIEW} h3") == "レビュー中のコメント2"
    restored = read_workspace_yaml(root, "comments.yaml")["items"][0]
    assert (restored["id"], restored["created"]) == ("C-1", created)
    wait_until_focused(page, f"{row} button[title='修正']")


def test_review_row_restore_when_moved(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """コメントの一覧を開いていないとき、別の項目へ移ると消した行の「元に戻す」を出さなくなる（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1")
    _row_button(page, "C-1", ROW_REMOVE_NAME).click()
    page.wait_for_selector(f"{review_row('aside.panel', 'C-1')}.removed", timeout=UPDATE_TIMEOUT_MS)
    # 実行
    page.evaluate("location.hash = '#tab=decisions&id=D-2'")
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === 'D-2の題'")
    page.evaluate("location.hash = '#tab=decisions&id=D-1'")
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === 'D-1の題'")
    # 検証
    assert page.get_by_role("button", name="元に戻す").count() == 0
    assert page.locator(f"{PANEL_REVIEW} li[data-comment='C-1']").count() == 0


def test_review_row_restore_when_panel_closed(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """コメントの一覧を開いていないとき、パネルを閉じると消した行の「元に戻す」を出さなくなる（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1")
    _row_button(page, "C-1", ROW_REMOVE_NAME).click()
    page.wait_for_selector(f"{review_row('aside.panel', 'C-1')}.removed", timeout=UPDATE_TIMEOUT_MS)
    # 実行
    page.click("aside.panel button[data-act='close']")
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    page.evaluate("location.hash = '#tab=decisions&id=D-1'")
    page.wait_for_selector("aside.panel.open")
    # 検証
    assert page.get_by_role("button", name="元に戻す").count() == 0
    assert page.locator(f"{PANEL_REVIEW} li[data-comment='C-1']").count() == 0


def test_review_row_restore_when_restored_in_list(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """コメントの一覧を開いている間は一覧と同じ消した行を見て、一覧の「元に戻す」で戻すと詳細パネルの行も戻る（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url)
    _open_detail_from_list(page, "C-1")
    _row_button(page, "C-1", ROW_REMOVE_NAME).click()
    page.wait_for_selector(f"{review_row('aside.panel', 'C-1')}.removed", timeout=UPDATE_TIMEOUT_MS)
    in_list = review_row(COMMENTS_PANEL, "C-1")
    page.wait_for_selector(f"{in_list}.removed")
    # 実行
    page.locator(f"{in_list}.removed").get_by_role("button", name="元に戻す").click()
    # 検証
    page.wait_for_selector(f"{review_row('aside.panel', 'C-1')} .review-body", timeout=UPDATE_TIMEOUT_MS)
    assert page.inner_text(f"{review_row('aside.panel', 'C-1')} .review-body") == "案 A にする"
    assert page.locator(f"{review_row('aside.panel', 'C-1')}.removed").count() == 0


def test_review_row_restore_when_list_closed(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """コメントの一覧を閉じた時点で、詳細パネルの消した行も一覧と一緒に消える（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url)
    _open_detail_from_list(page, "C-1")
    _row_button(page, "C-1", ROW_REMOVE_NAME).click()
    page.wait_for_selector(f"{review_row('aside.panel', 'C-1')}.removed", timeout=UPDATE_TIMEOUT_MS)
    # 実行
    page.get_by_role("button", name="コメントの一覧を閉じる").click()
    page.wait_for_function("!document.querySelector('aside.comments-panel.open')")
    # 検証
    assert page.get_by_role("button", name="元に戻す").count() == 0
    assert page.locator(f"{PANEL_REVIEW} li[data-comment='C-1']").count() == 0


def test_review_row_keyboard(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """キーボードだけで、行を直す・消す・戻すまで届く（正常系）。"""
    # 準備
    url, root = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1")
    row = review_row("aside.panel", "C-1")
    # 実行（直す）
    _row_button(page, "C-1", ROW_EDIT_NAME).focus()
    page.keyboard.press("Enter")
    wait_until_focused(page, f"{row} form.row-edit textarea")
    page.keyboard.press("Control+A")
    page.keyboard.type("案 B にする")
    page.keyboard.press("Tab")
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")
    page.wait_for_function(
        "document.querySelector(\"aside.panel li[data-comment='C-1'] .review-body\")?.textContent === '案 B にする'",
        timeout=UPDATE_TIMEOUT_MS,
    )
    wait_until_focused(page, f"{row} button[title='修正']")
    # 実行（消す）
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")
    page.wait_for_selector(f"{row}.removed", timeout=UPDATE_TIMEOUT_MS)
    wait_until_focused(page, f"{row} button")
    # 実行（戻す）
    page.keyboard.press("Enter")
    page.wait_for_selector(f"{row} .review-body", timeout=UPDATE_TIMEOUT_MS)
    wait_until_focused(page, f"{row} button[title='修正']")
    # 検証
    items = read_workspace_yaml(root, "comments.yaml")["items"]
    assert [(item["id"], item["body"]) for item in items] == [
        ("C-1", "案 B にする"),
        ("C-2", "案 B も見たい"),
        ("C-3", "別の項目へのコメント"),
    ]


def test_review_row_remove_keeps_input(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """行を消して描き直しても、コメントの入力欄の書きかけを保つ（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1")
    page.fill(DETAIL_TEXTAREA, "書きかけ")
    # 実行
    _row_button(page, "C-1", ROW_REMOVE_NAME).click()
    page.wait_for_selector(f"{review_row('aside.panel', 'C-1')}.removed", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.input_value(DETAIL_TEXTAREA) == "書きかけ"


def test_review_row_remove_keeps_scroll(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
) -> None:
    """行を消して描き直しても、本文のスクロール領域のスクロールの位置を保つ（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("A-1"),
        bodies={"A-1.md": LONG_BODY},
        comments=(
            make_comment("C-1", target="A-1", body="1 件目"),
            make_comment("C-2", target="A-1", body="2 件目"),
        ),
    )
    page = open_preview(url, "#tab=docs&id=A-1")
    button = _row_button(page, "C-1", "A-1 へのコメントを削除")
    button.scroll_into_view_if_needed()
    scrolled = page.evaluate(SETTLED_SCROLL_TOP_JS, PANEL_BODY)
    # 実行
    button.click()
    page.wait_for_selector(f"{review_row('aside.panel', 'C-1')}.removed", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert scrolled > 0
    assert page.evaluate(SETTLED_SCROLL_TOP_JS, PANEL_BODY) == scrolled


def test_selection_entry_when_in_review_comments(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """レビュー中のコメントの本文を選んでも、選んだ箇所のコメントの入口を出さない（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1")
    # 実行
    select_text(page, f"{review_row('aside.panel', 'C-1')} .review-body", "案 A にする")
    page.wait_for_timeout(SELECTION_SETTLE_MS)
    # 検証
    assert page.locator(PILL).count() == 0


def test_selection_entry_when_in_review_edit(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """行の書き換えの入力欄の文を選んでも、選んだ箇所のコメントの入口を出さない（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url, "#tab=decisions&id=D-1")
    field = _start_edit(page, "C-1", "案 A にする")
    # 実行
    page.locator(field).select_text()
    page.wait_for_timeout(SELECTION_SETTLE_MS)
    # 検証
    assert page.locator(PILL).count() == 0


def test_selection_entry_when_body(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """本文の文を選ぶと入口を出し、押すと入口を閉じて、本文の行の範囲の箇所をコメントの入力に添えて入力欄へフォーカスを移す（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("A-1"), bodies={"A-1.md": THREE_LINE_BODY})
    page = open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel .md:not(.md-value)")
    history_length = page.evaluate("history.length")
    # 実行
    select_text_for_pill(page, "aside.panel .md:not(.md-value)", "言い換えたい文")
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
    page.wait_for_selector("aside.panel .md:not(.md-value)")
    select_text_for_pill(page, "aside.panel .md:not(.md-value)", "言い換えたい文")
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
    open_review(page)
    # 実行
    page.click(f"{COMMENTS_PANEL} li[data-comment='C-1'] button.row-target")
    page.wait_for_selector("aside.panel.open .md:not(.md-value) .loc-hit")
    # 検証
    assert page.inner_text("aside.panel .md:not(.md-value) .loc-hit") == "最初の文 言い換えたい文 最後の文"
    assert page.eval_on_selector(
        "aside.panel .md:not(.md-value) .loc-hit", "e => getComputedStyle(e).backgroundColor"
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
    open_review(page)
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
    open_review(page)
    # 実行
    page.click(f"{COMMENTS_PANEL} li[data-comment='C-1'] button.row-target")
    page.wait_for_selector("aside.panel.open .md:not(.md-value)")
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


@pytest.mark.parametrize(
    ("open_panel", "name", "selector"),
    [
        pytest.param(open_settings, "settings", SETTINGS_PANEL, id="settings"),
        pytest.param(open_list, "comments", COMMENTS_PANEL, id="comments"),
    ],
)
def test_escape_closes_front_left_panel_first_when_narrow(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    open_panel: Callable[[Page], None],
    name: str,
    selector: str,
) -> None:
    """幅 390px で左のパネルが詳細パネルの前に出ているときの Esc は、左のパネルを先に閉じ、詳細パネルは開いたままにする。もう一度の Esc で詳細パネルを閉じる（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1"))
    page = open_preview(url, DETAIL_HASH)
    open_narrow(page)
    open_panel(page)
    wait_front(page, name)
    # 実行（1 回目の Esc）
    page.keyboard.press("Escape")
    page.wait_for_selector(selector, state="detached")
    wait_front(page, "detail")
    after_first = {
        "detail_open": page.locator("aside.panel.open").count(),
        "hash": page.evaluate("location.hash"),
    }
    # 実行（2 回目の Esc）
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    # 検証
    assert after_first == {"detail_open": 1, "hash": DETAIL_HASH}
    assert "id=" not in page.evaluate("location.hash")


def test_escape_closes_detail_first_when_wide(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """幅 1200px では、左のパネルを開いていても Esc は今のまま詳細パネルを先に閉じ、左のパネルは開いたままにする（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1"))
    page = open_preview(url, DETAIL_HASH)
    page.set_viewport_size(WIDE_VIEWPORT)
    page.wait_for_selector("aside.panel.open")
    open_settings(page)
    # 実行
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    assert page.locator(SETTINGS_PANEL_OPEN).count() == 1
    assert has_left_front(page) is False


def test_escape_closes_detail_first_when_narrow_and_detail_in_front(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """幅 390px で、左のパネルを開いた後に別の項目へ移って詳細パネルが前に出ているときの Esc は、詳細パネルを先に閉じ、左のパネルは開いたままで見える（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1"), make_item("D-2"))
    page = open_preview(url, DETAIL_HASH)
    open_narrow(page)
    open_settings(page)
    wait_front(page, "settings")
    page.evaluate("location.hash = '#tab=decisions&view=table&id=D-2'")
    wait_front(page, "detail")
    # 実行
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    wait_front(page, "settings")
    assert is_inert(page, "settings") is False
    assert has_left_front(page) is False


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
    page.goto(f"{url}{DIFF_D1_HASH}&diff=since")
    page.reload()
    page.wait_for_selector("aside.panel .df-head")
    assert page.inner_text("aside.panel .df-head-t") == "前回開いてから"
    assert page.inner_text("aside.panel .df-when") == "10/01 21:00 より後"
    # 変わっていない項目（V-2 で足した・変えたものに入らない T-1）には出さない
    page.goto(f"{url}#tab=tasks&view=table&id=T-1&diff=V-2")
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
    assert page.locator("aside.panel .md:not(.md-value) ins.df-blk, aside.panel .md:not(.md-value) del.df-blk").count() == 0
    # 変えただけの項目（V-2 の D-1）には札を置かない
    page.goto(f"{url}{DIFF_D1_HASH}&diff=V-2")
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
    page.wait_for_selector("aside.panel .md:not(.md-value) ins.df-blk")
    # 検証
    added = page.inner_text("aside.panel .md:not(.md-value) ins.df-blk")
    removed = page.inner_text("aside.panel .md:not(.md-value) del.df-blk")
    assert "新しい段落を足しました。" in added
    assert "次の段落を消します。" in removed
    # 足した塊・消した塊の頭に記号と、読み上げの名前がある
    assert page.inner_text("aside.panel .md:not(.md-value) ins.df-blk > .df-sign") == "+"
    assert page.inner_text("aside.panel .md:not(.md-value) del.df-blk > .df-sign") == "−"
    # 表は行ごとに印を付ける
    assert "7" in page.inner_text("aside.panel .md:not(.md-value) tr.df-add")
    assert "3" in page.inner_text("aside.panel .md:not(.md-value) tr.df-del")
    assert page.locator("aside.panel .md:not(.md-value) tr.df-add").count() == 1
    assert page.locator("aside.panel .md:not(.md-value) tr.df-del").count() == 1
    # 変えていない段落は印の外で、今の本文の行（1・14 行目の段落など）を持つ
    unchanged = page.eval_on_selector_all(
        "aside.panel .md:not(.md-value) > p[data-line-start]", "ps => ps.map(p => [p.dataset.lineStart, p.textContent])"
    )
    assert ["3", "最初の段落です。"] in unchanged or ["3", "最初の段落です。"] in [
        [line, text] for line, text in unchanged
    ]
    assert page.locator("aside.panel .md:not(.md-value) del.df-blk [data-line-start]").count() == 0


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


def test_diff_diagram_raw_when_long_line(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """差分の表示の間の図の Raw は、長い行を折り返して横にあふれず、折り返した続きの行は印の列の下へ回り込まない（正常系）。"""
    # 準備
    root = build_long_line_diff_workspace(make_workspace, call_tool, LONG_LINE)
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    _open_diff_panel(page, open_preview, str(served.data["url"]), "V-2")
    page.wait_for_selector("aside.panel figure.diagram.df-changed", timeout=DIFF_DIAGRAM_TIMEOUT_MS)
    # 実行
    page.click('aside.panel figure.diagram [data-act="diagram-raw"]')
    # 検証
    raw = "aside.panel figure.diagram > .dg-raw.df-raw"
    assert page.is_visible(raw)
    assert not overflows_horizontally(page, raw)
    added = page.evaluate(HANGING_LINES_JS, raw)
    assert [line["rows"] > 1 for line in added] == [True]
    assert all(line["clearOfSign"] for line in added)
    assert axe_rule_results(page, raw, SCROLLABLE_REGION_RULE)["violations"] == []


# 差分の表示の本文の領域と、語の面を確かめる検討事項 D-2（行の数が揃わない）・D-3（同じ部分が少ない）を開くハッシュ
DIFF_BODY = "aside.panel .md:not(.md-value)"
DIFF_D2_HASH = "#tab=decisions&view=table&id=D-2"
DIFF_D3_HASH = "#tab=decisions&view=table&id=D-3"

# 語の面を確かめる本文の、書き換えた語（前と今）
WORD_BEFORE = "来週"
WORD_AFTER = "今週"


def test_diff_body_when_inline_words(
    make_workspace: MakeWorkspace, call_tool: CallTool, open_preview: OpenPreview, page: Page
) -> None:
    """変えた行の対は、描いた文字のうち変わった語だけに濃い面を付ける。行の面・記号・取り消し線は残り、変えていない段落と消しただけの段落には付けない（正常系）。"""
    # 準備・実行
    url = serve_word_diff_workspace(make_workspace, call_tool)
    _open_diff_panel(page, open_preview, url, "V-2")
    page.wait_for_selector(f"{DIFF_BODY} span.df-word")
    # 検証（段落: 消した段落・足した段落・消しただけの段落の順）
    blocks = page.evaluate(WORD_MARKS_JS, f"{DIFF_BODY} del.df-blk, {DIFF_BODY} ins.df-blk")
    assert [block["words"] for block in blocks] == [
        [{"kind": "del", "text": WORD_BEFORE}],
        [{"kind": "add", "text": WORD_AFTER}],
        [],
    ]
    # 表の行も、書き換えたセルの語だけ（行の印は語の面に入らない）
    rows = page.evaluate(WORD_MARKS_JS, f"{DIFF_BODY} tr.df-row")
    assert [row["words"] for row in rows] == [
        [{"kind": "del", "text": WORD_BEFORE}],
        [{"kind": "add", "text": WORD_AFTER}],
    ]
    # 変えていない段落には語の面が付かない
    assert page.locator(f"{DIFF_BODY} > p span.df-word").count() == 0
    # 行の面・記号・取り消し線は残る
    for line in ("ins.df-blk:has(span.df-word)", "del.df-blk:has(span.df-word)"):
        assert (
            page.eval_on_selector(f"{DIFF_BODY} {line}", "e => getComputedStyle(e).backgroundColor")
            != TRANSPARENT
        )
    assert page.inner_text(f"{DIFF_BODY} ins.df-blk:has(span.df-word) > .df-sign") == "+"
    assert page.inner_text(f"{DIFF_BODY} del.df-blk:has(span.df-word) > .df-sign") == "−"
    assert (
        page.eval_on_selector(
            f"{DIFF_BODY} del.df-blk:has(span.df-word) > p",
            "e => getComputedStyle(e).textDecorationLine",
        )
        == "line-through"
    )


def test_diff_body_when_inline_words_unpaired(
    make_workspace: MakeWorkspace, call_tool: CallTool, open_preview: OpenPreview, page: Page
) -> None:
    """消した行と足した行の行の数が揃わない書き換えは、語の面を付けず、行の面と記号だけで示す（正常系）。"""
    # 準備・実行
    url = serve_word_diff_workspace(make_workspace, call_tool)
    _open_diff_panel(page, open_preview, url, "V-2", DIFF_D2_HASH)
    page.wait_for_selector(f"{DIFF_BODY} ins.df-blk")
    # 検証
    assert page.locator(f"{DIFF_BODY} del.df-blk").count() == 1
    assert page.locator(f"{DIFF_BODY} ins.df-blk").count() == 1
    assert page.locator(f"{DIFF_BODY} span.df-word").count() == 0


def test_diff_body_when_inline_words_little_same(
    make_workspace: MakeWorkspace, call_tool: CallTool, open_preview: OpenPreview, page: Page
) -> None:
    """行の数が揃っても、同じ部分が少ない（ほとんど書き換えた）対には語の面を付けない（正常系）。"""
    # 準備・実行
    url = serve_word_diff_workspace(make_workspace, call_tool)
    _open_diff_panel(page, open_preview, url, "V-2", DIFF_D3_HASH)
    page.wait_for_selector(f"{DIFF_BODY} ins.df-blk")
    # 検証
    assert page.locator(f"{DIFF_BODY} del.df-blk").count() == 1
    assert page.locator(f"{DIFF_BODY} ins.df-blk").count() == 1
    assert page.locator(f"{DIFF_BODY} span.df-word").count() == 0


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_diff_body_when_inline_words_color(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
    scheme: str,
) -> None:
    """語の面は行の面より濃く（画面の地から離れ）、上に置く文字は面の上で 4.5:1 以上の対比を保つ。ライトとダークの両方で（正常系）。"""
    # 準備
    url = serve_word_diff_workspace(make_workspace, call_tool)
    _open_diff_panel(page, open_preview, url, "V-2")
    page.emulate_media(color_scheme=scheme)
    page.reload()
    page.wait_for_selector(f"{DIFF_BODY} span.df-word")
    assert page.evaluate("document.documentElement.dataset.theme") == scheme
    # 実行
    added = page.evaluate(
        WORD_COLORS_JS, [f"{DIFF_BODY} ins.df-blk span.df-word.df-add", "ins.df-blk"]
    )
    removed = page.evaluate(
        WORD_COLORS_JS, [f"{DIFF_BODY} del.df-blk span.df-word.df-del", "del.df-blk"]
    )
    # 検証
    for colors in (added, removed):
        assert colour_distance(colors["wordBackground"], colors["surface"]) > colour_distance(
            colors["lineBackground"], colors["surface"]
        )
        assert contrast_ratio(colors["text"], colors["wordBackground"]) >= MIN_TEXT_CONTRAST


# キーの語の面を確かめる、背景（`lead`）と案 A の内容の値の要素
DIFF_KEY_LEAD = 'aside.panel [data-key="lead"]'
DIFF_KEY_OPTION = 'aside.panel [data-key="options[A].content"]'


def test_diff_keys_when_inline_words(
    make_workspace: MakeWorkspace, call_tool: CallTool, open_preview: OpenPreview, page: Page
) -> None:
    """背景と案の内容の前の値・今の値は、変わった語だけに濃い面を付ける。値の面・取り消し線・下線・矢印と、読み上げの名前は残る（正常系）。"""
    # 準備・実行
    url = serve_key_word_diff_workspace(make_workspace, call_tool)
    _open_diff_panel(page, open_preview, url, "V-2")
    page.wait_for_selector(f"{DIFF_KEY_LEAD} span.df-word")
    # 検証
    for selector, was, now in (
        (DIFF_KEY_LEAD, "来週", "今週"),
        (DIFF_KEY_OPTION, "毎週", "毎月"),
    ):
        pair = page.locator(f"{selector} .df-kv")
        assert pair.locator("del.df-was span.df-word.df-del").all_inner_texts() == [was]
        assert pair.locator("ins.df-now span.df-word.df-add").all_inner_texts() == [now]
        # 値の面・取り消し線・下線・矢印は残る
        assert page.eval_on_selector(
            f"{selector} del.df-was", "e => getComputedStyle(e).textDecorationLine"
        ) == "line-through"
        assert page.eval_on_selector(
            f"{selector} ins.df-now", "e => getComputedStyle(e).textDecorationLine"
        ) == "underline"
        assert page.eval_on_selector(
            f"{selector} del.df-was", "e => getComputedStyle(e).backgroundColor"
        ) != TRANSPARENT
        assert pair.locator(".df-arrow").inner_text() == "→"
        # 読み上げの名前は語の面の外に残る
        assert pair.locator("del.df-was > .sr-only").text_content() == "前の値: "
        assert pair.locator("ins.df-now > .sr-only").text_content() == "今の値: "


def test_diff_keys_when_inline_words_skipped(
    make_workspace: MakeWorkspace, call_tool: CallTool, open_preview: OpenPreview, page: Page
) -> None:
    """状態・キーの一覧（影響度）・タグには語の面を付けない。前の値・今の値は今までどおり並ぶ（正常系）。"""
    # 準備・実行
    url = serve_key_word_diff_workspace(make_workspace, call_tool)
    _open_diff_panel(page, open_preview, url, "V-2")
    page.wait_for_selector(f"{DIFF_KEY_LEAD} span.df-word")
    # 検証
    # 語の面は背景と案 A の内容の 4 つだけ
    assert page.locator("aside.panel span.df-word").count() == 4
    # 状態（面を塗らない差分）
    status = page.locator('aside.panel [data-key="status"] .df-kv')
    assert status.get_attribute("class") == "df-kv df-plain"
    assert status.locator("del.df-was").inner_text().endswith("未決定")
    assert status.locator("ins.df-now").inner_text().endswith("要見直し")
    assert status.locator("span.df-word").count() == 0
    # キーの一覧（影響度）とタグ
    meta = page.locator("aside.panel .d-meta dd.df-key .df-kv")
    assert meta.count() == 2
    assert meta.locator("span.df-word").count() == 0
    assert meta.nth(0).locator("del.df-was").inner_text().endswith("大")
    assert meta.nth(0).locator("ins.df-now").inner_text().endswith("中")
    assert meta.nth(1).locator("del.df-was").inner_text().endswith("要件、会議")
    assert meta.nth(1).locator("ins.df-now").inner_text().endswith("要件、運用")


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_diff_keys_when_inline_words_color(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
    scheme: str,
) -> None:
    """キーの語の面は値の面より濃く（画面の地から離れ）、上に置く文字は面の上で 4.5:1 以上の対比を保つ。ライトとダークの両方で（正常系）。"""
    # 準備
    url = serve_key_word_diff_workspace(make_workspace, call_tool)
    _open_diff_panel(page, open_preview, url, "V-2")
    page.emulate_media(color_scheme=scheme)
    page.reload()
    page.wait_for_selector(f"{DIFF_KEY_LEAD} span.df-word")
    assert page.evaluate("document.documentElement.dataset.theme") == scheme
    # 実行
    added = page.evaluate(
        WORD_COLORS_JS, [f"{DIFF_KEY_LEAD} ins.df-now span.df-word.df-add", "ins.df-now"]
    )
    removed = page.evaluate(
        WORD_COLORS_JS, [f"{DIFF_KEY_LEAD} del.df-was span.df-word.df-del", "del.df-was"]
    )
    # 検証
    for colors in (added, removed):
        assert colour_distance(colors["wordBackground"], colors["surface"]) > colour_distance(
            colors["lineBackground"], colors["surface"]
        )
        assert contrast_ratio(colors["text"], colors["wordBackground"]) >= MIN_TEXT_CONTRAST


def test_diff_diagram_raw_when_inline_words(
    make_workspace: MakeWorkspace, call_tool: CallTool, open_preview: OpenPreview, page: Page
) -> None:
    """図の Raw の変えた行の対は、変わった語だけに濃い面を付け、ほかの行には付けない（正常系）。"""
    # 準備
    url = serve_word_diff_workspace(make_workspace, call_tool)
    _open_diff_panel(page, open_preview, url, "V-2")
    page.wait_for_selector("aside.panel figure.diagram.df-changed", timeout=DIFF_DIAGRAM_TIMEOUT_MS)
    # 実行
    page.click('aside.panel figure.diagram [data-act="diagram-raw"]')
    lines = page.evaluate(WORD_MARKS_JS, "aside.panel figure.diagram > .dg-raw.df-raw .df-line")
    # 検証
    assert [line["words"] for line in lines if line["words"]] == [
        [{"kind": "del", "text": "仕様"}],
        [{"kind": "add", "text": "設計"}],
    ]


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
    assert page.locator("aside.panel .md:not(.md-value) ins.df-blk, aside.panel .md:not(.md-value) del.df-blk").count() == 0
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
    assert "手で書いた A" in page.inner_text("aside.panel .md:not(.md-value)")
    assert page.locator("aside.panel .md:not(.md-value) ins.df-blk, aside.panel .md:not(.md-value) del.df-blk").count() == 0
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
    assert page.locator("aside.panel .md:not(.md-value) ins.df-blk, aside.panel .md:not(.md-value) del.df-blk").count() == 0
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
    assert page.locator("aside.panel .md:not(.md-value) ins.df-blk, aside.panel .md:not(.md-value) del.df-blk").count() == 0
    assert "最初の段落です。" in page.inner_text("aside.panel .md:not(.md-value)")
    assert page.locator('aside.panel [data-key="status"] .df-kv').count() == 1
    assert page.locator("aside.panel figure.diagram.df-changed").count() == 0


def test_selection_entry_when_diff(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """差分の表示の間も、変えていない文を選べば入口を出し、今の本文の行をコメントに添える。消した部分を含む選択では出さない（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    _open_diff_panel(page, open_preview, url, "V-2")
    page.wait_for_selector("aside.panel .md:not(.md-value) del.df-blk")
    # 実行（変えていない段落を選ぶ）
    page.locator("aside.panel .md:not(.md-value)").scroll_into_view_if_needed()
    select_text_for_pill(page, "aside.panel .md:not(.md-value)", "最初の段落です。")
    page.click(PILL)
    # 検証（今の本文の 3 行目）
    assert page.inner_text("aside.panel .send-loc-name") == "本文 3 行目"
    # 消した部分を含む選択では出さない
    page.keyboard.press("Escape")
    select_text(page, "aside.panel .md:not(.md-value) del.df-blk", "次の段落を消します。")
    page.wait_for_timeout(SELECTION_SETTLE_MS)
    assert page.locator(PILL).count() == 0


def test_selection_entry_when_old_set_after_body_edit(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """古いまとまりを選び、その後に本文を直した項目では、本文の行の印を外し、本文を選んでも入口を出さない（正常系）。"""
    # 準備（D-2 は V-2 の後にも本文を直している）
    url, _ = write_history_preview()
    _open_diff_panel(page, open_preview, url, "V-2", "#tab=decisions&view=table&id=D-2")
    page.wait_for_selector("aside.panel .md:not(.md-value)")
    # 検証
    assert page.locator("aside.panel .md:not(.md-value) [data-line-start]").count() == 0
    select_text(page, "aside.panel .md:not(.md-value)", "1 行目の段落")
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
    page.click("aside.panel .md:not(.md-value) p a:has-text('決め方')")
    page.wait_for_function("new URLSearchParams(location.hash.slice(1)).get('h') === '決め方'")
    # 実行（本文に無い見出しへのリンク）
    hash_before = page.evaluate("location.hash")
    page.click("aside.panel .md:not(.md-value) p a:has-text('無い')")
    page.wait_for_timeout(200)
    # 検証
    assert "h=" in after_hash
    assert page.evaluate("history.length") == history_length
    assert page.evaluate("location.hash") == hash_before
    assert "%E7%84%A1" not in page.evaluate("location.hash")


def test_body_change_set_link_press(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """本文の `[文言](#diff=V-1)` は本文のほかのリンクと同じ見た目で、押すと開いている項目のままそのまとまりの差分の表示に切り替え、ハッシュの diff を履歴に積まずに書く。h は書かない（正常系）。"""
    # 準備
    url = build_body_link_workspace(make_workspace, make_item, call_tool)
    open_preview(url, "#tab=decisions&view=table&id=D-2")
    page.wait_for_selector("aside.panel.open .md a")
    history_length = page.evaluate("history.length")
    style_js = "e => { const s = getComputedStyle(e); return [s.color, s.textDecorationLine, s.cursor]; }"
    change_set_link = page.locator("aside.panel .md a", has_text="V-1 へ")
    heading_link = page.locator("aside.panel .md a", has_text="決め方へ")
    # 実行
    change_set_style = change_set_link.evaluate(style_js)
    heading_style = heading_link.evaluate(style_js)
    change_set_link.click()
    page.wait_for_selector(".df-chip")
    # 検証
    assert change_set_style == heading_style
    assert page.inner_text(".df-chip-t").endswith("D-1 を直す")
    assert page.locator("aside.panel.open").count() == 1
    assert page.evaluate("location.hash").count("diff=V-1") == 1
    assert "h=" not in page.evaluate("location.hash")
    assert "id=D-2" in page.evaluate("location.hash")
    assert page.evaluate("history.length") == history_length


def test_body_term_marks(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """文中の用語だけに印を付け（「保存」に分けず、「AIM」には付けない）、見出しとコードブロックには付けない。印は文字の色を変えず点線の下線で、押すとその用語の詳細へ移り履歴に積む（正常系）。"""
    # 準備
    url = _write_linked_preview(write_preview, make_item)
    page = open_preview(url, "#tab=docs&view=table&id=A-1")
    page.wait_for_selector("aside.panel .md:not(.md-value) a.term")
    history_length = page.evaluate("history.length")
    # 実行
    terms = page.eval_on_selector_all(
        "aside.panel .md:not(.md-value) a.term", "a => a.map(x => [x.textContent, x.dataset.id])"
    )
    in_heading_or_code = page.locator(
        "aside.panel .md:not(.md-value) :is(h2, pre) :is(a.term, a.idref)"
    ).count()
    style = page.eval_on_selector(
        "aside.panel .md:not(.md-value) a.term",
        "e => ({line: getComputedStyle(e).textDecorationLine, style: getComputedStyle(e).textDecorationStyle, color: getComputedStyle(e).color, parent: getComputedStyle(e.parentElement).color})",
    )
    page.click("aside.panel .md:not(.md-value) a.term >> nth=0")
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
    page.wait_for_selector("aside.panel .md:not(.md-value) a.idref")
    history_length = page.evaluate("history.length")
    # 実行
    refs = page.eval_on_selector_all(
        "aside.panel .md:not(.md-value) a.idref", "a => a.map(x => [x.textContent, x.dataset.id])"
    )
    white_space = page.eval_on_selector("aside.panel .md:not(.md-value) a.idref", "e => getComputedStyle(e).whiteSpace")
    in_code_block = page.locator("aside.panel .md:not(.md-value) pre a").count()
    page.click('aside.panel .md:not(.md-value) a.idref[data-id="D-3"]')
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
    mark = "aside.panel .md:not(.md-value) a.term >> nth=0"
    page.wait_for_selector("aside.panel .md:not(.md-value) a.term")
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


# ツールチップの形（役割・種類ごとの見出し・項目のリンクと文・区切り線・置き場所）を読む
READ_TIP_SCRIPT = """() => {
    const tip = document.getElementById('term-tip');
    const line = (element) => element === undefined ? null : getComputedStyle(element).borderTopWidth;
    return {
        role: tip.getAttribute('role'),
        inPanel: tip.closest('aside.panel') !== null,
        kinds: [...tip.querySelectorAll('.tt-kind')].map((e) => e.textContent),
        links: [...tip.querySelectorAll('a.tt-link')].map((a) => [a.dataset.id, a.textContent]),
        bodies: [...tip.querySelectorAll('.tt-item')].map((li) => [
            li.querySelector('a.tt-link').dataset.id,
            li.querySelector('.tt-body')?.textContent ?? null,
        ]),
        groupLine: line(tip.querySelectorAll('.tt-group')[1]),
        itemLine: line(tip.querySelectorAll('.tt-item')[2]),
    };
}"""


def _open_alias_panel(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem, **options: Any
) -> Page:
    """エイリアスを持つ資料・調査・用語と、本文を持つ A-1 を詳細パネルで開き、本文の印が付くのを待つ。"""
    url = write_alias_preview(write_preview, make_item, **options)
    page = open_preview(url, "#tab=docs&view=table&id=A-1")
    page.wait_for_selector(PANEL_MARKS)
    return page


def test_body_alias_marks(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """資料・調査のエイリアスにも用語と同じ印を付け、同じ語の項目を 1 つの印にまとめる。取り下げた資料だけのエイリアスと開いている項目自身のエイリアスには付けない。見出しとコードブロックには付けず、インラインコードは中身がちょうど語のときだけ付ける（正常系）。"""
    # 準備
    page = _open_alias_panel(write_preview, open_preview, make_item)
    history_length = page.evaluate("history.length")
    hash_before = page.evaluate("location.hash")
    # 実行
    marks = page.eval_on_selector_all(PANEL_MARKS, "a => a.map(x => [x.textContent, x.dataset.ids])")
    in_heading_or_block = page.locator(
        "aside.panel .md:not(.md-value) :is(h2, pre) a.term"
    ).count()
    in_code = page.eval_on_selector_all(
        "aside.panel .md:not(.md-value) code a.term", "a => a.map(x => x.textContent)"
    )
    style = page.eval_on_selector(
        PANEL_MARKS,
        "e => ({line: getComputedStyle(e).textDecorationLine, style: getComputedStyle(e).textDecorationStyle, color: getComputedStyle(e).color, parent: getComputedStyle(e.parentElement).color})",
    )
    mixed = f"{PANEL_MARKS} >> nth=0"
    term_only = f"{PANEL_MARKS} >> nth=2"
    mixed_attrs = page.evaluate(
        "s => { const e = document.querySelector(s); return [e.getAttribute('aria-details'), e.getAttribute('aria-describedby')]; }",
        PANEL_MARKS,
    )
    term_attrs = page.eval_on_selector(
        term_only, "e => [e.getAttribute('aria-details'), e.getAttribute('aria-describedby')]"
    )
    # 資料・調査にも一致した印を押しても移らない
    page.click(mixed)
    page.wait_for_timeout(200)
    # 検証
    # 段落の 3 つの印の後に、中身がちょうど語のインラインコードの印が続く
    assert marks == [
        ["特殊効果", MIXED_IDS],
        ["エフェクト", "A-2"],
        ["保存先", "G-2"],
        ["特殊効果", MIXED_IDS],
    ]
    assert in_heading_or_block == 0
    assert in_code == ["特殊効果"]
    assert style["line"] == "underline"
    assert style["style"] == "dotted"
    assert style["color"] == style["parent"]
    assert mixed_attrs == ["term-tip", None]
    assert term_attrs == [None, "term-tip"]
    assert page.evaluate("location.hash") == hash_before
    assert page.evaluate("history.length") == history_length


def test_body_alias_tooltip(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """資料・調査にも一致した印に乗せると、用語 → 資料 → 調査の順に種類ごとの見出し（種類名と件数）と区切り線で分けて並べ、全項目のタイトルを詳細へのリンクにして、資料・調査は説明（無ければ出さない）を添える。用語だけに一致した印は今と同じ形のまま（正常系）。"""
    # 準備
    page = _open_alias_panel(write_preview, open_preview, make_item)
    # 実行（資料・調査にも一致した印）
    page.hover(f"{PANEL_MARKS} >> nth=0")
    page.wait_for_selector(TIP_OPEN)
    mixed = page.evaluate(READ_TIP_SCRIPT)
    # 実行（用語だけに一致した印）
    page.mouse.move(2, 2)
    page.wait_for_function("!document.querySelector('#term-tip:popover-open')")
    page.hover(f"{PANEL_MARKS} >> nth=2")
    page.wait_for_selector(TIP_OPEN)
    term_only = page.evaluate(READ_TIP_SCRIPT)
    # 検証
    assert mixed["role"] is None
    assert mixed["inPanel"] is True
    assert mixed["kinds"] == ["用語 1", "資料 2", "調査 1"]
    assert mixed["links"] == [
        ["G-1", "特殊効果"],
        ["A-2", "特殊効果のスキーマ"],
        ["A-3", "炎ノード"],
        ["R-1", "特殊効果を重ねたときの描画の負荷"],
    ]
    assert mixed["bodies"] == [
        ["G-1", "画面に重ねる演出"],
        ["A-2", "特殊効果の設定ファイルのキーと型"],
        ["A-3", None],
        ["R-1", "ノードを 1〜8 個重ねたときの測り方と結果"],
    ]
    assert mixed["groupLine"] == "1px"
    assert mixed["itemLine"] == "1px"
    assert term_only["role"] == "tooltip"
    assert term_only["links"] == []


def test_body_alias_tooltip_open_link(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """ツールチップの中のタイトルを押すとその項目の詳細へ移り、履歴に積み、ツールチップを閉じる（正常系）。"""
    # 準備
    page = _open_alias_panel(write_preview, open_preview, make_item)
    history_length = page.evaluate("history.length")
    page.hover(f"{PANEL_MARKS} >> nth=0")
    page.wait_for_selector(TIP_OPEN)
    # 実行
    page.click(f'{TIP} a.tt-link[data-id="A-2"]')
    # 検証
    page.wait_for_function("location.hash.includes('id=A-2')")
    page.wait_for_function("!document.querySelector('#term-tip:popover-open')")
    assert page.evaluate("history.length") == history_length + 1
    assert page.inner_text("aside.panel .d-title") == "特殊効果のスキーマ"


def test_body_alias_tooltip_pinned(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """資料・調査にも一致した印を押すとツールチップを出したままにし（印から外れても消えない）、外を押すか Esc で閉じる。ほかの印に乗せても替えない（正常系）。"""
    # 準備
    page = _open_alias_panel(write_preview, open_preview, make_item)
    mixed = f"{PANEL_MARKS} >> nth=0"
    # 実行（押して、印から外して待つ）
    page.click(mixed)
    page.mouse.move(2, 2)
    page.wait_for_timeout(400)
    kept = page.evaluate("document.querySelector('#term-tip').matches(':popover-open')")
    # 実行（ほかの印に乗せても替わらない）
    page.hover(f"{PANEL_MARKS} >> nth=1")
    page.wait_for_timeout(300)
    still = page.evaluate(
        "[...document.querySelectorAll('#term-tip a.tt-link')].map((a) => a.dataset.id).join(' ')"
    )
    # 実行（Esc で閉じる）
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('#term-tip:popover-open')")
    # 実行（もう一度押して、外を押して閉じる）
    page.click(mixed)
    page.wait_for_selector(TIP_OPEN)
    page.click("aside.panel .panel-kind")
    page.wait_for_function("!document.querySelector('#term-tip:popover-open')")
    # 検証
    assert kept is True
    assert still == "G-1 A-2 A-3 R-1"


def test_body_alias_tooltip_keys(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """資料・調査にも一致した印から Tab で中の最初のリンクへ移り、Shift+Tab で印へ戻る。最後のリンクの次の Tab は本文の次の要素へ移し、Esc は印へフォーカスを戻して閉じる（正常系）。"""
    # 準備
    page = _open_alias_panel(write_preview, open_preview, make_item)
    mixed = f"{PANEL_MARKS} >> nth=0"
    page.focus(mixed)
    page.wait_for_selector(TIP_OPEN)
    active = "document.activeElement"
    # 実行（印から最初のリンクへ）
    page.keyboard.press("Tab")
    first = page.evaluate(f"{active}.dataset.id + ':' + {active}.className")
    # 実行（最初のリンクの Shift+Tab で印へ戻る）
    page.keyboard.press("Shift+Tab")
    back = page.evaluate(f"{active}.textContent + ':' + {active}.className")
    # 実行（Esc で閉じて、印へ戻る）
    page.keyboard.press("Tab")
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('#term-tip:popover-open')")
    after_escape = page.evaluate(f"{active}.textContent + ':' + {active}.className")
    # 実行（最後のリンクの次の Tab で、本文の次の要素へ）
    page.evaluate("document.activeElement.blur()")
    page.focus(mixed)
    page.wait_for_selector(TIP_OPEN)
    page.evaluate("[...document.querySelectorAll('#term-tip a.tt-link')].at(-1).focus()")
    page.keyboard.press("Tab")
    after_last = page.evaluate(f"{active}.textContent + ':' + {active}.className")
    # 検証
    assert first == "G-1:tt-link"
    assert back == "特殊効果:term"
    assert after_escape == "特殊効果:term"
    assert after_last == "エフェクト:term"


def _open_term_alias_panel(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> Page:
    """別名を持つ用語と、本文を持つ A-1 を詳細パネルで開き、本文の印が付くのを待つ。"""
    url = write_term_alias_preview(write_preview, make_item)
    page = open_preview(url, "#tab=docs&view=table&id=A-1")
    page.wait_for_selector(PANEL_MARKS)
    return page


def test_body_term_alias_marks(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """用語の別名にもタイトルと同じ印を付け（取り下げた用語の別名にも付け、空白だけの別名には付けない）、同じ用語のタイトルと別名が同じ語なら 1 回だけ数える。用語 1 件だけに一致した印は押すとその用語へ移って履歴に積み、用語 2 件に一致した印は押しても移らない（正常系）。"""
    # 準備
    page = _open_term_alias_panel(write_preview, open_preview, make_item)
    history_length = page.evaluate("history.length")
    hash_before = page.evaluate("location.hash")
    # 実行
    marks = page.eval_on_selector_all(
        PANEL_MARKS,
        "a => a.map(x => [x.textContent, x.dataset.ids, x.getAttribute('aria-describedby'), x.getAttribute('aria-details')])",
    )
    style = page.eval_on_selector(
        PANEL_MARKS,
        "e => ({line: getComputedStyle(e).textDecorationLine, style: getComputedStyle(e).textDecorationStyle, color: getComputedStyle(e).color, parent: getComputedStyle(e.parentElement).color})",
    )
    # 用語 2 件に一致した印を押しても移らない
    page.click(f"{PANEL_MARKS} >> nth=1")
    page.wait_for_timeout(200)
    stayed = (page.evaluate("location.hash"), page.evaluate("history.length"))
    # 用語 1 件だけに一致した印を押すとその用語へ移る
    page.click(f"{PANEL_MARKS} >> nth=0")
    page.wait_for_function("location.hash.includes('id=G-1')")
    # 検証
    assert marks == [
        ["マイグレーション", "G-1", "term-tip", None],
        ["移し替え", SHARED_TERM_IDS, None, "term-tip"],
        ["古い呼び方", "G-3", "term-tip", None],
    ]
    assert style["line"] == "underline"
    assert style["style"] == "dotted"
    assert style["color"] == style["parent"]
    assert stayed == (hash_before, history_length)
    assert page.evaluate("history.length") == history_length + 1


def test_body_term_alias_tooltip(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """用語 2 件に一致した印に乗せると「用語 2」の見出しの下に 2 件を並べ、タイトルを詳細へのリンクにする。別名に一致した用語 1 件だけの印は、用語・ID・意味だけを tooltip の役割で出す（正常系）。"""
    # 準備
    page = _open_term_alias_panel(write_preview, open_preview, make_item)
    # 実行（用語 2 件に一致した印）
    page.hover(f"{PANEL_MARKS} >> nth=1")
    page.wait_for_selector(TIP_OPEN)
    several = page.evaluate(READ_TIP_SCRIPT)
    # 実行（別名に一致した用語 1 件だけの印）
    page.mouse.move(2, 2)
    page.wait_for_function("!document.querySelector('#term-tip:popover-open')")
    page.hover(f"{PANEL_MARKS} >> nth=0")
    page.wait_for_selector(TIP_OPEN)
    single = page.evaluate(
        """() => {
            const tip = document.getElementById('term-tip');
            return {role: tip.getAttribute('role'), head: tip.querySelector('.tt-head').textContent, body: tip.querySelector('.tt-body').textContent, links: tip.querySelectorAll('a.tt-link').length};
        }"""
    )
    # 検証
    assert several["role"] is None
    assert several["inPanel"] is True
    assert several["kinds"] == ["用語 2"]
    assert several["links"] == [["G-1", "移し替え"], ["G-2", "版の更新"]]
    assert several["bodies"] == [["G-1", "記録を今の版に直すこと"], ["G-2", "版を上げること"]]
    assert single == {"role": "tooltip", "head": "移し替えG-1", "body": "記録を今の版に直すこと", "links": 0}


def test_body_term_alias_tooltip_pinned(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """用語 2 件に一致した印を押すとツールチップを出したままにし（印から外れても消えない）、外を押すと閉じる。Tab で中の最初のリンクへ移り、中のタイトルを押すとその用語へ移って履歴に積み、ツールチップを閉じる（正常系）。"""
    # 準備
    page = _open_term_alias_panel(write_preview, open_preview, make_item)
    history_length = page.evaluate("history.length")
    shared = f"{PANEL_MARKS} >> nth=1"
    # 実行（押して、印から外して待つ）
    page.click(shared)
    page.mouse.move(2, 2)
    page.wait_for_timeout(400)
    kept = page.evaluate("document.querySelector('#term-tip').matches(':popover-open')")
    # 実行（外を押して閉じる）
    page.click("aside.panel .panel-kind")
    page.wait_for_function("!document.querySelector('#term-tip:popover-open')")
    # 実行（フォーカスして Tab で中の最初のリンクへ）
    page.focus(shared)
    page.wait_for_selector(TIP_OPEN)
    page.keyboard.press("Tab")
    first = page.evaluate("document.activeElement.dataset.id + ':' + document.activeElement.className")
    # 実行（中のタイトルを押して移る）
    page.click(f'{TIP} a.tt-link[data-id="G-2"]')
    page.wait_for_function("location.hash.includes('id=G-2')")
    page.wait_for_function("!document.querySelector('#term-tip:popover-open')")
    # 検証
    assert kept is True
    assert first == "G-1:tt-link"
    assert page.evaluate("history.length") == history_length + 1
    assert page.inner_text("aside.panel .d-title") == "版の更新"


def test_body_alias_tooltip_placement(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """ツールチップは印の上に 6px 空けて出す（正常系）。"""
    # 準備（印を本文の中ほどに置く本文）
    far_body = "段落\n\n" * 14 + "特殊効果を重ねる\n"
    page = _open_alias_panel(write_preview, open_preview, make_item, body=far_body)
    mark = f"{PANEL_MARKS} >> nth=0"
    page.locator(mark).scroll_into_view_if_needed()
    # 実行（上に出す）
    page.hover(mark)
    page.wait_for_selector(TIP_OPEN)
    page.wait_for_timeout(200)
    above = page.evaluate(
        "() => { const m = document.querySelector('aside.panel .md a.term').getBoundingClientRect(); const t = document.getElementById('term-tip').getBoundingClientRect(); return {gap: Math.round(m.top - t.bottom), fits: t.top >= 8}; }"
    )
    # 検証
    assert above == {"gap": 6, "fits": True}


def test_body_alias_tooltip_scroll(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """項目が多いツールチップは、印の上に収まらないので印の下に出し、最大の高さ 360px で止める。中をスクロールして末尾の調査まで読め、後ろの本文は送らない（正常系）。"""
    # 準備（印が本文の領域の上のほうにあるよう、本文を送っておく）
    body = "特殊効果を重ねる\n\n" + "段落\n\n" * 40
    page = _open_alias_panel(write_preview, open_preview, make_item, extra_docs=8, body=body)
    page.wait_for_selector("aside.panel .md:not(.md-value) p:nth-of-type(41)", state="attached")
    page.evaluate(SCROLL_MARK_NEAR_TOP_JS, MARK_MARGIN_PX)
    before_hover = page.evaluate(MARK_IN_PANEL_BODY_JS)
    # 実行
    page.hover(f"{PANEL_MARKS} >> nth=0")
    page.wait_for_selector(TIP_OPEN)
    page.wait_for_timeout(200)
    before = page.evaluate(
        "() => { const m = document.querySelector('aside.panel .md a.term').getBoundingClientRect(); const t = document.getElementById('term-tip'); const b = t.getBoundingClientRect(); return {gap: Math.round(b.top - m.bottom), height: Math.round(b.height), scrollable: t.scrollHeight > t.clientHeight, overflowY: getComputedStyle(t).overflowY, overscroll: getComputedStyle(t).overscrollBehaviorY}; }"
    )
    box = page.locator(TIP).bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    for _ in range(6):
        page.mouse.wheel(0, 600)
        page.wait_for_timeout(60)
    page.wait_for_timeout(300)
    after = page.evaluate(
        "() => { const t = document.getElementById('term-tip'); const links = [...t.querySelectorAll('a.tt-link')]; const link = links.at(-1).getBoundingClientRect(); const b = t.getBoundingClientRect(); return {id: links.at(-1).dataset.id, inside: link.bottom <= b.bottom + 1 && link.top >= b.top, atEnd: t.scrollTop + t.clientHeight >= t.scrollHeight - 1, bodyTop: document.querySelector('aside.panel .panel-body').scrollTop}; }"
    )
    # 検証
    assert before_hover["inside"] is True
    assert before["gap"] == 6
    assert before["height"] == 360
    assert before["scrollable"] is True
    assert before["overflowY"] == "auto"
    assert before["overscroll"] == "contain"
    assert after == {"id": "R-1", "inside": True, "atEnd": True, "bodyTop": before_hover["scrollTop"]}


def test_detail_description_aliases(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """資料・調査の詳細に、見出し「説明」の節（結論と同じ灰色の面）と見出し「エイリアス」の節（タグ）を決めた位置に出す。説明は Markdown で描いて無害化し、キーの一覧には並べない。値を持たない項目には節を置かない（正常系）。"""
    # 準備
    url = write_preview(
        make_item(
            "A-1",
            description='**強調**の説明 <img src=x onerror="window.__x=1">',
            aliases=["特殊効果", "エフェクト"],
        ),
        make_item("A-2"),
        make_item(
            "R-1",
            question="何を調べたか",
            description="調査の説明",
            conclusion="調べた結論",
            aliases=["効果"],
            angles=["観点 1"],
        ),
        bodies={"A-1.md": "本文の段落\n", "A-2.md": "本文の段落\n"},
    )
    sections = """() => [...document.querySelectorAll('aside.panel .detail > *')]
        .map((e) => e.dataset.key ?? e.querySelector('h3, b')?.textContent ?? '')
        .filter((label) => ['question', '説明', '結論', 'エイリアス', '調査の観点', '本文'].includes(label))"""
    # 実行（資料）
    page = open_preview(url, "#tab=docs&view=table&id=A-1")
    page.wait_for_selector("aside.panel .detail h3")
    docs = page.evaluate(sections)
    described = page.evaluate(
        """() => {
            const section = [...document.querySelectorAll('aside.panel .d-sec')].find((s) => s.querySelector('h3')?.textContent === '説明');
            const style = getComputedStyle(section);
            return {
                strong: section.querySelectorAll('strong').length,
                hijacked: window.__x === undefined,
                keyed: section.querySelector('[data-key="description"]') !== null,
                filled: style.backgroundColor !== 'rgba(0, 0, 0, 0)' && style.borderTopWidth === '1px',
            };
        }"""
    )
    tags = page.eval_on_selector_all(
        "aside.panel .d-sec:has(h3:text-is('エイリアス')) .tag", "t => t.map(x => x.textContent)"
    )
    meta = page.eval_on_selector_all("aside.panel dl.d-meta dt", "t => t.map(x => x.textContent)")
    # 実行（値を持たない資料）
    page.goto(url + "#tab=docs&view=table&id=A-2")
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === 'A-2の題'")
    empty = page.evaluate(sections)
    # 実行（調査）
    page.goto(url + "#tab=research&view=table&id=R-1")
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === 'R-1の題'")
    research = page.evaluate(sections)
    # 検証
    assert docs == ["説明", "エイリアス", "本文"]
    assert described == {"strong": 1, "hijacked": True, "keyed": True, "filled": True}
    assert tags == ["特殊効果", "エフェクト"]
    assert not {"説明", "エイリアス", "description", "aliases"} & set(meta)
    assert empty == ["本文"]
    assert research == ["question", "説明", "結論", "エイリアス", "調査の観点"]


def _open_long_lines(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> Page:
    """長い行を持つコードブロックと、記法に長い行を持つ図を本文に持つ項目を詳細パネルで開く。"""
    url = write_preview(make_item("A-1"), bodies={"A-1.md": LONG_LINES_BODY})
    page = open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel .md:not(.md-value) pre:not(.dg-raw)")
    page.wait_for_selector("aside.panel .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    return page


def test_code_block_when_long_line(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """本文のコードブロックは、長い行を折り返して横にあふれず、axe の `scrollable-region-focusable` に当たらない（正常系）。"""
    # 準備・実行
    page = _open_long_lines(write_preview, open_preview, make_item)
    code = "aside.panel .md:not(.md-value) pre:not(.dg-raw)"
    # 検証
    assert not overflows_horizontally(page, code)
    assert axe_rule_results(page, code, SCROLLABLE_REGION_RULE)["violations"] == []


def test_diagram_raw_when_long_line(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """図の Raw は、記法の長い行を折り返して横にあふれず、axe の `scrollable-region-focusable` に当たらない（正常系）。"""
    # 準備
    page = _open_long_lines(write_preview, open_preview, make_item)
    # 実行
    page.click('aside.panel button[data-act="diagram-raw"]')
    # 検証
    raw = "aside.panel pre.dg-raw"
    assert page.is_visible(raw)
    assert not overflows_horizontally(page, raw)
    assert axe_rule_results(page, raw, SCROLLABLE_REGION_RULE)["violations"] == []


# 取り下げた項目を開くハッシュと、取り下げていない同じ種類の項目を開くハッシュ（種類ごと）
WITHDRAWN_HASHES = [
    pytest.param("#tab=research&id=R-2", "#tab=research&id=R-1", "R-2", id="research"),
    pytest.param("#tab=docs&view=table&id=A-2", "#tab=docs&view=table&id=A-1", "A-2", id="docs"),
    pytest.param("#tab=terms&id=G-2", "#tab=terms&id=G-1", "G-2", id="terms"),
    pytest.param("#tab=notes&id=N-2", "#tab=notes&id=N-1", "N-2", id="notes"),
    pytest.param("#tab=logs&id=L-2", "#tab=logs&id=L-1", "L-2", id="logs"),
]

# 見出しと取り下げた理由の節の並びを読む（題・キーの一覧・節の見出しの順）
PANEL_ORDER_JS = """() => [...document.querySelectorAll('aside.panel .detail > :is(h2.d-title, dl.d-meta, section.d-sec)')]
    .map(e => e.tagName === 'SECTION' ? e.querySelector('h3').textContent : e.className)"""


@pytest.mark.parametrize(("withdrawn_hash", "normal_hash", "item_id"), WITHDRAWN_HASHES)
def test_withdrawn_badge(
    write_removed_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    page: Page,
    withdrawn_hash: str,
    normal_hash: str,
    item_id: str,
) -> None:
    """取り下げた項目は、差分の表示によらず題の右に大きい取り下げの札を置き（題の文字は薄くしない）、キーの一覧には取り下げの値を出さず、「取り下げた理由」の節に理由を出す。取り下げていない項目には出さない（正常系）。"""
    # 準備・実行
    url, _ = write_removed_preview()
    preselect_diff(page, None)
    open_preview(url, withdrawn_hash)
    page.wait_for_selector("aside.panel.open .d-title")
    # 検証
    badge = page.locator(f"aside.panel .d-title {WITHDRAWN_BADGE}.wd-large")
    assert badge.count() == 1
    assert badge.inner_text() == "取り下げ"
    assert page.evaluate(
        "(() => { const t = document.querySelector('aside.panel .d-title'); const r = document.createRange(); r.selectNodeContents(t.firstChild);"
        " return t.querySelector('.wd-badge').getBoundingClientRect().left >= r.getBoundingClientRect().right; })()"
    )
    # キーの一覧に「取り下げ」の行は無く、理由は題・キーの一覧の後の節に出す
    assert "取り下げ" not in page.eval_on_selector_all("aside.panel .d-meta dt", "dts => dts.map(d => d.textContent)")
    order = page.evaluate(PANEL_ORDER_JS)
    assert order.index("取り下げた理由") > order.index("d-meta")
    reason = page.locator('aside.panel section.d-sec:has(> h3:text-is("取り下げた理由")) [data-key="reason"]')
    assert reason.inner_text() == WITHDRAWN_REASONS[item_id]
    # 題の文字の色は、取り下げていない項目と同じ
    withdrawn_color = page.eval_on_selector("aside.panel .d-title", "e => getComputedStyle(e).color")
    # 取り下げていない項目には札も節も出さない
    open_preview(url, normal_hash)
    page.reload()
    page.wait_for_selector("aside.panel.open .d-title")
    assert page.locator(f"aside.panel {WITHDRAWN_BADGE}").count() == 0
    assert page.locator('aside.panel section.d-sec > h3:text-is("取り下げた理由")').count() == 0
    assert page.eval_on_selector("aside.panel .d-title", "e => getComputedStyle(e).color") == withdrawn_color


def test_withdrawn_reason_when_decision_and_task(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """検討事項とタスクの `reason` は、「取り下げた理由」の節ではなく今の節（採用した案と理由・理由）に出し、取り下げの札を置かない（正常系）。"""
    # 準備
    url = write_preview(
        make_item("D-1", status="決定済み", options=ADOPTED_OPTIONS, reason="採用の理由"),
        make_item("T-1", status="中止", reason="タスクの理由"),
    )
    # 実行・検証（検討事項）
    page = open_preview(url, "#tab=decisions&id=D-1")
    page.wait_for_selector("aside.panel.open .d-title")
    headings = page.eval_on_selector_all("aside.panel h3", "hs => hs.map(h => h.textContent)")
    assert "採用した案と理由" in headings
    assert "取り下げた理由" not in headings
    assert page.locator(f"aside.panel {WITHDRAWN_BADGE}").count() == 0
    # 実行・検証（タスク）
    open_preview(url, "#tab=tasks&id=T-1")
    page.reload()
    page.wait_for_selector("aside.panel.open .d-title")
    assert page.locator("aside.panel b", has_text="理由").count() == 1
    assert "タスクの理由" in page.inner_text("aside.panel .panel-body")
    assert page.locator('aside.panel h3:text-is("取り下げた理由")').count() == 0
    assert page.locator(f"aside.panel {WITHDRAWN_BADGE}").count() == 0


def test_diff_withdrawn(
    write_removed_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """選んだ時点で取り下げたときは、「取り下げ」の行に前の値（なし）と今の値（取り下げの札）を並べ、「取り下げた理由」の節にも前の値（なし）と今の値を並べる（正常系）。"""
    # 準備・実行
    url, _ = write_removed_preview()
    _open_diff_panel(page, open_preview, url, "V-1", "#tab=research&id=R-2")
    # 検証
    row = page.locator("aside.panel .d-meta dt.df-key", has_text="取り下げ")
    assert row.count() == 1
    value = page.locator("aside.panel .d-meta dd.df-key .df-kv")
    assert value.locator("del.df-was").inner_text().endswith("（なし）")
    assert value.locator(f"ins.df-now {WITHDRAWN_BADGE}").inner_text() == "取り下げ"
    reason = page.locator('aside.panel [data-key="reason"] .df-kv')
    assert reason.locator("del.df-was").inner_text().endswith("（なし）")
    assert reason.locator("ins.df-now").inner_text().endswith(WITHDRAWN_REASONS["R-2"])
    # 題の右の札は、差分の表示でも同じ
    assert page.locator(f"aside.panel .d-title {WITHDRAWN_BADGE}.wd-large").count() == 1


def test_diff_withdrawn_when_unchanged(
    write_removed_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """取り下げが選んだ時点より前だったときは、「取り下げ」の行を出さず、理由の節に差分を出さず、題の右の札だけを置く（正常系）。"""
    # 準備・実行
    url, _ = write_removed_preview()
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=research&id=R-2")
    page.wait_for_selector("aside.panel.open .d-title")
    # 検証
    assert page.locator(f"aside.panel .d-title {WITHDRAWN_BADGE}.wd-large").count() == 1
    assert page.locator("aside.panel .d-meta dt.df-key").count() == 0
    assert page.locator('aside.panel [data-key="reason"] .df-kv').count() == 0
    assert page.locator('aside.panel [data-key="reason"]').inner_text() == WITHDRAWN_REASONS["R-2"]


# ─── HTML の本文 ───

# HTML の本文（4 行目に選ぶ段落を置く）
HTML_BODY = (
    "<style>p { color: rgb(51, 51, 51); }</style>\n"
    "\n"
    "<h1>画面のモック</h1>\n"
    "<p>言い換えたい文</p>\n"
)

# 本文を描く枠の外の、枠の中の段落
HTML_CODE_FRAME = "aside.panel .md iframe.html-frame"


def test_format_badge(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """資料の見出しに本文の形式の札（HTML / MD）を置き、資料以外には置かない（正常系）。"""
    # 準備
    url = write_preview(
        make_item("A-1", body="A-1.html"),
        make_item("A-2"),
        make_item("D-1"),
        bodies={"A-1.html": HTML_BODY, "A-2.md": "資料の本文\n"},
    )
    # 実行・検証
    page = open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel.open .d-title")
    assert page.inner_text("aside.panel .panel-head .fmt-badge") == "HTML"
    page.evaluate("location.hash = '#tab=docs&id=A-2'")
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === 'A-2の題'")
    assert page.inner_text("aside.panel .panel-head .fmt-badge") == "MD"
    page.evaluate("location.hash = '#tab=decisions&id=D-1'")
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === 'D-1の題'")
    assert page.locator("aside.panel .panel-head .fmt-badge").count() == 0


def test_html_body(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """本文が HTML の資料は、本文を枠で描き、枠の高さを中身に合わせる（正常系）。"""
    # 準備・実行
    url, _ = write_review_preview(make_item("A-1", body="A-1.html"), bodies={"A-1.html": HTML_BODY})
    page = open_preview(url, "#tab=docs&id=A-1")
    wait_frame_rendered(page, BODY_FRAME)
    # 検証
    assert page.locator("aside.panel .md:not(.md-value)").count() == 0
    assert frame_of(page, BODY_FRAME).locator("h1").inner_text() == "画面のモック"
    fit = frame_fit(page, BODY_FRAME)
    assert fit["bottom"] <= fit["height"]
    assert fit["later_height"] == fit["height"]


def test_html_code_block(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """Markdown の本文の中の html のコードブロックを、コードではなく枠で描く（正常系）。"""
    # 準備・実行
    url = write_preview(make_item("A-1"), bodies={"A-1.md": BODY_WITH_HTML_CODE_BLOCK})
    page = open_preview(url, "#tab=docs&id=A-1")
    wait_frame_rendered(page, HTML_CODE_FRAME)
    # 検証
    assert page.get_attribute(HTML_CODE_FRAME, "title") == "html のコードブロック"
    assert page.locator("aside.panel .md pre code").count() == 0
    assert frame_of(page, HTML_CODE_FRAME).locator("p").inner_text() == "枠の中の段落"
    # 前後の Markdown は今までどおり描く
    assert page.locator('aside.panel .md [data-md-level="1"]').all_inner_texts() == ["見出し"]
    assert page.locator("aside.panel .md > p").count() == 2


def test_selection_entry_when_html_body(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """枠の中の文を選ぶと入口を出し、押すと元の HTML の行の箇所を添える。選びを外すと入口を閉じる（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("A-1", body="A-1.html"), bodies={"A-1.html": HTML_BODY})
    page = open_preview(url, "#tab=docs&id=A-1")
    wait_frame_rendered(page, BODY_FRAME)
    # 実行（選ぶ）
    select_in_frame(page, BODY_FRAME, "言い換えたい文", "言い換えたい文")
    page.wait_for_selector(PILL, timeout=UPDATE_TIMEOUT_MS)
    # 実行（選びを外す）
    frame_of(page, BODY_FRAME).evaluate("getSelection().removeAllRanges()")
    page.wait_for_selector(PILL, state="detached", timeout=UPDATE_TIMEOUT_MS)
    # 実行（もう一度選んで押す）
    select_in_frame(page, BODY_FRAME, "言い換えたい文", "言い換えたい文")
    page.wait_for_selector(PILL, timeout=UPDATE_TIMEOUT_MS)
    page.get_by_role("button", name="選んだ箇所にコメント").click()
    # 検証
    assert page.locator(PILL).count() == 0
    assert page.inner_text("aside.panel .send-loc-name") == "本文 4 行目"
    assert page.inner_text("aside.panel .send-quote") == "言い換えたい文"
    assert page.evaluate("document.activeElement.matches('form.send textarea')") is True


def test_highlight_location_when_html_body(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
) -> None:
    """コメントの一覧の行から開くと、枠の中でその行を含む最も内側の要素を示す（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("A-1", body="A-1.html"),
        bodies={"A-1.html": HTML_BODY},
        comments=(
            make_comment(
                "C-1",
                target="A-1",
                body="ここは言い換える",
                loc={"kind": "body", "start": 4, "end": 4, "text": "言い換えたい文"},
            ),
        ),
    )
    page = open_preview(url)
    open_review(page)
    # 実行
    page.click(f"{COMMENTS_PANEL} li[data-comment='C-1'] button.row-target")
    wait_frame_rendered(page, BODY_FRAME)
    page.wait_for_timeout(FRAME_SETTLE_MS)
    # 検証
    hit = frame_of(page, BODY_FRAME).locator("[data-loc-hit]")
    assert hit.count() == 1
    assert hit.inner_text() == "言い換えたい文"
    assert hit.evaluate("e => getComputedStyle(e).backgroundColor") != "rgba(0, 0, 0, 0)"


def test_diff_html_body_when_format_changed(
    make_workspace: MakeWorkspace, call_tool: CallTool, open_preview: OpenPreview, page: Page
) -> None:
    """選んだ時点の本文が Markdown だったときは、描いた結果の印と切り替えを出さず、原文の差分だけを出す（正常系）。"""
    # 準備
    root = make_workspace()
    workspace = str(root)
    item = {
        "title": "画面のモック",
        "kind": "モック",
        "status": "下書き",
        "deliverable": False,
        "body_markdown": "# 画面のモック\n一覧の画面\n",
    }
    assert call_tool("add", workspace=workspace, kind="doc", item=item).is_error is False
    assert call_tool("commit", workspace=workspace, summary="足す").is_error is False
    updated = call_tool("update", workspace=workspace, id="A-1", item={"body_html": HTML_BODY})
    assert updated.is_error is False
    assert call_tool("commit", workspace=workspace, summary="形式を替える").is_error is False
    url = str(call_tool("preview_url", workspace=workspace).data["url"])
    preselect_diff(page, "V-2")
    # 実行
    open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel .df-raw")
    # 検証
    assert page.locator("aside.panel .html-diff-bar").count() == 0
    assert page.locator("aside.panel .html-marked").count() == 0
    assert "# 画面のモック" in page.inner_text("aside.panel .df-raw .df-line.df-del")
    assert "<h1>画面のモック</h1>" in page.inner_text("aside.panel .df-raw")


def test_html_code_block_when_link_pressed(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    link_target: str,
) -> None:
    """html のコードブロックの枠の中のリンクを押すと、枠の中で移らず新しいタブで開く（正常系）。"""
    # 準備
    body = (
        "# 見出し\n\n前の段落\n\n"
        f'```html\n<p><a id="link" href="{link_target}/code">コードブロックのリンク</a></p>\n```\n\n'
        "後の段落\n"
    )
    url = write_preview(make_item("A-1"), bodies={"A-1.md": body})
    page = open_preview(url, "#tab=docs&id=A-1")
    wait_frame_rendered(page, HTML_CODE_FRAME)
    frame = frame_of(page, HTML_CODE_FRAME)
    location = frame_location(frame)
    tabs = opened_tabs(page)
    # 実行
    tab = new_tab_after(page, lambda: frame.click("#link"))
    # 検証
    assert tab.url == f"{link_target}/code"
    assert tab.title() == LINK_PAGE_TITLE
    assert tab.evaluate("window.opener") is None
    assert opened_tabs(page) == tabs + 1
    assert frame_location(frame) == location
    assert frame.locator("#link").inner_text() == "コードブロックのリンク"


def test_html_body_diff_when_link_pressed(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
    link_target: str,
) -> None:
    """HTML の本文の差分の描いた結果の枠の中のリンクを押すと、枠の中で移らず新しいタブで開く（正常系）。"""
    # 準備（2 つ目の段落のリンクの文を書き換える）
    paragraph = f'<p><a id="link" href="{link_target}/diff">{{}}</a></p>\n'
    root = make_workspace()
    workspace = str(root)
    item = {
        "title": "画面のモック",
        "kind": "モック",
        "status": "下書き",
        "deliverable": False,
        "body_html": "<p>1 つ目の段落</p>\n" + paragraph.format("リンクの文"),
    }
    assert call_tool("add", workspace=workspace, kind="doc", item=item).is_error is False
    assert call_tool("commit", workspace=workspace, summary="足す").is_error is False
    updated = call_tool(
        "update",
        workspace=workspace,
        id="A-1",
        item={"body_html": "<p>1 つ目の段落</p>\n" + paragraph.format("書き直したリンクの文")},
    )
    assert updated.is_error is False
    assert call_tool("commit", workspace=workspace, summary="直す").is_error is False
    url = str(call_tool("preview_url", workspace=workspace).data["url"])
    preselect_diff(page, "V-2")
    open_preview(url, "#tab=docs&id=A-1")
    wait_frame_rendered(page, MARKED_FRAME)
    frame = frame_of(page, MARKED_FRAME)
    location = frame_location(frame)
    tabs = opened_tabs(page)
    # 実行
    tab = new_tab_after(page, lambda: frame.click("#link"))
    # 検証
    assert tab.url == f"{link_target}/diff"
    assert tab.title() == LINK_PAGE_TITLE
    assert tab.evaluate("window.opener") is None
    assert opened_tabs(page) == tabs + 1
    assert frame_location(frame) == location
    assert frame.locator("[data-df]").count() >= 1


# 見出しの帯のタイトルを測る横のパネル
HEAD_PANEL = "aside.panel"

# 幅 480px 以下で、種類の名前を見た目から外したときの大きさ（px）
VISUALLY_HIDDEN_SIZE_PX = 1


def _wait_panel_settled(page: Page) -> None:
    """パネルがすべり込んで、窓の右端に着くまで待つ（動きの間は位置が動く）。"""
    page.wait_for_selector("aside.panel.open .d-title")
    page.wait_for_function(
        "Math.abs(document.querySelector('aside.panel').getBoundingClientRect().right - innerWidth) < 1"
    )


@pytest.mark.parametrize(
    ("hash_text", "item", "with_badge"),
    [
        pytest.param("#tab=docs&id=A-1", "A-1", True, id="docs_with_badge"),
        pytest.param("#tab=notes&id=N-1", "N-1", False, id="notes"),
    ],
)
def test_head_title_on_scroll(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    hash_text: str,
    item: str,
    with_badge: bool,
) -> None:
    """本文を送って先頭のタイトルが隠れたときだけ見出しにタイトルを出し、先頭へ戻すと隠す。長いタイトルは 1 行で省略し、ボタンを押し出さない（正常系）。"""
    # 準備
    url = write_preview(
        make_item("A-1", title=HEAD_LONG_TITLE),
        make_item("N-1", title=HEAD_LONG_TITLE, content=LONG_BODY),
        bodies={"A-1.md": LONG_BODY},
    )
    page = open_preview(url, hash_text)
    _wait_panel_settled(page)
    # 実行
    page.wait_for_function(HEAD_TITLE_HIDDEN_JS, arg=HEAD_PANEL, timeout=HEAD_TITLE_TIMEOUT_MS)
    page.evaluate(ANIMATIONS_FINISHED_JS)
    before = page.evaluate(HEAD_METRICS_JS, HEAD_PANEL)
    page.evaluate(SCROLL_BODY_TO_END_JS, HEAD_PANEL)
    page.wait_for_function(HEAD_TITLE_SHOWN_JS, arg=HEAD_PANEL, timeout=HEAD_TITLE_TIMEOUT_MS)
    page.evaluate(ANIMATIONS_FINISHED_JS)
    after = page.evaluate(HEAD_METRICS_JS, HEAD_PANEL)
    page.evaluate(SCROLL_BODY_TO_TOP_JS, HEAD_PANEL)
    page.wait_for_function(HEAD_TITLE_HIDDEN_JS, arg=HEAD_PANEL, timeout=HEAD_TITLE_TIMEOUT_MS)
    back = page.evaluate(HEAD_METRICS_JS, HEAD_PANEL)
    # 検証
    # 本文の先頭のタイトルが見えるうちは出さない。隠していても場所は取り、種類と ID は動かない
    assert (before["shown"], before["visibility"]) == (False, "hidden")
    assert (after["titleLeft"], after["kindRight"]) == (before["titleLeft"], before["kindRight"])
    # 送って隠れると出る。読み上げからは外し、title は全文を持つ
    assert (after["shown"], after["visibility"]) == (True, "visible")
    assert after["text"] == HEAD_LONG_TITLE
    assert (after["titleAttr"], after["ariaHidden"]) == (HEAD_LONG_TITLE, "true")
    # 先頭へ戻すと隠れる
    assert (back["shown"], back["visibility"]) == (False, "hidden")
    # 長いタイトルは 1 行で省略記号付きで切れる
    assert after["text"].startswith(HEAD_TITLE_PREFIX)
    assert (after["truncated"], after["oneLine"]) == (True, True)
    assert (after["textOverflow"], after["whiteSpace"]) == ("ellipsis", "nowrap")
    # 資料は形式の札の右、それ以外は種類と ID の右に並ぶ
    assert after["titleLeft"] >= (after["badgeRight"] if with_badge else after["kindRight"])
    # ボタンは縮まず、タイトルに押し出されず、見出しの中に収まる
    assert after["buttonWidths"] == [HEAD_BUTTON_WIDTH_PX] * len(after["buttonWidths"])
    assert after["titleRight"] <= after["firstButtonLeft"]
    assert after["lastButtonRight"] <= after["headRight"]


@pytest.mark.parametrize(
    ("width", "label_hidden"),
    [
        pytest.param(480, True, id="width_480"),
        pytest.param(481, False, id="width_481"),
    ],
)
def test_head_title_kind_label_when_narrow(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    width: int,
    label_hidden: bool,
) -> None:
    """幅 480px 以下でタイトルを出している間は種類の名前を見た目から外して読み上げには残し、481px 以上では外さない（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1", title=HEAD_LONG_TITLE), bodies={"A-1.md": LONG_BODY})
    page = open_preview(url, "#tab=docs&id=A-1")
    page.set_viewport_size({"width": width, "height": NARROW_HEIGHT})
    _wait_panel_settled(page)
    kind_label = f"{HEAD_PANEL} .panel-kind-label"
    before = page.evaluate("(s) => document.querySelector(s).getBoundingClientRect().width", kind_label)
    # 実行
    page.evaluate(SCROLL_BODY_TO_END_JS, HEAD_PANEL)
    page.wait_for_function(HEAD_TITLE_SHOWN_JS, arg=HEAD_PANEL, timeout=HEAD_TITLE_TIMEOUT_MS)
    after = page.evaluate(
        "(s) => { const e = document.querySelector(s); const b = e.getBoundingClientRect(); return {width: b.width, height: b.height, text: e.textContent}; }",
        kind_label,
    )
    # 検証
    # タイトルを出す前は、どの幅でも種類の名前が見える
    assert before > VISUALLY_HIDDEN_SIZE_PX
    # 読み上げには残す（文字は DOM に残る）
    assert after["text"].strip() == "資料"
    # 480px 以下だけ見た目から外れる
    assert (after["width"] == VISUALLY_HIDDEN_SIZE_PX and after["height"] == VISUALLY_HIDDEN_SIZE_PX) == label_hidden
    # ID は残る
    assert page.inner_text(f"{HEAD_PANEL} .panel-kind .mono") == "A-1"


# タイトルを出した直後（出す指定が付いたそのコマ）の不透明度を返す。出る前は false を返して待たせる
HEAD_TITLE_OPACITY_WHEN_SHOWN_JS = """() => {
    const title = document.querySelector('aside.panel .panel-head .panel-title');
    return title.classList.contains('is-shown') ? getComputedStyle(title).opacity : false;
}"""


@pytest.mark.parametrize(
    ("reduced_motion", "animated"),
    [
        pytest.param("no-preference", ["opacity"], id="no_preference"),
        pytest.param("reduce", [], id="reduce"),
    ],
)
def test_head_title_motion(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    reduced_motion: str,
    animated: list[str],
) -> None:
    """見出しのタイトルは opacity の動きで出し入れし、動きを減らす設定では何も動かさない（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1", title=HEAD_LONG_TITLE), bodies={"A-1.md": LONG_BODY})
    page = open_preview(url, "#tab=docs&id=A-1")
    page.emulate_media(reduced_motion=reduced_motion)
    _wait_panel_settled(page)
    # 実行
    hidden_moving = animated_properties(page, f"{HEAD_PANEL} .panel-title")
    page.evaluate(SCROLL_BODY_TO_END_JS, HEAD_PANEL)
    page.wait_for_function(HEAD_TITLE_SHOWN_JS, arg=HEAD_PANEL, timeout=HEAD_TITLE_TIMEOUT_MS)
    shown_moving = animated_properties(page, f"{HEAD_PANEL} .panel-title")
    # 検証
    # 隠している間も出した後も、動かす対象は opacity だけ（動きを減らす設定では何も動かさない）
    assert hidden_moving == animated
    assert shown_moving == animated


def test_head_title_motion_when_reduced(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """動きを減らす設定では、見出しのタイトルを出す指定が付いた直後から不透明になっている（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1", title=HEAD_LONG_TITLE), bodies={"A-1.md": LONG_BODY})
    page = open_preview(url, "#tab=docs&id=A-1")
    page.emulate_media(reduced_motion="reduce")
    _wait_panel_settled(page)
    # 実行
    page.evaluate(SCROLL_BODY_TO_END_JS, HEAD_PANEL)
    opacity_when_shown = page.wait_for_function(
        HEAD_TITLE_OPACITY_WHEN_SHOWN_JS, timeout=HEAD_TITLE_TIMEOUT_MS
    ).json_value()
    # 検証
    assert opacity_when_shown == "1"


# ─── 差分のミニマップ ───

# ミニマップの帯の太さ（px）
MINIMAP_WIDTH_PX = 20

# 帯の印の無い、上端に近い位置（帯の上端からの距離）と、面を押したまま動かす距離
MINIMAP_EMPTY_AREA_OFFSET_PX = 40
MINIMAP_DRAG_DISTANCE_PX = 100

# 位置の比べで許す差（px）
MINIMAP_TOLERANCE_PX = 2

# 飛んだ箇所の枠が外れるまで待つ上限ミリ秒（枠は 1.6 秒出す）
MINIMAP_HIT_GONE_MS = 4_000


def _open_minimap_panel(
    write_minimap_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> Page:
    """差分の表示で A-1 の詳細パネルを開き、ミニマップの印が置かれるまで待つ。"""
    url, _ = write_minimap_preview()
    return open_minimap(page, open_preview, url, MINIMAP_HASH)


def test_diff_minimap(
    write_minimap_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """帯は本文のスクロール領域の右（スクロールバーの外側）に、本文と同じ高さの太さ 20px の縦の帯として並び、印は本文と同じ上下の順に、足した・消したを形で分けて置く（正常系）。"""
    # 準備・実行
    _open_minimap_panel(write_minimap_preview, open_preview, page)
    metrics = map_metrics(page, PANEL_SCOPE)
    shapes = mark_shapes(page, PANEL_SCOPE)
    toolbar = page.locator(f"{PANEL_SCOPE} .df-map")
    # 検証（本文のスクロールバーの外側に並び、本文には重ならない）
    assert metrics["mapLeft"] >= metrics["bodyRight"] - 1
    assert metrics["mapWidth"] == MINIMAP_WIDTH_PX
    assert metrics["mapHeight"] == pytest.approx(
        page.eval_on_selector(f"{PANEL_SCOPE} .panel-body", "e => e.getBoundingClientRect().height"),
        abs=MINIMAP_TOLERANCE_PX,
    )
    # 検証（読み上げ）
    assert toolbar.get_attribute("role") == "toolbar"
    assert toolbar.get_attribute("aria-orientation") == "vertical"
    assert toolbar.get_attribute("aria-label") == "変わった箇所"
    assert [shape["label"] for shape in shapes] == ["消した箇所（1 / 2）", "足した箇所（2 / 2）"]
    # 検証（印は 1 つのタブの止まりにまとめる）
    assert page.locator(f"{PANEL_SCOPE} .df-map .df-map-m[tabindex='0']").count() == 1
    assert page.locator(f"{PANEL_SCOPE} .df-map .df-map-m[tabindex='-1']").count() == 1
    # 検証（消した・足したは色だけでなく形で分ける。見えている範囲の面は読み上げに出さない）
    assert [shape["kind"] for shape in shapes] == ["df-del", "df-add"]
    assert shapes[0]["border"] != shapes[1]["border"]
    assert page.locator(f"{PANEL_SCOPE} .df-map-view").get_attribute("aria-hidden") == "true"
    # 検証（印は本文と同じ上下の順に、印の最小の長さ 12px 以上で並ぶ）
    assert shapes[0]["top"] < shapes[1]["top"]
    assert all(shape["height"] >= 12 for shape in shapes)


def test_diff_minimap_when_not_shown(
    write_minimap_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """差分の表示でないときと、変わった箇所の印が無いときは、ミニマップを出さない（正常系）。"""
    # 準備
    url, _ = write_minimap_preview()
    page.set_viewport_size(MINIMAP_VIEWPORT)
    # 実行（差分の表示でない）
    open_preview(url, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel.open .md")
    # 検証
    assert page.locator(f"{PANEL_SCOPE} .df-map").count() == 0
    # 実行（変わった箇所の無い A-2 を差分の表示で開く）
    page.goto(f"{url}#tab=docs&id=A-2&diff=V-1")
    page.reload()
    page.wait_for_selector("aside.panel.open .md")
    # 検証
    assert page.locator(f"{PANEL_SCOPE} .df-map").is_visible() is False
    assert page.locator(f"{PANEL_SCOPE} .df-map .df-map-m").count() == 0


def test_diff_minimap_when_not_comparable(
    write_history_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """選んだ時点の前後を組み立てられないときは、変わった箇所の印が無いので、ミニマップを出さない（正常系）。"""
    # 準備（保持する回数 1: D-2 は V-2 の回を持たず、前後を組み立てられない）
    url, _ = write_history_preview(history_limit=1)
    page.set_viewport_size(MINIMAP_VIEWPORT)
    # 実行
    _open_diff_panel(page, open_preview, url, "V-2", "#tab=decisions&view=table&id=D-2")
    # 検証
    assert page.inner_text("aside.panel .df-note") == NOTE_TRIMMED
    assert page.locator(f"{PANEL_SCOPE} .df-map").is_visible() is False
    assert page.locator(f"{PANEL_SCOPE} .df-map .df-map-m").count() == 0


def test_diff_minimap_when_mark_pressed(
    write_minimap_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """印を押すと、その箇所が本文のスクロール領域の見える範囲まで送られて枠で示され、履歴にもハッシュにも触れない（正常系）。"""
    # 準備
    _open_minimap_panel(write_minimap_preview, open_preview, page)
    history_length = page.evaluate("history.length")
    hash_before = page.evaluate("location.hash")
    assert not added_paragraph_in_view(page, PANEL_SCOPE)
    # 実行
    page.locator(f"{PANEL_SCOPE} .df-map .df-map-m").nth(1).click()
    # 検証
    assert scroll_top(page, PANEL_SCOPE) > 0
    assert added_paragraph_in_view(page, PANEL_SCOPE)
    assert page.locator(f"{PANEL_SCOPE} .md ins.df-blk.df-map-hit").count() == 1
    page.wait_for_function(
        "document.querySelectorAll('aside.panel .df-map-hit').length === 0",
        timeout=MINIMAP_HIT_GONE_MS,
    )
    assert page.evaluate("location.hash") == hash_before
    assert page.evaluate("history.length") == history_length


def test_diff_minimap_when_empty_area_pressed(
    write_minimap_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """印の無い所を押すと、押した位置に見えている範囲の面の中央が来るまで本文をすぐ送り、履歴にもハッシュにも触れない（正常系）。"""
    # 準備
    _open_minimap_panel(write_minimap_preview, open_preview, page)
    history_length = page.evaluate("history.length")
    hash_before = page.evaluate("location.hash")
    box = page.locator(f"{PANEL_SCOPE} .df-map").bounding_box()
    assert box is not None
    # 実行（帯の中ほどを押す）
    press_empty_area(page, PANEL_SCOPE, offset_y=box["height"] / 2)
    # 検証（中ほどを押したので、本文の送れる長さの半分まで送る）
    metrics = map_metrics(page, PANEL_SCOPE)
    assert metrics["scrollTop"] == pytest.approx(
        (metrics["scrollHeight"] - metrics["clientHeight"]) / 2, abs=MINIMAP_TOLERANCE_PX
    )
    assert page.evaluate("location.hash") == hash_before
    assert page.evaluate("history.length") == history_length
    # 実行（帯の上端に近い所を押す）
    press_empty_area(page, PANEL_SCOPE, offset_y=MINIMAP_EMPTY_AREA_OFFSET_PX)
    # 検証（先頭の近くまで送る）
    assert map_metrics(page, PANEL_SCOPE)["scrollTop"] < metrics["scrollTop"]


def test_diff_minimap_when_dragged(
    write_minimap_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """見えている範囲の面をマウスで押したまま下へ動かすと、スクロールバーと同じように本文を送り、離した後もその位置に留まり、履歴にもハッシュにも触れない（正常系）。"""
    # 準備
    _open_minimap_panel(write_minimap_preview, open_preview, page)
    history_length = page.evaluate("history.length")
    hash_before = page.evaluate("location.hash")
    before = map_metrics(page, PANEL_SCOPE)
    # 実行
    drag_view(page, PANEL_SCOPE, delta_y=MINIMAP_DRAG_DISTANCE_PX)
    # 検証（動かした長さに当たる本文の長さだけ送る）
    after = map_metrics(page, PANEL_SCOPE)
    assert after["scrollTop"] == pytest.approx(
        MINIMAP_DRAG_DISTANCE_PX / before["mapHeight"] * before["scrollHeight"],
        abs=MINIMAP_TOLERANCE_PX,
    )
    page.wait_for_timeout(300)
    assert map_metrics(page, PANEL_SCOPE)["scrollTop"] == after["scrollTop"]
    # 離した後はドラッグの見た目が残らない
    assert page.locator(f"{PANEL_SCOPE} .df-map.is-dragging").count() == 0
    assert page.evaluate("document.body.classList.contains('df-map-dragging')") is False
    assert page.evaluate("location.hash") == hash_before
    assert page.evaluate("history.length") == history_length
