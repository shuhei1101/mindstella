"""プレビューを開く（`session` がサーバーが配るプレビューの URL を示し、記録の書き換えを開いている画面へ反映する）の E2E テスト。

起動スクリプトの代わりに MCP サーバーを立て、示された URL を実際のブラウザで開く。描画のライブラリは CDN から読む。
"""

from __future__ import annotations

from playwright.sync_api import Page
from preview_helpers import OpenPreview, row_ids
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace

# 書き換えが画面に出るまで待つ上限ミリ秒
UPDATE_TIMEOUT_MS = 10_000

# 足す検討事項
NEW_DECISION = {
    "title": "新しい問い",
    "target": "mindmap",
    "category": "データ構造",
    "phase": "要件",
    "status": "未決定",
}


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """プレビューの URL を示され、開くと今の記録が出る。ワークスペースに preview.html は書き出されない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    url = served.data["url"]
    open_preview(url, "#tab=decisions&view=table")
    page.wait_for_selector("table.grid tbody tr")
    # 検証
    assert url.startswith("http://127.0.0.1:")
    assert row_ids(page) == ["D-1"]
    assert not (root / "preview.html").exists()


def test_normal_when_rewritten(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    open_preview: OpenPreview,
    page: Page,
) -> None:
    """記録を書き換えると、再読み込みの操作をせずに、開いている画面が描き直される（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    served = call_tool("preview_url", workspace=str(root))
    assert served.data is not None
    open_preview(served.data["url"], "#tab=decisions&view=table")
    page.wait_for_selector("table.grid tbody tr")
    opened_url = page.url
    # 実行
    added = call_tool("add", workspace=str(root), kind="decision", item=NEW_DECISION)
    assert added.is_error is False, added.text
    page.wait_for_function(
        "document.querySelectorAll('table.grid tbody tr').length === 2", timeout=UPDATE_TIMEOUT_MS
    )
    # 検証
    assert row_ids(page) == ["D-1", "D-2"]
    assert page.url == opened_url
    assert page.get_attribute('nav.tabbar a[data-tab="decisions"]', "aria-current") == "page"
