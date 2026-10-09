"""プレビューを開く（`session` がサーバーが配るプレビューの URL を示し、記録の書き換えを開いている画面へ反映する）の E2E テスト。

起動スクリプトの代わりに MCP サーバーを立て、示された URL を実際のブラウザで開く。描画のライブラリは CDN から読む。
"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page
from preview_helpers import OpenPreview, row_ids
from readme_helpers import preview_section
from workspace_fixtures import CallTool, MakeItem, MakeWorkspace, SnapshotTree

# 書き換えが画面に出るまで待つ上限ミリ秒
UPDATE_TIMEOUT_MS = 10_000

# 配信のページの路（`preview_url` が返す URL の終わり）
PAGE_PATH = "/mindstella.html"

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
    assert url.endswith(PAGE_PATH)
    assert row_ids(page) == ["D-1"]
    assert not (root / "preview.html").exists()
    # 直下の README.md のプレビューの節が、示した URL である
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert preview_section(readme).splitlines()[1] == url


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


def test_error_when_config_invalid(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """config.yaml がスキーマに合わないと、違う箇所を示すエラーが返り、配信は立たない（異常系）。"""
    # 準備
    root = make_workspace(settings={**valid_settings, "display": {"network_look": "rainbow"}})
    before = snapshot_tree(root)
    # 実行
    result = call_tool("preview_url", workspace=str(root))
    again = call_tool("preview_url", workspace=str(root))
    # 検証
    # プレビューの URL の取得がエラーを返し、本文に見た目の既定のキーと、選べる値が示される
    assert result.is_error is True
    assert any(
        line.startswith("config.yaml: display.network_look: ")
        and all(look in line for look in ("glow", "starlight", "constellation", "deep", "dust"))
        for line in result.text.splitlines()
    )
    # 配信が立っていないので、呼び直しても URL を返さず同じエラーになる
    assert again.is_error is True
    assert "config.yaml: display.network_look: " in again.text
    # config.yaml の中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before
