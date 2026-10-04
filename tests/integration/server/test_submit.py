"""回答・意見の送信（POST /api/submissions）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import yaml

from .fixture_types import (
    LockDirs,
    MakeItem,
    MakeSubmission,
    MakeWorkspace,
    SnapshotTree,
    WriteSubmissions,
)
from .http_helpers import http_request, post_json

# 送信の受け付けのパス
SUBMISSIONS_PATH = "/api/submissions"


def _read_submissions(root: Path) -> list[dict[str, object]]:
    """ワークスペースの送信の並びを読む。"""
    return yaml.safe_load((root / "submissions.yaml").read_text(encoding="utf-8"))["items"]


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """項目の ID と本文を受け、取り込んでいない送信として足す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    decisions_before = (root / "decisions.yaml").read_bytes()
    # 実行
    result = post_json(url, SUBMISSIONS_PATH, {"target": "D-1", "body": "案 A にする"})
    # 検証
    assert result.status == 201
    payload = result.json()
    assert payload["id"] == "S-1"
    assert _read_submissions(root) == [
        {
            "id": "S-1",
            "target": "D-1",
            "body": "案 A にする",
            "sent": payload["sent"],
            "taken": None,
        }
    ]
    assert (root / "decisions.yaml").read_bytes() == decisions_before


def test_error_when_body_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """空白だけの本文は足さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = post_json(url, SUBMISSIONS_PATH, {"target": "D-1", "body": "  "})
    # 検証
    assert result.status == 400
    assert "body" in result.json()["detail"]
    assert not (root / "submissions.yaml").exists()


def test_error_when_origin_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """別のサイトのページからの送信は足さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = post_json(
        url,
        SUBMISSIONS_PATH,
        {"target": "D-1", "body": "案 A にする"},
        headers={"Origin": "https://attacker.example"},
    )
    # 検証
    assert result.status == 403
    assert not (root / "submissions.yaml").exists()


def test_error_when_target_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """ワークスペースに無い ID へは足さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = post_json(url, SUBMISSIONS_PATH, {"target": "D-99", "body": "案 A にする"})
    # 検証
    assert result.status == 404
    assert "D-99" in result.json()["detail"]
    assert not (root / "submissions.yaml").exists()


def test_error_when_not_json(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """フォームの形の本文は足さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = http_request(
        url,
        SUBMISSIONS_PATH,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body="target=D-1&body=x",
    )
    # 検証
    assert result.status == 415
    assert not (root / "submissions.yaml").exists()


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
    serve_preview: Callable[[Path], str],
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは、前の送信を残してエラーを返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(root, make_submission("S-1"))
    url = serve_preview(root)
    before = snapshot_tree(root)
    lock_dirs(root)
    # 実行
    result = post_json(url, SUBMISSIONS_PATH, {"target": "D-1", "body": "案 A にする"})
    # 検証
    assert result.status == 500
    detail = result.json()["detail"]
    assert str(root) in detail
    assert "Traceback" not in detail
    assert snapshot_tree(root) == before
