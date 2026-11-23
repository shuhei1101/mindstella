"""NFR-26『記録の更新とスレッドの操作の時間』の非機能要件テスト。"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest
import yaml
from workspace_fixtures import CallTool, MakeItem, MakePost, MakeThread, MakeWorkspace, WriteThreads

# 実例と同じ件数（資料・検討事項・用語・スレッド）
DOC_COUNT = 136
DECISION_COUNT = 392
TERM_COUNT = 162
THREAD_COUNT = 787

# 項目ごとに持たせる変更履歴の回数
HISTORY_DEPTH = 3

# 1 回の操作の上限（秒）
LIMIT_SEC = 1.0

# 変更履歴の日時
HISTORY_AT = "2026-10-01T00:00:00+00:00"

# 測るツールと引数（ID は作ったワークスペースのもの）
OPERATIONS: dict[str, dict[str, Any]] = {
    "adopt": {"id": "D-1", "key": "B"},
    "thread": {"id": "TH-1"},
    "update_thread": {"id": "TH-1", "summary": "D-1 の確認"},
    "set_thread_status": {"id": "TH-1", "status": "closed", "reason": "了解を受けた"},
}

# 測る前に読み込みと検証を済ませる呼び出し（測る呼び出しと別の項目・スレッドに当てる）
WARMUPS: dict[str, dict[str, Any]] = {
    "adopt": {"id": "D-2", "key": "B"},
    "thread": {"id": "TH-2"},
    "update_thread": {"id": "TH-2", "summary": "D-2 の確認"},
    "set_thread_status": {"id": "TH-2", "status": "closed", "reason": "了解を受けた"},
}

# PyYAML が libyaml を持たない環境では、Python の実装で読み書きするため上限を超える
pytestmark = pytest.mark.skipif(not hasattr(yaml, "CSafeLoader"), reason="PyYAML が libyaml を持たない")


def _history() -> list[dict[str, Any]]:
    """変更履歴を HISTORY_DEPTH 回分返す（新しい順）。"""
    return [
        {"seq": seq, "at": HISTORY_AT, "by": "ai", "before": {"title": f"前のタイトル {seq}"}}
        for seq in range(HISTORY_DEPTH, 0, -1)
    ]


def _make_large_workspace(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
) -> Path:
    """実例と同じ件数の項目とスレッドを持ち、項目ごとに変更履歴を持つワークスペースを作る。"""
    options = [{"key": "A", "content": "案 A", "adopted": True}, {"key": "B", "content": "案 B", "adopted": False}]
    items = [
        *(make_item(f"A-{n}", history=_history(), seq=HISTORY_DEPTH) for n in range(1, DOC_COUNT + 1)),
        *(
            make_item(f"D-{n}", status="決定済み", options=options, history=_history(), seq=HISTORY_DEPTH)
            for n in range(1, DECISION_COUNT + 1)
        ),
        *(make_item(f"G-{n}", history=_history(), seq=HISTORY_DEPTH) for n in range(1, TERM_COUNT + 1)),
    ]
    root = make_workspace(*items)
    threads = [
        make_thread(
            f"TH-{n}",
            make_post(f"TH-{n}-1", body="この案でよいか", read=True, taken=HISTORY_AT),
            make_post(f"TH-{n}-2", author="ai", body="案 A で記録しました"),
            target=f"D-{(n - 1) % DECISION_COUNT + 1}",
        )
        for n in range(1, THREAD_COUNT + 1)
    ]
    write_threads(root, *threads)
    return root


@pytest.mark.parametrize("tool", ["adopt", "thread", "update_thread", "set_thread_status"])
def test_record_operation_time(
    tool: str,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    write_threads: WriteThreads,
    call_tool: CallTool,
) -> None:
    """記録が数百件のワークスペースで、1 件の操作を 1 秒以下で終える（正常系）。"""
    # 準備
    root = _make_large_workspace(make_workspace, make_item, make_post, make_thread, write_threads)
    warmup = call_tool(tool, workspace=str(root), **WARMUPS[tool])
    assert warmup.is_error is False, warmup.text
    # 実行
    started = time.perf_counter()
    result = call_tool(tool, workspace=str(root), **OPERATIONS[tool])
    elapsed = time.perf_counter() - started
    # 検証
    assert result.is_error is False, result.text
    assert elapsed <= LIMIT_SEC, f"{tool} が {elapsed:.3f} 秒かかった"
