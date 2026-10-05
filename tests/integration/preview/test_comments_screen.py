"""画面設計『コメントの一覧』の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page, Route
from preview_comment_helpers import (
    COMMENTS_BUTTON,
    COMMENTS_PANEL,
    DETAIL_MESSAGE,
    FREE_FORM,
    FREE_TEXTAREA,
    THREE_LINE_BODY,
    UPDATE_TIMEOUT_MS,
    free_comment,
    read_workspace_yaml,
)
from preview_fixture_types import OpenPreview, WriteReviewPreview
from workspace_fixtures import CallTool, MakeComment, MakeDraft, MakeItem

# 一覧の送る帯の要素
CHECK_ALL = f"{COMMENTS_PANEL} .send-band label.legend-all-check input"
BAND_COUNT = f"{COMMENTS_PANEL} .send-band .send-count"
BAND_RESULT = f"{COMMENTS_PANEL} .send-band .send-msg"

# 項目を指さないコメントの入力欄の畳む幅（これ以下）と、パネルを画面いっぱいに出す幅（これ以下）
COMPACT_WIDTH = 700
NARROW_WIDTH = 800
VIEWPORT_HEIGHT = 700

# 要見直しの赤（`--st-review`）の実際の色を読む
REVIEW_COLOR_SCRIPT = """(() => {
  const probe = document.createElement('i');
  probe.style.color = 'var(--st-review)';
  document.body.append(probe);
  const color = getComputedStyle(probe).color;
  probe.remove();
  return color;
})()"""


def _row(comment_id: str) -> str:
    """コメントの行の選択子を返す。"""
    return f"{COMMENTS_PANEL} li[data-comment='{comment_id}']"


def _open_list(page: Page) -> None:
    """トップバーのコメントのボタンで一覧を開き、開くのを待つ。"""
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open")


def _problem(status: int, detail: str) -> dict[str, Any]:
    """`application/problem+json` で返す理由の本文（RFC 9457）を作る。"""
    return {"type": "about:blank", "title": "error", "status": status, "detail": detail}


def _fulfill_problem(route: Route, status: int, detail: str) -> None:
    """要求に、理由つきのエラーで答える。"""
    route.fulfill(
        status=status,
        content_type="application/problem+json",
        body=json.dumps(_problem(status, detail), ensure_ascii=False),
    )


@pytest.fixture
def served_review(
    write_review_preview: WriteReviewPreview, make_item: MakeItem, make_comment: MakeComment
) -> tuple[str, Path]:
    """D-1・D-2・資料 A-1 と、項目・箇所・項目を指さないレビュー中のコメントを持つワークスペースの配信の URL を返す。"""
    return write_review_preview(
        make_item("D-1"),
        make_item("D-2"),
        make_item("A-1"),
        bodies={"A-1.md": THREE_LINE_BODY},
        comments=(
            make_comment("C-1", target="D-1", body="案 A にする"),
            make_comment(
                "C-2",
                target="A-1",
                body="ここは言い換える",
                loc={"kind": "body", "start": 2, "end": 2, "text": "言い換えたい文"},
            ),
            free_comment(make_comment("C-3", body="全体に目を通した")),
        ),
    )


def test_heading(served_review: tuple[str, Path], open_preview: OpenPreview) -> None:
    """トップバーのコメントのボタンで、見ている画面に重ねて左から出すパネルを開き、見出しとレビュー中の件数を出す（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url, "#tab=decisions&view=table")
    # 実行
    _open_list(page)
    page.wait_for_function(
        "document.querySelector('aside.comments-panel').getBoundingClientRect().x === 0"
    )
    # 検証
    assert page.get_attribute(COMMENTS_PANEL, "aria-label") == "コメントの一覧"
    assert page.inner_text(f"{COMMENTS_PANEL} .comments-head h2") == "レビュー中のコメント\n3"
    assert page.get_attribute(COMMENTS_BUTTON, "aria-expanded") == "true"
    box = page.locator(COMMENTS_PANEL).bounding_box()
    assert box is not None
    assert box["x"] == 0
    # 見ている画面を開いたまま重ねる
    assert page.locator("main table.grid").count() == 1


def test_close(served_review: tuple[str, Path], open_preview: OpenPreview) -> None:
    """閉じるボタン・Esc・トップバーのコメントのボタンで閉じ、履歴に積まない（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url, "#tab=decisions&view=table")
    history_length = page.evaluate("history.length")
    _open_list(page)
    assert history_length == page.evaluate("history.length")
    # 実行・検証（閉じるボタン）
    page.get_by_role("button", name="コメントの一覧を閉じる").click()
    page.wait_for_function("!document.querySelector('aside.comments-panel.open')")
    assert page.get_attribute(COMMENTS_BUTTON, "aria-expanded") == "false"
    # Esc
    _open_list(page)
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('aside.comments-panel.open')")
    # トップバーのコメントのボタン
    _open_list(page)
    page.click(COMMENTS_BUTTON)
    page.wait_for_function("!document.querySelector('aside.comments-panel.open')")
    assert page.evaluate("history.length") == history_length


def test_close_when_detail_open(
    served_review: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """詳細パネルを開いているときの Esc は、詳細パネルを先に閉じる（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url)
    _open_list(page)
    page.click(f"{_row('C-1')} button.row-target")
    page.wait_for_selector("aside.panel.open")
    # 実行・検証
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    assert page.locator(f"{COMMENTS_PANEL}.open").count() == 1
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('aside.comments-panel.open')")


def test_toggle_all(served_review: tuple[str, Path], open_preview: OpenPreview) -> None:
    """「すべて選ぶ」で全てのチェックを付ける・外す。一部だけのときは横棒にする（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url)
    _open_list(page)
    row_checks = f"{COMMENTS_PANEL} input.row-check"
    # 実行・検証
    assert page.get_attribute(f"{COMMENTS_PANEL} .send-band label.legend-all-check", "title") == "すべて選ぶ"
    assert page.get_by_label("すべて選ぶ").is_checked()
    page.get_by_label("すべて選ぶ").uncheck()
    assert page.eval_on_selector_all(row_checks, "cs => cs.map(c => c.checked)") == [False] * 3
    page.get_by_label("すべて選ぶ").check()
    assert page.eval_on_selector_all(row_checks, "cs => cs.map(c => c.checked)") == [True] * 3
    page.get_by_label("項目を指さないコメントを送る").uncheck()
    assert page.eval_on_selector(CHECK_ALL, "c => [c.checked, c.indeterminate]") == [False, True]


def test_selected_count(served_review: tuple[str, Path], open_preview: OpenPreview) -> None:
    """チェックした件数とレビュー中の件数を「{チェックした件数} / {レビュー中の件数} 件」で出す（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url)
    _open_list(page)
    assert page.inner_text(BAND_COUNT) == "3 / 3 件"
    # 実行
    page.locator(f"{_row('C-1')} input.row-check").uncheck()
    # 検証
    assert page.inner_text(BAND_COUNT) == "2 / 3 件"


def test_send(
    served_review: tuple[str, Path], open_preview: OpenPreview, call_tool: CallTool
) -> None:
    """チェックしたコメントだけを溜めた順に送り、送った行を一覧から外してコメントのボタンの件数を減らす（正常系）。"""
    # 準備
    url, root = served_review
    page = open_preview(url)
    _open_list(page)
    page.get_by_label("項目を指さないコメントを送る").uncheck()
    send = page.locator(f"{COMMENTS_PANEL} .send-band").get_by_role("button", name="まとめて送る")
    assert send.inner_text() == "まとめて送る（2 件）"
    # 実行
    send.click()
    page.wait_for_selector(f"{BAND_RESULT}.sent", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.get_attribute(BAND_RESULT, "role") == "status"
    assert page.inner_text(BAND_RESULT).startswith("2 件を送りました（")
    assert page.eval_on_selector_all(
        f"{COMMENTS_PANEL} .comments-list li", "rows => rows.map(r => r.dataset.comment)"
    ) == ["C-3"]
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "1"
    pending = call_tool("submissions", workspace=str(root))
    assert pending.data is not None
    assert [(item["target"], item["body"]) for item in pending.data["items"]] == [
        ("D-1", "案 A にする"),
        ("A-1", "ここは言い換える"),
    ]
    assert [item["id"] for item in read_workspace_yaml(root, "comments.yaml")["items"]] == ["C-3"]


def test_send_when_sending(
    served_review: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """送っている間は回る印と「送っています」を出し、まとめて送るを押せなくする（正常系）。"""
    # 準備
    url, _ = served_review
    held: list[Route] = []
    page.route("**/api/comments/send", lambda route: held.append(route))
    open_preview(url)
    _open_list(page)
    send = page.locator(f"{COMMENTS_PANEL} .send-band").get_by_role("button", name="まとめて送る")
    # 実行
    send.click()
    page.wait_for_selector(f"{BAND_RESULT}.sending")
    # 検証
    assert page.inner_text(BAND_RESULT) == "送っています"
    assert page.locator(f"{BAND_RESULT} .spinner").count() == 1
    assert send.is_disabled()
    held[0].continue_()
    page.wait_for_selector(f"{BAND_RESULT}.sent", timeout=UPDATE_TIMEOUT_MS)


def test_send_when_nothing_checked(
    served_review: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """チェックが 0 件のときは、まとめて送るを押せず、チェックを付けるよう出す（異常系）。"""
    # 準備
    url, _ = served_review
    posts: list[str] = []
    page.on(
        "request",
        lambda request: posts.append(request.url) if request.method == "POST" else None,
    )
    open_preview(url)
    _open_list(page)
    # 実行
    page.get_by_label("すべて選ぶ").uncheck()
    # 検証
    send = page.locator(f"{COMMENTS_PANEL} .send-band").get_by_role("button", name="まとめて送る")
    assert send.inner_text() == "まとめて送る（0 件）"
    assert send.is_disabled()
    assert page.inner_text(BAND_RESULT) == "送るコメントにチェックを付けてください。"
    assert posts == []


def test_send_when_stale(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
) -> None:
    """箇所が合わないコメントがあると、どれも送らず、その行に理由を出して行の枠を要見直しの赤にする（異常系）。"""
    # 準備
    url, root = write_review_preview(
        make_item("D-1"),
        make_item("A-1"),
        bodies={"A-1.md": THREE_LINE_BODY},
        comments=(
            make_comment("C-1", target="D-1", body="案 A にする"),
            make_comment(
                "C-2",
                target="A-1",
                body="ここは言い換える",
                loc={"kind": "body", "start": 2, "end": 2, "text": "消えた文"},
            ),
        ),
    )
    page = open_preview(url)
    _open_list(page)
    # 実行
    page.locator(f"{COMMENTS_PANEL} .send-band").get_by_role("button", name="まとめて送る").click()
    page.wait_for_selector(f"{BAND_RESULT}.stale", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert (
        page.inner_text(BAND_RESULT) == "送れませんでした。箇所が合わないコメントが 1 件あります。"
    )
    assert page.get_attribute(f"{_row('C-2')} .row-stale", "role") == "alert"
    assert "選んだ文が A-1 の" in page.inner_text(f"{_row('C-2')} .row-stale")
    assert page.locator(f"{_row('C-1')} .row-stale").count() == 0
    review = page.evaluate(REVIEW_COLOR_SCRIPT)
    assert page.eval_on_selector(_row("C-2"), "e => getComputedStyle(e).borderTopColor") == review
    assert not (root / "submissions.yaml").exists()
    assert len(read_workspace_yaml(root, "comments.yaml")["items"]) == 2


def test_send_when_unreachable(
    served_review: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """サーバーに届かないときは、立ち上げ直してから送るよう出す（異常系）。"""
    # 準備
    url, _ = served_review
    page.route("**/api/comments/send", lambda route: route.abort())
    open_preview(url)
    _open_list(page)
    # 実行
    page.locator(f"{COMMENTS_PANEL} .send-band").get_by_role("button", name="まとめて送る").click()
    page.wait_for_selector(f"{BAND_RESULT}.failed", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert (
        page.inner_text(BAND_RESULT)
        == "送れませんでした。サーバーが止まっています。立ち上げ直してから送ってください。"
    )
    assert page.locator(f"{BAND_RESULT} svg.icon").count() == 1


def test_send_when_server_refuses(
    served_review: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """サーバーが理由を返したときは、その理由を出す（異常系）。"""
    # 準備
    url, _ = served_review
    page.route(
        "**/api/comments/send",
        lambda route: _fulfill_problem(route, 500, "submissions.yaml を書けません"),
    )
    open_preview(url)
    _open_list(page)
    # 実行
    page.locator(f"{COMMENTS_PANEL} .send-band").get_by_role("button", name="まとめて送る").click()
    page.wait_for_selector(f"{BAND_RESULT}.failed", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.inner_text(BAND_RESULT) == "送れませんでした。submissions.yaml を書けません"


def test_rows_order(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
) -> None:
    """レビュー中のコメントを溜めた順（ID の連番の小さい順）に 1 件 1 行で並べる（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("D-1"),
        comments=(
            make_comment("C-10", target="D-1", body="十番目"),
            make_comment("C-2", target="D-1", body="二番目"),
        ),
    )
    page = open_preview(url)
    # 実行
    _open_list(page)
    # 検証
    assert page.eval_on_selector_all(
        f"{COMMENTS_PANEL} .comments-list li", "rows => rows.map(r => r.dataset.comment)"
    ) == ["C-2", "C-10"]


def test_row_check(served_review: tuple[str, Path], open_preview: OpenPreview) -> None:
    """行のチェックは、開いたときと新しく溜めたコメントがチェックした状態で入り、読み上げの名前に向けた項目を持つ（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url)
    _open_list(page)
    # 実行
    page.fill(FREE_TEXTAREA, "あとで足したコメント")
    page.locator(FREE_FORM).get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(_row("C-4"), timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.eval_on_selector_all(
        f"{COMMENTS_PANEL} input.row-check",
        "cs => cs.map(c => [c.getAttribute('aria-label'), c.checked])",
    ) == [
        ["D-1 へのコメントを送る", True],
        ["A-1 へのコメントを送る", True],
        ["項目を指さないコメントを送る", True],
        ["項目を指さないコメントを送る", True],
    ]
    assert page.inner_text(BAND_COUNT) == "4 / 4 件"


def test_row_target(served_review: tuple[str, Path], open_preview: OpenPreview) -> None:
    """向けた項目の ID とタイトルを出し、押すと一覧を開いたまま右にその項目の詳細パネルを開いて、行を選んだ見た目にする（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url)
    _open_list(page)
    target = f"{_row('C-1')} button.row-target"
    assert page.inner_text(target) == "D-1\nD-1の題"
    # 実行
    page.click(target)
    page.wait_for_selector("aside.panel.open")
    # 検証
    assert page.inner_text("aside.panel .d-title") == "D-1の題"
    assert page.locator(f"{COMMENTS_PANEL}.open").count() == 1
    assert page.eval_on_selector(_row("C-1"), "e => e.classList.contains('selected')") is True
    assert page.eval_on_selector(_row("C-3"), "e => e.classList.contains('selected')") is False
    panel_box = page.locator("aside.panel").bounding_box()
    list_box = page.locator(COMMENTS_PANEL).bounding_box()
    assert panel_box is not None
    assert list_box is not None
    assert panel_box["x"] >= list_box["x"] + list_box["width"]


def test_row_target_when_not_pointing(
    served_review: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """項目を指さないコメントは、押せない「項目を指さない」を出す（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url)
    # 実行
    _open_list(page)
    # 検証
    assert page.inner_text(f"{_row('C-3')} .row-target") == "項目を指さない"
    assert page.locator(f"{_row('C-3')} button.row-target").count() == 0


def test_row_target_when_gone(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
) -> None:
    """項目が消えたコメントは、押せない ID だけを出し、理由を出すまで箇所を外すを出さない（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("D-1"), comments=(make_comment("C-1", target="D-9", body="消えた項目へ"),)
    )
    page = open_preview(url)
    # 実行
    _open_list(page)
    # 検証
    assert page.inner_text(f"{_row('C-1')} .row-target") == "D-9"
    assert page.locator(f"{_row('C-1')} button.row-target").count() == 0


def test_row_location(served_review: tuple[str, Path], open_preview: OpenPreview) -> None:
    """箇所を持つコメントは、箇所の名前と選んだ文の引用を出す（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url)
    # 実行
    _open_list(page)
    # 検証
    assert page.inner_text(f"{_row('C-2')} .review-loc-name") == "本文 2 行目"
    assert page.inner_text(f"{_row('C-2')} .send-quote") == "言い換えたい文"
    assert page.locator(f"{_row('C-1')} .review-loc").count() == 0


def test_row_body(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
) -> None:
    """コメントの本文を、改行を保って出す（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("D-1"),
        comments=(make_comment("C-1", target="D-1", body="1 行目\n2 行目"),),
    )
    page = open_preview(url)
    # 実行
    _open_list(page)
    # 検証
    assert page.inner_text(f"{_row('C-1')} .review-body") == "1 行目\n2 行目"


def test_edit(served_review: tuple[str, Path], open_preview: OpenPreview) -> None:
    """「直す」で行の本文を入力欄に切り替え、直して送ると本文に戻す（正常系）。"""
    # 準備
    url, root = served_review
    page = open_preview(url)
    _open_list(page)
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを直す").click()
    field = f"{_row('C-1')} form.row-edit textarea"
    assert page.input_value(field) == "案 A にする"
    page.fill(field, "案 B にする")
    # 実行
    page.locator(f"{_row('C-1')} form.row-edit").get_by_role("button", name="直す").click()
    page.wait_for_function(
        "document.querySelector(\"li[data-comment='C-1'] .review-body\")?.textContent === '案 B にする'",
        timeout=UPDATE_TIMEOUT_MS,
    )
    # 検証
    assert page.locator(f"{_row('C-1')} form.row-edit").count() == 0
    saved = read_workspace_yaml(root, "comments.yaml")["items"]
    assert saved[0]["body"] == "案 B にする"


def test_edit_when_body_empty(
    served_review: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """空白だけの本文は送らず、コメントを入れてから直すよう出す（異常系）。"""
    # 準備
    url, root = served_review
    patches: list[str] = []
    page.on(
        "request",
        lambda request: patches.append(request.url) if request.method == "PATCH" else None,
    )
    open_preview(url)
    _open_list(page)
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを直す").click()
    page.fill(f"{_row('C-1')} form.row-edit textarea", "   ")
    # 実行
    page.locator(f"{_row('C-1')} form.row-edit").get_by_role("button", name="直す").click()
    # 検証
    assert page.inner_text(f"{_row('C-1')} form.row-edit .send-msg") == "コメントを入れてから直してください。"
    assert patches == []
    assert read_workspace_yaml(root, "comments.yaml")["items"][0]["body"] == "案 A にする"


def test_edit_when_server_refuses(
    served_review: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """サーバーが断ったときは、入力を残して理由を出す（異常系）。"""
    # 準備
    url, _ = served_review
    page.route(
        "**/api/comments/C-1",
        lambda route: (
            _fulfill_problem(route, 500, "comments.yaml を書けません")
            if route.request.method == "PATCH"
            else route.continue_()
        ),
    )
    open_preview(url)
    _open_list(page)
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを直す").click()
    page.fill(f"{_row('C-1')} form.row-edit textarea", "案 B にする")
    # 実行
    page.locator(f"{_row('C-1')} form.row-edit").get_by_role("button", name="直す").click()
    page.wait_for_selector(f"{_row('C-1')} form.row-edit .send-msg svg.icon", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.inner_text(f"{_row('C-1')} form.row-edit .send-msg") == "comments.yaml を書けません"
    assert page.input_value(f"{_row('C-1')} form.row-edit textarea") == "案 B にする"


def test_edit_when_cancelled(
    served_review: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """「やめる」と Esc で書き換えを捨てる。Esc では一覧を閉じない（正常系）。"""
    # 準備
    url, root = served_review
    page = open_preview(url)
    _open_list(page)
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを直す").click()
    page.fill(f"{_row('C-1')} form.row-edit textarea", "捨てる")
    # 実行・検証（やめる）
    page.get_by_role("button", name="やめる").click()
    assert page.inner_text(f"{_row('C-1')} .review-body") == "案 A にする"
    # Esc
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを直す").click()
    page.fill(f"{_row('C-1')} form.row-edit textarea", "捨てる")
    page.press(f"{_row('C-1')} form.row-edit textarea", "Escape")
    assert page.inner_text(f"{_row('C-1')} .review-body") == "案 A にする"
    assert page.locator(f"{COMMENTS_PANEL}.open").count() == 1
    assert read_workspace_yaml(root, "comments.yaml")["items"][0]["body"] == "案 A にする"


def test_remove_and_restore(
    served_review: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """削除で確認を挟まず行を消して「元に戻す」に置き換え、押すと同じ ID と日時で元の場所に戻す（正常系）。"""
    # 準備
    url, root = served_review
    page = open_preview(url)
    _open_list(page)
    created = read_workspace_yaml(root, "comments.yaml")["items"][0]["created"]
    # 実行（削除）
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを削除").click()
    page.wait_for_selector(f"{_row('C-1')}.removed", timeout=UPDATE_TIMEOUT_MS)
    # 検証（削除）
    assert page.locator("dialog[open]").count() == 0
    assert page.inner_text(f"{_row('C-1')} .removed-msg") == "コメントを削除しました。"
    assert [item["id"] for item in read_workspace_yaml(root, "comments.yaml")["items"]] == [
        "C-2",
        "C-3",
    ]
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "2"
    # 実行（元に戻す）
    page.get_by_role("button", name="元に戻す").click()
    page.wait_for_selector(f"{_row('C-1')} button.row-target", timeout=UPDATE_TIMEOUT_MS)
    # 検証（元に戻す）
    assert page.eval_on_selector_all(
        f"{COMMENTS_PANEL} .comments-list li", "rows => rows.map(r => r.dataset.comment)"
    ) == ["C-1", "C-2", "C-3"]
    restored = read_workspace_yaml(root, "comments.yaml")["items"][0]
    assert (restored["id"], restored["created"]) == ("C-1", created)


def test_restore_when_list_closed(
    served_review: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """一覧を閉じると、削除した行の「元に戻す」は出さなくなる（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url)
    _open_list(page)
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを削除").click()
    page.wait_for_selector(f"{_row('C-1')}.removed", timeout=UPDATE_TIMEOUT_MS)
    # 実行
    page.get_by_role("button", name="コメントの一覧を閉じる").click()
    page.wait_for_function("!document.querySelector('aside.comments-panel.open')")
    _open_list(page)
    # 検証
    assert page.get_by_role("button", name="元に戻す").count() == 0
    assert page.locator(_row("C-1")).count() == 0


def test_stale_reason_and_detach(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
) -> None:
    """箇所が合わない理由の行で「箇所を外す」を押すと、項目へのコメントにして理由と箇所を消す（正常系）。"""
    # 準備
    url, root = write_review_preview(
        make_item("A-1"),
        bodies={"A-1.md": THREE_LINE_BODY},
        comments=(
            make_comment(
                "C-1",
                target="A-1",
                body="ここは言い換える",
                loc={"kind": "body", "start": 2, "end": 2, "text": "消えた文"},
            ),
        ),
    )
    page = open_preview(url)
    _open_list(page)
    page.locator(f"{COMMENTS_PANEL} .send-band").get_by_role("button", name="まとめて送る").click()
    page.wait_for_selector(f"{_row('C-1')} .row-stale", timeout=UPDATE_TIMEOUT_MS)
    # 実行
    page.get_by_role("button", name="箇所を外す").click()
    page.wait_for_function(
        "!document.querySelector(\"li[data-comment='C-1'] .row-stale\")", timeout=UPDATE_TIMEOUT_MS
    )
    # 検証
    assert page.locator(f"{_row('C-1')} .review-loc").count() == 0
    assert read_workspace_yaml(root, "comments.yaml")["items"][0].get("loc") is None


def test_stale_reason_when_target_gone(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
) -> None:
    """項目が消えたコメントの理由の行には、箇所を外すを出さない（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("D-1"),
        comments=(
            make_comment(
                "C-1",
                target="D-9",
                body="消えた項目へ",
                loc={"kind": "value", "key": "title", "text": "題"},
            ),
        ),
    )
    page = open_preview(url)
    _open_list(page)
    # 実行
    page.locator(f"{COMMENTS_PANEL} .send-band").get_by_role("button", name="まとめて送る").click()
    page.wait_for_selector(f"{_row('C-1')} .row-stale", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.inner_text(f"{_row('C-1')} .row-stale span") == "D-9 がありません"
    assert page.get_by_role("button", name="箇所を外す").count() == 0


def test_empty(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """レビュー中のコメントが 0 件のときは、印と「レビュー中のコメントはありません。」を出し、送る帯は出さない（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("D-1"))
    page = open_preview(url)
    # 実行
    _open_list(page)
    # 検証
    assert page.inner_text(f"{COMMENTS_PANEL} .comments-empty") == "レビュー中のコメントはありません。"
    assert page.locator(f"{COMMENTS_PANEL} .comments-empty svg.icon").count() == 1
    assert page.locator(f"{COMMENTS_PANEL} .send-band").count() == 0
    assert page.locator(FREE_FORM).count() == 1


def test_free_input(
    served_review: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """項目を指さないコメントを下端の入力から溜めると、チェックした状態で一覧の末尾に足す（正常系）。"""
    # 準備
    url, root = served_review
    page = open_preview(url)
    _open_list(page)
    # 実行
    page.fill(FREE_TEXTAREA, "全体への補足")
    page.locator(FREE_FORM).get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(_row("C-4"), timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.eval_on_selector_all(
        f"{COMMENTS_PANEL} .comments-list li", "rows => rows.map(r => r.dataset.comment)"
    ) == ["C-1", "C-2", "C-3", "C-4"]
    assert page.inner_text(f"{_row('C-4')} .row-target") == "項目を指さない"
    assert page.inner_text(f"{_row('C-4')} .review-body") == "全体への補足"
    assert page.is_checked(f"{_row('C-4')} input.row-check")
    assert page.locator(f"{FREE_FORM} label.send-label").count() == 0
    saved = read_workspace_yaml(root, "comments.yaml")["items"]
    assert saved[-1].get("target") is None
    assert saved[-1]["body"] == "全体への補足"


def test_free_input_when_narrow(
    served_review: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """画面の幅 720px 以下では、項目を指さない入力を 1 行に畳み、フォーカスしたときに広げ、空のまま外へ出たら畳む（正常系）。"""
    # 準備
    url, _ = served_review
    page.set_viewport_size({"width": COMPACT_WIDTH, "height": VIEWPORT_HEIGHT})
    open_preview(url)
    _open_list(page)
    # 検証（畳んだ形）
    assert page.locator(f"{FREE_FORM}.collapsed").count() == 1
    assert page.locator(f"{FREE_FORM} button[type=submit]").count() == 0
    # 実行（フォーカスして広げる）
    page.focus(FREE_TEXTAREA)
    page.wait_for_selector(f"{FREE_FORM}:not(.collapsed)")
    assert page.locator(f"{FREE_FORM}").get_by_role("button", name="レビューに追加").is_visible()
    # 実行（空のまま外へ出る）
    page.get_by_role("button", name="コメントの一覧を閉じる").focus()
    page.wait_for_selector(f"{FREE_FORM}.collapsed")


def test_free_input_when_draft_exists(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_draft: MakeDraft,
    page: Page,
) -> None:
    """書きかけがあるときは、狭い幅でも広げて出す（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("D-1"),
        drafts=(free_comment(make_draft(body="全体への書きかけ")),),
    )
    page.set_viewport_size({"width": COMPACT_WIDTH, "height": VIEWPORT_HEIGHT})
    open_preview(url)
    # 実行
    _open_list(page)
    # 検証
    assert page.locator(f"{FREE_FORM}.collapsed").count() == 0
    assert page.input_value(FREE_TEXTAREA) == "全体への書きかけ"
    assert page.locator(FREE_FORM).get_by_role("button", name="レビューに追加").is_visible()


def test_narrow_width(served_review: tuple[str, Path], open_preview: OpenPreview, page: Page) -> None:
    """幅 900px 以下は画面の幅いっぱいに出し、行から開いた詳細パネルを閉じると一覧へ戻る（正常系）。"""
    # 準備
    url, _ = served_review
    page.set_viewport_size({"width": NARROW_WIDTH, "height": VIEWPORT_HEIGHT})
    open_preview(url)
    # 実行
    _open_list(page)
    # 検証
    width = page.evaluate(
        "document.querySelector('aside.comments-panel').getBoundingClientRect().width"
    )
    assert width == pytest.approx(NARROW_WIDTH, abs=1)
    page.click(f"{_row('C-1')} button.row-target")
    page.wait_for_selector("aside.panel.open")
    page.click("aside.panel button.panel-back")
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    assert page.locator(f"{COMMENTS_PANEL}.open").count() == 1
    assert page.is_visible(COMMENTS_PANEL)


def test_detail_input_message_is_separate(
    served_review: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """行から開いた詳細パネルの入力は、一覧の下端の入力とは別に項目へのコメントを溜める（正常系）。"""
    # 準備
    url, root = served_review
    page = open_preview(url)
    _open_list(page)
    page.click(f"{_row('C-1')} button.row-target")
    page.wait_for_selector("aside.panel.open form.send")
    # 実行
    page.fill("aside.panel form.send textarea", "詳細パネルから足す")
    page.locator("aside.panel form.send").get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.saved", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    page.wait_for_selector(_row("C-4"), timeout=UPDATE_TIMEOUT_MS)
    assert page.inner_text(f"{_row('C-4')} .review-body") == "詳細パネルから足す"
    assert page.inner_text(f"{_row('C-4')} .row-target") == "D-1\nD-1の題"
    assert [item["id"] for item in read_workspace_yaml(root, "comments.yaml")["items"]] == [
        "C-1",
        "C-2",
        "C-3",
        "C-4",
    ]
