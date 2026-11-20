"""migrations/v0.14.0/scripts/markdown_bodies_to_mark_md.py（本文の Markdown を .mark.md へ改名する変換）の単体テスト。"""

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
SCRIPT_PATH = Path("migrations") / "v0.14.0" / "scripts" / "markdown_bodies_to_mark_md.py"

# D-1 の変更履歴（HTML の本文の回と Markdown の本文の回）
D1_HISTORY: list[dict[str, Any]] = [
    {"seq": 3, "by": "ai", "at": "2026-11-02T00:00:00+00:00", "before": {"body": "docs/D-1.html"}},
    {"seq": 2, "by": "ai", "at": "2026-11-01T00:00:00+00:00", "before": {"body": "docs/D-1.md"}},
]


@pytest.fixture
def markdown_bodies_to_mark_md(scripts_dir: Path) -> ModuleType:
    """版のフォルダにある変換のスクリプトを、`call` と同じように場所から読み込んで返す。"""
    path = scripts_dir.parent / SCRIPT_PATH
    spec = importlib.util.spec_from_file_location("migration_v0_14_0_markdown_bodies_to_mark_md", path)
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


def _markdown_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> Path:
    """Markdown の本文の D-1・HTML の本文の A-1・どこからも指されない X-1 を持つワークスペースを作る。"""
    return make_workspace(
        make_item("D-1", body="docs/D-1.md", updated="2026-11-02T00:00:00+00:00", history=D1_HISTORY),
        make_item("A-1", body="docs/A-1.html"),
        bodies={
            "D-1.md": "# 背景\n\n本文\n",
            "A-1.html": "<p>資料</p>\n",
            "X-1.md": "どこからも指されない本文\n",
        },
        legacy_bodies=True,
    )


def test_migrate(
    markdown_bodies_to_mark_md: ModuleType, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """Markdown の本文を改名し、`body` と `before.body` を書き換える（正常系）。"""
    # 準備
    root = _markdown_workspace(make_workspace, make_item)
    docs = root / RECORD_DIR / "docs"
    # 実行
    changed = markdown_bodies_to_mark_md.migrate(root)
    # 検証
    assert (docs / "D-1.mark.md").read_text(encoding="utf-8") == "# 背景\n\n本文\n"
    assert (docs / "X-1.mark.md").read_text(encoding="utf-8") == "どこからも指されない本文\n"
    assert not (docs / "D-1.md").exists()
    assert not (docs / "X-1.md").exists()
    assert _item(root, "decisions.yaml", "D-1")["body"] == "docs/D-1.mark.md"
    d1_history = _read_yaml(root, "history.yaml")["items"]["D-1"]
    assert d1_history["updated"] == "2026-11-02T00:00:00+00:00"
    assert [entry["seq"] for entry in d1_history["history"]] == [3, 2]
    assert [entry["before"]["body"] for entry in d1_history["history"]] == [
        "docs/D-1.html",
        "docs/D-1.mark.md",
    ]
    assert _item(root, "docs.yaml", "A-1")["body"] == "docs/A-1.html"
    assert (docs / "A-1.html").read_text(encoding="utf-8") == "<p>資料</p>\n"
    assert sorted(changed) == [
        ".mindstella/decisions.yaml",
        ".mindstella/docs/D-1.mark.md",
        ".mindstella/docs/X-1.mark.md",
        ".mindstella/history.yaml",
    ]


def test_migrate_when_already_current(
    markdown_bodies_to_mark_md: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
) -> None:
    """もう一度当てても変わらない（正常系）。"""
    # 準備
    root = _markdown_workspace(make_workspace, make_item)
    markdown_bodies_to_mark_md.migrate(root)
    before = snapshot_tree(root)
    # 実行
    changed = markdown_bodies_to_mark_md.migrate(root)
    # 検証
    assert changed == []
    assert snapshot_tree(root) == before


def test_migrate_when_target_exists(
    markdown_bodies_to_mark_md: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
) -> None:
    """改名先が既にあれば何も書かずに失敗する（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", body="docs/D-1.md"),
        bodies={"D-1.md": "前の本文\n", "D-1.mark.md": "改名先の本文\n"},
        legacy_bodies=True,
    )
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(RuntimeError, match=r"docs/D-1\.mark\.md"):
        markdown_bodies_to_mark_md.migrate(root)
    assert snapshot_tree(root) == before


def test_migrate_when_no_history(
    markdown_bodies_to_mark_md: ModuleType, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """変更履歴のファイルが無くても改名する（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", body="docs/D-1.md"), bodies={"D-1.md": "本文\n"}, legacy_bodies=True)
    (root / RECORD_DIR / "history.yaml").unlink()
    # 実行
    markdown_bodies_to_mark_md.migrate(root)
    # 検証
    assert (root / RECORD_DIR / "docs" / "D-1.mark.md").read_text(encoding="utf-8") == "本文\n"
    assert _item(root, "decisions.yaml", "D-1")["body"] == "docs/D-1.mark.md"
    assert not (root / RECORD_DIR / "history.yaml").exists()
