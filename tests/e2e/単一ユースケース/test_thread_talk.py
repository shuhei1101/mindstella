"""スレッドで話す（スレッドの一覧でスレッドを開き、書き込みを読んで返信をレビューに追加し、まとめて送り、話が済んだら理由つきでクローズにする）の E2E テスト。

MCP サーバーを立て、サーバーが配るプレビューを実際のブラウザで開く。描画のライブラリは CDN から読む。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from playwright.sync_api import Page
from preview_helpers import (
    BACK_BUTTON,
    BAND_RESULT,
    CLOSED_NOTE,
    COMMENTS_BUTTON,
    COMMENTS_PANEL,
    REASON_FORM,
    REASON_OK,
    REASON_TEXTAREA,
    REPLY_FORM,
    REPLY_MESSAGE,
    REPLY_SEND,
    REPLY_TEXTAREA,
    REVIEW_ENTRY,
    REVIEW_HEAD,
    SEND_BAND,
    STATE_SEGMENTS,
    STATUS_BUTTON,
    THREAD_HEADING,
    THREAD_POSTS,
    THREAD_ROWS,
    UPDATE_TIMEOUT_MS,
    OpenPreview,
    open_closed_thread,
    open_list,
    open_thread,
    thread_row,
)
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
    WriteThreads,
)

# AI が立てたスレッドの問いと、利用者の返信の本文
AI_QUESTION = "D-1 の比べた結果を Issue に起票してよいですか"
REPLY_BODY = "起票してよい"

# 書き込みの日時（古い順）
T_0100 = "2026-10-12T01:00:00+00:00"
T_0200 = "2026-10-12T02:00:00+00:00"
T_0300 = "2026-10-12T03:00:00+00:00"
T_0400 = "2026-10-12T04:00:00+00:00"

# 書きかけを保つ待ち（入力が止まってから保つまでの間より長く）
DRAFT_WAIT_MS = 1_200

# 利用者がクローズにした記録
USER_CLOSED = {"kind": "closed", "author": "user", "reason": None, "created": T_0400}


def _read(root: Path, name: str) -> list[dict[str, Any]]:
    """ワークスペースの YAML の items を読む（ファイルが無ければ 0 件）。"""
    path = root / RECORD_DIR / name
    return yaml.safe_load(path.read_text(encoding="utf-8"))["items"] if path.exists() else []


def _thread(root: Path, thread_id: str) -> dict[str, Any]:
    """threads.yaml から、指定した ID のスレッドを返す。"""
    return next(item for item in _read(root, "threads.yaml") if item["id"] == thread_id)


def _serve(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    write_threads: WriteThreads,
    write_comments: WriteComments,
    *items: dict[str, Any],
    threads: tuple[dict[str, Any], ...],
    comments: tuple[dict[str, Any], ...] = (),
) -> tuple[str, Path]:
    """項目・スレッド・レビュー中の書き込みを持つワークスペースを作り、配信の URL とワークスペースのフォルダを返す。"""
    root = make_workspace(*items)
    write_threads(root, *threads)
    if comments:
        write_comments(root, *comments)
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    return str(served.data["url"]), root


def _without_target(comment: dict[str, Any]) -> dict[str, Any]:
    """向けた項目のキーを持たない（項目を指さない）コメントにする。"""
    return {key: value for key, value in comment.items() if key != "target"}


def _row_ids(page: Page) -> list[str]:
    """スレッドの一覧に並んだスレッドの ID を上から返す。"""
    return page.eval_on_selector_all(THREAD_ROWS, "rows => rows.map(r => r.dataset.thread)")


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    write_comments: WriteComments,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """AI のスレッドへの返信をレビューに追加してまとめて送ると、利用者の書き込みとして末尾に積まれ、取り込み待ちになる（正常系）。"""
    # 準備
    url, root = _serve(
        make_workspace,
        call_tool,
        write_threads,
        write_comments,
        make_item("D-1"),
        threads=(
            make_thread(
                "TH-1",
                make_post("TH-1-1", author="ai", body=AI_QUESTION, created=T_0100),
                summary="D-1 の比べた結果を Issue に起票してよいかの確認。返事待ち",
                tags=["起票"],
                target="D-1",
            ),
        ),
    )
    open_preview(url)
    # 実行（返信をレビューに追加する）
    open_thread(page, "TH-1")
    page.fill(REPLY_TEXTAREA, REPLY_BODY)
    page.click(REPLY_SEND)
    page.wait_for_selector(f"{THREAD_POSTS}[data-comment]", timeout=UPDATE_TIMEOUT_MS)
    # 検証（レビューに追加した時点）
    assert page.inner_text(f"{THREAD_POSTS}[data-comment] .post-body") == REPLY_BODY
    assert page.locator(f"{THREAD_POSTS}[data-comment] .th-pending").count() == 1
    assert [post["body"] for post in _thread(root, "TH-1")["posts"]] == [AI_QUESTION]
    page.click(BACK_BUTTON)
    page.wait_for_selector(thread_row("TH-1"))
    assert page.locator(f"{thread_row('TH-1')} .th-pending").count() == 1
    # 実行（レビュー中を確かめる画面からまとめて送る）
    page.click(REVIEW_ENTRY)
    page.wait_for_selector(REVIEW_HEAD)
    page.locator(SEND_BAND).get_by_role("button", name="まとめて送る").click()
    page.wait_for_selector(f"{BAND_RESULT}.sent", timeout=UPDATE_TIMEOUT_MS)
    # 検証（送った後）
    posts = _thread(root, "TH-1")["posts"]
    assert [(post["author"], post["body"]) for post in posts] == [
        ("ai", AI_QUESTION),
        ("user", REPLY_BODY),
    ]
    assert (posts[1]["read"], posts[1]["taken"]) == (False, None)
    awaiting = call_tool("threads", workspace=str(root), awaiting=True)
    assert awaiting.data is not None
    assert [item["id"] for item in awaiting.data["items"]] == ["TH-1"]
    assert awaiting.data["items"][0]["last_author"] == "user"
    assert _read(root, "comments.yaml") == []
    page.click(BACK_BUTTON)
    page.wait_for_selector(thread_row("TH-1"), timeout=UPDATE_TIMEOUT_MS)
    assert page.inner_text(f"{thread_row('TH-1')} .th-author") == "あなた"
    assert page.locator(f"{thread_row('TH-1')} .th-pending").count() == 0


def test_normal_when_close(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    write_comments: WriteComments,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """AI の返信の中の項目の ID から詳細パネルを開き、閉じて、理由つきでクローズにすると、既定の一覧から外れる（正常系）。"""
    # 準備
    url, root = _serve(
        make_workspace,
        call_tool,
        write_threads,
        write_comments,
        make_item("D-1", title="最初の問い"),
        threads=(
            make_thread(
                "TH-1",
                make_post("TH-1-1", body="案 A にする", read=True, created=T_0100),
                make_post("TH-1-2", author="ai", body="D-1 を案 A で決定にしました", created=T_0200),
                summary="D-1 の案の相談。案 A で決定",
                target="D-1",
            ),
        ),
    )
    open_preview(url)
    open_thread(page, "TH-1")
    # 実行（AI の返信の中の D-1 を押して、詳細パネルを開き、閉じる）
    page.click(f"{THREAD_POSTS}:nth-child(2) button.idlink")
    page.wait_for_selector("aside.panel.open")
    # 検証
    assert "D-1" in page.inner_text("aside.panel .panel-kind")
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    # 実行（理由を書いてクローズにする）
    page.click(STATUS_BUTTON)
    page.fill(REASON_TEXTAREA, "案 A で決着")
    page.click(REASON_OK)
    page.wait_for_selector(CLOSED_NOTE, timeout=UPDATE_TIMEOUT_MS)
    # 検証
    thread = _thread(root, "TH-1")
    closed = thread["events"][-1]
    assert (thread["status"], closed["kind"], closed["author"], closed["reason"]) == (
        "closed",
        "closed",
        "user",
        "案 A で決着",
    )
    assert bool(closed["created"]) is True
    assert page.inner_text(f"{THREAD_POSTS}.th-event .th-event-reason") == "案 A で決着"
    assert page.locator(REPLY_FORM).count() == 0
    # 実行（一覧へ戻る）
    page.click(BACK_BUTTON)
    page.wait_for_selector(f"{COMMENTS_PANEL} .comments-empty")
    # 検証（オープンだけの一覧に出ず、クローズに切り替えると出る）
    assert _row_ids(page) == []
    page.click(f"{STATE_SEGMENTS}[data-focus='filter:closed']")
    assert _row_ids(page) == ["TH-1"]


def test_normal_when_reopen(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    write_comments: WriteComments,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """クローズのスレッドを理由を書かずにオープンに戻すと、返信の入力が出て、オープンだけの一覧に戻る（正常系）。"""
    # 準備
    url, root = _serve(
        make_workspace,
        call_tool,
        write_threads,
        write_comments,
        make_item("D-1"),
        threads=(
            make_thread(
                "TH-1",
                make_post("TH-1-1", body="案 A にする", read=True, created=T_0100),
                status="closed",
                summary="D-1 の案の相談",
                events=[USER_CLOSED],
            ),
        ),
    )
    open_preview(url)
    open_closed_thread(page, "TH-1")
    # 実行
    page.click(STATUS_BUTTON)
    page.click(REASON_OK)
    page.wait_for_selector(REPLY_FORM, timeout=UPDATE_TIMEOUT_MS)
    # 検証
    thread = _thread(root, "TH-1")
    reopened = thread["events"][-1]
    assert (thread["status"], reopened["kind"], reopened["author"], reopened["reason"]) == (
        "open",
        "reopened",
        "user",
        None,
    )
    assert bool(reopened["created"]) is True
    page.click(BACK_BUTTON)
    page.click(f"{STATE_SEGMENTS}[data-focus='filter:open']")
    page.wait_for_selector(thread_row("TH-1"))
    assert _row_ids(page) == ["TH-1"]


def test_normal_when_ai_reply_arrives(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    write_comments: WriteComments,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """開いているスレッドへ AI が返信すると、画面を開き直さずに末尾へ出て、入力欄の書きかけは残る（正常系）。"""
    # 準備
    url, root = _serve(
        make_workspace,
        call_tool,
        write_threads,
        write_comments,
        make_item("D-1"),
        threads=(make_thread("TH-1", make_post("TH-1-1", body="案 A にする", created=T_0100)),),
    )
    open_preview(url)
    open_thread(page, "TH-1")
    page.fill(REPLY_TEXTAREA, "書きかけの返信")
    # 実行
    replied = call_tool(
        "reply",
        workspace=str(root),
        id="TH-1",
        body="D-1 を案 A で決定にしました",
        summary="D-1 の案の相談。案 A で決定",
    )
    # 検証
    assert replied.is_error is False
    page.wait_for_selector(f"{THREAD_POSTS}:has-text('D-1 を案 A で決定にしました')", timeout=UPDATE_TIMEOUT_MS)
    assert page.eval_on_selector_all(
        f"{THREAD_POSTS} .post-author", "authors => authors.map(a => a.textContent)"
    ) == ["あなた", "AI"]
    assert page.input_value(REPLY_TEXTAREA) == "書きかけの返信"


def test_normal_when_filtered(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    write_comments: WriteComments,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """行のタグを押すとそのタグで絞り、すべてに切り替えるとクローズも並び、チップを外すと戻る（正常系）。"""
    # 準備
    url, _ = _serve(
        make_workspace,
        call_tool,
        write_threads,
        write_comments,
        make_item("D-1"),
        threads=(
            make_thread("TH-1", make_post("TH-1-1", created=T_0100), tags=["画面"], summary="一つ目"),
            make_thread("TH-2", make_post("TH-2-1", created=T_0200), tags=["調査"], summary="二つ目"),
            make_thread(
                "TH-3",
                make_post("TH-3-1", created=T_0300),
                status="closed",
                tags=["画面"],
                summary="三つ目",
                events=[USER_CLOSED],
            ),
        ),
    )
    open_preview(url)
    open_list(page)
    # 実行・検証（タグ「画面」で絞る）
    page.click(f"{thread_row('TH-1')} button.th-tag")
    assert _row_ids(page) == ["TH-1"]
    assert page.inner_text(f"{COMMENTS_PANEL} .talk-chips .chip") == "画面"
    # 実行・検証（すべてに切り替える）
    page.click(f"{STATE_SEGMENTS}[data-focus='filter:all']")
    assert sorted(_row_ids(page)) == ["TH-1", "TH-3"]
    # 実行・検証（チップを外す）
    page.get_by_role("button", name="タグ「画面」の絞り込みを外す").click()
    assert sorted(_row_ids(page)) == ["TH-1", "TH-2", "TH-3"]


def test_normal_when_draft_kept(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    write_comments: WriteComments,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """返信の書きかけはスレッドごとに残り、一覧へ戻る・別のスレッドを開く・パネルを閉じる・読み込み直すのどれでも消えず、レビューに追加すると消える（正常系）。"""
    # 準備
    url, root = _serve(
        make_workspace,
        call_tool,
        write_threads,
        write_comments,
        make_item("D-1"),
        threads=(
            make_thread(
                "TH-1",
                make_post("TH-1-1", body="一つ目の質問", created=T_0100),
                make_post("TH-1-2", author="ai", body="一つ目の返事", created=T_0200),
                summary="一つ目",
            ),
            make_thread(
                "TH-2",
                make_post("TH-2-1", body="二つ目の質問", created=T_0100),
                make_post("TH-2-2", author="ai", body="二つ目の返事", created=T_0200),
                summary="二つ目",
            ),
        ),
    )
    open_preview(url)
    open_thread(page, "TH-1")
    # 実行（書きかける）
    page.fill(REPLY_TEXTAREA, "一つ目の書きかけ")
    page.wait_for_timeout(DRAFT_WAIT_MS)
    # 一覧へ戻り、2 件目のスレッドを開く
    page.click(BACK_BUTTON)
    page.click(f"{thread_row('TH-2')} button.th-open")
    page.wait_for_selector(REPLY_TEXTAREA)
    # 検証（2 件目の入力欄は空で、1 件目の書きかけが残っている）
    assert page.input_value(REPLY_TEXTAREA) == ""
    assert [(item["thread"], item["body"]) for item in _read(root, "drafts.yaml")] == [
        ("TH-1", "一つ目の書きかけ")
    ]
    # 実行（パネルを閉じ、画面を読み込み直して 1 件目を開き直す）
    page.click(COMMENTS_BUTTON)
    page.wait_for_function("!document.querySelector('aside.comments-panel.open')")
    page.reload()
    page.wait_for_selector("main#main > *", state="attached")
    open_thread(page, "TH-1")
    # 検証
    assert page.input_value(REPLY_TEXTAREA) == "一つ目の書きかけ"
    # 実行（レビューに追加する）
    page.click(REPLY_SEND)
    page.wait_for_selector(f"{THREAD_POSTS}[data-comment]", timeout=UPDATE_TIMEOUT_MS)
    # 検証（そのスレッドの書きかけが消える）
    page.wait_for_function(
        "document.querySelector('form.reply textarea').value === ''", timeout=UPDATE_TIMEOUT_MS
    )
    assert [item for item in _read(root, "drafts.yaml") if item.get("thread") == "TH-1"] == []


def test_normal_when_pending_reply_edited(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    write_comments: WriteComments,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """レビュー中の返信を書き換え、消して元に戻すと、スレッドの末尾とレビュー中を確かめる画面の本文が同じになり、一覧の行の印も合わせて外れ・戻る（正常系）。"""
    # 準備
    url, root = _serve(
        make_workspace,
        call_tool,
        write_threads,
        write_comments,
        make_item("D-1"),
        threads=(
            make_thread(
                "TH-1",
                make_post("TH-1-1", author="ai", body="D-1 を案 A で進めてよいですか", created=T_0100),
                summary="D-1 の進め方の確認",
            ),
        ),
        comments=(_without_target(make_comment("C-1", body="案 A にする", thread="TH-1")),),
    )
    open_preview(url)
    open_thread(page, "TH-1")
    row = f"{THREAD_POSTS}[data-comment='C-1']"
    # 実行（書き換える）
    page.locator(row).get_by_role("button", name="TH-1 への返信を修正").click()
    page.fill(f"{row} textarea", "案 A に決める")
    page.click(f"{row} form.row-edit button[type='submit']")
    page.wait_for_function(
        "selector => document.querySelector(selector)?.textContent.includes('案 A に決める')",
        arg=row,
        timeout=UPDATE_TIMEOUT_MS,
    )
    # 検証（レビュー中を確かめる画面の行も同じ本文）
    assert [item["body"] for item in _read(root, "comments.yaml")] == ["案 A に決める"]
    page.click(REVIEW_ENTRY)
    page.wait_for_selector(REVIEW_HEAD)
    assert page.inner_text(f"{COMMENTS_PANEL} li[data-comment='C-1'] .review-body") == "案 A に決める"
    page.click(BACK_BUTTON)
    page.wait_for_selector(row)
    # 実行（消す）
    page.locator(row).get_by_role("button", name="TH-1 への返信を削除").click()
    page.wait_for_selector(f"{COMMENTS_PANEL} ol.posts [role='status']", timeout=UPDATE_TIMEOUT_MS)
    # 検証（末尾の返信と、一覧の行の印が外れる）
    assert page.locator(f"{row}.pending").count() == 0
    page.click(BACK_BUTTON)
    page.wait_for_selector(thread_row("TH-1"))
    assert page.locator(f"{thread_row('TH-1')} .th-pending").count() == 0
    # 実行（元に戻す）
    page.click(f"{thread_row('TH-1')} button.th-open")
    page.get_by_role("button", name="元に戻す").click()
    page.wait_for_selector(f"{row}.pending", timeout=UPDATE_TIMEOUT_MS)
    # 検証（両方に戻る。スレッドの書き込みは送る前のまま）
    assert page.inner_text(f"{row} .post-body") == "案 A に決める"
    page.click(BACK_BUTTON)
    page.wait_for_selector(thread_row("TH-1"))
    assert page.locator(f"{thread_row('TH-1')} .th-pending").count() == 1
    assert [item["body"] for item in _read(root, "comments.yaml")] == ["案 A に決める"]
    assert len(_thread(root, "TH-1")["posts"]) == 1


def test_error_when_server_unreachable(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    start_server: StartServer,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """サーバーを止めてから返信をレビューに追加すると、追加できなかった旨を出し、入力欄に返信を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread(
            "TH-1",
            make_post("TH-1-1", author="ai", body=AI_QUESTION, created=T_0100),
            summary="D-1 の比べた結果を Issue に起票してよいかの確認。返事待ち",
        ),
    )
    server = start_server()
    served = server.call("preview_url", workspace=str(root))
    assert served.data is not None
    open_preview(str(served.data["url"]))
    open_thread(page, "TH-1")
    # スレッドを開いた後にサーバーを止める
    server.close_stdin()
    server.wait_exit()
    page.fill(REPLY_TEXTAREA, REPLY_BODY)
    # 実行
    page.click(REPLY_SEND)
    # 検証
    page.wait_for_function(
        "selector => document.querySelector(selector)?.textContent.includes('追加できませんでした')",
        arg=REPLY_MESSAGE,
        timeout=UPDATE_TIMEOUT_MS,
    )
    assert page.input_value(REPLY_TEXTAREA) == REPLY_BODY
    assert _read(root, "comments.yaml") == []
    assert [post["body"] for post in _thread(root, "TH-1")["posts"]] == [AI_QUESTION]


def test_error_when_reply_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    write_comments: WriteComments,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """入力欄を空のままにすると、レビューに追加のボタンを押せない（異常系）。"""
    # 準備
    url, root = _serve(
        make_workspace,
        call_tool,
        write_threads,
        write_comments,
        make_item("D-1"),
        threads=(make_thread("TH-1", make_post("TH-1-1", author="ai", body=AI_QUESTION)),),
    )
    open_preview(url)
    # 実行
    open_thread(page, "TH-1")
    # 検証
    assert page.input_value(REPLY_TEXTAREA) == ""
    assert page.is_disabled(REPLY_SEND)
    assert _read(root, "comments.yaml") == []
    assert [post["body"] for post in _thread(root, "TH-1")["posts"]] == [AI_QUESTION]


def test_normal_when_ai_close_arrives(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    write_comments: WriteComments,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """AI がクローズにすると、画面を開き直さずに末尾へ記録と理由が出て、利用者がオープンに戻すと返信の入力が戻る（正常系）。"""
    # 準備
    url, root = _serve(
        make_workspace,
        call_tool,
        write_threads,
        write_comments,
        make_item("D-1"),
        threads=(
            make_thread(
                "TH-1",
                make_post("TH-1-1", body="案 A にする", read=True, taken=T_0100, created=T_0100),
                make_post("TH-1-2", author="ai", body="D-1 を案 A で決定にしました", created=T_0200),
                make_post("TH-1-3", body="了解", created=T_0300),
                summary="D-1 の案の相談。案 A で決定",
            ),
        ),
    )
    open_preview(url)
    open_thread(page, "TH-1")
    # 実行（AI がクローズにする）
    closed = call_tool(
        "set_thread_status", workspace=str(root), id="TH-1", status="closed", reason="了解を受けた"
    )
    # 検証
    assert closed.is_error is False
    page.wait_for_selector(f"{THREAD_POSTS}.th-event.ai", timeout=UPDATE_TIMEOUT_MS)
    assert page.inner_text(f"{THREAD_POSTS}.th-event.ai .th-event-line span") == "AI がクローズにしました"
    assert page.inner_text(f"{THREAD_POSTS}.th-event.ai .th-event-reason") == "了解を受けた"
    assert page.inner_text(THREAD_HEADING) == "クローズ\nD-1 の案の相談。案 A で決定"
    assert page.locator(REPLY_FORM).count() == 0
    assert page.inner_text(STATUS_BUTTON) == "オープンに戻す"
    # 実行（利用者が理由を書かずにオープンに戻す）
    page.click(STATUS_BUTTON)
    page.click(REASON_OK)
    page.wait_for_selector(REPLY_FORM, timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert page.inner_text(f"{THREAD_POSTS}.th-event.user .th-event-line span") == "あなたがオープンに戻しました"
    assert [event["kind"] for event in _thread(root, "TH-1")["events"]] == ["closed", "reopened"]
    assert page.locator(REASON_FORM).count() == 0
