"""submissions（取り込んでいない送信）の結合テスト。"""

from __future__ import annotations

from pathlib import Path

import yaml

from .fixture_types import (
    CallTool,
    MakeItem,
    MakeSubmission,
    MakeWorkspace,
    SnapshotTree,
    WriteSubmissions,
)


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """取り込んでいない送信だけを送った順に返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="最初の問い"))
    write_submissions(
        root,
        make_submission("S-1", body="取り込み済み", taken="2026-10-02T00:00:00+00:00"),
        make_submission("S-2", body="案 A にする"),
        make_submission("S-3", body="理由も残して"),
    )
    before = snapshot_tree(root)
    # 実行
    result = call_tool("submissions", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    items = result.data["items"]
    assert [item["id"] for item in items] == ["S-2", "S-3"]
    assert [item["target_title"] for item in items] == ["最初の問い", "最初の問い"]
    assert [item["body"] for item in items] == ["案 A にする", "理由も残して"]
    assert snapshot_tree(root) == before


def test_normal_when_empty(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """submissions.yaml が無ければ 0 件を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = call_tool("submissions", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data == {"items": []}
    assert not (root / "submissions.yaml").exists()


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """mindmap.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("submissions", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
    call_tool: CallTool,
) -> None:
    """手で崩した submissions.yaml は読まずに、合わない箇所を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(root, make_submission("S-1"))
    broken = yaml.safe_load((root / "submissions.yaml").read_text(encoding="utf-8"))
    del broken["items"][0]["body"]
    (root / "submissions.yaml").write_text(
        yaml.safe_dump(broken, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    # 実行
    result = call_tool("submissions", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert any(line.startswith("submissions.yaml: items[0]") for line in result.text.splitlines())
