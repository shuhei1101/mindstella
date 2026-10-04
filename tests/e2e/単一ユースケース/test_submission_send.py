"""回答・意見を送る（サーバーが配るプレビューの詳細パネルから、項目の ID ごとに回答・意見を送る）の E2E テスト。

MCP サーバーを立て、サーバーが配るプレビューを実際のブラウザで開く。描画のライブラリは CDN から読む。
"""

from __future__ import annotations

from typing import Any

import yaml
from playwright.sync_api import Page
from preview_helpers import OpenPreview
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace, StartServer

# 未決定の検討事項 D-1 の案
OPTIONS = [
    {"key": "A", "content": "表で見せる"},
    {"key": "B", "content": "カードで見せる"},
]

# 送る本文
BODY = "案 A にする"

# 送信の入力欄・結果・送るボタン
TEXTAREA = "aside.panel form.send textarea"
MESSAGE = "aside.panel form.send .send-msg"
SEND_BUTTON = "aside.panel form.send button[type=submit]"

# 画面に結果が出るまで待つ上限ミリ秒
RESULT_TIMEOUT_MS = 10_000


def _open_detail(page: Page, open_preview: OpenPreview, url: str) -> None:
    """検討事項 D-1 の詳細パネルを開き、送信の入力欄が出るのを待つ。"""
    open_preview(url, "#tab=decisions&id=D-1")
    page.wait_for_selector(TEXTAREA)


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """詳細パネルから回答・意見を送ると、取り込んでいない送信として残り、入力欄が空になる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    decisions_before = (root / "decisions.yaml").read_bytes()
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    _open_detail(page, open_preview, served.data["url"])
    # 実行
    page.fill(TEXTAREA, BODY)
    page.click(SEND_BUTTON)
    page.wait_for_selector(f"{MESSAGE}.sent", timeout=RESULT_TIMEOUT_MS)
    # 検証
    submissions: list[dict[str, Any]] = yaml.safe_load(
        (root / "submissions.yaml").read_text(encoding="utf-8")
    )["items"]
    assert [(item["target"], item["body"], item["taken"]) for item in submissions] == [
        ("D-1", BODY, None)
    ]
    assert submissions[0]["sent"]
    assert "送りました" in page.inner_text(MESSAGE)
    assert page.input_value(TEXTAREA) == ""
    assert (root / "decisions.yaml").read_bytes() == decisions_before


def test_error_when_body_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """本文が空だと送らず、本文が要る旨を出す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=OPTIONS))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    _open_detail(page, open_preview, served.data["url"])
    # 実行
    page.fill(TEXTAREA, "   ")
    page.click(SEND_BUTTON)
    page.wait_for_selector(f"{MESSAGE}.empty", timeout=RESULT_TIMEOUT_MS)
    # 検証
    assert not (root / "submissions.yaml").exists()
    assert "回答・意見を入れてから送ってください。" in page.inner_text(MESSAGE)


def test_error_when_server_unreachable(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """サーバーを止めてから送ると、送れなかった旨を出し、入力した本文を残す（異常系）。"""
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
    page.fill(TEXTAREA, BODY)
    page.click(SEND_BUTTON)
    page.wait_for_selector(f"{MESSAGE}.failed", timeout=RESULT_TIMEOUT_MS)
    # 検証
    assert "送れませんでした" in page.inner_text(MESSAGE)
    assert page.input_value(TEXTAREA) == BODY
    assert not (root / "submissions.yaml").exists()
