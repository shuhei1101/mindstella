"""migrator.py（手順の読み込みと、並べる・当てる・値を入れる・版を書く処理）の単体テスト。"""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from typing import Any

import pytest
import yaml

import migrator
from errors import (
    SchemaMismatchError,
    StepFailedError,
    StepsInvalidError,
    WorkspaceNewerError,
    WorkspaceNotFoundError,
    WriteFailedError,
)
from fixture_types import (
    FailingReplace,
    MakeItem,
    MakeLegacyWorkspace,
    MakeWorkspace,
    PatchPluginVersion,
    SnapshotTree,
)
from migration_helpers import STEPS_FILE, make_step, snapshot_mtimes
from migration_ops import DESTRUCTIVE_OPS
from migrator import NeededValue
from versions import Version
from workspace_fixtures import DEFAULT_TIMESTAMP, RECORD_DIR, write_yaml

# 版のファイル
VERSION_FILE = "mindstella-version.ini"

# v0.3.0 の手順の版
V030 = Version(0, 3, 0)

# v0.5.0 の手順の版（設定の分野をプレイブックの配列へ移す）
V050 = Version(0, 5, 0)

# v0.6.0 の手順の版（設定ファイルの名前を改める）
V060 = Version(0, 6, 0)

# 手順を当てる前に値が要るキー（v0.3.0 の set_default の ask）
SUMMARY_NEEDED = NeededValue(file="mindmap.yaml", key="summary", description="話し合いの題名")

# 設定ファイルの名前を改めた後に値が要るキー（v0.6.0 の手順で改めて記録のフォルダへ移した先の名前）
RENAMED_SUMMARY_NEEDED = NeededValue(
    file=".mindstella/config.yaml", key="summary", description="話し合いの題名"
)

# v0.6.0 の手順の並び（設定ファイルの名前を改め、直下の記録を .mindstella/ へ移し、前の版のファイルを消す）
V060_STEPS = [
    make_step("rename_file", {"from": "mindmap.yaml", "to": "config.yaml"}),
    make_step("rename_file", {"from": "decisions.yaml", "to": ".mindstella/decisions.yaml"}),
    make_step("rename_file", {"from": "docs.yaml", "to": ".mindstella/docs.yaml"}),
    make_step("move_dir", {"from": "docs", "to": ".mindstella/docs"}),
    make_step("move_dir", {"from": "release", "to": ".mindstella/release"}),
    make_step("rename_file", {"from": "config.yaml", "to": ".mindstella/config.yaml"}),
    make_step("delete", {"path": "preview.html"}),
]

# 手順が読めない docs.yaml（閉じていないフローの配列）
BROKEN_DOCS = "items: [\n"


def _read_items(root: Path, file_name: str) -> list[dict[str, Any]]:
    """ワークスペースの YAML を読んで、項目の並びを返す。"""
    data = yaml.safe_load((root / file_name).read_text(encoding="utf-8"))
    return data["items"]


def _keys_except(settings: dict[str, Any], key: str) -> list[str]:
    """key を除いた設定のキーの名前を、並びのまま返す。"""
    return [name for name in settings if name != key]


def _fail_restore(*args: Any, **kwargs: Any) -> None:
    """写しから戻せないときの restore_backup の代わり。"""
    raise OSError("戻せません")


def test_list_versions(tmp_path: Path) -> None:
    """版のフォルダだけを版の順に返す（正常系）。"""
    # 準備
    (tmp_path / "v0.10.0").mkdir()
    (tmp_path / "v0.3.0").mkdir()
    (tmp_path / "notes").mkdir()
    (tmp_path / "v0.4.0").write_text("フォルダではない\n", encoding="utf-8")
    # 実行
    result = migrator.list_versions(migrations_dir=tmp_path)
    # 検証
    assert result == [Version(0, 3, 0), Version(0, 10, 0)]


def test_load_steps() -> None:
    """v0.3.0 の手順を読む（正常系）。"""
    # 実行
    steps = migrator.load_steps(V030)
    # 検証
    assert [step.version for step in steps] == [V030, V030, V030]
    assert [(step.index, step.op, step.args) for step in steps] == [
        (
            1,
            "rename_key",
            {"file": "docs.yaml", "each_item": True, "from": "done", "to": "status"},
        ),
        (
            2,
            "map_values",
            {
                "file": "docs.yaml",
                "each_item": True,
                "key": "status",
                "map": {True: "完成", False: "下書き"},
            },
        ),
        (
            3,
            "set_default",
            {
                "file": "mindmap.yaml",
                "each_item": False,
                "key": "summary",
                "ask": "話し合いの題名",
            },
        ),
    ]


def test_load_steps_when_v0_5_0() -> None:
    """v0.5.0 の手順は field_to_playbooks を呼ぶ 1 つだけを読む（正常系）。"""
    # 実行
    steps = migrator.load_steps(V050)
    # 検証
    assert [(step.version, step.index, step.op, step.args) for step in steps] == [
        (V050, 1, "call", {"script": "field_to_playbooks"})
    ]


def test_load_steps_when_invalid(tmp_path: Path) -> None:
    """決まっていない操作は送る（異常系）。"""
    # 準備
    folder = tmp_path / "v0.3.0"
    folder.mkdir()
    (folder / STEPS_FILE).write_text(
        "steps:\n  - op: rename_table\n    from: a\n    to: b\n", encoding="utf-8"
    )
    # 実行・検証
    with pytest.raises(StepsInvalidError):
        migrator.load_steps(V030, migrations_dir=tmp_path)


def test_plan_migration(
    make_legacy_workspace: MakeLegacyWorkspace, patch_plugin_version: PatchPluginVersion
) -> None:
    """版を記録する前の形式に v0.3.0 の手順を並べる（正常系）。"""
    # 準備
    root = make_legacy_workspace(
        legacy_docs={"A-1": True}, without_summary=True, settings_file="mindmap.yaml", top=True
    )
    patch_plugin_version("v0.3.0")
    mtimes = snapshot_mtimes(root)
    # 実行
    report = migrator.plan_migration(root)
    # 検証
    assert report.workspace_version is None
    assert report.plugin_version == V030
    assert report.relation == "older"
    assert [(step.version, step.index, step.op) for step in report.steps] == [
        (V030, 1, "rename_key"),
        (V030, 2, "map_values"),
        (V030, 3, "set_default"),
    ]
    assert report.needs_values == [SUMMARY_NEEDED]
    assert snapshot_mtimes(root) == mtimes


def test_plan_migration_when_same(
    make_workspace: MakeWorkspace, patch_plugin_version: PatchPluginVersion
) -> None:
    """版が同じなら手順は空（正常系）。"""
    # 準備
    root = make_workspace(raw_files={VERSION_FILE: "v0.3.0\n"})
    patch_plugin_version("v0.3.0")
    # 実行
    report = migrator.plan_migration(root)
    # 検証
    assert report.relation == "same"
    assert report.steps == []
    assert report.needs_values == []


def test_plan_migration_when_newer(
    make_workspace: MakeWorkspace, patch_plugin_version: PatchPluginVersion
) -> None:
    """版が新しくても送らずに newer を返す（正常系）。"""
    # 準備
    root = make_workspace(raw_files={VERSION_FILE: "v99.0.0\n"})
    patch_plugin_version("v0.3.0")
    # 実行
    report = migrator.plan_migration(root)
    # 検証
    assert report.relation == "newer"
    assert report.steps == []


def test_plan_migration_when_workspace_missing(tmp_path: Path) -> None:
    """設定ファイルがどこにも無ければ送る（異常系）。"""
    # 実行・検証
    with pytest.raises(WorkspaceNotFoundError):
        migrator.plan_migration(tmp_path)


def test_plan_migration_when_settings_renamed(
    make_legacy_workspace: MakeLegacyWorkspace, patch_plugin_version: PatchPluginVersion
) -> None:
    """後の手順で名前を改めるファイルの値が要るキーは、改めた先の名前で返す（正常系）。"""
    # 準備
    root = make_legacy_workspace(without_summary=True, settings_file="mindmap.yaml", top=True)
    patch_plugin_version("v0.6.0")
    # 実行
    report = migrator.plan_migration(root)
    # 検証
    v060_steps = [step for step in report.steps if step.version == V060]
    assert report.steps[-1].version == V060
    assert (v060_steps[0].op, v060_steps[0].args) == (
        "rename_file",
        {"from": "mindmap.yaml", "to": "config.yaml"},
    )
    assert [step.op in DESTRUCTIVE_OPS for step in v060_steps] == [True] * len(v060_steps)
    assert report.needs_values == [RENAMED_SUMMARY_NEEDED]
    assert (root / "mindmap.yaml").exists()
    assert not (root / "config.yaml").exists()
    assert not (root / RECORD_DIR).exists()


def test_apply_migration(
    make_legacy_workspace: MakeLegacyWorkspace, patch_plugin_version: PatchPluginVersion
) -> None:
    """v0.3.0 の手順を当てて、値が要るキーを返す（正常系）。"""
    # 準備
    root = make_legacy_workspace(
        legacy_docs={"A-1": True, "A-2": False},
        without_summary=True,
        settings_file="mindmap.yaml",
        top=True,
    )
    patch_plugin_version("v0.3.0")
    # 実行
    report = migrator.apply_migration(root)
    # 検証
    items = _read_items(root, "docs.yaml")
    assert [item["status"] for item in items] == ["完成", "下書き"]
    assert all("done" not in item for item in items)
    assert [item["updated"] for item in items] == [DEFAULT_TIMESTAMP, DEFAULT_TIMESTAMP]
    assert report.needs_values == [SUMMARY_NEEDED]
    assert report.backup is not None
    assert report.backup.kind == "copy"
    assert not (root / VERSION_FILE).exists()


def test_apply_migration_when_already_current(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    patch_plugin_version: PatchPluginVersion,
) -> None:
    """今の形のワークスペースは何も変えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1", status="完成"))
    patch_plugin_version("v0.3.0")
    before = snapshot_tree(root)
    mtimes = snapshot_mtimes(root)
    # 実行
    report = migrator.apply_migration(root)
    # 検証
    assert report.needs_values == []
    assert snapshot_tree(root) == before
    assert snapshot_mtimes(root) == mtimes


def test_apply_migration_when_newer(
    make_workspace: MakeWorkspace, patch_plugin_version: PatchPluginVersion
) -> None:
    """版が新しければ写しも取らずに送る（異常系）。"""
    # 準備
    root = make_workspace(raw_files={VERSION_FILE: "v99.0.0\n"})
    patch_plugin_version("v0.3.0")
    # 実行・検証
    with pytest.raises(WorkspaceNewerError) as exc_info:
        migrator.apply_migration(root)
    assert "v99.0.0" in str(exc_info.value)
    assert "v0.3.0" in str(exc_info.value)
    assert list(root.parent.glob("workspace.before-*")) == []


def test_apply_migration_when_step_fails(
    make_workspace: MakeWorkspace,
    snapshot_tree: SnapshotTree,
    patch_plugin_version: PatchPluginVersion,
) -> None:
    """手順が失敗したら写しから戻して送る（異常系）。"""
    # 準備
    root = make_workspace(raw_files={"docs.yaml": BROKEN_DOCS}, top=True)
    patch_plugin_version("v0.3.0")
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(StepFailedError) as exc_info:
        migrator.apply_migration(root)
    assert str(exc_info.value).startswith("v0.3.0 の手順 1（rename_key）: ")
    assert snapshot_tree(root) == before


def test_apply_migration_when_restore_fails(
    make_workspace: MakeWorkspace,
    patch_plugin_version: PatchPluginVersion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """戻せなかったときは写しの場所を添える（異常系）。"""
    # 準備
    root = make_workspace(raw_files={"docs.yaml": BROKEN_DOCS}, top=True)
    patch_plugin_version("v0.3.0")
    # migrator モジュールの参照を、戻せない関数に差し替える
    monkeypatch.setattr(migrator, "restore_backup", _fail_restore)
    # 実行・検証
    with pytest.raises(StepFailedError) as exc_info:
        migrator.apply_migration(root)
    backup_dir = root.parent / "workspace.before-v0.3.0"
    assert f"写しから戻せませんでした。写しは {backup_dir} にあります" in exc_info.value.lines


def test_apply_migration_when_settings_renamed(
    make_legacy_workspace: MakeLegacyWorkspace, patch_plugin_version: PatchPluginVersion
) -> None:
    """前の版の手順を当ててから設定ファイルの名前を改めて記録を .mindstella/ へ移し、値が要るキーを移した先で返す（正常系）。"""
    # 準備
    root = make_legacy_workspace(
        legacy_docs={"A-1": True}, without_summary=True, settings_file="mindmap.yaml", top=True
    )
    legacy_settings = yaml.safe_load((root / "mindmap.yaml").read_text(encoding="utf-8"))
    legacy_settings["field"] = "システム開発"
    del legacy_settings["playbooks"]
    write_yaml(root / "mindmap.yaml", legacy_settings)
    # 前の版の画面と、直下のロックのファイル
    (root / "preview.html").write_text("<html></html>\n", encoding="utf-8")
    (root / ".mindstella.lock").write_text("", encoding="utf-8")
    patch_plugin_version("v0.6.0")
    # 実行
    report = migrator.apply_migration(root)
    # 検証
    records = root / RECORD_DIR
    settings = yaml.safe_load((records / "config.yaml").read_text(encoding="utf-8"))
    assert [path.name for path in root.iterdir()] == [".mindstella"]
    assert settings["playbooks"] == ["システム開発"]
    assert "field" not in settings
    assert _read_items(records, "docs.yaml")[0]["status"] == "完成"
    assert (records / "docs" / "A-1.md").read_text(encoding="utf-8") == "資料の本文\n"
    assert report.needs_values == [RENAMED_SUMMARY_NEEDED]
    assert report.backup is not None
    assert (Path(report.backup.ref) / "mindmap.yaml").exists()


def test_apply_migration_when_config_current(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    patch_plugin_version: PatchPluginVersion,
) -> None:
    """版のファイルを持たない今の形（.mindstella/config.yaml）にも全ての手順を当てて何も変えない（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1", status="完成"))
    patch_plugin_version("v0.6.0")
    before = snapshot_tree(root)
    mtimes = snapshot_mtimes(root)
    # 実行
    report = migrator.apply_migration(root)
    # 検証
    assert report.needs_values == []
    assert snapshot_tree(root) == before
    assert snapshot_mtimes(root) == mtimes
    # 直下に記録のフォルダのほかのものが作られていない
    assert [path.name for path in root.iterdir()] == [".mindstella"]


def test_set_values(
    make_legacy_workspace: MakeLegacyWorkspace, valid_settings: dict[str, Any]
) -> None:
    """題名を入れ、ほかのキーと並びを変えない（正常系）。"""
    # 準備
    root = make_legacy_workspace(without_summary=True)
    # 実行
    migrator.set_values(root, [(".mindstella/config.yaml", "summary", "題名")])
    # 検証
    settings = yaml.safe_load((root / RECORD_DIR / "config.yaml").read_text(encoding="utf-8"))
    assert settings["summary"] == "題名"
    assert _keys_except(settings, "summary") == _keys_except(valid_settings, "summary")
    assert settings["phases"] == valid_settings["phases"]
    assert not (root / RECORD_DIR / VERSION_FILE).exists()


def test_set_values_when_write_fails(
    make_legacy_workspace: MakeLegacyWorkspace,
    snapshot_tree: SnapshotTree,
    failing_replace: FailingReplace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """置き換えられなければ送る（異常系）。"""
    # 準備
    root = make_legacy_workspace(without_summary=True)
    before = snapshot_tree(root)
    # migrator モジュールの参照を、config.yaml への置き換えが失敗するものに差し替える
    monkeypatch.setattr(migrator.os, "replace", failing_replace("config.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        migrator.set_values(root, [(".mindstella/config.yaml", "summary", "題名")])
    assert snapshot_tree(root) == before
    assert list(root.rglob("*.tmp")) == []


def test_record_version(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """合うワークスペースに版を書く（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    recorded = migrator.record_version(root, to_version=V030)
    # 検証
    assert recorded == V030
    first_line = (root / RECORD_DIR / VERSION_FILE).read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "v0.3.0"


def test_record_version_when_schema_mismatch(
    make_legacy_workspace: MakeLegacyWorkspace,
) -> None:
    """題名が無ければ書かない（異常系）。"""
    # 準備
    root = make_legacy_workspace(without_summary=True)
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        migrator.record_version(root, to_version=V030)
    assert any(
        line.startswith("config.yaml: ") and "summary" in line for line in exc_info.value.lines
    )
    assert not (root / RECORD_DIR / VERSION_FILE).exists()


@pytest.mark.parametrize(
    ("files", "expectation"),
    [
        pytest.param([".mindstella/config.yaml"], nullcontext(), id="record_config_yaml_only"),
        pytest.param(["config.yaml"], nullcontext(), id="top_config_yaml_only"),
        pytest.param(["mindmap.yaml"], nullcontext(), id="legacy_mindmap_yaml_only"),
        pytest.param([], pytest.raises(WorkspaceNotFoundError), id="neither"),
    ],
)
def test_require_migratable(tmp_path: Path, files: list[str], expectation: Any) -> None:
    """どれかの設定ファイルがあれば通し、無ければ送る（正常系）。"""
    # 準備
    for file_name in files:
        (tmp_path / file_name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / file_name).write_text("", encoding="utf-8")
    # 実行・検証
    with expectation:
        migrator.require_migratable(tmp_path)


@pytest.mark.parametrize(
    ("file_name", "later_steps", "expected"),
    [
        pytest.param("mindmap.yaml", V060_STEPS, ".mindstella/config.yaml", id="renamed_later"),
        pytest.param("mindmap.yaml", [], "mindmap.yaml", id="no_later_steps"),
        pytest.param("docs.yaml", V060_STEPS, ".mindstella/docs.yaml", id="moved_later"),
    ],
)
def test_renamed_file(file_name: str, later_steps: list[Any], expected: str) -> None:
    """後の rename_file だけを辿る（正常系）。"""
    # 実行
    result = migrator.renamed_file(file_name, later_steps)
    # 検証
    assert result == expected
