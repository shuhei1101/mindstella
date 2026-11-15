"""単体テストが共有する、AI の書き換えを記録へ書く補助（消した `update` のツールと同じ書き込み）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import commands
import history
import store


def ai_update(
    root: Path, item_id: str, values: dict[str, Any], *, now: Any = store.now_utc
) -> None:
    """1 項目のキーを置き換え、変更履歴と通し番号をつけて記録へ書く（編集した人は ai）。"""
    workspace = store.load_workspace(root)
    staged = commands.Staged(
        workspace=workspace,
        items=workspace.items,
        touched=frozenset(),
        bodies={},
        history=history.load_item_history(root),
        changes=history.load_changes(root),
    )
    updated, _ = commands.stage_update(staged, item_id, values, now)
    store.save_batch(
        workspace,
        store.BatchChange(
            items={kind: updated.items[kind] for kind in updated.touched},
            bodies=list(updated.bodies.values()),
            history=updated.history,
            changes=dict(updated.changes),
            removed_bodies=list(updated.removed_bodies),
        ),
    )
