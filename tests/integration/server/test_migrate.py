"""migrate（記録の形式の移行）の結合テスト。"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import yaml
from workspace_fixtures import LOCK_FILE_NAME

from .fixture_types import (
    CallTool,
    MakeItem,
    MakeLegacyWorkspace,
    MakeWorkspace,
    SnapshotTree,
)

# プラグインの版（plugins/mindstella/version.ini の 1 行目）
PLUGIN_VERSION = "v0.6.0"

# 版を記録する前の形式から並ぶ手順の版（v0.3.0・v0.5.0 の手順の次に v0.6.0 の手順が並ぶ）
STEP_VERSIONS = {"v0.3.0", "v0.5.0", "v0.6.0"}

# 手順 3（set_default）が失敗する、題名を足す手順の版
SUMMARY_STEP_VERSION = "v0.3.0"

# ワークスペースの版を持つファイルの名前
VERSION_FILE = "mindstella-version.ini"

# 渡す題名
SUMMARY = "要件出しのスキルを設計する"

# 前の版の設定ファイルの名前と、今の設定ファイルの名前
LEGACY_SETTINGS = "mindmap.yaml"
SETTINGS = "config.yaml"

# 読めない mindmap.yaml（閉じていないフローの配列）
BROKEN_SETTINGS = "field: [\n"

# 版が新しいワークスペースに書く版
NEWER_VERSION = "v99.0.0"


def _read_docs(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの資料の並びを読む。"""
    return yaml.safe_load((root / "docs.yaml").read_text(encoding="utf-8"))["items"]


def _mtimes(root: Path) -> dict[str, int]:
    """フォルダの下の全てのファイルの更新日時（ナノ秒）を、相対パス → 更新日時で返す。"""
    return {
        path.relative_to(root).as_posix(): path.stat().st_mtime_ns
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != LOCK_FILE_NAME
    }


def _git(cwd: Path, *args: str) -> str:
    """cwd で git を呼び、標準出力を返す。失敗したら例外にする。"""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout


def _init_git(path: Path) -> None:
    """フォルダを git の作業ツリーにし、コミットに要る作者をそのリポジトリの設定に置く。"""
    _git(path, "init", "-q")
    _git(path, "config", "user.name", "テスト")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "commit.gpgsign", "false")


def _create_current_workspace(
    tmp_path: Path, call_tool: CallTool, valid_settings: dict[str, Any]
) -> Path:
    """init で今の版のワークスペースを作り、そのフォルダを返す。"""
    root = tmp_path / "current"
    result = call_tool("init", workspace=str(root), settings=valid_settings)
    assert result.is_error is False
    return root


def test_normal_when_plan(
    make_legacy_workspace: MakeLegacyWorkspace,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """版を記録する前の形式に v0.3.0・v0.5.0・v0.6.0 の手順と値が要るキーを並べる（正常系）。"""
    # 準備
    root = make_legacy_workspace(
        legacy_docs={"A-1": True}, without_summary=True, settings_file=LEGACY_SETTINGS
    )
    before = snapshot_tree(root)
    mtimes = _mtimes(root)
    # 実行
    result = call_tool("migrate", workspace=str(root), plan=True)
    # 検証
    assert result.is_error is False
    payload = result.data
    assert payload["workspace_version"] is None
    assert payload["plugin_version"] == PLUGIN_VERSION
    assert payload["relation"] == "older"
    assert payload["steps"] != []
    assert {step["version"] for step in payload["steps"]} == STEP_VERSIONS
    # 破壊的な操作は v0.6.0 の設定ファイルの名前の改めだけ
    assert {step["version"] for step in payload["steps"] if step["destructive"]} == {"v0.6.0"}
    # 値が要るキーは、全ての手順を当てた後の名前（config.yaml）で返す
    assert {"file": "config.yaml", "key": "summary"} in [
        {"file": value["file"], "key": value["key"]} for value in payload["needs_values"]
    ]
    assert snapshot_tree(root) == before
    assert _mtimes(root) == mtimes


def test_normal_when_apply(make_legacy_workspace: MakeLegacyWorkspace, call_tool: CallTool) -> None:
    """写しを取って v0.3.0 の手順を当て、版のファイルは書かない（正常系）。"""
    # 準備
    root = make_legacy_workspace(
        legacy_docs={"A-1": True, "A-2": False}, without_summary=True, settings_file=LEGACY_SETTINGS
    )
    before = {item["id"]: item for item in _read_docs(root)}
    docs_before = (root / "docs.yaml").read_bytes()
    # 実行
    result = call_tool("migrate", workspace=str(root))
    # 検証
    assert result.is_error is False
    payload = result.data
    after = {item["id"]: item for item in _read_docs(root)}
    assert after["A-1"]["status"] == "完成"
    assert after["A-2"]["status"] == "下書き"
    assert "done" not in after["A-1"]
    assert "done" not in after["A-2"]
    assert after["A-1"]["updated"] == before["A-1"]["updated"]
    assert after["A-2"]["updated"] == before["A-2"]["updated"]
    assert {"file": "config.yaml", "key": "summary"} in [
        {"file": value["file"], "key": value["key"]} for value in payload["needs_values"]
    ]
    # 設定ファイルの名前が改まり、写しには前の名前のファイルが残る
    assert not (root / LEGACY_SETTINGS).exists()
    assert (root / SETTINGS).exists()
    assert payload["backup"]["kind"] == "copy"
    assert (Path(payload["backup"]["ref"]) / "docs.yaml").read_bytes() == docs_before
    assert (Path(payload["backup"]["ref"]) / LEGACY_SETTINGS).exists()
    assert not (root / VERSION_FILE).exists()


def test_normal_when_backup_git(
    tmp_path: Path,
    make_legacy_workspace: MakeLegacyWorkspace,
    call_tool: CallTool,
) -> None:
    """git の作業ツリーの中のワークスペースでは、ワークスペースのパスだけをコミットして写しにする（正常系）。"""
    # 準備
    root = make_legacy_workspace(
        legacy_docs={"A-1": True}, without_summary=True, settings_file=LEGACY_SETTINGS
    )
    # ワークスペースの親を作業ツリーにし、外のファイルはどちらもコミットしない
    _init_git(tmp_path)
    (tmp_path / "other.txt").write_text("外のファイル\n", encoding="utf-8")
    (tmp_path / "staged.txt").write_text("ステージしたファイル\n", encoding="utf-8")
    _git(tmp_path, "add", "staged.txt")
    # 実行
    result = call_tool("migrate", workspace=str(root))
    # 検証
    assert result.is_error is False
    backup = result.data["backup"]
    assert backup["kind"] == "git"
    committed = _git(tmp_path, "show", "--name-only", "--pretty=format:", backup["ref"]).split()
    assert committed != []
    assert all(name.startswith(f"{root.name}/") for name in committed)
    assert _git(tmp_path, "diff", "--cached", "--name-only").split() == ["staged.txt"]


def test_normal_when_set(make_legacy_workspace: MakeLegacyWorkspace, call_tool: CallTool) -> None:
    """`values` で値が要るキーに値を入れる（正常系）。"""
    # 準備
    root = make_legacy_workspace(without_summary=True)
    # 実行
    result = call_tool(
        "migrate",
        workspace=str(root),
        values=[{"file": "config.yaml", "key": "summary", "value": SUMMARY}],
    )
    # 検証
    assert result.is_error is False
    settings = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
    assert settings["summary"] == SUMMARY
    assert not (root / VERSION_FILE).exists()


def test_normal_when_record(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """点検に合うワークスペースで `record` が版のファイルを書く（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1", status="完成"))
    # 実行
    result = call_tool("migrate", workspace=str(root), record=True)
    # 検証
    assert result.is_error is False
    assert result.data["recorded"] == PLUGIN_VERSION
    first_line = (root / VERSION_FILE).read_text(encoding="utf-8").splitlines()[0]
    assert first_line == PLUGIN_VERSION


def test_normal_when_same(
    tmp_path: Path, call_tool: CallTool, valid_settings: dict[str, Any]
) -> None:
    """今の版のワークスペースでは並べる手順が無い（正常系）。"""
    # 準備
    root = _create_current_workspace(tmp_path, call_tool, valid_settings)
    # 実行
    result = call_tool("migrate", workspace=str(root), plan=True)
    # 検証
    assert result.is_error is False
    payload = result.data
    assert payload["relation"] == "same"
    assert payload["steps"] == []
    assert payload["needs_values"] == []


def test_normal_when_plan_newer(
    tmp_path: Path, call_tool: CallTool, valid_settings: dict[str, Any]
) -> None:
    """版が新しいワークスペースでも `plan` はエラーにせず newer を返す（正常系）。"""
    # 準備
    root = _create_current_workspace(tmp_path, call_tool, valid_settings)
    (root / VERSION_FILE).write_text(f"{NEWER_VERSION}\n", encoding="utf-8")
    # 実行
    result = call_tool("migrate", workspace=str(root), plan=True)
    # 検証
    assert result.is_error is False
    payload = result.data
    assert payload["workspace_version"] == NEWER_VERSION
    assert payload["relation"] == "newer"
    assert payload["steps"] == []


def test_normal_when_backup_ignored(
    tmp_path: Path,
    make_legacy_workspace: MakeLegacyWorkspace,
    call_tool: CallTool,
) -> None:
    """git の作業ツリーの中でも、ignore されたファイルを持つワークスペースは複製で写しを取る（正常系）。"""
    # 準備
    root = make_legacy_workspace(
        legacy_docs={"A-1": True}, without_summary=True, settings_file=LEGACY_SETTINGS
    )
    _init_git(tmp_path)
    (tmp_path / ".gitignore").write_text("*\n", encoding="utf-8")
    # 実行
    result = call_tool("migrate", workspace=str(root))
    # 検証
    assert result.is_error is False
    backup = result.data["backup"]
    assert backup["kind"] == "copy"
    assert (Path(backup["ref"]) / "docs.yaml").exists()
    assert _git(tmp_path, "rev-list", "--all", "--count").strip() == "0"


def test_normal_when_field_to_playbooks(
    make_workspace: MakeWorkspace, call_tool: CallTool, valid_settings: dict[str, Any]
) -> None:
    """v0.5.0 の手順で前の版の設定ファイル mindmap.yaml の field を playbooks の 1 件の配列へ移す（正常系）。"""
    # 準備
    # 前の版の形式: field を持ち playbooks を持たない設定（キーの並びは playbooks の位置に field を置く）
    settings = {
        ("field" if key == "playbooks" else key): ("システム開発" if key == "playbooks" else value)
        for key, value in {**valid_settings, "target_label": "システム"}.items()
    }
    root = make_workspace(settings=settings, settings_file=LEGACY_SETTINGS)
    (root / VERSION_FILE).write_text("v0.4.0\n", encoding="utf-8")
    # 実行
    result = call_tool("migrate", workspace=str(root), to_version="v0.5.0")
    # 検証
    assert result.is_error is False
    steps = result.data["steps"]
    assert [(step["version"], step["op"]) for step in steps] == [("v0.5.0", "call")]
    moved = yaml.safe_load((root / LEGACY_SETTINGS).read_text(encoding="utf-8"))
    assert "field" not in moved
    assert moved["playbooks"] == ["システム開発"]
    assert moved["target_label"] == "システム"
    assert (root / VERSION_FILE).read_text(encoding="utf-8") == "v0.4.0\n"


def test_normal_when_already_current(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """今の形（config.yaml）に版のファイルが無くても全ての手順を当てて、何も変えずに成功する（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1", status="完成"))
    before = snapshot_tree(root)
    mtimes = _mtimes(root)
    # 実行
    result = call_tool("migrate", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data["needs_values"] == []
    assert snapshot_tree(root) == before
    assert _mtimes(root) == mtimes
    assert not (root / LEGACY_SETTINGS).exists()


def test_normal_when_rename_settings_file(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """v0.6.0 の手順で mindmap.yaml を config.yaml に改める（正常系）。"""
    # 準備
    # 前の版（v0.5.0）の形式: config.yaml を持たず、題名を持つ mindmap.yaml を持つ
    root = make_workspace(settings_file=LEGACY_SETTINGS)
    (root / VERSION_FILE).write_text("v0.5.0\n", encoding="utf-8")
    legacy_bytes = (root / LEGACY_SETTINGS).read_bytes()
    # 実行
    result = call_tool("migrate", workspace=str(root))
    # 検証
    assert result.is_error is False
    payload = result.data
    assert [(step["version"], step["op"], step["destructive"]) for step in payload["steps"]] == [
        ("v0.6.0", "rename_file", True)
    ]
    assert not (root / LEGACY_SETTINGS).exists()
    assert (root / SETTINGS).read_bytes() == legacy_bytes
    assert payload["needs_values"] == []
    assert (root / VERSION_FILE).read_text(encoding="utf-8") == "v0.5.0\n"


def test_error_when_newer(
    tmp_path: Path,
    call_tool: CallTool,
    valid_settings: dict[str, Any],
    snapshot_tree: SnapshotTree,
) -> None:
    """版が新しいワークスペースには手順を当てない（異常系）。"""
    # 準備
    root = _create_current_workspace(tmp_path, call_tool, valid_settings)
    (root / VERSION_FILE).write_text(f"{NEWER_VERSION}\n", encoding="utf-8")
    before = snapshot_tree(root)
    # 実行
    result = call_tool("migrate", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert NEWER_VERSION in result.text
    assert PLUGIN_VERSION in result.text
    assert snapshot_tree(root) == before
    assert list(root.parent.glob(f"{root.name}.before-*")) == []


def test_error_when_step_fails(
    make_legacy_workspace: MakeLegacyWorkspace,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """手順 1・2 が docs.yaml を書き換えた後に手順 3 が失敗すると、写しから戻して終わる（異常系）。"""
    # 準備
    root = make_legacy_workspace(
        legacy_docs={"A-1": True, "A-2": False}, settings_file=LEGACY_SETTINGS
    )
    # 手順 3 が読む mindmap.yaml だけを読めない中身にする
    (root / "mindmap.yaml").write_text(BROKEN_SETTINGS, encoding="utf-8")
    before = snapshot_tree(root)
    # 実行
    result = call_tool("migrate", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert result.text.startswith(f"エラー: {SUMMARY_STEP_VERSION} の手順 3（set_default）: ")
    assert "mindmap.yaml" in result.text
    assert "Traceback" not in result.text
    # 手順 1・2 が書き換えた docs.yaml も含めて、全てのファイルが呼ぶ前と同じ
    assert snapshot_tree(root) == before
    assert not (root / VERSION_FILE).exists()


def test_error_when_schema_mismatch(
    make_legacy_workspace: MakeLegacyWorkspace,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """値が要るキーが無いままでは、版を書かない（異常系）。"""
    # 準備
    root = make_legacy_workspace(without_summary=True)
    before = snapshot_tree(root)
    # 実行
    result = call_tool("migrate", workspace=str(root), record=True)
    # 検証
    assert result.is_error is True
    assert any(
        line.startswith("config.yaml: ") and "summary" in line for line in result.text.splitlines()
    )
    assert snapshot_tree(root) == before
    assert not (root / VERSION_FILE).exists()


def test_error_when_workspace_not_found(
    tmp_path: Path, call_tool: CallTool, snapshot_tree: SnapshotTree
) -> None:
    """config.yaml も mindmap.yaml も無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("migrate", workspace=str(root), plan=True)
    # 検証
    assert result.is_error is True
    assert str(root) in result.text
    assert snapshot_tree(root) == {}
