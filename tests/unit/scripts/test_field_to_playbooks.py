"""migrations/v0.5.0/scripts/field_to_playbooks.py（設定の field をプレイブックの配列へ移す変換）の単体テスト。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
import yaml

from fixture_types import MakeWorkspace, SnapshotTree
from migration_helpers import snapshot_mtimes

# 変換のスクリプトの、プラグインの `skills/mindmap/` からの場所
SCRIPT_PATH = Path("migrations") / "v0.5.0" / "scripts" / "field_to_playbooks.py"


@pytest.fixture
def field_to_playbooks(scripts_dir: Path) -> ModuleType:
    """版のフォルダにある変換のスクリプトを、`call` と同じように場所から読み込んで返す。"""
    path = scripts_dir.parent / SCRIPT_PATH
    spec = importlib.util.spec_from_file_location("migration_v0_5_0_field_to_playbooks", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migrate(field_to_playbooks: ModuleType, make_workspace: MakeWorkspace) -> None:
    """field を同じ位置の playbooks の 1 件の配列へ移す（正常系）。"""
    # 準備
    root = make_workspace(
        settings={
            "summary": "要件出しのスキルを設計する",
            "field": "システム開発",
            "target_label": "システム",
            "phases": ["目的", "要件", "構成"],
        },
        settings_file="mindmap.yaml",
        top=True,
    )
    # 実行
    changed = field_to_playbooks.migrate(root)
    # 検証
    assert changed == ["mindmap.yaml"]
    settings = yaml.safe_load((root / "mindmap.yaml").read_text(encoding="utf-8"))
    assert list(settings) == ["summary", "playbooks", "target_label", "phases"]
    assert settings["playbooks"] == ["システム開発"]
    assert settings["target_label"] == "システム"
    assert list(root.rglob("*.tmp")) == []


def test_migrate_when_no_field(
    field_to_playbooks: ModuleType, make_workspace: MakeWorkspace, snapshot_tree: SnapshotTree
) -> None:
    """field を持たない設定は何も書かない（正常系）。"""
    # 準備
    root = make_workspace(
        settings={
            "summary": "要件出しのスキルを設計する",
            "playbooks": ["システム開発"],
            "target_label": "機能",
            "phases": ["目的", "要件", "構成"],
        },
        settings_file="mindmap.yaml",
        top=True,
    )
    before = snapshot_tree(root)
    before_mtimes = snapshot_mtimes(root)
    # 実行
    changed = field_to_playbooks.migrate(root)
    # 検証
    assert changed == []
    assert snapshot_tree(root) == before
    assert snapshot_mtimes(root) == before_mtimes


def test_migrate_when_both(
    field_to_playbooks: ModuleType, make_workspace: MakeWorkspace, snapshot_tree: SnapshotTree
) -> None:
    """field と playbooks を両方持つ設定は送り、何も書かない（異常系）。"""
    # 準備
    root = make_workspace(
        settings={
            "summary": "要件出しのスキルを設計する",
            "field": "システム開発",
            "playbooks": ["壁打ち"],
            "target_label": "システム",
            "phases": ["目的", "要件", "構成"],
        },
        settings_file="mindmap.yaml",
        top=True,
    )
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(ValueError, match="field と playbooks を両方持ちます"):
        field_to_playbooks.migrate(root)
    assert snapshot_tree(root) == before


def test_migrate_when_settings_renamed(
    field_to_playbooks: ModuleType, make_workspace: MakeWorkspace, snapshot_tree: SnapshotTree
) -> None:
    """mindmap.yaml が無ければ何も書かない（正常系）。"""
    # 準備
    root = make_workspace(top=True)
    before = snapshot_tree(root)
    before_mtimes = snapshot_mtimes(root)
    # 実行
    changed = field_to_playbooks.migrate(root)
    # 検証
    assert changed == []
    assert snapshot_tree(root) == before
    assert snapshot_mtimes(root) == before_mtimes
    assert not (root / "mindmap.yaml").exists()
