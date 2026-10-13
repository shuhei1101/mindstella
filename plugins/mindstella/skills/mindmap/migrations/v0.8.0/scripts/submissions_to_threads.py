"""送信（submissions.yaml）の 1 件ごとに、スレッド（threads.yaml）を 1 件作る（v0.8.0 の移し替え）。"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from store import RECORD_DIR, dump_yaml, remove_files, write_temp

# 送信のファイルの、ワークスペースからの相対パス
SUBMISSIONS_PATH = f"{RECORD_DIR}/submissions.yaml"

# スレッドのファイルの、ワークスペースからの相対パス
THREADS_PATH = f"{RECORD_DIR}/threads.yaml"

# 送信の ID（連番を取り出す）
SUBMISSION_ID = re.compile(r"^S-([0-9]+)$")

# 送信が必ず持つキー
REQUIRED_KEYS = ("id", "body", "sent", "taken")


def migrate(root: Path) -> list[str]:
    """送信をスレッドにして書き、変えたファイルの名前を返す（送信のファイルが無ければ空）。"""
    source = root / SUBMISSIONS_PATH
    # submissions.yaml が無い: 移すものが無いので何も書かない
    if not source.exists():
        return []
    destination = root / THREADS_PATH
    # threads.yaml が既にある: 二重に移さない
    if destination.exists():
        raise ValueError(f"{THREADS_PATH} が既にあるため、{SUBMISSIONS_PATH} を移せません")
    submissions = _load_submissions(source)
    threads = [_thread_of(number, submission) for number, submission in submissions]
    temp = write_temp(destination, dump_yaml({"items": threads}))
    try:
        os.replace(temp, destination)
    except OSError:
        # 置き換えられなかった一時ファイルは残さず、元の失敗を送り直す
        remove_files([temp])
        raise
    return [THREADS_PATH]


def _load_submissions(path: Path) -> list[tuple[int, dict[str, Any]]]:
    """送信を読み、連番の小さい順に（連番、送信）の並びで返す。形が崩れていれば ValueError にする。"""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    # 一番上が辞書でない・items が配列でない
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError(f"{SUBMISSIONS_PATH}: items の配列がありません")
    submissions: list[tuple[int, dict[str, Any]]] = []
    for index, item in enumerate(data["items"]):
        # 辞書でない・必要なキーが無い・ID が S-{連番} でない
        if not isinstance(item, dict) or any(key not in item for key in REQUIRED_KEYS):
            raise ValueError(f"{SUBMISSIONS_PATH}: items[{index}] の形が崩れています")
        matched = SUBMISSION_ID.match(str(item["id"]))
        if matched is None:
            raise ValueError(f"{SUBMISSIONS_PATH}: items[{index}] の id が S-{{連番}} ではありません")
        submissions.append((int(matched.group(1)), item))
    return sorted(submissions, key=lambda entry: entry[0])


def _thread_of(number: int, submission: dict[str, Any]) -> dict[str, Any]:
    """送信 1 件を、その本文を最初の書き込みにしたスレッドの辞書にする。"""
    thread_id = f"TH-{number}"
    taken = submission["taken"]
    thread: dict[str, Any] = {
        "id": thread_id,
        # 取り込み済みの送信はクローズ、取り込んでいないものはオープン
        "status": "closed" if taken is not None else "open",
        "tags": [],
        "summary": None,
    }
    # 向けた項目と箇所は、持つものだけ引き継ぐ
    for key in ("target", "loc"):
        if key in submission:
            thread[key] = submission[key]
    thread["posts"] = [
        {
            "id": f"{thread_id}-1",
            "author": "user",
            "body": submission["body"],
            "created": submission["sent"],
            "read": False,
            "taken": taken,
        }
    ]
    # 取り込み済みの送信は、取り込んだ日時にクローズにしたものとして残す
    thread["events"] = (
        []
        if taken is None
        else [{"kind": "closed", "author": "ai", "reason": None, "created": taken}]
    )
    return thread
