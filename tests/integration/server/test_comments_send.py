"""コメントをまとめて送る（POST /api/comments/send）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import yaml

from .fixture_types import (
    LockDirs,
    MakeComment,
    MakeItem,
    MakeSubmission,
    MakeWorkspace,
    SnapshotTree,
    WriteComments,
    WriteSubmissions,
)
from .http_helpers import http_request, post_json

# まとめて送るのパス
SEND_PATH = "/api/comments/send"

# 資料 A-1 の本文
A_BODY = "1 行目\n言い換えたい文\n3 行目"


def _read(root: Path, name: str) -> dict[str, object]:
    """ワークスペースの YAML を読む。"""
    return yaml.safe_load((root / name).read_text(encoding="utf-8"))


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """チェックしたコメントだけを送信へ移し、残りはレビュー中に残す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("A-1"), bodies={"A-1.md": A_BODY})
    loc = {"kind": "body", "start": 2, "end": 2, "text": "言い換えたい文"}
    no_target = make_comment("C-3", body="全体に目を通した")
    del no_target["target"]
    write_comments(
        root,
        make_comment("C-1", body="案 A にする"),
        make_comment("C-2", target="A-1", loc=loc, body="ここは言い換える"),
        no_target,
    )
    url = serve_preview(root)
    decisions_before = (root / "decisions.yaml").read_bytes()
    docs_before = (root / "docs.yaml").read_bytes()
    # 実行
    result = post_json(url, SEND_PATH, {"ids": ["C-2", "C-1"]})
    # 検証
    assert result.status == 201
    assert result.json()["items"] == [
        {"comment": "C-1", "submission": "S-1"},
        {"comment": "C-2", "submission": "S-2"},
    ]
    submissions = _read(root, "submissions.yaml")["items"]
    assert [(item["id"], item["target"], item["taken"]) for item in submissions] == [
        ("S-1", "D-1", None),
        ("S-2", "A-1", None),
    ]
    assert "loc" not in submissions[0]
    assert submissions[1]["loc"] == loc
    assert [item["id"] for item in _read(root, "comments.yaml")["items"]] == ["C-3"]
    assert (root / "decisions.yaml").read_bytes() == decisions_before
    assert (root / "docs.yaml").read_bytes() == docs_before


def test_error_when_ids_empty(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """チェックが 0 件の送信は受けない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    url = serve_preview(root)
    # 実行
    result = post_json(url, SEND_PATH, {"ids": []})
    # 検証
    assert result.status == 400
    assert "ids" in result.json()["detail"]
    assert not (root / "submissions.yaml").exists()


def test_error_when_origin_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """別のサイトのページからの送信は受けない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    url = serve_preview(root)
    before = (root / "comments.yaml").read_bytes()
    # 実行
    result = post_json(
        url, SEND_PATH, {"ids": ["C-1"]}, headers={"Origin": "https://attacker.example"}
    )
    # 検証
    assert result.status == 403
    assert not (root / "submissions.yaml").exists()
    assert (root / "comments.yaml").read_bytes() == before


def test_error_when_comment_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """消えたコメントを含むと、どれも送らない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    url = serve_preview(root)
    before = (root / "comments.yaml").read_bytes()
    # 実行
    result = post_json(url, SEND_PATH, {"ids": ["C-1", "C-9"]})
    # 検証
    assert result.status == 404
    assert "C-9" in result.json()["detail"]
    assert not (root / "submissions.yaml").exists()
    assert (root / "comments.yaml").read_bytes() == before


def test_error_when_location_stale(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """本文が書き換わって箇所が合わないコメントがあれば、どれも送らない（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"), make_item("A-1"), bodies={"A-1.md": "1 行目\n2 行目\n3 行目"}
    )
    stale_loc = {"kind": "body", "start": 5, "end": 5, "text": "5 行目"}
    write_comments(root, make_comment("C-1"), make_comment("C-2", target="A-1", loc=stale_loc))
    url = serve_preview(root)
    before = (root / "comments.yaml").read_bytes()
    # 実行
    result = post_json(url, SEND_PATH, {"ids": ["C-1", "C-2"]})
    # 検証
    assert result.status == 409
    stale = result.json()["stale"]
    assert [item["id"] for item in stale] == ["C-2"]
    assert stale[0]["reason"] != ""
    assert not (root / "submissions.yaml").exists()
    assert (root / "comments.yaml").read_bytes() == before


def test_error_when_not_json(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    write_comments: WriteComments,
    serve_preview: Callable[[Path], str],
) -> None:
    """フォームの形の本文は受けない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_comments(root, make_comment("C-1"))
    url = serve_preview(root)
    # 実行
    result = http_request(
        url,
        SEND_PATH,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body="ids=C-1",
    )
    # 検証
    assert result.status == 415
    assert not (root / "submissions.yaml").exists()


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_comment: MakeComment,
    make_submission: MakeSubmission,
    write_comments: WriteComments,
    write_submissions: WriteSubmissions,
    serve_preview: Callable[[Path], str],
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは、送信もレビュー中も前のままにする（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(root, make_submission("S-1"))
    write_comments(root, make_comment("C-1"))
    url = serve_preview(root)
    before = snapshot_tree(root)
    lock_dirs(root)
    # 実行
    result = post_json(url, SEND_PATH, {"ids": ["C-1"]})
    # 検証
    assert result.status == 500
    detail = result.json()["detail"]
    assert str(root) in detail
    assert "Traceback" not in detail
    assert snapshot_tree(root) == before
