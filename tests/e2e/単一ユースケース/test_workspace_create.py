"""ワークスペースの作成（スキルが新しいワークスペースを作る）の E2E テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from readme_helpers import assert_readme_commands
from workspace_fixtures import LOCK_FILE_NAME, RECORD_DIR, REPO_ROOT, CallTool, SnapshotTree

# スキルがセットアップのステップで決める設定
SETTINGS: dict[str, Any] = {
    "summary": "要件出しのスキル mindmap を設計する",
    "playbooks": ["システム開発"],
    "target_label": "システム",
    "phases": ["目的", "要件", "構成"],
    "targets": [{"name": "mindmap", "summary": "話し合いを記録するスキル"}],
    "categories": [{"name": "データ構造", "target": "mindmap", "summary": "YAML の種類とキー"}],
    "goal": {
        "phase": "構成",
        "summary": "作り始められる",
        "deliverables": [{"title": "YAML のスキーマ"}],
    },
    "links": [],
}

# 利用者が書いた README の中身（自動で書いた印が無い）
USER_README = "# 家計簿アプリの話し合い\n"

# 作られる 7 種類の YAML のファイル名
KIND_YAML_FILES = (
    "decisions.yaml",
    "tasks.yaml",
    "research.yaml",
    "docs.yaml",
    "terms.yaml",
    "notes.yaml",
    "logs.yaml",
)


def _read_kind_yamls(root: Path) -> dict[str, Any]:
    """7 種類の YAML を、ファイル名 → 読んだ値にして返す。"""
    return {
        name: yaml.safe_load((root / RECORD_DIR / name).read_text(encoding="utf-8"))
        for name in KIND_YAML_FILES
    }


def _list_top(root: Path) -> list[str]:
    """直下のファイルとフォルダの名前を並べて返す（排他ロックのファイルは除く）。"""
    return sorted(path.name for path in root.iterdir() if path.name != LOCK_FILE_NAME)


def test_normal(tmp_path: Path, call_tool: CallTool) -> None:
    """新しいワークスペースを作る（正常系）。"""
    # 準備
    root = tmp_path / "new-workspace"
    # 実行
    created = call_tool("init", workspace=str(root), settings=SETTINGS)
    checked = call_tool("check", workspace=str(root))
    # 検証
    assert created.is_error is False
    assert (
        yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8")) == SETTINGS
    )
    assert _read_kind_yamls(root) == {
        "decisions.yaml": {"items": []},
        "tasks.yaml": {"items": []},
        "research.yaml": {"items": []},
        "docs.yaml": {"items": []},
        "terms.yaml": {"items": []},
        "notes.yaml": {"items": []},
        "logs.yaml": {"items": []},
    }
    # mindstella-version.ini があり、1 行目がプラグインの版である
    plugin_version = (REPO_ROOT / "plugins" / "mindstella" / "version.ini").read_text(
        encoding="utf-8"
    )
    version_file = (root / RECORD_DIR / "mindstella-version.ini").read_text(encoding="utf-8")
    assert version_file.splitlines()[0] == plugin_version.splitlines()[0]
    assert (root / RECORD_DIR / "docs").is_dir()
    assert (root / RECORD_DIR / "release").is_dir()
    # 直下に、設定・種類ごとの YAML・docs/・release/・版のファイルが無く、README.md がある
    assert _list_top(root) == [RECORD_DIR, "README.md"]
    # 直下の README.md に、このフォルダの起動・接続のコマンドとスキルの呼び方の一覧がある
    assert_readme_commands(root, (root / "README.md").read_text(encoding="utf-8"))
    # 全ての YAML がスキーマに合う（点検がスキーマ違反を出さない）
    assert checked.is_error is False
    assert checked.data == {"ok": True, "problems": []}


def test_error_when_workspace_exists(
    tmp_path: Path, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """既存のワークスペースのフォルダを渡すと、何も書き換えずに既にあるというエラーになる（異常系）。"""
    # 準備
    root = tmp_path / "workspace"
    call_tool("init", workspace=str(root), settings=SETTINGS)
    call_tool(
        "add",
        workspace=str(root),
        kind="decision",
        item={"title": "最初の問い", "status": "未決定", "options": [{"key": "A", "content": "案 A"}]},
    )
    before = snapshot_tree(root)
    top_before = _list_top(root)
    # 実行
    result = call_tool("init", workspace=str(root), settings=SETTINGS)
    # 検証
    assert result.is_error is True
    assert "既にワークスペースがあります" in result.text
    assert str(root) in result.text
    assert snapshot_tree(root) == before
    # 直下のファイルとフォルダの並びが、作成を呼ぶ前と同じである
    assert _list_top(root) == top_before


def test_normal_when_without_goal(tmp_path: Path, call_tool: CallTool) -> None:
    """ゴールを持たず、プレイブックを 2 つ並べた設定でワークスペースを作る（正常系）。"""
    # 準備
    root = tmp_path / "new-workspace"
    settings = {
        **{key: value for key, value in SETTINGS.items() if key != "goal"},
        "playbooks": ["壁打ち", "調査"],
    }
    # 実行
    created = call_tool("init", workspace=str(root), settings=settings)
    checked = call_tool("check", workspace=str(root))
    # 検証
    assert created.is_error is False
    created_settings = yaml.safe_load(
        (root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8")
    )
    assert "goal" not in created_settings
    assert created_settings["playbooks"] == ["壁打ち", "調査"]
    # 全ての YAML がスキーマに合う（点検がスキーマ違反を出さない）
    assert checked.is_error is False
    assert checked.data == {"ok": True, "problems": []}


def test_error_when_unmigrated_workspace_exists(
    tmp_path: Path, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """移す前の形のワークスペースのフォルダを渡すと、何も作らず移し替えを案内するエラーになる（異常系）。"""
    # 準備
    root = tmp_path / "old-workspace"
    root.mkdir()
    (root / "mindmap.yaml").write_text("field: システム開発\n", encoding="utf-8")
    (root / "decisions.yaml").write_text(
        "items:\n  - id: D-1\n    title: 前の版の検討事項\n", encoding="utf-8"
    )
    before = snapshot_tree(root)
    # 実行
    result = call_tool("init", workspace=str(root), settings=SETTINGS)
    # 検証
    assert result.is_error is True
    assert "既にワークスペースがあります" in result.text
    assert "/mindstella:upgrade" in result.text
    assert not (root / RECORD_DIR).exists()
    assert not (root / "README.md").exists()
    assert snapshot_tree(root) == before


def test_normal_when_readme_exists(tmp_path: Path, call_tool: CallTool) -> None:
    """利用者が書いた README.md だけを直下に持つフォルダに、README.md を書き換えずにワークスペースを作る（正常系）。"""
    # 準備
    root = tmp_path / "new-workspace"
    root.mkdir()
    (root / "README.md").write_text(USER_README, encoding="utf-8")
    # 実行
    created = call_tool("init", workspace=str(root), settings=SETTINGS)
    # 検証
    assert created.is_error is False
    assert (root / RECORD_DIR / "config.yaml").is_file()
    assert (root / "README.md").read_text(encoding="utf-8") == USER_README
