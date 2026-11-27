"""画面設計『スレッド.tsx』の結合テスト。"""

from __future__ import annotations

from preview_fixture_types import StartVoicePreview as _StartVoicePreview
from preview_voice_helpers import (
    FAKE_MIC_SCRIPT,
    VOICE_TIMEOUT_MS,
    assert_mic_blocked_after_click,
    assert_recording_wave,
    put_caret,
    start_recording,
    wait_transcription_status,
)
from workspace_fixtures import MakeItem as _MakeItem, MakePost as _MakePost, MakeThread as _MakeThread

from collections.abc import Callable
from pathlib import Path
from typing import Any
import re

import pytest

from playwright.sync_api import Browser, Locator, Page, Playwright, expect
from preview_comment_helpers import free_comment, read_workspace_yaml
from preview_fixture_types import WriteReviewPreview
from preview_pending_helpers import assert_waiting, hold_requests, press_twice
from preview_spa_helpers import open_spa
from preview_width_helpers import LONG_POST_BODY, NARROWEST_SIZE, WIDE_SIZE, assert_no_horizontal_scroll, narrow_left_panel
from workspace_fixtures import MakeComment, MakeItem, MakePost, MakeThread, WriteComments
from preview_record_id_helpers import assert_tip

# 書き込みを待つ上限ミリ秒
UPDATE_TIMEOUT_MS = 10_000

# 改行の無い 3000 文字を超える書き込みの本文（スレッドのタイトルは書き込みの 1 行目になる）
LONG_FIRST_LINE = "長文の音声入力の書き込みから作ったスレッドのタイトル。" * 120

# 見出しのタイトルを省略する行数の上限（2 行に余裕を足した値）と、全文を開いた間の最大の高さ（px）
CLAMP_LINES_LIMIT = 2.5
TITLE_EXPANDED_MAX_PX = 288

# 要素の高さが行の高さの何行分かを返す
TITLE_LINES_JS = "(element) => element.getBoundingClientRect().height / parseFloat(getComputedStyle(element).lineHeight)"

# 指で操作するスマホの画面幅と高さ
TOUCH_VIEWPORT = {"width": 390, "height": 844}

# 5 行を超えるレビュー中の返信の本文
LONG_REPLY = "\n\n".join(f"{index} 行目の返信" for index in range(1, 9))

# パネルの幅より広い表とコードブロックを持つ書き込みの本文（表のセルは折り返さない英数字）
WIDE_BODY = (
    "| " + " | ".join(f"column_heading_{index:02d}" for index in range(1, 16)) + " |\n"
    + "| " + " | ".join("---" for _ in range(15)) + " |\n"
    + "| " + " | ".join(f"cell_value_{index:02d}" for index in range(1, 16)) + " |\n\n"
    + "```\n" + "長いコードの行" * 40 + "\n```\n\n"
    + "段落の文は" * 60
)


def _panel(page: Page) -> Locator:
    """コメントの一覧のパネルを返す。"""
    return page.get_by_role("dialog", name="コメント")


def _open(page: Page, spa_comments_preview: tuple[str, Path], thread: str) -> Page:
    """スレッドを開いた画面を返す。"""
    url, _ = spa_comments_preview
    return open_spa(page, url, f"?tab=decisions&panel=comments&thread={thread}")


def test_back(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """「一覧へ戻る」でスレッドの一覧へ戻り、開いていた行へフォーカスを戻す。入力欄の外の Esc も同じ（正常系）。"""
    # 準備
    _open(page, spa_comments_preview, "TH-2")
    # 実行
    _panel(page).get_by_role("button", name="一覧へ戻る").click()
    # 検証
    expect(_panel(page).get_by_role("group", name="スレッドの状態で絞る")).to_be_visible()
    assert "thread=" not in page.url
    expect(_panel(page).locator("[data-focus='thread:TH-2']")).to_be_focused()
    # 実行（Esc）
    _panel(page).locator("[data-focus='thread:TH-2']").click()
    page.keyboard.press("Escape")
    # 検証
    expect(_panel(page).get_by_role("group", name="スレッドの状態で絞る")).to_be_visible()


def test_post_thread_id_link_action(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem, make_thread: MakeThread, make_post: MakePost) -> None:
    """書き込みの本文の書き込みの ID のボタンを押すと、そのスレッドを開いてその書き込みまでスクロールし、フォーカスを移す。記録に無い ID は文字のまま（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("D-1", title="最初の問い"),
        threads=(
            make_thread(
                "TH-1",
                make_post("TH-1-1", author="ai", body="比較は TH-2-2 にあります。TH-99 は記録にありません。", created="2026-10-12T01:00:00+00:00"),
                summary="最初のスレッド",
            ),
            make_thread(
                "TH-2",
                make_post("TH-2-1", body="二つ目の質問", created="2026-10-12T02:00:00+00:00"),
                make_post("TH-2-2", author="ai", body="案の比較", created="2026-10-12T02:10:00+00:00"),
                summary="トップバーの見直し",
            ),
        ),
    )
    open_spa(page, url, "?tab=decisions&panel=comments&thread=TH-1")
    link = _panel(page).locator("[data-post-id='TH-1-1'] button.idlink[data-post='TH-2-2']")
    expect(_panel(page).locator("[data-post-id='TH-1-1']")).to_contain_text("TH-99 は記録にありません")
    expect(_panel(page).locator("[data-post-id='TH-1-1'] button.idlink")).to_have_count(1)
    # 実行
    link.click()
    # 検証
    expect(_panel(page).locator("[data-post-id='TH-2-2']")).to_be_focused()
    assert "thread=TH-2" in page.url


def test_change_status(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """「クローズにする」は理由を聞かずに状態を書き、一覧へ戻って次の行へフォーカスを移す（履歴に積まない）（正常系）。"""
    # 準備
    _, root = spa_comments_preview
    _open(page, spa_comments_preview, "TH-2")
    before = page.evaluate("history.length")
    # 実行
    _panel(page).get_by_role("button", name="クローズにする").click()
    # 検証
    expect(_panel(page).get_by_role("group", name="スレッドの状態で絞る")).to_be_visible()
    expect(_panel(page).get_by_role("textbox", name="理由（任意）")).to_have_count(0)
    expect(_panel(page).locator("[data-focus='thread:TH-1']")).to_be_focused()
    assert "thread=" not in page.url
    assert page.evaluate("history.length") == before
    threads = {thread["id"]: thread for thread in read_workspace_yaml(root, "threads.yaml")["items"]}
    assert threads["TH-2"]["status"] == "closed"
    assert threads["TH-2"]["events"][-1].get("reason") is None


def test_reopen(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """「オープンに戻す」はこの画面に留まり、状態の札と記録を描き直して「クローズにする」へフォーカスを戻す（正常系）。"""
    # 準備
    _, root = spa_comments_preview
    _open(page, spa_comments_preview, "TH-5")
    # 実行
    _panel(page).get_by_role("button", name="オープンに戻す").click()
    # 検証
    expect(_panel(page).get_by_role("button", name="クローズにする")).to_be_focused()
    expect(_panel(page).locator("[data-state=open]")).to_have_text("オープン")
    expect(_panel(page).locator("article[data-event=reopened]")).to_have_count(1)
    assert "thread=TH-5" in page.url
    threads = {thread["id"]: thread for thread in read_workspace_yaml(root, "threads.yaml")["items"]}
    assert threads["TH-5"]["status"] == "open"


def test_normal_when_pressed_again_while_closing(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """クローズを待つ間にもう一度押しても要求は 1 回で、待つ間は押せず、1 秒を超えると回るマーカーを出す（正常系）。"""
    # 準備
    _, root = spa_comments_preview
    _open(page, spa_comments_preview, "TH-2")
    held = hold_requests(page, "**/api/threads/*", "PATCH")
    button = _panel(page).get_by_role("button", name="クローズにする")
    # 幅は文字のフォントを読み終えてから測る（読み終える前の幅と比べない）
    page.evaluate("document.fonts.ready")
    box = button.bounding_box()
    assert box is not None
    # 実行（再描画の前に 2 回押す）
    press_twice(button)
    # 検証
    assert_waiting(page, button, held, box["width"])
    held.release()
    expect(_panel(page).get_by_role("group", name="スレッドの状態で絞る")).to_be_visible()
    threads = {thread["id"]: thread for thread in read_workspace_yaml(root, "threads.yaml")["items"]}
    assert [event["kind"] for event in threads["TH-2"]["events"]].count("closed") == 1


def test_status_failed(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """状態を書き換えられなかったとき、理由を `role="alert"` で出してこの画面に留まり、次に押すと送信の前に理由を消す（異常系）。"""
    # 準備
    _open(page, spa_comments_preview, "TH-2")
    page.route("**/api/threads/TH-2", lambda route: route.abort())
    # 実行
    _panel(page).get_by_role("button", name="クローズにする").click()
    # 検証
    expect(_panel(page).get_by_role("alert")).to_have_text("クローズにできませんでした。サーバーが止まっています。再起動してから押してください。")
    assert "thread=TH-2" in page.url
    # 実行（もう一度押す。送信を留めて、送信の前の表示を確かめる）
    page.unroute("**/api/threads/TH-2")
    held = hold_requests(page, "**/api/threads/*", "PATCH")
    _panel(page).get_by_role("button", name="クローズにする").click()
    # 検証
    expect(_panel(page).get_by_role("alert")).to_have_count(0)
    held.release()


def test_heading(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """見出しに状態の札と題（要約）を出す（正常系）。"""
    # 準備・実行
    _open(page, spa_comments_preview, "TH-1")
    heading = _panel(page).get_by_role("heading", level=2, name="D-1 の案の相談")
    # 検証
    expect(heading.locator("[data-state=open]")).to_have_text("オープン")


def test_target(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """向けた項目の ID とタイトルを出し、押すとパネルを開いたまま右にその項目の詳細パネルを開く（正常系）。"""
    # 準備
    _open(page, spa_comments_preview, "TH-1")
    target = _panel(page).get_by_role("button", name="D-1 最初の問い")
    # 実行
    target.click()
    # 検証
    page.wait_for_url("**id=D-1**")
    expect(page.get_by_role("complementary", name="詳細")).to_be_visible()
    expect(_panel(page)).to_be_visible()


def test_tags(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """スレッドのタグを # の印つきで並べ、押せない（正常系）。"""
    # 準備・実行
    _open(page, spa_comments_preview, "TH-1")
    # 検証
    expect(_panel(page).locator("[data-part=thread-tags]")).to_have_text("#画面")
    expect(_panel(page).locator("[data-part=thread-tags] button")).to_have_count(0)


def test_posts(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """書き込みを日時の順に並べ、その後ろにレビュー中の返信を並べる。開くと利用者の既読にする（正常系）。"""
    # 準備
    _, root = spa_comments_preview
    # 実行
    _open(page, spa_comments_preview, "TH-1")
    posts = _panel(page).locator("ol > li > article")
    # 検証
    expect(posts).to_have_count(3)
    assert posts.evaluate_all("items => items.map(e => e.dataset.comment ?? e.dataset.author)") == ["user", "ai", "C-43"]
    expect(posts.nth(2)).to_contain_text("レビュー中")
    expect(page.get_by_role("button", name="コメント（レビュー中 2 件）")).to_be_visible()
    thread = next(thread for thread in read_workspace_yaml(root, "threads.yaml")["items"] if thread["id"] == "TH-1")
    assert [post["seen"] for post in thread["posts"]] == [True, True]


def test_removed(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """レビュー中の返信を消すと元の場所に「コメントを削除しました。」と「元に戻す」を出し、「元に戻す」で戻す（正常系）。"""
    # 準備
    _open(page, spa_comments_preview, "TH-1")
    # 実行
    _panel(page).get_by_role("button", name="TH-1 への返信を削除").click()
    # 検証
    expect(_panel(page).get_by_role("status").filter(has_text="コメントを削除しました。")).to_be_visible()
    # 実行
    _panel(page).get_by_role("button", name="元に戻す").click()
    # 検証
    expect(_panel(page).locator("article[data-comment=C-43]")).to_be_visible()


def test_reply(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """返信を溜めると入力欄を空にし、書き込みの並びの末尾に足して、入口の件数を描き直す（正常系）。"""
    # 準備
    _, root = spa_comments_preview
    _open(page, spa_comments_preview, "TH-2")
    field = _panel(page).get_by_role("textbox", name="返信")
    # 実行
    field.fill("追記します")
    field.press("Control+Enter")
    # 検証
    expect(field).to_have_value("")
    expect(_panel(page).locator("ol > li > article").last).to_contain_text("追記します")
    expect(_panel(page).get_by_role("button", name="レビュー中の書き込みを確かめる（3 件）")).to_be_visible()
    items = read_workspace_yaml(root, "comments.yaml")["items"]
    assert [item["body"] for item in items if item.get("thread") == "TH-2"] == ["追記します"]


def test_closed_notice(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """クローズのスレッドは返信の入力の代わりに「クローズにしたスレッドです。」を出す（正常系）。"""
    # 準備・実行
    _open(page, spa_comments_preview, "TH-5")
    # 検証
    expect(_panel(page)).to_contain_text("クローズにしたスレッドです。")
    expect(_panel(page).get_by_role("textbox", name="返信")).to_have_count(0)
    expect(_panel(page).get_by_role("button", name="オープンに戻す")).to_be_visible()


def test_pending_notice(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """まだ送っていない新規スレッドは「まだ送信していないスレッドです。」を出し、状態を変えるボタンと返信の入力を出さない（正常系）。"""
    # 準備・実行
    _open(page, spa_comments_preview, "C-41")
    # 検証
    expect(_panel(page)).to_contain_text("まだ送信していないスレッドです。")
    expect(_panel(page).get_by_role("button", name="クローズにする")).to_have_count(0)
    expect(_panel(page).get_by_role("textbox", name="返信")).to_have_count(0)
    expect(_panel(page).locator("[data-state=pending]")).to_have_text("レビュー中")


def test_more(
    page: Page,
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_post: MakePost,
    make_thread: MakeThread,
) -> None:
    """5 行を超えるレビュー中の返信は畳んで「続きを表示」を出し、押すと開いて「折りたたむ」にする（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("D-1"),
        threads=(make_thread("TH-1", make_post("TH-1-1", body="質問")),),
        comments=(free_comment(make_comment("C-43", body=LONG_REPLY, thread="TH-1")),),
    )
    open_spa(page, url, "?tab=decisions&panel=comments&thread=TH-1")
    more = _panel(page).get_by_role("button", name="TH-1 への返信の続きを表示")
    # 検証
    expect(more).to_have_text("続きを表示")
    # 実行
    more.click()
    # 検証
    expect(_panel(page).get_by_role("button", name="TH-1 への返信の本文を折りたたむ")).to_have_text("折りたたむ")


def test_voice_input_when_service_stopped(
    page: Page,
    make_item: _MakeItem,
    make_post: _MakePost,
    make_thread: _MakeThread,
    start_voice_preview: _StartVoicePreview,
    unreachable_transcriber_url: str,
) -> None:
    """返信の入力で、文字起こしのサービスが起動していないときはマイクのボタンを押せなくし、押すと理由を結果の行に出す（正常系）。"""
    # 準備
    url, _ = start_voice_preview(
        unreachable_transcriber_url,
        make_item("D-1"),
        threads=(make_thread(
            "TH-1",
            make_post("TH-1-1", body="どちらにしますか", read=True),
            make_post("TH-1-2", author="ai", body="案 A と案 B があります"),
            target="D-1",
        ),),
    )
    # 実行
    open_spa(page, url, "?tab=decisions&panel=comments&thread=TH-1")
    # 検証
    field = page.get_by_role("textbox", name="返信")
    assert_mic_blocked_after_click(_panel(page).locator("form").filter(has=field), "[role=status]")


def test_pending_post_edit_voice_input(
    page: Page,
    make_item: _MakeItem,
    make_thread: _MakeThread,
    make_post: _MakePost,
    make_comment: MakeComment,
    write_comments: WriteComments,
    start_fake_transcriber: Callable[..., Any],
    start_voice_preview: _StartVoicePreview,
    valid_settings: dict[str, Any],
) -> None:
    """スレッドの中のレビュー中の返信の修正の入力で録音し、文字起こし後の挙動が review でも結果を録音前のカーソルの位置へ挿入するだけで、レビュー中に溜めない（正常系）。"""
    # 準備
    fake = start_fake_transcriber("done")
    url, root = start_voice_preview(
        fake.url,
        make_item("D-1"),
        threads=(make_thread("TH-1", make_post("TH-1-1", body="案を比べたい")),),
        settings={**valid_settings, "transcription": {"action": "review"}},
    )
    write_comments(root, free_comment(make_comment("C-1", body="確認: でよい", thread="TH-1")))
    page.add_init_script(FAKE_MIC_SCRIPT)
    with wait_transcription_status(page):
        open_spa(page, url, "?panel=comments&thread=TH-1")
    post = page.locator("article[data-comment='C-1']")
    post.get_by_role("button", name="TH-1 への返信を修正").click()
    form = post.locator("form[data-part=edit]")
    put_caret(form.locator("textarea"), "確認: でよい", 4)
    # 実行
    start_recording(form)
    assert_recording_wave(form)
    form.get_by_role("button", name="文字起こし", exact=True).click()
    # 検証
    expect(form.locator("[role=status]")).to_have_text("文字起こしの結果を挿入しました。", timeout=VOICE_TIMEOUT_MS)
    expect(form.locator("textarea")).to_have_value("確認: 案 A にするでよい")
    expect(form.locator("textarea")).to_be_focused()
    items = read_workspace_yaml(root, "comments.yaml")["items"]
    assert [(item["id"], item["body"]) for item in items] == [("C-1", "確認: でよい")]


def test_wide_table_scrolls_inside(
    page: Page,
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
) -> None:
    """パネルの幅より広い表・コードブロックを持つ書き込みは、並びと書き込みをパネルの幅に収め、表とコードブロックの中だけを横にスクロールし、段落は折り返す（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("D-1"),
        threads=(make_thread("TH-1", make_post("TH-1-1", body=WIDE_BODY, read=True), target="D-1"),),
    )
    for width in (1280, 390):
        page.set_viewport_size({"width": width, "height": 900})
        # 実行
        open_spa(page, url, "?tab=decisions&panel=comments&thread=TH-1")
        post = _panel(page).locator("article").filter(has_text="column_heading_01").first
        expect(post).to_be_visible()
        # 検証
        sizes = post.evaluate(
            """(article) => {
              const list = article.closest('ol');
              const scroller = article.querySelector('.post-table-scroll');
              const table = scroller.querySelector('table');
              const pre = article.querySelector('pre');
              const paragraph = [...article.querySelectorAll('p')].find((element) => element.textContent.includes('段落の文は'));
              return {
                list: list.scrollWidth <= list.clientWidth,
                article: article.getBoundingClientRect().right <= list.getBoundingClientRect().right + 1,
                table: [scroller, table].some((element) => element.scrollWidth > element.clientWidth && getComputedStyle(element).overflowX === 'auto'),
                code: pre.scrollWidth > pre.clientWidth,
                wrapped: paragraph.getBoundingClientRect().height > parseFloat(getComputedStyle(paragraph).lineHeight) * 1.5,
              };
            }"""
        )
        assert sizes == {"list": True, "article": True, "table": True, "code": True, "wrapped": True}, (width, sizes)



@pytest.mark.parametrize("tab", ["decisions", "tasks", "docs"])
def test_page_width_when_phone(
    playwright: Playwright, browser: Browser, spa_comments_preview: tuple[str, Path], tab: str
) -> None:
    """iPhone の端末の設定で、一覧のタブの上でスレッドを開いても、画面全体の幅が端末の幅を超えない（正常系）。"""
    # 準備
    url, _ = spa_comments_preview
    context = browser.new_context(**playwright.devices["iPhone 13"])
    phone = context.new_page()
    try:
        # 実行
        open_spa(phone, url, f"?tab={tab}&panel=comments&thread=TH-1")
        expect(_panel(phone).get_by_role("button", name="クローズにする")).to_be_visible()
        sizes = phone.evaluate("() => ({ inner: window.innerWidth, scroll: document.documentElement.scrollWidth })")
    finally:
        context.close()
    # 検証
    assert sizes == {"inner": 390, "scroll": 390}, sizes

# ─── 開いたときの最新の書き込み・書き込みの折りたたみ・見出しのタイトル（#372・#374） ───

# 改行で 8 行の書き込みの本文
EIGHT_LINES = "\n".join(f"{index} 行目" for index in range(1, 9))


def _long_thread(make_post: MakePost, make_thread: MakeThread) -> dict[str, Any]:
    """古い長い書き込み 6 件と、最新の長い書き込みを持つスレッドを返す（並びは画面の高さを超える）。"""
    posts = [make_post(f"TH-1-{index}", author="ai" if index % 2 == 0 else "user", body=EIGHT_LINES, read=True, created=f"2026-11-0{index}T00:00:00+00:00") for index in range(1, 8)]
    return make_thread("TH-1", *posts, target="D-1", summary="長いスレッドのタイトル。" * 8)


def test_open_latest(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem, make_post: MakePost, make_thread: MakeThread) -> None:
    """開くと最新の書き込みの先頭が並びの上端に来て、その書き込みにフォーカスがある。最新の書き込みは畳まない（正常系）。"""
    # 準備・実行
    url, _ = write_review_preview(make_item("D-1"), threads=(_long_thread(make_post, make_thread),))
    page.set_viewport_size({"width": 1280, "height": 700})
    open_spa(page, url, "?tab=decisions&panel=comments&thread=TH-1")
    latest = _panel(page).locator("article[data-post-id='TH-1-7']")
    # 検証
    expect(latest).to_be_focused()
    # 先頭を並びの上端に合わせる。その位置が一番下を超えるときは一番下まで送る
    placed = latest.evaluate(
        """(article) => {
          const list = article.closest('ol');
          const offset = article.getBoundingClientRect().top - list.getBoundingClientRect().top;
          return offset < 40 || list.scrollTop >= list.scrollHeight - list.clientHeight - 1;
        }"""
    )
    assert placed
    expect(latest.locator("[data-folded]")).to_have_count(0)
    expect(latest.get_by_role("button", name=re.compile("続きを表示"))).to_have_count(0)


def test_older_posts_folded(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem, make_post: MakePost, make_thread: MakeThread) -> None:
    """最新以外の長い書き込みは 5 行までに畳み、「続きを表示」で全文、「折りたたむ」で畳み直す（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("D-1"), threads=(_long_thread(make_post, make_thread),))
    open_spa(page, url, "?tab=decisions&panel=comments&thread=TH-1")
    first = _panel(page).locator("article[data-post-id='TH-1-1']")
    more = first.get_by_role("button", name="TH-1-1 の書き込みの続きを表示")
    expect(more).to_have_attribute("aria-expanded", "false")
    # 実行
    more.click()
    # 検証
    less = first.get_by_role("button", name="TH-1-1 の書き込みの本文を折りたたむ")
    expect(less).to_have_attribute("aria-expanded", "true")
    expect(first).to_contain_text("8 行目")
    # 実行
    less.click()
    # 検証
    expect(more).to_be_visible()


def test_title_collapsed_on_scroll(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem, make_post: MakePost, make_thread: MakeThread) -> None:
    """並びが一番上のときは見出しのタイトルを 2 行で省略して「続きを表示」を出し、スクロールした後は 1 行にして `title` に全文を持つ（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("D-1"), threads=(_long_thread(make_post, make_thread),))
    open_spa(page, url, "?tab=decisions&panel=comments&thread=TH-1")
    title = _panel(page).locator("[data-part='thread-title']")
    expect(_panel(page).locator("article[data-post-id='TH-1-7']")).to_be_focused()
    # 実行（一番上へ戻す）
    _panel(page).locator("ol").first.evaluate("(list) => { list.scrollTop = 0; list.dispatchEvent(new Event('scroll')); }")
    # 検証
    expect(title).not_to_have_attribute("data-collapsed", "")
    expect(title).to_have_attribute("data-clamped", "")
    expect(_panel(page).get_by_role("button", name="タイトルの続きを表示")).to_be_visible()
    # 実行（スクロールする）
    _panel(page).locator("ol").first.evaluate("(list) => { list.scrollTop = 200; list.dispatchEvent(new Event('scroll')); }")
    # 検証
    expect(title).to_have_attribute("data-collapsed", "")
    expect(title.locator("span[id]").first).to_have_attribute("title", "長いスレッドのタイトル。" * 8)
    expect(_panel(page).get_by_role("button", name="タイトルの続きを表示")).to_have_count(0)


def _first_long_post_thread(make_post: MakePost, make_thread: MakeThread) -> dict[str, Any]:
    """3000 文字を超える 1 件の書き込みから作り、要約を持たないスレッド（タイトルは書き込みの 1 行目）を返す。"""
    return make_thread("TH-1", make_post("TH-1-1", body=LONG_FIRST_LINE, read=True))


def test_long_title_clamped_on_open(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem, make_post: MakePost, make_thread: MakeThread) -> None:
    """3000 文字を超える書き込みから作ったスレッドを開いた直後から、見出しのタイトルを 2 行で省略して「続きを表示」を出す（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("D-1"), threads=(_first_long_post_thread(make_post, make_thread),))
    # 実行
    open_spa(page, url, "?tab=decisions&panel=comments&thread=TH-1")
    title = _panel(page).locator("[data-part='thread-title']")
    button = _panel(page).get_by_role("button", name="タイトルの続きを表示")
    # 検証
    expect(button).to_have_attribute("aria-expanded", "false")
    expect(title).to_have_attribute("data-clamped", "")
    expect(title).not_to_have_attribute("data-collapsed", "")
    assert title.locator("span[id]").first.evaluate(TITLE_LINES_JS) < CLAMP_LINES_LIMIT


def test_long_title_expand(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem, make_post: MakePost, make_thread: MakeThread) -> None:
    """「続きを表示」で全文を出して見出しの中で 288px までにしてスクロールさせ、「折りたたむ」で 2 行に戻す（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("D-1"), threads=(_first_long_post_thread(make_post, make_thread),))
    open_spa(page, url, "?tab=decisions&panel=comments&thread=TH-1")
    title = _panel(page).locator("[data-part='thread-title']")
    # 実行（開く）
    _panel(page).get_by_role("button", name="タイトルの続きを表示").click()
    region = _panel(page).get_by_role("region", name="スレッドのタイトルの全文")
    # 検証（開く）
    expect(_panel(page).get_by_role("button", name="タイトルを折りたたむ")).to_have_attribute("aria-expanded", "true")
    assert region.evaluate("(element) => element.getBoundingClientRect().height") <= TITLE_EXPANDED_MAX_PX
    assert region.evaluate("(element) => element.scrollHeight > element.clientHeight")
    expect(_panel(page).locator("article[data-post-id='TH-1-1']")).to_be_visible()
    # 実行（折りたたむ）
    _panel(page).get_by_role("button", name="タイトルを折りたたむ").click()
    # 検証（折りたたむ）
    expect(title).to_have_attribute("data-clamped", "")


@pytest.mark.parametrize("narrowed", [pytest.param(False, id="width-360"), pytest.param(True, id="panel-320")])
@pytest.mark.parametrize("expanded", [pytest.param(False, id="clamped"), pytest.param(True, id="expanded")])
def test_long_title_no_horizontal_scroll(
    page: Page,
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    narrowed: bool,
    expanded: bool,
) -> None:
    """3000 文字を超える書き込みのスレッドの見出しは、2 行の省略でも全文でも、幅 360px と最も狭めたパネルでパネルの右端を超えない（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("D-1"), threads=(_first_long_post_thread(make_post, make_thread),))
    page.set_viewport_size(WIDE_SIZE if narrowed else NARROWEST_SIZE)
    open_spa(page, url, "?tab=decisions&panel=comments&thread=TH-1")
    if narrowed:
        narrow_left_panel(page)
    # 実行
    if expanded:
        _panel(page).get_by_role("button", name="タイトルの続きを表示").click()
    # 検証
    title = _panel(page).locator("[data-part='thread-title']")
    assert title.evaluate("(element) => element.getBoundingClientRect().right") <= _panel(page).evaluate("(element) => element.getBoundingClientRect().right")
    assert_no_horizontal_scroll(page, _panel(page))


def test_title_id_links(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """スレッドの見出しのタイトルの中の記録にある D-1 をリンクにし、乗せるとツールチップを出し、押すと D-1 の詳細を開く（正常系）。"""
    # 準備
    _open(page, spa_comments_preview, "TH-1")
    link = _panel(page).locator("[data-part='thread-title']").get_by_role("link", name="D-1")
    # 実行
    link.hover()
    # 検証
    expect(link).to_have_attribute("href", "#id=D-1")
    assert_tip(page, "最初の問い")
    link.click()
    expect(page).to_have_url(re.compile(r"id=D-1"))


@pytest.mark.parametrize("narrowed", [pytest.param(False, id="width-360"), pytest.param(True, id="panel-320")])
def test_no_horizontal_scroll(
    page: Page,
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    narrowed: bool,
) -> None:
    """1 スレッドの書き込み 50 件（3000 文字を超える書き込みと改行の無い長い URL を含む）を、幅 360px と、幅 1440px で左のパネルを下限の 320px にして開いても、ページもパネルも横にスクロールしない（正常系）。"""
    # 準備
    posts = [
        make_post(f"TH-1-{n}", author="ai" if n % 2 == 0 else "user", body=LONG_POST_BODY if n in (1, 25, 50) else f"{n} 件目の書き込み", read=True)
        for n in range(1, 51)
    ]
    url, _ = write_review_preview(make_item("D-1"), threads=(make_thread("TH-1", *posts, summary="長い相談", target="D-1"),))
    page.set_viewport_size(WIDE_SIZE if narrowed else NARROWEST_SIZE)
    # 実行
    open_spa(page, url, "?tab=decisions&panel=comments&thread=TH-1")
    if narrowed:
        narrow_left_panel(page)
        expect(_panel(page).get_by_role("separator", name="コメントの一覧の幅")).to_have_attribute("aria-valuenow", "320")
    expect(_panel(page).locator("article")).to_have_count(50)
    # 検証
    assert_no_horizontal_scroll(page, _panel(page))


def test_post_id_touch_action(browser: Browser, write_review_preview: WriteReviewPreview, make_item: MakeItem, make_post: MakePost, make_thread: MakeThread) -> None:
    """指でスレッドの書き込みの中の項目の ID のボタンを押すと、ツールチップを出さずに 1 回でその項目の詳細パネルを開く（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("D-1", title="最初の問い"), threads=(make_thread("TH-1", make_post("TH-1-1", author="ai", body="D-1 を確認してください。", read=True), summary="D-1 の相談"),))
    context = browser.new_context(has_touch=True, is_mobile=True, viewport=TOUCH_VIEWPORT)
    page = context.new_page()
    open_spa(page, url, "?tab=decisions&panel=comments&thread=TH-1")
    button = page.locator("article[data-post-id='TH-1-1'] button.idlink", has_text="D-1")
    # 実行
    button.tap()
    # 検証
    expect(page).to_have_url(re.compile(r"id=D-1"))
    expect(page.locator("[popover]:popover-open")).to_have_count(0)
    context.close()


def test_removed_style(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """削除した書き込みの行は左の線だけで示し、カードの見た目（枠線・角丸・背景色の組）を重ねない（正常系）。"""
    # 準備
    _open(page, spa_comments_preview, "TH-1")
    # 実行
    _panel(page).get_by_role("button", name="TH-1 への返信を削除").click()
    row = _panel(page).locator("li:has(> [role=status])").filter(has_text="コメントを削除しました。")
    # 検証
    style = row.evaluate(
        "e => { const s = getComputedStyle(e); return [s.borderLeftWidth !== '0px', s.borderTopWidth, s.borderRadius, s.backgroundColor]; }"
    )
    assert style == [True, "0px", "0px", "rgba(0, 0, 0, 0)"]
