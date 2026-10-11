"""開発側の点検：ワークスペースの形（スキーマ）を変えた PR が、版を上げて移し替えの手順を足しているか。

今のワークスペースがそのまま読める変更は、手順の代わりに `migrations/no-steps.yaml` に変えたスキーマの中身のハッシュを載せて通す。

最新のタグを読むため、タグを取っていない clone では先に `git fetch --tags` を流す（タグが 1 つも無ければ skip する）。
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest
import yaml

import migrator
import versions
from versions import Version

# このファイルから見たリポジトリの直下（tests/unit/scripts の 3 つ上）
REPO_ROOT_PARENT_DEPTH = 3
REPO_ROOT = Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH]

# リリースの版を持つファイル（リポジトリの直下の version.ini）
RELEASE_VERSION_FILE = REPO_ROOT / "version.ini"

# スキーマの置き場所（リポジトリの直下からの相対パス）
SCHEMA_RELATIVE_DIR = "plugins/mindstella/skills/mindmap/schemas"

# 移し替えの手順の形のスキーマ。ワークスペースの形ではないので、比べない
STEPS_SCHEMA_NAME = "migration-steps.schema.json"

# 手順の要らない変更の一覧（変えたスキーマのファイル名・変えた後の中身の SHA-256・理由）
NO_STEPS_FILE = REPO_ROOT / "plugins/mindstella/skills/mindmap/migrations/no-steps.yaml"


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    """リポジトリの直下で git を呼び、終了コードが 0 以外でも例外にせず返す。"""
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _latest_tag() -> Version | None:
    """`v{メジャー}.{マイナー}.{パッチ}` のタグのうち、版が最も新しいものを返す。タグが無ければ None。"""
    tags: list[Version] = []
    for name in _git("tag", "--list", "v*").stdout.split():
        # 版の形でないタグは、版の順に並べないので飛ばす
        try:
            tags.append(versions.parse_release_version(name))
        except ValueError:
            continue
    return max(tags) if tags else None


def _schema_names_at(tag: Version) -> set[str]:
    """タグの時点のスキーマのファイル名を返す（手順の形のスキーマを除く）。"""
    listed = _git("ls-tree", "--name-only", str(tag), f"{SCHEMA_RELATIVE_DIR}/").stdout.split()
    return {Path(name).name for name in listed if Path(name).name != STEPS_SCHEMA_NAME}


def _schema_hash(text: str) -> str:
    """スキーマの中身（UTF-8 の文字列）の SHA-256 を 16 進で返す。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _changed_schemas_since(tag: Version) -> tuple[list[str], list[str]]:
    """タグの時点にあったスキーマのうち、消えたものと中身が変わったものの名前を返す（足したファイルは比べない）。"""
    current_dir = REPO_ROOT / SCHEMA_RELATIVE_DIR
    removed: list[str] = []
    changed: list[str] = []
    for name in sorted(_schema_names_at(tag)):
        # タグの時点にあったファイルが消えた
        if not (current_dir / name).exists():
            removed.append(name)
            continue
        # タグの時点にあったファイルの中身の違い
        shown = _git("show", f"{tag}:{SCHEMA_RELATIVE_DIR}/{name}")
        if shown.stdout != (current_dir / name).read_text(encoding="utf-8"):
            changed.append(name)
    return removed, changed


def _no_steps_hashes() -> dict[str, str]:
    """手順の要らない変更の一覧から、スキーマのファイル名 → 載っている中身の SHA-256 を返す。"""
    entries = yaml.safe_load(NO_STEPS_FILE.read_text(encoding="utf-8"))
    return {entry["schema"]: entry["sha256"] for entry in entries}


def _unlisted_schemas(changed: list[str]) -> list[str]:
    """変えたスキーマのうち、一覧に今の中身のハッシュで載っていないものの名前を返す。"""
    listed = _no_steps_hashes()
    current_dir = REPO_ROOT / SCHEMA_RELATIVE_DIR
    return [
        name
        for name in changed
        if listed.get(name) != _schema_hash((current_dir / name).read_text(encoding="utf-8"))
    ]


def test_schema_changes_have_migration() -> None:
    """最新のタグからスキーマが変わったら、手順の要らない変更の一覧に今の中身で載るか、タグより新しくプラグインの版以下の手順がある（正常系）。"""
    # 準備
    latest = _latest_tag()
    if latest is None:
        pytest.skip("版のタグが 1 つも無い clone では確かめない")
    removed, changed = _changed_schemas_since(latest)
    # 一覧に今の中身のハッシュで載っていない変えたスキーマ（消えたスキーマは一覧で通さない）
    unlisted = _unlisted_schemas(changed)
    plugin_version = versions.read_plugin_version()
    covering = [
        version for version in migrator.list_versions() if latest < version <= plugin_version
    ]
    # 検証
    assert covering != [] or (removed == [] and unlisted == []), (
        f"スキーマが {latest} から変わっている（消えた: {removed}、一覧に載っていない: {unlisted}）のに、"
        f"{latest} より新しく {plugin_version} 以下の版の手順が migrations/ にありません。"
        "今のワークスペースが読めない変更なら版を上げて手順を足し、読める変更なら no-steps.yaml に行を足してください"
    )


def test_plugin_version_not_behind_release_version() -> None:
    """プラグインの版がリポジトリの直下の version.ini の版より前でない（正常系）。"""
    # 準備
    release_lines = RELEASE_VERSION_FILE.read_text(encoding="utf-8").splitlines()
    release_version = versions.parse_release_version(release_lines[0])
    # 実行
    plugin_version = versions.read_plugin_version()
    # 検証
    assert plugin_version >= release_version
