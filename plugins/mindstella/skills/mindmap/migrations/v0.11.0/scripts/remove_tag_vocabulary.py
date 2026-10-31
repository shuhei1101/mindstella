"""設定からタグの語彙（`tags`）を削除する（v0.11.0 の移し替え）。"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from store import RECORD_DIR, dump_yaml, remove_files, write_temp

# 設定のファイルの、ワークスペースからの相対パス
CONFIG_PATH = f"{RECORD_DIR}/config.yaml"

# 削除するキー
VOCABULARY_KEY = "tags"


def migrate(root: Path) -> list[str]:
    """設定から `tags` を削除して書き、変えたファイルの名前を返す（設定か `tags` が無ければ空）。"""
    config_path = root / CONFIG_PATH
    # 設定が無い: 何も書かない
    if not config_path.is_file():
        return []
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    # 一番上が辞書でない
    if not isinstance(config, dict):
        raise ValueError(f"{CONFIG_PATH} の形が崩れています")
    # tags が無い: 何も書かない
    if VOCABULARY_KEY not in config:
        return []
    # 他のキーの並びを保って tags を削除する
    updated = {key: value for key, value in config.items() if key != VOCABULARY_KEY}
    temp = write_temp(config_path, dump_yaml(updated))
    try:
        os.replace(temp, config_path)
    except OSError:
        # 置き換えられなかった一時ファイルは残さず、元の失敗を送り直す
        remove_files([temp])
        raise
    return [CONFIG_PATH]
