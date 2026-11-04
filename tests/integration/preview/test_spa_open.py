"""インターフェース定義『SPAを開く』の結合テスト。"""

from __future__ import annotations

import time
from typing import Any

from playwright.sync_api import Page
from preview_fixture_types import WriteReviewPreview
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
    opened_url = page.url
    scroll_top = page.evaluate(SCROLL_TOP_SCRIPT)
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
    # 準備
    root = make_workspace(make_item("D-1"), settings={**valid_settings, "preview": {"port": free_port()}})
    server = start_server()
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
