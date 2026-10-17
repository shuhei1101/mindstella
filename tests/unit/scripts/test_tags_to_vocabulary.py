"""migrations/v0.10.0/scripts/tags_to_vocabulary.py（使っているタグを語彙へ登録する変換）の単体テスト。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

from fixture_types import (
    MakeItem,
    MakeThread,
    MakeWorkspace,
    SnapshotTree,
    WriteThreads,
)
from workspace_fixtures import RECORD_DIR

# 変換のスクリプトの、プラグインの `skills/mindmap/` からの場所
SCRIPT_PATH = Path("migrations") / "v0.10.0" / "scripts" / "tags_to_vocabulary.py"

# 変換が書くファイルの、ワークスペースからの相対パス
CONFIG_PATH = f"{RECORD_DIR}/config.yaml"


@pytest.fixture
def tags_to_vocabulary(scripts_dir: Path) -> ModuleType:
    """版のフォルダにある変換のスクリプトを、`call` と同じように場所から読み込んで返す。"""
    path = scripts_dir.parent / SCRIPT_PATH
    spec = importlib.util.spec_from_file_location("migration_v0_10_0_tags_to_vocabulary", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_config(root: Path) -> dict[str, Any]:
    """ワークスペースの config.yaml を読む。"""
    return yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))


def test_tags_to_vocabulary(
    tags_to_vocabulary: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    snapshot_tree: SnapshotTree,
) -> None:
    """項目とスレッドのタグを重なりなく名前の順で語彙へ書く（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["保存", "通知"]), make_item("N-1", tags=["脱線", "保存"])
    )
    write_threads(root, make_thread("TH-1", tags=["起票"]))
    before = snapshot_tree(root)
    config_before = _read_config(root)
    # 実行
    changed = tags_to_vocabulary.migrate(root)
    # 検証
    assert changed == [CONFIG_PATH]
    config_after = _read_config(root)
    assert config_after["tags"] == [
        {"name": "保存"},
        {"name": "脱線"},
        {"name": "起票"},
        {"name": "通知"},
    ]
    assert {key: value for key, value in config_after.items() if key != "tags"} == config_before
    # 設定以外のファイルは呼ぶ前と同じ
    after = snapshot_tree(root)
    assert {name: data for name, data in after.items() if name != CONFIG_PATH} == {
        name: data for name, data in before.items() if name != CONFIG_PATH
    }


def test_tags_to_vocabulary_when_existing(
    tags_to_vocabulary: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """既にある語彙の説明を残し、無いタグだけを足す。もう一度当てても変えない（正常系）。"""
    # 準備
    settings = {**valid_settings, "tags": [{"name": "保存", "summary": "s"}]}
    root = make_workspace(make_item("D-1", tags=["保存", "通知"]), settings=settings)
    # 実行
    tags_to_vocabulary.migrate(root)
    after_first = _read_config(root)
    second_changed = tags_to_vocabulary.migrate(root)
    # 検証
    assert after_first["tags"] == [{"name": "保存", "summary": "s"}, {"name": "通知"}]
    assert second_changed == []
    assert _read_config(root) == after_first


def test_tags_to_vocabulary_when_no_tags(
    tags_to_vocabulary: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
) -> None:
    """タグを使っていなければ書かない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行
    changed = tags_to_vocabulary.migrate(root)
    # 検証
    assert changed == []
    assert snapshot_tree(root) == before
    assert "tags" not in _read_config(root)


def test_tags_to_vocabulary_when_broken(
    tags_to_vocabulary: ModuleType,
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
        tags_to_vocabulary.migrate(root)
    assert snapshot_tree(root) == before
