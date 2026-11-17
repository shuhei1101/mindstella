"""migrations/v0.13.0/scripts/refs_to_related.py（参照のキーを種類つきの関連へ移す変換）の単体テスト。"""

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
def refs_to_related(scripts_dir: Path) -> ModuleType:
    """v0.13.0 の refs_to_related.py を読み込んで返す。"""
    return load_migration_script(scripts_dir, "v0.13.0", "refs_to_related")


def _item(root: Path, file_name: str, item_id: str) -> dict[str, Any]:
    """種類ごとの YAML から ID の項目を読む。"""
    items = yaml.safe_load((root / RECORD_DIR / file_name).read_text(encoding="utf-8"))["items"]
    return next(item for item in items if item["id"] == item_id)


def test_refs_to_related(
    refs_to_related: ModuleType, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """参照のキーを related へ移し、同じ組は 1 件にする（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("D-2", depends_on=["D-1"], parent="D-1", related=["R-1", "D-1"]),
        make_item("T-1", depends_on=["T-2"], **{"for": ["D-2"]}),
        make_item("T-2"),
        make_item("R-1"),
        with_history=False,
    )
    # 実行
    changed = refs_to_related.migrate(root)
    # 検証
    assert changed == [f"{RECORD_DIR}/decisions.yaml", f"{RECORD_DIR}/tasks.yaml"]
    d2 = _item(root, "decisions.yaml", "D-2")
    assert d2["related"] == [
        {"to": "D-1", "type": "depends_on"},
        {"to": "D-1", "type": "parent"},
        {"to": "R-1", "type": "see_also"},
        {"to": "D-1", "type": "see_also"},
    ]
    assert "depends_on" not in d2
    assert "parent" not in d2
    assert _item(root, "tasks.yaml", "T-1")["related"] == [
        {"to": "T-2", "type": "depends_on"},
        {"to": "D-2", "type": "for"},
    ]


def test_refs_to_related_when_applied_twice(
    refs_to_related: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
) -> None:
    """2 度当てても変わらない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("D-2", depends_on=["D-1"], related=["D-1"]),
        with_history=False,
    )
    refs_to_related.migrate(root)
    before = snapshot_tree(root)
    # 実行
    changed = refs_to_related.migrate(root)
    # 検証
    assert changed == []
    assert snapshot_tree(root) == before
