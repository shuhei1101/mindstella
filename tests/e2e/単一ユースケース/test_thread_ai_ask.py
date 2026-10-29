"""AIがスレッドを立てる（`session` が、ワークスペースの外へ書き込む前の確認と、話の流れと関係の無い知らせを、スレッドを立てて利用者に返事を求める）の E2E テスト。

モデルを呼ばず、手順が連ねるスレッドを立てるツールの呼び出しを、決めた引数で再生する。開いている画面に出るシナリオは、MCP サーバーが配るプレビューを実際のブラウザで開く。
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from conftest import Replay
from playwright.sync_api import Page
from preview_helpers import (
    COMMENTS_BUTTON,
    COMMENTS_PANEL,
    THREAD_ROWS,
    UPDATE_TIMEOUT_MS,
    OpenPreview,
    open_list,
)
from workspace_fixtures import (
    RECORD_DIR,
    CallTool,
    MakeItem,
    MakeWorkspace,
    SnapshotTree,
)

# 立てるスレッドの本文・タグ・要約
QUESTION = "D-1 の比べた結果を Issue に起票してよいですか"
TAGS = ["起票"]
SUMMARY = "D-1 の比べた結果を Issue に起票してよいかの確認。返事待ち"

# 空のオープン一覧の文言
EMPTY = f"{COMMENTS_PANEL} .comments-empty"


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """確認の問いを本文・タグ・要約つきのオープンのスレッドとして立て、取り込み待ちには出ない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    ws = {"workspace": str(root)}
    # 実行
    created = replay("new_thread", **ws, body=QUESTION, tags=TAGS, summary=SUMMARY)
    awaiting = replay("threads", **ws, awaiting=True)
    checked = replay("check", **ws)
    # 検証
    threads = read_yaml(root, "threads.yaml")["items"]
    assert [item["id"] for item in threads] == [created["id"]]
    thread = threads[0]
    assert thread["status"] == "open"
    assert [(post["author"], post["body"]) for post in thread["posts"]] == [("ai", QUESTION)]
    # 最初の書き込みは利用者の未読
    assert thread["posts"][0]["seen"] is False
    assert (thread["tags"], thread["summary"]) == (TAGS, SUMMARY)
    assert thread["summary"] != QUESTION
    assert awaiting == {"items": []}
    assert checked["ok"] is True
    assert checked["problems"] == []


def test_normal_when_shown_on_open_screen(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """プレビューでスレッドの一覧を開いたまま AI がスレッドを立てると、画面を開き直さずに行が足される（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    open_preview(str(served.data["url"]))
    open_list(page)
    page.wait_for_selector(EMPTY)
    # 実行
    created = call_tool(
        "new_thread", workspace=str(root), body=QUESTION, tags=TAGS, summary=SUMMARY
    )
    # 検証
    assert created.is_error is False
    assert created.data is not None
    page.wait_for_selector(THREAD_ROWS, timeout=UPDATE_TIMEOUT_MS)
    assert page.eval_on_selector_all(THREAD_ROWS, "rows => rows.map(r => r.dataset.thread)") == [
        created.data["id"]
    ]
    assert page.inner_text(f"{THREAD_ROWS} .th-author") == "AI"
    assert page.inner_text(f"{THREAD_ROWS} .th-title") == SUMMARY
    assert page.get_attribute(f"{COMMENTS_PANEL} .talk-filter button[aria-pressed='true']", "data-focus") == "filter:open"
    assert page.inner_text(f"{COMMENTS_PANEL} .talk-filter button[aria-pressed='true'] .count") == "1"
    # 足した行とトップバーのコメントのボタンに未読の印が出る
    assert page.inner_text(f"{THREAD_ROWS} .th-unread") == "未読"
    page.wait_for_selector(f"{COMMENTS_BUTTON} .unread-dot", timeout=UPDATE_TIMEOUT_MS)


def test_error_when_body_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """本文が空のまま立てようとするとエラーを返し、スレッドは 0 件のままである（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行
    result = call_tool("new_thread", workspace=str(root), body="  ", summary=SUMMARY)
    # 検証
    assert result.is_error is True
    assert "body" in result.text
    assert not (root / RECORD_DIR / "threads.yaml").exists()
    assert snapshot_tree(root) == before
