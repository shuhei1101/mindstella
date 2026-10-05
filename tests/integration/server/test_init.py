"""init（ワークスペースの作成）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from workspace_fixtures import REPO_ROOT

from .fixture_types import CallTool, LockDirs, MakeWorkspace, SnapshotTree

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
        name: yaml.safe_load((root / name).read_text(encoding="utf-8")) for name in KIND_YAML_FILES
    }


def test_normal(tmp_path: Path, call_tool: CallTool, valid_settings: dict[str, Any]) -> None:
    """設定を渡して空のワークスペースを作る（正常系）。"""
    # 準備
    root = tmp_path / "new-workspace"
    # 実行
    result = call_tool("init", workspace=str(root), settings=valid_settings)
    # 検証
    assert result.is_error is False
    assert yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8")) == valid_settings
    assert _read_kind_yamls(root) == {
        "decisions.yaml": {"items": []},
        "tasks.yaml": {"items": []},
        "research.yaml": {"items": []},
        "docs.yaml": {"items": []},
        "terms.yaml": {"items": []},
        "notes.yaml": {"items": []},
        "logs.yaml": {"items": []},
    }
    plugin_version = (REPO_ROOT / "plugins" / "mindstella" / "version.ini").read_text(
        encoding="utf-8"
    )
    version_file = (root / "mindstella-version.ini").read_text(encoding="utf-8")
    assert version_file.splitlines()[0] == plugin_version.splitlines()[0]
    assert (root / "docs").is_dir()
    assert (root / "release").is_dir()
    payload = result.data
    assert payload["workspace"] == str(root)
    assert set(payload["files"]) == {
        "config.yaml",
        *KIND_YAML_FILES,
        "mindstella-version.ini",
        "docs/",
        "release/",
    }


def test_normal_when_no_goal(
    tmp_path: Path, call_tool: CallTool, valid_settings: dict[str, Any]
) -> None:
    """ゴールと概要を持たず、プレイブックを 2 つ並べた設定で作る（正常系）。"""
    # 準備
    root = tmp_path / "new-workspace"
    settings = {
        **{
            key: value
            for key, value in valid_settings.items()
            if key not in ("goal", "description")
        },
        "playbooks": ["壁打ち", "調査"],
    }
    # 実行
    result = call_tool("init", workspace=str(root), settings=settings)
    # 検証
    assert result.is_error is False
    created = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
    assert "goal" not in created
    assert "description" not in created
    assert created["playbooks"] == ["壁打ち", "調査"]
    checked = call_tool("check", workspace=str(root))
    assert checked.data is not None
    assert checked.data["problems"] == []


def test_error_when_workspace_exists(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    valid_settings: dict[str, Any],
) -> None:
    """config.yaml があるフォルダには作らず、何も書き換えない（異常系）。"""
    # 準備
    root = make_workspace()
    before = snapshot_tree(root)
    # 実行
    result = call_tool("init", workspace=str(root), settings=valid_settings)
    # 検証
    assert result.is_error is True
    assert str(root) in result.text
    assert snapshot_tree(root) == before


def test_error_when_settings_mismatch(
    tmp_path: Path, call_tool: CallTool, valid_settings: dict[str, Any]
) -> None:
    """フェーズが無い設定では作らず、フォルダも作らない（異常系）。"""
    # 準備
    root = tmp_path / "new-workspace"
    del valid_settings["phases"]
    # 実行
    result = call_tool("init", workspace=str(root), settings=valid_settings)
    # 検証
    assert result.is_error is True
    assert "config.yaml" in result.text
    assert "phases" in result.text
    assert not root.exists()


def test_error_when_write_fails(
    tmp_path: Path,
    call_tool: CallTool,
    lock_dirs: LockDirs,
    valid_settings: dict[str, Any],
) -> None:
    """書き込めない場所には作らず、エラーの行を返す（異常系）。"""
    # 準備
    locked = tmp_path / "locked"
    locked.mkdir()
    lock_dirs(locked)
    root = locked / "new-workspace"
    # 実行
    result = call_tool("init", workspace=str(root), settings=valid_settings)
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert "Traceback" not in result.text
    assert not root.exists()


def test_error_when_old_settings_file_exists(
    tmp_path: Path,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    valid_settings: dict[str, Any],
) -> None:
    """mindmap.yaml だけがあるフォルダには作らず、前の版の記録を上書きしない（異常系）。"""
    # 準備
    root = tmp_path / "old-workspace"
    root.mkdir()
    (root / "mindmap.yaml").write_text("field: システム開発\n", encoding="utf-8")
    (root / "decisions.yaml").write_text(
        "items:\n  - id: D-1\n    title: 前の版の検討事項\n", encoding="utf-8"
    )
    before = snapshot_tree(root)
    # 実行
    result = call_tool("init", workspace=str(root), settings=valid_settings)
    # 検証
    assert result.is_error is True
    assert str(root) in result.text
    assert not (root / "config.yaml").exists()
    assert snapshot_tree(root) == before
