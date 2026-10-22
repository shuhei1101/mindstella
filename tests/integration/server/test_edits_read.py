"""保存待ちの編集の読み取り（GET /api/edits）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .fixture_types import MakeEdit, MakeItem, MakeWorkspace, WriteEdits
from .http_helpers import http_request
from workspace_fixtures import RECORD_DIR

# 保存待ちの編集の読み取りのパス
EDITS_PATH = "/api/edits"


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    serve_preview: Callable[[Path], str],
) -> None:
    """溜めた順に保存待ちの編集を返し、書き込めるかの確かめ用の控えは返さない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_edits(
        root,
        make_edit("E-1"),
        make_edit(
            "E-2",
            target="new-1",
            op="item-add",
            key="tasks",
            value={"title": "画面を作る", "status": "未着手"},
            before=None,
            base=None,
        ),
    )
    url = serve_preview(root)
    # 実行
    result = http_request(url, EDITS_PATH)
    # 検証
    assert result.status == 200
    payload = result.json()
    assert payload["count"] == 2
    assert [(e["id"], e["target"], e["op"], e["key"]) for e in payload["items"]] == [
        ("E-1", "D-1", "set", "answer"),
        ("E-2", "new-1", "item-add", "tasks"),
    ]
    assert all("base" not in edit for edit in payload["items"])


def test_normal_when_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """edits.yaml が無ければ 0 件を返し、ファイルは作らない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = http_request(url, EDITS_PATH)
    # 検証
    assert result.status == 200
    assert result.json() == {"items": [], "count": 0}
    assert not (root / RECORD_DIR / "edits.yaml").exists()


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_edit: MakeEdit,
    write_edits: WriteEdits,
    serve_preview: Callable[[Path], str],
) -> None:
    """スキーマに合わない edits.yaml は読まず、合わない箇所を 422 で返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_edits(root, make_edit("E-1", op="rename"))
    url = serve_preview(root)
    # 実行
    result = http_request(url, EDITS_PATH)
    # 検証
    assert result.status == 422
    detail = result.json()["detail"]
    assert "edits.yaml" in detail
    assert "op" in detail
