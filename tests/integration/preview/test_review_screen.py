"""画面設計『レビュー中の書き込み』の結合テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, Route
from preview_fit_helpers import assert_fits_smallest, set_smallest
from preview_comment_helpers import (
    BAND_COUNT,
    BAND_RESULT,
    CHECK_ALL,
    COMMENTS_BUTTON,
    COMMENTS_PANEL,
    REVIEW_ENTRY,
    REVIEW_HEAD,
    THREE_LINE_BODY,
    UPDATE_TIMEOUT_MS,
    free_comment,
    fulfill_problem,
    open_review,
    read_workspace_yaml,
    review_row,
)
from preview_fixture_types import OpenPreview, WriteReviewPreview
from preview_post_link_helpers import DIFF_CHIP_TITLE, DIFF_SETTLE_MS, hash_params
from preview_stack_helpers import DETAIL_HASH, is_inert, open_narrow, wait_front
from claude_pane_fixtures import StartClaudePane
from workspace_fixtures import (
    RECORD_DIR,
    CallTool,
    MakeComment,
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
    StartServer,
    WriteComments,
)

# パネルを画面いっぱいに出す幅（これ以下）
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


def _open_row_in_detail(page: Page, comment_id: str) -> None:
    """一覧の行の向けた項目を押して、一覧を開いたまま詳細パネルを開く。"""
    page.click(f"{_row(comment_id)} button.row-target")
    page.wait_for_selector("aside.panel.open")


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
    """見出しの帯の「レビュー中」でパネルの中を切り替え、見出しの題とレビュー中の書き込みの件数を出す。この画面では入口を出さない（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url)
    history_length = page.evaluate("history.length")
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open")
    assert page.get_attribute(REVIEW_ENTRY, "aria-label") == "レビュー中の書き込みを確かめる（3 件）"
    # 実行
    page.click(REVIEW_ENTRY)
    page.wait_for_selector(REVIEW_HEAD)
    # 検証
    assert page.inner_text(f"{REVIEW_HEAD} h3.review-title") == "レビュー中の書き込み\n3"
    assert page.inner_text(f"{COMMENTS_PANEL} .comments-head h2") == "コメント"
    assert page.locator(REVIEW_ENTRY).count() == 0
    assert page.get_by_role("button", name="コメントの一覧を閉じる").count() == 1
    assert page.evaluate("history.length") == history_length


def test_back(served_review: tuple[str, Path], open_preview: OpenPreview) -> None:
    """戻るで開く前の画面（スレッドの一覧）へ戻り、「レビュー中」の入口へフォーカスを戻す。Esc も同じ（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url)
    open_review(page)
    # 実行・検証（戻る）
    page.get_by_role("button", name="戻る").click()
    page.wait_for_selector(f"{COMMENTS_PANEL} .talk-band")
    assert page.locator(REVIEW_HEAD).count() == 0
    assert page.evaluate(
        "document.activeElement === document.querySelector('aside.comments-panel button.review-entry')"
    )
    # Esc
    page.click(REVIEW_ENTRY)
    page.wait_for_selector(REVIEW_HEAD)
    page.keyboard.press("Escape")
    page.wait_for_selector(f"{COMMENTS_PANEL} .talk-band")
    assert page.locator(f"{COMMENTS_PANEL}.open").count() == 1


def test_narrow_back_by_escape_in_front_of_detail(
    served_review: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """幅 390px で一覧が詳細パネルの前に出ているときの Esc は、レビュー中の書き込みの画面から開く前の画面へ戻り、詳細パネルは閉じない（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url, DETAIL_HASH)
    open_narrow(page)
    open_review(page)
    wait_front(page, "comments")
    # 実行
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_selector(f"{COMMENTS_PANEL} .talk-band")
    wait_front(page, "comments")
    assert page.locator(REVIEW_HEAD).count() == 0
    assert page.locator("aside.panel.open").count() == 1
    assert is_inert(page, "detail") is True


def test_toggle_all(served_review: tuple[str, Path], open_preview: OpenPreview) -> None:
    """「すべて選ぶ」で全てのチェックを付ける・外す。一部だけのときは横棒にする（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url)
    open_review(page)
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
    open_review(page)
    assert page.inner_text(BAND_COUNT) == "3 / 3 件"
    # 実行
    page.locator(f"{_row('C-1')} input.row-check").uncheck()
    # 検証
    assert page.inner_text(BAND_COUNT) == "2 / 3 件"


def test_send(
    served_review: tuple[str, Path], open_preview: OpenPreview, call_tool: CallTool
) -> None:
    """チェックしたものだけを溜めた順に送り、送った行をレビュー中の書き込みから外してコメントのボタンの件数を減らす（正常系）。"""
    # 準備
    url, root = served_review
    page = open_preview(url)
    open_review(page)
    page.get_by_label("項目を指さないコメントを送る").uncheck()
    send = page.locator(f"{COMMENTS_PANEL} .send-band").get_by_role("button", name="まとめて送る")
    assert send.inner_text() == "まとめて送る（2 件）"
    # 実行
    send.click()
    page.wait_for_selector(f"{BAND_RESULT}.sent", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.get_attribute(BAND_RESULT, "role") == "status"
    # tmux の外で立てたサーバーなので、入力できなかったと出す
    assert page.inner_text(BAND_RESULT).startswith(
        "2 件を送りましたが、Claude Code には入力できませんでした（"
    )
    assert page.inner_text(BAND_RESULT).endswith(
        "送った内容は保存されていて、次に話し合いを始めたときに取り込まれます。"
    )
    assert page.eval_on_selector_all(
        f"{COMMENTS_PANEL} .comments-list li", "rows => rows.map(r => r.dataset.comment)"
    ) == ["C-3"]
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "1"
    awaiting = call_tool("threads", workspace=str(root), awaiting=True)
    assert awaiting.data is not None
    assert [(item["id"], item["target"], item["head"]) for item in awaiting.data["items"]] == [
        ("TH-2", "A-1", "ここは言い換える"),
        ("TH-1", "D-1", "案 A にする"),
    ]
    assert [item["id"] for item in read_workspace_yaml(root, "comments.yaml")["items"]] == ["C-3"]


def test_send_when_entered(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    start_server: StartServer,
    start_claude_pane: StartClaudePane,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """tmux の中で立てたサーバーなら、送った結果に Claude Code へ入力したことを出す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1", target="D-1", body="案 A にする"))
    pane = start_claude_pane(mode="user", cwd=root)
    server = start_server(extra_env=pane.env, cwd=root)
    opened = server.call("preview_url", workspace=str(root))
    assert opened.data is not None
    page = open_preview(str(opened.data["url"]))
    open_review(page)
    send = page.locator(f"{COMMENTS_PANEL} .send-band").get_by_role("button", name="まとめて送る")
    # 実行
    send.click()
    page.wait_for_selector(f"{BAND_RESULT}.sent", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.get_attribute(BAND_RESULT, "role") == "status"
    assert page.inner_text(BAND_RESULT).startswith("1 件を送り、Claude Code に入力しました（")
    assert len(pane.lines()) == 1


def test_send_when_sending(
    served_review: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """送っている間は回る印と「送っています」を出し、まとめて送るを押せなくする（正常系）。"""
    # 準備
    url, _ = served_review
    held: list[Route] = []
    page.route("**/api/comments/send", lambda route: held.append(route))
    open_preview(url)
    open_review(page)
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
        lambda request: (
            posts.append(request.url)
            if request.method == "POST" and not request.url.endswith("/api/opened")
            else None
        ),
    )
    open_preview(url)
    open_review(page)
    # 実行
    page.get_by_label("すべて選ぶ").uncheck()
    # 検証
    send = page.locator(f"{COMMENTS_PANEL} .send-band").get_by_role("button", name="まとめて送る")
    assert send.inner_text() == "まとめて送る（0 件）"
    assert send.is_disabled()
    assert page.inner_text(BAND_RESULT) == "送る書き込みにチェックを付けてください。"
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
    open_review(page)
    # 実行
    page.locator(f"{COMMENTS_PANEL} .send-band").get_by_role("button", name="まとめて送る").click()
    page.wait_for_selector(f"{BAND_RESULT}.stale", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert (
        page.inner_text(BAND_RESULT) == "送れませんでした。送れない書き込みが 1 件あります。"
    )
    assert page.get_attribute(f"{_row('C-2')} .row-stale", "role") == "alert"
    assert "選んだ文が A-1 の" in page.inner_text(f"{_row('C-2')} .row-stale")
    assert page.locator(f"{_row('C-1')} .row-stale").count() == 0
    review = page.evaluate(REVIEW_COLOR_SCRIPT)
    assert page.eval_on_selector(_row("C-2"), "e => getComputedStyle(e).borderTopColor") == review
    assert not (root / RECORD_DIR / "threads.yaml").exists()
    assert len(read_workspace_yaml(root, "comments.yaml")["items"]) == 2


def test_send_when_unreachable(
    served_review: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """サーバーに届かないときは、立ち上げ直してから送るよう出す（異常系）。"""
    # 準備
    url, _ = served_review
    page.route("**/api/comments/send", lambda route: route.abort())
    open_preview(url)
    open_review(page)
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
        lambda route: fulfill_problem(route, 500, "threads.yaml を書けません"),
    )
    open_preview(url)
    open_review(page)
    # 実行
    page.locator(f"{COMMENTS_PANEL} .send-band").get_by_role("button", name="まとめて送る").click()
    page.wait_for_selector(f"{BAND_RESULT}.failed", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.inner_text(BAND_RESULT) == "送れませんでした。threads.yaml を書けません"


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
    open_review(page)
    # 検証
    assert page.eval_on_selector_all(
        f"{COMMENTS_PANEL} .comments-list li", "rows => rows.map(r => r.dataset.comment)"
    ) == ["C-2", "C-10"]


def test_row_check(served_review: tuple[str, Path], open_preview: OpenPreview) -> None:
    """行のチェックは、開いたときにチェックした状態で入り、読み上げの名前に向けた項目を持つ（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url)
    # 実行
    open_review(page)
    # 検証
    assert page.eval_on_selector_all(
        f"{COMMENTS_PANEL} input.row-check",
        "cs => cs.map(c => [c.getAttribute('aria-label'), c.checked])",
    ) == [
        ["D-1 へのコメントを送る", True],
        ["A-1 へのコメントを送る", True],
        ["項目を指さないコメントを送る", True],
    ]
    assert page.inner_text(BAND_COUNT) == "3 / 3 件"


def test_row_target(served_review: tuple[str, Path], open_preview: OpenPreview) -> None:
    """向けた項目の ID とタイトルを出し、押すと一覧を開いたまま右にその項目の詳細パネルを開いて、行を選んだ見た目にする（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url)
    open_review(page)
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
    """項目を指さないコメントは、向けた項目を何も出さず、行の頭を「新しいスレッド」の札だけにする（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url)
    # 実行
    open_review(page)
    # 検証
    assert page.inner_text(f"{_row('C-3')} .row-head") == "新しいスレッド"
    assert page.locator(f"{_row('C-3')} .row-target").count() == 0
    assert "項目を指さない" not in page.inner_text(_row("C-3"))


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
    open_review(page)
    # 検証
    assert page.inner_text(f"{_row('C-1')} .row-target") == "D-9"
    assert page.locator(f"{_row('C-1')} button.row-target").count() == 0


def test_row_location(served_review: tuple[str, Path], open_preview: OpenPreview) -> None:
    """箇所を持つコメントは、箇所の名前と選んだ文の引用を出す（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url)
    # 実行
    open_review(page)
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
    open_review(page)
    # 検証
    assert page.inner_text(f"{_row('C-1')} .review-body") == "1 行目\n2 行目"


def test_row_body_change_set_link(
    write_post_link_preview: WriteReviewPreview, open_preview: OpenPreview
) -> None:
    """行の本文の記録にあるまとまりを指すリンクだけをまとまりのリンクにし、項目の ID は文字のまま出す。押すとこの画面を開いたままそのまとまりの差分の表示に切り替える（正常系）。"""
    # 準備
    url, _ = write_post_link_preview()
    page = open_preview(url)
    history_before = page.evaluate("history.length")
    open_review(page)
    body = f"{_row('C-1')} .review-body"
    # 検証（リンクは 1 つで、行の D-2 は文字のまま）
    assert page.eval_on_selector_all(
        f"{body} a.setlink", "links => links.map(a => a.textContent)"
    ) == ["V-2 の直し"]
    assert page.get_attribute(f"{body} a.setlink", "href") == "#diff=V-2"
    assert page.get_attribute(f"{body} a.setlink", "title") == "D-2 を直す"
    assert page.locator(f"{body} button").count() == 0
    assert page.inner_text(body) == "V-2 の直し は D-2 にも関わる"
    # 実行
    page.click(f"{body} a.setlink")
    page.wait_for_function(
        f"document.querySelector('{DIFF_CHIP_TITLE}')?.textContent.endsWith('D-2 を直す')",
        timeout=DIFF_SETTLE_MS,
    )
    # 検証（この画面は開いたまま）
    assert page.locator(REVIEW_HEAD).count() == 1
    assert hash_params(page)["diff"] == ["V-2"]
    assert page.evaluate("history.length") == history_before


def test_edit(served_review: tuple[str, Path], open_preview: OpenPreview) -> None:
    """「修正」で行の本文を入力欄に切り替え、直して「修正」を押すと本文に戻す（正常系）。"""
    # 準備
    url, root = served_review
    page = open_preview(url)
    open_review(page)
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを修正").click()
    field = f"{_row('C-1')} form.row-edit textarea"
    assert page.input_value(field) == "案 A にする"
    page.fill(field, "案 B にする")
    # 実行
    page.locator(f"{_row('C-1')} form.row-edit").get_by_role("button", name="修正", exact=True).click()
    page.wait_for_function(
        "document.querySelector(\"li[data-comment='C-1'] .review-body\")?.textContent.trim() === '案 B にする'",
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
    open_review(page)
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを修正").click()
    page.fill(f"{_row('C-1')} form.row-edit textarea", "   ")
    # 実行
    page.locator(f"{_row('C-1')} form.row-edit").get_by_role("button", name="修正", exact=True).click()
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
            fulfill_problem(route, 500, "comments.yaml を書けません")
            if route.request.method == "PATCH"
            else route.continue_()
        ),
    )
    open_preview(url)
    open_review(page)
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを修正").click()
    page.fill(f"{_row('C-1')} form.row-edit textarea", "案 B にする")
    # 実行
    page.locator(f"{_row('C-1')} form.row-edit").get_by_role("button", name="修正", exact=True).click()
    page.wait_for_selector(f"{_row('C-1')} form.row-edit .send-msg svg.icon", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.inner_text(f"{_row('C-1')} form.row-edit .send-msg") == "comments.yaml を書けません"
    assert page.input_value(f"{_row('C-1')} form.row-edit textarea") == "案 B にする"


def test_edit_when_cancelled(
    served_review: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """「キャンセル」と Esc で書き換えを捨てる。Esc では一覧を閉じない（正常系）。"""
    # 準備
    url, root = served_review
    page = open_preview(url)
    open_review(page)
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを修正").click()
    page.fill(f"{_row('C-1')} form.row-edit textarea", "捨てる")
    # 実行・検証（キャンセル）
    page.get_by_role("button", name="キャンセル").click()
    assert page.inner_text(f"{_row('C-1')} .review-body") == "案 A にする"
    # Esc
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを修正").click()
    page.fill(f"{_row('C-1')} form.row-edit textarea", "捨てる")
    page.press(f"{_row('C-1')} form.row-edit textarea", "Escape")
    assert page.inner_text(f"{_row('C-1')} .review-body") == "案 A にする"
    assert page.locator(f"{COMMENTS_PANEL}.open").count() == 1
    assert read_workspace_yaml(root, "comments.yaml")["items"][0]["body"] == "案 A にする"


def test_edit_when_started_in_detail(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """詳細パネルで書き換えている行は、一覧では本文だけを出して入力欄も「修正」「削除」も出さない（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url)
    open_review(page)
    _open_row_in_detail(page, "C-1")
    # 実行
    page.locator(review_row("aside.panel", "C-1")).get_by_role("button", name="D-1 へのコメントを修正").click()
    page.wait_for_selector(f"{review_row('aside.panel', 'C-1')} form.row-edit")
    # 検証
    assert page.locator(f"{_row('C-1')} form.row-edit").count() == 0
    assert page.locator(f"{_row('C-1')} .row-actions").count() == 0
    assert page.inner_text(f"{_row('C-1')} .review-body") == "案 A にする"
    assert page.locator(f"{_row('C-2')} .row-actions").count() == 1


def test_edit_when_started_in_list(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """一覧で書き換えている行は、詳細パネルでは本文だけを出して入力欄も「修正」「削除」も出さない（正常系）。"""
    # 準備
    url, _ = served_review_rows
    page = open_preview(url)
    open_review(page)
    _open_row_in_detail(page, "C-1")
    # 実行
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを修正").click()
    page.wait_for_selector(f"{_row('C-1')} form.row-edit")
    # 検証
    detail_row = review_row("aside.panel", "C-1")
    assert page.locator(f"{detail_row} form.row-edit").count() == 0
    assert page.locator(f"{detail_row} .row-actions").count() == 0
    assert page.inner_text(f"{detail_row} .review-body") == "案 A にする"
    assert page.locator(f"{review_row('aside.panel', 'C-2')} .row-actions").count() == 1


def test_edit_when_started_in_detail_while_editing_in_list(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """一覧で書き換えている間に詳細パネルで別の行の「修正」を押すと、一覧の書き換えを捨てる（正常系）。"""
    # 準備
    url, root = served_review_rows
    page = open_preview(url)
    open_review(page)
    _open_row_in_detail(page, "C-1")
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを修正").click()
    page.fill(f"{_row('C-1')} form.row-edit textarea", "捨てる")
    # 実行
    page.locator(review_row("aside.panel", "C-2")).get_by_role("button", name="D-1 へのコメントを修正").click()
    page.wait_for_selector(f"{review_row('aside.panel', 'C-2')} form.row-edit")
    # 検証
    assert page.locator(f"{_row('C-1')} form.row-edit").count() == 0
    assert page.inner_text(f"{_row('C-1')} .review-body") == "案 A にする"
    assert page.locator(f"{_row('C-1')} .row-actions").count() == 1
    assert page.locator(f"{_row('C-2')} form.row-edit").count() == 0
    assert page.locator(f"{_row('C-2')} .row-actions").count() == 0
    assert read_workspace_yaml(root, "comments.yaml")["items"][0]["body"] == "案 A にする"


def test_edit_when_started_in_list_while_editing_in_detail(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """詳細パネルで書き換えている間に一覧で別の行の「修正」を押すと、詳細パネルの書き換えを捨てる（正常系）。"""
    # 準備
    url, root = served_review_rows
    page = open_preview(url)
    open_review(page)
    _open_row_in_detail(page, "C-1")
    page.locator(review_row("aside.panel", "C-1")).get_by_role("button", name="D-1 へのコメントを修正").click()
    page.fill(f"{review_row('aside.panel', 'C-1')} form.row-edit textarea", "捨てる")
    # 実行
    page.locator(_row("C-2")).get_by_role("button", name="D-1 へのコメントを修正").click()
    page.wait_for_selector(f"{_row('C-2')} form.row-edit")
    # 検証
    detail_row = review_row("aside.panel", "C-1")
    assert page.locator(f"{detail_row} form.row-edit").count() == 0
    assert page.inner_text(f"{detail_row} .review-body") == "案 A にする"
    assert page.locator(f"{detail_row} .row-actions").count() == 1
    assert page.locator(f"{review_row('aside.panel', 'C-2')} form.row-edit").count() == 0
    assert page.locator(f"{review_row('aside.panel', 'C-2')} .row-actions").count() == 0
    assert read_workspace_yaml(root, "comments.yaml")["items"][0]["body"] == "案 A にする"


def test_edit_when_list_closed(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """一覧を閉じると、一覧で始めた書き換えを捨て、詳細パネルの行に「修正」「削除」を戻す（正常系）。"""
    # 準備
    url, root = served_review_rows
    page = open_preview(url)
    open_review(page)
    _open_row_in_detail(page, "C-1")
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを修正").click()
    page.fill(f"{_row('C-1')} form.row-edit textarea", "捨てる")
    # 実行
    page.get_by_role("button", name="コメントの一覧を閉じる").click()
    page.wait_for_function("!document.querySelector('aside.comments-panel.open')")
    # 検証
    detail_row = review_row("aside.panel", "C-1")
    assert page.locator(f"{detail_row} form.row-edit").count() == 0
    assert page.locator(f"{detail_row} .row-actions").count() == 1
    assert page.inner_text(f"{detail_row} .review-body") == "案 A にする"
    open_review(page)
    assert page.locator(f"{_row('C-1')} form.row-edit").count() == 0
    assert page.inner_text(f"{_row('C-1')} .review-body") == "案 A にする"
    assert read_workspace_yaml(root, "comments.yaml")["items"][0]["body"] == "案 A にする"


@pytest.mark.parametrize(
    "leave_selector",
    [
        pytest.param("aside.panel button[data-act='close']", id="close_panel"),
        pytest.param(f"{COMMENTS_PANEL} li[data-comment='C-3'] button.row-target", id="move_to_other_item"),
    ],
)
def test_edit_when_detail_left(
    served_review_rows: tuple[str, Path], open_preview: OpenPreview, leave_selector: str
) -> None:
    """詳細パネルで書き換えを始めた後に別の項目へ移るかパネルを閉じると、書き換えを捨て、一覧の本文だけの行を元の行に戻す（正常系）。"""
    # 準備
    url, root = served_review_rows
    page = open_preview(url)
    open_review(page)
    _open_row_in_detail(page, "C-1")
    page.locator(review_row("aside.panel", "C-1")).get_by_role("button", name="D-1 へのコメントを修正").click()
    page.fill(f"{review_row('aside.panel', 'C-1')} form.row-edit textarea", "捨てる")
    # 実行
    page.click(leave_selector)
    page.wait_for_selector(f"{_row('C-1')} .row-actions")
    # 検証
    assert page.locator(f"{_row('C-1')} form.row-edit").count() == 0
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
    open_review(page)
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
    open_review(page)
    page.locator(_row("C-1")).get_by_role("button", name="D-1 へのコメントを削除").click()
    page.wait_for_selector(f"{_row('C-1')}.removed", timeout=UPDATE_TIMEOUT_MS)
    # 実行
    page.get_by_role("button", name="コメントの一覧を閉じる").click()
    page.wait_for_function("!document.querySelector('aside.comments-panel.open')")
    open_review(page)
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
    open_review(page)
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
    open_review(page)
    # 実行
    page.locator(f"{COMMENTS_PANEL} .send-band").get_by_role("button", name="まとめて送る").click()
    page.wait_for_selector(f"{_row('C-1')} .row-stale", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.inner_text(f"{_row('C-1')} .row-stale span") == "D-9 がありません"
    assert page.get_by_role("button", name="箇所を外す").count() == 0


def test_empty(
    write_review_preview: WriteReviewPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """レビュー中の書き込みが 0 件のときは、印と「レビュー中の書き込みはありません。」を出し、送る帯は出さない（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("D-1"))
    page = open_preview(url)
    # 実行
    open_review(page)
    # 検証
    assert page.inner_text(f"{COMMENTS_PANEL} .comments-empty") == "レビュー中の書き込みはありません。"
    assert page.locator(f"{COMMENTS_PANEL} .comments-empty svg.icon").count() == 1
    assert page.locator(f"{COMMENTS_PANEL} .send-band").count() == 0


def test_narrow_width(served_review: tuple[str, Path], open_preview: OpenPreview, page: Page) -> None:
    """幅 900px 以下は画面の幅いっぱいに出し、行から開いた詳細パネルを閉じるとレビュー中の書き込みへ戻る（正常系）。"""
    # 準備
    url, _ = served_review
    page.set_viewport_size({"width": NARROW_WIDTH, "height": VIEWPORT_HEIGHT})
    open_preview(url)
    # 実行
    open_review(page)
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


@pytest.fixture
def served_replies(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_post: MakePost,
    make_thread: MakeThread,
) -> tuple[str, Path]:
    """オープンの TH-1 への返信 C-1・クローズの TH-2 への返信 C-2・D-1 への新しいスレッド C-3 を持つワークスペースの配信の URL とフォルダを返す。"""
    return write_review_preview(
        make_item("D-1"),
        threads=(
            make_thread(
                "TH-1",
                make_post("TH-1-1", author="ai", body="起票してよいですか", created="2026-10-12T01:00:00+00:00"),
                summary="起票の確認",
            ),
            make_thread(
                "TH-2",
                make_post("TH-2-1", read=True, taken="2026-10-12T00:30:00+00:00"),
                status="closed",
                summary="閉じた話",
            ),
        ),
        comments=(
            free_comment(make_comment("C-1", body="起票してよい", thread="TH-1")),
            free_comment(make_comment("C-2", body="了解", thread="TH-2")),
            make_comment("C-3", target="D-1", body="案 A にする"),
        ),
    )


def test_row_reply(served_replies: tuple[str, Path], open_preview: OpenPreview) -> None:
    """返信の行は、頭に「返信」と返信先のスレッドの状態の札と題を出し、押すとそのスレッドを開く（正常系）。"""
    # 準備
    url, _ = served_replies
    page = open_preview(url)
    open_review(page)
    # 検証
    assert page.inner_text(f"{_row('C-1')} .row-kind") == "返信"
    assert page.inner_text(f"{_row('C-1')} .row-target") == "オープン\n起票の確認"
    assert page.inner_text(f"{_row('C-3')} .row-kind") == "新しいスレッド"
    assert page.get_attribute(f"{_row('C-1')} input.row-check", "aria-label") == "TH-1 への返信を送る"
    assert page.locator(f"{_row('C-1')}").get_by_role("button", name="TH-1 への返信を修正").count() == 1
    assert page.locator(f"{_row('C-1')}").get_by_role("button", name="TH-1 への返信を削除").count() == 1
    # 実行
    page.click(f"{_row('C-1')} .row-head button.row-target")
    # 検証（スレッドの画面へ切り替わる）
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
    assert page.inner_text(f"{COMMENTS_PANEL} .th-heading") == "オープン\n起票の確認"


def test_row_blocked(served_replies: tuple[str, Path], open_preview: OpenPreview) -> None:
    """クローズのスレッドへの返信は、チェックを押せず、送る件数に入れず、理由とそのスレッドを開く入口を出す（正常系）。"""
    # 準備
    url, _ = served_replies
    page = open_preview(url)
    # 実行
    open_review(page)
    # 検証
    check = f"{_row('C-2')} input.row-check"
    assert page.is_disabled(check)
    assert not page.is_checked(check)
    assert page.inner_text(BAND_COUNT) == "2 / 2 件"
    assert (
        page.inner_text(f"{_row('C-2')} .row-blocked span")
        == "クローズのスレッドへの返信は送れません。オープンに戻すと送れます。"
    )
    # 実行（そのスレッドを開く）
    page.locator(f"{_row('C-2')} .row-blocked").get_by_role("button", name="スレッドを開く").click()
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
    # 検証
    assert page.inner_text(f"{COMMENTS_PANEL} .th-heading") == "クローズ\n閉じた話"
    assert page.get_by_role("button", name="オープンに戻す").count() == 1


def test_row_open_thread(served_replies: tuple[str, Path], open_preview: OpenPreview) -> None:
    """新しいスレッドの行の「スレッドを開く」で、まだ送っていないそのスレッドを開く（正常系）。"""
    # 準備
    url, _ = served_replies
    page = open_preview(url)
    open_review(page)
    # 実行
    page.locator(f"{_row('C-3')} .row-thread-open").get_by_role("button", name="スレッドを開く").click()
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
    # 検証
    assert page.inner_text(f"{COMMENTS_PANEL} .th-heading") == "レビュー中\n案 A にする"
    assert page.inner_text(f"{COMMENTS_PANEL} .th-closed-note") == "まだ送っていないスレッドです。"


def test_send_when_reply(
    served_replies: tuple[str, Path], open_preview: OpenPreview, call_tool: CallTool
) -> None:
    """返信はそのスレッドの書き込みに移り、クローズのスレッドへの返信は送らずレビュー中に残す（正常系）。"""
    # 準備
    url, root = served_replies
    page = open_preview(url)
    open_review(page)
    # 実行
    page.locator(f"{COMMENTS_PANEL} .send-band").get_by_role("button", name="まとめて送る").click()
    page.wait_for_selector(f"{BAND_RESULT}.sent", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.inner_text(BAND_RESULT).startswith("2 件を送りましたが、Claude Code には入力できませんでした（")
    assert page.eval_on_selector_all(
        f"{COMMENTS_PANEL} .comments-list li", "rows => rows.map(r => r.dataset.comment)"
    ) == ["C-2"]
    threads = {item["id"]: item for item in read_workspace_yaml(root, "threads.yaml")["items"]}
    assert [post["body"] for post in threads["TH-1"]["posts"]] == ["起票してよいですか", "起票してよい"]
    assert [post["body"] for post in threads["TH-2"]["posts"]] == ["TH-2-1の本文"]
    assert threads["TH-3"]["target"] == "D-1"


def test_row_selected_from_thread(
    served_replies: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """スレッドの画面から開いたときは、そのスレッドへの返信の行を選んだ見た目にする（正常系）。"""
    # 準備
    url, _ = served_replies
    page = open_preview(url)
    open_list_button = f"{COMMENTS_PANEL} ul.th-list > li:has(button[data-focus='thread:TH-1']) button.th-open"
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open")
    page.click(open_list_button)
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
    # 実行
    page.click(REVIEW_ENTRY)
    page.wait_for_selector(REVIEW_HEAD)
    # 検証
    assert page.eval_on_selector(_row("C-1"), "e => e.classList.contains('selected')") is True
    assert page.eval_on_selector(_row("C-3"), "e => e.classList.contains('selected')") is False
    # 戻るで、見ていたスレッドの画面へ戻る
    page.get_by_role("button", name="戻る").click()
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
    assert page.inner_text(f"{COMMENTS_PANEL} .th-heading") == "オープン\n起票の確認"


def test_fit_smallest(served_review: tuple[str, Path], open_preview: OpenPreview) -> None:
    """レビュー中の書き込みの画面は、幅 320px で横にスクロールせず、パネルと「まとめて送る」が表示幅の中にある（正常系）。"""
    # 準備
    url, _ = served_review
    page = open_preview(url, "#tab=decisions&view=table")
    set_smallest(page)
    # 実行
    open_review(page)
    # 検証
    assert_fits_smallest(
        page,
        (COMMENTS_PANEL, f"{COMMENTS_PANEL} button:has-text('まとめて送る')"),
        scope=COMMENTS_PANEL,
    )


# 畳む行の数（折り返した後の見た目の行）
FOLD_LINES = 5

# 改行で 8 行の本文と、2 行の本文
LONG_BODY = "\n".join(f"{number} 行目の気づき" for number in range(1, 9))
SHORT_BODY = "1 行目\n2 行目"

# 幅 390px の狭い画面
PHONE_VIEWPORT = {"width": 390, "height": 844}

# 本文の見た目の行の数（高さ ÷ 行の高さ）を返す
BODY_LINES_SCRIPT = """(selector) => {
    const body = document.querySelector(selector);
    return Math.round(body.getBoundingClientRect().height / parseFloat(getComputedStyle(body).lineHeight));
}"""

# 開閉のボタンの文字が 1 行に収まっているか（折り返すと文字の外接の四角が複数になる）
MORE_TEXT_RECTS_SCRIPT = "(selector) => document.querySelector(selector).getClientRects().length"


def _more(comment_id: str) -> str:
    """行の開閉のボタン（「続きを読む」「折りたたむ」）の選択子を返す。"""
    return f"{_row(comment_id)} button.review-more"


def _body_lines(page: Page, comment_id: str) -> int:
    """行の本文の見た目の行の数を返す。"""
    return int(page.evaluate(BODY_LINES_SCRIPT, f"{_row(comment_id)} .review-body"))


def _wait_more(page: Page, comment_id: str) -> None:
    """行の開閉のボタンが出る（本文を測り終える）まで待つ。"""
    page.wait_for_selector(_more(comment_id), state="visible")


@pytest.fixture
def served_long(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_post: MakePost,
    make_thread: MakeThread,
) -> tuple[str, Path]:
    """8 行の項目を指さない新しいスレッド C-1・8 行の返信 C-2・2 行の返信 C-3・2 行の D-1 への新しいスレッド C-4 を持つワークスペースの配信の URL とフォルダを返す。"""
    return write_review_preview(
        make_item("D-1"),
        threads=(
            make_thread(
                "TH-1",
                make_post("TH-1-1", author="ai", body="起票してよいですか", created="2026-10-12T01:00:00+00:00"),
                summary="起票の確認",
            ),
        ),
        comments=(
            free_comment(make_comment("C-1", body=LONG_BODY)),
            free_comment(make_comment("C-2", body=LONG_BODY, thread="TH-1")),
            free_comment(make_comment("C-3", body=SHORT_BODY, thread="TH-1")),
            make_comment("C-4", target="D-1", body=SHORT_BODY),
        ),
    )


def test_row_more(served_long: tuple[str, Path], open_preview: OpenPreview) -> None:
    """折り返した後の見た目の行で 5 行を超える本文は 5 行までに畳み、新しいスレッドの行では「スレッドを開く」と同じ行の先に、下向きの印の「続きを読む」を出す（正常系）。"""
    # 準備
    url, _ = served_long
    page = open_preview(url)
    # 実行
    open_review(page)
    _wait_more(page, "C-1")
    # 検証
    more = _more("C-1")
    assert page.inner_text(more) == "続きを読む"
    assert page.get_attribute(more, "aria-expanded") == "false"
    assert page.get_attribute(more, "aria-label") == "項目を指さないコメントの続きを読む"
    assert page.get_attribute(more, "aria-controls") == "review-body-C-1"
    assert page.eval_on_selector(f"{_row('C-1')} .review-body", "e => e.classList.contains('folded')") is True
    assert _body_lines(page, "C-1") == FOLD_LINES
    assert page.eval_on_selector_all(
        f"{_row('C-1')} .row-thread-open > button", "buttons => buttons.map(b => b.textContent.trim())"
    ) == ["続きを読む", "スレッドを開く"]
    assert page.locator(f"{more} svg.icon").count() == 1


def test_row_more_when_toggled(served_long: tuple[str, Path], open_preview: OpenPreview) -> None:
    """「続きを読む」で全文を開いて「折りたたむ」（上向きの印）に変え、もう一度押すと 5 行に畳み直す。ハッシュも履歴も変えない（正常系）。"""
    # 準備
    url, _ = served_long
    page = open_preview(url)
    open_review(page)
    _wait_more(page, "C-1")
    hash_before = page.evaluate("location.hash")
    history_before = page.evaluate("history.length")
    more = _more("C-1")
    # 実行（開く）
    page.click(more)
    # 検証
    assert page.inner_text(more) == "折りたたむ"
    assert page.get_attribute(more, "aria-expanded") == "true"
    assert page.get_attribute(more, "aria-label") == "項目を指さないコメントの本文を折りたたむ"
    assert page.eval_on_selector(f"{_row('C-1')} .review-body", "e => e.classList.contains('folded')") is False
    assert _body_lines(page, "C-1") == len(LONG_BODY.splitlines())
    # 実行（畳み直す）
    page.click(more)
    # 検証
    assert page.inner_text(more) == "続きを読む"
    assert page.get_attribute(more, "aria-expanded") == "false"
    assert _body_lines(page, "C-1") == FOLD_LINES
    assert page.evaluate("location.hash") == hash_before
    assert page.evaluate("history.length") == history_before


def test_row_more_when_reply(served_long: tuple[str, Path], open_preview: OpenPreview) -> None:
    """返信の行は、開閉のボタンだけの行を本文の下に出し、読み上げの名前を返信先のスレッドで言う（正常系）。"""
    # 準備
    url, _ = served_long
    page = open_preview(url)
    # 実行
    open_review(page)
    _wait_more(page, "C-2")
    # 検証
    assert page.inner_text(_more("C-2")) == "続きを読む"
    assert page.get_attribute(_more("C-2"), "aria-label") == "TH-1 への返信の続きを読む"
    assert page.eval_on_selector_all(
        f"{_row('C-2')} .review-more-row > *", "nodes => nodes.map(n => n.textContent.trim())"
    ) == ["続きを読む"]
    assert page.locator(f"{_row('C-2')} .row-thread-open").count() == 0
    assert page.get_by_role("button", name="スレッドを開く").count() == 2
    assert _body_lines(page, "C-2") == FOLD_LINES


def test_row_more_when_short(served_long: tuple[str, Path], open_preview: OpenPreview) -> None:
    """5 行以下の本文は畳まず、開閉のボタンも、返信の行のボタンだけの行も出さない（正常系）。"""
    # 準備
    url, _ = served_long
    page = open_preview(url)
    open_review(page)
    _wait_more(page, "C-1")
    # 検証
    for comment_id in ("C-3", "C-4"):
        assert page.is_visible(_more(comment_id)) is False
        assert page.eval_on_selector(f"{_row(comment_id)} .review-body", "e => e.classList.contains('folded')") is False
        assert _body_lines(page, comment_id) == len(SHORT_BODY.splitlines())
    # 返信の行は、ボタンだけの行ごと見えない
    assert page.is_visible(f"{_row('C-3')} .review-more-row") is False
    # 新しいスレッドの行は「スレッドを開く」だけを見せる
    assert page.eval_on_selector_all(
        f"{_row('C-4')} .row-thread-open > button:not([hidden])", "buttons => buttons.map(b => b.textContent.trim())"
    ) == ["スレッドを開く"]


def test_row_more_when_editing(served_long: tuple[str, Path], open_preview: OpenPreview) -> None:
    """本文を書き換えている行は畳まず、開閉のボタンも出さない（正常系）。"""
    # 準備
    url, _ = served_long
    page = open_preview(url)
    open_review(page)
    _wait_more(page, "C-1")
    # 実行
    page.get_by_role("button", name="項目を指さないコメントを修正").click()
    # 検証
    assert page.input_value(f"{_row('C-1')} form.row-edit textarea") == LONG_BODY
    assert page.locator(f"{_row('C-1')} .review-body").count() == 0
    assert page.is_visible(_more("C-1")) is False


def test_row_body_when_redrawn(served_long: tuple[str, Path], open_preview: OpenPreview) -> None:
    """開いた本文は、画面の描き直しと本文の書き換えをまたいで開いたまま保ち、パネルを閉じて開き直すと畳んだ状態に戻る（正常系）。"""
    # 準備
    url, _ = served_long
    page = open_preview(url)
    open_review(page)
    _wait_more(page, "C-1")
    page.click(_more("C-1"))
    assert page.inner_text(_more("C-1")) == "折りたたむ"
    # 実行（別の行のチェックで描き直す）
    page.uncheck(f"{_row('C-4')} input.row-check")
    # 検証
    _wait_more(page, "C-1")
    assert page.inner_text(_more("C-1")) == "折りたたむ"
    assert _body_lines(page, "C-1") == len(LONG_BODY.splitlines())
    # 実行（本文を書き換え始めて、やめる）
    page.get_by_role("button", name="項目を指さないコメントを修正").click()
    page.get_by_role("button", name="キャンセル").click()
    # 検証
    _wait_more(page, "C-1")
    assert page.inner_text(_more("C-1")) == "折りたたむ"
    assert _body_lines(page, "C-1") == len(LONG_BODY.splitlines())
    # 実行（パネルを閉じて開き直す）
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open", state="detached")
    open_review(page)
    _wait_more(page, "C-1")
    # 検証
    assert page.inner_text(_more("C-1")) == "続きを読む"
    assert _body_lines(page, "C-1") == FOLD_LINES


def test_row_more_when_narrow(served_long: tuple[str, Path], open_preview: OpenPreview, page: Page) -> None:
    """幅 390px でも見た目の 5 行で畳み、「続きを読む」の文字をボタンの中で折り返さない（正常系）。"""
    # 準備
    url, _ = served_long
    page.set_viewport_size(PHONE_VIEWPORT)
    open_preview(url)
    # 実行
    open_review(page)
    _wait_more(page, "C-2")
    # 検証
    for comment_id in ("C-1", "C-2"):
        assert _body_lines(page, comment_id) == FOLD_LINES
        assert page.evaluate(MORE_TEXT_RECTS_SCRIPT, f"{_more(comment_id)} span") == 1
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


# 行の上端を一覧のスクロール領域の上端より 24px 上へ隠す
HIDE_ROW_TOP_SCRIPT = """(selector) => {
    const row = document.querySelector(selector);
    const scroller = document.querySelector('aside.comments-panel .comments-body');
    scroller.scrollTop += row.getBoundingClientRect().top - scroller.getBoundingClientRect().top + 24;
}"""

# 行の上端と下端が、一覧のスクロール領域の上端と下端からどれだけ内側かを返す（負は外へ隠れている）
ROW_INSIDE_SCRIPT = """(selector) => {
    const row = document.querySelector(selector).getBoundingClientRect();
    const scroller = document.querySelector('aside.comments-panel .comments-body').getBoundingClientRect();
    return { top: row.top - scroller.top, bottom: scroller.bottom - row.bottom };
}"""

# 画面の高さ（開いた行の全体が一覧のスクロール領域に入る高さ）
SHORT_VIEWPORT = {"width": 1280, "height": 560}


def test_row_more_when_folded_again(served_long: tuple[str, Path], open_preview: OpenPreview, page: Page) -> None:
    """「折りたたむ」で畳み直すと、上端が一覧から外れかけていた行を一覧の中へ寄せる（正常系）。"""
    # 準備
    url, _ = served_long
    page.set_viewport_size(SHORT_VIEWPORT)
    open_preview(url)
    open_review(page)
    _wait_more(page, "C-2")
    page.click(_more("C-2"))
    page.evaluate(HIDE_ROW_TOP_SCRIPT, _row("C-2"))
    assert page.evaluate(ROW_INSIDE_SCRIPT, _row("C-2"))["top"] < 0
    # 実行
    page.click(_more("C-2"))
    # 検証
    inside = page.evaluate(ROW_INSIDE_SCRIPT, _row("C-2"))
    assert inside["top"] >= -1
    assert inside["bottom"] >= -1
