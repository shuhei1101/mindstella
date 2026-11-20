"""記録の形式の移行（関数 `migrate`）の結合テスト。

関数はテストごとの子プロセスで呼び、結果か例外を JSON で受け取る。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml
from session_fixtures import SCRIPTS_DIR
from workspace_fixtures import (
    LOCK_FILE_NAME,
    MDMARK_COMMAND_ENV,
    NOOP_MDMARK_COMMAND,
    RECORD_DIR,
    plugin_version,
    step_versions_after,
    write_yaml,
)

from .fixture_types import (
    CallTool,
    MakeItem,
    MakeLegacyWorkspace,
    MakeSubmission,
    MakeThread,
    MakeWorkspace,
    SnapshotTree,
    WriteSubmissions,
    WriteThreads,
)

# プラグインの版（plugins/mindstella/version.ini の 1 行目）
PLUGIN_VERSION = plugin_version()

# 版を記録する前の形式から並ぶ手順の版（migrations/ の全ての手順の版）
STEP_VERSIONS = step_versions_after(None)

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

# 資料を mdmark の今の書き方へ移す手順の版と、その前の版
MDMARK_STEP_VERSION = "v0.13.0"

# 資料を mdmark の今の書き方へ移す手順の、v0.13.0 の中の番号
MDMARK_STEP_INDEX = 5
BEFORE_MDMARK_VERSION = "v0.12.1"

# v0.13.0 までの config.yaml の、プレビューの配信の固定のポート
FIXED_PREVIEW_PORT = 47800

# mdmark の今の版で廃止した flow の範囲の定義（種類 llm・script のノード）
RETIRED_FLOW = {
    "title": "問い合わせへの自動返信",
    "scope": "メールを受け取ってから下書きを作るまで",
    "width": 600,
    "height": 200,
    "nodes": [
        {"id": "recv", "kind": "script", "x": 20, "y": 60, "w": 140, "h": 64, "name": "受け取り"},
        {
            "id": "draft",
            "kind": "llm",
            "x": 300,
            "y": 60,
            "w": 140,
            "h": 64,
            "name": "返信の下書き",
        },
    ],
    "wires": [
        {
            "id": "w-body",
            "from": "recv",
            "to": "draft",
            "line": "flow",
            "points": [[160, 92], [300, 92]],
            "label": "本文",
        }
    ],
}

# mdmark の今の版で廃止した sequence の範囲の定義
RETIRED_SEQUENCE = {
    "title": "問い合わせ 1 通の流れ",
    "participants": [
        {"id": "recv", "kind": "script", "name": "受け取り"},
        {"id": "draft", "kind": "llm", "name": "返信の下書き"},
    ],
    "steps": [{"from": "recv", "to": "draft", "label": "本文"}],
}


# 子プロセスで `migrate` を呼び、結果か例外を JSON で標準出力に書くコード
RUNNER = """
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import migrator
from migration_ops import DESTRUCTIVE_OPS
to_version = migrator.parse_release_version(sys.argv[3]) if sys.argv[3] else None
try:
    report = migrator.migrate(Path(sys.argv[2]), to_version=to_version)
except Exception as error:
    lines = [str(error), *getattr(error, "lines", [])]
    print(json.dumps({"error": type(error).__name__, "text": "\\n".join(lines)}, ensure_ascii=False))
    sys.exit(0)
print(json.dumps({
    "workspace_version": None if report.workspace_version is None else str(report.workspace_version),
    "plugin_version": str(report.plugin_version),
    "relation": report.relation,
    "steps": [
        {"version": str(step.version), "index": step.index, "op": step.op, "destructive": step.op in DESTRUCTIVE_OPS or bool(step.args.get("destructive"))}
        for step in report.steps
    ],
    "backup": None if report.backup is None else {"kind": report.backup.kind, "ref": report.backup.ref},
    "recorded": None if report.recorded is None else str(report.recorded),
    "provisional": report.provisional,
    "not_carried": report.not_carried,
    "reports": report.reports,
    "source_files": report.source_files,
}, ensure_ascii=False))
"""


@dataclass(frozen=True)
class MigrateResult:
    """`migrate` の結果。例外のときは `error` に型の名前、`text` にメッセージと行を持つ。"""

    error: str | None
    text: str
    data: dict[str, Any] | None


def _migrate(
    root: Path, to_version: str | None = None, env: dict[str, str] | None = None
) -> MigrateResult:
    """子プロセスで `migrate` を呼ぶ。"""
    completed = subprocess.run(
        [sys.executable, "-c", RUNNER, str(SCRIPTS_DIR), str(root), to_version or ""],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={
            **os.environ,
            "PYTHONUTF8": "1",
            MDMARK_COMMAND_ENV: NOOP_MDMARK_COMMAND,
            **(env or {}),
        },
        check=True,
    )
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    if "error" in payload:
        return MigrateResult(error=payload["error"], text=payload["text"], data=None)
    return MigrateResult(error=None, text="", data=payload)


def _retired_range(directive: str, definition: dict[str, Any]) -> str:
    """廃止した図の範囲（マーカーと JSON のコードブロック）を返す。"""
    body = json.dumps(definition, ensure_ascii=False, indent=2)
    return f"<!-- {directive} -->\n\n```json\n{body}\n```\n\n<!-- /{directive} -->\n"


def _make_mdmark_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> Path:
    """A-1 に flow・sequence の図、A-2 に引数を書いた表のマーカーを持つ、v0.12.1 のワークスペースを作る。"""
    root = make_workspace(
        make_item("A-1", body="docs/A-1.md"),
        make_item("A-2", body="docs/A-2.md"),
        bodies={
            "A-1.md": f"# 構成\n\n{_retired_range('flow', RETIRED_FLOW)}\n{_retired_range('sequence', RETIRED_SEQUENCE)}",
            "A-2.md": "# 一覧\n\n<!-- table: data +count -->\n\n| 名前 | 数 |\n| --- | --- |\n| a | 1 |\n\n<!-- /table -->\n",
        },
        legacy_bodies=True,
    )
    (root / RECORD_DIR / VERSION_FILE).write_text(f"{BEFORE_MDMARK_VERSION}\n", encoding="utf-8")
    return root


def _read_items(root: Path, file_name: str) -> list[dict[str, Any]]:
    """ワークスペースの種類ごとの YAML の項目の並びを読む。"""
    return yaml.safe_load((root / RECORD_DIR / file_name).read_text(encoding="utf-8"))["items"]


def _read_docs(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの資料の並びを読む。"""
    return yaml.safe_load((root / RECORD_DIR / "docs.yaml").read_text(encoding="utf-8"))["items"]


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


def _create_current_workspace(tmp_path: Path, valid_settings: dict[str, Any]) -> Path:
    """プラグインの版を記録した今の形式のワークスペースを作り、そのフォルダを返す。"""
    root = tmp_path / "current"
    records = root / RECORD_DIR
    (records / "docs").mkdir(parents=True)
    write_yaml(records / "config.yaml", valid_settings)
    # 作成と同じく、2 行目にその版の手順を当て終えた数を置く
    steps = yaml.safe_load(
        (MIGRATIONS_DIR / PLUGIN_VERSION / "steps.yaml").read_text(encoding="utf-8")
    )["steps"]
    (records / VERSION_FILE).write_text(f"{PLUGIN_VERSION}\n{len(steps)}\n", encoding="utf-8")
    # 作成で置かれる、プラグインと同じ中身のスキーマの複製
    copies = records / "schemas"
    copies.mkdir()
    for name in SOURCE_SCHEMAS:
        shutil.copyfile(PLUGIN_SCHEMA_DIR / name, copies / name)
    return root


# 子プロセスでプラグインの配信の設定を組み立て、YAML で標準出力に書くコード
SOURCE_CONFIG_RUNNER = """
import sys
import pytest
import yaml
sys.path.insert(0, sys.argv[1])
import store
print(yaml.safe_dump(store.build_source_config("current", "題名"), allow_unicode=True, sort_keys=False))
"""


def _build_source_config() -> dict[str, Any]:
    """プラグインの `build_source_config` が組み立てる配信の設定を返す。"""
    completed = subprocess.run(
        [sys.executable, "-c", SOURCE_CONFIG_RUNNER, str(SCRIPTS_DIR)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return yaml.safe_load(completed.stdout)


# 配信の設定が指すスキーマ（プラグインの `skills/mindmap/schemas/` の中の名前）
SOURCE_SCHEMAS = (
    "common.schema.json",
    "decisions.schema.json",
    "tasks.schema.json",
    "research.schema.json",
    "docs.schema.json",
    "terms.schema.json",
    "notes.schema.json",
    "logs.schema.json",
)

# プラグインのスキーマの置き場所
PLUGIN_SCHEMA_DIR = SCRIPTS_DIR.parent / "schemas"

# 移し替えの手順の置き場所
MIGRATIONS_DIR = SCRIPTS_DIR.parent / "migrations"


def _read_version(root: Path) -> str:
    """記録のフォルダの版のファイルの 1 行目。"""
    return (root / RECORD_DIR / VERSION_FILE).read_text(encoding="utf-8").splitlines()[0]


def test_normal_when_apply(make_legacy_workspace: MakeLegacyWorkspace) -> None:
    """写しを取ってプラグインの版までの手順を当て、題名に仮の値を入れてバージョンのファイルを書く（正常系）。"""
    # 準備
    root = make_legacy_workspace(
        legacy_docs={"A-1": True, "A-2": False},
        without_summary=True,
        settings_file=LEGACY_SETTINGS,
        top=True,
    )
    before = {
        item["id"]: item
        for item in yaml.safe_load((root / "docs.yaml").read_text(encoding="utf-8"))["items"]
    }
    docs_before = (root / "docs.yaml").read_bytes()
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error is None, result.text
    payload = result.data
    assert payload is not None
    after = {item["id"]: item for item in _read_docs(root)}
    assert (after["A-1"]["status"], after["A-2"]["status"]) == ("完成", "下書き")
    assert "done" not in after["A-1"]
    assert "done" not in after["A-2"]
    # 更新日時は v0.13.0 の手順で history.yaml の行へ値を変えずに移る
    history = yaml.safe_load((root / RECORD_DIR / "history.yaml").read_text(encoding="utf-8"))[
        "items"
    ]
    assert history["A-1"]["updated"] == before["A-1"]["updated"]
    assert history["A-2"]["updated"] == before["A-2"]["updated"]
    # 設定ファイルの名前が改まって記録のフォルダへ移り、本文のフォルダは v0.14.0 の手順で直下へ戻る
    assert sorted(path.name for path in root.iterdir()) == [RECORD_DIR, "docs"]
    settings = yaml.safe_load((root / RECORD_DIR / SETTINGS).read_text(encoding="utf-8"))
    assert settings["summary"] == root.name
    assert {"file": ".mindstella/config.yaml", "key": "summary", "value": root.name} in payload[
        "provisional"
    ]
    assert payload["backup"]["kind"] == "copy"
    assert (Path(payload["backup"]["ref"]) / "docs.yaml").read_bytes() == docs_before
    assert (Path(payload["backup"]["ref"]) / LEGACY_SETTINGS).exists()
    assert _read_version(root) == PLUGIN_VERSION
    assert payload["recorded"] == PLUGIN_VERSION


def test_normal_when_backup_git(tmp_path: Path, make_legacy_workspace: MakeLegacyWorkspace) -> None:
    """git の作業ツリーの中のワークスペースでは、ワークスペースのパスだけをコミットして写しにする（正常系）。"""
    # 準備
    root = make_legacy_workspace(
        legacy_docs={"A-1": True}, without_summary=True, settings_file=LEGACY_SETTINGS, top=True
    )
    # ワークスペースの親を作業ツリーにし、外のファイルはどちらもコミットしない
    _init_git(tmp_path)
    (tmp_path / "other.txt").write_text("外のファイル\n", encoding="utf-8")
    (tmp_path / "staged.txt").write_text("ステージしたファイル\n", encoding="utf-8")
    _git(tmp_path, "add", "staged.txt")
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error is None, result.text
    assert result.data is not None
    backup = result.data["backup"]
    assert backup["kind"] == "git"
    committed = _git(tmp_path, "show", "--name-only", "--pretty=format:", backup["ref"]).split()
    assert committed != []
    assert all(name.startswith(f"{root.name}/") for name in committed)
    assert _git(tmp_path, "diff", "--cached", "--name-only").split() == ["staged.txt"]


def test_normal_when_same(
    tmp_path: Path, valid_settings: dict[str, Any], snapshot_tree: SnapshotTree
) -> None:
    """今の版のワークスペースでは並べる手順が無く、何も書かない（正常系）。"""
    # 準備
    root = _create_current_workspace(tmp_path, valid_settings)
    before = (snapshot_tree(root), _mtimes(root))
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error is None, result.text
    assert result.data is not None
    assert (result.data["relation"], result.data["steps"], result.data["provisional"]) == (
        "same",
        [],
        [],
    )
    assert (snapshot_tree(root), _mtimes(root)) == before


def test_normal_when_backup_ignored(
    tmp_path: Path, make_legacy_workspace: MakeLegacyWorkspace
) -> None:
    """git の作業ツリーの中でも、ignore されたファイルを持つワークスペースは複製で写しを取る（正常系）。"""
    # 準備
    root = make_legacy_workspace(
        legacy_docs={"A-1": True}, without_summary=True, settings_file=LEGACY_SETTINGS, top=True
    )
    _init_git(tmp_path)
    (tmp_path / ".gitignore").write_text("*\n", encoding="utf-8")
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error is None, result.text
    assert result.data is not None
    backup = result.data["backup"]
    assert backup["kind"] == "copy"
    assert (Path(backup["ref"]) / "docs.yaml").exists()
    assert _git(tmp_path, "rev-list", "--all", "--count").strip() == "0"


def test_normal_when_already_current(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any]
) -> None:
    """今の形（config.yaml が題名を持ち、資料が status）に版のファイルが無くても、何も変えずに成功する（正常系）。"""
    # 準備（今の形の設定はワークスペースの ID を持つ）
    root = make_workspace(
        make_item("A-1", status="完成"),
        settings={"id": "mindstella-workspace-0a1b2c", **valid_settings},
    )
    watched = [root / RECORD_DIR / SETTINGS, root / RECORD_DIR / "docs.yaml"]
    before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in watched]
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error is None, result.text
    assert result.data is not None
    assert result.data["provisional"] == []
    assert [(path.read_bytes(), path.stat().st_mtime_ns) for path in watched] == before
    assert not (root / LEGACY_SETTINGS).exists()
    assert not (root / SETTINGS).exists()


def test_normal_when_field_to_playbooks(
    make_workspace: MakeWorkspace, valid_settings: dict[str, Any]
) -> None:
    """v0.5.0 の手順で前の版の設定ファイル mindmap.yaml の field を playbooks の 1 件の配列へ移す（正常系）。"""
    # 準備
    settings = {**valid_settings, "field": "システム開発", "target_label": "システム"}
    root = make_workspace(settings=settings, settings_file=LEGACY_SETTINGS, top=True)
    (root / VERSION_FILE).write_text("v0.4.0\n", encoding="utf-8")
    # 実行
    result = _migrate(root, to_version="v0.5.0")
    # 検証
    assert result.error is None, result.text
    assert result.data is not None
    assert [(step["version"], step["op"]) for step in result.data["steps"]] == [("v0.5.0", "call")]
    moved = yaml.safe_load((root / LEGACY_SETTINGS).read_text(encoding="utf-8"))
    assert "field" not in moved
    assert moved["playbooks"] == ["システム開発"]
    assert moved["target_label"] == "システム"
    assert (root / VERSION_FILE).read_text(encoding="utf-8") == "v0.4.0\n"


def test_normal_when_rename_settings_file(
    make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """v0.6.0 の手順で mindmap.yaml を config.yaml に改め、直下の記録を .mindstella/ へ移す（正常系）。"""
    # 準備
    # 前の版（v0.5.0）の形式: config.yaml を持たず、題名を持つ mindmap.yaml を持つ。記録は全て直下にある
    root = make_workspace(
        make_item("D-1", body="D-1.md"),
        bodies={"D-1.md": "本文\n"},
        settings_file=LEGACY_SETTINGS,
        top=True,
        with_history=False,
    )
    (root / VERSION_FILE).write_text("v0.5.0\n", encoding="utf-8")
    (root / "release").mkdir(exist_ok=True)
    (root / "release" / "資料.md").write_text("資料\n", encoding="utf-8")
    (root / "preview.html").write_text("<html></html>\n", encoding="utf-8")
    legacy = {
        "config": (root / LEGACY_SETTINGS).read_bytes(),
        "decisions": (root / "decisions.yaml").read_bytes(),
        "body": (root / "docs" / "D-1.md").read_bytes(),
        "release": (root / "release" / "資料.md").read_bytes(),
    }
    # 実行
    result = _migrate(root, to_version="v0.6.0")
    # 検証
    assert result.error is None, result.text
    payload = result.data
    assert payload is not None
    assert payload["workspace_version"] == "v0.5.0"
    steps = payload["steps"]
    assert {step["version"] for step in steps} == {"v0.6.0"}
    assert (steps[0]["op"], steps[0]["destructive"]) == ("rename_file", True)
    assert all(step["destructive"] for step in steps)
    # 直下には記録のフォルダだけが残る
    assert [path.name for path in root.iterdir()] == [RECORD_DIR]
    records = root / RECORD_DIR
    assert (records / SETTINGS).read_bytes() == legacy["config"]
    assert (records / "decisions.yaml").read_bytes() == legacy["decisions"]
    assert (records / "docs" / "D-1.md").read_bytes() == legacy["body"]
    assert (records / "release" / "資料.md").read_bytes() == legacy["release"]
    assert payload["provisional"] == []
    assert (records / VERSION_FILE).read_text(encoding="utf-8") == "v0.5.0\n"


def test_error_when_newer(
    tmp_path: Path, valid_settings: dict[str, Any], snapshot_tree: SnapshotTree
) -> None:
    """版が新しいワークスペースには手順を当てない（異常系）。"""
    # 準備
    root = _create_current_workspace(tmp_path, valid_settings)
    (root / RECORD_DIR / VERSION_FILE).write_text(f"{NEWER_VERSION}\n", encoding="utf-8")
    before = snapshot_tree(root)
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error == "WorkspaceNewerError"
    assert NEWER_VERSION in result.text
    assert PLUGIN_VERSION in result.text
    assert snapshot_tree(root) == before
    assert list(root.parent.glob(f"{root.name}.before-*")) == []


def test_error_when_step_fails(
    make_legacy_workspace: MakeLegacyWorkspace, snapshot_tree: SnapshotTree
) -> None:
    """手順 1・2 が docs.yaml を書き換えた後に手順 3 が失敗すると、写しから戻して終わる（異常系）。"""
    # 準備
    root = make_legacy_workspace(
        legacy_docs={"A-1": True, "A-2": False}, settings_file=LEGACY_SETTINGS, top=True
    )
    # 手順 3 が読む mindmap.yaml だけを読めない中身にする
    (root / LEGACY_SETTINGS).write_text(BROKEN_SETTINGS, encoding="utf-8")
    before = snapshot_tree(root)
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error == "StepFailedError"
    assert result.text.startswith(f"{SUMMARY_STEP_VERSION} の手順 3（set_default）: ")
    assert LEGACY_SETTINGS in result.text
    # 手順 1・2 が書き換えた docs.yaml も含めて、全てのファイルが呼ぶ前と同じ
    assert snapshot_tree(root) == before


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace, valid_settings: dict[str, Any], snapshot_tree: SnapshotTree
) -> None:
    """手順を当てた後にスキーマに合わなければ写しから戻し、バージョンを書かない（異常系）。"""
    # 準備
    root = make_workspace(settings={**valid_settings, "summary": 123}, legacy_bodies=True)
    (root / RECORD_DIR / VERSION_FILE).write_text("v0.13.0\n", encoding="utf-8")
    before = snapshot_tree(root)
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error == "SchemaMismatchError"
    assert any(
        line.startswith("config.yaml: ") and "summary" in line for line in result.text.splitlines()
    )
    assert snapshot_tree(root) == before


def test_error_when_workspace_not_found(tmp_path: Path, snapshot_tree: SnapshotTree) -> None:
    """config.yaml も mindmap.yaml も無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error == "WorkspaceNotFoundError"
    assert str(root) in result.text
    assert snapshot_tree(root) == {}


def _read_decisions(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの検討事項の並びを読む。"""
    return _read_items(root, "decisions.yaml")


def test_normal_when_answer_to_option(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """v0.7.0 の手順で、案を持たない決定済みの検討事項にだけ答えから採用した案を作る（正常系）。"""
    # 準備
    adopted_option = {"key": "A", "content": "案 A", "adopted": True}
    decided = make_item("D-1", status="決定済み", answer="種類ごとに分ける", reason="探しやすい")
    undecided = make_item("D-2", status="未決定")
    already = make_item("D-3", status="決定済み", options=[adopted_option])
    root = make_workspace(
        *(
            {key: value for key, value in item.items() if key != "options"}
            for item in (decided, undecided)
        ),
        already,
        with_history=False,
    )
    (root / RECORD_DIR / VERSION_FILE).write_text("v0.6.0\n", encoding="utf-8")
    before = _read_decisions(root)
    # 実行
    result = _migrate(root, to_version="v0.7.0")
    # 検証
    assert result.error is None, result.text
    assert result.data is not None
    assert [
        (step["version"], step["op"], step["destructive"]) for step in result.data["steps"]
    ] == [("v0.7.0", "call", False)]
    after = _read_decisions(root)
    assert after[0]["options"] == [
        {"key": "A", "content": "種類ごとに分ける", "reason": "探しやすい", "adopted": True}
    ]
    for key in ("status", "answer", "updated"):
        assert after[0][key] == before[0][key]
    assert after[1:] == before[1:]
    assert (root / RECORD_DIR / VERSION_FILE).read_text(encoding="utf-8") == "v0.6.0\n"
    # もう一度当てても、案は 1 件のまま
    again = _migrate(root, to_version="v0.7.0")
    assert again.error is None, again.text
    assert len(_read_decisions(root)[0]["options"]) == 1


def test_normal_when_submissions_to_threads(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_submission: MakeSubmission,
    write_submissions: WriteSubmissions,
    call_tool: CallTool,
) -> None:
    """v0.7.0 のワークスペースの送信を、取り込み済みはクローズ、取り込んでいないものはオープンのスレッドへ移す（正常系）。"""
    # 準備
    taken_at = "2026-10-02T08:00:00+00:00"
    root = make_workspace(make_item("D-1"))
    no_target = make_submission("S-2", body="全体に目を通した")
    del no_target["target"]
    write_submissions(root, make_submission("S-1", taken=taken_at), no_target)
    (root / RECORD_DIR / VERSION_FILE).write_text("v0.7.0\n", encoding="utf-8")
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error is None, result.text
    threads = _read_items(root, "threads.yaml")
    closed, opened = threads
    assert (closed["id"], closed["status"], closed["target"]) == ("TH-1", "closed", "D-1")
    assert [(event["kind"], event["author"]) for event in closed["events"]] == [("closed", "ai")]
    assert closed["posts"][0]["taken"] == taken_at
    assert (opened["id"], opened["status"], "target" in opened) == ("TH-2", "open", False)
    assert opened["posts"][0]["taken"] is None
    # 利用者が送ったものは利用者の既読
    assert [thread["posts"][0]["seen"] for thread in threads] == [True, True]
    assert not (root / RECORD_DIR / "submissions.yaml").exists()
    assert call_tool("check", workspace=str(root)).data == {"ok": True, "problems": []}
    awaiting = call_tool("threads", workspace=str(root), awaiting=True)
    assert awaiting.data is not None
    assert [item["id"] for item in awaiting.data["items"]] == ["TH-2"]


def test_normal_when_tags_to_vocabulary(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    snapshot_tree: SnapshotTree,
) -> None:
    """v0.9.0 のワークスペースの項目とスレッドが使っているタグを、説明なしで語彙へ登録する（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["保存", "通知"]), make_item("N-1", tags=["脱線", "保存"])
    )
    write_threads(root, make_thread("TH-1", tags=["起票"]))
    (root / RECORD_DIR / VERSION_FILE).write_text("v0.9.0\n", encoding="utf-8")
    config_path = root / RECORD_DIR / SETTINGS
    settings_before = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    records_before = {
        name: data
        for name, data in snapshot_tree(root).items()
        if name != f"{RECORD_DIR}/{SETTINGS}"
    }
    # 実行（この手順の次の版が語彙を外すので、v0.10.0 までを当てる）
    result = _migrate(root, to_version="v0.10.0")
    # 検証
    assert result.error is None, result.text
    assert result.data is not None
    assert [
        (step["version"], step["op"], step["destructive"]) for step in result.data["steps"]
    ] == [("v0.10.0", "call", False)]
    settings = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert settings["tags"] == [
        {"name": "保存"},
        {"name": "脱線"},
        {"name": "起票"},
        {"name": "通知"},
    ]
    assert {key: value for key, value in settings.items() if key != "tags"} == settings_before
    records_after = {
        name: data
        for name, data in snapshot_tree(root).items()
        if name != f"{RECORD_DIR}/{SETTINGS}"
    }
    assert records_after == records_before
    # もう一度当てても、タグは 4 件のまま
    again = _migrate(root, to_version="v0.10.0")
    assert again.error is None, again.text
    assert len(yaml.safe_load(config_path.read_text(encoding="utf-8"))["tags"]) == 4


def test_normal_when_tag_vocabulary_removed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    valid_settings: dict[str, Any],
    snapshot_tree: SnapshotTree,
) -> None:
    """v0.10.0 のワークスペースの config.yaml からタグの語彙を削除し、項目とスレッドのタグは残す（正常系）。"""
    # 準備
    vocabulary = [{"name": "保存", "summary": "保存の話"}, {"name": "通知"}]
    root = make_workspace(
        make_item("D-1", tags=["保存", "通知"]), settings={**valid_settings, "tags": vocabulary}
    )
    write_threads(root, make_thread("TH-1", tags=["起票"]))
    (root / RECORD_DIR / VERSION_FILE).write_text("v0.10.0\n", encoding="utf-8")
    config_path = root / RECORD_DIR / SETTINGS
    settings_before = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    records_before = {
        name: data
        for name, data in snapshot_tree(root).items()
        if name != f"{RECORD_DIR}/{SETTINGS}"
    }
    # 実行
    result = _migrate(root, to_version="v0.11.0")
    # 検証
    assert result.error is None, result.text
    assert result.data is not None
    assert [
        (step["version"], step["op"], step["destructive"]) for step in result.data["steps"]
    ] == [("v0.11.0", "call", True)]
    settings = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert settings == {key: value for key, value in settings_before.items() if key != "tags"}
    records_after = {
        name: data
        for name, data in snapshot_tree(root).items()
        if name != f"{RECORD_DIR}/{SETTINGS}"
    }
    assert records_after == records_before
    # もう一度当てても、config.yaml は変わらない
    config_after = config_path.read_text(encoding="utf-8")
    again = _migrate(root, to_version="v0.11.0")
    assert again.error is None, again.text
    assert config_path.read_text(encoding="utf-8") == config_after


def test_normal_when_tags_to_objects(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> None:
    """v0.11.0 のワークスペースの項目の文字列のタグを {name} に置き換え、スレッドのタグは残す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", tags=["保存", "通知", "ＡＰＩ", "api"]),
        make_item("N-1", tags=[]),
        with_history=False,
    )
    write_threads(root, make_thread("TH-1", tags=["起票"]))
    (root / RECORD_DIR / VERSION_FILE).write_text("v0.11.0\n", encoding="utf-8")
    decisions_path = root / RECORD_DIR / "decisions.yaml"
    updated_before = _read_decisions(root)[0]["updated"]
    # 実行
    result = _migrate(root, to_version="v0.12.0")
    # 検証
    assert result.error is None, result.text
    assert result.data is not None
    assert [
        (step["version"], step["op"], step["destructive"]) for step in result.data["steps"]
    ] == [("v0.12.0", "call", True)]
    decision = _read_decisions(root)[0]
    assert decision["tags"] == [{"name": "保存"}, {"name": "通知"}, {"name": "ＡＰＩ"}]
    assert decision["updated"] == updated_before
    assert _read_items(root, "notes.yaml")[0]["tags"] == []
    assert _read_items(root, "threads.yaml")[0]["tags"] == ["起票"]
    # もう一度当てても、D-1 は変わらない
    decisions_after = decisions_path.read_text(encoding="utf-8")
    again = _migrate(root, to_version="v0.12.0")
    assert again.error is None, again.text
    assert decisions_path.read_text(encoding="utf-8") == decisions_after


def test_normal_when_project_index_layout(
    make_workspace: MakeWorkspace, make_item: MakeItem, snapshot_tree: SnapshotTree
) -> None:
    """v0.12.0 のワークスペースの参照・本文・履歴を、記録を project-index で配る形にする（正常系）。"""
    # 準備
    stamps = {"created": "2026-10-01T00:00:00+00:00", "updated": "2026-10-02T00:00:00+00:00"}
    history = [
        {"seq": 2, "at": "2026-10-02T00:00:00+00:00", "by": "ai", "before": {"answer": None}}
    ]
    root = make_workspace(
        make_item("D-1", **stamps),
        make_item(
            "D-2",
            depends_on=["D-1"],
            parent="D-1",
            related=["R-1"],
            body="D-2.md",
            history=history,
            **stamps,
        ),
        make_item("R-1", **stamps),
        make_item("T-1", depends_on=["T-2"], **{"for": ["D-2"]}, **stamps),
        make_item("T-2", **stamps),
        bodies={"D-2.md": "D-2 の本文\n"},
        with_history=False,
    )
    (root / RECORD_DIR / VERSION_FILE).write_text("v0.12.0\n", encoding="utf-8")
    # 実行
    result = _migrate(root, to_version=MDMARK_STEP_VERSION)
    # 検証
    assert result.error is None, result.text
    assert result.data is not None
    # 手順は refs_to_related・body_to_docs_path・place_source_config・meta_to_history_yaml・mdmark_documents の順
    assert [
        (step["version"], step["op"], step["destructive"]) for step in result.data["steps"]
    ] == [
        ("v0.13.0", "call", True),
        ("v0.13.0", "call", True),
        ("v0.13.0", "call", False),
        ("v0.13.0", "call", True),
        ("v0.13.0", "call", True),
    ]
    decisions = {item["id"]: item for item in _read_decisions(root)}
    tasks = {item["id"]: item for item in _read_items(root, "tasks.yaml")}
    assert decisions["D-2"]["related"] == [
        {"to": "D-1", "type": "depends_on"},
        {"to": "D-1", "type": "parent"},
        {"to": "R-1", "type": "see_also"},
    ]
    assert not {"depends_on", "parent", "updated", "history"} & set(decisions["D-2"])
    assert tasks["T-1"]["related"] == [
        {"to": "T-2", "type": "depends_on"},
        {"to": "D-2", "type": "for"},
    ]
    assert not {"for", "depends_on"} & set(tasks["T-1"])
    assert decisions["D-2"]["body"] == "docs/D-2.md"
    row = yaml.safe_load((root / RECORD_DIR / "history.yaml").read_text(encoding="utf-8"))["items"][
        "D-2"
    ]
    assert (row["updated"], row["history"]) == (stamps["updated"], history)
    assert (root / RECORD_DIR / "dev-docs.yaml").is_file()
    assert (root / RECORD_DIR / "schemas").is_dir()
    after = snapshot_tree(root)
    again = _migrate(root, to_version=MDMARK_STEP_VERSION)
    assert again.error is None, again.text
    assert snapshot_tree(root) == after


def test_normal_when_mdmark_documents(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """資料の flow・sequence の図を map へ、引数のマーカーを JSON の記載へ移し、map の種類を設定へ移す（正常系）。"""
    # 準備
    root = _make_mdmark_workspace(make_workspace, make_item)
    # 実行（実際の mdmark の CLI を呼ぶ。空の指定は既定の差し替えを外す）
    result = _migrate(root, env={MDMARK_COMMAND_ENV: ""})
    # 検証
    assert result.error is None, result.text
    assert result.data is not None
    record = root / RECORD_DIR
    first = (root / "docs" / "A-1.mark.md").read_text(encoding="utf-8")
    assert "<!-- flow" not in first
    assert "<!-- sequence" not in first
    assert first.count("<!-- /map -->") == 2
    second = (root / "docs" / "A-2.mark.md").read_text(encoding="utf-8")
    assert '<!-- table: {"kind": "data"' in second
    settings = yaml.safe_load((record / SETTINGS).read_text(encoding="utf-8"))
    assert {"llm", "script"} <= set(settings["mdmark"]["map"]["kinds"])
    # v0.13.0 の 5 件目（mdmark_documents）の報告の行
    prefix = f"{MDMARK_STEP_VERSION} #{MDMARK_STEP_INDEX}: "
    assert [line for line in result.data["reports"] if line.startswith(prefix)] != []
    assert not (record / "mdmark.config.yaml").exists()
    assert not (record / ".mdmark").exists()
    assert call_tool("check", workspace=str(root)).data == {"ok": True, "problems": []}


def test_error_when_mdmark_documents_fail(
    make_workspace: MakeWorkspace, make_item: MakeItem, snapshot_tree: SnapshotTree, tmp_path: Path
) -> None:
    """mdmark の CLI が終了コード 0 以外で終わると、写しから戻してエラーを返す（異常系）。"""
    # 準備
    root = _make_mdmark_workspace(make_workspace, make_item)
    fake = tmp_path / "fake_mdmark.py"
    fake.write_text(
        'import sys\nprint("変換できません: docs/A-1.md")\nsys.exit(1)\n', encoding="utf-8"
    )
    before = snapshot_tree(root)
    # 実行
    result = _migrate(
        root, to_version=MDMARK_STEP_VERSION, env={MDMARK_COMMAND_ENV: f"{sys.executable} {fake}"}
    )
    # 検証
    assert result.error == "StepFailedError"
    assert result.text.startswith(f"{MDMARK_STEP_VERSION} の手順 {MDMARK_STEP_INDEX}（call）: ")
    assert "変換できません: docs/A-1.md" in result.text
    assert snapshot_tree(root) == before


# v0.14.0 の手順で消す設定のキーを持つ設定
DISCUSSION_SETTINGS = {
    "playbooks": ["壁打ち"],
    "goal": {"phase": "結論", "summary": "まとめる", "deliverables": []},
    "phases": ["問い", "結論"],
    "targets": [{"name": "認証"}],
    "target_label": "対象",
    "categories": [{"name": "方式", "target": "認証", "summary": "方式の話"}],
}


def test_normal_when_discussion_keys_removed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    snapshot_tree: SnapshotTree,
) -> None:
    """v0.14.0 の手順で、削除するキーを消し、対象・カテゴリーをタグへ、属性・観点・確かさを本文へ移す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item(
            "D-1",
            phase="結論",
            target="認証",
            category="方式",
            attrs={"優先度": "高"},
            weight="大",
        ),
        make_item("A-1", deliverable=True, status="完成", body="docs/A-1.mark.md"),
        make_item("R-1", angles=["費用", "運用"], confidence="中"),
        settings={**valid_settings, **DISCUSSION_SETTINGS},
        bodies={"A-1.mark.md": "資料の本文\n"},
        legacy_bodies=True,
    )
    records = root / RECORD_DIR
    (records / VERSION_FILE).write_text("v0.13.0\n", encoding="utf-8")
    (records / "release").mkdir(exist_ok=True)
    (records / "release" / "資料.md").write_text("書き出した資料\n", encoding="utf-8")
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error is None, result.text
    settings = yaml.safe_load((records / SETTINGS).read_text(encoding="utf-8"))
    assert settings == valid_settings
    removed = {
        "phase",
        "target",
        "category",
        "attrs",
        "weight",
        "deliverable",
        "angles",
        "confidence",
    }
    decision = _read_decisions(root)[0]
    research = _read_items(root, "research.yaml")[0]
    doc = _read_docs(root)[0]
    assert not removed & (set(decision) | set(research) | set(doc))
    assert decision["tags"] == [{"name": "topic:認証"}, {"name": "topic:方式"}]
    assert "| 優先度 | 高 |" in (records / decision["body"]).read_text(encoding="utf-8")
    research_body = (records / research["body"]).read_text(encoding="utf-8")
    assert "| 観点 | 費用・運用 |" in research_body
    assert "| 確かさ | 中 |" in research_body
    # 書き出した資料のコピーは v0.14.0 の手順 3 が消す
    assert not (records / "release").exists()
    assert _read_version(root) == PLUGIN_VERSION
    # もう一度当てても、ワークスペースが変わらない
    after = snapshot_tree(root)
    again = _migrate(root)
    assert again.error is None, again.text
    assert snapshot_tree(root) == after


def test_normal_when_schema_copy_stale(
    tmp_path: Path, valid_settings: dict[str, Any], snapshot_tree: SnapshotTree
) -> None:
    """今の版のワークスペースでは手順を当てず、プラグインのスキーマと中身が違うスキーマの複製だけを書き直す（正常系）。"""
    # 準備
    root = _create_current_workspace(tmp_path, valid_settings)
    copies = root / RECORD_DIR / "schemas"
    (copies / "docs.schema.json").write_text(
        json.dumps({"type": "object", "required": ["deliverable"]}), encoding="utf-8"
    )
    (copies / "legacy.schema.json").write_text('{"title": "前の版"}\n', encoding="utf-8")
    before = _mtimes(root)
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error is None, result.text
    assert result.data is not None
    assert (result.data["relation"], result.data["steps"], result.data["backup"]) == (
        "same",
        [],
        None,
    )
    assert result.data["source_files"] == [".mindstella/schemas/docs.schema.json"]
    assert (copies / "docs.schema.json").read_bytes() == (
        PLUGIN_SCHEMA_DIR / "docs.schema.json"
    ).read_bytes()
    assert (copies / "legacy.schema.json").read_text(encoding="utf-8") == '{"title": "前の版"}\n'
    after = _mtimes(root)
    changed = sorted(path for path in after if after[path] != before.get(path))
    assert changed == [".mindstella/schemas/docs.schema.json"]


def test_normal_when_source_config_without_write_dates(
    tmp_path: Path, valid_settings: dict[str, Any]
) -> None:
    """今の版のワークスペースの配信の設定の、write_dates を持たない種類の行に write_dates: false を足す（正常系）。"""
    # 準備
    root = _create_current_workspace(tmp_path, valid_settings)
    config = _build_source_config()
    for row in config["documents"]:
        row.pop("write_dates", None)
        # 利用者が書いた値にあたる
        if row["id"] == "terms":
            row["write_dates"] = True
    path = root / RECORD_DIR / "dev-docs.yaml"
    write_yaml(path, config)
    before = _mtimes(root)
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error is None, result.text
    assert result.data is not None
    assert (result.data["relation"], result.data["steps"]) == ("same", [])
    assert result.data["source_files"] == [".mindstella/dev-docs.yaml"]
    written = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert {row["id"]: row["write_dates"] for row in written["documents"]} == {
        "decisions": False,
        "tasks": False,
        "research": False,
        "docs": False,
        "terms": True,
        "notes": False,
        "logs": False,
    }
    for row in written["documents"]:
        row.pop("write_dates")
    for row in config["documents"]:
        row.pop("write_dates", None)
    assert written == config
    after = _mtimes(root)
    changed = sorted(path for path in after if after[path] != before.get(path))
    assert changed == [".mindstella/dev-docs.yaml"]


# D-1 の変更履歴（HTML の本文の回と Markdown の本文の回）
MARKDOWN_BODY_HISTORY: list[dict[str, Any]] = [
    {"seq": 3, "by": "ai", "at": "2026-11-02T00:00:00+00:00", "before": {"body": "docs/D-1.html"}},
    {"seq": 2, "by": "ai", "at": "2026-11-01T00:00:00+00:00", "before": {"body": "docs/D-1.md"}},
]


def test_normal_when_markdown_bodies_renamed(
    make_workspace: MakeWorkspace, make_item: MakeItem, snapshot_tree: SnapshotTree
) -> None:
    """v0.14.0 の手順で、docs/ の Markdown の本文を .mark.md へ改名し、項目の body と変更履歴の before.body を書き換える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item(
            "D-1",
            body="docs/D-1.md",
            updated="2026-11-02T00:00:00+00:00",
            history=MARKDOWN_BODY_HISTORY,
        ),
        make_item("A-1", body="docs/A-1.html"),
        bodies={
            "D-1.md": "# 背景\n\n本文\n",
            "A-1.html": "<p>資料</p>\n",
            "X-1.md": "どこからも指されない本文\n",
        },
        legacy_bodies=True,
    )
    records = root / RECORD_DIR
    (records / VERSION_FILE).write_text("v0.13.0\n", encoding="utf-8")
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error is None, result.text
    assert result.data is not None
    assert [
        (step["version"], step["index"], step["op"], step["destructive"])
        for step in result.data["steps"]
    ] == [
        ("v0.14.0", 1, "call", True),
        ("v0.14.0", 2, "call", True),
        ("v0.14.0", 3, "call", True),
        ("v0.14.0", 4, "call", True),
        ("v0.14.0", 5, "call", True),
    ]
    decision = _read_decisions(root)[0]
    assert decision["body"] == "../docs/D-1.mark.md"
    assert (root / "docs" / "D-1.mark.md").read_text(encoding="utf-8") == "# 背景\n\n本文\n"
    assert not (root / "docs" / "D-1.md").exists()
    d1_row = yaml.safe_load((records / "history.yaml").read_text(encoding="utf-8"))["items"]["D-1"]
    assert [entry["before"]["body"] for entry in d1_row["history"]] == [
        "../docs/D-1.html",
        "../docs/D-1.mark.md",
    ]
    assert [entry["seq"] for entry in d1_row["history"]] == [3, 2]
    assert d1_row["updated"] == "2026-11-02T00:00:00+00:00"
    assert _read_docs(root)[0]["body"] == "../docs/A-1.html"
    assert (root / "docs" / "A-1.html").read_text(encoding="utf-8") == "<p>資料</p>\n"
    assert (root / "docs" / "X-1.mark.md").read_text(
        encoding="utf-8"
    ) == "どこからも指されない本文\n"
    assert not (root / "docs" / "X-1.md").exists()
    assert not (records / "docs").exists()
    # もう一度当てても、ワークスペースが変わらない
    after = snapshot_tree(root)
    again = _migrate(root)
    assert again.error is None, again.text
    assert snapshot_tree(root) == after


def test_error_when_mark_md_exists(
    make_workspace: MakeWorkspace, make_item: MakeItem, snapshot_tree: SnapshotTree
) -> None:
    """改名先が既にあるとき、手順が失敗して写しから戻す（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", body="docs/D-1.md"),
        bodies={"D-1.md": "前の本文\n", "D-1.mark.md": "改名先の本文\n"},
        legacy_bodies=True,
    )
    records = root / RECORD_DIR
    (records / VERSION_FILE).write_text("v0.13.0\n", encoding="utf-8")
    before = snapshot_tree(root)
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error == "StepFailedError"
    assert result.text.startswith("v0.14.0 の手順 2（call）:")
    assert "docs/D-1.mark.md" in result.text
    assert snapshot_tree(root) == before
    assert _read_version(root) == "v0.13.0"


# D-1 の変更履歴（移す前の本文の回）
MOVED_BODY_HISTORY: list[dict[str, Any]] = [
    {"seq": 2, "by": "ai", "at": "2026-11-01T00:00:00+00:00", "before": {"body": "docs/D-1.html"}},
]

# A-1 の本文（埋め込むファイルを直下からの相対パスで指す）
EMBEDDING_BODY = '<p>資料</p>\n<video src="../files/clip.mp4"></video>\n'


def _old_source_config() -> dict[str, Any]:
    """今の版より前の配信の設定（paths_base を持たず、paths が記録のフォルダからの YAML の名前）を返す。"""
    config = _build_source_config()
    config.pop("paths_base", None)
    for row in config["documents"]:
        row["paths"] = [f"{row['id']}.yaml"]
    return config


def _make_root_move_workspace(
    make_workspace: MakeWorkspace, make_item: MakeItem, *, with_files: bool = True
) -> Path:
    """本文・埋め込むファイル・release/ と前の版の配信の設定を記録のフォルダに持つ、v0.13.0 のワークスペースを作る。"""
    root = make_workspace(
        make_item(
            "D-1",
            body="docs/D-1.mark.md",
            updated="2026-11-02T00:00:00+00:00",
            history=MOVED_BODY_HISTORY,
        ),
        make_item("A-1", body="docs/A-1.html"),
        raw_files={
            "dev-docs.yaml": yaml.safe_dump(
                _old_source_config(), allow_unicode=True, sort_keys=False
            )
        },
        bodies={"D-1.mark.md": "# 背景\n\n本文\n", "A-1.html": EMBEDDING_BODY},
        legacy_bodies=True,
    )
    records = root / RECORD_DIR
    (records / VERSION_FILE).write_text("v0.13.0\n", encoding="utf-8")
    # 埋め込むファイルを持つワークスペースか
    if with_files:
        (records / "files").mkdir()
        (records / "files" / "clip.mp4").write_bytes(b"\x00\x01clip")
    (records / "release").mkdir()
    (records / "release" / "A-1.mark.md").write_text("書き出した資料\n", encoding="utf-8")
    return root


def test_normal_when_bodies_moved_to_root(
    make_workspace: MakeWorkspace, make_item: MakeItem, snapshot_tree: SnapshotTree
) -> None:
    """v0.14.0 の手順で、本文と埋め込むファイルを直下へ移し、body・before.body と配信の設定を書き換えて release/ を消す（正常系）。"""
    # 準備
    root = _make_root_move_workspace(make_workspace, make_item)
    records = root / RECORD_DIR
    old_config = yaml.safe_load((records / "dev-docs.yaml").read_text(encoding="utf-8"))
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error is None, result.text
    assert (root / "docs" / "D-1.mark.md").read_text(encoding="utf-8") == "# 背景\n\n本文\n"
    assert (root / "docs" / "A-1.html").read_text(encoding="utf-8") == EMBEDDING_BODY
    assert (root / "files" / "clip.mp4").read_bytes() == b"\x00\x01clip"
    for name in ("docs", "files", "release"):
        assert not (records / name).exists()
    assert _read_decisions(root)[0]["body"] == "../docs/D-1.mark.md"
    assert _read_docs(root)[0]["body"] == "../docs/A-1.html"
    d1_row = yaml.safe_load((records / "history.yaml").read_text(encoding="utf-8"))["items"]["D-1"]
    assert [entry["before"]["body"] for entry in d1_row["history"]] == ["../docs/D-1.html"]
    assert [entry["seq"] for entry in d1_row["history"]] == [2]
    assert d1_row["updated"] == "2026-11-02T00:00:00+00:00"
    written = yaml.safe_load((records / "dev-docs.yaml").read_text(encoding="utf-8"))
    assert written["paths_base"] == ".."
    assert {row["id"]: row["paths"] for row in written["documents"]} == {
        row["id"]: [f".mindstella/{row['id']}.yaml"] for row in old_config["documents"]
    }
    written.pop("paths_base")
    for row in [*written["documents"], *old_config["documents"]]:
        row.pop("paths")
    assert written == old_config
    # もう一度当てても、ワークスペースが変わらない
    after = snapshot_tree(root)
    again = _migrate(root)
    assert again.error is None, again.text
    assert snapshot_tree(root) == after


@pytest.mark.parametrize(
    ("folder", "file_name", "with_files"),
    [
        pytest.param("docs", "memo.md", True, id="root-docs"),
        pytest.param("files", "memo.png", False, id="root-files-without-records-files"),
    ],
)
def test_error_when_root_docs_exists(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    folder: str,
    file_name: str,
    with_files: bool,
) -> None:
    """直下に利用者の docs/ か files/ があるとき、手順が失敗して写しから戻す（異常系）。"""
    # 準備
    root = _make_root_move_workspace(make_workspace, make_item, with_files=with_files)
    (root / folder).mkdir()
    (root / folder / file_name).write_text("利用者のファイル\n", encoding="utf-8")
    before = snapshot_tree(root)
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error == "StepFailedError"
    assert result.text.startswith("v0.14.0 の手順 3（call）:")
    assert f"{folder}/" in result.text
    assert "改名" in result.text
    assert snapshot_tree(root) == before
    assert _read_version(root) == "v0.13.0"


@pytest.mark.parametrize(
    ("display", "expected_display"),
    [
        pytest.param({"network_look": "starlight"}, None, id="display_emptied"),
        pytest.param(
            {"network_look": "glow", "visible_kinds": ["decisions", "tasks"]},
            {"visible_kinds": ["decisions", "tasks"]},
            id="kinds_kept",
        ),
    ],
)
def test_normal_when_network_look_removed(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    snapshot_tree: SnapshotTree,
    display: dict[str, Any],
    expected_display: dict[str, Any] | None,
) -> None:
    """v0.14.0 の手順で、config.yaml の display から network_look を消し、空になった display も消す（正常系）。"""
    # 準備
    root = make_workspace(settings={**valid_settings, "display": display}, legacy_bodies=True)
    records = root / RECORD_DIR
    (records / VERSION_FILE).write_text("v0.13.0\n", encoding="utf-8")
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error is None, result.text
    assert result.data is not None
    settings = yaml.safe_load((records / SETTINGS).read_text(encoding="utf-8"))
    assert {key: value for key, value in settings.items() if key != "display"} == valid_settings
    assert settings.get("display") == expected_display
    v0_14_steps = [step for step in result.data["steps"] if step["version"] == "v0.14.0"]
    assert (v0_14_steps[3]["index"], v0_14_steps[3]["op"], v0_14_steps[3]["destructive"]) == (
        4,
        "call",
        True,
    )
    assert _read_version(root) == PLUGIN_VERSION
    # もう一度当てても、ワークスペースが変わらない
    after = snapshot_tree(root)
    again = _migrate(root)
    assert again.error is None, again.text
    assert snapshot_tree(root) == after


def test_normal_when_preview_port_removed(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    snapshot_tree: SnapshotTree,
) -> None:
    """v0.14.0 の手順で、config.yaml からプレビューの配信の設定 preview を消す（正常系）。"""
    # 準備
    root = make_workspace(
        settings={**valid_settings, "preview": {"port": FIXED_PREVIEW_PORT}}, legacy_bodies=True
    )
    records = root / RECORD_DIR
    (records / VERSION_FILE).write_text("v0.13.0\n", encoding="utf-8")
    # 実行
    result = _migrate(root)
    # 検証
    assert result.error is None, result.text
    assert result.data is not None
    settings = yaml.safe_load((records / SETTINGS).read_text(encoding="utf-8"))
    assert settings == valid_settings
    v0_14_steps = [step for step in result.data["steps"] if step["version"] == "v0.14.0"]
    assert (v0_14_steps[4]["index"], v0_14_steps[4]["op"], v0_14_steps[4]["destructive"]) == (
        5,
        "call",
        True,
    )
    # もう一度当てても、ワークスペースが変わらない
    after = snapshot_tree(root)
    again = _migrate(root)
    assert again.error is None, again.text
    assert snapshot_tree(root) == after
