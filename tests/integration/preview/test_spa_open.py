"""インターフェース定義『SPAを開く』の結合テスト。"""

from __future__ import annotations

from record_write_helpers import call_or_write, write_tool
import json
import re
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
import yaml

from playwright.sync_api import Page, Route, expect
from preview_fixture_types import BODY_WITH_DIAGRAM, WritePreview, WriteReviewPreview
from preview_embedded_files_helpers import EMBEDDED_FILES_BODY, put_embedded_files
from preview_spa_helpers import SPA_CONTENT_SELECTOR, SPA_RENDER_TIMEOUT_MS, open_spa, spa_url, watch_console
from workspace_fixtures import (
    PORT_ENV,
    RECORD_DIR,
    CallTool,
    MakeComment,
    MakeItem,
    MakePost,
    MakeThread,
    MakeWorkspace,
    StartServer,
    WriteThreads,
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

# 配る書き出しの図が描き終わるまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000

# 配る書き出しで開く資料の本文（mermaid の図と、部品 map が描く map の範囲を持つ）
EXPORT_BODY = BODY_WITH_DIAGRAM + """
<!-- map -->

```mermaid
flowchart LR
  X[構成の左] --> Y[構成の右]
```

<!-- /map -->
"""

# map の図の描画の領域のノードの名前の要素
MAP_NODE_NAMES = ".mdmark-map .mdmark-diagram-stage .mdmark-diagram-node-name"


# 足す検討事項
NEW_DECISION = {
    "title": "新しい問い",
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
    """`/w/{ワークスペース}/` を開くと、記録を読んでトップバーと概要を描く（正常系）。"""
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
    page.wait_for_selector("#tile-open")
    # 検証
    assert page.get_attribute("header span[title]", "title") == "要件出しのスキル mindmap を設計する"
    assert page.get_attribute(CURRENT_TAB, "data-tab") == "overview"
    assert "D-1の題" in page.inner_text("#tile-open")
    assert page.get_attribute('header button[aria-label^="コメント"]', "aria-label") == (
        "コメント（未読あり・レビュー中 2 件）"
    )
    assert page.evaluate("location.pathname + location.search") == urlsplit(spa_url(url)).path
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
    added = write_tool(call_tool, "add", workspace=str(root), kind="decision", item=NEW_DECISION)
    started = time.monotonic()
    page.wait_for_selector(f"{DECISIONS_COUNT}:text-is('2')", timeout=UPDATE_TIMEOUT_MS)
    elapsed = time.monotonic() - started
    # 検証
    assert added.is_error is False, added.text
    assert elapsed <= REFLECT_LIMIT_SEC
    assert page.url == opened_url
    assert page.evaluate(SCROLL_TOP_SCRIPT) == scroll_top


# 保留の間にも出さない「更新があります」のバーの文言
STALE_TEXT = "更新があります"

# 入力中に書き換えてから、画面に反映していないことを確かめるまで待つミリ秒（インターフェース定義の期待の 3 秒）
HOLD_CHECK_MS = 3_000


def test_normal_when_records_changed_while_typing(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    page: Page,
) -> None:
    """入力する欄にフォーカスがある間は読み直さず、保留を画面に出さない。フォーカスが外れたら 1 回だけ読み直す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    open_spa(page, served.data["url"], "?tab=decisions&view=table&id=D-1")
    main = page.locator("main#main")
    expect(main.get_by_role("button", name="D-1の題", exact=True)).to_be_visible()
    entry = page.get_by_role("complementary", name="詳細").get_by_role("textbox", name="D-1 へのコメント")
    entry.fill("途中まで")
    opened_url = page.url
    records_requests: list[str] = []
    page.on(
        "request",
        lambda request: records_requests.append(request.url)
        if request.method == "GET" and request.url.split("?")[0].endswith("/api/records")
        else None,
    )
    # 実行（入力欄にフォーカスを置いたまま検討事項を足す）
    added = write_tool(call_tool, "add", workspace=str(root), kind="decision", item=NEW_DECISION)
    page.wait_for_timeout(HOLD_CHECK_MS)
    held = {
        "requests": len(records_requests),
        "added_shown": main.get_by_text(NEW_DECISION["title"]).count(),
        "value": entry.input_value(),
        "focused": entry.evaluate("e => document.activeElement === e"),
        # 更新のボタンのツールチップ（読み上げから外した要素）の文言は帯に数えない
        "stale_bar": page.get_by_text(STALE_TEXT).and_(page.locator(":not([aria-hidden='true'] *)")).count(),
    }
    # 実行（入力欄の外を押す）
    page.get_by_role("complementary", name="詳細").get_by_role("heading", name="D-1の題").click()
    started = time.monotonic()
    expect(main.get_by_text(NEW_DECISION["title"]).first).to_be_visible(timeout=UPDATE_TIMEOUT_MS)
    elapsed = time.monotonic() - started
    # 検証
    assert added.is_error is False, added.text
    assert held == {"requests": 0, "added_shown": 0, "value": "途中まで", "focused": True, "stale_bar": 0}
    assert elapsed <= REFLECT_LIMIT_SEC
    assert len(records_requests) == 1
    assert entry.input_value() == "途中まで"
    assert page.url == opened_url


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
    page.wait_for_selector("#tile-open")
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
    assert page.locator("#tile-open").count() == 0
    assert console.exceptions == []


def test_error_when_server_stopped(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
    page: Page,
) -> None:
    """書き換えの知らせが切れたら、トップバーに接続が切れたことを出し、立ち上がり直すとつなぎ直す（異常系）。"""
    # 準備（再起動も同じポートで待ち受けるよう、常駐サーバーのポートを決めて渡す）
    port_env = {PORT_ENV: str(free_port())}
    server = start_server(extra_env=port_env)
    root = make_workspace(make_item("D-1"))
    served = server.call("preview_url", workspace=str(root))
    assert served.data is not None
    open_spa(page, served.data["url"])
    page.wait_for_selector("#tile-open")
    # 実行（server_stop で常駐サーバーを止める）
    server.call("server_stop")
    server.wait_exit()
    page.wait_for_selector(CONNECTION, timeout=UPDATE_TIMEOUT_MS)
    stopped_tile = page.inner_text("#tile-open")
    restarted = start_server(extra_env=port_env).call("preview_url", workspace=str(root))
    page.wait_for_selector(CONNECTION, state="detached", timeout=UPDATE_TIMEOUT_MS)
    # 検証
    assert "D-1の題" in stopped_tile
    assert restarted.data is not None
    assert restarted.data["url"] == served.data["url"]
    assert "D-1の題" in page.inner_text("#tile-open")


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
    page.wait_for_url("**/w/*/?tab=tasks")


def test_normal_when_filter(page: Page, spa_preview: str) -> None:
    """`f.{列}` の条件で開き、そのタブの保存領域に残し、端末の保存領域には残さない（正常系）。"""
    open_spa(page, spa_preview, "?tab=decisions&view=table&f.status=%E4%BF%9D%E7%95%99")
    expect(page.get_by_role("cell", name="画面の幅", exact=True)).to_be_visible()
    key = "(location.pathname.split('/')[1] === 'w' ? ':' + decodeURIComponent(location.pathname.split('/')[2]) : '')"
    page.wait_for_function(f"(sessionStorage.getItem('mindmap-filters' + {key}) ?? '').includes('保留')")
    assert "保留" not in (page.evaluate(f"localStorage.getItem('mindmap-preview' + {key})") or "")


def test_normal_when_diff(make_workspace: MakeWorkspace, call_tool: CallTool, page: Page) -> None:
    """`diff` が指すまとまりの差分の表示で開き、時点を選び直すと履歴に積まずに `diff` を置き換える（正常系）。"""
    # 準備（V-1 で D-1・D-2 を足し、V-2 で D-1 の本文を変えて D-3 を足し、D-2 を消す）
    root = make_workspace()
    workspace = str(root)
    decision = {"status": "未決定", "options": [{"key": "A", "content": "案 A"}]}
    call_or_write(call_tool, "add", workspace=workspace, kind="decision", item={**decision, "title": "本文を変える問い", "body_markdown": "1 行目\n\n消す行\n"})
    call_or_write(call_tool, "add", workspace=workspace, kind="decision", item={**decision, "title": "消す問い"})
    call_or_write(call_tool, "commit", workspace=workspace, summary="足す")
    call_or_write(call_tool, "update", workspace=workspace, id="D-1", item={"body_markdown": "1 行目\n\n足した行\n"})
    call_or_write(call_tool, "add", workspace=workspace, kind="decision", item={**decision, "title": "足す問い"})
    call_or_write(call_tool, "remove", workspace=workspace, id="D-2")
    call_or_write(call_tool, "commit", workspace=workspace, summary="直す")
    served = call_tool("preview_url", workspace=workspace)
    assert served.data is not None
    url = served.data["url"]
    open_spa(page, url, "?tab=decisions&view=table&id=D-1&diff=V-2")
    main = page.locator("main#main")
    detail = page.get_by_role("complementary", name="詳細")
    # 検証（開いた直後）
    expect(main.locator("tr:has(button[data-id='D-1']) [title='変更']")).to_have_count(1)
    expect(main.locator("tr:has(button[data-id='D-3']) [title='新規']")).to_have_count(1)
    removed = main.get_by_role("region", name="この時点で削除した項目").locator("li[data-removed-id]")
    expect(removed).to_have_count(1)
    expect(removed).to_have_attribute("data-removed-id", "D-2")
    expect(removed).to_contain_text("消す問い")
    expect(detail.locator('.md .mdmark-diff-block[data-kind="add"]').first).to_be_visible()
    expect(detail.locator('.md .mdmark-diff-block[data-kind="del"]').first).to_be_attached()
    dotted = page.eval_on_selector_all("nav[aria-label=項目の種類] a:has(.sr-only)", "tabs => tabs.map(t => t.dataset.tab)")
    assert dotted == ["decisions"]
    history_length = page.evaluate("history.length")
    # 実行
    page.locator("header button[aria-label^=変更履歴]").click()
    page.get_by_role("dialog", name="変更履歴").locator("button[data-sel='V-1']").click()
    # 検証（選び直した後）
    expect(page).to_have_url(re.compile("diff=V-1"))
    assert page.evaluate("history.length") == history_length
    # 実行
    page.reload()
    # 検証（再読み込みした後）
    expect(page).to_have_url(re.compile("diff=V-1"))
    expect(main.locator("tr:has(button[data-id='D-1']) [title='新規']")).to_have_count(1)


def test_normal_when_diff_missing(page: Page, write_history_preview: WriteReviewPreview) -> None:
    """記録に無い時点は外す（正常系）。"""
    url, _ = write_history_preview()
    open_spa(page, url, "?tab=decisions&diff=V-99")
    page.wait_for_function("!location.search.includes('V-99')")


def test_normal_when_unread(make_workspace: MakeWorkspace, call_tool: CallTool, page: Page) -> None:
    """開いていないまとまりを未読に数え、開いたまとまりと「すべて既読にする」で既読にし、増えたまとまりを未読に加える（正常系）。"""
    # 準備（まとまり V-1・V-2 を作る）
    root = make_workspace()
    workspace = str(root)
    call_or_write(call_tool, "add", workspace=workspace, kind="decision", item=NEW_DECISION)
    call_or_write(call_tool, "commit", workspace=workspace, summary="1 つ目")
    call_or_write(call_tool, "update", workspace=workspace, id="D-1", item={"title": "直した問い"})
    call_or_write(call_tool, "commit", workspace=workspace, summary="2 つ目")
    served = call_tool("preview_url", workspace=workspace)
    assert served.data is not None
    url = served.data["url"]
    history_button = page.locator("header button[aria-label^=変更履歴]")
    dialog = page.get_by_role("dialog", name="変更履歴")
    # 実行（開く）
    open_spa(page, url, "?tab=decisions")
    # 検証
    expect(history_button).to_have_attribute("aria-label", "変更履歴（未読 2 件）")
    history_button.click()
    assert dialog.locator("button[data-sel]").evaluate_all("rows => rows.map((r) => r.dataset.sel)") == ["", "turn", "V-2", "V-1"]
    expect(dialog.locator("button[data-sel]").first).to_contain_text("最新")
    expect(dialog.get_by_text("未読", exact=True)).to_have_count(2)
    expect(dialog.get_by_text("前回開いてから")).to_have_count(0)
    # 実行（V-2 を選ぶ）
    dialog.locator("button[data-sel='V-2']").click()
    # 検証
    expect(page).to_have_url(re.compile("diff=V-2"))
    expect(history_button).to_have_attribute("aria-label", "変更履歴（過去の差分を表示中）（未読 1 件）")
    history_button.click()
    expect(dialog.locator("button[data-sel='V-2']").get_by_text("未読", exact=True)).to_have_count(0)
    # 実行（「最新」に戻し、すべて既読にする）
    dialog.locator("button[data-sel='']").click()
    history_button.click()
    dialog.get_by_role("button", name="すべて既読にする").click()
    dialog.get_by_role("button", name="変更履歴を閉じる").click()
    # 検証
    expect(history_button).to_have_attribute("aria-label", "変更履歴")
    page.reload()
    expect(history_button).to_have_attribute("aria-label", "変更履歴")
    # 実行（まとまり V-3 を作る）
    call_or_write(call_tool, "add", workspace=workspace, kind="decision", item={**NEW_DECISION, "title": "3 つ目の問い"})
    call_or_write(call_tool, "commit", workspace=workspace, summary="3 つ目")
    # 検証（再読み込みの操作をせずに未読が増える）
    expect(history_button).to_have_attribute("aria-label", "変更履歴（未読 1 件）", timeout=UPDATE_TIMEOUT_MS)
    history_button.click()
    expect(dialog.get_by_text("未読", exact=True)).to_have_count(1)
    expect(dialog.locator("button[data-sel='V-3']").get_by_text("未読", exact=True)).to_have_count(1)
    # 実行（diff=since を付けて開き直す）
    open_spa(page, url, "?tab=decisions&diff=since")
    # 検証
    page.wait_for_function("!location.search.includes('diff=')")
    expect(history_button).not_to_have_attribute("aria-label", re.compile("過去の差分"))


@pytest.mark.parametrize("width", [pytest.param(1280, id="w1280"), pytest.param(390, id="w390")])
def test_normal_when_doc_keeps_page_height(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool, page: Page, width: int) -> None:
    """本文の長い資料を開いても画面の全体は縦にスクロールせず、本文の区画の中だけがスクロールする（正常系）。"""
    # 準備
    body = "\n\n".join(f"段落 {number}" for number in range(1, 121)) + "\n\n最後の段落\n"
    root = make_workspace(make_item("A-1"), bodies={"A-1.mark.md": body})
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    page.set_viewport_size({"width": width, "height": 800})
    open_spa(page, served.data["url"], "?tab=docs&id=A-1")
    region = page.get_by_role("region", name="詳細の本文")
    # 本文を最後の段落まで描き終えてからスクロールする
    region.get_by_text("最後の段落", exact=True).wait_for(state="attached")
    # 実行
    region.evaluate("e => { e.scrollTop = e.scrollHeight; }")
    # 検証
    assert page.evaluate("document.scrollingElement.scrollHeight <= document.scrollingElement.clientHeight")
    assert page.locator("header").evaluate("e => e.getBoundingClientRect().top") == 0
    expect(region.get_by_text("最後の段落", exact=True)).to_be_in_viewport()


def test_normal_when_option_chosen(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool, page: Page) -> None:
    """検討事項の詳細で案を選んで溜め、選び直してからまとめて送信すると、利用者の選択として記録する（正常系）。"""
    # 準備
    options = [{"key": "A", "content": "案 A"}, {"key": "B", "content": "案 B"}]
    root = make_workspace(make_item("D-1", options=options))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    errors = watch_console(page)
    open_spa(page, served.data["url"], "?tab=decisions&id=D-1")
    detail = page.get_by_role("complementary", name="詳細")
    comments_button = page.locator("header button[aria-label^=コメント]")
    # 実行（案 A を選ぶ）
    detail.get_by_role("button", name="案 A を選ぶ").click()
    detail.get_by_role("button", name="この案を選ぶ").click()
    # 検証
    expect(detail.locator("[data-chosen]")).to_contain_text("案 A")
    expect(comments_button).to_have_attribute("aria-label", re.compile("レビュー中 1 件"))
    # 実行（案 B で選び直し、一言を添える）
    detail.get_by_role("button", name="案 B を選ぶ").click()
    detail.get_by_role("textbox", name="一言（任意）").fill("費用を優先する")
    detail.get_by_role("button", name="この案を選ぶ").click()
    # 検証
    expect(detail.locator("[data-chosen]")).to_have_count(1)
    expect(detail.locator("[data-chosen]")).to_contain_text("案 B")
    expect(comments_button).to_have_attribute("aria-label", re.compile("レビュー中 1 件"))
    # 実行（コメントの一覧のレビュー中からまとめて送信する）
    comments_button.click()
    page.get_by_role("dialog", name="コメント").get_by_role("button", name="レビュー中の書き込みを確かめる（1 件）").click()
    page.get_by_role("dialog", name="コメント").get_by_role("button", name="まとめて送信（1 件）").click()
    # 検証
    expect(page.get_by_role("dialog", name="コメント").get_by_role("status").filter(has_text="1 件を送信し")).to_be_visible()
    expect(comments_button).to_have_attribute("aria-label", "コメント（レビュー中 0 件）")
    [item] = _workspace_yaml(root, "decisions.yaml")["items"]
    assert (item["user_choice"]["key"], item["user_choice"]["note"], item["status"]) == ("B", "費用を優先する", "未決定")
    page.set_viewport_size({"width": 390, "height": 844})
    open_spa(page, served.data["url"], "?tab=decisions&id=D-1")
    box = page.get_by_role("complementary", name="詳細").get_by_role("button", name="案 A を選ぶ").bounding_box()
    assert box is not None
    assert (box["width"] >= 24, box["height"] >= 24) == (True, True)
    assert errors.messages == []
    assert errors.exceptions == []


def test_normal_when_records_changed_with_item(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool, page: Page) -> None:
    """書き換えの知らせで、開いている項目を保ったまま描き直す（正常系）。"""
    root = make_workspace(make_item("D-1"))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    open_spa(page, served.data["url"], "?tab=decisions&id=D-1")
    panel = page.get_by_role("complementary", name="詳細")
    panel.wait_for()
    write_tool(call_tool, "update", workspace=str(root), id="D-1", item={"title": "書き換えた題"})
    expect(panel.get_by_role("heading", name="書き換えた題")).to_be_visible()


def _served_with_commit(make_workspace: MakeWorkspace, call_tool: CallTool, *items: tuple[str, dict[str, Any]]) -> str:
    """実際のツールで項目を足して `commit`（V-1）したワークスペースの配信の URL を返す。"""
    root = make_workspace()
    for kind, item in items:
        added = write_tool(call_tool, "add", workspace=str(root), kind=kind, item=item)
        assert added.is_error is False, added.text
    committed = call_tool("commit", workspace=str(root), summary="最初の書き込み")
    assert committed.is_error is False, committed.text
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    return str(served.data["url"])


def _history_length(page: Page) -> int:
    """ブラウザの履歴の数を返す。"""
    length: int = page.evaluate("history.length")
    return length


def test_normal_when_search(make_workspace: MakeWorkspace, call_tool: CallTool, page: Page) -> None:
    """`Ctrl+K` で全体の検索を開き、検索の言葉にヒットした項目を選んで、その項目のタブと詳細パネルを開く（正常系）。"""
    # 準備
    url = _served_with_commit(
        make_workspace,
        call_tool,
        ("decision", {"title": "画面の分け方", "status": "未決定", "options": [{"key": "A", "content": "案 A"}]}),
        ("task", {"title": "決める", "kind": "作業", "status": "未着手"}),
    )
    open_spa(page, url, "?tab=tasks&diff=V-1")
    before = _history_length(page)
    # 実行（Ctrl+K を押す）
    page.keyboard.press("Control+k")
    search_box = page.get_by_role("textbox", name="検索キーワード")
    expect(search_box).to_be_focused()
    opened = (page.evaluate("location.search"), _history_length(page))
    # 実行（「画面」と入力する）
    search_box.fill("画面")
    page.wait_for_url(re.compile("q="))
    typed = (page.evaluate("decodeURIComponent(location.search)"), _history_length(page))
    hits = page.get_by_role("listbox", name="検索の結果").inner_text()
    # 実行（D-1 を押す）
    page.get_by_role("option").filter(has_text="D-1").click()
    page.wait_for_url("**/w/*/?tab=decisions*")
    chosen = (page.evaluate("location.search"), _history_length(page))
    # 実行（ブラウザで戻る）
    page.go_back()
    page.wait_for_url("**/w/*/?tab=tasks*")
    back = page.evaluate("decodeURIComponent(location.search)")
    # 検証
    assert opened == ("?tab=tasks&diff=V-1&search=1", before)
    assert typed == ("?tab=tasks&diff=V-1&search=1&q=画面", before)
    assert "D-1" in hits
    assert chosen == ("?tab=decisions&id=D-1&diff=V-1", before + 1)
    assert back == "?tab=tasks&diff=V-1&search=1&q=画面"
    assert page.get_attribute(CURRENT_TAB, "data-tab") == "tasks"


def test_normal_when_search_filter_candidate(write_preview: WritePreview, make_item: MakeItem, page: Page) -> None:
    """全体の検索の先頭の絞り込みの候補を選び、今の画面の絞り込みにその値を加える（正常系）。"""
    # 準備
    url = write_preview(
        make_item("A-1", title="画面の資料", status="確認中", tags=[{"name": "画面"}]),
        make_item("A-2", title="廃止の資料", status="確認中", tags=[{"name": "画面"}, {"name": "廃止"}]),
        make_item("A-3", title="タグの無い資料", status="確認中"),
    )
    open_spa(page, url, "?tab=docs")
    before = _history_length(page)
    # 実行（Ctrl+K を押して「廃」と入力する）
    page.keyboard.press("Control+k")
    page.get_by_role("textbox", name="検索キーワード").fill("廃")
    page.wait_for_url(re.compile("q="))
    candidate = page.get_by_role("group", name="絞り込みをオンにする").get_by_role("option")
    expect(candidate).to_have_count(1)
    first = page.get_by_role("option").first.inner_text()
    # 実行（「タグ = 廃止」を押す）
    candidate.click()
    page.wait_for_url(re.compile("f\\.tags="))
    # 検証
    assert "タグ = 廃止" in first
    assert "1" in first
    expect(page.get_by_role("dialog", name="すべての項目を検索")).to_be_hidden()
    assert page.evaluate("decodeURIComponent(location.search)") == "?tab=docs&f.tags=廃止"
    assert _history_length(page) == before + 1
    expect(page.get_by_text("廃止の資料")).to_be_visible()
    expect(page.get_by_text("画面の資料")).to_be_hidden()
    expect(page.get_by_text("タグの無い資料")).to_be_hidden()

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
    url = write_preview(make_item("D-1", title="本文あり", status="未決定", body="../docs/D-1.mark.md"), bodies={"D-1.mark.md": "本文の原文"})

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
    """詳細の本文の文を選んで箇所を添えたコメントを溜め、コメントの一覧のレビュー中の書き込みからまとめて送信（正常系）。"""
    # 準備
    url, root = write_review_preview(make_item("A-1", title="手引き"), bodies={"A-1.mark.md": THREE_LINE_BODY})
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
    panel.get_by_role("tab", name="コメント").click()
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
    # 実行（まとめて送信）
    page.get_by_role("dialog", name="コメント").get_by_role("button", name="まとめて送信（1 件）").click()
    # 検証
    expect(page.get_by_role("dialog", name="コメント").get_by_role("status").filter(has_text="1 件を送信し")).to_be_visible()
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
    """`thread` が指すスレッドを開いて既読にし、返信を溜め、理由を聞かずにクローズにして一覧へ戻る（正常系）。"""
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
    # 実行（クローズにする）
    before = _history_length(page)
    panel.get_by_role("button", name="クローズにする").click()
    # 検証（一覧へ戻り、履歴に積まない）
    expect(panel.get_by_role("group", name="スレッドの状態で絞る")).to_be_visible()
    assert "thread=" not in page.url
    assert _history_length(page) == before
    thread = _workspace_yaml(root, "threads.yaml")["items"][0]
    assert thread["status"] == "closed"
    assert thread["events"][-1].get("reason") is None


def test_normal_when_comment_draft_restored(page: Page, write_review_preview: WriteReviewPreview, make_item: MakeItem) -> None:
    """コメントの入力欄の下書きをサーバーに保ち、読み込み直すと同じ入力欄に戻す（正常系）。"""
    # 準備
    url, root = write_review_preview(make_item("D-1"))
    open_spa(page, url, "?tab=decisions&id=D-1")
    field = page.get_by_role("complementary", name="詳細").get_by_role("textbox", name="D-1 へのコメント")
    # 実行（書いて入力を止め、下書きの保存を待つ）
    with page.expect_response(lambda response: response.url.endswith("/api/drafts") and response.request.method == "PUT"):
        field.fill("下書きの文")
    # 検証
    assert [(draft["target"], draft["body"]) for draft in _workspace_yaml(root, "drafts.yaml")["items"]] == [("D-1", "下書きの文")]
    # 実行（読み込み直す）
    page.reload()
    # 検証
    expect(page.get_by_role("complementary", name="詳細").get_by_role("textbox", name="D-1 へのコメント")).to_have_value("下書きの文")


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
    prefs = json.loads(page.evaluate(f"localStorage.getItem('{PREFS_KEY}' + (location.pathname.split('/')[1] === 'w' ? ':' + decodeURIComponent(location.pathname.split('/')[2]) : ''))"))
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
    """無いスレッド・無いタグ・無い項目を指す値と、コメントの一覧を開いていないときのコメントの値を外して開く（正常系）。"""
    # 準備
    url, _ = write_review_preview(make_item("D-1"), threads=(make_thread("TH-1", tags=["画面"]),))
    # 実行
    open_spa(page, url, "?panel=comments&thread=TH-99&ttag=無いタグ&ttarget=D-99")
    # 検証
    expect(page.get_by_role("dialog", name="コメント").get_by_role("group", name="スレッドの状態で絞る")).to_be_visible()
    page.wait_for_function("() => location.search === '?panel=comments'")
    # 実行
    open_spa(page, url, "?tab=decisions&thread=TH-1&review=1&ttarget=D-1")
    # 検証
    page.wait_for_function("() => location.search === '?tab=decisions'")
    expect(page.get_by_role("dialog", name="コメント")).to_have_count(0)


def test_normal_when_comment_target_filtered(
    page: Page,
    write_review_preview: WriteReviewPreview,
    make_item: MakeItem,
    make_thread: MakeThread,
    make_post: MakePost,
    make_comment: MakeComment,
) -> None:
    """詳細パネルのボタンで、開いている項目で絞ったスレッドの一覧を開き、項目の絞り込みを外す（正常系）。"""
    # 準備
    url, _ = write_review_preview(
        make_item("D-1"),
        make_item("D-2"),
        threads=(
            make_thread("TH-1", make_post("TH-1-1", body="D-1 の話", created="2026-10-12T01:00:00+00:00"), summary="D-1 の話", target="D-1"),
            make_thread("TH-2", make_post("TH-2-1", body="D-2 の話", created="2026-10-12T02:00:00+00:00"), summary="D-2 の話", target="D-2"),
        ),
        comments=(make_comment("C-1", target="D-1", body="D-1 への新規スレッド"),),
    )
    open_spa(page, url, "?tab=decisions&id=D-1")
    panel = page.get_by_role("dialog", name="コメント")
    rows = panel.locator("li[data-thread], li[data-pending]")
    before = page.evaluate("history.length")
    # 実行
    page.get_by_role("complementary", name="詳細").get_by_role("button", name="D-1 のコメントの一覧を開く").click()
    # 検証
    page.wait_for_function("() => location.search === '?tab=decisions&id=D-1&panel=comments&ttarget=D-1'")
    expect(rows).to_have_count(2)
    expect(rows.nth(0)).to_contain_text("D-1 への新規スレッド")
    expect(rows.nth(1)).to_contain_text("D-1 の話")
    assert page.evaluate("history.length") == before
    # 実行
    panel.get_by_role("button", name="項目「D-1」の絞り込みを外す").click()
    # 検証
    page.wait_for_function("() => !new URLSearchParams(location.search).has('ttarget')")
    expect(rows).to_have_count(3)
    assert page.evaluate("history.length") == before


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
    make_workspace: MakeWorkspace, make_item: MakeItem, start_server: StartServer, page: Page
) -> None:
    """サーバーが止まった後に溜めると、本文を残して届かなかった理由を出す（異常系）。"""
    # 準備
    server = start_server()
    root = make_workspace(make_item("D-1"))
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
    """まとめて送信の 409 では、箇所が合わない書き込みの行に理由を出し、どれも送らない（異常系）。"""
    # 準備
    url, root = write_review_preview(
        make_item("A-1", title="手引き"),
        comments=(make_comment("C-1", target="A-1", loc={"kind": "body", "start": 3, "end": 3, "text": "三行目の文"}, body="言い換える"),),
        bodies={"A-1.mark.md": THREE_LINE_BODY},
    )
    errors = watch_console(page)
    open_spa(page, url, "?panel=comments&review=1")
    panel = page.get_by_role("dialog", name="コメント")
    expect(panel.locator("li[data-comment='C-1']")).to_be_visible()
    # 実行（A-1 の本文を 1 行にしてから、まとめて送信）
    updated = write_tool(call_tool, "update", workspace=str(root), id="A-1", item={"body_markdown": "一行だけ\n"})
    assert updated.is_error is False, updated.text
    panel.get_by_role("button", name="まとめて送信（1 件）").click()
    # 検証
    row = panel.locator("li[data-comment='C-1']")
    expect(row.get_by_role("alert")).to_be_visible()
    expect(row.get_by_role("button", name="箇所を解除")).to_be_visible()
    assert [item["id"] for item in _workspace_yaml(root, "comments.yaml")["items"]] == ["C-1"]
    assert (_workspace_yaml(root, "threads.yaml") or {"items": []})["items"] == []
    assert errors.exceptions == []


def test_normal_when_duplicate_ids(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool, page: Page
) -> None:
    """同じ ID の項目が 2 件になったら、トップバーの下に重なった ID の通知を出し、閉じると隠す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    open_spa(page, served.data["url"], "?tab=decisions")
    duplicated = [make_item("D-1"), make_item("D-1", title="もう 1 件")]
    # 実行
    (root / RECORD_DIR / "decisions.yaml").write_text(
        yaml.safe_dump({"items": duplicated}, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    notice = page.get_by_role("alert").filter(has_text="同じ ID の項目が 2 件あります")
    expect(notice).to_be_visible()
    text = " ".join(notice.inner_text().split())
    notice.get_by_role("button", name="通知を閉じる").click()
    # 検証
    assert "D-1 が重なりました。片方の ID を変更してください。" in text
    expect(notice).to_have_count(0)


def test_normal_when_embedded_files(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool, page: Page) -> None:
    """本文の ../files/{名前} を配信の /w/{workspace}/files/{名前} に解決して、動画・画像を描く（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1"), bodies={"A-1.mark.md": EMBEDDED_FILES_BODY})
    put_embedded_files(root)
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    workspace_base = urlsplit(served.data["url"]).path.rsplit("/", 1)[0]
    # 実行
    open_spa(page, served.data["url"], "?tab=docs&id=A-1")
    panel = page.get_by_role("complementary", name="詳細")
    video = panel.locator("video")
    image = panel.locator("img")
    expect(video).to_have_attribute("src", f"{workspace_base}/files/clip.mp4", timeout=UPDATE_TIMEOUT_MS)
    expect(image).to_have_attribute("src", f"{workspace_base}/files/shot.png")
    # 検証
    expect(video).to_have_js_property("error", None)
    page.wait_for_function("(v) => v.readyState >= 1", arg=video.element_handle(), timeout=UPDATE_TIMEOUT_MS)
    page.wait_for_function("(i) => i.complete && i.naturalWidth > 0", arg=image.element_handle(), timeout=UPDATE_TIMEOUT_MS)


def _export_url(call_tool: CallTool, root: Path, out: Path) -> str:
    """ワークスペースを `out` へ書き出し、書き出した HTML の `file://` の URL を返す。"""
    result = call_tool("export", workspace=str(root), out=str(out))
    assert result.is_error is False, result.text
    return out.as_uri()


def test_normal_when_exported_offline(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool, page: Page, tmp_path: Path
) -> None:
    """配る書き出しを `file://` で開くと、外部への要求をせずに概要と詳細の本文・mermaid と map の図を描く（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1", status="下書き", body="../docs/A-1.mark.md"), bodies={"A-1.mark.md": EXPORT_BODY})
    url = _export_url(call_tool, root, tmp_path / "配る.html")
    blocked: list[str] = []

    def _block(route: Route) -> None:
        """`file:` 以外への要求を数えて失敗させる。"""
        blocked.append(route.request.url)
        route.abort()

    page.route(lambda request_url: not request_url.startswith("file:"), _block)
    console = watch_console(page)
    # 実行
    page.goto(url)
    page.wait_for_selector("#tile-open", timeout=SPA_RENDER_TIMEOUT_MS)
    page.goto(f"{url}#/?tab=docs&id=A-1")
    panel = page.get_by_role("complementary", name="詳細")
    panel.locator(".mermaid svg").first.wait_for(timeout=DIAGRAM_TIMEOUT_MS)
    panel.locator(MAP_NODE_NAMES).first.wait_for(timeout=DIAGRAM_TIMEOUT_MS)
    # 検証
    expect(panel.get_by_role("heading", name="流れ")).to_be_visible()
    expect(panel.locator(MAP_NODE_NAMES, has_text="構成の左")).to_have_count(1)
    assert "X[構成の左]" not in page.inner_text("body")
    assert blocked == []
    assert console.messages == []
    assert console.exceptions == []


def test_normal_when_exported_read_only(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool, page: Page, tmp_path: Path
) -> None:
    """配る書き出しは、項目の追加・編集・確認済み・コメント・保存待ち・ワークスペースの既定にするの操作を出さない（正常系）。"""
    # 準備
    root = make_workspace(make_item("T-1", status="進行中"))
    url = _export_url(call_tool, root, tmp_path / "配る.html")
    # 実行
    page.goto(f"{url}#/?tab=tasks&id=T-1")
    page.wait_for_selector(SPA_CONTENT_SELECTOR, state="attached", timeout=SPA_RENDER_TIMEOUT_MS)
    panel = page.get_by_role("complementary", name="詳細")
    expect(panel).to_be_visible()
    header = page.locator("header")
    page.get_by_role("button", name="表示の設定").click()
    settings = page.get_by_role("dialog", name="表示の設定")
    expect(settings).to_be_visible()
    # 検証
    expect(header.get_by_role("button", name=re.compile(r"^コメント"))).to_have_count(0)
    expect(header.get_by_role("button", name=re.compile(r"^保存待ち"))).to_have_count(0)
    expect(page.get_by_role("button", name="タスクの項目を追加")).to_have_count(0)
    expect(panel.get_by_role("button", name="編集する")).to_have_count(0)
    expect(panel.get_by_role("button", name=re.compile("確認済み"))).to_have_count(0)
    expect(panel.get_by_role("button", name="T-1 のコメントの一覧を開く")).to_have_count(0)
    expect(panel.get_by_role("textbox")).to_have_count(0)
    expect(settings.get_by_role("button", name="ワークスペースの既定にする")).to_have_count(0)


# ─── 横幅（モジュール構成『React』の補足「横幅」） ───

# 動作環境の最も狭い画面の幅
NARROWEST_SIZE = {"width": 360, "height": 800}

# 改行の無い長いタイトル（長い URL を含む）
_LONG_TITLE = f"{'改行の無い長いタイトル' * 8}https://example.com/{'segment' * 20}"

# 列が多く画面の幅を超える表を持つ資料の本文
_WIDE_TABLE_BODY = (
    "| " + " | ".join(f"列{n}" for n in range(1, 13)) + " |\n"
    + "| " + " | ".join("---" for _ in range(12)) + " |\n"
    + "| " + " | ".join(f"値{n}の長い文字列" for n in range(1, 13)) + " |\n\n"
    + f"https://example.com/{'very-long-path-segment-' * 15}end\n"
)


@pytest.mark.parametrize(
    "search",
    [
        "?tab=overview",
        "?tab=decisions",
        "?tab=tasks",
        "?tab=docs",
        "?tab=settings",
        "?tab=decisions&id=D-1",
        "?tab=docs&id=A-1",
    ],
)
def test_normal_when_narrowest_no_horizontal_scroll(
    page: Page, write_preview: WritePreview, make_item: MakeItem, search: str
) -> None:
    """幅 360px で、改行の無い長いタイトルと列の多い表を持つ記録を開いても、ページは横にスクロールしない（正常系）。"""
    # 準備
    url = write_preview(
        make_item("D-1", title=_LONG_TITLE),
        make_item("T-1", title=_LONG_TITLE),
        make_item("A-1", title=_LONG_TITLE, body="../docs/A-1.mark.md"),
        bodies={"A-1.mark.md": _WIDE_TABLE_BODY},
    )
    page.set_viewport_size(NARROWEST_SIZE)
    # 実行
    open_spa(page, url, search)
    page.wait_for_timeout(500)
    # 検証
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), page.evaluate(
        "[document.documentElement.scrollWidth, document.documentElement.clientWidth]"
    )
    # 資料の詳細: 閉じるボタンが画面の中に残り、コメントの入力欄が表示の幅に収まる（画面設計『資料』の補足「横幅」）
    if "id=A-1" in search:
        detail = page.get_by_role("complementary", name="詳細")
        for control in (detail.get_by_role("button", name="詳細を閉じる"), detail.get_by_role("textbox", name="A-1 へのコメント")):
            box = control.bounding_box()
            assert box is not None
            assert box["x"] >= 0 and box["x"] + box["width"] <= NARROWEST_SIZE["width"] + 1


# 端末の保存領域のキー（サーバーの配信では末尾に `:{workspace}` を付ける）
_PREFS_KEY_JS = "'mindmap-preview' + (location.pathname.split('/')[1] === 'w' ? ':' + decodeURIComponent(location.pathname.split('/')[2]) : '')"


def _snapshot(root: Path) -> dict[str, bytes]:
    """ワークスペースの記録と設定のファイルの中身を、相対パスごとに返す（開いた時刻の印は除く）。"""
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.parts and path.name != ".mindstella-opened"
    }


def test_normal_when_favorites(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool, page: Page) -> None:
    """お気に入りだけで絞り込んで開き、チップの × で解除するとお気に入りを先頭に並べ、記録と設定を書き換えない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1"),
        make_item("A-2"),
        make_item("A-3"),
        bodies={"A-1.mark.md": "資料 1\n", "A-2.mark.md": "資料 2\n", "A-3.mark.md": "資料 3\n"},
    )
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    before = _snapshot(root)
    page.add_init_script(
        "try { if (!sessionStorage.getItem('favorites-seeded')) {"
        f" localStorage.setItem({_PREFS_KEY_JS}, JSON.stringify({{ favorites: ['A-3', 'A-9'], favoritesOnly: true }}));"
        " sessionStorage.setItem('favorites-seeded', '1'); } } catch (e) {}"
    )
    # 実行
    open_spa(page, served.data["url"], "?tab=docs&sort=id")
    cards = page.locator("[data-card]")
    # 検証
    clear = page.get_by_role("button", name="お気に入りのみ の条件を解除")
    expect(clear).to_be_visible()
    expect(cards).to_have_count(1)
    expect(cards.first).to_have_attribute("data-card", "A-3")
    expect(page.locator("[data-card='A-9']")).to_have_count(0)
    # 実行（チップの × で解除する）
    clear.click()
    # 検証
    expect(clear).to_have_count(0)
    expect(cards).to_have_count(3)
    assert cards.evaluate_all("(cards) => cards.map((card) => card.dataset.card)") == ["A-3", "A-1", "A-2"]
    prefs = json.loads(page.evaluate(f"localStorage.getItem({_PREFS_KEY_JS}) ?? '{{}}'"))
    assert prefs.get("favoritesOnly") is None
    assert prefs["favorites"] == ["A-3", "A-9"]
    assert _snapshot(root) == before


@pytest.fixture
def outside_page() -> Iterator[str]:
    """別のポートで 1 枚のページを配り、その URL を返す（テストの後に止める）。"""
    body = b"<!doctype html><title>outside</title><p>outside</p>"

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", free_port()), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/outside"
    finally:
        server.shutdown()
        server.server_close()


def test_normal_when_external_links(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    make_post: MakePost,
    write_threads: WriteThreads,
    call_tool: CallTool,
    page: Page,
    outside_page: str,
) -> None:
    """本文とスレッドの書き込みの別のオリジンを指すリンクを新規タブで開き、項目の ID のリンクは今のタブで開く（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1", title="手引き"),
        make_item("D-1", title="記録の形", status="未決定"),
        bodies={"A-1.mark.md": f"[外のページ]({outside_page}) と D-1 を見る。\n"},
    )
    write_threads(root, make_thread("TH-1", make_post("TH-1-1", author="ai", body=f"参考: {outside_page}"), summary="参考のページ"))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    open_spa(page, served.data["url"], "?tab=docs&id=A-1")
    panel = page.get_by_role("complementary", name="詳細")
    body_link = panel.locator(f'.md a[href="{outside_page}"]')
    expect(body_link).to_have_attribute("target", "_blank", timeout=UPDATE_TIMEOUT_MS)
    expect(body_link).to_have_attribute("rel", "noopener noreferrer")
    before = page.url
    # 実行（本文の外のページへのリンク）
    with page.context.expect_page() as opened:
        body_link.click()
    # 検証
    assert opened.value.url == outside_page
    assert page.url == before
    opened.value.close()
    # 実行・検証（本文の D-1 は今のタブ）
    id_link = panel.locator('.md a[data-id="D-1"], .md a[href="#id=D-1"]').first
    assert id_link.get_attribute("target") is None
    id_link.click()
    page.wait_for_url(re.compile(r"id=D-1"))
    assert len(page.context.pages) == 1
    # 実行（スレッドの書き込みの外のページの URL）
    open_spa(page, served.data["url"], "?tab=docs&panel=comments&thread=TH-1")
    post_link = page.locator(f'a[href="{outside_page}"]').first
    expect(post_link).to_have_attribute("target", "_blank", timeout=UPDATE_TIMEOUT_MS)
    with page.context.expect_page() as opened_post:
        post_link.click()
    # 検証
    assert opened_post.value.url == outside_page
    assert len(page.context.pages) == 2


# 言語 markdown と言語 python のコードブロックを持つ本文
CODE_BLOCKS_BODY = """# 手引き

```markdown
## 見出し

- 項目
  - 入れ子の項目
```

```python
def total(items):
    result = 0
    for item in items:
        if item > 0:
            result += item
    return result
```
"""


def test_normal_when_code_blocks(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool, page: Page) -> None:
    """本文のコードブロックを mdmark のバー・行の部品・色分けで描く（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1", title="手引き"), bodies={"A-1.mark.md": CODE_BLOCKS_BODY})
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    errors = watch_console(page)
    # 実行
    open_spa(page, served.data["url"], "?tab=docs&id=A-1")
    panel = page.get_by_role("complementary", name="詳細")
    blocks = panel.locator(".md .mdmark-code")
    expect(blocks).to_have_count(2, timeout=UPDATE_TIMEOUT_MS)
    markdown, python = blocks.nth(0), blocks.nth(1)
    raw = markdown.locator("button.mdmark-code-raw")
    expect(raw).to_have_attribute("aria-pressed", "false")
    rendered = markdown.inner_text()
    raw.click()
    # 検証（markdown は描いた結果から元の Markdown に切り替わる）
    expect(raw).to_have_attribute("aria-pressed", "true")
    assert "## 見出し" not in rendered
    expect(markdown.locator("pre")).to_contain_text("## 見出し")
    # 検証（python は字下げの縦線・行の開閉・色分けを持つ）
    expect(python.locator('.mdmark-code-line[data-indent="2"]')).not_to_have_count(0)
    expect(python.locator("button.mdmark-code-fold")).not_to_have_count(0)
    expect(python.locator(".hljs-keyword")).not_to_have_count(0)
    # 検証（言語の札とコピーのボタンはコードブロック 1 つに 1 つずつ）
    for block in (markdown, python):
        expect(block.locator(".mdmark-code-lang")).to_have_count(1)
        expect(block.locator("button.mdmark-code-copy")).to_have_count(1)
    expect(panel.locator(".md button.code-copy, .md .code-lang")).to_have_count(0)
    assert errors.messages == []
    assert errors.exceptions == []
