"""migrations/v0.11.0/scripts/remove_tag_vocabulary.py（設定からタグの語彙を削除する変換）の単体テスト。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

from fixture_types import MakeItem, MakeWorkspace, SnapshotTree
from workspace_fixtures import RECORD_DIR

# 変換のスクリプトの、プラグインの `skills/mindmap/` からの場所
SCRIPT_PATH = Path("migrations") / "v0.11.0" / "scripts" / "remove_tag_vocabulary.py"

# 変換が書くファイルの、ワークスペースからの相対パス
CONFIG_PATH = f"{RECORD_DIR}/config.yaml"


@pytest.fixture
def remove_tag_vocabulary(scripts_dir: Path) -> ModuleType:
    """版のフォルダにある変換のスクリプトを、`call` と同じように場所から読み込んで返す。"""
    path = scripts_dir.parent / SCRIPT_PATH
    spec = importlib.util.spec_from_file_location("migration_v0_11_0_remove_tag_vocabulary", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_config(root: Path) -> dict[str, Any]:
    """ワークスペースの config.yaml を読む。"""
    return yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))


def test_remove_tag_vocabulary(
    remove_tag_vocabulary: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    snapshot_tree: SnapshotTree,
) -> None:
    """設定から tags を削除し、他のキーと項目のタグを残す（正常系）。"""
    # 準備
    settings = {**valid_settings, "tags": [{"name": "保存", "summary": "s"}]}
    root = make_workspace(make_item("D-1", tags=["保存"]), settings=settings)
    before = snapshot_tree(root)
    config_before = _read_config(root)
    # 実行
    changed = remove_tag_vocabulary.migrate(root)
    # 検証
    assert changed == [CONFIG_PATH]
    config_after = _read_config(root)
    assert "tags" not in config_after
    assert list(config_after) == [key for key in config_before if key != "tags"]
    assert config_after == {key: value for key, value in config_before.items() if key != "tags"}
    # 設定以外のファイル（項目のタグを含む）は呼ぶ前と同じ
    after = snapshot_tree(root)
    assert {name: data for name, data in after.items() if name != CONFIG_PATH} == {
        name: data for name, data in before.items() if name != CONFIG_PATH
    }


def test_remove_tag_vocabulary_when_no_tags(
    remove_tag_vocabulary: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
) -> None:
    """tags が無ければ書かない。もう一度当てても変えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", tags=["保存"]))
    before = snapshot_tree(root)
    # 実行
    changed = remove_tag_vocabulary.migrate(root)
    second_changed = remove_tag_vocabulary.migrate(root)
    # 検証
    assert changed == []
    assert second_changed == []
    assert snapshot_tree(root) == before


def test_remove_tag_vocabulary_when_broken(
    remove_tag_vocabulary: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
) -> None:
    """設定の形が崩れていれば移さない（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["保存"]), raw_files={"config.yaml": "- 保存\n- 通知\n"}
    )
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(ValueError, match=r"config\.yaml"):
        remove_tag_vocabulary.migrate(root)
    assert snapshot_tree(root) == before
