"""migrations/v0.14.0/scripts/move_bodies_to_root.py（本文と埋め込むファイルを直下へ移す変換）の単体テスト。"""

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
SCRIPT_PATH = Path("migrations") / "v0.14.0" / "scripts" / "move_bodies_to_root.py"

# 配信の設定の種類の行の id
KIND_IDS = ("decisions", "tasks", "research", "docs", "terms", "notes", "logs")


def _source_config(paths_prefix: str) -> dict[str, Any]:
    """種類ごとの 7 つの行を持つ配信の設定を組み立てる（terms の行だけ write_dates を真にする）。"""
    return {
        "version": "3",
        "name": "mindstella-workspace-123456",
        "related": {"types": ["depends_on", "parent", "for", "see_also"]},
        "documents": [
            {
                "id": kind_id,
                "paths": [f"{paths_prefix}{kind_id}.yaml"],
                "schema": f"schemas/{kind_id}.schema.json",
                "records": "items",
                "body_file": "body",
                "write_dates": kind_id == "terms",
            }
            for kind_id in KIND_IDS
        ],
    }


# 移し替える前の配信の設定（paths_base を持たず、paths は記録のフォルダからの YAML の名前）
OLD_SOURCE_CONFIG: dict[str, Any] = _source_config("")

# 移し替えた後の配信の設定（paths_base を足し、paths を直下からのパスにする）
NEW_SOURCE_CONFIG: dict[str, Any] = {**_source_config(".mindstella/"), "paths_base": ".."}

# D-1 の変更履歴（移す前の本文の回）
D1_HISTORY: list[dict[str, Any]] = [
    {"seq": 2, "by": "ai", "at": "2026-11-01T00:00:00+00:00", "before": {"body": "docs/D-1.md"}},
]


@pytest.fixture
def move_bodies_to_root(scripts_dir: Path) -> ModuleType:
    """版のフォルダにある変換のスクリプトを、`call` と同じように場所から読み込んで返す。"""
    path = scripts_dir.parent / SCRIPT_PATH
    spec = importlib.util.spec_from_file_location("migration_v0_14_0_move_bodies_to_root", path)
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


def _old_workspace(make_workspace: MakeWorkspace, make_item: MakeItem, *, with_files: bool = True) -> Path:
    """本文と release/ を記録のフォルダに持つ、移し替える前のワークスペースを作る。

    with_files が真なら、埋め込むファイルの `.mindstella/files/clip.mp4` も置く。
    """
    root = make_workspace(
        make_item("D-1", body="docs/D-1.mark.md", updated="2026-11-02T00:00:00+00:00", history=D1_HISTORY),
        make_item("A-1", body="docs/A-1.html"),
        raw_files={"dev-docs.yaml": yaml.safe_dump(OLD_SOURCE_CONFIG, allow_unicode=True, sort_keys=False)},
        bodies={"D-1.mark.md": "# 背景\n\n本文\n", "A-1.html": "<p>資料</p>\n"},
        legacy_bodies=True,
    )
    records = root / RECORD_DIR
    # 埋め込むファイルを持つワークスペースか
    if with_files:
        (records / "files").mkdir()
        (records / "files" / "clip.mp4").write_bytes(b"\x00\x01clip")
    (records / "release").mkdir()
    (records / "release" / "A-1.mark.md").write_text("書き出した資料\n", encoding="utf-8")
    return root


def test_migrate(move_bodies_to_root: ModuleType, make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """本文と埋め込むファイルを直下へ移し、参照と配信の設定を書き換え、release/ を消す（正常系）。"""
    # 準備
    root = _old_workspace(make_workspace, make_item)
    # 実行
    changed = move_bodies_to_root.migrate(root)
    # 検証
    assert (root / "docs" / "D-1.mark.md").read_text(encoding="utf-8") == "# 背景\n\n本文\n"
    assert (root / "docs" / "A-1.html").read_text(encoding="utf-8") == "<p>資料</p>\n"
    assert (root / "files" / "clip.mp4").read_bytes() == b"\x00\x01clip"
    assert not (root / RECORD_DIR / "docs").exists()
    assert not (root / RECORD_DIR / "files").exists()
    assert not (root / RECORD_DIR / "release").exists()
    assert _item(root, "decisions.yaml", "D-1")["body"] == "../docs/D-1.mark.md"
    assert _item(root, "docs.yaml", "A-1")["body"] == "../docs/A-1.html"
    d1_history = _read_yaml(root, "history.yaml")["items"]["D-1"]
    assert d1_history["updated"] == "2026-11-02T00:00:00+00:00"
    assert [entry["seq"] for entry in d1_history["history"]] == [2]
    assert d1_history["history"][0]["before"]["body"] == "../docs/D-1.md"
    assert _read_yaml(root, "dev-docs.yaml") == NEW_SOURCE_CONFIG
    assert sorted(changed) == [
        ".mindstella/decisions.yaml",
        ".mindstella/dev-docs.yaml",
        ".mindstella/docs.yaml",
        ".mindstella/history.yaml",
        ".mindstella/release/",
        "docs/",
        "files/",
    ]


def test_migrate_when_already_current(
    move_bodies_to_root: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
) -> None:
    """もう一度当てても変わらない（正常系）。"""
    # 準備
    root = _old_workspace(make_workspace, make_item)
    move_bodies_to_root.migrate(root)
    before = snapshot_tree(root)
    # 実行
    changed = move_bodies_to_root.migrate(root)
    # 検証
    assert changed == []
    assert snapshot_tree(root) == before


@pytest.mark.parametrize(
    ("folder", "file_name", "with_files"),
    [
        pytest.param("docs", "memo.md", True, id="root-docs"),
        pytest.param("files", "memo.png", False, id="root-files-without-records-files"),
    ],
)
def test_migrate_when_root_folder_exists(
    move_bodies_to_root: ModuleType,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    folder: str,
    file_name: str,
    with_files: bool,
) -> None:
    """移し替えていないワークスペースの直下に docs/ か files/ があれば何も書かずに失敗する（異常系）。"""
    # 準備
    root = _old_workspace(make_workspace, make_item, with_files=with_files)
    (root / folder).mkdir()
    (root / folder / file_name).write_text("利用者のファイル\n", encoding="utf-8")
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(RuntimeError, match=rf"{folder}/.*改名"):
        move_bodies_to_root.migrate(root)
    assert snapshot_tree(root) == before


def test_migrate_without_bodies(
    move_bodies_to_root: ModuleType, make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """本文も埋め込むファイルも持たないワークスペースでも配信の設定を書き換える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        raw_files={"dev-docs.yaml": yaml.safe_dump(OLD_SOURCE_CONFIG, allow_unicode=True, sort_keys=False)},
        legacy_bodies=True,
        with_history=False,
    )
    (root / RECORD_DIR / "docs").rmdir()
    # 実行
    changed = move_bodies_to_root.migrate(root)
    # 検証
    assert _read_yaml(root, "dev-docs.yaml") == NEW_SOURCE_CONFIG
    assert not (root / "docs").exists()
    assert not (root / "files").exists()
    assert not (root / RECORD_DIR / "history.yaml").exists()
    assert changed == [".mindstella/dev-docs.yaml"]
