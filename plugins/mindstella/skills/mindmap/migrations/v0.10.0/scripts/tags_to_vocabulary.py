"""項目とスレッドが使っているタグを、説明なしで設定の語彙（`tags`）へ登録する（v0.10.0 の移し替え）。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from kinds import KINDS
from store import RECORD_DIR, dump_yaml, remove_files, write_temp

# 設定のファイルの、ワークスペースからの相対パス
CONFIG_PATH = f"{RECORD_DIR}/config.yaml"

# スレッドのファイルの、ワークスペースからの相対パス
THREADS_PATH = f"{RECORD_DIR}/threads.yaml"

# 語彙を置くキーと、無いときにその後ろへ置くキー
VOCABULARY_KEY = "tags"
VOCABULARY_AFTER_KEY = "categories"


def migrate(root: Path) -> list[str]:
    """使っているタグを語彙へ足して書き、変えたファイルの名前を返す（足すものも並びの変わりも無ければ空）。"""
    config_path = root / CONFIG_PATH
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    # 一番上が辞書でない
    if not isinstance(config, dict):
        raise ValueError(f"{CONFIG_PATH} の形が崩れています")
    current = _vocabulary_entries(config.get(VOCABULARY_KEY))
    known = {entry["name"] for entry in current}
    # 今の語彙に無い名前だけを足し、全体を名前の順に並べる（今の要素の説明は残す）
    added = [{"name": name} for name in sorted(_used_tags(root) - known)]
    entries = sorted([*current, *added], key=lambda entry: entry["name"])
    # 足す名前が無く、並びも変わらない: 何も書かない
    if not added and entries == current:
        return []
    updated = _with_vocabulary(config, entries)
    temp = write_temp(config_path, dump_yaml(updated))
    try:
        os.replace(temp, config_path)
    except OSError:
        # 置き換えられなかった一時ファイルは残さず、元の失敗を送り直す
        remove_files([temp])
        raise
    return [CONFIG_PATH]


def _vocabulary_entries(tags: Any) -> list[dict[str, Any]]:
    """設定の `tags` のうち、名前が空でない文字列の要素だけを返す。"""
    if not isinstance(tags, list):
        return []
    return [
        entry
        for entry in tags
        if isinstance(entry, dict) and isinstance(entry.get("name"), str) and entry["name"]
    ]


def _used_tags(root: Path) -> set[str]:
    """種類ごとの YAML の項目とスレッドが持つ `tags` の、空でない文字列を集める（読めないファイルと形の合わない要素は飛ばす）。"""
    names: set[str] = set()
    files = [f"{RECORD_DIR}/{spec.file}" for spec in KINDS.values()] + [THREADS_PATH]
    for relative in files:
        path = root / relative
        # 無いファイルは飛ばす
        if not path.is_file():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            continue
        for item in items:
            tags = item.get("tags") if isinstance(item, dict) else None
            if isinstance(tags, list):
                names.update(tag for tag in tags if isinstance(tag, str) and tag)
    return names


def _with_vocabulary(config: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    """設定のキーの並びを保って `tags` を置き換える（無ければ `categories` の後ろ、それも無ければ末尾に置く）。"""
    # 語彙のキーが既にある: その位置で置き換える
    if VOCABULARY_KEY in config:
        return {key: (entries if key == VOCABULARY_KEY else value) for key, value in config.items()}
    updated: dict[str, Any] = {}
    for key, value in config.items():
        updated[key] = value
        # categories の後ろに置く
        if key == VOCABULARY_AFTER_KEY:
            updated[VOCABULARY_KEY] = entries
    # categories が無かった: 末尾に置く
    updated.setdefault(VOCABULARY_KEY, entries)
    return updated
