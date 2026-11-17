"""migrations/v0.13.0/scripts/body_to_docs_path.py（本文のパスを docs/ から書く変換）の単体テスト。"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

from fixture_types import MakeItem, MakeWorkspace, SnapshotTree
from migration_helpers import load_migration_script
from workspace_fixtures import RECORD_DIR


@pytest.fixture
def body_to_docs_path(scripts_dir: Path) -> ModuleType:
    """v0.13.0 の body_to_docs_path.py を読み込んで返す。"""
    return load_migration_script(scripts_dir, "v0.13.0", "body_to_docs_path")


def _items(root: Path) -> list[dict[str, Any]]:
    """decisions.yaml の items を読む。"""
    return yaml.safe_load((root / RECORD_DIR / "decisions.yaml").read_text(encoding="utf-8"))["items"]


def test_body_to_docs_path(
    body_to_docs_path: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
) -> None:
    """ファイル名だけの body を docs/ からのパスにする（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", body="D-1.md"),
        make_item("D-2", body="docs/D-2.md"),
        make_item("D-3"),
        with_history=False,
    )
    # 実行
    changed = body_to_docs_path.migrate(root)
    after_first = snapshot_tree(root)
    changed_twice = body_to_docs_path.migrate(root)
    # 検証
    assert changed == [f"{RECORD_DIR}/decisions.yaml"]
    d1, d2, d3 = _items(root)
    assert d1["body"] == "docs/D-1.md"
    assert d2["body"] == "docs/D-2.md"
    assert "body" not in d3
    assert changed_twice == []
    assert snapshot_tree(root) == after_first
