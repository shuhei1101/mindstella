"""画面設計『スレッド』（スレッド 1 件の画面）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page
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
    thread_row,
    wait_until_focused,
)
from preview_fixture_types import OpenPreview, WriteReviewPreview
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


def test_updated_by_change(
    served_thread: tuple[str, Path], open_preview: OpenPreview, call_tool: CallTool
) -> None:
    """書き換えの知らせが届いたら、スレッドを読み直して AI の返信と AI が状態を変えた記録を並びに足し、入力中の返信は保つ（正常系）。"""
    # 準備
    url, root = served_thread
    page = open_preview(url)
    open_thread(page, "TH-1")
    page.fill(REPLY_TEXTAREA, "入力途中")
    # 実行
    call_tool("reply", workspace=str(root), id="TH-1", body="AI の返信です", summary="案の相談", take=True)
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
