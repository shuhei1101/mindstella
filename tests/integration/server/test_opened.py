"""POST /api/opened（前回開いた日時）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import yaml

from .fixture_types import CallTool, LockDirs, MakeItem, MakeWorkspace, SnapshotTree
from .history_helpers import DECISION_ITEM, add_item, commit
from .http_helpers import http_request
from workspace_fixtures import RECORD_DIR

# 前回開いた時点（日時と通し番号）を持つファイルの名前
OPENED_FILE = ".mindstella-opened"

# 前の版の形（日時だけ）の前回開いた日時と、通し番号を持つ形の前回開いた時点
PREVIOUS_VERSION_OPENED_AT = "2026-10-04T13:05:00+00:00"
OPENED_WITH_SEQ_TEXT = "2026-10-04T13:05:00+00:00\n3\n"

# スキーマに合わない変更履歴（last_seq が文字列）
INVALID_CHANGES_TEXT = 'last_seq: "x"\nsets: []\npending:\n  added: []\n  changed: []\n'


def test_normal(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    serve_preview: Callable[[Path], str],
) -> None:
    """開くたびに前回開いた時点を返し、今の時点に書き換える（正常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "decision", DECISION_ITEM)
    commit(call_tool, root, "足す")
    # まとめていない変更を 1 つ足し、先頭のまとまりの until_seq を last_seq より小さくする
    add_item(call_tool, root, "decision", DECISION_ITEM)
    changes = yaml.safe_load((root / RECORD_DIR / "changes.yaml").read_text(encoding="utf-8"))
    head_seq = changes["sets"][0]["until_seq"]
    assert head_seq < changes["last_seq"]
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
    assert first.json()["opened"]["seq"] == head_seq
    assert second.json()["previous"] == first.json()["opened"]
    opened_lines = (root / RECORD_DIR / OPENED_FILE).read_text(encoding="utf-8").splitlines()
    assert opened_lines == [second.json()["opened"]["at"], str(second.json()["opened"]["seq"])]
    for name, content in records.items():
        assert (root / RECORD_DIR / name).read_bytes() == content


def test_normal_when_previous_has_no_seq(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """日時だけを持つ前の版の形は前回開いた時点なしとして返し、今の形で書き換える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"), raw_files={OPENED_FILE: f"{PREVIOUS_VERSION_OPENED_AT}\n"}
    )
    url = serve_preview(root)
    # 実行
    result = http_request(url, "/api/opened", method="POST")
    # 検証
    assert result.status == 200
    assert result.json()["previous"] is None
    opened_lines = (root / RECORD_DIR / OPENED_FILE).read_text(encoding="utf-8").splitlines()
    assert opened_lines == [result.json()["opened"]["at"], str(result.json()["opened"]["seq"])]


def test_error_when_changes_invalid(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """変更履歴がスキーマに合わないときは合わない箇所を返し、前回開いた時点を書き換えない（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        raw_files={OPENED_FILE: OPENED_WITH_SEQ_TEXT, "changes.yaml": INVALID_CHANGES_TEXT},
    )
    url = serve_preview(root)
    # 実行
    result = http_request(url, "/api/opened", method="POST")
    # 検証
    assert result.status == 422
    assert result.headers["content-type"].startswith("application/problem+json")
    assert any(
        line.startswith("changes.yaml: last_seq:") for line in result.json()["detail"].splitlines()
    )
    assert (root / RECORD_DIR / OPENED_FILE).read_text(encoding="utf-8") == OPENED_WITH_SEQ_TEXT


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
