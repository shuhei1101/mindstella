"""インターフェース定義『SPAを開く』の結合テスト。"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import yaml

from playwright.sync_api import Page, Route, expect
from preview_fixture_types import WritePreview, WriteReviewPreview
from preview_spa_helpers import SPA_ROOT_PATH, open_spa, watch_console
from workspace_fixtures import (
    RECORD_DIR,
    CallTool,
    MakeComment,
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
    StartServer,
    free_port,
)

# 書き換えの知らせ・接続の状態を待つ上限ミリ秒
UPDATE_TIMEOUT_MS = 10_000

# 書き換えてから画面に出るまでの上限秒数（非機能要件『画面への反映の時間』）
REFLECT_LIMIT_SEC = 2.0

# トップバーの開いている画面のタブ
CURRENT_TAB = 'nav[aria-label="項目の種類"] a[aria-current="page"]'

# タブの帯の検討事項のタブの件数
DECISIONS_COUNT = 'nav[aria-label="項目の種類"] a[data-tab="decisions"] > span'

# トップバーの接続の状態
CONNECTION = 'header [role="status"]'

# 本文の区画のスクロールの位置を読む
SCROLL_TOP_SCRIPT = "document.querySelector('main#main').scrollTop"

# 本文の区画をスクロールの範囲の中ほどへ送り、送った後の位置を返す
SCROLL_TO_MIDDLE_SCRIPT = """() => {
    const main = document.querySelector('main#main');
    main.scrollTop = Math.floor((main.scrollHeight - main.clientHeight) / 2);
    return main.scrollTop;
}"""

# 本文の区画が縦にスクロールする窓の高さ
SCROLLABLE_HEIGHT = 360

# 足す検討事項
NEW_DECISION = {
    "title": "新しい問い",
    "target": "mindmap",
    "category": "データ構造",
    "phase": "要件",
    "status": "未決定",
    "options": [{"key": "A", "content": "案 A"}],
}


def test_normal(
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_thread: MakeThread,
    make_post: MakePost,
    page: Page,
) -> None:
    """`/spa/` を開くと、記録を読んでトップバーと概要を描く（正常系）。"""
    # 準備
    url, _root = write_review_preview(
        make_item("D-1"),
        make_item("D-2"),
        make_item("T-1", status="進行中"),
        comments=(make_comment("C-1"), make_comment("C-2")),
        threads=(make_thread("TH-1", make_post("TH-1-1", seen=False)),),
    )
    console = watch_console(page)
    # 実行
    open_spa(page, url)
    page.wait_for_selector("#tile-running")
    # 検証
    assert page.get_attribute("header span[title]", "title") == "要件出しのスキル mindmap を設計する"
    assert page.get_attribute(CURRENT_TAB, "data-tab") == "overview"
    assert "T-1の題" in page.inner_text("#tile-running")
    assert "D-1の題" in page.inner_text("#tile-next")
    assert page.get_attribute('header button[aria-label^="コメント"]', "aria-label") == (
        "コメント（未読あり・レビュー中 2 件）"
    )
    assert page.evaluate("location.pathname + location.search") == SPA_ROOT_PATH
    assert console.messages == []
    assert console.exceptions == []


def test_normal_when_records_changed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    page: Page,
) -> None:
    """ツールで記録を書き換えると、開き直さずに概要を描き直す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    open_spa(page, served.data["url"])
    page.wait_for_selector(f"{DECISIONS_COUNT}:text-is('1')")
    page.set_viewport_size({"width": 1280, "height": SCROLLABLE_HEIGHT})
    page.wait_for_function(f"innerHeight === {SCROLLABLE_HEIGHT}")
    opened_url = page.url
    scroll_top = page.evaluate(SCROLL_TO_MIDDLE_SCRIPT)
    assert scroll_top > 0
    # 実行
    added = call_tool("add", workspace=str(root), kind="decision", item=NEW_DECISION)
    started = time.monotonic()
    page.wait_for_selector(f"{DECISIONS_COUNT}:text-is('2')", timeout=UPDATE_TIMEOUT_MS)
    elapsed = time.monotonic() - started
    # 検証
    assert added.is_error is False, added.text
    assert elapsed <= REFLECT_LIMIT_SEC
    assert page.url == opened_url
    assert page.evaluate(SCROLL_TOP_SCRIPT) == scroll_top


def test_normal_when_search_invalid(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    page: Page,
) -> None:
    """`tab` が決めた値でなければ概要を開き、URL から外す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    # 実行
    open_spa(page, served.data["url"], "?tab=unknown")
    page.wait_for_selector("#tile-next")
    # 検証
    assert page.get_attribute(CURRENT_TAB, "data-tab") == "overview"
    assert page.evaluate("new URLSearchParams(location.search).has('tab')") is False


def test_error_when_records_invalid(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    page: Page,
) -> None:
    """記録がスキーマに合わず読めないとき、読めなかった箇所を画面に出す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", status="不明"))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    console = watch_console(page)
    # 実行
    open_spa(page, served.data["url"])
    # 検証
    alert = page.inner_text('main#main section[role="alert"]')
    assert "記録を読めませんでした" in alert
    assert "decisions.yaml" in alert
    assert "status" in alert
    assert page.locator("#tile-next").count() == 0
    assert console.exceptions == []


def test_error_when_server_stopped(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    start_server: StartServer,
    page: Page,
) -> None:
    """書き換えの知らせが切れたら、トップバーに接続が切れたことを出し、立ち上がり直すとつなぎ直す（異常系）。"""
    # 準備（常駐サーバーがポートを掴んだ後に、配信のポートを選ぶ）
    server = start_server()
    root = make_workspace(make_item("D-1"), settings={**valid_settings, "preview": {"port": free_port()}})
    served = server.call("preview_url", workspace=str(root))
    assert served.data is not None
    open_spa(page, served.data["url"])
    page.wait_for_selector("#tile-next")
    # 実行（server_stop で常駐サーバーを止める）
    server.call("server_stop")
    server.wait_exit()
    page.wait_for_selector(CONNECTION, timeout=UPDATE_TIMEOUT_MS)
    stopped_tile = page.inner_text("#tile-next")
    restarted = start_server().call("preview_url", workspace=str(root))
    page.wait_for_selector(CONNECTION, state="detached", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert "D-1の題" in stopped_tile
    assert restarted.data is not None
    assert restarted.data["url"] == served.data["url"]
    assert "D-1の題" in page.inner_text("#tile-next")


def test_normal_when_list_screen(page: Page, spa_preview: str) -> None:
    """`tab` の一覧の画面を描く（正常系）。"""
    open_spa(page, spa_preview, "?tab=tasks")
    expect(page.get_by_role("group", name="表示形式")).to_be_visible()
    expect(page.get_by_text("画面を作る")).to_be_visible()


def test_normal_when_item(page: Page, spa_preview: str) -> None:
    """`id` の項目を詳細パネルで開く（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    expect(page.get_by_role("complementary", name="詳細")).to_contain_text("記録の形")


def test_normal_when_search_mismatched(page: Page, spa_preview: str) -> None:
    """記録・画面に合わない値を外す（正常系）。"""
    open_spa(page, spa_preview, "?tab=tasks&view=map&id=T-99")
    page.wait_for_url("**/spa/?tab=tasks")


def test_normal_when_filter(page: Page, spa_preview: str) -> None:
    """`f.{列}` の条件で開き、端末に残す（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&view=table&f.status=%E4%BF%9D%E7%95%99")
    expect(page.get_by_role("cell", name="画面の幅")).to_be_visible()
    assert "保留" in page.evaluate("localStorage.getItem('mindmap-preview')")


def test_normal_when_diff(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """`diff` の時点の差分を出す（正常系）。"""
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions&diff=V-2&id=D-1")
    expect(page.get_by_role("complementary", name="詳細")).to_contain_text("新しい段落を足しました")


def test_normal_when_diff_missing(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """記録に無い時点は外す（正常系）。"""
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions&diff=V-99")
    page.wait_for_function("!location.search.includes('V-99')")


def test_normal_when_since(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """「前回開いてから」は同じタブで `POST /api/opened` を呼び直さない（正常系）。"""
    url, _ = write_history_preview()
    calls: list[str] = []
    page.on("request", lambda request: calls.append(request.url) if request.url.endswith("/api/opened") else None)
    open_spa(page, url, "?tab=decisions&diff=since")
    page.wait_for_function("sessionStorage.getItem('mindmap-preview-opened') !== null")
    open_spa(page, url, "?tab=tasks&diff=since")
    page.wait_for_load_state("networkidle")
    assert len(calls) == 1


def test_normal_when_records_changed_with_item(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool, page: Page) -> None:
    """書き換えの知らせで、開いている項目を保ったまま描き直す（正常系）。"""
    root = make_workspace(make_item("D-1"))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    open_spa(page, served.data["url"], "?tab=decisions&id=D-1")
    panel = page.get_by_role("complementary", name="詳細")
    panel.wait_for()
    call_tool("update", workspace=str(root), id="D-1", item={"title": "書き換えた題"})
    expect(panel.get_by_role("heading", name="書き換えた題")).to_be_visible()


def test_normal_when_legacy_screen(page: Page, spa_preview: str) -> None:
    """React に無いネットワークは今の画面を開く（正常系）。"""
    open_spa(page, spa_preview, "?tab=tasks")
    page.get_by_role("link", name="ネットワーク").click()
    page.wait_for_url("**/mindstella.html#tab=graph")


def test_normal_when_edits_saved(page: Page, spa_preview: str) -> None:
    """編集を溜めてまとめて保存すると、記録へ書き込む（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&id=D-1")
    page.get_by_role("button", name="編集する").click()
    title = page.get_by_role("textbox", name="タイトル")
    title.fill("保存した題")
    title.blur()
    page.get_by_role("button", name="保存待ち").first.click()
    page.get_by_role("complementary", name="保存待ちの編集").get_by_role("button", name="まとめて保存する").click()
    expect(page.get_by_role("status").filter(has_text="1 件を保存しました")).to_be_visible()


def test_normal_when_item_added_and_removed(page: Page, spa_preview: str) -> None:
    """一覧から足した項目を保存し、詳細から消す編集を保存する（正常系）。"""
    open_spa(page, spa_preview, "?tab=tasks")
    page.get_by_role("button", name="タスクの項目を追加").click()
    title = page.get_by_role("complementary", name="タスクを追加").get_by_role("textbox", name="タイトル")
    title.fill("足すタスク")
    title.blur()
    expect(page.locator("[data-new-id]")).to_be_visible()
    page.get_by_role("button", name="保存待ち").first.click()
    page.get_by_role("complementary", name="保存待ちの編集").get_by_role("button", name="まとめて保存する").click()
    card = page.locator("[data-id]").filter(has_text="足すタスク")
    expect(card).to_be_visible()
    card.click()
    page.get_by_role("button", name="編集する").click()
    page.get_by_role("button", name="項目を削除").click()
    expect(page.get_by_role("button", name="削除を取り消す")).to_be_visible()


def test_normal_when_settings(page: Page, spa_preview: str) -> None:
    """設定の画面で題名を書き換えて保存する（正常系）。"""
    open_spa(page, spa_preview, "?tab=settings")
    title = page.get_by_role("textbox", name="題名")
    title.fill("新しい題名")
    title.blur()
    page.get_by_role("button", name="保存待ち").first.click()
    page.get_by_role("complementary", name="保存待ちの編集").get_by_role("button", name="まとめて保存する").click()
    expect(page.locator("header")).to_contain_text("新しい題名")


def test_error_when_library_unavailable(page: Page, write_preview: WritePreview, make_item: MakeItem) -> None:
    """描画のライブラリが読めないとき、原文とライブラリの名前を出す（異常系）。"""
    url = write_preview(make_item("D-1", title="本文あり", status="未決定", body="D-1.md"), bodies={"D-1.md": "本文の原文"})

    def _abort(route: Route) -> None:
        """mdmark の取得を止める。"""
        route.abort()

    page.route("**/mdmark@*/**", _abort)
    open_spa(page, url, "?tab=decisions&id=D-1")
    panel = page.get_by_role("complementary", name="詳細")
    expect(panel).to_contain_text("本文の原文")
    expect(panel).to_contain_text("mdmark")


def test_error_when_save_blocked(page: Page, spa_preview: str) -> None:
    """保存が 409 のとき、溜めた編集を残して書き込めない編集を知らせる（異常系）。"""
    open_spa(page, spa_preview, "?tab=settings")
    title = page.get_by_role("textbox", name="題名")
    title.fill("断られる題名")
    title.blur()
    page.get_by_role("button", name="保存待ち").first.click()
    panel = page.get_by_role("complementary", name="保存待ちの編集")
    row = panel.locator("li[id^='pe-row-']")
    row.wait_for()
    edit_id = (row.get_attribute("id") or "").removeprefix("pe-row-")

    def _refuse(route: Route) -> None:
        """まとめて保存を 409 で断る。"""
        blocked = [{"id": edit_id, "reason": "invalid", "detail": "書き込めない理由", "refs": []}]
        body = {"type": "about:blank", "title": "Conflict", "status": 409, "detail": "x", "blocked": blocked}
        route.fulfill(status=409, content_type="application/problem+json", body=json.dumps(body))

    page.route("**/api/edits/save", _refuse)
    panel.get_by_role("button", name="まとめて保存する").click()
    expect(panel.get_by_role("alert")).to_contain_text("何も保存していません")
    expect(row).to_be_visible()



# ─── コメントと表示の設定 ───

# 本文が 3 行の資料の本文
THREE_LINE_BODY = "一行目の文\n二行目の文\n三行目の文\n"

# 本文の中の文字を選び、選び終えたことを知らせる（文字を持つ本文のテキストの中の範囲）
SELECT_TEXT_JS = """(text) => {
  const walker = document.createTreeWalker(document.querySelector('.md'), NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  while (node !== null && !node.textContent.includes(text)) node = walker.nextNode();
  const start = node.textContent.indexOf(text);
  const range = document.createRange();
  range.setStart(node, start);
  range.setEnd(node, start + text.length);
  const selection = getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
  node.parentElement.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }));
}"""

# トップバーのコメントのボタン（読み上げの名前に件数を持つ）
COMMENTS_BUTTON = 'header button[aria-label^="コメント（"]'

# 端末の保存領域のキー
PREFS_KEY = "mindmap-preview"


def _history_length(page: Page) -> int:
    """ブラウザの履歴の数を返す。"""
    return int(page.evaluate("history.length"))


def _workspace_yaml(root: Path, name: str) -> Any:
    """ワークスペースの記録のフォルダの YAML を返す（無ければ None）。"""
    path = root / RECORD_DIR / name
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None


def test_normal_when_comment_sent(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem, call_tool: CallTool) -> None:
    """詳細の本文の文を選んで箇所を添えたコメントを溜め、コメントの一覧のレビュー中の書き込みからまとめて送る（正常系）。"""
    # 準備
    url, root = write_review_preview(make_item("A-1", title="手引き"), bodies={"A-1.md": THREE_LINE_BODY})
    errors = watch_console(page)
    open_spa(page, url, "?tab=docs&id=A-1")
    panel = page.get_by_role("complementary", name="詳細")
    expect(panel.locator(".md")).to_contain_text("二行目の文")
    # 実行（本文の 2 行目の文を選び、入口からコメントを溜める）
    page.evaluate(SELECT_TEXT_JS, "二行目の文")
    page.get_by_role("button", name="選んだ箇所にコメント").click()
    field = panel.get_by_role("textbox", name="A-1 へのコメント")
    field.fill("ここを言い換える")
    field.press("Control+Enter")
    # 検証
    expect(panel.locator("li[data-comment]")).to_have_count(1)
    expect(panel.locator("li[data-comment]")).to_contain_text("本文 2 行目")
    expect(page.locator(COMMENTS_BUTTON)).to_have_attribute("aria-label", "コメント（レビュー中 1 件）")
    # 実行（コメントのボタン・「レビュー中」を押す）
    before = _history_length(page)
    page.locator(COMMENTS_BUTTON).click()
    page.wait_for_url("**panel=comments**")
    page.get_by_role("dialog", name="コメント").get_by_role("button", name="レビュー中の書き込みを確かめる（1 件）").click()
    page.wait_for_url("**review=1**")
    # 検証
    assert _history_length(page) == before
    # 実行（まとめて送る）
    page.get_by_role("dialog", name="コメント").get_by_role("button", name="まとめて送る（1 件）").click()
    # 検証
    expect(page.get_by_role("dialog", name="コメント").get_by_role("status").filter(has_text="1 件を送り")).to_be_visible()
    expect(page.locator(COMMENTS_BUTTON)).to_have_attribute("aria-label", "コメント（レビュー中 0 件）")
    awaiting = call_tool("threads", workspace=str(root), awaiting=True)
    assert awaiting.data is not None
    assert [(item["target"], item["head"]) for item in awaiting.data["items"]] == [("A-1", "ここを言い換える")]
    threads = _workspace_yaml(root, "threads.yaml")["items"]
    assert threads[0]["loc"]["start"] == 2
    assert errors.messages == []
    assert errors.exceptions == []


def test_normal_when_thread_replied_and_closed(
    page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem, make_post: MakePost, make_thread: MakeThread
) -> None:
    """`thread` が指すスレッドを開いて既読にし、返信を溜め、理由を添えてクローズにする（正常系）。"""
    # 準備
    url, root = write_review_preview(
        make_item("D-1"),
        threads=(make_thread("TH-1", make_post("TH-1-1", body="質問"), make_post("TH-1-2", author="ai", body="答え", seen=False), summary="相談"),),
    )
    # 実行（開く。既読にする要求の応答を待つ）
    with page.expect_response(lambda response: response.url.endswith("/api/threads/TH-1/seen") and response.request.method == "POST"):
        open_spa(page, url, "?panel=comments&thread=TH-1")
    panel = page.get_by_role("dialog", name="コメント")
    # 検証
    expect(page.locator(COMMENTS_BUTTON)).to_have_attribute("aria-label", "コメント（レビュー中 0 件）", timeout=UPDATE_TIMEOUT_MS)
    assert [post["seen"] for post in _workspace_yaml(root, "threads.yaml")["items"][0]["posts"]] == [True, True]
    # 実行（返信を溜める）
    reply = panel.get_by_role("textbox", name="返信")
    reply.fill("了解")
    reply.press("Control+Enter")
    # 検証
    expect(panel.locator("ol > li > article").last).to_contain_text("了解")
    assert [item["thread"] for item in _workspace_yaml(root, "comments.yaml")["items"]] == ["TH-1"]
    # 実行（理由を添えてクローズにする）
    panel.get_by_role("button", name="クローズにする").click()
    panel.get_by_role("textbox", name="理由（任意）").fill("決まった")
    panel.get_by_role("button", name="クローズにする").click()
    # 検証
    expect(panel).to_contain_text("クローズにしたスレッドです。")
    thread = _workspace_yaml(root, "threads.yaml")["items"][0]
    assert thread["status"] == "closed"
    assert thread["events"][-1]["reason"] == "決まった"
    # 実行（一覧へ戻る）
    before = _history_length(page)
    panel.get_by_role("button", name="一覧へ戻る").click()
    # 検証
    expect(panel.get_by_role("group", name="スレッドの状態で絞る")).to_be_visible()
    assert "thread=" not in page.url
    assert _history_length(page) == before


def test_normal_when_comment_draft_restored(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem) -> None:
    """コメントの入力欄の書きかけをサーバーに保ち、読み込み直すと同じ入力欄に戻す（正常系）。"""
    # 準備
    url, root = write_review_preview(make_item("D-1"))
    open_spa(page, url, "?tab=decisions&id=D-1")
    field = page.get_by_role("complementary", name="詳細").get_by_role("textbox", name="D-1 へのコメント")
    # 実行（書いて入力を止め、書きかけの保存を待つ）
    with page.expect_response(lambda response: response.url.endswith("/api/drafts") and response.request.method == "PUT"):
        field.fill("書きかけの文")
    # 検証
    assert [(draft["target"], draft["body"]) for draft in _workspace_yaml(root, "drafts.yaml")["items"]] == [("D-1", "書きかけの文")]
    # 実行（読み込み直す）
    page.reload()
    # 検証
    expect(page.get_by_role("complementary", name="詳細").get_by_role("textbox", name="D-1 へのコメント")).to_have_value("書きかけの文")


def test_normal_when_display_settings(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem) -> None:
    """表示の設定のパネルで表示する種類を個人の上書きとして変え、既定の保存の確かめを経てワークスペースの既定にする（正常系）。"""
    # 準備
    url, root = write_review_preview(make_item("D-1"), make_item("N-1"))
    config_before = (root / RECORD_DIR / "config.yaml").read_bytes()
    open_spa(page, url, "?tab=notes&panel=display")
    panel = page.get_by_role("dialog", name="表示の設定")
    before = _history_length(page)
    # 実行（メモを外す）
    panel.get_by_role("checkbox", name="メモ").click()
    # 検証
    expect(page.get_by_role("navigation", name="項目の種類").get_by_role("link", name="メモ")).to_have_count(0)
    page.wait_for_function("() => !location.search.includes('tab=')")
    assert _history_length(page) == before
    prefs = json.loads(page.evaluate(f"localStorage.getItem('{PREFS_KEY}')"))
    assert "notes" not in prefs["kinds"]
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == config_before
    # 実行（ワークスペースの既定にする）
    panel.get_by_role("button", name="ワークスペースの既定にする").click()
    dialog = page.get_by_role("dialog", name="ワークスペースの既定を書き換えますか")
    # 検証
    expect(dialog).to_contain_text("すべて表示")
    expect(dialog).to_contain_text("メモを表示しない")
    # 実行（保存する）
    dialog.get_by_role("button", name="保存する").click()
    # 検証
    expect(panel.locator("[data-part=message]")).to_contain_text("ワークスペースの既定にしました（")
    assert "notes" not in _workspace_yaml(root, "config.yaml")["display"]["visible_kinds"]
    # 実行（設定を編集する）
    panel.get_by_role("button", name="設定を編集する").click()
    # 検証
    page.wait_for_url("**tab=settings**")
    expect(panel).to_have_count(0)


def test_normal_when_comment_search_mismatched(
    page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem, make_thread: MakeThread
) -> None:
    """無いスレッド・無いタグを指す値と、コメントの一覧を開いていないときのコメントの値を外して開く（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("D-1"), threads=(make_thread("TH-1", tags=["画面"]),))
    # 実行
    open_spa(page, url, "?panel=comments&thread=TH-99&ttag=無いタグ")
    # 検証
    expect(page.get_by_role("dialog", name="コメント").get_by_role("group", name="スレッドの状態で絞る")).to_be_visible()
    page.wait_for_function("() => location.search === '?panel=comments'")
    # 実行
    open_spa(page, url, "?tab=decisions&thread=TH-1&review=1")
    # 検証
    page.wait_for_function("() => location.search === '?tab=decisions'")
    expect(page.get_by_role("dialog", name="コメント")).to_have_count(0)


def test_error_when_comment_body_empty(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem) -> None:
    """空白だけの本文は溜めずに理由を出す（異常系）。"""
    # 準備
    url, root = write_review_preview(make_item("D-1"))
    open_spa(page, url, "?tab=decisions&id=D-1")
    panel = page.get_by_role("complementary", name="詳細")
    posted: list[str] = []
    page.on("request", lambda request: posted.append(request.url) if request.method == "POST" and request.url.endswith("/api/comments") else None)
    # 実行
    field = panel.get_by_role("textbox", name="D-1 へのコメント")
    field.fill("   ")
    field.press("Control+Enter")
    # 検証
    expect(panel.locator("form[data-id='D-1'] [role=status]")).to_have_text("コメントを入れてから追加してください。")
    assert posted == []
    expect(page.locator(COMMENTS_BUTTON)).to_have_attribute("aria-label", "コメント（レビュー中 0 件）")
    assert _workspace_yaml(root, "comments.yaml") is None


def test_error_when_comment_server_unreachable(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any], start_server: StartServer, page: Page
) -> None:
    """サーバーが止まった後に溜めると、本文を残して届かなかった理由を出す（異常系）。"""
    # 準備（常駐サーバーがポートを掴んだ後に、配信のポートを選ぶ）
    server = start_server()
    root = make_workspace(make_item("D-1"), settings={**valid_settings, "preview": {"port": free_port()}})
    served = server.call("preview_url", workspace=str(root))
    assert served.data is not None
    errors = watch_console(page)
    open_spa(page, served.data["url"], "?tab=decisions&id=D-1")
    panel = page.get_by_role("complementary", name="詳細")
    field = panel.get_by_role("textbox", name="D-1 へのコメント")
    # 実行（server_stop で常駐サーバーを止めてから溜める）
    server.call("server_stop")
    server.wait_exit()
    field.fill("止まった後のコメント")
    panel.get_by_role("button", name="レビューに追加").click()
    # 検証
    expect(panel.locator("form[data-id='D-1'] [role=status]")).to_contain_text("サーバーが止まっています。")
    expect(field).to_have_value("止まった後のコメント")
    expect(panel.get_by_role("button", name="レビューに追加")).to_be_enabled()
    assert errors.exceptions == []


def test_error_when_comment_send_stale(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem, make_comment: MakeComment, call_tool: CallTool) -> None:
    """まとめて送るの 409 では、箇所が合わない書き込みの行に理由を出し、どれも送らない（異常系）。"""
    # 準備
    url, root = write_review_preview(
        make_item("A-1", title="手引き"),
        comments=(make_comment("C-1", target="A-1", loc={"kind": "body", "start": 3, "end": 3, "text": "三行目の文"}, body="言い換える"),),
        bodies={"A-1.md": THREE_LINE_BODY},
    )
    errors = watch_console(page)
    open_spa(page, url, "?panel=comments&review=1")
    panel = page.get_by_role("dialog", name="コメント")
    expect(panel.locator("li[data-comment='C-1']")).to_be_visible()
    # 実行（A-1 の本文を 1 行にしてから、まとめて送る）
    updated = call_tool("update", workspace=str(root), id="A-1", item={"body_markdown": "一行だけ\n"})
    assert updated.is_error is False, updated.text
    panel.get_by_role("button", name="まとめて送る（1 件）").click()
    # 検証
    row = panel.locator("li[data-comment='C-1']")
    expect(row.get_by_role("alert")).to_be_visible()
    expect(row.get_by_role("button", name="箇所を外す")).to_be_visible()
    assert [item["id"] for item in _workspace_yaml(root, "comments.yaml")["items"]] == ["C-1"]
    assert (_workspace_yaml(root, "threads.yaml") or {"items": []})["items"] == []
    assert errors.exceptions == []
