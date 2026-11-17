"""項目の作成日時・更新日時・編集した人・通し番号・変更履歴を、値を変えずに `history.yaml` へ移す（v0.13.0 の移し替え）。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from kinds import HISTORY_FILE, KINDS
from store import RECORD_DIR, dump_yaml, remove_files, write_temp

# history.yaml へ移すキー
META_KEYS = ("created", "updated", "updated_by", "seq", "added_seq", "history", "history_dropped_seq")


def migrate(root: Path) -> list[str]:
    """種類ごとの YAML の項目の履歴のキーを history.yaml へ移し、書いたファイルを返す（変えなければ空）。"""
    history_relative = f"{RECORD_DIR}/{HISTORY_FILE}"
    history_path = root / history_relative
    rows = _read_rows(history_path)
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
    targets: list[tuple[str, str]] = []
    for relative, data in loaded:
        items: list[Any] = []
        moved = False
        for item in data["items"]:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                items.append(item)
                continue
            meta = {key: item[key] for key in META_KEYS if key in item}
            if not meta:
                items.append(item)
                continue
            # 行が既にキーを持てば上書きしない
            rows[item["id"]] = {**meta, **rows.get(item["id"], {})}
            items.append({key: value for key, value in item.items() if key not in META_KEYS})
            moved = True
        if moved:
            targets.append((relative, dump_yaml({**data, "items": items})))
    if not targets:
        return []
    # history.yaml を先に、変えた種類の YAML をその後に置き換える
    targets.insert(0, (history_relative, dump_yaml({"items": rows})))
    for relative, text in targets:
        path = root / relative
        temp = write_temp(path, text)
        try:
            os.replace(temp, path)
        except OSError:
            remove_files([temp])
            raise
    return [relative for relative, _ in targets]


def _read_rows(path: Path) -> dict[str, Any]:
    """`history.yaml` の items を読む（無ければ空）。"""
    if not path.is_file():
        return {}
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    rows = value.get("items") if isinstance(value, dict) else None
    if not isinstance(rows, dict):
        raise ValueError(f"{RECORD_DIR}/{HISTORY_FILE} の形が崩れています")
    return rows
