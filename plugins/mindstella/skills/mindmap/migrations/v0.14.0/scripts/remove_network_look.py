"""設定の表示の既定から、削除したネットワークの見た目の既定を消す（v0.14.0 の移し替え）。"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

# 書き換える設定（ワークスペースの直下からの相対パス）
CONFIG_FILE = ".mindstella/config.yaml"

# `display` から消すキー
REMOVED_KEY = "network_look"


def migrate(root: Path) -> list[str]:
    """`config.yaml` の `display` から `network_look` を消し、空になった `display` も消して、変えたファイルを返す。"""
    path = root / CONFIG_FILE
    # 設定を持たないワークスペースは何も変えない
    if not path.is_file():
        return []
    config = _load(path)
    display = config.get("display") if isinstance(config, dict) else None
    # 消すキーを持たない（移し替え済み・display を持たない）ときは書かない
    if not isinstance(display, dict) or REMOVED_KEY not in display:
        return []
    kept_display = {key: value for key, value in display.items() if key != REMOVED_KEY}
    # display が空になったら display ごと消し、ほかのキーの並びは保つ
    if kept_display:
        new_config = {key: (kept_display if key == "display" else value) for key, value in config.items()}
    else:
        new_config = {key: value for key, value in config.items() if key != "display"}
    _replace(path, yaml.safe_dump(new_config, allow_unicode=True, sort_keys=False))
    return [CONFIG_FILE]


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
