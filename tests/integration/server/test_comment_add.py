"""レビュー中のコメントの追加（POST /api/comments）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import yaml

from .fixture_types import (
    LockDirs,
    MakeComment,
    MakeDraft,
    MakeItem,
    MakeWorkspace,
    SnapshotTree,
    WriteComments,
    WriteDrafts,
)
from .http_helpers import http_request, post_json
from workspace_fixtures import RECORD_DIR

# コメントの受け付けのパス
COMMENTS_PATH = "/api/comments"

# 資料 A-1 の本文（2 行目は書式の記号を持つ）
A_BODY = "1 行目\n- **言い換えたい**文\n3 行目"


def _read_comments(root: Path) -> dict[str, object]:
    """ワークスペースの comments.yaml を読む。"""
    return yaml.safe_load((root / RECORD_DIR / "comments.yaml").read_text(encoding="utf-8"))


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_draft: MakeDraft,
    write_drafts: WriteDrafts,
    serve_preview: Callable[[Path], str],
) -> None:
    """項目へのコメントを溜め、同じ向けた先の書きかけを消す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_drafts(root, make_draft(target="D-1", body="案 A に"))
    url = serve_preview(root)
    decisions_before = (root / RECORD_DIR / "decisions.yaml").read_bytes()
    # 実行
    result = post_json(url, COMMENTS_PATH, {"target": "D-1", "body": "案 A にする"})
    # 検証
    assert result.status == 201
    payload = result.json()
    assert (payload["id"], payload["count"]) == ("C-1", 1)
    saved = _read_comments(root)
    assert saved["seq"] == 1
    assert [(item["id"], item["target"], item["body"]) for item in saved["items"]] == [
        ("C-1", "D-1", "案 A にする")
    ]
    drafts = yaml.safe_load((root / RECORD_DIR / "drafts.yaml").read_text(encoding="utf-8"))[
        "items"
    ]
    assert [draft for draft in drafts if draft.get("target") == "D-1"] == []
    assert not (root / RECORD_DIR / "submissions.yaml").exists()
    assert (root / RECORD_DIR / "decisions.yaml").read_bytes() == decisions_before


def test_normal_when_body_location(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """本文の箇所を持つコメントを溜める（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1"), bodies={"A-1.md": A_BODY})
    url = serve_preview(root)
    loc = {"kind": "body", "start": 2, "end": 2, "text": "言い換えたい文"}
    # 実行
    result = post_json(
        url, COMMENTS_PATH, {"target": "A-1", "loc": loc, "body": "ここは言い換える"}
    )
    # 検証
    assert result.status == 201
    assert _read_comments(root)["items"][0]["loc"] == loc


def test_normal_when_no_target(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """項目に紐づかないコメントを溜める（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = post_json(url, COMMENTS_PATH, {"body": "全体に目を通した"})
    # 検証
    assert result.status == 201
    item = _read_comments(root)["items"][0]
    assert "target" not in item
    assert "loc" not in item


def test_normal_when_restore(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """消したコメントを同じ ID と日時で元の並びに戻す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"), make_comment("C-3"), seq=3)
    url = serve_preview(root)
    created = "2026-10-05T01:00:00+00:00"
    # 実行
    result = post_json(
        url,
        COMMENTS_PATH,
        {"id": "C-2", "created": created, "target": "D-1", "body": "戻すコメント"},
    )
    # 検証
    assert result.status == 201
    assert result.json()["id"] == "C-2"
    saved = _read_comments(root)
    assert saved["seq"] == 3
    assert [item["id"] for item in saved["items"]] == ["C-1", "C-2", "C-3"]


def test_error_when_body_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """空白だけの本文は溜めない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = post_json(url, COMMENTS_PATH, {"target": "D-1", "body": "  "})
    # 検証
    assert result.status == 400
    assert "body" in result.json()["detail"]
    assert not (root / RECORD_DIR / "comments.yaml").exists()


def test_error_when_origin_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """別のサイトのページからのコメントは溜めない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = post_json(
        url,
        COMMENTS_PATH,
        {"target": "D-1", "body": "案 A にする"},
        headers={"Origin": "https://attacker.example"},
    )
    # 検証
    assert result.status == 403
    assert not (root / RECORD_DIR / "comments.yaml").exists()


def test_error_when_target_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """ワークスペースに無い項目へは溜めない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = post_json(url, COMMENTS_PATH, {"target": "D-99", "body": "案 A にする"})
    # 検証
    assert result.status == 404
    assert "D-99" in result.json()["detail"]
    assert not (root / RECORD_DIR / "comments.yaml").exists()


def test_error_when_location_stale(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """本文に無い文を指す箇所は溜めない（異常系）。"""
    # 準備
    root = make_workspace(make_item("A-1"), bodies={"A-1.md": A_BODY})
    url = serve_preview(root)
    loc = {"kind": "body", "start": 1, "end": 1, "text": "本文に無い文"}
    # 実行
    result = post_json(url, COMMENTS_PATH, {"target": "A-1", "loc": loc, "body": "本文"})
    # 検証
    assert result.status == 409
    assert result.json()["detail"] != ""
    assert not (root / RECORD_DIR / "comments.yaml").exists()


def test_error_when_not_json(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """フォームの形の本文は溜めない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = http_request(
        url,
        COMMENTS_PATH,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body="target=D-1&body=x",
    )
    # 検証
    assert result.status == 415
    assert not (root / RECORD_DIR / "comments.yaml").exists()


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは、前のコメントを残してエラーを返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    url = serve_preview(root)
    before = snapshot_tree(root)
    lock_dirs(root / RECORD_DIR)
    # 実行
    result = post_json(url, COMMENTS_PATH, {"target": "D-1", "body": "案 A にする"})
    # 検証
    assert result.status == 500
    detail = result.json()["detail"]
    assert str(root) in detail
    assert "Traceback" not in detail
    assert snapshot_tree(root) == before
