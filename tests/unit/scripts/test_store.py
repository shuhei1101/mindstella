"""store.py（読み込み・検証・採番・書き込み）の単体テスト。"""

from __future__ import annotations

import dataclasses
import os
import re
import shutil
import stat
import subprocess
import sys
import threading
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

import migrator
import store
from errors import (
    ItemNotFoundError,
    SchemaMismatchError,
    WorkspaceExistsError,
    WorkspaceNotFoundError,
    WriteFailedError,
)
from fixture_types import FailingUnlink, MakeItem, MakeWorkspace, SnapshotTree
from workspace_fixtures import RECORD_DIR, write_yaml

# 壊れた YAML（閉じていないフローの配列）
BROKEN_YAML = "items: [unclosed"


def _prepare_target(target: Path, mode: int | None) -> None:
    """mode があれば、その権限を持つ置き換え先のファイルを作る（None なら作らない）。"""
    # 置き換え先が無い場合を作るときは何もしない
    if mode is None:
        return
    target.write_text("元の中身\n", encoding="utf-8")
    target.chmod(mode)


@pytest.fixture
def restore_umask() -> Iterator[None]:
    """テストの後で umask を元に戻す。"""
    original = os.umask(0)
    os.umask(original)
    yield
    os.umask(original)


def _fail_body_temp(
    real_write_temp: Callable[[Path, str], Path],
) -> Callable[[Path, str], Path]:
    """docs/ の本文の一時ファイルだけ書けない _write_temp の代わりを作る。"""

    def _write_temp(target: Path, text: str) -> Path:
        """置き換え先が docs/ の下なら OSError、それ以外は本物で書く。"""
        # 本文（docs/ の下）の一時ファイル
        if target.parent.name == "docs":
            raise OSError("書き込めません")
        # YAML の一時ファイルは本物で書く
        return real_write_temp(target, text)

    return _write_temp


def test_load_workspace(make_workspace, make_item) -> None:
    """設定と種類ごとの項目を読む（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    workspace = store.load_workspace(root)
    # 検証
    assert workspace.items == {
        "decision": [make_item("D-1")],
        "task": [],
        "research": [],
        "doc": [],
        "term": [],
        "note": [],
        "log": [],
    }
    assert workspace.load_problems == []


def test_load_workspace_when_yaml_broken(make_workspace) -> None:
    """読めない YAML を問題に記録して続ける（正常系）。"""
    # 準備
    root = make_workspace(raw_files={"tasks.yaml": BROKEN_YAML})
    # 実行
    workspace = store.load_workspace(root)
    # 検証
    assert workspace.items["task"] == []
    assert len(workspace.load_problems) == 1
    problem = workspace.load_problems[0]
    assert problem.file == "tasks.yaml"
    assert problem.kind == "schema"
    assert problem.key == "(全体)"


def test_load_workspace_when_settings_missing(tmp_path: Path) -> None:
    """config.yaml が無いフォルダは読まない（異常系）。"""
    # 実行・検証
    with pytest.raises(WorkspaceNotFoundError, match=re.escape(str(tmp_path))):
        store.load_workspace(tmp_path)


def test_load_workspace_when_top_level_list(make_workspace) -> None:
    """一番上が配列のファイルは項目を空にし、読んだ値は raw に残す（正常系）。"""
    # 準備
    root = make_workspace(raw_files={"decisions.yaml": "- id: D-1\n"})
    # 実行
    workspace = store.load_workspace(root)
    # 検証
    assert workspace.items["decision"] == []
    assert workspace.raw["decisions.yaml"] == [{"id": "D-1"}]
    assert workspace.load_problems == []


def test_load_workspace_when_settings_broken(make_workspace) -> None:
    """設定が YAML として読めなければ問題に記録して空にする（正常系）。"""
    # 準備
    root = make_workspace(raw_files={"config.yaml": BROKEN_YAML})
    # 実行
    workspace = store.load_workspace(root)
    # 検証
    assert workspace.settings == {}
    assert len(workspace.load_problems) == 1
    problem = workspace.load_problems[0]
    assert problem.file == "config.yaml"
    assert problem.key == "(全体)"
    assert "config.yaml" not in workspace.raw


def test_validate_workspace(make_workspace, make_item) -> None:
    """合うワークスペースは問題 0 件（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1")))
    # 実行
    problems = store.validate_workspace(workspace)
    # 検証
    assert problems == []


def test_validate_workspace_when_status_invalid(make_workspace, make_item) -> None:
    """共通でない種類固有の値の誤りを拾う（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("D-2", status="完了"))
    workspace = store.load_workspace(root)
    # 実行
    problems = store.validate_workspace(workspace)
    # 検証
    assert len(problems) == 1
    problem = problems[0]
    assert problem.kind == "schema"
    assert problem.file == "decisions.yaml"
    assert problem.key == "items[1].status"
    assert problem.id == "D-2"


def test_validate_workspace_when_common_key_invalid(make_workspace, make_item) -> None:
    """共通のスキーマ側で決めたキーの誤りも拾う（ファイルをまたぐ $ref）（正常系）。"""
    # 準備
    root = make_workspace(make_item("T-1", tags="データ"))
    workspace = store.load_workspace(root)
    # 実行
    problems = store.validate_workspace(workspace)
    # 検証
    assert len(problems) == 1
    assert problems[0].file == "tasks.yaml"
    assert problems[0].key == "items[0].tags"


def test_validate_workspace_when_load_problem(make_workspace) -> None:
    """読めなかったファイルの問題も含める（正常系）。"""
    # 準備
    root = make_workspace(raw_files={"notes.yaml": BROKEN_YAML})
    workspace = store.load_workspace(root)
    # 実行
    problems = store.validate_workspace(workspace)
    # 検証
    assert workspace.load_problems[0] in problems


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("- id: D-1\n", id="top_level_list"),
        pytest.param("items: []\nextra: 1\n", id="extra_key"),
    ],
)
def test_validate_workspace_when_top_level_invalid(make_workspace, text: str) -> None:
    """一番上の形の誤りを拾う（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(raw_files={"decisions.yaml": text}))
    # 実行
    problems = store.validate_workspace(workspace)
    # 検証
    assert len(problems) == 1
    assert problems[0].file == "decisions.yaml"
    assert problems[0].kind == "schema"
    assert problems[0].key == "(全体)"


# 前の版の形式の設定（題名の無い設定。`field` を持ち、`playbooks` を持たない）
LEGACY_SETTINGS: dict[str, Any] = {
    "field": "システム開発",
    "target_label": "システム",
    "phases": ["目的", "要件", "構成"],
    "targets": [{"name": "mindmap", "summary": "話し合いを記録するスキル"}],
    "categories": [{"name": "データ構造", "target": "mindmap", "summary": "YAML の種類とキー"}],
    "goal": {"phase": "構成", "summary": "作り始められる", "deliverables": []},
}


@pytest.mark.parametrize(
    ("file_name", "item_id", "kind", "settings", "expected"),
    [
        pytest.param("config.yaml", None, "schema", LEGACY_SETTINGS, True, id="settings"),
        pytest.param("docs.yaml", "A-1", "schema", LEGACY_SETTINGS, True, id="legacy_doc"),
        pytest.param("decisions.yaml", "D-1", "schema", LEGACY_SETTINGS, False, id="decision"),
        pytest.param("docs.yaml", "A-1", "broken_ref", LEGACY_SETTINGS, False, id="broken_ref"),
        pytest.param(
            "config.yaml",
            None,
            "schema",
            {"summary": "要件出しのスキルを設計する", **LEGACY_SETTINGS},
            True,
            id="settings_with_field",
        ),
    ],
)
def test_is_legacy_problem(
    make_legacy_workspace,
    make_item,
    file_name: str,
    item_id: str | None,
    kind: str,
    settings: dict[str, Any],
    expected: bool,
) -> None:
    """前の版の形式の問題を見分ける（正常系）。"""
    # 準備
    root = make_legacy_workspace(make_item("D-1", status="完了"), legacy_docs={"A-1": True})
    write_yaml(root / RECORD_DIR / "config.yaml", settings)
    workspace = store.load_workspace(root)
    problems = store.validate_workspace(workspace)
    problem = next(p for p in problems if p.file == file_name and p.id == item_id)
    # 種類だけを差し替えた問題にする
    problem = dataclasses.replace(problem, kind=kind)
    # 実行
    result = store.is_legacy_problem(problem, workspace)
    # 検証
    assert result is expected


@pytest.mark.parametrize(
    "schema_name",
    [
        pytest.param("settings.schema.json", id="settings"),
        pytest.param("decisions.schema.json", id="decisions"),
        pytest.param("tasks.schema.json", id="tasks"),
        pytest.param("research.schema.json", id="research"),
        pytest.param("docs.schema.json", id="docs"),
        pytest.param("terms.schema.json", id="terms"),
        pytest.param("notes.schema.json", id="notes"),
        pytest.param("logs.schema.json", id="logs"),
    ],
)
def test_load_validators(schema_name: str) -> None:
    """同梱のスキーマから 8 つの検証器を作り、各スキーマがそれ自体として正しい（正常系）。"""
    # 実行
    validators = store.load_validators()
    # 検証
    assert len(validators) == 8
    assert schema_name in validators
    Draft202012Validator.check_schema(validators[schema_name].schema)


def test_find_item(make_workspace, make_item) -> None:
    """ID の項目と位置を返す（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1"), make_item("D-2")))
    # 実行
    ref = store.find_item(workspace, "D-2")
    # 検証
    assert ref.kind == "decision"
    assert ref.index == 1
    assert ref.item == make_item("D-2")


def test_find_item_when_unknown_prefix(make_workspace, make_item) -> None:
    """種類に当たらない ID は見つからない（異常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1")))
    # 実行・検証
    with pytest.raises(ItemNotFoundError, match="X-1"):
        store.find_item(workspace, "X-1")


def test_find_item_when_id_missing(make_workspace, make_item) -> None:
    """種類に当たるが項目が無い ID は見つからない（異常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1")))
    # 実行・検証
    with pytest.raises(ItemNotFoundError, match="D-9"):
        store.find_item(workspace, "D-9")


def test_next_id(make_workspace, make_item) -> None:
    """間が空いていても最大 + 1 を振る（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1"), make_item("D-3")))
    # 実行
    item_id = store.next_id(workspace, "decision")
    # 検証
    assert item_id == "D-4"


def test_next_id_when_empty(make_workspace, make_item) -> None:
    """項目が無ければ 1 を振る（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1")))
    # 実行
    item_id = store.next_id(workspace, "task")
    # 検証
    assert item_id == "T-1"


def test_save_change(make_workspace, make_item, snapshot_tree) -> None:
    """項目の並びと本文を書き、一時ファイルを残さない（正常系）。"""
    # 準備
    root = make_workspace()
    workspace = store.load_workspace(root)
    item = make_item("D-1", body="D-1.md")
    change = store.Change(
        kind="decision",
        items=[item],
        body=store.BodyWrite(name="D-1.md", text="## 経緯\n"),
    )
    # 実行
    store.save_change(workspace, change)
    # 検証
    saved = yaml.safe_load((root / RECORD_DIR / "decisions.yaml").read_text(encoding="utf-8"))
    assert saved == {"items": [item]}
    assert (root / RECORD_DIR / "docs" / "D-1.md").read_text(encoding="utf-8") == "## 経緯\n"
    assert list(root.rglob("*.tmp")) == []


def test_save_change_when_schema_mismatch(make_workspace, make_item, snapshot_tree) -> None:
    """スキーマに合わない変更は書かない（異常系）。"""
    # 準備
    root = make_workspace()
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    change = store.Change(
        kind="decision",
        items=[make_item("D-1", body="D-1.md", status="完了")],
        body=store.BodyWrite(name="D-1.md", text="本文\n"),
    )
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        store.save_change(workspace, change)
    assert exc_info.value.lines[0].startswith("decisions.yaml: items[0].status:")
    assert snapshot_tree(root) == before


def test_save_change_when_temp_write_fails(
    make_workspace, make_item, snapshot_tree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """一時ファイルを書けなければ何も置き換えない（異常系）。"""
    # 準備
    root = make_workspace()
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    change = store.Change(
        kind="decision",
        items=[make_item("D-1", body="D-1.md")],
        body=store.BodyWrite(name="D-1.md", text="本文\n"),
    )
    # store モジュールの参照を、本文の一時ファイルだけ書けないものに差し替える
    monkeypatch.setattr(store, "_write_temp", _fail_body_temp(store._write_temp))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        store.save_change(workspace, change)
    assert snapshot_tree(root) == before
    assert list(root.rglob("*.tmp")) == []


def test_save_change_when_yaml_replace_fails_with_previous_body(
    make_workspace,
    make_item,
    snapshot_tree,
    failing_replace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """YAML の置き換えに失敗したら前の本文に戻す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", body="D-1.md"), bodies={"D-1.md": "前の本文\n"})
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    change = store.Change(
        kind="decision",
        items=[make_item("D-1", body="D-1.md", answer="a")],
        body=store.BodyWrite(name="D-1.md", text="新しい本文\n"),
    )
    # store モジュールの参照を、decisions.yaml への置き換えだけ失敗するものに差し替える
    monkeypatch.setattr(store.os, "replace", failing_replace("decisions.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError, match=r"decisions\.yaml"):
        store.save_change(workspace, change)
    assert snapshot_tree(root) == before
    assert list(root.rglob("*.tmp")) == []


def test_save_change_when_yaml_replace_fails_without_previous_body(
    make_workspace,
    make_item,
    snapshot_tree,
    failing_replace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """YAML の置き換えに失敗したら新しく書いた本文を消す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    change = store.Change(
        kind="decision",
        items=[make_item("D-1", body="D-1.md")],
        body=store.BodyWrite(name="D-1.md", text="新しい本文\n"),
    )
    # store モジュールの参照を、decisions.yaml への置き換えだけ失敗するものに差し替える
    monkeypatch.setattr(store.os, "replace", failing_replace("decisions.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        store.save_change(workspace, change)
    assert not (root / RECORD_DIR / "docs" / "D-1.md").exists()
    assert snapshot_tree(root) == before
    assert list(root.rglob("*.tmp")) == []


def test_save_change_when_changes_replace_fails(
    make_workspace,
    make_item,
    snapshot_tree,
    failing_replace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """まとまりの置き換えに失敗したら項目と本文を戻す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", body="D-1.md"), bodies={"D-1.md": "前の本文\n"})
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    change = store.Change(
        kind="decision",
        items=[make_item("D-1", body="D-1.md", answer="a")],
        body=store.BodyWrite(name="D-1.md", text="新しい本文\n"),
        changes={"last_seq": 1, "sets": [], "pending": {"added": [], "changed": ["D-1"]}},
    )
    # store モジュールの参照を、changes.yaml への置き換えだけ失敗するものに差し替える
    monkeypatch.setattr(store.os, "replace", failing_replace("changes.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError, match=r"changes\.yaml"):
        store.save_change(workspace, change)
    assert snapshot_tree(root) == before
    assert list(root.rglob("*.tmp")) == []


def test_save_batch(make_workspace, make_item) -> None:
    """複数の種類と本文とまとまりを書き、一時ファイルを残さない（正常系）。"""
    # 準備
    root = make_workspace()
    workspace = store.load_workspace(root)
    decision = make_item("D-1", body="D-1.md")
    task = make_item("T-1")
    changes = {"last_seq": 2, "sets": [], "pending": {"added": ["D-1", "T-1"], "changed": []}}
    change = store.BatchChange(
        items={"decision": [decision], "task": [task]},
        bodies=[store.BodyWrite(name="D-1.md", text="## 経緯\n")],
        changes=changes,
    )
    # 実行
    store.save_batch(workspace, change)
    # 検証
    records = root / RECORD_DIR
    assert yaml.safe_load((records / "decisions.yaml").read_text(encoding="utf-8")) == {
        "items": [decision]
    }
    assert yaml.safe_load((records / "tasks.yaml").read_text(encoding="utf-8")) == {"items": [task]}
    assert (records / "docs" / "D-1.md").read_text(encoding="utf-8") == "## 経緯\n"
    assert yaml.safe_load((records / "changes.yaml").read_text(encoding="utf-8")) == changes
    assert list(root.rglob("*.tmp")) == []


def test_save_batch_when_schema_mismatch(make_workspace, make_item, snapshot_tree) -> None:
    """1 つの種類でもスキーマに合わなければ何も書かない（異常系）。"""
    # 準備
    root = make_workspace()
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    change = store.BatchChange(
        items={
            "task": [make_item("T-1")],
            "decision": [make_item("D-1", status="完了")],
        }
    )
    # 実行・検証
    with pytest.raises(SchemaMismatchError):
        store.save_batch(workspace, change)
    assert snapshot_tree(root) == before


def test_save_batch_when_replace_fails(
    make_workspace,
    make_item,
    snapshot_tree,
    failing_replace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """途中の置き換えに失敗したら、置き換えたファイルを戻す（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", body="D-1.md"),
        make_item("T-1"),
        bodies={"D-1.md": "前の本文\n"},
    )
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    change = store.BatchChange(
        items={
            "decision": [make_item("D-1", body="D-1.md", answer="a")],
            "task": [make_item("T-1", result="r")],
        },
        bodies=[store.BodyWrite(name="D-1.md", text="新しい本文\n")],
    )
    # store モジュールの参照を、tasks.yaml への置き換えだけ失敗するものに差し替える
    monkeypatch.setattr(store.os, "replace", failing_replace("tasks.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError, match=r"tasks\.yaml"):
        store.save_batch(workspace, change)
    assert snapshot_tree(root) == before
    assert list(root.rglob("*.tmp")) == []


def test_create_workspace(tmp_path: Path, valid_settings: dict[str, Any]) -> None:
    """まだ無いフォルダにワークスペースを作る（正常系）。"""
    # 準備
    root = tmp_path / "ws"
    # 実行
    files = store.create_workspace(root, valid_settings, version="v0.3.0")
    # 検証
    assert len(files) == 12
    assert set(files) == {
        "README.md",
        ".mindstella/config.yaml",
        ".mindstella/decisions.yaml",
        ".mindstella/tasks.yaml",
        ".mindstella/research.yaml",
        ".mindstella/docs.yaml",
        ".mindstella/terms.yaml",
        ".mindstella/notes.yaml",
        ".mindstella/logs.yaml",
        ".mindstella/mindstella-version.ini",
        ".mindstella/docs/",
        ".mindstella/release/",
    }
    records = root / RECORD_DIR
    assert yaml.safe_load((records / "config.yaml").read_text(encoding="utf-8")) == valid_settings
    assert (records / "mindstella-version.ini").read_text(encoding="utf-8") == "v0.3.0\n"
    # 直下には記録のフォルダと、自動で書いた印で始まる README だけが並ぶ
    assert sorted(path.name for path in root.iterdir()) == [".mindstella", "README.md"]
    first_line = (root / "README.md").read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "<!-- mindstella:readme -->"


# 前の版の設定ファイル（mindmap.yaml）と検討事項 D-1 だけを持つフォルダの中身
LEGACY_WORKSPACE_FILES = {
    "mindmap.yaml": "field: システム開発\ntarget_label: システム\n",
    "decisions.yaml": "items:\n  - id: D-1\n    title: 前の版の検討事項\n",
}


@pytest.mark.parametrize(
    ("files", "expects_hint"),
    [
        pytest.param({".mindstella/config.yaml": "summary: 題名\n"}, False, id="record_config"),
        pytest.param({"config.yaml": "summary: 題名\n"}, True, id="top_config_yaml"),
        pytest.param(LEGACY_WORKSPACE_FILES, True, id="legacy_mindmap_yaml"),
    ],
)
def test_create_workspace_when_exists(
    tmp_path: Path,
    snapshot_tree: SnapshotTree,
    valid_settings: dict[str, Any],
    files: dict[str, str],
    expects_hint: bool,
) -> None:
    """.mindstella/config.yaml か、直下の config.yaml・mindmap.yaml があるフォルダには作らない（異常系）。"""
    # 準備
    root = tmp_path / "ws"
    root.mkdir()
    for file_name, text in files.items():
        (root / file_name).parent.mkdir(parents=True, exist_ok=True)
        (root / file_name).write_text(text, encoding="utf-8")
    before = snapshot_tree(root)
    entries_before = sorted(path.name for path in root.iterdir())
    # 実行・検証
    with pytest.raises(WorkspaceExistsError, match=re.escape(str(root))) as exc_info:
        store.create_workspace(root, valid_settings, version="v0.3.0")
    assert snapshot_tree(root) == before
    assert sorted(path.name for path in root.iterdir()) == entries_before
    # 直下の前の版の設定ファイルには、移し替えの案内を続ける
    assert (f"/mindstella:upgrade {root}" in "".join(exc_info.value.lines)) is expects_hint


def test_create_workspace_when_settings_invalid(
    tmp_path: Path, valid_settings: dict[str, Any]
) -> None:
    """設定がスキーマに合わなければフォルダも作らない（異常系）。"""
    # 準備
    root = tmp_path / "ws"
    del valid_settings["phases"]
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        store.create_workspace(root, valid_settings, version="v0.3.0")
    assert "config.yaml" in str(exc_info.value.lines)
    assert "phases" in str(exc_info.value.lines)
    assert not root.exists()


def test_create_workspace_when_write_fails(
    tmp_path: Path, valid_settings: dict[str, Any], failing_write_text
) -> None:
    """途中で書けなくなったら作ったものを消す（異常系）。"""
    # 準備
    root = tmp_path / "ws"
    # 7 種類の YAML のうち最後の logs.yaml だけ書けないようにする
    failing_write_text("logs.yaml")
    # 実行・検証
    with pytest.raises(WriteFailedError):
        store.create_workspace(root, valid_settings, version="v0.3.0")
    assert not root.exists()


def test_create_workspace_when_user_readme_exists(
    tmp_path: Path, valid_settings: dict[str, Any]
) -> None:
    """利用者の README があるフォルダには README を書かずに作る（正常系）。"""
    # 準備
    (tmp_path / "README.md").write_text("# 家計簿アプリの話し合い\n", encoding="utf-8")
    before = (tmp_path / "README.md").read_bytes()
    # 実行
    files = store.create_workspace(tmp_path, valid_settings, version="v0.3.0")
    # 検証
    assert "README.md" not in files
    assert (tmp_path / RECORD_DIR / "config.yaml").is_file()
    assert (tmp_path / "README.md").read_bytes() == before


def test_create_workspace_when_readme_write_fails(
    tmp_path: Path, valid_settings: dict[str, Any]
) -> None:
    """README を書けなければ作ったものを消す（異常系）。"""
    # 準備
    (tmp_path / "README.md").mkdir()
    # 実行・検証
    with pytest.raises(WriteFailedError):
        store.create_workspace(tmp_path, valid_settings, version="v0.3.0")
    assert not (tmp_path / RECORD_DIR).exists()
    assert (tmp_path / "README.md").is_dir()


def test_clear_release(make_workspace: MakeWorkspace) -> None:
    """release/ の中のファイルとフォルダを消し、消したものを名前の順に返す（正常系）。"""
    # 準備
    root = make_workspace()
    release = root / RECORD_DIR / "release"
    (release / "古い資料.md").write_text("古い\n", encoding="utf-8")
    (release / "図").mkdir()
    (release / "図" / "構成.md").write_text("図\n", encoding="utf-8")
    settings_before = (root / RECORD_DIR / "config.yaml").read_bytes()
    # 実行
    removed = store.clear_release(root)
    # 検証
    assert removed == ["古い資料.md", "図/"]
    assert release.is_dir()
    assert list(release.iterdir()) == []
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == settings_before


def test_clear_release_when_release_dir_missing(
    make_workspace: MakeWorkspace, snapshot_tree: SnapshotTree
) -> None:
    """release/ が無ければ空の release/ を作り、前の版の handoff/ は触らない（正常系）。"""
    # 準備
    root = make_workspace()
    shutil.rmtree(root / RECORD_DIR / "release")
    (root / "handoff").mkdir()
    (root / "handoff" / "資料.md").write_text("前の版の資料\n", encoding="utf-8")
    handoff_before = snapshot_tree(root / "handoff")
    # 実行
    removed = store.clear_release(root)
    # 検証
    assert removed == []
    assert (root / RECORD_DIR / "release").is_dir()
    assert list((root / RECORD_DIR / "release").iterdir()) == []
    assert snapshot_tree(root / "handoff") == handoff_before


def test_clear_release_when_workspace_missing(tmp_path: Path) -> None:
    """.mindstella/config.yaml が無ければ何も消さない（異常系）。"""
    # 準備
    release = tmp_path / RECORD_DIR / "release"
    release.mkdir(parents=True)
    (release / "資料.md").write_text("資料\n", encoding="utf-8")
    # 実行・検証
    with pytest.raises(WorkspaceNotFoundError, match=re.escape(str(tmp_path))):
        store.clear_release(tmp_path)
    assert (release / "資料.md").read_text(encoding="utf-8") == "資料\n"


def test_clear_release_when_remove_fails(
    make_workspace: MakeWorkspace, failing_unlink: FailingUnlink
) -> None:
    """消せないものに当たった時点で止まり、それまでに消したものは戻さない（異常系）。"""
    # 準備
    root = make_workspace()
    release = root / RECORD_DIR / "release"
    (release / "一.md").write_text("一\n", encoding="utf-8")
    (release / "二.md").write_text("二\n", encoding="utf-8")
    # 名前の順に消すので、一.md を消した後に二.md で止まる
    failing_unlink("二.md")
    # 実行・検証
    with pytest.raises(WriteFailedError, match=re.escape(str(release / "二.md"))):
        store.clear_release(root)
    assert (release / "二.md").exists()
    assert not (release / "一.md").exists()


def test_read_body(make_workspace) -> None:
    """ある本文を読む（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(bodies={"D-1.md": "本文\n"}))
    # 実行
    text = store.read_body(workspace, "D-1.md")
    # 検証
    assert text == "本文\n"


def test_read_body_when_missing(make_workspace) -> None:
    """無い本文は None を返す（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace())
    # 実行
    text = store.read_body(workspace, "D-9.md")
    # 検証
    assert text is None


def test_read_body_when_outside(make_workspace) -> None:
    """docs/ の外を指す名前は読まない（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace())
    # 実行
    text = store.read_body(workspace, "../config.yaml")
    # 検証
    assert text is None


def test_dump_yaml() -> None:
    """日本語とキーの並びを保つ（正常系）。"""
    # 実行
    text = store.dump_yaml({"title": "問い", "id": "D-1"})
    # 検証
    assert text == "title: 問い\nid: D-1\n"


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        pytest.param(["items", 0, "options", 1, "key"], "items[0].options[1].key", id="nested"),
        pytest.param([], "(全体)", id="empty"),
    ],
)
def test_format_path(path: list[str | int], expected: str) -> None:
    """キーと添字をつなぐ（正常系）。"""
    # 実行
    text = store._format_path(path)
    # 検証
    assert text == expected


@pytest.mark.parametrize(
    "broken_text",
    [
        pytest.param("- id: D-1\n", id="top_level_list"),
        pytest.param("items:\n- id: D-1\nextra: 1\n", id="extra_key"),
        pytest.param("items:\n- id: D-1\n- 文字列の要素\n", id="string_element"),
        pytest.param(BROKEN_YAML, id="yaml_unreadable"),
    ],
)
def test_save_change_when_file_shape_broken(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    broken_text: str,
) -> None:
    """書き戻すと中身を失うファイルには書かない（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("D-2"),
        raw_files={"decisions.yaml": broken_text},
    )
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    change = store.Change(kind="decision", items=[make_item("D-1")])
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        store.save_change(workspace, change)
    assert all(line.startswith("decisions.yaml: ") for line in exc_info.value.lines)
    assert len(exc_info.value.lines) >= 1
    assert snapshot_tree(root) == before


def test_save_change_when_item_value_fixed(
    make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """項目の中の合わない値は、それを直す変更なら書ける（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", status="完了"))
    workspace = store.load_workspace(root)
    change = store.Change(kind="decision", items=[make_item("D-1", status="未決定")])
    # 実行
    store.save_change(workspace, change)
    # 検証
    saved = yaml.safe_load((root / RECORD_DIR / "decisions.yaml").read_text(encoding="utf-8"))
    assert saved["items"][0]["status"] == "未決定"


@pytest.mark.skipif(sys.platform == "win32", reason="権限のビットは Windows では効かない")
@pytest.mark.parametrize(
    ("target_mode", "expected_mode"),
    [
        pytest.param(0o640, 0o640, id="copy_from_target"),
        pytest.param(None, 0o644, id="from_umask"),
    ],
)
def test_write_temp_when_mode(
    tmp_path: Path,
    restore_umask: None,
    target_mode: int | None,
    expected_mode: int,
) -> None:
    """置き換え先の権限を一時ファイルに写す（正常系）。"""
    # 準備
    target = tmp_path / "target.yaml"
    _prepare_target(target, target_mode)
    os.umask(0o022)
    # 実行
    temp = store._write_temp(target, "新しい中身\n")
    # 検証
    assert stat.S_IMODE(temp.stat().st_mode) == expected_mode


def _try_lock_in_child(lock_file: Path) -> str:
    """別のプロセスで lock_file に flock(LOCK_EX | LOCK_NB) を試し、取れたら acquired、取れなければ blocked を返す。"""
    code = (
        "import fcntl, sys\n"
        "stream = open(sys.argv[1], 'a')\n"
        "try:\n"
        "    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
        "    print('acquired')\n"
        "except BlockingIOError:\n"
        "    print('blocked')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(lock_file)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_workspace_lock(tmp_path: Path) -> None:
    """鍵とロックを持ち、抜けたら放す（正常系）。"""
    # 準備
    (tmp_path / RECORD_DIR).mkdir()
    (tmp_path / RECORD_DIR / "config.yaml").write_text("", encoding="utf-8")
    process_lock = threading.Lock()
    lock_file = tmp_path / RECORD_DIR / ".mindstella.lock"
    # 実行
    with store.workspace_lock(tmp_path, process_lock):
        inside_child = _try_lock_in_child(lock_file)
        inside_locked = process_lock.locked()
    # 検証
    assert inside_child == "blocked"
    assert inside_locked is True
    assert _try_lock_in_child(lock_file) == "acquired"
    assert process_lock.locked() is False


def test_workspace_lock_when_raises(tmp_path: Path) -> None:
    """中の処理が例外でも放す（正常系）。"""
    # 準備
    (tmp_path / RECORD_DIR).mkdir()
    (tmp_path / RECORD_DIR / "config.yaml").write_text("", encoding="utf-8")
    process_lock = threading.Lock()
    # 実行・検証
    with pytest.raises(ValueError, match="中で失敗"), store.workspace_lock(tmp_path, process_lock):
        raise ValueError("中で失敗")
    assert process_lock.locked() is False
    assert _try_lock_in_child(tmp_path / RECORD_DIR / ".mindstella.lock") == "acquired"


def test_workspace_lock_when_folder_missing(tmp_path: Path) -> None:
    """まだ無いフォルダも作って取る（正常系）。"""
    # 準備
    root = tmp_path / "ws"
    # 実行
    with store.workspace_lock(root, threading.Lock(), create=True):
        pass
    # 検証
    assert (root / RECORD_DIR / ".mindstella.lock").exists()


@pytest.mark.parametrize(
    "relative",
    [
        pytest.param(Path(), id="empty_folder"),
        pytest.param(Path("typo") / "ws", id="missing_folder"),
    ],
)
def test_workspace_lock_when_not_workspace(tmp_path: Path, relative: Path) -> None:
    """ワークスペースでないフォルダでは何も作らずに止める（異常系）。"""
    # 準備
    root = tmp_path / relative
    process_lock = threading.Lock()
    # 実行・検証
    with (
        pytest.raises(WorkspaceNotFoundError, match="ワークスペースがありません"),
        store.workspace_lock(root, process_lock),
    ):
        pass
    assert process_lock.locked() is False
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("require", "expectation", "lock_file_exists"),
    [
        pytest.param(migrator.require_migratable, nullcontext(), True, id="require_migratable"),
        pytest.param(
            store.require_workspace,
            pytest.raises(WorkspaceNotFoundError, match="ワークスペースがありません"),
            False,
            id="default",
        ),
    ],
)
def test_workspace_lock_when_require_given(
    tmp_path: Path,
    require: Callable[[Path], None],
    expectation: AbstractContextManager[Any],
    lock_file_exists: bool,
) -> None:
    """渡した確かめの関数でワークスペースを確かめる（正常系）。"""
    # 準備
    (tmp_path / "mindmap.yaml").write_text("", encoding="utf-8")
    process_lock = threading.Lock()
    # 実行・検証
    with expectation, store.workspace_lock(tmp_path, process_lock, require=require):
        pass
    assert (tmp_path / ".mindstella.lock").exists() is lock_file_exists
    assert process_lock.locked() is False


def test_require_workspace(make_workspace: MakeWorkspace) -> None:
    """.mindstella/config.yaml があれば通す（正常系）。"""
    # 準備
    root = make_workspace()
    # 実行・検証（例外にならない）
    store.require_workspace(root)


@pytest.mark.parametrize(
    ("files", "expects_hint"),
    [
        pytest.param({}, False, id="empty_folder"),
        pytest.param({"mindmap.yaml": "field: システム開発\n"}, True, id="legacy_settings_only"),
        pytest.param({"config.yaml": "summary: 題名\n"}, True, id="top_config_only"),
    ],
)
def test_require_workspace_when_missing(
    tmp_path: Path, files: dict[str, str], expects_hint: bool
) -> None:
    """無いフォルダと、前の版の形のフォルダを分けて送る（異常系）。"""
    # 準備
    for file_name, text in files.items():
        (tmp_path / file_name).write_text(text, encoding="utf-8")
    # 実行・検証
    with pytest.raises(WorkspaceNotFoundError, match=re.escape(str(tmp_path))) as exc_info:
        store.require_workspace(tmp_path)
    assert (len(exc_info.value.lines) == 1) is expects_hint
    assert (f"/mindstella:upgrade {tmp_path}" in "".join(exc_info.value.lines)) is expects_hint


def test_check_settings(make_workspace: MakeWorkspace, valid_settings: dict[str, Any]) -> None:
    """合う設定は問題 0 件で、display も読む（正常系）。"""
    # 準備
    display = {"network_look": "starlight", "visible_kinds": ["decisions"]}
    root = make_workspace(settings={**valid_settings, "display": display})
    # 実行
    settings, problems = store.check_settings(root)
    # 検証
    assert settings["display"]["network_look"] == "starlight"
    assert problems == []


@pytest.mark.parametrize(
    ("display", "raw_files", "expected_key"),
    [
        pytest.param({"network_look": "rainbow"}, {}, "display.network_look", id="unknown_look"),
        pytest.param(
            {"visible_kinds": ["decisions", "decisions"]},
            {},
            "display.visible_kinds",
            id="duplicate_kinds",
        ),
        pytest.param({}, {"config.yaml": BROKEN_YAML}, "(全体)", id="broken_yaml"),
    ],
)
def test_check_settings_when_invalid(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    display: dict[str, Any],
    raw_files: dict[str, str],
    expected_key: str,
) -> None:
    """合わない設定と読めない設定を問題にする（正常系）。"""
    # 準備
    root = make_workspace(settings={**valid_settings, "display": display}, raw_files=raw_files)
    # 実行
    _, problems = store.check_settings(root)
    # 検証
    assert expected_key in [problem.key for problem in problems]
    assert {problem.file for problem in problems} == {"config.yaml"}


@pytest.mark.parametrize(
    "items",
    [
        pytest.param(
            [{"id": "D-1", "status": "未決定", "options": [{"key": "A", "content": "案 A"}]}],
            id="undecided_with_options",
        ),
        pytest.param(
            [
                {
                    "id": "D-1",
                    "status": "決定済み",
                    "options": [
                        {"key": "A", "content": "案 A", "adopted": True},
                        {"key": "B", "content": "案 B"},
                    ],
                }
            ],
            id="decided_with_adopted",
        ),
        pytest.param(
            [
                {
                    "id": "D-1",
                    "status": "要見直し",
                    "options": [{"key": "A", "content": "案 A", "adopted": True}],
                }
            ],
            id="review_with_adopted",
        ),
        pytest.param(
            [
                {"id": "D-1", "status": "未整理"},
                {"id": "D-2", "status": "対象外", "options": []},
                {"id": "D-3", "status": "取り下げ"},
            ],
            id="optional_statuses_without_options",
        ),
    ],
)
def test_check_decision_rules(items: list[dict[str, Any]]) -> None:
    """決まりに合う検討事項は問題 0 件（正常系）。"""
    # 実行
    problems = store.check_decision_rules({"items": items})
    # 検証
    assert problems == []


def test_check_decision_rules_when_mismatch() -> None:
    """合わない決まりを 1 件ずつ拾う（正常系）。"""
    # 準備
    decisions = {
        "items": [
            {"id": "D-1", "status": "未決定", "options": []},
            {
                "id": "D-2",
                "status": "決定済み",
                "options": [{"key": "A", "content": "案 A"}, {"key": "B", "content": "案 B"}],
            },
            {
                "id": "D-3",
                "status": "未決定",
                "options": [{"key": "A", "content": "案 A", "adopted": True}],
            },
        ]
    }
    # 実行
    problems = store.check_decision_rules(decisions)
    # 検証
    assert [(problem.id, problem.key) for problem in problems] == [
        ("D-1", "items[0].options"),
        ("D-2", "items[1].options"),
        ("D-3", "items[2].status"),
    ]
    assert {(problem.kind, problem.file) for problem in problems} == {
        ("decision_state", "decisions.yaml")
    }
    assert "A" in problems[2].detail
    assert "未決定" in problems[2].detail


def test_check_decision_rules_when_malformed() -> None:
    """形の崩れた要素は飛ばす（正常系）。"""
    # 準備
    decisions = {"items": ["文字列", {"id": "D-1", "status": "未決定", "options": "文字列"}]}
    # 実行
    problems = store.check_decision_rules(decisions)
    # 検証
    assert problems == []


@pytest.mark.parametrize(
    ("kwargs", "expected_legacy"),
    [
        pytest.param({"written_ids": frozenset({"D-1"})}, False, id="written"),
        pytest.param({}, True, id="not_written"),
    ],
)
def test_build_mismatch_error_when_decision_state(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    kwargs: dict[str, Any],
    expected_legacy: bool,
) -> None:
    """書き込む項目だけが案と状態に合わないときは前の版の形式にしない（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1")))
    problem = store.Problem(
        kind="decision_state",
        file="decisions.yaml",
        id="D-1",
        key="items[0].options",
        detail="D-1 は状態 未決定 のため案を 1 つ以上持つ（options に案を書く）",
    )
    # 実行
    error = store.build_mismatch_error([problem], workspace, **kwargs)
    # 検証
    assert error.legacy is expected_legacy
    assert len(error.lines) == 1
    assert error.lines[0].startswith("decisions.yaml: items[0].options:")


def test_written_ids(make_item: MakeItem) -> None:
    """足した項目と直した項目だけを返す（正常系）。"""
    # 準備
    before = [make_item("D-1"), make_item("D-2")]
    after = [make_item("D-1"), make_item("D-2", status="保留"), make_item("D-3")]
    # 実行
    written = store._written_ids(before, after)
    # 検証
    assert written == frozenset({"D-2", "D-3"})


def test_validate_workspace_when_decision_state(
    make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """案と状態の決まりに合わない検討事項も問題に含める（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1", options=[])))
    # 実行
    problems = store.validate_workspace(workspace)
    # 検証
    assert len(problems) == 1
    problem = problems[0]
    assert problem.kind == "decision_state"
    assert problem.file == "decisions.yaml"
    assert problem.key == "items[0].options"
    assert problem.id == "D-1"


@pytest.mark.parametrize(
    ("kept_d2", "changed_d1", "expected_legacy", "expected_id"),
    [
        pytest.param({"options": []}, {"lead": "直した"}, True, "D-2", id="other_item_mismatch"),
        pytest.param({}, {"status": "決定済み"}, False, "D-1", id="written_item_mismatch"),
    ],
)
def test_save_change_when_decision_state(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    kept_d2: dict[str, Any],
    changed_d1: dict[str, Any],
    expected_legacy: bool,
    expected_id: str,
) -> None:
    """書き換える項目以外の案と状態の合わない検討事項があるときだけ、前の版の形式とする（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("D-2", **kept_d2))
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    change = store.Change(
        kind="decision", items=[make_item("D-1", **changed_d1), make_item("D-2", **kept_d2)]
    )
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        store.save_change(workspace, change)
    assert exc_info.value.legacy is expected_legacy
    assert all(expected_id in line for line in exc_info.value.lines)
    assert snapshot_tree(root) == before


@pytest.mark.parametrize(
    ("kept_d2", "added_d3", "expected_legacy", "expected_id"),
    [
        pytest.param({"options": []}, {}, True, "D-2", id="other_item_mismatch"),
        pytest.param({}, {"options": []}, False, "D-3", id="written_item_mismatch"),
    ],
)
def test_save_batch_when_decision_state(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    kept_d2: dict[str, Any],
    added_d3: dict[str, Any],
    expected_legacy: bool,
    expected_id: str,
) -> None:
    """書き換える項目以外の案と状態の合わない検討事項があるときだけ、前の版の形式とする（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("D-2", **kept_d2))
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    change = store.BatchChange(
        items={
            "decision": [
                make_item("D-1"),
                make_item("D-2", **kept_d2),
                make_item("D-3", **added_d3),
            ],
            "task": [make_item("T-1")],
        }
    )
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        store.save_batch(workspace, change)
    assert exc_info.value.legacy is expected_legacy
    assert all(expected_id in line for line in exc_info.value.lines)
    assert snapshot_tree(root) == before


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        pytest.param({}, True, id="no_written_ids"),
        pytest.param({"written_ids": frozenset({"D-1"})}, False, id="written"),
        pytest.param({"written_ids": frozenset({"D-2"})}, True, id="other_written"),
    ],
)
def test_is_legacy_problem_when_decision_state(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    kwargs: dict[str, Any],
    expected: bool,
) -> None:
    """書き込む項目以外の案と状態の合わない検討事項だけを前の版の形式とする（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1", options=[])))
    problem = store.Problem(
        kind="decision_state",
        file="decisions.yaml",
        id="D-1",
        key="items[0].options",
        detail="D-1 は状態 未決定 のため案を 1 つ以上持つ（options に案を書く）",
    )
    # 実行
    result = store.is_legacy_problem(problem, workspace, **kwargs)
    # 検証
    assert result is expected
