"""submissions.py（コメントの送信の読み書き）の単体テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

import comments
import locations
import store
import submissions
from errors import SchemaMismatchError, SubmissionNotFoundError, WriteFailedError
from fixture_types import FailingReplace, MakeItem, MakeSubmission, MakeWorkspace, WriteSubmissions
from workspace_fixtures import RECORD_DIR

# now の代わりに返す日時
FIXED_NOW = "2026-10-04T03:00:00+00:00"

# 本文の 2 行目を指す箇所（資料 A-1 の本文 `A_BODY` の 2 行目）
LINE2_LOC = {"kind": "body", "start": 2, "end": 2, "text": "言い換えたい文"}

# 資料 A-1 の本文
A_BODY = "1 行目\n言い換えたい文\n3 行目"


def _fixed_now() -> str:
    """今の日時の代わりに、決めた日時を返す。"""
    return FIXED_NOW


def _read_submissions(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの submissions.yaml を読んで、送信の並びを返す。"""
    data = yaml.safe_load((root / RECORD_DIR / "submissions.yaml").read_text(encoding="utf-8"))
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


def test_load_submissions_when_previous_version(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """loc・comment を持たない前の版の送信も読む（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(root, make_submission("S-1"))
    # 実行
    result = submissions.load_submissions(root)
    # 検証
    assert (result[0].loc, result[0].comment) == (None, None)


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
            loc=None,
        )
    ]


def test_list_pending_submissions_when_location_and_no_target(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """箇所を持つ送信と項目に紐づかない送信を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1"), bodies={"A-1.md": A_BODY})
    no_target = make_submission("S-2")
    del no_target["target"]
    write_submissions(root, make_submission("S-1", target="A-1", loc=LINE2_LOC), no_target)
    workspace = store.load_workspace(root)
    # 実行
    result = submissions.list_pending_submissions(workspace)
    # 検証
    assert result[0].loc == LINE2_LOC
    assert (result[1].target, result[1].target_title, result[1].loc) == (None, None, None)


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
    mtime_before = (root / RECORD_DIR / "submissions.yaml").stat().st_mtime_ns

    def _unexpected_now() -> str:
        """取り込み済みでは今の日時を引かないので、呼ばれたら失敗させる。"""
        raise AssertionError("now は呼ばれないはず")

    # 実行
    result = submissions.take_submission(root, "S-1", now=_unexpected_now)
    # 検証
    assert result == ("2026-10-03T00:00:00+00:00", True)
    assert (root / RECORD_DIR / "submissions.yaml").stat().st_mtime_ns == mtime_before


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
    before = (root / RECORD_DIR / "submissions.yaml").read_bytes()
    monkeypatch.setattr(submissions.os, "replace", failing_replace("submissions.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        submissions.take_submission(root, "S-1", now=_fixed_now)
    assert (root / RECORD_DIR / "submissions.yaml").read_bytes() == before


def _review_comment(
    comment_id: str, *, target: str | None, loc: dict[str, Any] | None = None
) -> comments.ReviewComment:
    """送るレビュー中のコメントを作る。"""
    return comments.ReviewComment(
        id=comment_id,
        target=target,
        loc=None if loc is None else locations.parse_location(loc),
        body=f"{comment_id}の本文",
        created="2026-10-01T00:00:00+00:00",
    )


def test_append_submissions(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """連番を振って並びの順に末尾へ足す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("A-1"), bodies={"A-1.md": A_BODY})
    write_submissions(root, make_submission("S-1"), make_submission("S-3"))
    pending = [
        _review_comment("C-1", target="D-1"),
        _review_comment("C-2", target="A-1", loc=LINE2_LOC),
        _review_comment("C-3", target=None),
    ]
    # 実行
    result = submissions.append_submissions(root, pending, now=_fixed_now)
    # 検証
    assert [(sent.id, sent.comment) for sent in result] == [
        ("S-4", "C-1"),
        ("S-5", "C-2"),
        ("S-6", "C-3"),
    ]
    assert _read_submissions(root)[2:] == [
        {
            "id": "S-4",
            "target": "D-1",
            "body": "C-1の本文",
            "sent": FIXED_NOW,
            "taken": None,
            "comment": "C-1",
        },
        {
            "id": "S-5",
            "target": "A-1",
            "loc": LINE2_LOC,
            "body": "C-2の本文",
            "sent": FIXED_NOW,
            "taken": None,
            "comment": "C-2",
        },
        {
            "id": "S-6",
            "body": "C-3の本文",
            "sent": FIXED_NOW,
            "taken": None,
            "comment": "C-3",
        },
    ]


def test_append_submissions_when_first(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """ファイルが無ければ作って S-1（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = submissions.append_submissions(
        root, [_review_comment("C-1", target="D-1")], now=_fixed_now
    )
    # 検証
    assert [sent.id for sent in result] == ["S-1"]
    assert (root / RECORD_DIR / "submissions.yaml").is_file()


def test_append_submissions_when_already_sent(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """既に送ったコメントは足さずにその送信を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_submissions(root, make_submission("S-1", comment="C-1"))
    pending = [_review_comment("C-1", target="D-1"), _review_comment("C-2", target="D-1")]
    # 実行
    result = submissions.append_submissions(root, pending, now=_fixed_now)
    # 検証
    assert [sent.id for sent in result] == ["S-1", "S-2"]
    assert len(_read_submissions(root)) == 2


def test_append_submissions_when_write_fails(
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
    before = (root / RECORD_DIR / "submissions.yaml").read_bytes()
    monkeypatch.setattr(submissions.os, "replace", failing_replace("submissions.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        submissions.append_submissions(root, [_review_comment("C-1", target="D-1")], now=_fixed_now)
    assert (root / RECORD_DIR / "submissions.yaml").read_bytes() == before
    assert list(root.rglob("*.tmp")) == []
