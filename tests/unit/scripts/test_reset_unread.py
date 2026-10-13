"""reset_unread.py（SessionStart のフックが呼ぶ、スレッドの書き込みを未読へ戻すスクリプト）の単体テスト。"""

from __future__ import annotations

import fcntl
import functools
import io
import itertools
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

import reset_unread
from fixture_types import MakeItem, MakePost, MakeThread, MakeWorkspace, WriteThreads
from workspace_fixtures import LOCK_FILE_NAME, RECORD_DIR

# 崩れたスレッドのファイル
BROKEN_THREADS = "items: ["


def _read_reads(root: Path) -> list[bool]:
    """ワークスペースの threads.yaml の全ての書き込みの既読を、並びのまま返す。"""
    data = yaml.safe_load((root / RECORD_DIR / "threads.yaml").read_text(encoding="utf-8"))
    return [post["read"] for thread in data["items"] for post in thread["posts"]]


@pytest.mark.parametrize(
    ("cwd_name", "expected"),
    [
        pytest.param("cwd1", ["cwd1"], id="cwd_is_workspace"),
        pytest.param("cwd2", ["cwd2/a", "cwd2/b"], id="children_only"),
        pytest.param("cwd3", [], id="two_levels_down"),
        pytest.param("missing", [], id="missing_cwd"),
    ],
)
def test_find_workspaces(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    cwd_name: str,
    expected: list[str],
) -> None:
    """作業フォルダと直下だけを探す（正常系）。"""
    # 準備
    make_workspace(make_item("D-1"), name="cwd1")
    make_workspace(make_item("D-1"), name="cwd2/b")
    make_workspace(make_item("D-1"), name="cwd2/a")
    (tmp_path / "cwd2" / "c").mkdir()
    make_workspace(make_item("D-1"), name="cwd3/x/y")
    # 実行
    result = reset_unread.find_workspaces(tmp_path / cwd_name)
    # 検証
    assert [path.relative_to(tmp_path).as_posix() for path in result] == expected


def test_reset_workspace(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """既読を未読に戻す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(
        root,
        make_thread("TH-1", make_post("TH-1-1", read=True), make_post("TH-1-2", author="ai")),
    )
    # 実行
    reason = reset_unread.reset_workspace(root)
    # 検証
    assert reason is None
    assert _read_reads(root) == [False, False]


def test_reset_workspace_when_locked(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """ロックを取れなければ上限で飛ばす（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1", make_post("TH-1-1", read=True)))
    before = (root / RECORD_DIR / "threads.yaml").read_bytes()
    # 呼ぶたびに 1 秒進む時計
    clock = functools.partial(next, itertools.count())
    # 別のファイル記述子で排他ロックを持ったまま呼ぶ
    with (root / RECORD_DIR / LOCK_FILE_NAME).open("a", encoding="utf-8") as holder:
        fcntl.flock(holder, fcntl.LOCK_EX)
        # 実行
        reason = reset_unread.reset_workspace(root, sleep=lambda _sec: None, clock=clock)
    # 検証
    assert reason is not None
    assert reason.startswith("ロックを取れませんでした")
    assert (root / RECORD_DIR / "threads.yaml").read_bytes() == before


def test_reset_workspace_when_invalid(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """崩れたスレッドのファイルは飛ばして理由を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), raw_files={"threads.yaml": BROKEN_THREADS})
    # 実行
    reason = reset_unread.reset_workspace(root)
    # 検証
    assert reason is not None
    assert "threads.yaml: " in reason
    assert (root / RECORD_DIR / "threads.yaml").read_text(encoding="utf-8") == BROKEN_THREADS
    # ロックが外れている（別の記述子から取り直せる）
    with (root / RECORD_DIR / LOCK_FILE_NAME).open("a", encoding="utf-8") as probe:
        fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_main(
    capsys: pytest.CaptureFixture[str],
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """作業フォルダのワークスペースを戻し、何も出さない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    write_threads(root, make_thread("TH-1", make_post("TH-1-1", read=True)))
    stdin = io.StringIO(json.dumps({"cwd": str(root), "source": "resume"}))
    stderr = io.StringIO()
    # 実行
    code = reset_unread.main(stdin=stdin, stderr=stderr)
    # 検証
    assert code == 0
    assert _read_reads(root) == [False]
    assert capsys.readouterr().out == ""
    assert stderr.getvalue() == ""


@pytest.mark.parametrize(
    ("stdin_text", "expected_stderr_lines"),
    [
        pytest.param('{"cwd": "CWD"}', 0, id="no_workspace"),
        pytest.param("not json", 1, id="not_json"),
        pytest.param("{}", 1, id="no_cwd"),
    ],
)
def test_main_when_nothing_to_do(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    stdin_text: str,
    expected_stderr_lines: int,
) -> None:
    """ワークスペースが無い・入力が読めないときも 0 で終える（正常系）。"""
    # 準備
    stdin = io.StringIO(stdin_text.replace("CWD", str(tmp_path)))
    stderr = io.StringIO()
    # 実行
    code = reset_unread.main(stdin=stdin, stderr=stderr)
    # 検証
    assert code == 0
    assert capsys.readouterr().out == ""
    assert len(stderr.getvalue().splitlines()) == expected_stderr_lines


def test_main_when_one_fails(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """戻せないワークスペースを飛ばして次を戻す（正常系）。"""
    # 準備
    broken = make_workspace(
        make_item("D-1"), name="cwd/a", raw_files={"threads.yaml": BROKEN_THREADS}
    )
    healthy = make_workspace(make_item("D-1"), name="cwd/b")
    write_threads(healthy, make_thread("TH-1", make_post("TH-1-1", read=True)))
    payload: dict[str, Any] = {"cwd": str(tmp_path / "cwd")}
    stdin = io.StringIO(json.dumps(payload))
    stderr = io.StringIO()
    # 実行
    code = reset_unread.main(stdin=stdin, stderr=stderr)
    # 検証
    assert code == 0
    assert _read_reads(healthy) == [False]
    lines = stderr.getvalue().splitlines()
    assert len(lines) == 1
    assert str(broken) in lines[0]
    assert capsys.readouterr().out == ""
