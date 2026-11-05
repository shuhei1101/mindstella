"""migrations/v0.12.0/scripts/tags_to_objects.py（項目のタグをオブジェクトにする変換）の単体テスト。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

from fixture_types import MakeItem, MakeThread, MakeWorkspace, SnapshotTree, WriteThreads
from workspace_fixtures import RECORD_DIR

# 変換のスクリプトの、プラグインの `skills/mindmap/` からの場所
SCRIPT_PATH = Path("migrations") / "v0.12.0" / "scripts" / "tags_to_objects.py"

# 変換が書くファイルの、ワークスペースからの相対パス
DECISIONS_PATH = f"{RECORD_DIR}/decisions.yaml"

# D-1 の更新日時
UPDATED_T0 = "2026-01-01T00:00:00+00:00"


@pytest.fixture
def tags_to_objects(scripts_dir: Path) -> ModuleType:
    """版のフォルダにある変換のスクリプトを、`call` と同じように場所から読み込んで返す。"""
    path = scripts_dir.parent / SCRIPT_PATH
    spec = importlib.util.spec_from_file_location("migration_v0_12_0_tags_to_objects", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_items(root: Path, file_name: str) -> list[dict[str, Any]]:
    """ワークスペースの種類ごとの YAML の items を読む。"""
    data = yaml.safe_load((root / RECORD_DIR / file_name).read_text(encoding="utf-8"))
    return data["items"]


def test_tags_to_objects(
    tags_to_objects: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    snapshot_tree: SnapshotTree,
) -> None:
    """文字列のタグを name のオブジェクトにし、表記をそろえて重なるタグは最初だけ残す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["API", "画面", "ａｐｉ"], updated=UPDATED_T0),
        make_item("T-1", tags=[{"name": "通知", "main": True}]),
        make_item("N-1"),
    )
    write_threads(root, make_thread("TH-1", tags=["起票"]))
    before = snapshot_tree(root)
    # 実行
    changed = tags_to_objects.migrate(root)
    # 検証
    assert changed == [DECISIONS_PATH]
    decision = _read_items(root, "decisions.yaml")[0]
    assert decision["tags"] == [{"name": "API"}, {"name": "画面"}]
    assert decision["updated"] == UPDATED_T0
    # decisions.yaml 以外（T-1・N-1・TH-1）は呼ぶ前と同じ
    after = snapshot_tree(root)
    assert {name: data for name, data in after.items() if name != DECISIONS_PATH} == {
        name: data for name, data in before.items() if name != DECISIONS_PATH
    }


def test_tags_to_objects_when_applied(
    tags_to_objects: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
) -> None:
    """もう一度当てても変えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", tags=["API", "画面", "ａｐｉ"]))
    tags_to_objects.migrate(root)
    first = snapshot_tree(root)
    # 実行
    second_changed = tags_to_objects.migrate(root)
    # 検証
    assert second_changed == []
    assert snapshot_tree(root) == first


def test_tags_to_objects_when_broken(
    tags_to_objects: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
) -> None:
    """形が崩れていれば移さない（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("T-1", tags=["画面"]), raw_files={"decisions.yaml": "- API\n- 画面\n"}
    )
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(ValueError, match=r"decisions\.yaml"):
        tags_to_objects.migrate(root)
    assert snapshot_tree(root) == before
