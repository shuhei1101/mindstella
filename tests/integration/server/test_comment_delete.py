"""レビュー中のコメントの削除（DELETE /api/comments/{id}）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import yaml

from .fixture_types import MakeComment, MakeItem, MakeWorkspace, WriteComments
from .http_helpers import http_request


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """消して中身と件数を返し、連番は変えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"), make_comment("C-2", body="案 B も見たい"), seq=2)
    url = serve_preview(root)
    # 実行
    result = http_request(url, "/api/comments/C-2", method="DELETE")
    # 検証
    assert result.status == 200
    payload = result.json()
    assert (payload["body"], payload["count"]) == ("案 B も見たい", 1)
    saved = yaml.safe_load((root / "comments.yaml").read_text(encoding="utf-8"))
    assert [item["id"] for item in saved["items"]] == ["C-1"]
    assert saved["seq"] == 2


def test_error_when_origin_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """別のサイトのページからの削除は受けない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    url = serve_preview(root)
    before = (root / "comments.yaml").read_bytes()
    # 実行
    result = http_request(
        url,
        "/api/comments/C-1",
        method="DELETE",
        headers={"Origin": "https://attacker.example"},
    )
    # 検証
    assert result.status == 403
    assert (root / "comments.yaml").read_bytes() == before


def test_error_when_comment_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """レビュー中に無い ID は消さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    url = serve_preview(root)
    before = (root / "comments.yaml").read_bytes()
    # 実行
    result = http_request(url, "/api/comments/C-9", method="DELETE")
    # 検証
    assert result.status == 404
    assert "C-9" in result.json()["detail"]
    assert (root / "comments.yaml").read_bytes() == before
