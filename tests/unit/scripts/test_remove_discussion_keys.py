"""migrations/v0.14.0/scripts/remove_discussion_keys.py（議論のキーを消す変換）の単体テスト。"""

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
SCRIPT_PATH = Path("migrations") / "v0.14.0" / "scripts" / "remove_discussion_keys.py"

# 移し替える前の版の設定（削除するキーを全て持つ）
LEGACY_SETTINGS: dict[str, Any] = {
    "summary": "家計簿アプリを決める",
    "playbooks": ["システム開発"],
    "target_label": "機能",
    "phases": ["目的", "要件"],
    "targets": [{"name": "認証", "summary": "ログイン"}],
    "categories": [{"name": "方式", "target": "認証", "summary": "方式の選び方"}],
    "goal": {"phase": "要件", "summary": "要件が決まる", "deliverables": []},
    "links": [],
}

# 削除するキー
REMOVED_SETTING_KEYS = ("goal", "phases", "playbooks", "targets", "target_label", "categories")
REMOVED_ITEM_KEYS = ("target", "category", "phase", "attrs", "weight", "deliverable", "angles", "confidence")


@pytest.fixture
def remove_discussion_keys(scripts_dir: Path) -> ModuleType:
    """版のフォルダにある変換のスクリプトを、`call` と同じように場所から読み込んで返す。"""
    path = scripts_dir.parent / SCRIPT_PATH
    spec = importlib.util.spec_from_file_location("migration_v0_14_0_remove_discussion_keys", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_yaml(root: Path, name: str) -> Any:
    """ワークスペースの記録のフォルダの YAML を読む。"""
    return yaml.safe_load((root / RECORD_DIR / name).read_text(encoding="utf-8"))


def _item(root: Path, name: str, item_id: str) -> dict[str, Any]:
    """種類の YAML から ID の項目を返す。"""
    return next(item for item in _read_yaml(root, name)["items"] if item["id"] == item_id)


def _legacy_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> Path:
    """削除するキーを設定と D-1・A-1・R-1 に持つワークスペースを作る。"""
    return make_workspace(
        make_item(
            "D-1",
            phase="要件",
            target="認証",
            category="方式",
            attrs={"優先度": "高"},
            weight="大",
            body="docs/D-1.md",
        ),
        make_item("A-1", deliverable=True),
        make_item("R-1", angles=["費用", "運用"], confidence="中"),
        settings=LEGACY_SETTINGS,
        bodies={"D-1.md": "# 背景\n\n本文\n", "A-1.md": "資料の本文\n"},
    )


def test_migrate(
    remove_discussion_keys: ModuleType, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """削除するキーを消し、残す値をタグと本文へ移す（正常系）。"""
    # 準備
    root = _legacy_workspace(make_workspace, make_item)
    # 実行
    remove_discussion_keys.migrate(root)
    # 検証
    config = _read_yaml(root, "config.yaml")
    assert list(config) == ["summary", "links"]
    decision = _item(root, "decisions.yaml", "D-1")
    assert {"name": "topic:認証"} in decision["tags"]
    assert {"name": "topic:方式"} in decision["tags"]
    decision_body = (root / RECORD_DIR / "docs" / "D-1.md").read_text(encoding="utf-8")
    assert "属性" in decision_body
    assert "| 優先度 | 高 |" in decision_body
    research = _item(root, "research.yaml", "R-1")
    assert research["body"] == "docs/R-1.md"
    research_body = (root / RECORD_DIR / "docs" / "R-1.md").read_text(encoding="utf-8")
    assert "観点と確かさ" in research_body
    assert "費用" in research_body
    assert "運用" in research_body
    assert "中" in research_body
    document = _item(root, "docs.yaml", "A-1")
    assert set(REMOVED_ITEM_KEYS).isdisjoint(decision)
    assert set(REMOVED_ITEM_KEYS).isdisjoint(document)
    assert set(REMOVED_ITEM_KEYS).isdisjoint(research)


def test_migrate_when_tag_exists(
    remove_discussion_keys: ModuleType, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """同じ名前のタグは足さない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=[{"name": "topic:認証"}], target="認証"), settings=LEGACY_SETTINGS
    )
    # 実行
    remove_discussion_keys.migrate(root)
    # 検証
    assert _item(root, "decisions.yaml", "D-1")["tags"] == [{"name": "topic:認証"}]


def test_migrate_when_already_current(
    remove_discussion_keys: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
) -> None:
    """もう一度当てても変わらない（正常系）。"""
    # 準備
    root = _legacy_workspace(make_workspace, make_item)
    remove_discussion_keys.migrate(root)
    before = snapshot_tree(root)
    # 実行
    changed = remove_discussion_keys.migrate(root)
    # 検証
    assert changed == []
    assert snapshot_tree(root) == before


@pytest.mark.parametrize(
    ("item_id", "attrs", "body_name", "expected"),
    [
        pytest.param("D-1", {"メモ": "A|B\nC"}, "D-1.md", "| メモ | A\\|B<br>C |", id="markdown"),
        pytest.param("A-1", {"式": "a<b&c"}, "A-1.html", "<td>a&lt;b&amp;c</td>", id="html"),
    ],
)
def test_migrate_when_cell_has_special_chars(
    remove_discussion_keys: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    item_id: str,
    attrs: dict[str, str],
    body_name: str,
    expected: str,
) -> None:
    """表のセルの記号を打ち消す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item(item_id, attrs=attrs, body=f"docs/{body_name}"),
        settings=LEGACY_SETTINGS,
        bodies={body_name: "本文\n"},
    )
    # 実行
    remove_discussion_keys.migrate(root)
    # 検証
    assert expected in (root / RECORD_DIR / "docs" / body_name).read_text(encoding="utf-8")
