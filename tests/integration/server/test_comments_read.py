"""レビュー中のコメントの読み取り（GET /api/comments）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .fixture_types import (
    MakeComment,
    MakeDraft,
    MakeItem,
    MakeWorkspace,
    SnapshotTree,
    WriteComments,
    WriteDrafts,
)
from .http_helpers import http_request
from workspace_fixtures import RECORD_DIR

# 読み取りのパス
COMMENTS_PATH = "/api/comments"


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_draft: MakeDraft,
    write_comments: WriteComments,
    write_drafts: WriteDrafts,
    serve_preview: Callable[[Path], str],
    snapshot_tree: SnapshotTree,
) -> None:
    """レビュー中のコメントにタイトルを付け、書きかけと返す。何も書き換えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="最初の問い"))
    no_target = make_comment("C-2", body="全体に目を通した")
    del no_target["target"]
    write_comments(root, make_comment("C-1"), no_target)
    write_drafts(root, make_draft(target="D-1", body="案 B も見たい"))
    url = serve_preview(root)
    before = snapshot_tree(root)
    # 実行
    result = http_request(url, COMMENTS_PATH)
    # 検証
    assert result.status == 200
    payload = result.json()
    assert [item["id"] for item in payload["items"]] == ["C-1", "C-2"]
    assert payload["items"][0]["target_title"] == "最初の問い"
    assert (payload["items"][1]["target"], payload["items"][1]["target_title"]) == (None, None)
    assert [draft["target"] for draft in payload["drafts"]] == ["D-1"]
    assert snapshot_tree(root) == before


def test_normal_when_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """まだ無ければ空を返し、ファイルは作らない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = http_request(url, COMMENTS_PATH)
    # 検証
    assert result.status == 200
    assert result.json() == {"items": [], "drafts": []}
    assert not (root / RECORD_DIR / "comments.yaml").exists()
    assert not (root / RECORD_DIR / "drafts.yaml").exists()


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """形が崩れた comments.yaml は読まず、合わない箇所を返す（異常系）。"""
    # 準備
    broken = (
        "seq: 1\nitems:\n  - id: C-1\n    target: D-1\n    created: '2026-10-01T00:00:00+00:00'\n"
    )
    root = make_workspace(make_item("D-1"), raw_files={"comments.yaml": broken})
    url = serve_preview(root)
    # 実行
    result = http_request(url, COMMENTS_PATH)
    # 検証
    assert result.status == 422
    lines = result.json()["detail"].split("\n")
    assert any(line.startswith("comments.yaml: items[0]") for line in lines)
