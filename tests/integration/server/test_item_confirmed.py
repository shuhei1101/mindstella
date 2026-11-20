"""確認済みの付け外し（PUT /api/items/{id}/confirmed）の結合テスト。"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from .fixture_types import LockDirs, MakeItem, MakeWorkspace
from .http_helpers import send_json
from workspace_fixtures import RECORD_DIR

# 書き換える前の D-1 の更新日時・通し番号・変更履歴
D1_UPDATED = "2026-10-05T01:00:00+00:00"
D1_HISTORY = [{"seq": 2, "at": D1_UPDATED, "by": "ai", "before": {"answer": None}}]


def _history_path(root: Path) -> Path:
    """`history.yaml` のパス。"""
    return root / RECORD_DIR / "history.yaml"


def _rows(root: Path) -> dict[str, Any]:
    """`history.yaml` の `items` を読む。"""
    return yaml.safe_load(_history_path(root).read_text(encoding="utf-8"))["items"]


def _drop_row(root: Path, item_id: str) -> None:
    """`history.yaml` から 1 行を消す。"""
    data = yaml.safe_load(_history_path(root).read_text(encoding="utf-8"))
    data["items"].pop(item_id)
    _history_path(root).write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def test_normal(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """確認済みにし、解除するとキーを消す。項目の中身・更新日時・変更履歴は変えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", updated=D1_UPDATED, updated_by="ai", seq=2, history=D1_HISTORY))
    url = serve_preview(root)
    decisions_before = (root / RECORD_DIR / "decisions.yaml").read_bytes()
    changes_path = root / RECORD_DIR / "changes.yaml"
    changes_before = changes_path.read_bytes() if changes_path.exists() else None
    row_before = dict(_rows(root)["D-1"])
    # 実行
    first = send_json(url, "PUT", "/api/items/D-1/confirmed", {"confirmed": True})
    after_first = dict(_rows(root)["D-1"])
    second = send_json(url, "PUT", "/api/items/D-1/confirmed", {"confirmed": False})
    after_second = dict(_rows(root)["D-1"])
    # 検証
    assert (first.status, first.json()) == (200, {"id": "D-1", "confirmed": True})
    assert after_first == {**row_before, "confirmed": True}
    assert (second.status, second.json()) == (200, {"id": "D-1", "confirmed": False})
    assert after_second == row_before
    assert (root / RECORD_DIR / "decisions.yaml").read_bytes() == decisions_before
    assert (changes_path.read_bytes() if changes_path.exists() else None) == changes_before


def test_normal_when_no_history_row(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """行が無い項目は confirmed だけの行を作り、解除すると行ごと消す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("D-2"))
    _drop_row(root, "D-1")
    url = serve_preview(root)
    # 実行
    first = send_json(url, "PUT", "/api/items/D-1/confirmed", {"confirmed": True})
    after_first = _rows(root).get("D-1")
    second = send_json(url, "PUT", "/api/items/D-1/confirmed", {"confirmed": False})
    after_second = _rows(root)
    # 検証
    assert (first.status, second.status) == (200, 200)
    assert after_first == {"confirmed": True}
    assert "D-1" not in after_second
    assert "D-2" in after_second


def test_normal_when_unchanged(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """既にその状態なら書かない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", confirmed=True))
    url = serve_preview(root)
    stamp = _history_path(root).stat().st_mtime_ns
    content = _history_path(root).read_bytes()
    time.sleep(0.01)
    # 実行
    result = send_json(url, "PUT", "/api/items/D-1/confirmed", {"confirmed": True})
    # 検証
    assert (result.status, result.json()) == (200, {"id": "D-1", "confirmed": True})
    assert _history_path(root).stat().st_mtime_ns == stamp
    assert _history_path(root).read_bytes() == content


def test_error_when_origin_mismatch(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """別のサイトのページからの書き換えは受けない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    before = _history_path(root).read_bytes()
    # 実行
    result = send_json(
        url,
        "PUT",
        "/api/items/D-1/confirmed",
        {"confirmed": True},
        headers={"Origin": "https://attacker.example"},
    )
    # 検証
    assert result.status == 403
    assert _history_path(root).read_bytes() == before


def test_error_when_item_not_found(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """記録に無い項目は書き換えない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    before = _history_path(root).read_bytes()
    # 実行
    result = send_json(url, "PUT", "/api/items/D-9/confirmed", {"confirmed": True})
    # 検証
    assert result.status == 404
    assert "D-9" in result.json()["detail"]
    assert _history_path(root).read_bytes() == before


def test_error_when_body_invalid(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """confirmed が真偽値でない本文は受けない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    before = _history_path(root).read_bytes()
    # 実行
    result = send_json(url, "PUT", "/api/items/D-1/confirmed", {"confirmed": "yes"})
    # 検証
    assert result.status == 400
    assert "confirmed" in result.json()["detail"]
    assert _history_path(root).read_bytes() == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは前の状態を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    before = _history_path(root).read_bytes()
    lock_dirs(root / RECORD_DIR)
    # 実行
    result = send_json(url, "PUT", "/api/items/D-1/confirmed", {"confirmed": True})
    # 検証
    assert result.status == 500
    detail = result.json()["detail"]
    assert str(root) in detail
    assert "Traceback" not in detail
    assert _history_path(root).read_bytes() == before
