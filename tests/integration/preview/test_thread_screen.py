"""画面設計『スレッド』（スレッド 1 件の画面）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, Route
from preview_comment_helpers import (
    COMMENTS_BUTTON,
    COMMENTS_PANEL,
    DRAFT_WAIT_MS,
    REVIEW_ENTRY,
    REVIEW_HEAD,
    UPDATE_TIMEOUT_MS,
    free_comment,
    fulfill_problem,
    open_list,
    open_thread,
    read_workspace_yaml,
    review_row,
    thread_row,
    wait_until_focused,
)
from preview_fixture_types import OpenPreview, WriteReviewPreview
from preview_post_link_helpers import DIFF_CHIP_TITLE, DIFF_SETTLE_MS, hash_params
from preview_stack_helpers import DETAIL_HASH, has_left_front, is_inert, open_narrow, wait_front
from workspace_fixtures import (
    CallTool,
    MakeComment,
    MakeDraft,
    MakeItem,
    MakePost,
    MakeThread,
)

# 見出し・向けた項目・タグ・書き込みの並び
HEADING = f"{COMMENTS_PANEL} .th-heading"
TARGET = f"{COMMENTS_PANEL} .th-meta button.row-target"
TAGS = f"{COMMENTS_PANEL} .th-meta .th-tag"
POSTS = f"{COMMENTS_PANEL} ol.posts > li"

# 状態を変えるボタンと理由の入力
STATUS_BUTTON = f"{COMMENTS_PANEL} button[data-focus='status']"
REASON_FORM = f"{COMMENTS_PANEL} form.th-reason"
REASON_TEXTAREA = f"{REASON_FORM} textarea"
REASON_OK = f"{REASON_FORM} button[data-focus='reason-ok']"
REASON_CANCEL = f"{REASON_FORM} button[data-focus='reason-cancel']"
ACTION_MSG = f"{COMMENTS_PANEL} .th-action-msg"

# 返信の入力と、クローズ・未送信の知らせ
REPLY_FORM = f"{COMMENTS_PANEL} form.reply"
REPLY_TEXTAREA = f"{REPLY_FORM} textarea"
REPLY_SEND = f"{REPLY_FORM} button[data-focus='reply-send']"
REPLY_MSG = f"{REPLY_FORM} .send-msg"
CLOSED_NOTE = f"{COMMENTS_PANEL} .th-closed-note"

# 利用者がクローズにした記録
USER_CLOSED = {
    "kind": "closed",
    "author": "user",
    "reason": "案 A で決着",
    "created": "2026-10-12T04:00:00+00:00",
}

# パネルの動きが終わってから、書き込みの頭の中に「修正」「削除」の組が収まっているかを返す
POST_ACTIONS_IN_HEAD_JS = """async (selector) => {
    await Promise.all(document.getAnimations().map(animation => animation.finished));
    const head = document.querySelector(`${selector} .post-head`).getBoundingClientRect();
    const actions = document.querySelector(`${selector} .post-head .row-actions`).getBoundingClientRect();
    return actions.left >= head.left && actions.right <= head.right && actions.top >= head.top && actions.bottom <= head.bottom;
}"""


def _open_closed_thread(page: Page, thread_id: str) -> None:
    """一覧を「クローズ」で絞ってから、スレッドの行を押してスレッドの画面を開く。"""
    open_list(page)
    page.click(f"{COMMENTS_PANEL} .talk-filter button[data-focus='filter:closed']")
    page.click(f"{thread_row(thread_id)} button.th-open")
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")


def _thread_in_yaml(root: Path, thread_id: str) -> dict[str, object]:
    """threads.yaml から、指定した ID のスレッドを返す。"""
    items = read_workspace_yaml(root, "threads.yaml")["items"]
    return next(item for item in items if item["id"] == thread_id)


@pytest.fixture
def served_thread(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_post: MakePost,
    make_thread: MakeThread,
) -> tuple[str, Path]:
    """D-1 に向いた TH-1（オープン・タグ 画面と調査・AI と利用者の書き込み 2 件）と、閉じた TH-2（利用者がクローズにした記録つき）と、TH-1 へのレビュー中の返信 C-1 を持つワークスペースの配信の URL とフォルダを返す。"""
    return write_review_preview(
        make_item("D-1", title="最初の問い"),
        threads=(
            make_thread(
                "TH-1",
                make_post("TH-1-1", author="ai", body="D-1 の案を決めたい", created="2026-10-12T01:00:00+00:00"),
                make_post("TH-1-2", read=True, body="案 A にする", created="2026-10-12T02:00:00+00:00"),
                summary="案の相談",
                tags=["画面", "調査"],
                target="D-1",
            ),
            make_thread(
                "TH-2",
                make_post("TH-2-1", read=True, body="閉じた質問", created="2026-10-12T03:00:00+00:00"),
                status="closed",
                summary="閉じた話",
                events=[USER_CLOSED],
            ),
        ),
        comments=(free_comment(make_comment("C-1", body="了解です D-1", thread="TH-1")),),
    )


def test_heading(served_thread: tuple[str, Path], open_preview: OpenPreview) -> None:
    """状態の札と題を見出しに、向けた項目とタグを題の下に出し、書き込みを日時の順に並べて返信を後ろに足す（正常系）。"""
    # 準備
    url, _ = served_thread
    page = open_preview(url)
    # 実行
    open_thread(page, "TH-1")
    # 検証
    assert page.inner_text(HEADING) == "オープン\n案の相談"
    assert page.inner_text(TARGET) == "D-1\n最初の問い"
    assert page.eval_on_selector_all(TAGS, "tags => tags.map(t => t.textContent.trim())") == ["画面", "調査"]
    assert page.eval_on_selector_all(
        f"{POSTS} .post-author", "authors => authors.map(a => a.textContent)"
    ) == ["AI", "あなた", "あなた"]
    assert page.get_attribute(f"{POSTS}:nth-child(3)", "data-comment") == "C-1"
    assert "pending" in (page.get_attribute(f"{POSTS}:nth-child(3)", "class") or "").split()


def test_back(served_thread: tuple[str, Path], open_preview: OpenPreview) -> None:
    """「一覧へ戻る」で一覧へ戻り、開いていた行へフォーカスを戻す。入力欄の外での Esc も同じ（履歴に積まない）（正常系）。"""
    # 準備
    url, _ = served_thread
    page = open_preview(url)
    history_length = page.evaluate("history.length")
    open_thread(page, "TH-1")
    # 実行（ボタン）
    page.get_by_role("button", name="一覧へ戻る").click()
    # 検証
    page.wait_for_selector(f"{COMMENTS_PANEL} .talk-filter")
    wait_until_focused(page, f"{thread_row('TH-1')} button.th-open")
    # 実行（Esc）
    page.click(f"{thread_row('TH-1')} button.th-open")
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_selector(f"{COMMENTS_PANEL} .talk-filter")
    assert page.locator(f"{COMMENTS_PANEL}.open").count() == 1
    assert page.evaluate("history.length") == history_length


def test_back_when_typing(served_thread: tuple[str, Path], open_preview: OpenPreview) -> None:
    """返信の入力欄にフォーカスがあるときの Esc は入力から外れるだけで、一覧へ戻らない（正常系）。"""
    # 準備
    url, _ = served_thread
    page = open_preview(url)
    open_thread(page, "TH-1")
    page.click(REPLY_TEXTAREA)
    # 実行
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_function(
        "selector => document.activeElement !== document.querySelector(selector)", arg=REPLY_TEXTAREA
    )
    assert page.locator(f"{COMMENTS_PANEL} .th-head").count() == 1
    assert page.locator(f"{COMMENTS_PANEL} .talk-filter").count() == 0


def test_target(served_thread: tuple[str, Path], open_preview: OpenPreview) -> None:
    """向けた項目を押すと、パネルを開いたまま右にその項目の詳細パネルを開く（正常系）。"""
    # 準備
    url, _ = served_thread
    page = open_preview(url)
    open_thread(page, "TH-1")
    # 実行
    page.click(TARGET)
    # 検証
    page.wait_for_selector("aside.panel.open")
    assert page.locator(f"{COMMENTS_PANEL}.open").count() == 1


def test_narrow_back_by_escape_in_front_of_detail(
    served_thread: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """幅 390px で一覧が詳細パネルの前に出ているときの Esc は、スレッドの画面から一覧へ戻り、詳細パネルは閉じない（正常系）。"""
    # 準備
    url, _ = served_thread
    page = open_preview(url, DETAIL_HASH)
    open_narrow(page)
    open_thread(page, "TH-1")
    wait_front(page, "comments")
    # 実行
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_selector(f"{COMMENTS_PANEL} .talk-filter")
    wait_front(page, "comments")
    assert page.locator(f"{COMMENTS_PANEL} .th-head").count() == 0
    assert page.locator("aside.panel.open").count() == 1
    assert is_inert(page, "detail") is True


def test_narrow_escape_when_typing_in_front_of_detail(
    served_thread: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """幅 390px で一覧が詳細パネルの前に出ているとき、返信の入力欄にフォーカスがある Esc は入力から外れるだけで、スレッドの画面も詳細パネルも閉じない（正常系）。"""
    # 準備
    url, _ = served_thread
    page = open_preview(url, DETAIL_HASH)
    open_narrow(page)
    open_thread(page, "TH-1")
    wait_front(page, "comments")
    page.click(REPLY_TEXTAREA)
    # 実行
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_function(
        "selector => document.activeElement !== document.querySelector(selector)", arg=REPLY_TEXTAREA
    )
    wait_front(page, "comments")
    assert page.locator(f"{COMMENTS_PANEL} .th-head").count() == 1
    assert page.locator("aside.panel.open").count() == 1


def test_narrow_target_opens_detail_in_front(
    served_thread: tuple[str, Path], open_preview: OpenPreview
) -> None:
    """幅 390px で、いま開いている項目を向けたスレッドの向けた項目を押すと、詳細パネルが一覧の前に出て一覧が `inert` になる（正常系）。"""
    # 準備
    url, _ = served_thread
    page = open_preview(url, DETAIL_HASH)
    open_narrow(page)
    open_thread(page, "TH-1")
    wait_front(page, "comments")
    # 実行
    page.click(TARGET)
    # 検証
    wait_front(page, "detail")
    assert page.inner_text("aside.panel .d-title") == "最初の問い"
    assert has_left_front(page) is False
    assert is_inert(page, "comments") is True
    assert is_inert(page, "detail") is False


def test_post_id_link(served_thread: tuple[str, Path], open_preview: OpenPreview) -> None:
    """本文の中の記録にある項目の ID は、その項目を開くボタンにする（正常系）。"""
    # 準備
    url, _ = served_thread
    page = open_preview(url)
    open_thread(page, "TH-1")
    link = f"{POSTS}:nth-child(1) button.idlink"
    # 検証
    assert page.inner_text(link) == "D-1"
    assert page.get_attribute(link, "title") == "最初の問い"
    # 実行
    page.click(link)
    # 検証
    page.wait_for_selector("aside.panel.open")


def test_post_change_set_link(
    write_post_link_preview: WriteReviewPreview, open_preview: OpenPreview, page: Page
) -> None:
    """本文の中の記録にあるまとまりを指すリンクは、まとまりの説明を title に持つリンクにし、押すと（Enter でも）スレッドの画面を開いたままそのまとまりの差分の表示に切り替える。レビュー中の返信の中でも同じ（正常系）。"""
    # 準備
    url, _ = write_post_link_preview()
    open_preview(url)
    open_thread(page, "TH-1")
    history_before = page.evaluate("history.length")
    link = f"{POSTS}:nth-child(1) .post-body a.setlink"
    # 検証（読み上げの名前は文言、href はまとまりの ID、title はまとまりの説明）
    assert page.eval_on_selector_all(link, "links => links.map(a => a.textContent)") == [
        "D-1 を直した",
        "他の引数つき",
    ]
    assert page.get_attribute(f"{link} >> nth=0", "href") == "#diff=V-1"
    assert page.get_attribute(f"{link} >> nth=0", "title") == "D-1 を直す"
    assert page.get_by_role("link", name="D-1 を直した").count() == 1
    # 実行（Enter で押す）
    page.focus(f"{link} >> nth=0")
    page.keyboard.press("Enter")
    page.wait_for_function(
        f"document.querySelector('{DIFF_CHIP_TITLE}')?.textContent.endsWith('D-1 を直す')",
        timeout=DIFF_SETTLE_MS,
    )
    # 検証（スレッドの画面は開いたまま）
    assert page.locator(f"{COMMENTS_PANEL}.open").count() == 1
    assert page.locator(HEADING).count() == 1
    assert hash_params(page)["diff"] == ["V-1"]
    assert page.evaluate("history.length") == history_before
    # 実行（レビュー中の返信の中のリンクを押す）
    reply = f"{review_row(COMMENTS_PANEL, 'C-1')} .post-body"
    page.click(f"{reply} a.setlink")
    page.wait_for_function(
        f"document.querySelector('{DIFF_CHIP_TITLE}')?.textContent.endsWith('D-2 を直す')",
        timeout=DIFF_SETTLE_MS,
    )
    # 検証（リンクの外の D-2 は項目を開くボタンのまま）
    assert page.inner_text(f"{reply} a.setlink") == "V-2 の直し"
    assert page.locator(f"{reply} a.setlink button").count() == 0
    assert page.eval_on_selector_all(
        f"{reply} button.idlink", "buttons => buttons.map(b => b.textContent)"
    ) == ["D-2"]
    assert page.locator(HEADING).count() == 1
    assert hash_params(page)["diff"] == ["V-2"]
    assert page.evaluate("history.length") == history_before


def test_status_close(served_thread: tuple[str, Path], open_preview: OpenPreview) -> None:
    """「クローズにする」で理由の入力を出して入力欄へフォーカスを移し、確定で変えた状態と理由を 1 回で書いて描き直す（正常系）。"""
    # 準備
    url, root = served_thread
    page = open_preview(url)
    open_thread(page, "TH-1")
    assert page.inner_text(STATUS_BUTTON) == "クローズにする"
    # 実行
    page.click(STATUS_BUTTON)
    page.wait_for_selector(REASON_FORM)
    # 検証（入力）
    assert page.locator(STATUS_BUTTON).count() == 0
    assert page.inner_text(f"{REASON_FORM} label") == "理由（任意）"
    wait_until_focused(page, REASON_TEXTAREA)
    # 実行（確定）
    page.fill(REASON_TEXTAREA, "案 A で決着")
    page.click(REASON_OK)
    # 検証
    page.wait_for_selector(REASON_FORM, state="detached", timeout=UPDATE_TIMEOUT_MS)
    page.wait_for_function(
        "selector => document.querySelector(selector)?.textContent.includes('クローズ')",
        arg=HEADING,
        timeout=UPDATE_TIMEOUT_MS,
    )
    assert page.inner_text(HEADING) == "クローズ\n案の相談"
    assert page.inner_text(CLOSED_NOTE) == "クローズにしたスレッドです。"
    assert page.locator(REPLY_FORM).count() == 0
    assert page.inner_text(STATUS_BUTTON) == "オープンに戻す"
    wait_until_focused(page, STATUS_BUTTON)
    event = f"{POSTS}.th-event"
    assert page.inner_text(f"{event} .th-event-line span") == "あなたがクローズにしました"
    assert page.inner_text(f"{event} .th-event-reason") == "案 A で決着"
    thread = _thread_in_yaml(root, "TH-1")
    assert (thread["status"], thread["events"][-1]["reason"]) == ("closed", "案 A で決着")


def test_status_reopen(served_thread: tuple[str, Path], open_preview: OpenPreview) -> None:
    """クローズのスレッドは「オープンに戻す」で戻し、理由が空白だけなら理由なしで書く。返信の入力が戻る（正常系）。"""
    # 準備
    url, root = served_thread
    page = open_preview(url)
    _open_closed_thread(page, "TH-2")
    assert page.inner_text(STATUS_BUTTON) == "オープンに戻す"
    # 実行
    page.click(STATUS_BUTTON)
    page.fill(REASON_TEXTAREA, "   ")
    page.click(REASON_OK)
    # 検証
    page.wait_for_selector(REPLY_FORM, timeout=UPDATE_TIMEOUT_MS)
    assert page.inner_text(HEADING) == "オープン\n閉じた話"
    thread = _thread_in_yaml(root, "TH-2")
    assert (thread["status"], thread["events"][-1]["kind"], thread["events"][-1]["reason"]) == (
        "open",
        "reopened",
        None,
    )


def test_status_cancel(served_thread: tuple[str, Path], open_preview: OpenPreview) -> None:
    """「キャンセル」と入力欄の Esc で理由の入力を閉じ、「状態を変える」へフォーカスを戻す。一覧へは戻らず、何も書かない（正常系）。"""
    # 準備
    url, root = served_thread
    page = open_preview(url)
    open_thread(page, "TH-1")
    threads_file = root / ".mindstella" / "threads.yaml"
    before = threads_file.read_bytes()
    # 実行（キャンセル）
    page.click(STATUS_BUTTON)
    page.click(REASON_CANCEL)
    # 検証
    page.wait_for_selector(REASON_FORM, state="detached")
    wait_until_focused(page, STATUS_BUTTON)
    # 実行（Esc）
    page.click(STATUS_BUTTON)
    wait_until_focused(page, REASON_TEXTAREA)
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_selector(REASON_FORM, state="detached")
    wait_until_focused(page, STATUS_BUTTON)
    assert page.locator(f"{COMMENTS_PANEL} .th-head").count() == 1
    assert threads_file.read_bytes() == before


def test_status_ctrl_enter(served_thread: tuple[str, Path], open_preview: OpenPreview) -> None:
    """理由の入力欄の Ctrl+Enter で確定する（正常系）。"""
    # 準備
    url, _ = served_thread
    page = open_preview(url)
    open_thread(page, "TH-1")
    page.click(STATUS_BUTTON)
    page.fill(REASON_TEXTAREA, "決着")
    # 実行
    page.press(REASON_TEXTAREA, "Control+Enter")
    # 検証
    page.wait_for_selector(CLOSED_NOTE, timeout=UPDATE_TIMEOUT_MS)


def test_status_failed(served_thread: tuple[str, Path], open_preview: OpenPreview, page: Page) -> None:
    """状態を変えられなかったときは理由を出して、理由の入力は開いたまま残す。次に確定すると消す（異常系）。"""
    # 準備
    url, _ = served_thread
    page.route("**/api/threads/TH-1", lambda route: fulfill_problem(route, 500, "書き込めませんでした"))
    open_preview(url)
    open_thread(page, "TH-1")
    page.click(STATUS_BUTTON)
    page.fill(REASON_TEXTAREA, "決着")
    # 実行
    page.click(REASON_OK)
    # 検証
    page.wait_for_selector(ACTION_MSG, timeout=UPDATE_TIMEOUT_MS)
    assert page.get_attribute(ACTION_MSG, "role") == "alert"
    assert page.inner_text(ACTION_MSG) == "クローズにできませんでした。書き込めませんでした"
    assert page.input_value(REASON_TEXTAREA) == "決着"
    # 実行（次に確定する）
    page.unroute("**/api/threads/TH-1")
    page.click(REASON_OK)
    # 検証
    page.wait_for_selector(ACTION_MSG, state="detached", timeout=UPDATE_TIMEOUT_MS)


def test_status_unreachable(served_thread: tuple[str, Path], open_preview: OpenPreview, page: Page) -> None:
    """サーバーに届かないときは、立ち上げ直しの案内を出す（異常系）。"""
    # 準備
    url, _ = served_thread
    page.route("**/api/threads/TH-2", lambda route: route.abort())
    open_preview(url)
    _open_closed_thread(page, "TH-2")
    page.click(STATUS_BUTTON)
    # 実行
    page.click(REASON_OK)
    # 検証
    page.wait_for_selector(ACTION_MSG, timeout=UPDATE_TIMEOUT_MS)
    assert (
        page.inner_text(ACTION_MSG)
        == "オープンに戻せませんでした。サーバーが止まっています。立ち上げ直してから押してください。"
    )


def test_reply(served_thread: tuple[str, Path], open_preview: OpenPreview) -> None:
    """返信を溜めると入力欄を空にして書き込みの並びの末尾へ足し、コメントのボタンと「レビュー中」の件数を描き直す。この画面に留まる（正常系）。"""
    # 準備
    url, root = served_thread
    page = open_preview(url)
    open_thread(page, "TH-1")
    assert page.is_disabled(REPLY_SEND)
    # 実行
    page.fill(REPLY_TEXTAREA, "続きは D-1 で")
    page.click(REPLY_SEND)
    # 検証
    page.wait_for_selector(f"{POSTS}[data-comment='C-2']", timeout=UPDATE_TIMEOUT_MS)
    assert page.input_value(REPLY_TEXTAREA) == ""
    assert page.eval_on_selector_all(POSTS, "posts => posts.at(-1).dataset.comment") == "C-2"
    assert page.inner_text(REPLY_MSG) == "レビューに追加しました（レビュー中 2 件）。"
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "2"
    assert page.locator(f"{COMMENTS_PANEL} .th-head").count() == 1
    saved = read_workspace_yaml(root, "comments.yaml")["items"][-1]
    assert (saved["id"], saved["thread"], saved["body"]) == ("C-2", "TH-1", "続きは D-1 で")
    assert "target" not in saved


def test_reply_when_ctrl_enter(served_thread: tuple[str, Path], open_preview: OpenPreview) -> None:
    """Ctrl+Enter でも溜める。空白だけの間は溜めない（正常系）。"""
    # 準備
    url, _ = served_thread
    page = open_preview(url)
    open_thread(page, "TH-1")
    page.fill(REPLY_TEXTAREA, "   ")
    page.press(REPLY_TEXTAREA, "Control+Enter")
    assert page.locator(f"{POSTS}[data-comment='C-2']").count() == 0
    # 実行
    page.fill(REPLY_TEXTAREA, "了解")
    page.press(REPLY_TEXTAREA, "Control+Enter")
    # 検証
    page.wait_for_selector(f"{POSTS}[data-comment='C-2']", timeout=UPDATE_TIMEOUT_MS)


def test_reply_failed(served_thread: tuple[str, Path], open_preview: OpenPreview, page: Page) -> None:
    """溜められなかったときは理由を出し、入力欄の中身を残す（異常系）。"""
    # 準備
    url, _ = served_thread
    page.route(
        "**/api/comments",
        lambda route: fulfill_problem(route, 409, "クローズのスレッドです")
        if route.request.method == "POST"
        else route.continue_(),
    )
    open_preview(url)
    open_thread(page, "TH-1")
    page.fill(REPLY_TEXTAREA, "続き")
    # 実行
    page.click(REPLY_SEND)
    # 検証
    page.wait_for_function(
        "selector => document.querySelector(selector)?.textContent.includes('追加できませんでした')",
        arg=REPLY_MSG,
        timeout=UPDATE_TIMEOUT_MS,
    )
    assert page.inner_text(REPLY_MSG) == "レビューに追加できませんでした。クローズのスレッドです"
    assert page.input_value(REPLY_TEXTAREA) == "続き"


def test_reply_draft(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    make_draft: MakeDraft,
) -> None:
    """スレッドごとの書きかけを入力欄に戻し、入力が止まったときに thread ごとに保つ（正常系）。"""
    # 準備
    url, root = write_review_preview(
        make_item("D-1"),
        threads=(
            make_thread("TH-1", make_post("TH-1-1", author="ai"), summary="一つ目"),
            make_thread("TH-2", make_post("TH-2-1", author="ai"), summary="二つ目"),
        ),
        drafts=(free_comment(make_draft(thread="TH-2", body="二つ目の書きかけ")),),
    )
    page = open_preview(url)
    open_thread(page, "TH-1")
    assert page.input_value(REPLY_TEXTAREA) == ""
    # 実行（入力が止まる）
    page.fill(REPLY_TEXTAREA, "一つ目の書きかけ")
    page.wait_for_timeout(DRAFT_WAIT_MS)
    # 検証
    drafts = read_workspace_yaml(root, "drafts.yaml")["items"]
    assert sorted((draft["thread"], draft["body"]) for draft in drafts) == [
        ("TH-1", "一つ目の書きかけ"),
        ("TH-2", "二つ目の書きかけ"),
    ]
    # 実行（一覧を経て別のスレッドへ）
    page.get_by_role("button", name="一覧へ戻る").click()
    page.click(f"{thread_row('TH-2')} button.th-open")
    page.wait_for_selector(REPLY_TEXTAREA)
    # 検証
    assert page.input_value(REPLY_TEXTAREA) == "二つ目の書きかけ"


def test_closed(served_thread: tuple[str, Path], open_preview: OpenPreview) -> None:
    """クローズのスレッドは返信の入力の代わりに知らせを出し、利用者の状態の記録を日時の順に並べる（正常系）。"""
    # 準備
    url, _ = served_thread
    page = open_preview(url)
    # 実行
    _open_closed_thread(page, "TH-2")
    # 検証
    assert page.inner_text(HEADING) == "クローズ\n閉じた話"
    assert page.inner_text(CLOSED_NOTE) == "クローズにしたスレッドです。"
    assert page.locator(REPLY_FORM).count() == 0
    assert page.get_attribute(f"{POSTS}:nth-child(2)", "data-event") == "closed"
    assert page.inner_text(f"{POSTS}:nth-child(2) .th-event-line span") == "あなたがクローズにしました"


def test_pending_thread(
    write_review_preview: WriteReviewPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
) -> None:
    """まだ送っていない新しいスレッドは、最初の書き込みをレビュー中の形で出し、状態を変えるボタンと返信の入力を出さず、知らせを出す（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("D-1", title="最初の問い"),
        comments=(make_comment("C-1", target="D-1", body="案 A にする"),),
    )
    page = open_preview(url)
    # 実行
    open_list(page)
    page.click(f"{thread_row('new:C-1')} button.th-open")
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
    # 検証
    assert page.inner_text(HEADING) == "レビュー中\n案 A にする"
    assert page.inner_text(TARGET) == "D-1\n最初の問い"
    assert page.locator(STATUS_BUTTON).count() == 0
    assert page.locator(REPLY_FORM).count() == 0
    assert page.inner_text(CLOSED_NOTE) == "まだ送っていないスレッドです。"
    assert page.locator(f"{POSTS}[data-comment='C-1'].pending").count() == 1


def test_pending_post_edit(served_thread: tuple[str, Path], open_preview: OpenPreview) -> None:
    """レビュー中の返信を「修正」で書き換え、「削除」で消して「元に戻す」で戻す（正常系）。"""
    # 準備
    url, root = served_thread
    page = open_preview(url)
    open_thread(page, "TH-1")
    row = f"{POSTS}[data-comment='C-1']"
    # 実行（修正）
    page.locator(row).get_by_role("button", name="TH-1 への返信を修正").click()
    page.fill(f"{row} textarea", "直した返信")
    page.click(f"{row} form.row-edit button[type='submit']")
    # 検証
    page.wait_for_function(
        "selector => document.querySelector(selector)?.textContent.includes('直した返信')",
        arg=row,
        timeout=UPDATE_TIMEOUT_MS,
    )
    assert read_workspace_yaml(root, "comments.yaml")["items"][0]["body"] == "直した返信"
    # 実行（削除）
    page.locator(row).get_by_role("button", name="TH-1 への返信を削除").click()
    # 検証
    removed = f"{COMMENTS_PANEL} ol.posts [role='status']"
    page.wait_for_selector(removed, timeout=UPDATE_TIMEOUT_MS)
    assert page.inner_text(removed) == "コメントを削除しました。"
    # 実行（元に戻す）
    page.get_by_role("button", name="元に戻す").click()
    # 検証
    page.wait_for_selector(row, timeout=UPDATE_TIMEOUT_MS)


@pytest.mark.parametrize("width", [390, 720])
def test_pending_post_actions_in_head_when_narrow(
    served_thread: tuple[str, Path], open_preview: OpenPreview, width: int
) -> None:
    """幅 720px 以下でも、レビュー中の返信の「修正」「削除」を書き込みの頭の中に置く（正常系）。"""
    # 準備
    url, _ = served_thread
    page = open_preview(url)
    open_thread(page, "TH-1")
    # 実行
    page.set_viewport_size({"width": width, "height": 700})
    # 検証
    assert page.evaluate(POST_ACTIONS_IN_HEAD_JS, f"{POSTS}[data-comment='C-1']") is True


def test_updated_by_change(
    served_thread: tuple[str, Path], open_preview: OpenPreview, call_tool: CallTool
) -> None:
    """書き換えの知らせが届いたら、スレッドを読み直して AI の返信と AI が状態を変えた記録を並びに足し、入力中の返信は保つ（正常系）。"""
    # 準備
    url, root = served_thread
    page = open_preview(url)
    open_thread(page, "TH-1")
    page.fill(REPLY_TEXTAREA, "入力途中")
    # 実行（AI の返信が並んでも、入力中の返信は保つ）
    call_tool("reply", workspace=str(root), id="TH-1", body="AI の返信です", summary="案の相談", take=True)
    page.wait_for_selector(f"{POSTS}:has-text('AI の返信です')", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.input_value(REPLY_TEXTAREA) == "入力途中"
    # 実行
    call_tool("set_thread_status", workspace=str(root), id="TH-1", status="closed", reason="了解を受けた")
    # 検証
    page.wait_for_function(
        "selector => document.querySelector(selector)?.textContent.includes('クローズ')",
        arg=HEADING,
        timeout=UPDATE_TIMEOUT_MS,
    )
    assert page.locator(f"{POSTS}:has-text('AI の返信です')").count() == 1
    assert page.inner_text(f"{POSTS}.th-event.ai .th-event-line span") == "AI がクローズにしました"
    assert page.inner_text(f"{POSTS}.th-event.ai .th-event-reason") == "了解を受けた"


def test_review_entry_from_thread(served_thread: tuple[str, Path], open_preview: OpenPreview) -> None:
    """スレッドの画面からも「レビュー中」の入口でレビュー中の書き込みの画面を開ける（正常系）。"""
    # 準備
    url, _ = served_thread
    page = open_preview(url)
    open_thread(page, "TH-1")
    # 実行
    page.click(REVIEW_ENTRY)
    # 検証
    page.wait_for_selector(REVIEW_HEAD)


# 利用者の既読にする要求のパス（スレッドの ID を取り出す）
SEEN_URL = "**/api/threads/*/seen"

# 既読になるのを待つ間に、threads.yaml を読み直す間隔ミリ秒
SEEN_POLL_MS = 100


def _record_seen_requests(page: Page, *, status: int | None = None) -> list[str]:
    """既読にする要求を控える入れ物を返す。status を渡すとサーバーへ届かせず、その応答を返す。"""
    requested: list[str] = []

    def _handle(route: Route) -> None:
        """要求のスレッドの ID を控え、status が無ければ本物のサーバーへ通す。"""
        requested.append(route.request.url.split("/")[-2])
        if status is None:
            route.continue_()
        else:
            fulfill_problem(route, status, "書けませんでした")

    page.route(SEEN_URL, _handle)
    return requested


def _wait_seen(page: Page, root: Path, thread_id: str) -> None:
    """threads.yaml のスレッドの全ての書き込みが利用者の既読になるのを待つ。"""
    for _ in range(UPDATE_TIMEOUT_MS // SEEN_POLL_MS):
        posts = _thread_in_yaml(root, thread_id)["posts"]
        if all(post["seen"] for post in posts):  # type: ignore[index]
            return
        page.wait_for_timeout(SEEN_POLL_MS)
    raise AssertionError(f"{thread_id} が既読になりません")


@pytest.fixture
def served_unseen_thread(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_post: MakePost,
    make_thread: MakeThread,
) -> tuple[str, Path]:
    """AI の返信が利用者の未読のオープンの TH-1（レビュー中の返信 C-1 つき）・全て既読の TH-2・D-1 へのまだ送っていない新しいスレッド C-2 を持つワークスペースの配信の URL とフォルダを返す。"""
    return write_review_preview(
        make_item("D-1", title="最初の問い"),
        threads=(
            make_thread(
                "TH-1",
                make_post("TH-1-1", read=True, body="案を決めたい", created="2026-10-12T01:00:00+00:00"),
                make_post(
                    "TH-1-2", author="ai", seen=False, body="案 A で決めました", created="2026-10-12T02:00:00+00:00"
                ),
                summary="未読のスレッド",
                target="D-1",
            ),
            make_thread(
                "TH-2",
                make_post("TH-2-1", author="ai", created="2026-10-12T03:00:00+00:00"),
                summary="既読のスレッド",
            ),
        ),
        comments=(
            free_comment(make_comment("C-1", body="了解です", thread="TH-1")),
            make_comment("C-2", target="D-1", body="新しい話"),
        ),
    )


def test_seen_when_opened(
    served_unseen_thread: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """未読のスレッドの画面を出すと、そのスレッドを利用者の既読にする。並びは応答を待たずに出す（正常系）。"""
    # 準備
    url, root = served_unseen_thread
    requested = _record_seen_requests(page)
    open_preview(url)
    # 実行
    open_thread(page, "TH-1")
    # 検証
    assert page.inner_text(HEADING) == "オープン\n未読のスレッド"
    assert page.locator(f"{POSTS}:has-text('案 A で決めました')").count() == 1
    _wait_seen(page, root, "TH-1")
    assert requested == ["TH-1"]
    # 既読にしたのは利用者の既読だけで、AI の既読と取り込み済みは変えない
    posts = _thread_in_yaml(root, "TH-1")["posts"]
    assert [(post["read"], post.get("taken")) for post in posts] == [(True, None), (True, None)]  # type: ignore[union-attr]


def test_seen_when_opened_seen_thread(
    served_unseen_thread: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """利用者の未読の書き込みが無いスレッドの画面を出しても、既読にする要求を送らない（正常系）。"""
    # 準備
    url, root = served_unseen_thread
    requested = _record_seen_requests(page)
    open_preview(url)
    # 実行
    open_thread(page, "TH-2")
    page.wait_for_selector(f"{POSTS}")
    page.wait_for_timeout(DRAFT_WAIT_MS)
    # 検証
    assert requested == []
    assert [post["seen"] for post in _thread_in_yaml(root, "TH-2")["posts"]] == [True]  # type: ignore[index]


def test_seen_when_opened_from_review(
    served_unseen_thread: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """レビュー中の書き込みの行から未読のスレッドの画面を出しても、既読にする（正常系）。"""
    # 準備
    url, root = served_unseen_thread
    requested = _record_seen_requests(page)
    open_preview(url)
    page.click(COMMENTS_BUTTON)
    page.wait_for_selector(f"{COMMENTS_PANEL}.open")
    page.click(REVIEW_ENTRY)
    page.wait_for_selector(REVIEW_HEAD)
    # 実行
    page.click(f"{COMMENTS_PANEL} li[data-comment='C-1'] .row-head button.row-target")
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
    # 検証
    _wait_seen(page, root, "TH-1")
    assert requested == ["TH-1"]


def test_seen_when_opened_pending_thread(
    served_unseen_thread: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """まだ送っていない新しいスレッドの画面を出すときは、既読にする要求を送らない（正常系）。"""
    # 準備
    url, _ = served_unseen_thread
    requested = _record_seen_requests(page)
    open_preview(url)
    open_list(page)
    # 実行
    page.click(f"{COMMENTS_PANEL} ul.th-list > li:has(> button[data-focus='thread:new:C-2']) button.th-open")
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
    page.wait_for_timeout(DRAFT_WAIT_MS)
    # 検証
    assert requested == []


def test_seen_when_failed(
    served_unseen_thread: tuple[str, Path], open_preview: OpenPreview, page: Page
) -> None:
    """既読にできなくても画面にエラーを出さず、次にスレッドの画面を出したときに呼び直す（異常系）。"""
    # 準備
    url, root = served_unseen_thread
    requested = _record_seen_requests(page, status=500)
    open_preview(url)
    # 実行（1 回目: 断られる）
    open_thread(page, "TH-1")
    page.wait_for_timeout(DRAFT_WAIT_MS)
    # 検証
    assert requested == ["TH-1"]
    assert page.inner_text(HEADING) == "オープン\n未読のスレッド"
    assert page.locator(f"{COMMENTS_PANEL} [role='alert'], {ACTION_MSG}").count() == 0
    assert [post["seen"] for post in _thread_in_yaml(root, "TH-1")["posts"]] == [True, False]  # type: ignore[index]
    # 実行（2 回目: 一覧へ戻って開き直す）
    page.get_by_role("button", name="一覧へ戻る").click()
    page.click(f"{thread_row('TH-1')} button.th-open")
    page.wait_for_selector(f"{COMMENTS_PANEL} .th-head h3.th-heading")
    page.wait_for_timeout(DRAFT_WAIT_MS)
    # 検証
    assert requested == ["TH-1", "TH-1"]


def test_seen_when_reply_arrives_while_open(
    served_unseen_thread: tuple[str, Path],
    open_preview: OpenPreview,
    page: Page,
    call_tool: CallTool,
) -> None:
    """スレッドの画面を開いている間に届いた AI の返信も、描き直した後に既読にする（正常系）。"""
    # 準備
    url, root = served_unseen_thread
    requested = _record_seen_requests(page)
    open_preview(url)
    open_thread(page, "TH-2")
    page.wait_for_selector(POSTS)
    assert requested == []
    # 実行
    call_tool("reply", workspace=str(root), id="TH-2", body="続きの返信です", summary="既読のスレッド")
    # 検証
    page.wait_for_selector(f"{POSTS}:has-text('続きの返信です')", timeout=UPDATE_TIMEOUT_MS)
    _wait_seen(page, root, "TH-2")
    assert requested == ["TH-2"]
