"""take_submission（送信を取り込み済みにする）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .fixture_types import (
    CallTool,
    LockDirs,
    MakeItem,
    MakeSubmission,
    MakeWorkspace,
    WriteSubmissions,
)
from workspace_fixtures import RECORD_DIR

# 取り込み済みの送信の日時
TAKEN_AT = "2026-10-02T00:00:00+00:00"


def _read_submissions(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの送信の並びを読む。"""
    return yaml.safe_load((root / RECORD_DIR / "submissions.yaml").read_text(encoding="utf-8"))[
        "items"
    ]


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
    call_tool: CallTool,
) -> None:
    """取り込んでいない送信に取り込んだ日時を付ける（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(
        root, make_submission("S-1", taken=TAKEN_AT), make_submission("S-2", body="案 A にする")
    )
    # 実行
    result = call_tool("take_submission", workspace=str(root), id="S-2")
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["id"] == "S-2"
    assert result.data["already"] is False
    submissions = _read_submissions(root)
    assert submissions[0] == make_submission("S-1", taken=TAKEN_AT)
    assert submissions[1]["taken"] == result.data["taken"]
    pending = call_tool("submissions", workspace=str(root))
    assert pending.data == {"items": []}


def test_normal_when_already_taken(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
    call_tool: CallTool,
) -> None:
    """取り込み済みの送信には書かずに、前の日時を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(root, make_submission("S-1", taken=TAKEN_AT))
    before = (root / RECORD_DIR / "submissions.yaml").read_bytes()
    # 実行
    result = call_tool("take_submission", workspace=str(root), id="S-1")
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["already"] is True
    assert result.data["taken"] == TAKEN_AT
    assert (root / RECORD_DIR / "submissions.yaml").read_bytes() == before


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("take_submission", workspace=str(root), id="S-1")
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_submission_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
    call_tool: CallTool,
) -> None:
    """無い ID を指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(root, make_submission("S-1"))
    before = (root / RECORD_DIR / "submissions.yaml").read_bytes()
    # 実行
    result = call_tool("take_submission", workspace=str(root), id="S-9")
    # 検証
    assert result.is_error is True
    assert "S-9" in result.text
    assert (root / RECORD_DIR / "submissions.yaml").read_bytes() == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
    call_tool: CallTool,
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは、前の送信を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(root, make_submission("S-1"))
    before = (root / RECORD_DIR / "submissions.yaml").read_bytes()
    lock_dirs(root / RECORD_DIR)
    # 実行
    result = call_tool("take_submission", workspace=str(root), id="S-1")
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert "Traceback" not in result.text
    assert (root / RECORD_DIR / "submissions.yaml").read_bytes() == before
