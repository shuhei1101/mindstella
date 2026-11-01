"""保存待ちの編集の取り消し（DELETE /api/edits/{id}）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from .fixture_types import MakeEdit, MakeItem, MakeWorkspace, SnapshotTree, WriteEdits
from .http_helpers import http_request
from workspace_fixtures import RECORD_DIR

# 保存待ちの編集のパス
EDITS_PATH = "/api/edits"

# 別のサイトのページから送る送り元
FOREIGN_ORIGIN = {"Origin": "https://attacker.example"}


def _read_edits(root: Path) -> dict[str, Any]:
    """ワークスペースの edits.yaml を読む。"""
    return yaml.safe_load((root / RECORD_DIR / "edits.yaml").read_text(encoding="utf-8"))


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    serve_preview: Callable[[Path], str],
) -> None:
    """保存待ちの編集 1 件を外し、残りの件数を返す。項目は書き換えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("T-1"))
    write_edits(
        root,
        make_edit("E-1"),
        make_edit("E-2", target="T-1", key="status", value="完了", before="未着手"),
    )
    url = serve_preview(root)
    tasks_before = (root / RECORD_DIR / "tasks.yaml").read_bytes()
    # 実行
    result = http_request(url, f"{EDITS_PATH}/E-2", method="DELETE")
    # 検証
    assert result.status == 200
    assert result.json() == {"removed": ["E-2"], "count": 1}
    assert [edit["id"] for edit in _read_edits(root)["items"]] == ["E-1"]
    assert (root / RECORD_DIR / "tasks.yaml").read_bytes() == tasks_before


def test_normal_when_option_add(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    serve_preview: Callable[[Path], str],
) -> None:
    """足した案の追加を取り消すと、その案を採用する切り替えも一緒に外す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_edits(
        root,
        make_edit("E-1", op="option-add", key="C", value={"content": "案 C"}, before=None),
        make_edit("E-2", op="adopt", key="C", value="C", before="A"),
    )
    url = serve_preview(root)
    # 実行
    result = http_request(url, f"{EDITS_PATH}/E-1", method="DELETE")
    # 検証
    assert result.status == 200
    assert result.json() == {"removed": ["E-1", "E-2"], "count": 0}
    assert _read_edits(root)["items"] == []


def test_error_when_origin_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    serve_preview: Callable[[Path], str],
) -> None:
    """別のサイトのページからは外さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_edits(root, make_edit("E-1"))
    url = serve_preview(root)
    # 実行
    result = http_request(url, f"{EDITS_PATH}/E-1", method="DELETE", headers=FOREIGN_ORIGIN)
    # 検証
    assert result.status == 403
    assert [edit["id"] for edit in _read_edits(root)["items"]] == ["E-1"]


def test_error_when_edit_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    serve_preview: Callable[[Path], str],
    snapshot_tree: SnapshotTree,
) -> None:
    """保存待ちに無い ID は外さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_edits(root, make_edit("E-1"))
    url = serve_preview(root)
    before = snapshot_tree(root)
    # 実行
    result = http_request(url, f"{EDITS_PATH}/E-9", method="DELETE")
    # 検証
    assert result.status == 404
    assert "E-9" in result.json()["detail"]
    assert snapshot_tree(root) == before
