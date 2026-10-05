"""書きかけの保存（PUT /api/drafts）の結合テスト。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import yaml

from .fixture_types import MakeDraft, MakeItem, MakeWorkspace, WriteDrafts
from .http_helpers import http_request, send_json

# 書きかけの保存のパス
DRAFTS_PATH = "/api/drafts"


def _read_drafts(root: Path) -> list[dict[str, object]]:
    """ワークスペースの書きかけの並びを読む。"""
    return yaml.safe_load((root / "drafts.yaml").read_text(encoding="utf-8"))["items"]


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """向けた先ごとに書きかけを保ち、同じ向けた先は上書きする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    first = send_json(url, "PUT", DRAFTS_PATH, {"target": "D-1", "body": "案 B"})
    second = send_json(url, "PUT", DRAFTS_PATH, {"target": "D-1", "body": "案 B も見たい"})
    # 検証
    assert (first.status, second.status) == (204, 204)
    drafts = _read_drafts(root)
    assert [(draft["target"], draft["body"]) for draft in drafts] == [("D-1", "案 B も見たい")]
    read = http_request(url, "/api/comments")
    assert [draft["body"] for draft in read.json()["drafts"]] == ["案 B も見たい"]


def test_normal_when_empty_body(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_draft: MakeDraft,
    write_drafts: WriteDrafts,
    serve_preview: Callable[[Path], str],
) -> None:
    """空の本文はその向けた先の書きかけを消す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_drafts(root, make_draft(target="D-1"))
    url = serve_preview(root)
    # 実行
    result = send_json(url, "PUT", DRAFTS_PATH, {"target": "D-1", "body": ""})
    # 検証
    assert result.status == 204
    assert [draft for draft in _read_drafts(root) if draft.get("target") == "D-1"] == []


def test_error_when_origin_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """別のサイトのページからの書きかけは保たない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = send_json(
        url,
        "PUT",
        DRAFTS_PATH,
        {"target": "D-1", "body": "案 B"},
        headers={"Origin": "https://attacker.example"},
    )
    # 検証
    assert result.status == 403
    assert not (root / "drafts.yaml").exists()


def test_error_when_target_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """ワークスペースに無い項目への書きかけは保たない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    # 実行
    result = send_json(url, "PUT", DRAFTS_PATH, {"target": "D-99", "body": "x"})
    # 検証
    assert result.status == 404
    assert "D-99" in result.json()["detail"]
    assert not (root / "drafts.yaml").exists()
