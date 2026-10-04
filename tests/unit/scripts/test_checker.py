"""checker.py（スキーマ違反・ID の重複・参照切れ・本文のずれの点検）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest

import checker
import store
from fixture_types import MakeItem, MakeSubmission, MakeWorkspace, WriteSubmissions


def _keys(
    problems: list[store.Problem],
) -> set[tuple[str, str, str | None, str | None]]:
    """問題から種類・ファイル・ID・キーの組を取り出し、並びを問わない集まりにする。"""
    return {(problem.kind, problem.file, problem.id, problem.key) for problem in problems}


def test_check_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """整ったワークスペースは問題 0 件（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", body="D-1.md"),
        make_item("D-2", depends_on=["D-1"]),
        bodies={"D-1.md": "本文\n"},
    )
    workspace = store.load_workspace(root)
    # 実行
    problems = checker.check_workspace(workspace)
    # 検証
    assert problems == []


def test_check_workspace_when_problems(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """4 種類の問題をまとめて返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", depends_on=["D-9"]),
        make_item("D-2", status="完了"),
        make_item("R-1", body="R-1.md"),
        bodies={"X-1.md": "どこからも指されない本文\n"},
    )
    workspace = store.load_workspace(root)
    # 実行
    problems = checker.check_workspace(workspace)
    # 検証
    assert _keys(problems) == {
        ("broken_ref", "decisions.yaml", "D-1", "depends_on"),
        ("schema", "decisions.yaml", "D-2", "items[1].status"),
        ("orphan_body", "docs/X-1.md", None, None),
        ("missing_body", "research.yaml", "R-1", "items[0].body"),
    }
    assert [problem.file for problem in problems] == [
        "decisions.yaml",
        "decisions.yaml",
        "docs/X-1.md",
        "research.yaml",
    ]


def test_check_duplicate_ids(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """2 つ目の項目だけを問題にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("D-1", title="重複"))
    workspace = store.load_workspace(root)
    # 実行
    problems = checker._check_duplicate_ids(workspace)
    # 検証
    assert _keys(problems) == {("duplicate_id", "decisions.yaml", "D-1", "items[1].id")}


def test_check_refs_when_missing(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any]
) -> None:
    """存在しない ID を指す参照を拾う（正常系）。"""
    # 準備
    valid_settings["goal"]["deliverables"] = [{"title": "納品物", "doc": "A-9"}]
    root = make_workspace(
        make_item("D-1", depends_on=["D-9"]),
        make_item("T-1", **{"for": ["D-8"]}),
        settings=valid_settings,
    )
    workspace = store.load_workspace(root)
    # 実行
    problems = checker._check_refs(workspace)
    # 検証
    assert len(problems) == 3
    assert {problem.kind for problem in problems} == {"broken_ref"}
    assert {problem.detail for problem in problems} == {
        "存在しない ID: D-9",
        "存在しない ID: D-8",
        "存在しない ID: A-9",
    }


def test_check_refs_when_no_goal(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any]
) -> None:
    """ゴールを持たない設定は納品物の参照を見ない（正常系）。"""
    # 準備
    settings = {key: value for key, value in valid_settings.items() if key != "goal"}
    root = make_workspace(make_item("D-1", depends_on=["D-9"]), settings=settings)
    workspace = store.load_workspace(root)
    # 実行
    problems = checker._check_refs(workspace)
    # 検証
    assert _keys(problems) == {("broken_ref", "decisions.yaml", "D-1", "depends_on")}
    assert "D-9" in problems[0].detail


def test_check_phases(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any]
) -> None:
    """設定の phases に無い項目の phase と goal.phase を拾う（正常系）。"""
    # 準備
    settings = {
        **valid_settings,
        "phases": ["目的", "要件"],
        "goal": {"phase": "結論", "summary": "まとめる", "deliverables": []},
    }
    root = make_workspace(
        make_item("D-1", phase="発散"),
        make_item("D-2", phase="要件"),
        make_item("T-1"),
        settings=settings,
    )
    workspace = store.load_workspace(root)
    # 実行
    problems = checker._check_phases(workspace)
    # 検証
    assert _keys(problems) == {
        ("unknown_phase", "mindmap.yaml", None, "goal.phase"),
        ("unknown_phase", "decisions.yaml", "D-1", "items[0].phase"),
    }
    assert {problem.detail for problem in problems} == {"結論", "発散"}


def test_check_phases_when_no_goal(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any]
) -> None:
    """ゴールを持たない設定は goal.phase を見ない（正常系）。"""
    # 準備
    settings = {
        **{key: value for key, value in valid_settings.items() if key != "goal"},
        "phases": ["目的", "要件"],
    }
    root = make_workspace(make_item("D-1", phase="目的"), settings=settings)
    workspace = store.load_workspace(root)
    # 実行
    problems = checker._check_phases(workspace)
    # 検証
    assert problems == []


def test_check_refs_when_wrong_kind(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """決めた種類でない ID を指す参照を拾う（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", parent="T-1"), make_item("T-1"))
    workspace = store.load_workspace(root)
    # 実行
    problems = checker._check_refs(workspace)
    # 検証
    assert len(problems) == 1
    assert problems[0].kind == "broken_ref"
    assert problems[0].id == "D-1"
    assert problems[0].key == "parent"
    assert "T-1" in problems[0].detail


def test_check_refs_when_related_any_kind(
    make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """related は種類を問わない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", related=["T-1", "G-1"]),
        make_item("T-1"),
        make_item("G-1"),
    )
    workspace = store.load_workspace(root)
    # 実行
    problems = checker._check_refs(workspace)
    # 検証
    assert problems == []


def test_check_bodies(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """本文が無い項目と指されない本文を拾う（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("R-1", body="R-1.md"),
        make_item("D-1", body="D-1.md"),
        bodies={"D-1.md": "本文\n", "X-1.md": "どこからも指されない本文\n"},
    )
    workspace = store.load_workspace(root)
    # 実行
    problems = checker._check_bodies(workspace)
    # 検証
    assert _keys(problems) == {
        ("missing_body", "research.yaml", "R-1", "items[0].body"),
        ("orphan_body", "docs/X-1.md", None, None),
    }


def test_check_submissions(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
) -> None:
    """無い項目への送信を拾い、項目に紐づかない送信は拾わない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    no_target = make_submission("S-3")
    del no_target["target"]
    write_submissions(
        root,
        make_submission("S-1", target="D-8"),
        make_submission("S-2", target="D-1"),
        no_target,
    )
    workspace = store.load_workspace(root)
    # 実行
    problems = checker._check_submissions(workspace)
    # 検証
    assert _keys(problems) == {("broken_ref", "submissions.yaml", "S-1", "target")}
    assert "D-8" in problems[0].detail


def test_check_submissions_when_invalid(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """崩れた送信のファイルは schema にする（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        raw_files={
            "submissions.yaml": (
                "items:\n  - id: S-1\n    target: D-1\n"
                "    sent: 2026-10-01T00:00:00+00:00\n    taken: null\n"
            )
        },
    )
    workspace = store.load_workspace(root)
    # 実行
    problems = checker._check_submissions(workspace)
    # 検証
    assert problems != []
    assert all(
        problem.kind == "schema" and problem.file == "submissions.yaml" for problem in problems
    )


def test_check_submissions_when_missing(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """送信のファイルが無ければ問題 0 件（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    workspace = store.load_workspace(root)
    # 実行
    problems = checker._check_submissions(workspace)
    # 検証
    assert problems == []


@pytest.mark.parametrize(
    ("raw_files", "expected_files"),
    [
        pytest.param(
            {
                "comments.yaml": (
                    "seq: 1\nitems:\n  - id: C-1\n    target: D-1\n"
                    "    created: 2026-10-01T00:00:00+00:00\n"
                )
            },
            {"comments.yaml"},
            id="comments_body_removed",
        ),
        pytest.param({"drafts.yaml": "items: [\n"}, {"drafts.yaml"}, id="drafts_unreadable"),
        pytest.param(
            {
                "comments.yaml": (
                    "seq: 1\nitems:\n  - id: C-1\n    target: D-9\n    body: 本文\n"
                    "    created: '2026-10-01T00:00:00+00:00'\n"
                )
            },
            set(),
            id="target_removed",
        ),
        pytest.param({}, set(), id="no_files"),
    ],
)
def test_check_comments(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    raw_files: dict[str, str],
    expected_files: set[str],
) -> None:
    """崩れたファイルだけを schema にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), raw_files=raw_files)
    workspace = store.load_workspace(root)
    # 実行
    problems = checker._check_comments(workspace)
    # 検証
    assert {problem.file for problem in problems} == expected_files
    assert all(problem.kind == "schema" and problem.id is None for problem in problems)
