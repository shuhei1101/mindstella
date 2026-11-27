"""resume.py（MindStella のセッションの再開の状況と注入文）の単体テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2
import pytest
import yaml

import read_point
import resume
from fixture_types import MakeItem, MakeThread, MakeWorkspace, WriteThreads


def _write_last_seq(root: Path, last_seq: int) -> None:
    """ワークスペースの changes.yaml を、まとまり 0 件・まだまとめていない変更なしの last_seq で書く。"""
    path = root / ".mindstella" / "changes.yaml"
    data = {"last_seq": last_seq, "sets": [], "pending": {"added": [], "changed": []}}
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def _status(**changes: Any) -> dict[str, Any]:
    """注入文を描く元の、件数 0 の再開の状況に渡したキーを重ねて返す。"""
    status: dict[str, Any] = {
        "trigger": "resume",
        "awaiting_threads": 0,
        "user_choices": 0,
        "changed": [],
        "changed_more": 0,
        "removed": [],
        "removed_more": 0,
        "needs_review": [],
        "needs_review_more": 0,
        "in_progress": [],
        "in_progress_more": 0,
        "flow": None,
        "migration": None,
        "until_seq": 0,
    }
    status.update(changes)
    return status


def _notes(make_item: MakeItem, count: int) -> list[dict[str, Any]]:
    """N-1 から N-{count} までの、どれも時点 1 より後に足したメモを返す。"""
    return [make_item(f"N-{number}", seq=number + 1, added_seq=number + 1) for number in range(1, count + 1)]


def test_summarize_resume(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    tmp_path: Path,
) -> None:
    """変更・要見直し・進行中・取り込み待ちをまとめ、何も書かない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", status="要見直し", seq=5, added_seq=1),
        make_item("D-2", seq=2, added_seq=2),
        make_item("T-1", status="進行中", seq=4, added_seq=4),
    )
    _write_last_seq(root, 5)
    write_threads(root, make_thread("TH-1"))
    state_root = tmp_path / "state"
    read_point.save_read_seq(root, 3, state_root=state_root)
    # 実行
    result = resume.summarize_resume(root, "compact", state_root=state_root)
    # 検証
    assert result["trigger"] == "resume"
    assert [item["id"] for item in result["changed"]] == ["T-1", "D-1"]
    assert result["needs_review"] == [{"id": "D-1", "title": "D-1の題"}]
    assert result["in_progress"] == [{"id": "T-1", "title": "T-1の題"}]
    assert result["awaiting_threads"] == 1
    assert result["user_choices"] == 0
    assert result["until_seq"] == 5
    assert result["changed_more"] == 0
    assert result["removed_more"] == 0
    assert result["needs_review_more"] == 0
    assert result["in_progress_more"] == 0
    assert read_point.load_read_seq(root, state_root=state_root) == 3


def test_summarize_resume_when_user_choices(
    make_workspace: MakeWorkspace, make_item: MakeItem, tmp_path: Path
) -> None:
    """利用者が案を選んだ検討事項を数え、注入文に件数を入れる（正常系）。"""
    # 準備
    options = [{"key": "A", "content": "案 A"}, {"key": "B", "content": "案 B"}]
    chosen = {"key": "B", "at": "2026-10-01T00:00:00+00:00"}
    root = make_workspace(
        make_item("D-1", options=options, user_choice=chosen),
        make_item("D-2", options=options, user_choice=chosen),
        make_item("D-3", options=options),
    )
    _write_last_seq(root, 0)
    decisions_before = (root / ".mindstella" / "decisions.yaml").read_bytes()
    # 実行
    result = resume.summarize_resume(root, "compact", state_root=tmp_path / "state")
    # 検証
    assert (result["user_choices"], result["awaiting_threads"]) == (2, 0)
    assert "2" in result["context"]
    assert "D-1" not in result["context"]
    assert "D-2" not in result["context"]
    assert (root / ".mindstella" / "decisions.yaml").read_bytes() == decisions_before


def test_summarize_resume_when_no_read_point(
    make_workspace: MakeWorkspace, make_item: MakeItem, tmp_path: Path
) -> None:
    """前回参照した時点が無ければ変更を返さない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", seq=4, added_seq=4))
    _write_last_seq(root, 4)
    # 実行
    result = resume.summarize_resume(root, "startup", state_root=tmp_path / "state")
    # 検証
    assert result["trigger"] == "startup"
    assert result["changed"] == []
    assert result["removed"] == []
    assert result["until_seq"] == 4


def test_summarize_resume_when_over_limit(
    make_workspace: MakeWorkspace, make_item: MakeItem, tmp_path: Path
) -> None:
    """上限を超えた分は件数だけにする（正常系）。"""
    # 準備
    root = make_workspace(*_notes(make_item, 25))
    _write_last_seq(root, 26)
    state_root = tmp_path / "state"
    read_point.save_read_seq(root, 1, state_root=state_root)
    # 実行
    result = resume.summarize_resume(root, "resume", state_root=state_root)
    # 検証
    assert len(result["changed"]) == 20
    assert result["changed_more"] == 5


def test_summarize_resume_when_migrated(make_workspace: MakeWorkspace, tmp_path: Path) -> None:
    """知らせていない移し替えの報告を返し、消さない（正常系）。"""
    # 準備
    root = make_workspace()
    _write_last_seq(root, 0)
    state_root = tmp_path / "state"
    read_point.save_migration_report(
        root,
        {"not_carried": [{"item": "D-1", "key": "attrs", "value": "x"}], "provisional": []},
        state_root=state_root,
    )
    # 実行
    first = resume.summarize_resume(root, "resume", state_root=state_root)
    second = resume.summarize_resume(root, "resume", state_root=state_root)
    # 検証
    assert first["migration"]["not_carried"] == [{"item": "D-1", "key": "attrs", "value": "x"}]
    assert second["migration"]["not_carried"] == [{"item": "D-1", "key": "attrs", "value": "x"}]


def test_render_context() -> None:
    """状況と案内を描く（正常系）。"""
    # 準備
    status = _status(
        trigger="resume",
        awaiting_threads=1,
        changed=[{"id": "D-1", "kind": "decisions", "title": "保存の方式", "updated_by": "user"}],
        needs_review=[{"id": "D-1", "title": "保存の方式"}],
        in_progress=[{"id": "T-1", "title": "画面を作る"}],
        flow={"source": "aituber", "doc": "flow-script"},
    )
    # 実行
    result = resume.render_context(status)
    # 検証
    assert "再開" in result
    assert "1" in result
    assert "D-1" in result
    assert "T-1" in result
    assert "flow-script" in result
    assert "mindstella/startup" in result
    assert "changes_since_read" not in result
    assert "/mindstella:" not in result


def test_render_context_when_overflow_or_migrated() -> None:
    """超えた分と移し替えの報告を描く（正常系）。"""
    # 準備
    status = _status(
        trigger="startup",
        changed=[{"id": "N-1", "kind": "notes", "title": "メモ", "updated_by": "ai"}],
        changed_more=5,
        migration={"not_carried": [{"item": "D-1", "key": "attrs", "value": "社内"}], "provisional": []},
        flow=None,
    )
    # 実行
    result = resume.render_context(status)
    # 検証
    assert "起動" in result
    assert "5" in result
    assert "changes_since_read" in result
    assert "社内" in result
    assert "進め方の文書" not in result


@pytest.mark.parametrize(
    ("count", "expected"), [pytest.param(3, True, id="chosen"), pytest.param(0, False, id="none")]
)
def test_render_context_when_user_choices(count: int, expected: bool) -> None:
    """利用者が案を選んだ検討事項が 1 件以上のときだけ件数を描く（正常系）。"""
    # 準備
    status = _status(user_choices=count)
    # 実行
    result = resume.render_context(status)
    # 検証
    assert ("案を選んだ検討事項" in result) == expected
    if expected:
        assert "3" in result
        assert "user_choices" in result


def test_render_context_when_undefined(tmp_path: Path) -> None:
    """変数が足りなければ描かない（異常系）。"""
    # 準備
    prompt_file = tmp_path / "broken.yaml"
    prompt = {
        "id": "broken",
        "name": "壊れた注入文",
        "description": "vars に無い変数を使う",
        "kind": "hook",
        "lang": "ja",
        "vars": {},
        "parts": [{"id": "body", "texts": [{"lang": "ja", "text": "{{ missing }}"}]}],
    }
    prompt_file.write_text(yaml.safe_dump(prompt, allow_unicode=True), encoding="utf-8")
    # 実行・検証
    with pytest.raises(jinja2.UndefinedError, match="missing"):
        resume.render_context(_status(), prompt_file=prompt_file)

