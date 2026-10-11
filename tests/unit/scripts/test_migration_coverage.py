"""開発側の点検：ワークスペースの形（スキーマ）を変えた PR（任意のキーを足すだけの変更を除く）が、版を上げて移し替えの手順を足しているか。

最新のタグを読むため、タグを取っていない clone では先に `git fetch --tags` を流す（タグが 1 つも無ければ skip する）。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

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


def _without_added_optional_keys(*, tagged: Any, current: Any) -> Any:
    """今のスキーマから、タグの時点に無かった任意のキー（`properties` に増えて `required` に入っていないもの）を除いて返す。"""
    # 入れ子のオブジェクト: キーごとに、タグの時点の同じ場所と比べる
    if isinstance(tagged, dict) and isinstance(current, dict):
        required = set(current.get("required", []))
        result: dict[str, Any] = {}
        for key, value in current.items():
            tagged_properties = tagged.get("properties")
            if key == "properties" and isinstance(value, dict) and isinstance(tagged_properties, dict):
                # 増えたキーのうち、任意のものは除く（必須のものは残し、差として見える）
                result[key] = {
                    name: _without_added_optional_keys(tagged=tagged_properties.get(name), current=sub)
                    for name, sub in value.items()
                    if name in tagged_properties or name in required
                }
            else:
                result[key] = _without_added_optional_keys(tagged=tagged.get(key), current=value)
        return result
    # 同じ長さの配列: 要素ごとに比べる
    if isinstance(tagged, list) and isinstance(current, list) and len(tagged) == len(current):
        return [
            _without_added_optional_keys(tagged=before, current=after)
            for before, after in zip(tagged, current, strict=True)
        ]
    return current


def _schema_change_needs_migration(*, tagged: dict[str, Any], current: dict[str, Any]) -> bool:
    """タグの時点のスキーマから今のスキーマへの違いが、任意のキーを足しただけに限られなければ真を返す。"""
    return _without_added_optional_keys(tagged=tagged, current=current) != tagged


def _schemas_changed_since(tag: Version) -> bool:
    """タグの時点にあったスキーマのファイルが消えたか、任意のキーを足しただけでない違いがあるかを返す（足したファイルは比べない）。"""
    current_dir = REPO_ROOT / SCHEMA_RELATIVE_DIR
    tagged_names = sorted(_schema_names_at(tag))
    # タグの時点にあったファイルが消えた
    if any(not (current_dir / name).exists() for name in tagged_names):
        return True
    # タグの時点にあったファイルの中身の違い（任意のキーを足しただけなら、既存のワークスペースがそのまま通るので変わりとしない）
    for name in tagged_names:
        shown = _git("show", f"{tag}:{SCHEMA_RELATIVE_DIR}/{name}")
        tagged_schema = json.loads(shown.stdout)
        current_schema = json.loads((current_dir / name).read_text(encoding="utf-8"))
        if _schema_change_needs_migration(tagged=tagged_schema, current=current_schema):
            return True
    return False


def test_schema_changes_have_migration() -> None:
    """最新のタグからスキーマが任意のキーの追加より大きく変わったら、タグより新しくプラグインの版以下の手順がある（正常系）。"""
    # 準備
    latest = _latest_tag()
    if latest is None:
        pytest.skip("版のタグが 1 つも無い clone では確かめない")
    changed = _schemas_changed_since(latest)
    plugin_version = versions.read_plugin_version()
    covering = [
        version for version in migrator.list_versions() if latest < version <= plugin_version
    ]
    # 検証
    assert covering != [] or not changed, (
        f"スキーマが {latest} から変わっているのに、{latest} より新しく {plugin_version} 以下の"
        "版の手順が migrations/ にありません。版を上げて手順を足してください"
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


# 項目の形のスキーマ（`items` の中に `properties` と `required` を持つ）
BASE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id"],
                "properties": {"id": {"type": "string"}, "title": {"type": "string"}},
                "additionalProperties": False,
            },
        }
    },
}


def _with_item_schema(**changes: Any) -> dict[str, Any]:
    """BASE_SCHEMA の `items` の中の項目のスキーマに、渡した値を重ねた写しを返す。"""
    schema = json.loads(json.dumps(BASE_SCHEMA))
    schema["properties"]["items"]["items"].update(changes)
    return schema


@pytest.mark.parametrize(
    ("current", "expected"),
    [
        pytest.param(BASE_SCHEMA, False, id="same"),
        pytest.param(
            _with_item_schema(
                properties={
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "aliases": {"type": "array", "items": {"type": "string", "minLength": 1}},
                }
            ),
            False,
            id="optional_key_added",
        ),
        pytest.param(
            _with_item_schema(
                required=["id", "kind"],
                properties={
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "kind": {"type": "string"},
                },
            ),
            True,
            id="required_key_added",
        ),
        pytest.param(
            _with_item_schema(properties={"id": {"type": "integer"}, "title": {"type": "string"}}),
            True,
            id="key_type_changed",
        ),
        pytest.param(
            _with_item_schema(properties={"id": {"type": "string"}}),
            True,
            id="key_removed",
        ),
        pytest.param(_with_item_schema(additionalProperties=True), True, id="additional_changed"),
        pytest.param(
            _with_item_schema(
                properties={
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "aliases": {"type": "array"},
                },
                additionalProperties=True,
            ),
            True,
            id="optional_key_added_with_other_change",
        ),
    ],
)
def test_schema_change_needs_migration(current: dict[str, Any], expected: bool) -> None:
    """任意のキーを足しただけの違いは手順を求めず、それ以外の違いは求める（正常系）。"""
    # 準備
    tagged = BASE_SCHEMA
    # 実行
    result = _schema_change_needs_migration(tagged=tagged, current=current)
    # 検証
    assert result is expected
