"""項目の `body` のファイル名を、記録のフォルダからのパス（`docs/{ファイル名}`）にする（v0.13.0 の移し替え）。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from kinds import BODY_DIR, KINDS
from store import RECORD_DIR, dump_yaml, remove_files, write_temp


def migrate(root: Path) -> list[str]:
    """種類ごとの YAML の項目の body を docs/ からのパスにし、変えたファイルを種類の順に返す（変えなければ空）。"""
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
    """`/` を含まない body を `docs/{body}` にした新しい項目を返す（`updated`・`history` は変えない）。"""
    if not isinstance(item, dict):
        return item
    body = item.get("body")
    if not isinstance(body, str) or "/" in body:
        return item
    return {**item, "body": f"{BODY_DIR}/{body}"}
