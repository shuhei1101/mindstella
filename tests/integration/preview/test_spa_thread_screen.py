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

from playwright.sync_api import Locator, Page, expect
from preview_comment_helpers import free_comment, read_workspace_yaml
from preview_fixture_types import WriteReviewPreview
from preview_pending_helpers import assert_waiting, hold_requests, press_twice
from preview_spa_helpers import open_spa
from workspace_fixtures import MakeComment, MakeItem, MakePost, MakeThread, WriteComments

# 書き込みを待つ上限ミリ秒
UPDATE_TIMEOUT_MS = 10_000

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
    """「クローズにする」を押すと理由の入力を出して入力欄へフォーカスを移し、その間はボタンを出さない（正常系）。"""
    # 準備
    _open(page, spa_comments_preview, "TH-2")
    # 実行
    _panel(page).get_by_role("button", name="クローズにする").click()
    # 検証
    expect(_panel(page).get_by_role("textbox", name="理由（任意）")).to_be_focused()
    expect(_panel(page).get_by_role("button", name="クローズにする")).to_have_count(1)


def test_reason_input(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """理由を書いて確定すると状態と理由を書き、状態の札と記録を描き直して「オープンに戻す」へフォーカスを戻す（正常系）。"""
    # 準備
    _, root = spa_comments_preview
    _open(page, spa_comments_preview, "TH-2")
    _panel(page).get_by_role("button", name="クローズにする").click()
    # 実行
    _panel(page).get_by_role("textbox", name="理由（任意）").fill("済んだ")
    _panel(page).get_by_role("button", name="クローズにする").click()
    # 検証
    expect(_panel(page).get_by_role("button", name="オープンに戻す")).to_be_focused()
    expect(_panel(page).locator("[data-state=closed]")).to_have_text("クローズ")
    expect(_panel(page).locator("article[data-event=closed]")).to_contain_text("済んだ")
    threads = {thread["id"]: thread for thread in read_workspace_yaml(root, "threads.yaml")["items"]}
    assert threads["TH-2"]["status"] == "closed"
    assert threads["TH-2"]["events"][-1]["reason"] == "済んだ"



def test_normal_when_pressed_again_while_closing(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """クローズを待つ間にもう一度押しても要求は 1 回で、待つ間は確定が押せず、1 秒を超えると回るマーカーを出す（正常系）。"""
    # 準備
    _, root = spa_comments_preview
    _open(page, spa_comments_preview, "TH-2")
    _panel(page).get_by_role("button", name="クローズにする").click()
    _panel(page).get_by_role("textbox", name="理由（任意）").fill("済んだ")
    held = hold_requests(page, "**/api/threads/*", "PATCH")
    button = _panel(page).get_by_role("button", name="クローズにする")
    box = button.bounding_box()
    assert box is not None
    # 実行（再描画の前に 2 回押す）
    press_twice(button)
    # 検証
    assert_waiting(page, button, held, box["width"])
    held.release()
    expect(_panel(page).locator("[data-state=closed]")).to_have_text("クローズ")
    expect(_panel(page).locator("article[data-event=closed]")).to_have_count(1)
    threads = {thread["id"]: thread for thread in read_workspace_yaml(root, "threads.yaml")["items"]}
    assert [event["kind"] for event in threads["TH-2"]["events"]].count("closed") == 1

def test_reason_input_when_cancel(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """理由の入力の Esc は理由の入力を閉じて「状態を変える」へフォーカスを戻し、一覧へは戻らない（正常系）。"""
    # 準備
    _open(page, spa_comments_preview, "TH-2")
    _panel(page).get_by_role("button", name="クローズにする").click()
    # 実行
    page.keyboard.press("Escape")
    # 検証
    expect(_panel(page).get_by_role("textbox", name="理由（任意）")).to_have_count(0)
    expect(_panel(page).get_by_role("button", name="クローズにする")).to_be_focused()
    assert "thread=TH-2" in page.url


def test_status_failed(page: Page, spa_comments_preview: tuple[str, Path]) -> None:
    """状態を書き換えられなかったとき、理由を `role="alert"` で出し、理由の入力は開いたまま残す（異常系）。"""
    # 準備
    _open(page, spa_comments_preview, "TH-2")
    page.route("**/api/threads/TH-2", lambda route: route.abort())
    _panel(page).get_by_role("button", name="クローズにする").click()
    # 実行
    _panel(page).get_by_role("textbox", name="理由（任意）").press("Control+Enter")
    # 検証
    expect(_panel(page).get_by_role("alert")).to_have_text("クローズにできませんでした。サーバーが止まっています。再起動してから押してください。")
    expect(_panel(page).get_by_role("textbox", name="理由（任意）")).to_be_visible()


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

