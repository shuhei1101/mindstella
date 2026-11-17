"""change_detection.py（記録のファイルの書き換えの検知と履歴への記録）の単体テスト。"""

from __future__ import annotations

import logging
import subprocess
import threading
from pathlib import Path
from typing import Any

import pytest
import yaml

import change_detection
from change_detection import ChangeDetector, ItemDiff, Snapshot, Writer
from claude_input import InputTarget, InputTargets
from fixture_types import MakeItem, MakeWorkspace
from state import SessionState, update_session
from workspace_fixtures import RECORD_DIR, write_yaml
from workspaces import workspace_id_for

# 記録した日時
NOW = "2026-11-15T08:00:00+00:00"

# 時計の始まり（秒）と、外部の変更をまとめるまでの秒数を過ぎた時刻
CLOCK_START = 1000.0
CLOCK_AFTER_DELAY = 1060.0

# 重なった ID の貼り付ける文の始まり
DUPLICATE_PREFIX = "[mindstella] 同じ ID の項目が 2 件あります: D-1（decisions.yaml）"

# 貼り付けの宛先
TARGET = InputTarget(
    socket="/tmp/tmux-1000/default",
    pane="%1",
    config_dir=Path("/home/u/.claude"),
    cwd=Path("/w"),
    claude_pid=4321,
    claude_started_at="100",
)


class _IdleThread:
    """start を呼んでも何もしないスレッドの代わり（poll はテストから呼ぶ）。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """渡した引数は使わない。"""

    def start(self) -> None:
        """何もしない。"""

    def join(self, timeout: float | None = None) -> None:
        """何もしない。"""


class _FixedTargets(InputTargets):
    """どのワークスペースにも同じ宛先を返す台帳。"""

    def __init__(self, target: InputTarget | None) -> None:
        """返す宛先を持つ。"""
        super().__init__()
        self._fixed = target

    def target_of(self, root: Path) -> InputTarget | str | None:
        """持っている宛先を返す。"""
        return self._fixed


def _records(root: Path) -> Path:
    """記録のフォルダを返す。"""
    return root / RECORD_DIR


def _read(root: Path, name: str) -> Any:
    """記録のフォルダの YAML を読む。無ければ None。"""
    path = _records(root) / name
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None


def _snapshot_dir(state_dir: Path, root: Path) -> Path:
    """そのワークスペースの前回の中身のフォルダを返す。"""
    return state_dir / "workspaces" / workspace_id_for(root) / "snapshot"


def _started(
    root: Path, state_dir: Path, monkeypatch: pytest.MonkeyPatch, targets: InputTargets | None = None
) -> ChangeDetector:
    """スレッドを立てずに始めた変更の検知を返す。"""
    monkeypatch.setattr(change_detection.threading, "Thread", _IdleThread)
    detector = ChangeDetector(root, state_dir, threading.Lock(), targets or InputTargets())
    detector.start()
    return detector


def _write_items(root: Path, name: str, *items: dict[str, Any]) -> None:
    """種類の YAML を渡した項目で書き換える。"""
    write_yaml(_records(root) / name, {"items": list(items)})


def _snapshot(files: dict[str, str]) -> Snapshot:
    """Git の作業ツリーでない中身を作る。"""
    return Snapshot(files=files, git_head=None, git_ref=None)


def _place(root: Path, names: tuple[str, ...]) -> None:
    """ワークスペースの直下からのパスに空のファイルを置く。"""
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")


def _write_session(state_dir: Path, root: Path, session: SessionState | None) -> None:
    """そのワークスペースの session.json を置く（None なら置かない）。"""
    if session is not None:
        update_session(state_dir, workspace_id_for(root), lambda _: session)


def _not_work_tree(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """Git の作業ツリーでないときの git の結果を返す。"""
    return subprocess.CompletedProcess(args=args, returncode=128, stdout="", stderr="not a git repository")


def test_start_when_no_snapshot(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """snapshot が無ければ今の中身で作り、記録しない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    state_dir = tmp_path / "state"
    history_before = _read(root, "history.yaml")
    # 実行
    _started(root, state_dir, monkeypatch)
    # 検証
    assert (_snapshot_dir(state_dir, root) / "decisions.yaml").read_text(encoding="utf-8") == (
        _records(root) / "decisions.yaml"
    ).read_text(encoding="utf-8")
    assert _read(root, "history.yaml") == history_before
    assert _read(root, "changes.yaml") is None


def test_start_when_changed_while_stopped(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """snapshot と違えば外部の変更として記録する（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", answer="今の答え"))
    state_dir = tmp_path / "state"
    snapshot_dir = _snapshot_dir(state_dir, root)
    snapshot_dir.mkdir(parents=True)
    write_yaml(snapshot_dir / "decisions.yaml", {"items": [make_item("D-1", answer="前の答え")]})
    # 実行
    _started(root, state_dir, monkeypatch)
    # 検証
    assert _read(root, "history.yaml")["items"]["D-1"]["history"][0]["by"] == "external"


def test_poll_when_external(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MindStella のセッションが応答の途中でなければ外部の変更として記録し、時間が過ぎたらまとめる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    clock = [CLOCK_START]
    monkeypatch.setattr(change_detection.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(change_detection, "classify_writer", lambda *args, **kwargs: Writer.EXTERNAL)
    detector = _started(root, tmp_path / "state", monkeypatch)
    _write_items(root, "decisions.yaml", make_item("D-1", answer="ほかで書いた答え"))
    edited = (_records(root) / "decisions.yaml").read_text(encoding="utf-8")
    # 実行
    detector.poll()
    first_history = _read(root, "history.yaml")
    first_changes = _read(root, "changes.yaml")
    clock[0] = CLOCK_AFTER_DELAY
    detector.poll()
    # 検証
    assert first_history["items"]["D-1"]["updated_by"] == "external"
    assert first_changes["pending"]["by"] == "external"
    changes = _read(root, "changes.yaml")
    assert changes["sets"][0]["by"] == "external"
    assert changes["sets"][0]["summary"] == "ほかのセッションの書き込み"
    assert changes["pending"] == {"added": [], "changed": []}
    assert (_records(root) / "decisions.yaml").read_text(encoding="utf-8") == edited


def test_poll_when_session(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """応答の途中の書き換えは ai の変更としてまとめない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    clock = [CLOCK_START]
    monkeypatch.setattr(change_detection.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(change_detection, "classify_writer", lambda *args, **kwargs: Writer.AI)
    detector = _started(root, tmp_path / "state", monkeypatch)
    _write_items(root, "decisions.yaml", make_item("D-1", answer="応答の途中の答え"))
    # 実行
    detector.poll()
    clock[0] = CLOCK_AFTER_DELAY
    detector.poll()
    # 検証
    assert _read(root, "history.yaml")["items"]["D-1"]["updated_by"] == "ai"
    changes = _read(root, "changes.yaml")
    assert changes["pending"]["by"] == "ai"
    assert changes["sets"] == []


def test_poll_when_git(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Git の操作は記録せず前回の中身だけ置き換える（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    state_dir = tmp_path / "state"
    monkeypatch.setattr(change_detection, "classify_writer", lambda *args, **kwargs: Writer.GIT)
    detector = _started(root, state_dir, monkeypatch)
    history_before = _read(root, "history.yaml")
    _write_items(root, "decisions.yaml", make_item("D-1", answer="切り替えたブランチの答え"))
    # 実行
    detector.poll()
    # 検証
    assert _read(root, "history.yaml") == history_before
    assert _read(root, "changes.yaml") is None
    assert (_snapshot_dir(state_dir, root) / "decisions.yaml").read_text(encoding="utf-8") == (
        _records(root) / "decisions.yaml"
    ).read_text(encoding="utf-8")


def test_poll_when_unreadable(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """読めない種類の YAML は飛ばし、ログを 1 回だけ残す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    detector = _started(root, tmp_path / "state", monkeypatch)
    history_before = _read(root, "history.yaml")
    caplog.set_level(logging.WARNING)
    # 実行
    (_records(root) / "decisions.yaml").write_text("items: [\n", encoding="utf-8")
    detector.poll()
    (_records(root) / "decisions.yaml").write_text("items: [{\n", encoding="utf-8")
    detector.poll()
    # 検証
    assert _read(root, "history.yaml") == history_before
    assert _read(root, "changes.yaml") is None
    assert caplog.text.count("unreadable: decisions.yaml") == 1


def test_poll_when_duplicate(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """重なった ID の集まりが変わったときだけ貼り付ける（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    pasted: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        change_detection,
        "paste_duplicates",
        lambda root, duplicates, targets: pasted.append(duplicates),
    )
    detector = _started(root, tmp_path / "state", monkeypatch)
    # 実行
    _write_items(root, "decisions.yaml", make_item("D-1"), make_item("D-1", title="同じ ID の検討事項"))
    detector.poll()
    _write_items(
        root, "decisions.yaml", make_item("D-1"), make_item("D-1", title="同じ ID の検討事項を直した")
    )
    detector.poll()
    # 検証
    assert pasted == [("D-1",)]
    assert detector.duplicate_ids() == ("D-1",)


def test_accept_own_write(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """受け取った後の poll は自分の書き込みを記録せず、間に書かれたほかのファイルは記録する（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("N-1"))
    detector = _started(root, tmp_path / "state", monkeypatch)
    _write_items(root, "notes.yaml", make_item("N-1", content="ほかで書いたメモ"))
    _write_items(
        root, "decisions.yaml", make_item("D-1", options=[{"key": "A", "content": "書き換えた案"}])
    )
    written = (_records(root) / "decisions.yaml").read_text(encoding="utf-8")
    # 実行
    detector.accept_own_write({"decisions.yaml": written})
    detector.poll()
    # 検証
    rows = _read(root, "history.yaml")["items"]
    assert "history" not in rows["D-1"]
    assert len(rows["N-1"]["history"]) == 1


def test_take_snapshot(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """種類の YAML と本文を読み、読めないファイルは前回の中身で埋める（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", body="docs/D-1.md"),
        bodies={"D-1.md": "本文\n"},
        raw_files={"notes.yaml": "items: [\n"},
    )
    previous = _snapshot({"notes.yaml": "items: []\n"})
    # 実行
    snapshot, unreadable = change_detection.take_snapshot(root, previous=previous, run=_not_work_tree)
    # 検証
    assert sorted(snapshot.files) == ["decisions.yaml", "docs/D-1.md", "notes.yaml"]
    assert snapshot.files["notes.yaml"] == "items: []\n"
    assert snapshot.files["docs/D-1.md"] == "本文\n"
    assert unreadable == ["notes.yaml"]
    assert snapshot.git_head is None


def test_diff_snapshots(make_item: MakeItem) -> None:
    """追加・変更・削除と、本文だけの変更を見分ける（正常系）。"""
    # 準備
    d1_before = make_item("D-1", answer="前の答え")
    d1_after = make_item("D-1", answer="今の答え")
    d2 = make_item("D-2", body="docs/D-2.md")
    d3 = make_item("D-3")
    d4 = make_item("D-4")
    before = _snapshot(
        {
            "decisions.yaml": yaml.safe_dump({"items": [d1_before, d2, d3]}, allow_unicode=True),
            "docs/D-2.md": "前の本文\n",
        }
    )
    after = _snapshot(
        {
            "decisions.yaml": yaml.safe_dump({"items": [d1_after, d2, d4]}, allow_unicode=True),
            "docs/D-2.md": "今の本文\n",
        }
    )
    # 実行
    diff = change_detection.diff_snapshots(before, after)
    # 検証
    assert diff == ItemDiff(
        added=[("decision", d4)],
        changed=[
            ("decision", d1_before, d1_after, None, None),
            ("decision", d2, d2, "前の本文\n", "今の本文\n"),
        ],
        removed=[("decision", d3)],
    )


def test_diff_snapshots_when_same(make_item: MakeItem) -> None:
    """同じ中身なら違いが無い（正常系）。"""
    # 準備
    text = yaml.safe_dump({"items": [make_item("D-1")]}, allow_unicode=True)
    # 実行
    diff = change_detection.diff_snapshots(
        _snapshot({"decisions.yaml": text}), _snapshot({"decisions.yaml": text})
    )
    # 検証
    assert diff == ItemDiff(added=[], changed=[], removed=[])


@pytest.mark.parametrize(
    ("after_head", "git_files", "session", "alive", "expected"),
    [
        pytest.param("b" * 40, (), None, False, Writer.GIT, id="head_changed"),
        pytest.param("a" * 40, (".git/MERGE_HEAD",), None, False, Writer.GIT, id="merge_head"),
        pytest.param(
            "a" * 40,
            (),
            SessionState(session="s", status="running", started_at=NOW, responding=True),
            True,
            Writer.AI,
            id="responding_alive",
        ),
        pytest.param(
            "a" * 40,
            (),
            SessionState(session="s", status="running", started_at=NOW, responding=True),
            False,
            Writer.EXTERNAL,
            id="responding_dead",
        ),
        pytest.param("a" * 40, (), None, True, Writer.EXTERNAL, id="no_session"),
    ],
)
def test_classify_writer(
    tmp_path: Path,
    after_head: str,
    git_files: tuple[str, ...],
    session: SessionState | None,
    alive: bool,
    expected: Writer,
) -> None:
    """Git の操作・応答の途中・それ以外を見分ける（正常系）。"""
    # 準備
    root = tmp_path / "ws"
    root.mkdir()
    state_dir = tmp_path / "state"
    _place(root, git_files)
    _write_session(state_dir, root, session)
    before = Snapshot(files={}, git_head="a" * 40, git_ref="refs/heads/main")
    after = Snapshot(files={}, git_head=after_head, git_ref="refs/heads/main")
    # 実行
    writer = change_detection.classify_writer(before, after, root, state_dir, alive=lambda _: alive)
    # 検証
    assert writer == expected


@pytest.mark.parametrize(
    ("returncode", "started_at", "expected"),
    [
        pytest.param(0, "100", True, id="alive"),
        pytest.param(1, "100", False, id="no_pane"),
        pytest.param(0, "200", False, id="restarted"),
    ],
)
def test_session_alive(
    monkeypatch: pytest.MonkeyPatch, returncode: int, started_at: str, expected: bool
) -> None:
    """ペインとプロセスの有無を見分ける（正常系）。"""
    # 準備
    session = {"pane": "%1", "socket": "/tmp/tmux-1000/default", "pid": 4321, "pid_started_at": "100"}
    monkeypatch.setattr(change_detection, "process_started_at", lambda pid, *args, **kwargs: started_at)

    def run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        """tmux の結果を返す。"""
        return subprocess.CompletedProcess(args=args, returncode=returncode, stdout="%1\n", stderr="")

    # 実行
    result = change_detection.session_alive(session, run=run)
    # 検証
    assert result is expected


def test_record_diff(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """追加・変更・削除をそれぞれ記録する（正常系）。"""
    # 準備
    d1_before = make_item("D-1", answer="前の答え")
    root = make_workspace(
        d1_before,
        make_item("D-2", title="消した検討事項"),
        raw_files={"changes.yaml": "last_seq: 3\nsets: []\npending: {added: [], changed: []}\n"},
    )
    diff = ItemDiff(
        added=[("decision", make_item("D-4"))],
        changed=[("decision", d1_before, make_item("D-1", answer="今の答え"), None, None)],
        removed=[("decision", make_item("D-2", title="消した検討事項"))],
    )
    # 実行
    change_detection.record_diff(root, diff, "external", now=lambda: NOW)
    # 検証
    rows = _read(root, "history.yaml")["items"]
    assert rows["D-4"]["added_seq"] == 4
    assert rows["D-1"]["history"][0]["by"] == "external"
    assert rows["D-1"]["history"][0]["before"] == {"answer": "前の答え"}
    assert "D-2" not in rows
    assert _read(root, "changes.yaml")["pending"] == {
        "added": ["D-4"],
        "changed": ["D-1"],
        "removed": [
            {"id": "D-2", "kind": "decision", "title": "消した検討事項", "seq": 6, "added_seq": 0}
        ],
        "by": "external",
    }


def test_record_diff_when_writer_differs(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """書いた元が違う変更が入っていれば先にまとめる（正常系）。"""
    # 準備
    d1_before = make_item("D-1", answer="前の答え")
    root = make_workspace(
        d1_before,
        make_item("D-3"),
        raw_files={
            "changes.yaml": "last_seq: 3\nsets: []\npending: {added: [], changed: [D-3], by: ai}\n"
        },
    )
    diff = ItemDiff(
        added=[],
        changed=[("decision", d1_before, make_item("D-1", answer="今の答え"), None, None)],
        removed=[],
    )
    # 実行
    change_detection.record_diff(root, diff, "external", now=lambda: NOW)
    # 検証
    changes = _read(root, "changes.yaml")
    assert changes["sets"][0]["summary"] == "まとめる前の AI の書き換え"
    assert changes["sets"][0]["changed"] == ["D-3"]
    assert changes["pending"] == {"added": [], "changed": ["D-1"], "by": "external"}


def test_find_duplicate_ids(make_item: MakeItem) -> None:
    """種類をまたいでも数える（正常系）。"""
    # 準備
    snapshot = _snapshot(
        {
            "decisions.yaml": yaml.safe_dump(
                {"items": [make_item("D-1"), make_item("D-1", title="同じ ID")]}, allow_unicode=True
            ),
            "notes.yaml": yaml.safe_dump({"items": [make_item("N-1")]}, allow_unicode=True),
        }
    )
    # 実行
    duplicates = change_detection.find_duplicate_ids(snapshot)
    # 検証
    assert duplicates == ("D-1",)


@pytest.mark.parametrize(
    ("target", "expected_count"),
    [
        pytest.param(TARGET, 1, id="with_target"),
        pytest.param(None, 0, id="without_target"),
    ],
)
def test_paste_duplicates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: InputTarget | None, expected_count: int
) -> None:
    """宛先があれば 1 回貼り、無ければ貼らない（正常系）。"""
    # 準備
    texts: list[str] = []
    monkeypatch.setattr(
        change_detection,
        "paste_to_pane",
        lambda target, text, **kwargs: texts.append(text),
    )
    # 実行
    change_detection.paste_duplicates(tmp_path, ("D-1",), _FixedTargets(target))
    # 検証
    assert len(texts) == expected_count
    assert all(text.startswith(DUPLICATE_PREFIX) for text in texts)
