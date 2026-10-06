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
from workspace_fixtures import RECORD_DIR


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """取り込んでいない送信だけを送った順に返し、箇所と項目に紐づかない送信も返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", title="最初の問い"),
        make_item("A-1"),
        bodies={"A-1.md": "1 行目\n言い換えたい文\n3 行目"},
    )
    loc = {"kind": "body", "start": 2, "end": 2, "text": "言い換えたい文"}
    no_target = make_submission("S-4", body="全体に目を通した")
    del no_target["target"]
    write_submissions(
        root,
        make_submission("S-1", body="取り込み済み", taken="2026-10-02T00:00:00+00:00"),
        make_submission("S-2", body="案 A にする"),
        make_submission("S-3", target="A-1", body="ここは言い換える", loc=loc),
        no_target,
    )
    before = snapshot_tree(root)
    # 実行
    result = call_tool("submissions", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    items = result.data["items"]
    assert [item["id"] for item in items] == ["S-2", "S-3", "S-4"]
    assert (items[0]["target_title"], items[0]["loc"]) == ("最初の問い", None)
    assert items[1]["loc"] == loc
    assert (items[2]["target"], items[2]["target_title"], items[2]["loc"]) == (None, None, None)
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
    assert not (root / RECORD_DIR / "submissions.yaml").exists()


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
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
    broken = yaml.safe_load((root / RECORD_DIR / "submissions.yaml").read_text(encoding="utf-8"))
    del broken["items"][0]["body"]
    (root / RECORD_DIR / "submissions.yaml").write_text(
        yaml.safe_dump(broken, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    # 実行
    result = call_tool("submissions", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert any(line.startswith("submissions.yaml: items[0]") for line in result.text.splitlines())
