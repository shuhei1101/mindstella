"""スレッドの結合テストの共通の関数（threads.yaml の読み書き）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from workspace_fixtures import RECORD_DIR


def threads_path(root: Path) -> Path:
    """ワークスペースの threads.yaml のパスを返す。"""
    return root / RECORD_DIR / "threads.yaml"


def read_threads(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの threads.yaml のスレッドの並びを読む。"""
    return yaml.safe_load(threads_path(root).read_text(encoding="utf-8"))["items"]


def find_thread(root: Path, thread_id: str) -> dict[str, Any]:
    """ワークスペースの threads.yaml から、ID のスレッドを返す。"""
    return next(thread for thread in read_threads(root) if thread["id"] == thread_id)


def drop_thread_key(root: Path, key: str) -> None:
    """threads.yaml の 1 件目のスレッドからキーを消して、スキーマに合わない形にする。"""
    data = yaml.safe_load(threads_path(root).read_text(encoding="utf-8"))
    del data["items"][0][key]
    threads_path(root).write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def drop_post_key(root: Path, key: str) -> None:
    """threads.yaml の 1 件目のスレッドの 1 件目の書き込みからキーを消して、スキーマに合わない形にする。"""
    data = yaml.safe_load(threads_path(root).read_text(encoding="utf-8"))
    del data["items"][0]["posts"][0][key]
    threads_path(root).write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
