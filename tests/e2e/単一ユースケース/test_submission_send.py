"""項目へコメントする（サーバーが配るプレビューの詳細パネルで、開いている項目へのコメントを書き、送らずにレビュー中として溜める）の E2E テスト。

MCP サーバーを立て、サーバーが配るプレビューを実際のブラウザで開く。描画のライブラリは CDN から読む。
"""

from __future__ import annotations

from typing import Any

import yaml
from playwright.sync_api import Page
from preview_helpers import (
    COMMENTS_BUTTON,
    DETAIL_MESSAGE,
    DETAIL_TEXTAREA,
    OpenPreview,
)
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace, StartServer

# 未決定の検討事項 D-1 の案
OPTIONS = [
    {"key": "A", "content": "表で見せる"},
    {"key": "B", "content": "カードで見せる"},
]

# 溜める本文
BODY = "案 A にする"

# 溜めずにパネルを閉じる書きかけの本文
DRAFT_BODY = "案 B も見たい"

# 画面に結果が出るまで待つ上限ミリ秒
RESULT_TIMEOUT_MS = 10_000

# 閉じるときに保つ書きかけが、ファイルに届くまで待つミリ秒
DRAFT_FLUSH_WAIT_MS = 600


def _open_detail(page: Page, open_preview: OpenPreview, url: str) -> None:
    """検討事項 D-1 の詳細パネルを開き、コメントの入力欄が出るのを待つ。"""
    open_preview(url, "#tab=decisions&id=D-1")
    page.wait_for_selector(DETAIL_TEXTAREA)


def _read_comments(root: Any) -> list[dict[str, Any]]:
    """ワークスペースのレビュー中のコメントを読む（ファイルが無ければ 0 件）。"""
    path = root / "comments.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))["items"] if path.exists() else []


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """詳細パネルでコメントを溜めると、レビュー中のコメントとして残り、入力欄が空になる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    decisions_before = (root / "decisions.yaml").read_bytes()
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    _open_detail(page, open_preview, served.data["url"])
    # 実行
    page.fill(DETAIL_TEXTAREA, BODY)
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.saved", timeout=RESULT_TIMEOUT_MS)
    # 検証
    comments = _read_comments(root)
    assert [(item["target"], item["body"]) for item in comments] == [("D-1", BODY)]
    assert not (root / "submissions.yaml").exists()
    assert page.inner_text(DETAIL_MESSAGE) == "レビューに追加しました（レビュー中 1 件）。"
    assert page.input_value(DETAIL_TEXTAREA) == ""
    assert page.inner_text(f"{COMMENTS_BUTTON} .count") == "1"
    assert (root / "decisions.yaml").read_bytes() == decisions_before


def test_error_when_body_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """本文が空だと溜めず、本文が要る旨を出す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    _open_detail(page, open_preview, served.data["url"])
    # 実行
    page.fill(DETAIL_TEXTAREA, "   ")
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.empty", timeout=RESULT_TIMEOUT_MS)
    # 検証
    assert _read_comments(root) == []
    assert "コメントを入れてから追加してください。" in page.inner_text(DETAIL_MESSAGE)


def test_error_when_server_unreachable(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """サーバーを止めてから溜めると、溜められなかった旨を出し、入力した本文を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    server = start_server()
    served = server.call("preview_url", workspace=str(root))
    assert served.data is not None
    _open_detail(page, open_preview, served.data["url"])
    # 開いた後にサーバーを止める
    server.close_stdin()
    server.wait_exit()
    # 実行
    page.fill(DETAIL_TEXTAREA, BODY)
    page.get_by_role("button", name="レビューに追加").click()
    page.wait_for_selector(f"{DETAIL_MESSAGE}.failed", timeout=RESULT_TIMEOUT_MS)
    # 検証
    assert "レビューに追加できませんでした" in page.inner_text(DETAIL_MESSAGE)
    assert page.input_value(DETAIL_TEXTAREA) == BODY
    assert _read_comments(root) == []


def test_normal_when_draft_restored_after_restart(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """溜めずにパネルを閉じた書きかけを、サーバーを立ち上げ直した後の新しい URL で開いた入力欄へ戻す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    first_server = start_server()
    served = first_server.call("preview_url", workspace=str(root))
    assert served.data is not None
    _open_detail(page, open_preview, served.data["url"])
    # 実行（書きかけを入れて溜めずにパネルを閉じる）
    page.fill(DETAIL_TEXTAREA, DRAFT_BODY)
    page.click('aside.panel button[data-act="close"]')
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    page.wait_for_timeout(DRAFT_FLUSH_WAIT_MS)
    # サーバーを止めて立て直し、新しい URL で開く
    first_server.close_stdin()
    first_server.wait_exit()
    second_server = start_server()
    restarted = second_server.call("preview_url", workspace=str(root))
    assert restarted.data is not None
    _open_detail(page, open_preview, restarted.data["url"])
    # 検証
    assert restarted.data["url"] != served.data["url"]
    assert page.input_value(DETAIL_TEXTAREA) == DRAFT_BODY
    assert _read_comments(root) == []
