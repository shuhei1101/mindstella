"""ids.py（ワークスペースごと・種類ごとの ID の予約）の単体テスト。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ids import IdReservations

# 同時に振るスレッドの数
THREAD_COUNT = 8

# 予約を分ける 2 つのワークスペースの絶対パス（ファイルは読まない）
WORKSPACE_A = Path("/workspaces/a")
WORKSPACE_B = Path("/workspaces/b")


def test_reserve() -> None:
    """項目と消した ID の最大の次から振る（正常系）。"""
    # 準備
    reservations = IdReservations()
    items = [{"id": "D-1"}, {"id": "D-2"}]
    # 実行
    ids = reservations.reserve(WORKSPACE_A, "decision", items, ["D-3"], count=2)
    # 検証
    assert ids == ["D-4", "D-5"]


def test_reserve_when_reserved() -> None:
    """書き込まれていない予約の次から振る（正常系）。"""
    # 準備
    reservations = IdReservations()
    items = [{"id": "D-1"}]
    # 実行
    first = reservations.reserve(WORKSPACE_A, "decision", items, [])
    second = reservations.reserve(WORKSPACE_A, "decision", items, [])
    # 検証
    assert first == ["D-2"]
    assert second == ["D-3"]


def test_reserve_when_concurrent() -> None:
    """並行して振っても重ならない（正常系）。"""
    # 準備
    reservations = IdReservations()
    items = [{"id": "D-1"}]
    # 実行
    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as pool:
        results = list(
            pool.map(
                lambda _: reservations.reserve(WORKSPACE_A, "decision", items, [])[0],
                range(THREAD_COUNT),
            )
        )
    # 検証
    assert sorted(results) == ["D-2", "D-3", "D-4", "D-5", "D-6", "D-7", "D-8", "D-9"]


def test_reserve_when_other_workspace() -> None:
    """ワークスペースと種類ごとに予約を分ける（正常系）。"""
    # 準備
    reservations = IdReservations()
    reservations.reserve(WORKSPACE_A, "decision", [], [])
    # 実行
    other_workspace = reservations.reserve(WORKSPACE_B, "decision", [], [])
    other_kind = reservations.reserve(WORKSPACE_A, "task", [], [])
    # 検証
    assert other_workspace == ["D-1"]
    assert other_kind == ["T-1"]
