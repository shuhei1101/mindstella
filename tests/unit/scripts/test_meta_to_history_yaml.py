"""migrations/v0.13.0/scripts/meta_to_history_yaml.py（項目の履歴のキーを history.yaml へ移す変換）の単体テスト。"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

from fixture_types import MakeItem, MakeWorkspace, SnapshotTree
from migration_helpers import load_migration_script
from workspace_fixtures import RECORD_DIR

# D-1 の作成日時・更新日時
CREATED = "2026-10-01T00:00:00+00:00"
UPDATED = "2026-10-02T00:00:00+00:00"

# D-1 の変更履歴 1 回分
ENTRY = {"seq": 3, "at": UPDATED, "by": "ai", "before": {"answer": None}}


@pytest.fixture
def meta_to_history_yaml(scripts_dir: Path) -> ModuleType:
    """v0.13.0 の meta_to_history_yaml.py を読み込んで返す。"""
    return load_migration_script(scripts_dir, "v0.13.0", "meta_to_history_yaml")


def _read(root: Path, file_name: str) -> Any:
    """記録のフォルダの YAML を読む。"""
    return yaml.safe_load((root / RECORD_DIR / file_name).read_text(encoding="utf-8"))


def test_meta_to_history_yaml(
    meta_to_history_yaml: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
) -> None:
    """履歴のキーを値を変えずに移す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item(
            "D-1",
            answer="答え",
            created=CREATED,
            updated=UPDATED,
            updated_by="ai",
            seq=3,
            history=[ENTRY],
        ),
        with_history=False,
    )
    # 実行
    meta_to_history_yaml.migrate(root)
    after_first = snapshot_tree(root)
    changed_twice = meta_to_history_yaml.migrate(root)
    # 検証
    assert _read(root, "history.yaml")["items"]["D-1"] == {
        "created": CREATED,
        "updated": UPDATED,
        "updated_by": "ai",
        "seq": 3,
        "history": [ENTRY],
    }
    assert _read(root, "decisions.yaml")["items"][0] == make_item("D-1", answer="答え")
    assert changed_twice == []
    assert snapshot_tree(root) == after_first
