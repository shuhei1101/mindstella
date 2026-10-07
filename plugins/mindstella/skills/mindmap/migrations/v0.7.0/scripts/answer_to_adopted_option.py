"""決定済みで答えを持ち案を持たない検討事項に、答えから採用した案を 1 つ作る（v0.7.0 の移し替え）。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from store import RECORD_DIR, dump_yaml, remove_files, write_temp

# 検討事項のファイルの、ワークスペースからの相対パス
DECISIONS_PATH = f"{RECORD_DIR}/decisions.yaml"

# 答えから作る案の記号
ADOPTED_KEY = "A"


def migrate(root: Path) -> list[str]:
    """答えから採用した案を作り、変えたファイルの名前を返す（変えなければ空）。"""
    path = root / DECISIONS_PATH
    # decisions.yaml が無い: 移すものが無いので何も書かない
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    # 一番上が辞書でない・items が配列でない: 形の崩れは点検の schema が拾うので何も書かない
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return []
    changed = False
    for item in data["items"]:
        # 辞書でない要素と、案を作る対象でない検討事項は変えない
        if not _needs_option(item):
            continue
        option: dict[str, Any] = {"key": ADOPTED_KEY, "content": item["answer"]}
        # 理由を持つ検討事項は、案にも理由を入れる
        if isinstance(item.get("reason"), str) and item["reason"] != "":
            option["reason"] = item["reason"]
        option["adopted"] = True
        item["options"] = [option]
        changed = True
    # 1 件も変えなかった: 何も書かない
    if not changed:
        return []
    temp = write_temp(path, dump_yaml(data))
    try:
        os.replace(temp, path)
    except OSError:
        # 置き換えられなかった一時ファイルは残さず、元の失敗を送り直す
        remove_files([temp])
        raise
    return [DECISIONS_PATH]


def _needs_option(item: Any) -> bool:
    """決定済みで答えを持ち、案を持たない検討事項か。"""
    return (
        isinstance(item, dict)
        and item.get("status") == "決定済み"
        and isinstance(item.get("answer"), str)
        and item["answer"] != ""
        and not item.get("options")
    )
