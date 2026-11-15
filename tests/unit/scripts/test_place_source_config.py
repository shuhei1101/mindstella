"""migrations/v0.13.0/scripts/place_source_config.py（記録の配信の設定を置く変換）の単体テスト。"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest
import yaml

import store
from fixture_types import MakeWorkspace
from migration_helpers import load_migration_script
from workspace_fixtures import RECORD_DIR
from workspaces import workspace_id_for

# プラグインの種類ごとの 7 つのスキーマと共通のスキーマ
SCHEMA_NAMES = [
    "common.schema.json",
    "decisions.schema.json",
    "docs.schema.json",
    "logs.schema.json",
    "notes.schema.json",
    "research.schema.json",
    "tasks.schema.json",
    "terms.schema.json",
]

# 利用者が書き換えた配信の設定
EDITED_CONFIG = "version: '3'\nname: 書き換えた配信\n"


@pytest.fixture
def place_source_config(scripts_dir: Path) -> ModuleType:
    """v0.13.0 の place_source_config.py を読み込んで返す。"""
    return load_migration_script(scripts_dir, "v0.13.0", "place_source_config")


def _schema_texts(folder: Path) -> dict[str, str]:
    """フォルダの 8 つのスキーマの中身を返す。"""
    return {name: (folder / name).read_text(encoding="utf-8") for name in SCHEMA_NAMES}


def test_place_source_config(
    place_source_config: ModuleType, make_workspace: MakeWorkspace, scripts_dir: Path
) -> None:
    """設定が無ければ作り、スキーマを置き換える（正常系）。"""
    # 準備
    root = make_workspace(with_history=False)
    # 実行
    place_source_config.migrate(root)
    # 検証
    records = root / RECORD_DIR
    assert yaml.safe_load((records / "dev-docs.yaml").read_text(encoding="utf-8")) == (
        store.build_source_config(workspace_id_for(root), "要件出しのスキル mindmap を設計する")
    )
    assert sorted(path.name for path in (records / "schemas").iterdir()) == SCHEMA_NAMES
    assert _schema_texts(records / "schemas") == _schema_texts(scripts_dir.parent / "schemas")


def test_place_source_config_when_config_exists(
    place_source_config: ModuleType, make_workspace: MakeWorkspace, scripts_dir: Path
) -> None:
    """既にある設定は書き換えない（正常系）。"""
    # 準備
    root = make_workspace(raw_files={"dev-docs.yaml": EDITED_CONFIG}, with_history=False)
    # 実行
    place_source_config.migrate(root)
    # 検証
    records = root / RECORD_DIR
    assert (records / "dev-docs.yaml").read_text(encoding="utf-8") == EDITED_CONFIG
    assert _schema_texts(records / "schemas") == _schema_texts(scripts_dir.parent / "schemas")
