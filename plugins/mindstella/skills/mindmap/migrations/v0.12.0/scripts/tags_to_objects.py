"""項目の文字列のタグを `{name}` にし、表記をそろえて重なるタグを外す（v0.12.0 の移し替え）。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from kinds import KINDS
from store import RECORD_DIR, dump_yaml, remove_files, write_temp
from tag_text import normalize_tag, tag_name


def migrate(root: Path) -> list[str]:
    """種類ごとの YAML の項目のタグを移し、変えたファイルの名前を種類の順に返す（変えなければ空）。"""
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
        if not _convert_items(data["items"]):
            continue
        path = root / relative
        temp = write_temp(path, dump_yaml(data))
        try:
            os.replace(temp, path)
        except OSError:
            # 置き換えられなかった一時ファイルは残さず、元の失敗を送り直す
            remove_files([temp])
            raise
        changed.append(relative)
    return changed


def _convert_items(items: list[Any]) -> bool:
    """項目の `tags` を移し、1 件でも変えたかを返す（`updated`・`history` は変えない）。"""
    changed = False
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("tags"), list):
            continue
        converted = _convert_tags(item["tags"])
        if converted != item["tags"]:
            item["tags"] = converted
            changed = True
    return changed


def _convert_tags(tags: list[Any]) -> list[Any]:
    """文字列の要素を `{name}` にし、正規化した名前が前の要素と同じ要素を外す。"""
    seen: set[str] = set()
    converted: list[Any] = []
    for entry in tags:
        name = tag_name(entry)
        # 名前を取れない要素はそのまま残す
        if name is None:
            converted.append(entry)
            continue
        normalized = normalize_tag(name)
        if normalized in seen:
            continue
        seen.add(normalized)
        converted.append({"name": entry} if isinstance(entry, str) else entry)
    return converted
