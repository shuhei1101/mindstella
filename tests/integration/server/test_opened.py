"""POST /api/opened（前回開いた日時）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .fixture_types import CallTool, LockDirs, MakeItem, MakeWorkspace, SnapshotTree
from .history_helpers import DECISION_ITEM, add_item, commit
from .http_helpers import http_request
from workspace_fixtures import RECORD_DIR

# 前回開いた日時を持つファイルの名前
OPENED_FILE = ".mindstella-opened"


def test_normal(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    serve_preview: Callable[[Path], str],
) -> None:
    """開くたびに前回開いた日時を返し、今の日時に書き換える（正常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "decision", DECISION_ITEM)
    commit(call_tool, root, "足す")
    url = serve_preview(root)
    records = {
        name: (root / RECORD_DIR / name).read_bytes() for name in ("decisions.yaml", "changes.yaml")
    }
    # 実行
    first = http_request(url, "/api/opened", method="POST")
    second = http_request(url, "/api/opened", method="POST")
    # 検証
    assert first.status == 200
    assert second.status == 200
    assert first.json()["previous"] is None
    assert second.json()["previous"] == first.json()["opened"]
    opened_text = (root / RECORD_DIR / OPENED_FILE).read_text(encoding="utf-8")
    assert opened_text.splitlines()[0] == second.json()["opened"]
    for name, content in records.items():
        assert (root / RECORD_DIR / name).read_bytes() == content


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは 500 を返し、ファイルを作らない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    before = snapshot_tree(root)
    lock_dirs(root / RECORD_DIR)
    # 実行
    result = http_request(url, "/api/opened", method="POST")
    # 検証
    assert result.status == 500
    assert result.headers["content-type"].startswith("application/problem+json")
    assert snapshot_tree(root) == before
    assert not (root / OPENED_FILE).exists()
