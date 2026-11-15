"""種類ごとの次の ID を、常駐サーバーのメモリに持つ予約と合わせて振る（ファイルは書かない）。"""

from __future__ import annotations

import threading
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from kinds import KINDS, Kind, kind_of_id


class IdReservations:
    """ワークスペースの絶対パスと種類ごとに、振った最大の連番を 1 つ持つ予約。"""

    def __init__(self) -> None:
        """空の予約と、予約を触る間だけ取る鍵を作る。"""
        # (ワークスペース, 種類) → 振った最大の連番
        self._reserved: dict[tuple[Path, Kind], int] = {}
        self._guard = threading.Lock()

    def reserve(
        self,
        root: Path,
        kind: Kind,
        items: list[dict[str, Any]],
        taken: Iterable[str],
        *,
        count: int = 1,
    ) -> list[str]:
        """その種類の連番の最大（項目・消した ID・予約）+ 1 から `count` 個の ID を振り、予約を進める。"""
        key = (root, kind)
        with self._guard:
            numbers = [
                _number_of(item_id)
                for item_id in (*(item.get("id") for item in items), *taken)
                if isinstance(item_id, str) and kind_of_id(item_id) == kind
            ]
            start = max([*numbers, self._reserved.get(key, 0)]) + 1
            last = start + count - 1
            self._reserved[key] = last
        prefix = KINDS[kind].prefix
        return [f"{prefix}-{number}" for number in range(start, last + 1)]


def _number_of(item_id: str) -> int:
    """`D-12` の形の ID の連番を返す。"""
    return int(item_id.split("-", 1)[1])


# 常駐サーバーのプロセスに 1 つの予約（起動し直すと空になる）
RESERVATIONS = IdReservations()


def reserve_ids(
    root: Path,
    kind: Kind,
    items: list[dict[str, Any]],
    taken: Iterable[str],
    *,
    count: int = 1,
) -> list[str]:
    """プロセスに 1 つの予約から ID を振る。"""
    return RESERVATIONS.reserve(root, kind, items, taken, count=count)
