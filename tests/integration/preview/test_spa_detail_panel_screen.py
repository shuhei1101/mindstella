"""画面設計『詳細パネル.tsx』の結合テスト。"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from playwright.sync_api import Locator, Page, expect
from preview_a11y_checks import axe_rule_results
from preview_body_link_helpers import build_body_link_workspace
from preview_body_scroll_helpers import LONG_LINES_BODY, SCROLLABLE_REGION_RULE
from preview_edit_helpers import edit_edits, edit_items
from preview_embed_helpers import EMBEDDED_BODY, build_embedded_diff_workspace
from preview_fixture_types import WritePreview, WriteReviewPreview, WriteSamplePreview
from preview_spa_helpers import open_spa
from workspace_fixtures import ADOPTED_OPTIONS, RECORD_DIR, CallTool, MakeEdit, MakeItem, MakeWorkspace

# 送る本文のスクロールの位置（px）
SCROLLED_TOP = 600

# 本文の高さの変化でブラウザが補正する位置のずれ（px）
SCROLL_TOLERANCE = 10


def test_draws_body_with_mdmark(page: Page, spa_preview: str) -> None:
    """mdmark で本文を描き、見出しと表と案を出す（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    panel = page.get_by_role("complementary", name="詳細")
    expect(panel.get_by_role("heading", name="決め方")).to_be_visible()
    expect(panel.get_by_role("cell", name="表の行")).to_be_visible()
    expect(panel).to_contain_text("案 A")


def test_edit_stores_pending(page: Page, spa_preview: str) -> None:
    """タイトルを書き換えると保存待ちに溜まる（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    page.get_by_role("button", name="編集する").click()
    title = page.get_by_role("textbox", name="タイトル")
    title.fill("書き換えた題")
    title.blur()
    page.get_by_role("button", name="保存待ち").first.click()
    expect(page.get_by_role("complementary", name="保存待ちの編集")).to_contain_text("書き換えた題")


def test_remove_can_be_cancelled(page: Page, spa_preview: str) -> None:
    """項目の削除を溜め、取り消せる（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&id=D-2")
    page.get_by_role("button", name="編集する").click()
    page.get_by_role("button", name="項目を削除").click()
    cancel = page.get_by_role("button", name="削除を取り消す")
    expect(cancel).to_be_visible()
    cancel.click()
    expect(page.get_by_role("button", name="項目を削除")).to_be_visible()


def test_back_keeps_trail_over_reload(page: Page, spa_preview: str) -> None:
    """見てきた項目の位置は履歴に持つので、再読み込みしても戻る・進むを押せる（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    panel = page.get_by_role("complementary", name="詳細")
    back = panel.get_by_role("button", name="前の項目へ戻る")
    forward = panel.get_by_role("button", name="次の項目へ進む")
    expect(back).to_be_disabled()
    panel.get_by_role("button", name="D-2").click()
    expect(back).to_be_enabled()
    page.reload()
    expect(back).to_be_enabled()
    back.click()
    expect(page).to_have_url(re.compile("id=D-1"))
    expect(back).to_be_disabled()
    expect(forward).to_be_enabled()


def test_back_keeps_trail_over_filter(page: Page, spa_preview: str) -> None:
    """絞り込みを変えても、見てきた項目の位置を保つ（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&view=table&id=D-1")
    panel = page.get_by_role("complementary", name="詳細")
    panel.get_by_role("button", name="D-2").click()
    expect(page).to_have_url(re.compile("id=D-2"))
    page.get_by_role("button", name="状態: 保留 の条件を解除").click()
    expect(panel.get_by_role("button", name="前の項目へ戻る")).to_be_enabled()


def test_restores_body_scroll(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """本文を送った項目を開き直すと、その位置へ戻る（正常系）。"""
    long_body = "\n\n".join(f"段落 {number}" for number in range(200))
    url = write_preview(make_item("D-1", title="長い本文", status="未決定", body="D-1.md"), make_item("D-2", title="別の項目", status="未決定"), bodies={"D-1.md": long_body})
    open_spa(page, url, "?tab=decisions&id=D-1")
    page.get_by_text("段落 199").wait_for()
    page.locator("aside .panel-body").evaluate(f"(element) => {{ element.scrollTop = {SCROLLED_TOP}; }}")
    page.wait_for_function("sessionStorage.getItem('mindmap-body-scroll') !== null")
    page.goto(page.url.replace("id=D-1", "id=D-2"))
    page.get_by_role("complementary", name="詳細").wait_for()
    page.goto(page.url.replace("id=D-2", "id=D-1"))
    page.get_by_text("段落 199").wait_for()
    page.wait_for_function(f"Math.abs(document.querySelector('aside .panel-body').scrollTop - {SCROLLED_TOP}) < {SCROLL_TOLERANCE}")


# ─── 画面設計の要素の確認項目 ───

# 図を描き終わるまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000

# 差分のライブラリ jsdiff を配る URL（これだけ止める）
JSDIFF_URL_PATTERN = "https://cdn.jsdelivr.net/npm/diff@*/**"

# 本文の行の差分を打ち切らせる本文の行数
LARGE_LINE_COUNT = 5000

# 用語・ID のリンク・見出しのリンク・まとまりのリンクを持つ本文
LINKED_BODY = (
    "## 保存先\n\n"
    "保存先と AI と D-3 と D-99 と A-1\n\n"
    "```\n保存先 D-3\n```\n\n"
    "## 決め方\n\n"
    "[決め方](#決め方) と [V-1 へ](#diff=V-1)\n"
)

# HTML の本文
HTML_BODY = "<style>p { color: rgb(51, 51, 51); }</style>\n\n<h1>画面のモック</h1>\n<p>言い換えたい文</p>\n"

# 子 4（#369）でコメントを移すまで出さない要素（読み上げの名前・文言）
COMMENT_ELEMENTS = [
    pytest.param("レビュー中のコメント", id="review_comments"),
    pytest.param("新しい順", id="review_order"),
    pytest.param("選んだ箇所にコメント", id="selection_entry"),
    pytest.param("コメントを修正", id="row_edit"),
    pytest.param("コメントを削除", id="row_remove"),
    pytest.param("元に戻す", id="row_restore"),
    pytest.param("続きを読む", id="row_more"),
]


def _panel(page: Page) -> Locator:
    """詳細パネルを返す。"""
    return page.get_by_role("complementary", name="詳細")


def _linked(page: Page, write_preview: WritePreview, make_item: MakeItem) -> Locator:
    """用語 G-1「保存先」・G-3「AI」、検討事項 D-3 と、リンクを持つ本文の資料 A-1 の詳細パネルを開く。"""
    url = write_preview(
        make_item("A-1"),
        make_item("D-3"),
        make_item("G-1", title="保存先", meaning="記録を置く場所"),
        make_item("G-3", title="AI", meaning="人工知能"),
        bodies={"A-1.md": LINKED_BODY},
    )
    open_spa(page, url, "?tab=docs&id=A-1")
    panel = _panel(page)
    panel.locator("a.term").first.wait_for()
    return panel


def _diff(page: Page, url: str, sel: str, item: str = "D-1", tab: str = "decisions") -> Locator:
    """差分の表示で項目の詳細パネルを開く。"""
    open_spa(page, url, f"?tab={tab}&view=table&id={item}&diff={sel}")
    panel = _panel(page)
    panel.get_by_role("heading", level=2).wait_for()
    return panel


def test_back_forward_label(page: Page, spa_preview: str) -> None:
    """戻る・進むは矢印の印のボタンで、読み上げの名前は「前の項目へ戻る」「次の項目へ進む」（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    panel = _panel(page)
    # 検証
    expect(panel.get_by_role("button", name="前の項目へ戻る")).to_have_text("←")
    expect(panel.get_by_role("button", name="次の項目へ進む")).to_have_text("→")


def test_back_forward_enabled(page: Page, spa_preview: str) -> None:
    """戻る・進むは、その向きに見てきた項目があるときだけ押せる（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    panel = _panel(page)
    expect(panel.get_by_role("button", name="前の項目へ戻る")).to_be_disabled()
    expect(panel.get_by_role("button", name="次の項目へ進む")).to_be_disabled()
    # 実行
    panel.get_by_role("button", name="D-2").click()
    # 検証
    expect(panel.get_by_role("button", name="前の項目へ戻る")).to_be_enabled()
    expect(panel.get_by_role("button", name="次の項目へ進む")).to_be_disabled()


def test_full_label(page: Page, spa_preview: str) -> None:
    """全画面表示のボタンの読み上げの名前は「全画面表示」（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    # 検証
    expect(_panel(page).get_by_role("button", name="全画面表示")).to_be_visible()


def test_options_visible(page: Page, spa_preview: str) -> None:
    """案の節は案を持つ検討事項にだけ出す（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    expect(_panel(page).get_by_role("heading", name="案", exact=True)).to_be_visible()
    # 実行
    open_spa(page, spa_preview, "?tab=tasks&id=T-1")
    # 検証
    expect(_panel(page).get_by_role("heading", name="案", exact=True)).to_have_count(0)


def test_code_block_when_long_line(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """本文のコードブロックは、長い行を折り返さずコードブロックの中だけで横に送り、フォーカスで止まって矢印で送れ、axe の `scrollable-region-focusable` に当たらない（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1"), bodies={"A-1.md": LONG_LINES_BODY})
    open_spa(page, url, "?tab=docs&id=A-1")
    code = _panel(page).locator(".md pre[tabindex='0']").first
    expect(code).to_be_visible()
    white_space = code.evaluate("e => getComputedStyle(e).whiteSpace")
    label = code.get_attribute("aria-label")
    # 実行
    code.focus()
    page.keyboard.press("ArrowRight")
    # 検証
    expect(code).to_be_focused()
    page.wait_for_function("() => document.activeElement.scrollLeft > 0")
    assert white_space == "pre"
    assert label == "コード: text"
    assert code.evaluate("e => e.scrollWidth > e.clientWidth")
    assert axe_rule_results(page, ".md pre[tabindex='0']", SCROLLABLE_REGION_RULE)["violations"] == []


def test_body_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """本文は、項目が Markdown の `body` を持つときに mdmark で描き、HTML の本文では枠で描く（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1"), make_item("A-2", body="A-2.html"), bodies={"A-1.md": "## 見出し\n\n段落\n", "A-2.html": HTML_BODY})
    open_spa(page, url, "?tab=docs&id=A-1")
    expect(_panel(page).locator(".md").get_by_role("heading", name="見出し")).to_be_visible()
    # 実行
    open_spa(page, url, "?tab=docs&id=A-2")
    # 検証
    expect(_panel(page).locator("iframe.html-frame")).to_be_visible()
    expect(_panel(page).locator(".md")).to_have_count(0)


@pytest.mark.parametrize(("name", "title"), [pytest.param("図を拡大表示", "拡大表示", id="zoom"), pytest.param("原文をコピー", "コピー", id="copy")])
def test_diagram_tool_label(page: Page, write_sample_preview: WriteSamplePreview, name: str, title: str) -> None:
    """図の拡大表示・コピーのボタンは、印に `title` の「拡大表示」「コピー」を持つ（正常系）。"""
    # 準備・実行
    open_spa(page, write_sample_preview(), "?tab=decisions&id=D-3")
    _panel(page).locator(".mermaid svg").wait_for(timeout=DIAGRAM_TIMEOUT_MS)
    # 検証
    expect(_panel(page).get_by_role("button", name=name)).to_have_attribute("title", title)


def test_diagram_raw_label(page: Page, write_sample_preview: WriteSamplePreview) -> None:
    """図の Raw のボタンの文言は「Raw」（正常系）。"""
    # 準備・実行
    open_spa(page, write_sample_preview(), "?tab=decisions&id=D-3")
    _panel(page).locator(".mermaid svg").wait_for(timeout=DIAGRAM_TIMEOUT_MS)
    # 検証
    expect(_panel(page).locator("figure.diagram").get_by_role("button", name="Raw")).to_have_text("Raw")


def test_related_visible(page: Page, write_sample_preview: WriteSamplePreview) -> None:
    """関係する項目は、その種類の項目が 1 件以上あるときだけ節を出す（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url, "?tab=decisions&id=D-2")
    expect(_panel(page).get_by_role("heading", name="前提", exact=True)).to_be_visible()
    # 実行
    open_spa(page, url, "?tab=decisions&id=D-1")
    # 検証
    expect(_panel(page).get_by_role("heading", name="前提", exact=True)).to_have_count(0)
    expect(_panel(page).get_by_role("heading", name="後続の項目", exact=True)).to_be_visible()


def test_comment_input_visible(page: Page, spa_preview: str) -> None:
    """サーバーの配信で開いたときは、「今の画面でコメントする」のリンクを出す（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    # 検証
    expect(_panel(page).get_by_role("link", name="今の画面でコメントする")).to_have_attribute("href", re.compile(r"/mindstella\.html#tab=decisions&id=D-1"))


def test_diff_point_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """差分の表示の間、開いた項目が変わったときは選んだ時点の名前を出し、差分の表示でないときは出さない（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions&id=D-1")
    expect(_panel(page)).not_to_contain_text("決める")
    # 実行
    panel = _diff(page, url, "V-2")
    # 検証
    expect(panel).to_contain_text("決める")


def test_new_badge_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """差分の表示の間、開いた項目がその時点で足されたときだけ題の横に新規の札を出す（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    expect(_diff(page, url, "V-2").get_by_role("heading", level=2)).not_to_contain_text("新規")
    # 実行
    panel = _diff(page, url, "V-1")
    # 検証
    expect(panel.get_by_role("heading", level=2)).to_contain_text("新規")


def test_key_diff_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """差分の表示の間、選んだ時点で変わったキーは前の値と今の値を並べる（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    panel = _diff(page, url, "V-2")
    # 検証
    expect(panel.locator("[data-key=answer] del.df-was")).to_contain_text("旧い答え")
    expect(panel.locator("[data-key=answer] ins.df-now")).to_contain_text("新しい答え")


def test_body_diff_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """差分の表示の間、Markdown の本文が変わったときは足した部分と消した部分に印を付ける（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    panel = _diff(page, url, "V-2")
    # 検証
    expect(panel.locator(".md ins.df-blk").first).to_be_visible()


def test_diagram_diff_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """差分の表示の間、図の記法が変わったときは図に差分の色を付ける（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    panel = _diff(page, url, "V-2")
    # 検証
    expect(panel.locator("figure.diagram.df-colored")).to_have_count(1, timeout=DIAGRAM_TIMEOUT_MS)


def test_diagram_raw_diff_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """差分の表示の間、図の Raw を押すと記法の行ごとに足した行と消した行を印つきで出す（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    panel = _diff(page, url, "V-2")
    figure = panel.locator("figure.diagram.df-colored")
    figure.wait_for(timeout=DIAGRAM_TIMEOUT_MS)
    # 実行
    figure.get_by_role("button", name="Raw").click()
    # 検証
    expect(figure.locator(".dg-raw.df-raw ins, .dg-raw.df-raw .df-add").first).to_be_visible()


def test_trimmed_note_label(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """選んだ時点の変更履歴が保持する回数を超えて消えているときは、前後を組み立てられない旨を出す（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview(history_limit=1)
    panel = _diff(page, url, "V-2", item="D-2")
    # 検証
    expect(panel.get_by_role("note")).to_have_text("このまとまりの前後を組み立てられません。保持する回数を超えた古い変更履歴は消えています。今の内容を出しています。")


def test_trimmed_note_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """変更履歴が残っているときは、前後を組み立てられない旨を出さない（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    panel = _diff(page, url, "V-2", item="D-2")
    # 検証
    expect(panel.get_by_text("このまとまりの前後を組み立てられません。")).to_have_count(0)


def test_body_unavailable_label(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """書き換えの後に本文のファイルが直接書き換えられていると、本文の差分を出せない旨を出す（正常系）。"""
    # 準備
    url, root = write_history_preview()
    (root / RECORD_DIR / "docs" / "D-1.md").write_text("手で書いた A\n\n手で書いた B\n", encoding="utf-8")
    # 実行
    panel = _diff(page, url, "V-2")
    # 検証
    expect(panel.get_by_text("本文の差分を出せません。書き換えの後に、本文のファイルが直接書き換えられています。今の本文を出しています。")).to_be_visible()


def test_body_unavailable_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """本文のファイルが記録のとおりなら、本文の差分を出せない旨を出さない（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    panel = _diff(page, url, "V-2")
    panel.locator(".md ins.df-blk").first.wait_for()
    # 検証
    expect(panel.get_by_text("本文の差分を出せません。")).to_have_count(0)


def test_body_too_large_label(page: Page, write_history_preview: WriteReviewPreview, call_tool: CallTool) -> None:
    """本文の行の差分を打ち切ったときは、計算しきれない旨を出す（正常系）。"""
    # 準備（大きな本文をまとめ、全ての行が違う大きな本文へまとめる前に書き換える）
    url, root = write_history_preview()
    before = "".join(f"前の行 {index}\n" for index in range(LARGE_LINE_COUNT))
    after = "".join(f"後の行 {index}\n" for index in range(LARGE_LINE_COUNT))
    assert call_tool("update", workspace=str(root), id="D-1", item={"body_markdown": before, "answer": "大きい前"}).is_error is False
    assert call_tool("commit", workspace=str(root), summary="大きな本文にする").is_error is False
    assert call_tool("update", workspace=str(root), id="D-1", item={"body_markdown": after, "answer": "大きい後"}).is_error is False
    # 実行
    panel = _diff(page, url, "pending")
    # 検証
    expect(panel.get_by_text("本文の差分を出せません。書き換えが大きく、差分を計算しきれませんでした。今の本文を出しています。")).to_be_visible(timeout=DIAGRAM_TIMEOUT_MS)


def test_body_too_large_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """本文の差分を計算しきれたときは、計算しきれない旨を出さない（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    panel = _diff(page, url, "V-2")
    panel.locator(".md ins.df-blk").first.wait_for()
    # 検証
    expect(panel.get_by_text("差分を計算しきれませんでした。")).to_have_count(0)


def test_library_note_label(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """jsdiff を読めないときは、差分のライブラリを読めない旨を出す（異常系）。"""
    # 準備
    url, _ = write_history_preview()
    page.route(JSDIFF_URL_PATTERN, lambda route: route.abort())
    # 実行
    panel = _diff(page, url, "V-2")
    # 検証
    expect(panel.get_by_role("alert").filter(has_text="jsdiff")).to_have_text("本文と図の差分を表示できません。読み込めなかったライブラリ: jsdiff通信を確認して、ページを再読み込みしてください。")


def test_library_note_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """jsdiff を読めたときは、差分のライブラリを読めない旨を出さない（正常系）。"""
    # 準備・実行
    url, _ = write_history_preview()
    panel = _diff(page, url, "V-2")
    panel.locator(".md ins.df-blk").first.wait_for()
    # 検証
    expect(panel.get_by_text("読み込めなかったライブラリ: jsdiff")).to_have_count(0)


@pytest.mark.parametrize("name", COMMENT_ELEMENTS)
def test_comment_elements_hidden(page: Page, served_review_rows: tuple[str, Path], name: str) -> None:
    """レビュー中のコメントと、その並び・行の操作・選んだ箇所の入口・示す箇所は、子 4（#369）で移すまで出さない（正常系）。"""
    # 準備・実行
    url, _ = served_review_rows
    open_spa(page, url, "?tab=decisions&id=D-1")
    # 検証
    expect(_panel(page).get_by_text(name)).to_have_count(0)
    expect(_panel(page).get_by_role("button", name=name)).to_have_count(0)
    expect(_panel(page)).not_to_contain_text("案 A にする")


def test_comment_location_hidden(page: Page, write_commented_preview: WriteReviewPreview) -> None:
    """箇所を指すコメントがあっても、示す箇所を出さない（子 4（#369）で移すまで）（正常系）。"""
    # 準備・実行
    url, _ = write_commented_preview()
    open_spa(page, url, "?tab=decisions&id=D-3")
    # 検証
    expect(_panel(page).locator("mark, .loc-hl")).to_have_count(0)


def test_scroll_region_visible(page: Page, spa_preview: str) -> None:
    """本文のスクロール領域を常に出し、読み上げの名前は「詳細の本文」で、キーボードで送れる（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    region = _panel(page).get_by_role("region", name="詳細の本文")
    # 検証
    expect(region).to_be_visible()
    expect(region).to_have_attribute("tabindex", "0")


def test_heading_link_label(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """見出しのリンクは「#」の印で、読み上げの名前は「見出し「{見出し}」へのリンク」（正常系）。"""
    # 準備・実行
    panel = _linked(page, write_preview, make_item)
    link = panel.get_by_role("link", name="見出し「保存先」へのリンク")
    # 検証
    expect(link.locator("svg")).to_have_count(1)


def test_heading_link_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """見出しの無い本文には、見出しのリンクを置かない（正常系）。"""
    # 準備・実行
    url = write_preview(make_item("A-1"), bodies={"A-1.md": "見出しの無い段落\n"})
    open_spa(page, url, "?tab=docs&id=A-1")
    _panel(page).locator(".md p").wait_for()
    # 検証
    expect(_panel(page).get_by_role("link", name=re.compile("^見出し「"))).to_have_count(0)


def test_term_mark_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """本文の文中に用語のタイトルが出てくるときだけ印を付け、コードブロックの中には付けない（正常系）。"""
    # 準備・実行
    panel = _linked(page, write_preview, make_item)
    # 検証
    assert panel.locator(".md a.term").evaluate_all("marks => marks.map((m) => m.textContent)") == ["保存先", "AI"]
    expect(panel.locator(".md pre a.term")).to_have_count(0)


def test_term_tip_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """本文の印に乗せている間だけツールチップを出す（正常系）。"""
    # 準備
    panel = _linked(page, write_preview, make_item)
    tip = page.locator("[popover]:popover-open")
    expect(tip).to_have_count(0)
    # 実行
    panel.locator(".md a.term").first.hover()
    # 検証
    expect(tip).to_contain_text("記録を置く場所")


def test_id_link_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """本文に記録にある項目の ID が出てくるときだけリンクにし、記録に無い ID・開いている項目自身はリンクにしない（正常系）。"""
    # 準備・実行
    panel = _linked(page, write_preview, make_item)
    # 検証
    assert panel.locator(".md a.idref").evaluate_all("links => links.map((a) => a.dataset.id)") == ["D-3"]


def test_lead_visible(page: Page, write_sample_preview: WriteSamplePreview) -> None:
    """背景は `lead` を持つ検討事項にだけ出す（正常系）。"""
    # 準備
    url = write_sample_preview()
    open_spa(page, url, "?tab=decisions&id=D-2")
    expect(_panel(page).locator("[data-key=lead]")).to_contain_text("キーをどう持つか")
    # 実行
    open_spa(page, url, "?tab=decisions&id=D-4")
    # 検証
    expect(_panel(page).locator("[data-key=lead]")).to_have_count(0)


def test_recommended_label(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """推奨の印の文言は「推奨」（正常系）。"""
    # 準備・実行
    url = write_preview(make_item("D-1", status="未決定", options=[{"key": "A", "content": "案 A"}, {"key": "B", "content": "案 B", "recommended": True}]))
    open_spa(page, url, "?tab=decisions&id=D-1")
    # 検証
    expect(_panel(page).get_by_text("推奨", exact=True)).to_have_count(1)


def test_recommended_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """採用した案があるときは、推奨の印を出さない（正常系）。"""
    # 準備・実行
    url = write_preview(make_item("D-1", status="決定済み", options=[{"key": "A", "content": "案 A", "adopted": True}, {"key": "B", "content": "案 B", "recommended": True}]))
    open_spa(page, url, "?tab=decisions&id=D-1")
    # 検証
    expect(_panel(page).get_by_text("推奨", exact=True)).to_have_count(0)


def test_adopted_label(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """採用した案と理由の節の見出しは「採用した案と理由」（正常系）。"""
    # 準備・実行
    url = write_preview(make_item("D-1", status="決定済み", answer="種類ごとに分ける", reason="探しやすい", options=ADOPTED_OPTIONS))
    open_spa(page, url, "?tab=decisions&id=D-1")
    # 検証
    expect(_panel(page).get_by_role("heading", name="採用した案と理由")).to_be_visible()


def test_adopted_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """`answer`・`reason` のどちらも持たない検討事項には、採用した案と理由の節を置かない（正常系）。"""
    # 準備・実行
    url = write_preview(make_item("D-1", status="未決定"))
    open_spa(page, url, "?tab=decisions&id=D-1")
    # 検証
    expect(_panel(page).get_by_role("heading", name="採用した案と理由")).to_have_count(0)


def test_value_text_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """文字列の値は、項目がその値を持つときに mdmark で描き、段落の中の改行も改行として出す（正常系）。"""
    # 準備・実行
    url = write_preview(make_item("D-1", status="決定済み", answer="**強調**の答え\n2 行目", options=ADOPTED_OPTIONS))
    open_spa(page, url, "?tab=decisions&id=D-1")
    answer = _panel(page).locator("[data-key=answer]")
    # 検証
    expect(answer.locator("strong")).to_have_text("強調")
    expect(answer.locator("br")).to_have_count(1)


def test_withdrawn_badge_visible(page: Page, write_removed_preview: WriteReviewPreview) -> None:
    """取り下げた項目は、差分の表示によらず題の右に取り下げの札を置く（正常系）。"""
    # 準備
    url, _ = write_removed_preview()
    open_spa(page, url, "?tab=docs&id=A-2")
    expect(_panel(page).get_by_role("heading", level=2)).to_contain_text("取り下げ")
    # 実行
    open_spa(page, url, "?tab=docs&id=A-1")
    # 検証
    expect(_panel(page).get_by_role("heading", level=2)).not_to_contain_text("取り下げ")


def test_withdrawn_reason_label(page: Page, write_removed_preview: WriteReviewPreview) -> None:
    """取り下げた理由の節の見出しは「取り下げた理由」で、理由を出す（正常系）。"""
    # 準備・実行
    url, _ = write_removed_preview()
    open_spa(page, url, "?tab=docs&id=A-2")
    reason = _panel(page).locator("[data-key=reason]")
    # 検証
    expect(reason).to_contain_text("取り下げた理由")
    expect(reason).to_contain_text("別の資料に統合した")


def test_withdrawn_reason_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """検討事項とタスクの `reason` は、取り下げた理由の節に出さない（正常系）。"""
    # 準備・実行
    url = write_preview(make_item("T-1", status="中止", reason="タスクの理由"))
    open_spa(page, url, "?tab=tasks&id=T-1")
    # 検証
    expect(_panel(page)).to_contain_text("タスクの理由")
    expect(_panel(page).get_by_text("取り下げた理由")).to_have_count(0)


def test_format_badge_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """資料の見出しにだけ本文の形式の札を置く（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1", body="A-1.html"), make_item("D-1"), bodies={"A-1.html": HTML_BODY})
    open_spa(page, url, "?tab=docs&id=A-1")
    expect(_panel(page).get_by_text("HTML", exact=True)).to_be_visible()
    # 実行
    open_spa(page, url, "?tab=decisions&id=D-1")
    # 検証
    expect(_panel(page).get_by_text("MD", exact=True)).to_have_count(0)
    expect(_panel(page).get_by_text("HTML", exact=True)).to_have_count(0)


def test_html_body_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """資料の `body` が `.html` で終わるときは、本文を枠で描く（正常系）。"""
    # 準備・実行
    url = write_preview(make_item("A-1", body="A-1.html"), bodies={"A-1.html": HTML_BODY})
    open_spa(page, url, "?tab=docs&id=A-1")
    frame = _panel(page).frame_locator("iframe.html-frame")
    # 検証
    expect(frame.locator("h1")).to_have_text("画面のモック")


def test_html_body_action(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """HTML の本文の中の外のページへのリンクは、枠の中では移らず新しいタブで開く（正常系）。"""
    # 準備
    body = '<p><a id="out" href="https://example.com/">外のページ</a></p>\n'
    url = write_preview(make_item("A-1", body="A-1.html"), bodies={"A-1.html": body})
    open_spa(page, url, "?tab=docs&id=A-1")
    frame = _panel(page).frame_locator("iframe.html-frame")
    page.context.route("https://example.com/**", lambda route: route.fulfill(status=200, body="ok"))
    # 実行
    with page.context.expect_page() as opened:
        frame.locator("#out").click()
    # 検証
    assert opened.value.url == "https://example.com/"
    expect(frame.locator("#out")).to_be_visible()


def test_html_code_block_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """Markdown の本文の `html` のコードブロックは、コードではなく枠で描く（正常系）。"""
    # 準備・実行
    url = write_preview(make_item("A-1"), bodies={"A-1.md": "前の段落\n\n```html\n<p>枠の中の段落</p>\n```\n"})
    open_spa(page, url, "?tab=docs&id=A-1")
    # 検証
    expect(_panel(page).frame_locator(".md iframe.html-frame").locator("p")).to_have_text("枠の中の段落")


def test_html_code_block_action(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """`html` のコードブロックの枠の中の相対の URL のリンクは、押しても移らない（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1"), bodies={"A-1.md": '```html\n<p><a id="rel" href="other.html">相対</a></p>\n```\n'})
    open_spa(page, url, "?tab=docs&id=A-1")
    frame = _panel(page).frame_locator(".md iframe.html-frame")
    before = page.url
    # 実行
    frame.locator("#rel").click()
    page.wait_for_timeout(300)
    # 検証
    assert page.url == before
    expect(frame.locator("#rel")).to_be_visible()


def test_html_body_diff_visible(page: Page, write_html_body_layout_preview: WriteReviewPreview) -> None:
    """差分の表示の間で HTML の本文が変わったときは、HTML の本文の差分を出す（正常系）。"""
    # 準備・実行
    url, _ = write_html_body_layout_preview()
    panel = _diff(page, url, "V-2", item="A-1", tab="docs")
    # 検証
    expect(panel.get_by_role("group", name="本文の差分の見せ方")).to_be_visible()


def test_html_body_diff_action(page: Page, write_html_body_layout_preview: WriteReviewPreview) -> None:
    """HTML の本文の差分の描いた結果の枠の中のリンク以外の文も、本文と同じ枠で描く（正常系）。"""
    # 準備・実行
    url, _ = write_html_body_layout_preview()
    panel = _diff(page, url, "V-2", item="A-1", tab="docs")
    # 検証
    expect(panel.frame_locator(".html-marked iframe").locator("[data-df]").first).to_be_attached()


def test_description_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """説明の節は `description` を持つ資料・調査にだけ出す（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1", description="資料の説明"), make_item("A-2"), bodies={"A-1.md": "本文\n", "A-2.md": "本文\n"})
    open_spa(page, url, "?tab=docs&id=A-1")
    expect(_panel(page).locator("[data-key=description]")).to_contain_text("資料の説明")
    # 実行
    open_spa(page, url, "?tab=docs&id=A-2")
    # 検証
    expect(_panel(page).locator("[data-key=description]")).to_have_count(0)


def test_aliases_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """エイリアスの節は `aliases` を持つ資料・調査にだけ出す（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1", aliases=["特殊効果"]), make_item("A-2"), bodies={"A-1.md": "本文\n", "A-2.md": "本文\n"})
    open_spa(page, url, "?tab=docs&id=A-1")
    expect(_panel(page).get_by_role("heading", name="エイリアス")).to_be_visible()
    # 実行
    open_spa(page, url, "?tab=docs&id=A-2")
    # 検証
    expect(_panel(page).get_by_role("heading", name="エイリアス")).to_have_count(0)


def test_kind_and_id_visible(page: Page, spa_preview: str) -> None:
    """種類と ID を見出しに常に出す（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=tasks&id=T-1")
    # 検証
    expect(_panel(page).get_by_text("タスク", exact=True).first).to_be_visible()
    expect(_panel(page).get_by_text("T-1", exact=True).first).to_be_visible()


def test_head_title_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """見出しのタイトルは本文の先頭のタイトルが外れている間だけ出す（正常系）。"""
    # 準備
    long_body = "\n\n".join(f"{number} 番目の段落" for number in range(1, 121)) + "\n"
    url = write_preview(make_item("A-1", title="長い本文の資料"), bodies={"A-1.md": long_body})
    open_spa(page, url, "?tab=docs&id=A-1")
    head = _panel(page).locator("span[aria-hidden=true][title='長い本文の資料']")
    expect(head).to_have_css("opacity", "0")
    _panel(page).get_by_text("120 番目の段落").wait_for(state="attached")
    # 実行
    _panel(page).get_by_role("region", name="詳細の本文").evaluate("e => { e.scrollTop = e.scrollHeight; }")
    # 検証
    expect(head).to_have_css("opacity", "1")


def test_change_set_link_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """本文に `#diff=` のリンクがあるときは、まとまりのリンクとして出す（正常系）。"""
    # 準備・実行
    panel = _linked(page, write_preview, make_item)
    # 検証
    expect(panel.locator(".md a", has_text="V-1 へ")).to_have_attribute("href", "#diff=V-1")


def test_change_set_link_action(page: Page, make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool) -> None:
    """まとまりのリンクを押すと、開いている項目のままそのまとまりの差分の表示に切り替え、URL の `diff` を書き換える（正常系）。"""
    # 準備
    url = build_body_link_workspace(make_workspace, make_item, call_tool)
    open_spa(page, url, "?tab=decisions&view=table&id=D-2")
    link = _panel(page).locator(".md a", has_text="V-1 へ")
    # 実行
    link.click()
    # 検証
    expect(page).to_have_url(re.compile("diff=V-1"))
    expect(page).to_have_url(re.compile("id=D-2"))


def test_minimap_visible(page: Page, write_minimap_preview: WriteReviewPreview) -> None:
    """差分の表示の間で本文に変わった箇所があるときは、差分のミニマップを出し、差分の表示でないときは出さない（正常系）。"""
    # 準備
    url, _ = write_minimap_preview()
    open_spa(page, url, "?tab=docs&id=A-1")
    expect(_panel(page).get_by_role("toolbar", name="変わった箇所")).to_have_count(0)
    # 実行
    panel = _diff(page, url, "V-1", item="A-1", tab="docs")
    # 検証
    expect(panel.get_by_role("toolbar", name="変わった箇所")).to_be_visible()


def test_layout_switch_visible(page: Page, write_body_layout_preview: WriteReviewPreview) -> None:
    """差分の表示の間で本文が変わったときは、本文の差分の並べ方の切り替えを出し、差分の表示でないときは出さない（正常系）。"""
    # 準備
    url, _ = write_body_layout_preview()
    open_spa(page, url, "?tab=docs&id=A-1")
    expect(_panel(page).get_by_role("group", name="本文の差分の並べ方")).to_have_count(0)
    # 実行
    panel = _diff(page, url, "V-2", item="A-1", tab="docs")
    # 検証
    expect(panel.get_by_role("group", name="本文の差分の並べ方")).to_be_visible()


def test_side_by_side_visible(page: Page, write_body_layout_preview: WriteReviewPreview) -> None:
    """並べ方を「左右に並べる」にすると、左に選んだ時点・右に今の本文を並べる（正常系）。"""
    # 準備
    url, _ = write_body_layout_preview()
    panel = _diff(page, url, "V-2", item="A-1", tab="docs")
    # 実行
    panel.get_by_role("button", name="左右に並べる").click()
    # 検証
    expect(panel.get_by_role("region", name="選んだ時点の本文")).to_be_visible()
    expect(panel.get_by_role("region", name="今の本文")).to_be_visible()


def test_edit_label(page: Page, spa_preview: str) -> None:
    """編集するのボタンの文言は「編集する」で、編集の表示の間は「編集を終える」（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    button = _panel(page).get_by_role("button", name="編集する")
    expect(button).to_have_text("編集する")
    # 実行
    button.click()
    # 検証
    expect(_panel(page).get_by_role("button", name="編集を終える")).to_have_text("編集を終える")


def test_edit_visible(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """編集するは差分の表示をしていないときだけ出す（正常系）。"""
    # 準備
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions&id=D-1")
    expect(_panel(page).get_by_role("button", name="編集する")).to_be_visible()
    # 実行
    panel = _diff(page, url, "V-2")
    # 検証
    expect(panel.get_by_role("button", name="編集する")).to_have_count(0)


def test_head_pending_mark_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """保存待ちの編集がある項目の見出しにだけ、保存待ちの印を出す（正常系）。"""
    # 準備
    url, _ = write_edit_preview(*edit_items(make_item, "D"), make_item("D-4"), edits=edit_edits(make_edit, "D"))
    open_spa(page, url, "?tab=decisions&id=D-1")
    expect(_panel(page).locator("[title=保存待ち]").first).to_be_visible()
    # 実行
    open_spa(page, url, "?tab=decisions&id=D-4")
    # 検証
    expect(_panel(page).locator("[title^=保存]")).to_have_count(0)


def test_key_pending_mark_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """保存待ちの編集があるキーの名前の右にだけ、保存待ちの印を出す（正常系）。"""
    # 準備・実行
    url, _ = write_edit_preview(*edit_items(make_item, "D"), edits=edit_edits(make_edit, "D"))
    open_spa(page, url, "?tab=decisions&id=D-1")
    _panel(page).get_by_role("button", name="編集する").click()
    form = page.get_by_role("form", name="D-1 を編集")
    # 検証
    expect(form.locator("label", has_text="タイトル").locator("xpath=..").locator("[title=保存待ち]")).to_have_count(1)
    expect(form.locator("label", has_text="状態").locator("xpath=..").locator("[title^=保存]")).to_have_count(0)


def test_edit_view_visible(page: Page, spa_preview: str) -> None:
    """編集の表示は「編集する」を押した間だけ出す（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    expect(page.get_by_role("form", name="D-1 を編集")).to_have_count(0)
    # 実行
    _panel(page).get_by_role("button", name="編集する").click()
    # 検証
    expect(page.get_by_role("form", name="D-1 を編集")).to_be_visible()


def test_title_input_label(page: Page, spa_preview: str) -> None:
    """タイトルの入力の名前は「タイトル」（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    _panel(page).get_by_role("button", name="編集する").click()
    # 検証
    expect(page.get_by_role("form", name="D-1 を編集").get_by_role("textbox", name="タイトル")).to_have_value("記録の形")


def test_option_inputs_visible(page: Page, spa_preview: str) -> None:
    """案の入力は検討事項の編集の表示にだけ出す（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    _panel(page).get_by_role("button", name="編集する").click()
    expect(page.get_by_role("textbox", name="案 A の中身")).to_be_visible()
    # 実行
    open_spa(page, spa_preview, "?tab=tasks&id=T-1")
    _panel(page).get_by_role("button", name="編集する").click()
    # 検証
    expect(page.get_by_role("textbox", name=re.compile("^案 .* の中身$"))).to_have_count(0)


def test_remove_label(page: Page, spa_preview: str) -> None:
    """項目を削除の文言は「項目を削除」で、溜めた後は「削除を取り消す」（正常系）。"""
    # 準備
    open_spa(page, spa_preview, "?tab=decisions&id=D-2")
    _panel(page).get_by_role("button", name="編集する").click()
    expect(page.get_by_role("button", name="項目を削除")).to_have_text(re.compile("項目を削除"))
    # 実行
    page.get_by_role("button", name="項目を削除").click()
    # 検証
    expect(page.get_by_role("button", name="削除を取り消す")).to_have_text(re.compile("削除を取り消す"))


def test_remove_visible(page: Page, spa_preview: str) -> None:
    """項目を削除は、追加の入力では出さない（正常系）。"""
    # 準備・実行
    open_spa(page, spa_preview, "?tab=tasks")
    page.get_by_role("button", name="タスクの項目を追加").click()
    # 検証
    expect(page.get_by_role("complementary", name="タスクを追加").get_by_role("button", name="項目を削除")).to_have_count(0)


def test_blocked_reason_visible(page: Page, write_edit_preview: WriteReviewPreview, make_item: MakeItem, make_edit: MakeEdit) -> None:
    """直前の保存が 409 でその項目の編集が書き込めなかったときだけ、書き込めない理由を出す（異常系）。"""
    # 準備
    url, _ = write_edit_preview(*edit_items(make_item, "D"), edits=edit_edits(make_edit, "D"))
    open_spa(page, url, "?tab=decisions&id=D-3&panel=pending")
    panel = page.get_by_role("complementary", name="保存待ちの編集")
    edit_id = panel.locator("li[id^='pe-row-']").last.get_attribute("id")
    assert edit_id is not None
    blocked = '{"type":"about:blank","title":"Conflict","status":409,"detail":"書き込めません","blocked":[{"id":"%s","reason":"invalid","detail":"書き込めない理由の文","refs":[]}]}'
    page.route("**/api/edits/save", lambda route: route.fulfill(status=409, content_type="application/problem+json", body=blocked % edit_id.removeprefix("pe-row-")))
    # 実行
    panel.get_by_role("button", name="まとめて保存する").click()
    panel.get_by_role("alert").wait_for()
    page.keyboard.press("Escape")
    _panel(page).get_by_role("button", name="編集する").click()
    # 検証
    expect(page.get_by_role("form", name="D-3 を編集")).to_contain_text("書き込めない理由の文")


def test_resizer_visible(page: Page, spa_preview: str) -> None:
    """幅の区切りは表示の幅が 901px 以上のときだけ出す（正常系）。"""
    # 準備
    page.set_viewport_size({"width": 1280, "height": 800})
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    expect(page.get_by_role("separator", name="詳細パネルの幅")).to_be_visible()
    # 実行
    page.set_viewport_size({"width": 900, "height": 800})
    # 検証
    expect(page.get_by_role("separator", name="詳細パネルの幅")).to_be_hidden()


def test_resizer_initial_value(page: Page, spa_preview: str) -> None:
    """幅の区切りは、そのタブに残した幅が無ければ既定の 640 で開き、残した幅があればその幅で開く（正常系）。"""
    # 準備
    page.set_viewport_size({"width": 1440, "height": 800})
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    separator = page.get_by_role("separator", name="詳細パネルの幅")
    expect(separator).to_have_attribute("aria-valuenow", "640")
    # 実行
    page.evaluate("sessionStorage.setItem('mindmap-panel-width', '700')")
    page.reload()
    # 検証
    expect(separator).to_have_attribute("aria-valuenow", "700")


def test_resizer_action(page: Page, spa_preview: str) -> None:
    """幅の区切りにフォーカスして ← で広げ、→ で狭め、変えた幅をそのタブに残す（正常系）。"""
    # 準備
    page.set_viewport_size({"width": 1440, "height": 800})
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    separator = page.get_by_role("separator", name="詳細パネルの幅")
    separator.focus()
    # 実行
    page.keyboard.press("ArrowLeft")
    wider = int(separator.get_attribute("aria-valuenow") or "0")
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowRight")
    # 検証
    assert wider > 640
    assert int(separator.get_attribute("aria-valuenow") or "0") < 640
    assert page.evaluate("sessionStorage.getItem('mindmap-panel-width')") == separator.get_attribute("aria-valuenow")


def test_export_label(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """エクスポートのボタンの読み上げの名前は「エクスポート」（正常系）。"""
    # 準備・実行
    url = write_preview(make_item("A-1"), bodies={"A-1.md": "本文\n"})
    open_spa(page, url, "?tab=docs&id=A-1")
    # 検証
    expect(_panel(page).get_by_role("button", name="エクスポート", exact=True)).to_be_visible()


def test_export_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """エクスポートは本文が Markdown の資料にだけ置き、HTML の資料・資料以外・編集の表示の間は置かない（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1"), make_item("A-2", body="A-2.html"), make_item("D-1"), bodies={"A-1.md": "本文\n", "A-2.html": HTML_BODY})
    # 実行・検証（HTML の資料と資料以外）
    open_spa(page, url, "?tab=docs&id=A-2")
    expect(_panel(page).get_by_role("button", name="エクスポート", exact=True)).to_have_count(0)
    open_spa(page, url, "?tab=decisions&id=D-1")
    expect(_panel(page).get_by_role("button", name="エクスポート", exact=True)).to_have_count(0)
    # 実行・検証（編集の表示の間）
    open_spa(page, url, "?tab=docs&id=A-1")
    _panel(page).get_by_role("button", name="編集する").click()
    expect(_panel(page).get_by_role("button", name="エクスポート", exact=True)).to_have_count(0)


def test_export_menu_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """エクスポートのメニューは「エクスポート」を押した間だけ出す（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1"), bodies={"A-1.md": "本文\n"})
    open_spa(page, url, "?tab=docs&id=A-1")
    expect(page.get_by_role("dialog", name="エクスポート")).to_have_count(0)
    # 実行
    _panel(page).get_by_role("button", name="エクスポート", exact=True).click()
    # 検証
    expect(page.get_by_role("dialog", name="エクスポート")).to_be_visible()


def test_export_menu_action(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """Markdown でエクスポートすると、サーバーの API を呼ばずに `{ID}.md` をダウンロードさせる（正常系）。"""
    # 準備
    url = write_preview(make_item("A-1"), bodies={"A-1.md": "本文の段落\n"})
    open_spa(page, url, "?tab=docs&id=A-1")
    _panel(page).get_by_role("button", name="エクスポート", exact=True).click()
    page.get_by_role("button", name=re.compile("^Markdown でエクスポート")).click()
    # 実行
    with page.expect_download() as download:
        page.get_by_role("button", name="エクスポート", exact=True).last.click()
    # 検証
    assert download.value.suggested_filename == "A-1.md"


def test_copy_value_label(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """操作できる部品の今の値をコピーするボタンの文言は「今の値をコピー」（正常系）。"""
    # 準備・実行
    url = write_preview(make_item("A-1"), bodies={"A-1.md": EMBEDDED_BODY})
    open_spa(page, url, "?tab=docs&id=A-1")
    # 検証
    expect(_panel(page).get_by_role("button", name="今の値をコピー")).to_have_text(re.compile("今の値をコピー"), timeout=DIAGRAM_TIMEOUT_MS)


def test_embedded_diff_visible(make_workspace: MakeWorkspace, call_tool: CallTool, page: Page) -> None:
    """差分の表示の間で、本文が Markdown の資料に変わった埋め込んだ HTML の範囲があるときは、範囲の差分を出す（正常系）。"""
    # 準備
    root = build_embedded_diff_workspace(make_workspace, call_tool)
    url = str(call_tool("preview_url", workspace=str(root)).data["url"])
    # 実行
    panel = _diff(page, url, "V-2", item="A-1", tab="docs")
    # 検証
    expect(panel.get_by_role("group", name="埋め込んだ HTMLの差分の見せ方")).to_be_visible(timeout=DIAGRAM_TIMEOUT_MS)


def test_tags_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """タグは項目がタグを持つときだけ並べ、主題のタグに印を付ける（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1", tags=[{"name": "画面", "main": True}]), make_item("D-2", tags=[]))
    open_spa(page, url, "?tab=decisions&id=D-1")
    expect(_panel(page).locator("[title=主題]")).to_contain_text("画面")
    # 実行
    open_spa(page, url, "?tab=decisions&id=D-2")
    # 検証
    expect(_panel(page).locator("dt", has_text="タグ")).to_have_count(0)


def test_tags_input_visible(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """タグの入力は編集の表示の間だけ出す（正常系）。"""
    # 準備
    url = write_preview(make_item("D-1", tags=[{"name": "画面"}]))
    open_spa(page, url, "?tab=decisions&id=D-1")
    expect(page.get_by_role("combobox", name="タグを追加")).to_have_count(0)
    # 実行
    _panel(page).get_by_role("button", name="編集する").click()
    # 検証
    expect(page.get_by_role("combobox", name="タグを追加")).to_be_visible()
