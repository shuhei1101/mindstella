"""書き換えの知らせ（GET /api/events）の結合テスト。"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from workspace_fixtures import RECORD_DIR, McpServer

from .fixture_types import MakeItem, MakeWorkspace, StartServer
from .http_helpers import EventStream

# 書き換えてから知らせが届くまでを待つ上限秒数
CHANGED_WITHIN_SEC = 1

# 書き換えが無いことを確かめる間の秒数
QUIET_SEC = 2

# つないでから、サーバーが見張りの基準を取り終えるまで待つ秒数（直後の書き換えは基準に入って知らせが無い）
WATCH_START_SEC = 0.5

# 足す検討事項
NEW_DECISION = {
    "title": "新しい問い",
    "target": "mindmap",
    "category": "データ構造",
    "phase": "要件",
    "status": "未決定",
    "options": [{"key": "A", "content": "案 A"}],
}


def _add_decision(server: McpServer, root: Path) -> None:
    """検討事項を 1 件足す。エラーならテストを止める。"""
    result = server.call("add", workspace=str(root), kind="decision", item=NEW_DECISION)
    assert result.is_error is False, result.text


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    mcp_server: McpServer,
    serve_preview: Callable[[Path], str],
    open_events: Callable[[str], EventStream],
) -> None:
    """ツールで書き換えると changed を知らせる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    stream = open_events(serve_preview(root))
    # 実行
    _add_decision(mcp_server, root)
    # 検証
    assert stream.status == 200
    assert stream.headers["content-type"] == "text/event-stream"
    assert stream.wait_for_changed(CHANGED_WITHIN_SEC) is True


def test_normal_when_other_process_writes(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
    serve_preview: Callable[[Path], str],
    open_events: Callable[[str], EventStream],
) -> None:
    """同じワークスペースを別の MCP サーバーのツールで書き換えても知らせる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    stream = open_events(serve_preview(root))
    other = start_server()
    # 実行
    _add_decision(other, root)
    # 検証
    assert stream.wait_for_changed(CHANGED_WITHIN_SEC) is True


def test_normal_when_unchanged(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
    open_events: Callable[[str], EventStream],
) -> None:
    """書き換えが無ければ changed を送らない（正常系）。"""
    # 準備
    stream = open_events(serve_preview(make_workspace(make_item("D-1"))))
    # 実行・検証
    assert stream.wait_for_changed(QUIET_SEC) is False


def test_normal_when_html_body_rewritten(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
    open_events: Callable[[str], EventStream],
) -> None:
    """YAML を書き換えずに HTML の本文のファイルだけが変わっても知らせる（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1", body="A-1.html"), bodies={"A-1.html": "<p>一覧の画面</p>\n"}
    )
    stream = open_events(serve_preview(root))
    time.sleep(WATCH_START_SEC)
    # 実行
    (root / RECORD_DIR / "docs" / "A-1.html").write_text("<p>書き換えた画面</p>\n", encoding="utf-8")
    # 検証
    assert stream.wait_for_changed(CHANGED_WITHIN_SEC) is True
