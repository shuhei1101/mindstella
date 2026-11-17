"""検討事項・タスクの参照のキー（`depends_on`・`parent`・`for`）を、種類つきの `related` へ移す（v0.13.0 の移し替え）。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from kinds import KINDS
from store import RECORD_DIR, dump_yaml, remove_files, write_temp

# related へ移す参照のキー（並びは related に並べる順）
REF_KEYS = ("depends_on", "parent", "for")

# 元の related の ID の文字列に付ける種類
SEE_ALSO = "see_also"


def migrate(root: Path) -> list[str]:
    """種類ごとの YAML の項目の参照のキーを related へ移し、変えたファイルを種類の順に返す（変えなければ空）。"""
    loaded: list[tuple[str, dict[str, Any]]] = []
    # 全てのファイルを先に読み、形の崩れたファイルがあれば何も書かない
    for spec in KINDS.values():
        relative = f"{RECORD_DIR}/{spec.file}"
        path = root / relative
        if not path.is_file():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            raise ValueError(f"{relative} の形が崩れています")
        loaded.append((relative, data))
    changed: list[str] = []
    for relative, data in loaded:
        converted = [_convert(item) for item in data["items"]]
        if converted == data["items"]:
            continue
        path = root / relative
        temp = write_temp(path, dump_yaml({**data, "items": converted}))
        try:
            os.replace(temp, path)
        except OSError:
            # 置き換えられなかった一時ファイルは残さず、元の失敗を送り直す
            remove_files([temp])
            raise
        changed.append(relative)
    return changed


def _convert(item: Any) -> Any:
    """1 項目の参照のキーを related へ移した新しい項目を返す（`updated`・`history` は変えない）。"""
    if not isinstance(item, dict):
        return item
    old_related = item.get("related")
    if not any(key in item for key in REF_KEYS) and not (
        isinstance(old_related, list) and any(isinstance(entry, str) for entry in old_related)
    ):
        return item
    entries: list[Any] = []
    for key in REF_KEYS:
        value = item.get(key)
        targets = [value] if isinstance(value, str) else value if isinstance(value, list) else []
        entries.extend({"to": target, "type": key} for target in targets if isinstance(target, str))
    for entry in old_related if isinstance(old_related, list) else []:
        entries.append({"to": entry, "type": SEE_ALSO} if isinstance(entry, str) else entry)
    # 同じ to・type の組は最初の 1 件だけ残す
    unique: list[Any] = []
    for entry in entries:
        if entry not in unique:
            unique.append(entry)
    converted = {key: value for key, value in item.items() if key not in REF_KEYS}
    if unique:
        converted["related"] = unique
    else:
        converted.pop("related", None)
    return converted
