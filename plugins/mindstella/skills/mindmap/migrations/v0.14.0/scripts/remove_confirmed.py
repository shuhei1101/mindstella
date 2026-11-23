"""項目の履歴から確認済み `confirmed` を、設定から `confirm_on_comment` を消す（v0.14.0 の移し替え）。"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

# 書き換える項目の履歴（ワークスペースの直下からの相対パス）
HISTORY_FILE = ".mindstella/history.yaml"

# 書き換える設定（ワークスペースの直下からの相対パス）
CONFIG_FILE = ".mindstella/config.yaml"

# 項目の履歴の `items` の行から消すキー
REMOVED_ROW_KEY = "confirmed"

# 設定から消すキー
REMOVED_SETTING_KEY = "confirm_on_comment"


def migrate(root: Path) -> list[str]:
    """`history.yaml` の行から `confirmed` を、`config.yaml` から `confirm_on_comment` を消して、変えたファイルを返す。"""
    history_path = root / HISTORY_FILE
    config_path = root / CONFIG_FILE
    # 両方を読み終えてから書く（片方が読めなければ、どちらも書き換えない）
    history = _load(history_path) if history_path.is_file() else None
    config = _load(config_path) if config_path.is_file() else None
    writes: list[tuple[str, Path, Any]] = []
    new_history = _without_confirmed(history)
    # 確認済みを持つ行があった: 履歴を書き換える
    if new_history is not None:
        writes.append((HISTORY_FILE, history_path, new_history))
    # 設定がオブジェクトで、消すキーを持つ: 設定を書き換える（ほかのキーの並びは保つ）
    if isinstance(config, dict) and REMOVED_SETTING_KEY in config:
        new_config = {key: value for key, value in config.items() if key != REMOVED_SETTING_KEY}
        writes.append((CONFIG_FILE, config_path, new_config))
    for _, path, data in writes:
        _replace(path, yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    return [name for name, _, _ in writes]


def _without_confirmed(history: Any) -> dict[str, Any] | None:
    """行から `confirmed` を消した履歴を返す。消す行が無ければ None を返す。"""
    # 履歴が無い・行の辞書を持たない: 変えない
    if not isinstance(history, dict) or not isinstance(history.get("items"), dict):
        return None
    items: dict[str, Any] = {}
    changed = False
    for item_id, row in history["items"].items():
        # 確認済みを持たない行はそのまま残す
        if not isinstance(row, dict) or REMOVED_ROW_KEY not in row:
            items[item_id] = row
            continue
        changed = True
        rest = {key: value for key, value in row.items() if key != REMOVED_ROW_KEY}
        # 確認済みだけを持っていた行は、行ごと消す
        if rest:
            items[item_id] = rest
    if not changed:
        return None
    return {**history, "items": items}


def _load(path: Path) -> Any:
    """YAML を読む。読めなければ RuntimeError を送る。"""
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise RuntimeError(f"{path.name} を YAML として読めません") from error


def _replace(path: Path, text: str) -> None:
    """一時ファイルに書いてから置き換える。途中で失敗したら残った一時ファイルを消す。"""
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)
