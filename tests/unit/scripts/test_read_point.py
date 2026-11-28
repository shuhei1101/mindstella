"""read_point.py（前回参照した時点と移し替えの報告の読み書き）の単体テスト。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

import read_point
import state
import workspaces
from errors import ArgumentError, SchemaMismatchError, WriteFailedError
from fixture_types import MakeWorkspace


def _write_last_seq(root: Path, last_seq: int) -> None:
    """ワークスペースの changes.yaml を、まとまり 0 件・まだまとめていない変更なしの last_seq で書く。"""
    path = root / ".mindstella" / "changes.yaml"
    data = {"last_seq": last_seq, "sets": [], "pending": {"added": [], "changed": []}}
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def _read_point_path(root: Path, state_root: Path) -> Path:
    """ワークスペースの read_point.json の場所を返す。"""
    return state.workspace_dir(state_root, workspaces.workspace_id_of(root)) / read_point.READ_POINT_FILE


def test_load_read_seq(make_workspace: MakeWorkspace, tmp_path: Path) -> None:
    """書いた時点を読む（正常系）。"""
    # 準備
    root = make_workspace()
    state_root = tmp_path / "state"
    read_point.save_read_seq(root, 5, state_root=state_root)
    # 実行
    result = read_point.load_read_seq(root, state_root=state_root)
    # 検証
    assert result == 5


def test_load_read_seq_when_missing(make_workspace: MakeWorkspace, tmp_path: Path) -> None:
    """無ければ None（正常系）。"""
    # 準備
    root = make_workspace()
    # 実行
    result = read_point.load_read_seq(root, state_root=tmp_path / "state")
    # 検証
    assert result is None


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("{", id="not_json"),
        pytest.param('{"read_seq": -1}', id="negative"),
        pytest.param('{"read_seq": "3"}', id="string"),
    ],
)
def test_load_read_seq_when_broken(make_workspace: MakeWorkspace, tmp_path: Path, text: str) -> None:
    """壊れたファイルは読まない（異常系）。"""
    # 準備
    root = make_workspace()
    state_root = tmp_path / "state"
    path = _read_point_path(root, state_root)
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")
    # 実行・検証
    with pytest.raises(SchemaMismatchError, match="スキーマに合いません") as raised:
        read_point.load_read_seq(root, state_root=state_root)
    assert any(line.startswith("read_point.json: read_seq") for line in raised.value.lines)


def test_save_read_seq_when_write_fails(
    make_workspace: MakeWorkspace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """書けなければ前の時点を残す（異常系）。"""
    # 準備
    root = make_workspace()
    state_root = tmp_path / "state"
    read_point.save_read_seq(root, 3, state_root=state_root)

    def _failing_replace(*args: object, **kwargs: object) -> None:
        """置き換えを OSError で失敗させる。"""
        raise OSError("置き換えられない")

    monkeypatch.setattr(os, "replace", _failing_replace)
    # 実行・検証
    with pytest.raises(WriteFailedError):
        read_point.save_read_seq(root, 7, state_root=state_root)
    monkeypatch.undo()
    assert read_point.load_read_seq(root, state_root=state_root) == 3
    assert sorted(path.name for path in _read_point_path(root, state_root).parent.iterdir()) == [
        "read_point.json"
    ]


def test_advance_read_seq(make_workspace: MakeWorkspace, tmp_path: Path) -> None:
    """時点を進め、移し替えの報告を消す（正常系）。"""
    # 準備
    root = make_workspace()
    state_root = tmp_path / "state"
    _write_last_seq(root, 5)
    read_point.save_read_seq(root, 3, state_root=state_root)
    read_point.save_migration_report(
        root, {"not_carried": [{"item": "D-1", "key": "attrs", "value": "x"}], "provisional": []}, state_root=state_root
    )
    # 実行
    result = read_point.advance_read_seq(root, 5, state_root=state_root)
    # 検証
    assert result == 5
    assert read_point.load_read_seq(root, state_root=state_root) == 5
    assert read_point.load_migration_report(root, state_root=state_root) is None


def test_advance_read_seq_when_already_ahead(make_workspace: MakeWorkspace, tmp_path: Path) -> None:
    """今の時点を戻さない（正常系）。"""
    # 準備
    root = make_workspace()
    state_root = tmp_path / "state"
    _write_last_seq(root, 5)
    read_point.save_read_seq(root, 5, state_root=state_root)
    # 実行
    result = read_point.advance_read_seq(root, 3, state_root=state_root)
    # 検証
    assert result == 5
    assert read_point.load_read_seq(root, state_root=state_root) == 5


@pytest.mark.parametrize(
    "until_seq",
    [
        pytest.param(-1, id="negative"),
        pytest.param(9, id="beyond_last_seq"),
    ],
)
def test_advance_read_seq_when_out_of_range(
    make_workspace: MakeWorkspace, tmp_path: Path, until_seq: int
) -> None:
    """通し番号の外は書かない（異常系）。"""
    # 準備
    root = make_workspace()
    state_root = tmp_path / "state"
    _write_last_seq(root, 5)
    read_point.save_read_seq(root, 3, state_root=state_root)
    # 実行・検証
    with pytest.raises(ArgumentError, match="引数の誤り: until_seq"):
        read_point.advance_read_seq(root, until_seq, state_root=state_root)
    assert read_point.load_read_seq(root, state_root=state_root) == 3


def test_save_migration_report_appends(make_workspace: MakeWorkspace, tmp_path: Path) -> None:
    """知らせていない報告に足す（正常系）。"""
    # 準備
    root = make_workspace()
    state_root = tmp_path / "state"
    first = {"not_carried": [{"item": "D-1", "key": "attrs", "value": "a"}], "provisional": []}
    second = {
        "not_carried": [{"item": "R-1", "key": "angles", "value": "b"}],
        "provisional": [{"file": ".mindstella/config.yaml", "key": "summary", "value": "workspace"}],
    }
    read_point.save_migration_report(root, first, state_root=state_root)
    # 実行
    read_point.save_migration_report(root, second, state_root=state_root)
    # 検証
    assert read_point.load_migration_report(root, state_root=state_root) == {
        "not_carried": [
            {"item": "D-1", "key": "attrs", "value": "a"},
            {"item": "R-1", "key": "angles", "value": "b"},
        ],
        "provisional": [{"file": ".mindstella/config.yaml", "key": "summary", "value": "workspace"}],
    }


def _turn_point_path(root: Path, state_root: Path) -> Path:
    """ワークスペースの turn_point.json の場所を返す。"""
    return state.workspace_dir(state_root, workspaces.workspace_id_of(root)) / "turn_point.json"


def test_load_turn_point(make_workspace: MakeWorkspace, tmp_path: Path) -> None:
    """書いた始まりを読む（正常系）。"""
    # 準備
    root = make_workspace()
    state_root = tmp_path / "state"
    read_point.save_turn_point(root, 4, "2026-11-28T05:50:00+00:00", state_root=state_root)
    # 実行
    result = read_point.load_turn_point(root, state_root=state_root)
    # 検証
    assert result == (4, "2026-11-28T05:50:00+00:00")


def test_load_turn_point_when_missing(make_workspace: MakeWorkspace, tmp_path: Path) -> None:
    """無ければ 0 と None（正常系）。"""
    # 準備
    root = make_workspace()
    # 実行
    result = read_point.load_turn_point(root, state_root=tmp_path / "state")
    # 検証
    assert result == (0, None)


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("{", id="not_json"),
        pytest.param('{"turn_seq": -1, "at": "2026-11-28T05:50:00+00:00"}', id="negative"),
        pytest.param('{"turn_seq": 3, "at": 1}', id="at_number"),
    ],
)
def test_load_turn_point_when_broken(make_workspace: MakeWorkspace, tmp_path: Path, text: str) -> None:
    """壊れたファイルは読まない（異常系）。"""
    # 準備
    root = make_workspace()
    state_root = tmp_path / "state"
    path = _turn_point_path(root, state_root)
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")
    # 実行・検証
    with pytest.raises(SchemaMismatchError, match="スキーマに合いません") as raised:
        read_point.load_turn_point(root, state_root=state_root)
    assert any(line.startswith("turn_point.json:") for line in raised.value.lines)


def test_save_turn_point_when_write_fails(
    make_workspace: MakeWorkspace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """書けなければ前の始まりを残す（異常系）。"""
    # 準備
    root = make_workspace()
    state_root = tmp_path / "state"
    read_point.save_turn_point(root, 3, "2026-11-28T05:50:00+00:00", state_root=state_root)

    def _failing_replace(*args: object, **kwargs: object) -> None:
        """置き換えを OSError で失敗させる。"""
        raise OSError("置き換えられない")

    monkeypatch.setattr(os, "replace", _failing_replace)
    # 実行・検証
    with pytest.raises(WriteFailedError):
        read_point.save_turn_point(root, 7, "2026-11-28T06:00:00+00:00", state_root=state_root)
    monkeypatch.undo()
    assert read_point.load_turn_point(root, state_root=state_root) == (3, "2026-11-28T05:50:00+00:00")
    assert sorted(path.name for path in _turn_point_path(root, state_root).parent.iterdir()) == [
        "turn_point.json"
    ]
