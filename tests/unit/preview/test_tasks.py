"""screens/tasks.ts（タスクの画面とボードの列）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, MakeItem

# タスクの状態の並び（スキーマの列挙の順）
TASK_STATUSES = ["未着手", "進行中", "保留", "完了", "中止"]


def test_board_columns(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, make_item: MakeItem
) -> None:
    """状態の並びの順に分ける（正常系）。"""
    # 準備
    items = [
        make_item("T-2", status="未着手"),
        make_item("T-1", status="未着手"),
        make_item("T-3", status="完了"),
    ]
    load_preview_scripts()
    # 実行
    columns = preview_page.evaluate(
        """({items, statuses}) => MindmapPreview.boardColumns({items, statuses}).map(
            (column) => [column.status, column.items.map((item) => item.id)]
        )""",
        {"items": items, "statuses": TASK_STATUSES},
    )
    # 検証
    assert columns == [
        ["未着手", ["T-1", "T-2"]],
        ["進行中", []],
        ["保留", []],
        ["完了", ["T-3"]],
        ["中止", []],
    ]


@pytest.mark.parametrize(
    ("status_filter", "expected"),
    [
        pytest.param(
            ["未着手", "進行中"],
            [
                ["未着手", False],
                ["進行中", False],
                ["保留", True],
                ["完了", True],
                ["中止", True],
            ],
            id="status_condition",
        ),
        pytest.param(
            [],
            [
                ["未着手", False],
                ["進行中", False],
                ["保留", False],
                ["完了", False],
                ["中止", False],
            ],
            id="no_status_condition",
        ),
    ],
)
def test_board_columns_when_status_filter(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_item: MakeItem,
    status_filter: list[str],
    expected: list[list[Any]],
) -> None:
    """状態の条件から外した列を示す（正常系）。"""
    # 準備
    items = [make_item("T-1", status="未着手")]
    load_preview_scripts()
    # 実行
    columns = preview_page.evaluate(
        """({items, statuses, statusFilter}) => MindmapPreview.boardColumns(
            {items, statuses, statusFilter}
        ).map((column) => [column.status, column.excluded])""",
        {"items": items, "statuses": TASK_STATUSES, "statusFilter": status_filter},
    )
    # 検証
    assert columns == expected
