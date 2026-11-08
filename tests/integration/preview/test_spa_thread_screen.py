"""画面設計『スレッド.tsx』の結合テスト。"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Locator, Page, expect
from preview_comment_helpers import free_comment, read_workspace_yaml
from preview_fixture_types import WriteReviewPreview
from preview_spa_helpers import open_spa
from workspace_fixtures import MakeComment, MakeItem, MakePost, MakeThread

# 書き込みを待つ上限ミリ秒
UPDATE_TIMEOUT_MS = 10_000

# 5 行を超えるレビュー中の返信の本文
LONG_REPLY = "\n\n".join(f"{index} 行目の返信" for index in range(1, 9))


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
    expect(_panel(page).get_by_role("alert")).to_have_text("クローズにできませんでした。サーバーが止まっています。立ち上げ直してから押してください。")
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
    """まだ送っていない新しいスレッドは「まだ送っていないスレッドです。」を出し、状態を変えるボタンと返信の入力を出さない（正常系）。"""
    # 準備・実行
    _open(page, spa_comments_preview, "C-41")
    # 検証
    expect(_panel(page)).to_contain_text("まだ送っていないスレッドです。")
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
    """5 行を超えるレビュー中の返信は畳んで「続きを読む」を出し、押すと開いて「折りたたむ」にする（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("D-1"),
        threads=(make_thread("TH-1", make_post("TH-1-1", body="質問")),),
        comments=(free_comment(make_comment("C-43", body=LONG_REPLY, thread="TH-1")),),
    )
    open_spa(page, url, "?tab=decisions&panel=comments&thread=TH-1")
    more = _panel(page).get_by_role("button", name="TH-1 への返信の続きを読む")
    # 検証
    expect(more).to_have_text("続きを読む")
    # 実行
    more.click()
    # 検証
    expect(_panel(page).get_by_role("button", name="TH-1 への返信の本文を折りたたむ")).to_have_text("折りたたむ")
