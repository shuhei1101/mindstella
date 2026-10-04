"""設定（mindmap.yaml）の `field` を、同じ位置の `playbooks` の 1 件の配列へ移す（v0.5.0 の移し替え）。"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from store import dump_yaml, remove_files, write_temp

# 設定のファイル名
SETTINGS_FILE = "mindmap.yaml"


def migrate(root: Path) -> list[str]:
    """`field` を `playbooks` の 1 件の配列へ移し、変えたファイルの名前を返す（変えなければ空）。"""
    path = root / SETTINGS_FILE
    settings = yaml.safe_load(path.read_text(encoding="utf-8"))
    # 設定が辞書でない: field を探せないので、理由の分かる失敗にする
    if not isinstance(settings, dict):
        raise ValueError(f"{SETTINGS_FILE} の中身が辞書ではありません")
    # field が無い: 移すものが無いので何も書かない
    if "field" not in settings:
        return []
    # field と playbooks が両方ある: どちらを正とするか決められない
    if "playbooks" in settings:
        raise ValueError("field と playbooks を両方持ちます")
    # キーの並びを保ち、field の位置に playbooks を置く
    moved = {
        ("playbooks" if key == "field" else key): ([value] if key == "field" else value)
        for key, value in settings.items()
    }
    temp = write_temp(path, dump_yaml(moved))
    try:
        os.replace(temp, path)
    except OSError:
        # 置き換えられなかった一時ファイルは残さず、元の失敗を送り直す
        remove_files([temp])
        raise
    return [SETTINGS_FILE]
