"""kinds.py（種類の定義）の単体テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

import kinds


@pytest.mark.parametrize(
    ("item_id", "expected"),
    [
        pytest.param("D-12", "decision", id="decision"),
        pytest.param("L-1", "log", id="log"),
    ],
)
def test_kind_of_id_when_known_prefix(item_id: str, expected: str) -> None:
    """頭の文字から種類を引く（正常系）。"""
    # 実行
    kind = kinds.kind_of_id(item_id)
    # 検証
    assert kind == expected


@pytest.mark.parametrize(
    "item_id",
    [
        pytest.param("X-1", id="unknown_prefix"),
        pytest.param("D-", id="no_number"),
        pytest.param("D-0x", id="not_digits"),
        pytest.param("d-1", id="lowercase"),
    ],
)
def test_kind_of_id_when_unknown(item_id: str) -> None:
    """形が合わない・頭の文字が無い ID は None を返す（正常系）。"""
    # 実行
    kind = kinds.kind_of_id(item_id)
    # 検証
    assert kind is None


def test_records_root(tmp_path: Path) -> None:
    """直下の .mindstella を返す（正常系）。"""
    # 実行
    records = kinds.records_root(tmp_path)
    # 検証
    assert records == tmp_path / ".mindstella"
    # フォルダは作らない
    assert not records.exists()


def test_body_root(tmp_path: Path) -> None:
    """直下の docs を返す（正常系）。"""
    # 実行
    body_dir = kinds.body_root(tmp_path)
    # 検証
    assert body_dir == tmp_path / "docs"
    # フォルダは作らない
    assert not body_dir.exists()


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        pytest.param("decisions.yaml", ".mindstella/decisions.yaml", id="record_file"),
        pytest.param("../docs/D-1.mark.md", "docs/D-1.mark.md", id="body"),
    ],
)
def test_workspace_path(name: str, expected: str) -> None:
    """記録のファイルと本文を直下からのパスにする（正常系）。"""
    # 実行
    path = kinds.workspace_path(name)
    # 検証
    assert path == expected
