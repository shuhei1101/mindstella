"""本文の Markdown を mdmark の文書の拡張子 .mark.md へ改名し、項目の body と変更履歴の before.body を書き換える（v0.14.0 の移し替え）。"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

# 記録のフォルダ（ワークスペースの直下からの相対パス）
RECORD_DIR = ".mindstella"

# 本文を置くフォルダ（記録のフォルダからの相対パス）
BODY_DIR = "docs"

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

# 改名する前の Markdown の本文の拡張子
MARKDOWN_SUFFIX = ".md"

# mdmark の文書の拡張子
MARK_SUFFIX = ".mark.md"


def migrate(root: Path) -> list[str]:
    """`docs/` の直下の .mark.md でない *.md を改名し、それを指す body と before.body を書き換えて、変えたファイルを返す。"""
    records = root / RECORD_DIR
    renames = _collect_renames(records / BODY_DIR)
    writes: dict[Path, str] = {}
    # 種類ごとの YAML の項目の body を書き換える
    for file_name in KIND_FILES:
        path = records / file_name
        data = _load(path)
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            continue
        new_items = [_renamed_item(item) for item in items]
        if new_items != items:
            writes[path] = _dump({**data, "items": new_items})
    # 変更履歴の各回の before.body を書き換える
    history_path = records / HISTORY_FILE
    history = _load(history_path)
    rows = history.get("items") if isinstance(history, dict) else None
    if isinstance(rows, dict):
        new_rows = {item_id: _renamed_row(row) for item_id, row in rows.items()}
        if new_rows != rows:
            writes[history_path] = _dump({**history, "items": new_rows})
    for source, target in renames:
        os.replace(source, target)
    _replace_all(writes)
    return [path.relative_to(root).as_posix() for path in [*writes, *(target for _, target in renames)]]


def _collect_renames(body_dir: Path) -> list[tuple[Path, Path]]:
    """改名する本文と改名先を名前の順に返す。改名先が既にあれば何も書かずに送る。"""
    if not body_dir.is_dir():
        return []
    renames = [
        (path, path.with_name(_mark_name(path.name)))
        for path in sorted(body_dir.glob(f"*{MARKDOWN_SUFFIX}"))
        if path.is_file() and not path.name.endswith(MARK_SUFFIX)
    ]
    existing = [target for _, target in renames if target.exists()]
    # 改名先が既にある: 上書きしないよう、どのファイルも書き換えずに止める
    if existing:
        names = "、".join(f"{BODY_DIR}/{target.name}" for target in existing)
        raise RuntimeError(f"改名先の本文が既にあります: {names}")
    return renames


def _mark_name(name: str) -> str:
    """`{名前}.md` を `{名前}.mark.md` にする。"""
    return f"{name.removesuffix(MARKDOWN_SUFFIX)}{MARK_SUFFIX}"


def _renamed_body(body: Any) -> Any:
    """`docs/{名前}.md` の body を `docs/{名前}.mark.md` にする（ほかの値はそのまま）。"""
    if (
        isinstance(body, str)
        and body.startswith(f"{BODY_DIR}/")
        and body.endswith(MARKDOWN_SUFFIX)
        and not body.endswith(MARK_SUFFIX)
    ):
        return _mark_name(body)
    return body


def _renamed_item(item: Any) -> Any:
    """項目の body を改名後のパスにした項目を返す（書き換えが無ければ同じ項目）。"""
    if not isinstance(item, dict) or "body" not in item:
        return item
    body = _renamed_body(item["body"])
    return item if body == item["body"] else {**item, "body": body}


def _renamed_row(row: Any) -> Any:
    """変更履歴の行の各回の before.body を改名後のパスにした行を返す（書き換えが無ければ同じ行）。"""
    entries = row.get("history") if isinstance(row, dict) else None
    if not isinstance(entries, list):
        return row
    new_entries = [_renamed_entry(entry) for entry in entries]
    return row if new_entries == entries else {**row, "history": new_entries}


def _renamed_entry(entry: Any) -> Any:
    """変更履歴の 1 回の before.body を改名後のパスにした回を返す（書き換えが無ければ同じ回）。"""
    before = entry.get("before") if isinstance(entry, dict) else None
    if not isinstance(before, dict) or "body" not in before:
        return entry
    body = _renamed_body(before["body"])
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
