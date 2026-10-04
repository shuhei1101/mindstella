"""レビュー中のコメントの書き換え（PATCH /api/comments/{id}）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import yaml

from .fixture_types import MakeComment, MakeItem, MakeWorkspace, WriteComments
from .http_helpers import send_json


def _read_comments(root: Path) -> dict[str, object]:
    """ワークスペースの comments.yaml を読む。"""
    return yaml.safe_load((root / "comments.yaml").read_text(encoding="utf-8"))


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """本文を書き換え、並びとほかのキーは変えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1", body="案 A にする"), make_comment("C-2"))
    url = serve_preview(root)
    before = _read_comments(root)
    # 実行
    result = send_json(url, "PATCH", "/api/comments/C-1", {"body": "案 A に決める"})
    # 検証
    assert result.status == 200
    assert result.json()["body"] == "案 A に決める"
    saved = _read_comments(root)
    assert [item["id"] for item in saved["items"]] == ["C-1", "C-2"]
    assert saved["items"][0] == {**before["items"][0], "body": "案 A に決める"}
    assert saved["items"][1] == before["items"][1]


def test_normal_when_remove_location(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """箇所を外して項目へのコメントにする（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1"), bodies={"A-1.md": "1 行目\n2 行目\n3 行目\n4 行目\n5 行目"}
    )
    loc = {"kind": "body", "start": 5, "end": 5, "text": "5 行目"}
    write_comments(root, make_comment("C-1", target="A-1", loc=loc))
    url = serve_preview(root)
    # 実行
    result = send_json(url, "PATCH", "/api/comments/C-1", {"loc": None})
    # 検証
    assert result.status == 200
    assert result.json()["loc"] is None
    item = _read_comments(root)["items"][0]
    assert "loc" not in item
    assert item["target"] == "A-1"


def test_error_when_body_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """空白だけの本文には書き換えない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    url = serve_preview(root)
    before = (root / "comments.yaml").read_bytes()
    # 実行
    result = send_json(url, "PATCH", "/api/comments/C-1", {"body": "  "})
    # 検証
    assert result.status == 400
    assert "body" in result.json()["detail"]
    assert (root / "comments.yaml").read_bytes() == before


def test_error_when_origin_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """別のサイトのページからの書き換えは受けない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    url = serve_preview(root)
    before = (root / "comments.yaml").read_bytes()
    # 実行
    result = send_json(
        url,
        "PATCH",
        "/api/comments/C-1",
        {"body": "案 A に決める"},
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
    """レビュー中に無い ID は書き換えない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    url = serve_preview(root)
    before = (root / "comments.yaml").read_bytes()
    # 実行
    result = send_json(url, "PATCH", "/api/comments/C-9", {"body": "案 A に決める"})
    # 検証
    assert result.status == 404
    assert "C-9" in result.json()["detail"]
    assert (root / "comments.yaml").read_bytes() == before
