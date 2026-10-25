"""部品設計『スレッドの書き込み』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page
from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 狭い幅で書き込みが占める部品の幅の割合の下限
NARROW_POST_RATIO = 0.9

POST = "ol.posts > li"


def test_user_post(open_story: OpenStory) -> None:
    """利用者の書き込み。右に寄せ、頭に「あなた」と日時を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--user-post")
    # 検証
    assert page.inner_text(f"{POST} .post-author") == "あなた"
    assert page.get_attribute(f"{POST} time", "datetime") == "2026-10-12T01:20:00+00:00"
    assert "user" in (page.get_attribute(POST, "class") or "").split()
    assert page.inner_text(f"{POST} .post-body").startswith("D-12 は案 B にしたい")
    # 本文の中の記録にある ID は、その項目を開くボタンにする
    assert page.get_attribute(f"{POST} button.idlink", "title") == "移し替えが途中で失敗したときの扱い"
    box = page.locator(POST).bounding_box()
    assert box is not None
    assert box["x"] + box["width"] >= page.evaluate("innerWidth") * 0.5


def test_ai_post(open_story: OpenStory) -> None:
    """AI の書き込み。左に寄せ、頭に「AI」と日時を出し、記録にある項目の ID はその項目を開くボタン、段落の中の改行は改行（`br`）として出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--ai-post")
    # 検証
    assert page.inner_text(f"{POST} .post-author") == "AI"
    assert "ai" in (page.get_attribute(POST, "class") or "").split()
    assert page.eval_on_selector_all(
        f"{POST} button.idlink", "buttons => buttons.map(b => b.textContent)"
    ) == ["D-12", "T-14"]
    assert page.locator(f"{POST} .post-body > p").count() == 1
    assert page.locator(f"{POST} .post-body > p > br").count() == 1
    assert page.inner_text(f"{POST} .post-body") == (
        "D-12 を案 B（写しから戻す）で決定にしました。\n戻す手順を書くタスクを T-14 に足しています。"
    )


def test_markdown_post(open_story: OpenStory) -> None:
    """AI の書き込みの Markdown。見出しは `h2`、表は `table`、`python` のコードは言語の札とコピーのボタンを持つ `pre`、`mermaid` は図、`> [!NOTE]` は「補足」の囲みで描かれ、記法の文字は出ない。段落の中の D-1 は項目を開くボタン。生の HTML の `onerror` は取り除かれて動かない（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--markdown-post")
    page.wait_for_selector(f"{POST} .post-body figure.diagram svg")
    body = f"{POST} .post-body"
    # 検証（見出し・表・コードブロック・図・囲み）
    assert page.inner_text(f"{body} h2") == "比べた結果"
    assert page.locator(f"{body} table").count() == 1
    assert page.locator(f"{body} .md-code .code-lang").all_inner_texts() == ["python"]
    assert page.locator(f"{body} .md-code button.code-copy").count() == 1
    assert page.locator(f"{body} .md-code pre").count() == 1
    assert page.locator(f"{body} figure.diagram .mermaid svg").count() == 1
    assert page.inner_text(f"{body} .markdown-alert .markdown-alert-title") == "補足"
    # 検証（記法の文字は出ない）
    text = page.inner_text(body)
    assert "##" not in text
    assert "| --- |" not in text
    assert "```" not in text
    assert "[!NOTE]" not in text
    # 検証（段落の中の D-1 は項目を開くボタン）
    assert page.get_attribute(f"{body} > p button.idlink", "title") == "描画のライブラリ"
    # 検証（生の HTML の `onerror` は取り除かれて動かない）
    assert page.locator(f"{body} [onerror]").count() == 0
    assert page.evaluate("window.injected !== true")


def test_pending_markdown(open_story: OpenStory) -> None:
    """レビュー中の返信の Markdown。破線の枠の中で「起票してよい」を太字（`strong`）で描き、`**` は出ない（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--pending-markdown")
    # 検証
    assert page.get_attribute(POST, "data-comment") == "C-45"
    assert page.eval_on_selector(POST, "e => getComputedStyle(e).borderTopStyle") == "dashed"
    assert page.inner_text(f"{POST} .post-body strong") == "起票してよい"
    assert "**" not in page.inner_text(f"{POST} .post-body")


def test_unknown_id(open_story: OpenStory) -> None:
    """本文の中の記録に無い ID は、ボタンにせず文字のまま出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--unknown-id")
    # 検証
    assert "D-99" in page.inner_text(f"{POST} .post-body")
    assert page.eval_on_selector_all(
        f"{POST} button.idlink", "buttons => buttons.map(b => b.textContent)"
    ) == ["D-12"]


def test_closed_event(open_story: OpenStory) -> None:
    """利用者がクローズにした記録。枠の無い 1 行にチェックの印・「あなたがクローズにしました」・日時、次の行に理由を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--closed-event")
    # 検証
    assert page.get_attribute(POST, "data-event") == "closed"
    assert page.inner_text(f"{POST} .th-event-line span") == "あなたがクローズにしました"
    assert page.locator(f"{POST} .th-event-line svg.icon").count() == 1
    assert page.locator(f"{POST} .th-event-line time[datetime]").count() == 1
    assert page.locator(f"{POST} .th-event-reason").count() == 1
    assert page.eval_on_selector(POST, "e => getComputedStyle(e).borderTopWidth") == "0px"


def test_reopened_event(open_story: OpenStory) -> None:
    """利用者が理由を書かずにオープンに戻した記録。戻す印と「あなたがオープンに戻しました」・日時の 1 行だけを出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--reopened-event")
    # 検証
    assert page.get_attribute(POST, "data-event") == "reopened"
    assert page.inner_text(f"{POST} .th-event-line span") == "あなたがオープンに戻しました"
    assert page.locator(f"{POST} .th-event-reason").count() == 0


def test_ai_closed_event(open_story: OpenStory) -> None:
    """AI がクローズにした記録。書き手を「AI が」にする（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--ai-closed-event")
    # 検証
    assert page.inner_text(f"{POST} .th-event-line span") == "AI がクローズにしました"
    assert "ai" in (page.get_attribute(POST, "class") or "").split()


def test_ai_reopened_event(open_story: OpenStory) -> None:
    """AI がオープンに戻した記録。「AI がオープンに戻しました」と理由を出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--ai-reopened-event")
    # 検証
    assert page.inner_text(f"{POST} .th-event-line span") == "AI がオープンに戻しました"
    assert page.locator(f"{POST} .th-event-reason").count() == 1


def test_pending(open_story: OpenStory) -> None:
    """レビュー中の返信。利用者の書き込みと同じく右に寄せ、破線の枠と頭に「レビュー中」の印、右上に「修正」「削除」を出し、日時は出さない（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--pending")
    # 検証
    assert page.get_attribute(POST, "data-comment") == "C-43"
    assert page.inner_text(f"{POST} .post-author") == "あなた"
    assert page.inner_text(f"{POST} .th-pending") == "レビュー中"
    assert page.locator(f"{POST} time").count() == 0
    assert page.eval_on_selector(POST, "e => getComputedStyle(e).borderTopStyle") == "dashed"
    assert page.get_by_role("button", name="TH-1 への返信を修正").count() == 1
    assert page.get_by_role("button", name="TH-1 への返信を削除").count() == 1
    assert page.get_attribute(f"{POST} button.idlink", "title") == "移し替えの失敗の扱いを書く"


def test_pending_editing(open_story: OpenStory) -> None:
    """レビュー中の返信を書き換えている。本文の代わりに書き換えの入力欄と「キャンセル」「修正」を出し、「修正」「削除」のアイコンは出さない（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--pending-editing")
    # 検証
    assert page.input_value(f"{POST} form.row-edit textarea") == "了解。T-14 は今週中に書いてほしい"
    assert page.get_by_role("button", name="キャンセル").count() == 1
    assert page.locator(f"{POST} form.row-edit button[type='submit']").inner_text() == "修正"
    assert page.get_by_role("button", name="TH-1 への返信を修正").count() == 0
    assert page.get_by_role("button", name="TH-1 への返信を削除").count() == 0


def test_pending_edit_failed(open_story: OpenStory) -> None:
    """書き換えを保てなかった。入力を残し、印のアイコンと理由を出す（異常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--pending-edit-failed")
    # 検証
    assert page.get_attribute(f"{POST} .send-msg", "role") == "alert"
    assert (
        page.inner_text(f"{POST} .send-msg")
        == "サーバーが止まっています。立ち上げ直してから直してください。"
    )
    assert page.locator(f"{POST} .send-msg svg.icon").count() == 1
    assert page.input_value(f"{POST} form.row-edit textarea") != ""


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。AI の書き込みは左に寄せたまま、書き込みの幅を部品の幅の 9 割以上に広げる（正常系）。"""
    # 準備
    page = open_story("preview-threadpost--narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    list_box = page.locator("ol.posts").bounding_box()
    post_box = page.locator(POST).bounding_box()
    assert list_box is not None
    assert post_box is not None
    assert post_box["width"] >= list_box["width"] * NARROW_POST_RATIO
    assert post_box["x"] == pytest.approx(list_box["x"], abs=1)
    assert post_box["x"] + post_box["width"] < list_box["x"] + list_box["width"]
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


# まとまりのリンク
SET_LINK = f"{POST} .post-body a.setlink"

# 本文の色の付いた文字の色（`--accent`）の実際の色を読む
ACCENT_COLOR_JS = """(() => {
  const probe = document.createElement('i');
  probe.style.color = 'var(--accent)';
  document.body.append(probe);
  const color = getComputedStyle(probe).color;
  probe.remove();
  return color;
})()"""

# 要素の文字の色と下線
LINK_STYLE_JS = "e => ({color: getComputedStyle(e).color, line: getComputedStyle(e).textDecorationLine})"

# 今フォーカスのある要素の文字
ACTIVE_TEXT_JS = "document.activeElement?.textContent ?? ''"


def _assert_link_looks_like_body_link(page: Page, selector: str) -> None:
    """まとまりのリンクが、詳細の本文のリンクと同じ色の付いた文字と下線で出ていることを確かめる。"""
    style = page.eval_on_selector(selector, LINK_STYLE_JS)
    assert style == {"color": page.evaluate(ACCENT_COLOR_JS), "line": "underline"}


def test_change_set_link(open_story: OpenStory) -> None:
    """AI の書き込みの中のまとまりのリンクだけを色の付いた文字と下線のリンクにし、中の ID はボタンにしない。Tab で本文の順に止まり、Enter で押せる（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--change-set-link")
    # 検証（リンクは 1 つだけで、読み上げの名前は文言、title はまとまりの説明）
    assert page.locator(SET_LINK).count() == 1
    assert page.inner_text(SET_LINK) == "A-14 の手引きの書き直し"
    assert page.get_attribute(SET_LINK, "href") == "#diff=V-6"
    assert page.get_attribute(SET_LINK, "title") == "A-14 の手引きを書き直す"
    assert page.get_by_role("link", name="A-14 の手引きの書き直し").count() == 1
    assert page.locator(f"{SET_LINK} button").count() == 0
    _assert_link_looks_like_body_link(page, SET_LINK)
    # 検証（外の A-14・D-12 は項目を開くボタンで、記録に無いまとまりを指す書き方はリンクにせず文言だけを出す）
    assert page.eval_on_selector_all(
        f"{POST} button.idlink", "buttons => buttons.map(b => b.textContent)"
    ) == ["A-14", "D-12"]
    assert page.locator(f"{POST} .post-body a").count() == 1
    assert "前に相談した版は 古い手引き にありました" in page.inner_text(f"{POST} .post-body")
    assert "[古い手引き]" not in page.inner_text(f"{POST} .post-body")
    # 実行（Tab で本文の順に止まる）
    page.keyboard.press("Tab")
    assert page.evaluate(ACTIVE_TEXT_JS) == "A-14"
    page.keyboard.press("Tab")
    assert page.evaluate(ACTIVE_TEXT_JS) == "A-14 の手引きの書き直し"
    page.keyboard.press("Tab")
    assert page.evaluate(ACTIVE_TEXT_JS) == "D-12"
    # 実行（Enter で押す）
    page.focus(SET_LINK)
    url_before = page.url
    page.keyboard.press("Enter")
    # 検証（既定の動作を止める: ハッシュを書き換えない）
    assert page.url == url_before


def test_change_set_link_not_linked(open_story: OpenStory) -> None:
    """まとまりのリンクにしない書き方（`since`・`diff` の無いハッシュ）はリンクにせず文言だけを出し、他の引数つきは `diff` だけを読んでリンクにする（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--change-set-link-not-linked")
    # 検証
    assert page.eval_on_selector_all(SET_LINK, "links => links.map(a => a.textContent)") == ["その他"]
    assert page.get_attribute(SET_LINK, "href") == "#diff=V-5"
    assert page.get_attribute(SET_LINK, "title") == "A-11 の段落を直す"
    text = page.inner_text(f"{POST} .post-body")
    assert page.locator(f"{POST} .post-body a").count() == 1
    assert text.startswith("since から と ハッシュの例 は押せなくてよい。")
    assert "](#" not in text


def test_pending_change_set_link(open_story: OpenStory) -> None:
    """レビュー中の返信の中でも、破線の枠の中に同じ見た目のまとまりのリンクを出し、外の項目の ID はボタンにする（正常系）。"""
    # 準備・実行
    page = open_story("preview-threadpost--pending-change-set-link")
    # 検証
    assert page.get_attribute(POST, "data-comment") == "C-44"
    assert page.eval_on_selector(POST, "e => getComputedStyle(e).borderTopStyle") == "dashed"
    assert page.eval_on_selector_all(SET_LINK, "links => links.map(a => a.textContent)") == [
        "A-14 の手引きの書き直し"
    ]
    assert page.get_attribute(SET_LINK, "href") == "#diff=V-6"
    assert page.get_attribute(SET_LINK, "title") == "A-14 の手引きを書き直す"
    _assert_link_looks_like_body_link(page, SET_LINK)
    assert page.eval_on_selector_all(
        f"{POST} button.idlink", "buttons => buttons.map(b => b.textContent)"
    ) == ["T-14"]


def test_change_set_link_long(open_story: OpenStory) -> None:
    """長い文言のまとまりのリンクは、行の中で書き込みの幅で折り返し、書き込みからはみ出さない（正常系）。"""
    # 準備
    page = open_story("preview-threadpost--change-set-link-long")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    assert page.locator(SET_LINK).count() == 1
    rects = page.eval_on_selector(
        SET_LINK, "e => [...e.getClientRects()].map(r => ({left: r.left, right: r.right}))"
    )
    body = page.locator(f"{POST} .post-body").bounding_box()
    assert body is not None
    assert len(rects) >= 2
    assert all(
        rect["left"] >= body["x"] - 1 and rect["right"] <= body["x"] + body["width"] + 1
        for rect in rects
    )
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
