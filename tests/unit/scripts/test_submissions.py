"""submissions.py（回答・意見の送信の読み書き）の単体テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

import store
import submissions
from errors import (
    ItemNotFoundError,
    SchemaMismatchError,
    SubmissionInvalidError,
    SubmissionNotFoundError,
    WriteFailedError,
)
from fixture_types import FailingReplace, MakeItem, MakeSubmission, MakeWorkspace, WriteSubmissions

# now の代わりに返す日時
FIXED_NOW = "2026-10-04T03:00:00+00:00"

# 本文の上限（非機能要件の「送信の本文の長さ」）
MAX_BODY_CHARS = 10000


def _fixed_now() -> str:
    """今の日時の代わりに、決めた日時を返す。"""
    return FIXED_NOW


def _read_submissions(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの submissions.yaml を読んで、送信の並びを返す。"""
    data = yaml.safe_load((root / "submissions.yaml").read_text(encoding="utf-8"))
    return data["items"]


def test_load_submissions(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """並びの順に読む（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(root, make_submission("S-1"), make_submission("S-2", body="二つ目"))
    # 実行
    result = submissions.load_submissions(root)
    # 検証
    assert result == [
        submissions.Submission(
            id="S-1",
            target="D-1",
            body="S-1の本文",
            sent="2026-10-01T00:00:00+00:00",
            taken=None,
        ),
        submissions.Submission(
            id="S-2",
            target="D-1",
            body="二つ目",
            sent="2026-10-01T00:00:00+00:00",
            taken=None,
        ),
    ]


def test_load_submissions_when_missing(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """ファイルが無ければ空（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = submissions.load_submissions(root)
    # 検証
    assert result == []


@pytest.mark.parametrize(
    ("text", "expected_prefix"),
    [
        pytest.param("items: [", "submissions.yaml: ", id="unreadable"),
        pytest.param(
            "items:\n  - id: S-1\n    target: D-1\n    sent: 2026-10-01T00:00:00+00:00\n    taken: null\n",
            "submissions.yaml: items[0]",
            id="body_removed",
        ),
    ],
)
def test_load_submissions_when_invalid(
    make_workspace: MakeWorkspace, make_item: MakeItem, text: str, expected_prefix: str
) -> None:
    """読めない・合わないファイルは読まない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), raw_files={"submissions.yaml": text})
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        submissions.load_submissions(root)
    assert exc_info.value.lines[0].startswith(expected_prefix)


def test_add_submission(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """連番を振って末尾に足す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(root, make_submission("S-1"), make_submission("S-3"))
    # 実行
    result = submissions.add_submission(
        root, {"target": "D-1", "body": "  案 A にする "}, now=_fixed_now
    )
    # 検証
    assert result == submissions.Submission(
        id="S-4", target="D-1", body="案 A にする", sent=FIXED_NOW, taken=None
    )
    assert _read_submissions(root)[-1] == {
        "id": "S-4",
        "target": "D-1",
        "body": "案 A にする",
        "sent": FIXED_NOW,
        "taken": None,
    }


def test_add_submission_when_first(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """ファイルが無ければ作って S-1（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = submissions.add_submission(root, {"target": "D-1", "body": "最初"}, now=_fixed_now)
    # 検証
    assert result.id == "S-1"
    assert (root / "submissions.yaml").is_file()


@pytest.mark.parametrize(
    ("data", "expected_key"),
    [
        pytest.param({"target": "D-1", "body": "  "}, "body", id="blank_body"),
        pytest.param({"target": "D-1", "body": "あ" * (MAX_BODY_CHARS + 1)}, "body", id="too_long"),
        pytest.param({"body": "本文"}, "target", id="target_missing"),
        pytest.param({"target": "D-1", "body": 1}, "body", id="body_not_string"),
    ],
)
def test_add_submission_when_invalid(
    make_workspace: MakeWorkspace, make_item: MakeItem, data: dict[str, Any], expected_key: str
) -> None:
    """本文・形の誤りは足さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行・検証
    with pytest.raises(SubmissionInvalidError, match=expected_key):
        submissions.add_submission(root, data, now=_fixed_now)
    assert not (root / "submissions.yaml").exists()


def test_add_submission_when_boundary(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """ちょうど上限の本文は足す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    body = " " + "あ" * MAX_BODY_CHARS + " "
    # 実行
    result = submissions.add_submission(root, {"target": "D-1", "body": body}, now=_fixed_now)
    # 検証
    assert len(result.body) == MAX_BODY_CHARS


def test_add_submission_when_target_missing(
    make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """無い項目へは足さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行・検証
    with pytest.raises(ItemNotFoundError, match="D-99"):
        submissions.add_submission(root, {"target": "D-99", "body": "本文"}, now=_fixed_now)


def test_add_submission_when_write_fails(
    monkeypatch: pytest.MonkeyPatch,
    failing_replace: FailingReplace,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """置き換えに失敗したら前の送信を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(root, make_submission("S-1"))
    before = (root / "submissions.yaml").read_bytes()
    monkeypatch.setattr(submissions.os, "replace", failing_replace("submissions.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        submissions.add_submission(root, {"target": "D-1", "body": "本文"}, now=_fixed_now)
    assert (root / "submissions.yaml").read_bytes() == before
    assert list(root.rglob("*.tmp")) == []


def test_list_pending_submissions(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """取り込んでいないものだけを送った順に返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="問い"))
    write_submissions(
        root,
        make_submission("S-1", taken="2026-10-03T00:00:00+00:00"),
        make_submission("S-3"),
        make_submission("S-2"),
    )
    workspace = store.load_workspace(root)
    # 実行
    result = submissions.list_pending_submissions(workspace)
    # 検証
    assert [(pending.id, pending.target_title) for pending in result] == [
        ("S-2", "問い"),
        ("S-3", "問い"),
    ]


def test_list_pending_submissions_when_target_removed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """消えた項目への送信はタイトルを None にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(root, make_submission("S-1", target="D-9"))
    workspace = store.load_workspace(root)
    # 実行
    result = submissions.list_pending_submissions(workspace)
    # 検証
    assert result == [
        submissions.PendingSubmission(
            id="S-1",
            target="D-9",
            target_title=None,
            body="S-1の本文",
            sent="2026-10-01T00:00:00+00:00",
        )
    ]


def test_take_submission(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """取り込んでいない送信に日時を付ける（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    taken_before = "2026-10-03T00:00:00+00:00"
    write_submissions(root, make_submission("S-1", taken=taken_before), make_submission("S-2"))
    # 実行
    result = submissions.take_submission(root, "S-2", now=_fixed_now)
    # 検証
    assert result == (FIXED_NOW, False)
    saved = _read_submissions(root)
    assert saved[1]["taken"] == FIXED_NOW
    assert saved[0]["taken"] == taken_before


def test_take_submission_when_already_taken(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """取り込み済みなら前の日時を返して書かない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(root, make_submission("S-1", taken="2026-10-03T00:00:00+00:00"))
    mtime_before = (root / "submissions.yaml").stat().st_mtime_ns

    def _unexpected_now() -> str:
        """取り込み済みでは今の日時を引かないので、呼ばれたら失敗させる。"""
        raise AssertionError("now は呼ばれないはず")

    # 実行
    result = submissions.take_submission(root, "S-1", now=_unexpected_now)
    # 検証
    assert result == ("2026-10-03T00:00:00+00:00", True)
    assert (root / "submissions.yaml").stat().st_mtime_ns == mtime_before


def test_take_submission_when_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """無い ID は取り込み済みにしない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(root, make_submission("S-1"))
    # 実行・検証
    with pytest.raises(SubmissionNotFoundError, match="S-9"):
        submissions.take_submission(root, "S-9", now=_fixed_now)


def test_take_submission_when_write_fails(
    monkeypatch: pytest.MonkeyPatch,
    failing_replace: FailingReplace,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """置き換えに失敗したら前の送信を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(root, make_submission("S-1"))
    before = (root / "submissions.yaml").read_bytes()
    monkeypatch.setattr(submissions.os, "replace", failing_replace("submissions.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        submissions.take_submission(root, "S-1", now=_fixed_now)
    assert (root / "submissions.yaml").read_bytes() == before
