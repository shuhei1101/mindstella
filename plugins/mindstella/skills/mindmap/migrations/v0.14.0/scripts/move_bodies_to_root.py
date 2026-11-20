"""本文と埋め込むファイルのフォルダをワークスペースの直下へ移し、本文の参照と配信の設定を書き換えて、release/ を消す（v0.14.0 の移し替え）。"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import yaml

# 記録のフォルダ（ワークスペースの直下からの相対パス）
RECORD_DIR = ".mindstella"

# 記録のフォルダから直下へ同じ名前で移すフォルダ（本文と埋め込むファイル）
MOVED_DIRS = ("docs", "files")

# 消す記録のフォルダの中のフォルダ（書き出した資料のコピー）
RELEASE_DIR = "release"

# body を書き換える種類ごとの YAML（記録のフォルダからの相対パス）
KIND_FILES = (
    "decisions.yaml",
    "tasks.yaml",
    "research.yaml",
    "docs.yaml",
    "terms.yaml",
    "notes.yaml",
    "logs.yaml",
)

# before.body を書き換える変更履歴の YAML（記録のフォルダからの相対パス）
HISTORY_FILE = "history.yaml"

# paths_base・paths を書き換える配信の設定（記録のフォルダからの相対パス）
SOURCE_CONFIG_FILE = "dev-docs.yaml"

# 書き換える body・before.body の値の頭
OLD_BODY_PREFIX = "docs/"

# 書き換えた後の値の頭（記録のフォルダから直下の docs/ を指す）
NEW_BODY_PREFIX = "../docs/"

# 配信の設定に足す paths_base の値。このキーを持つ設定は移し替え済みとして扱う
PATHS_BASE = ".."


def migrate(root: Path) -> list[str]:
    """本文と埋め込むファイルを直下へ移し、本文の参照と配信の設定を書き換え、release/ を消して、変えたファイルとフォルダを返す。"""
    records = root / RECORD_DIR
    config_path = records / SOURCE_CONFIG_FILE
    config = _load(config_path)
    migrated = isinstance(config, dict) and "paths_base" in config
    # まだ移し替えていないのに直下に同じ名前のフォルダがある: 利用者のファイルと混ぜず、何も書かずに止める
    if not migrated:
        existing = [name for name in MOVED_DIRS if (root / name).exists()]
        if existing:
            names = "、".join(f"{name}/" for name in existing)
            raise RuntimeError(
                f"ワークスペースの直下に {names} が既にあります。改名してからワークスペースを開き直してください"
            )
    writes: dict[Path, str] = {}
    # 種類ごとの YAML の項目の body を書き換える
    for file_name in KIND_FILES:
        path = records / file_name
        data = _load(path)
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            continue
        new_items = [_moved_item(item) for item in items]
        if new_items != items:
            writes[path] = _dump({**data, "items": new_items})
    # 変更履歴の各回の before.body を書き換える
    history_path = records / HISTORY_FILE
    history = _load(history_path)
    rows = history.get("items") if isinstance(history, dict) else None
    if isinstance(rows, dict):
        new_rows = {item_id: _moved_row(row) for item_id, row in rows.items()}
        if new_rows != rows:
            writes[history_path] = _dump({**history, "items": new_rows})
    # 移し替えていない配信の設定: paths_base を足し、種類の行の paths を直下からのパスにする
    if isinstance(config, dict) and not migrated:
        writes[config_path] = _dump(_moved_config(config))
    _replace_all(writes)
    changed = [path.relative_to(root).as_posix() for path in writes]
    # 記録のフォルダにある本文と埋め込むファイルのフォルダを直下へ移す
    for name in MOVED_DIRS:
        source = records / name
        if source.is_dir():
            os.replace(source, root / name)
            changed.append(f"{name}/")
    # 書き出した資料のコピーを消す
    release = records / RELEASE_DIR
    if release.is_dir():
        shutil.rmtree(release)
        changed.append(f"{RECORD_DIR}/{RELEASE_DIR}/")
    return changed


def _moved_config(config: dict[str, Any]) -> dict[str, Any]:
    """paths_base を足し、種類の行の paths を記録のフォルダの中の YAML を直下から指すパスにした設定を返す。"""
    kind_files = {file_name.removesuffix(".yaml"): file_name for file_name in KIND_FILES}
    documents = config.get("documents")
    new_documents = documents
    if isinstance(documents, list):
        new_documents = [
            # 種類の行だけを書き換える（ほかの行は利用者が書いたものとして残す）
            {**row, "paths": [f"{RECORD_DIR}/{kind_files[row['id']]}"]}
            if isinstance(row, dict) and row.get("id") in kind_files
            else row
            for row in documents
        ]
    return {**config, "documents": new_documents, "paths_base": PATHS_BASE}


def _moved_body(body: Any) -> Any:
    """`docs/` で始まる body を `../docs/` で始まる値にする（ほかの値はそのまま）。"""
    if isinstance(body, str) and body.startswith(OLD_BODY_PREFIX):
        return f"{NEW_BODY_PREFIX}{body.removeprefix(OLD_BODY_PREFIX)}"
    return body


def _moved_item(item: Any) -> Any:
    """項目の body を直下の本文を指すパスにした項目を返す（書き換えが無ければ同じ項目）。"""
    if not isinstance(item, dict) or "body" not in item:
        return item
    body = _moved_body(item["body"])
    return item if body == item["body"] else {**item, "body": body}


def _moved_row(row: Any) -> Any:
    """変更履歴の行の各回の before.body を直下の本文を指すパスにした行を返す（書き換えが無ければ同じ行）。"""
    entries = row.get("history") if isinstance(row, dict) else None
    if not isinstance(entries, list):
        return row
    new_entries = [_moved_entry(entry) for entry in entries]
    return row if new_entries == entries else {**row, "history": new_entries}


def _moved_entry(entry: Any) -> Any:
    """変更履歴の 1 回の before.body を直下の本文を指すパスにした回を返す（書き換えが無ければ同じ回）。"""
    before = entry.get("before") if isinstance(entry, dict) else None
    if not isinstance(before, dict) or "body" not in before:
        return entry
    body = _moved_body(before["body"])
    return entry if body == before["body"] else {**entry, "before": {**before, "body": body}}


def _load(path: Path) -> Any:
    """YAML を読む。無ければ None。"""
    if not path.is_file():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise RuntimeError(f"{path.name} を YAML として読めません") from error


def _dump(data: Any) -> str:
    """記録の YAML の書き方（日本語をそのまま・キーの並びを保つ）で文字列にする。"""
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def _replace_all(writes: dict[Path, str]) -> None:
    """全てのファイルを一時ファイルに書いてから置き換える。途中で失敗したら残った一時ファイルを消す。"""
    temps: list[tuple[Path, Path]] = []
    try:
        for path, text in writes.items():
            handle, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(text)
            temps.append((Path(temp), path))
        for temp, path in temps:
            os.replace(temp, path)
    finally:
        for temp, _ in temps:
            temp.unlink(missing_ok=True)
