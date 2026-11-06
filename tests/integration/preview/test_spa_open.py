"""インターフェース定義『SPAを開く』の結合テスト。"""

from __future__ import annotations

import json
import time
from typing import Any

from playwright.sync_api import Page, Route, expect
from preview_fixture_types import WritePreview, WriteReviewPreview
from preview_spa_helpers import SPA_ROOT_PATH, open_spa, watch_console
from workspace_fixtures import (
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

