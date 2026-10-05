"""screens/overview.ts（概要）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, MakeData, MakeItem

# 表示する種類の全て
ALL_KINDS = ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]

# 検討事項・タスク・資料を除いた、表示する種類
KINDS_WITHOUT_DECISIONS_TASKS_DOCS = ["research", "terms", "notes", "logs"]

# 納品物 6 件（5 件を超えると、納品物の資料へ移る「すべて表示」を出す）
DELIVERABLES = [{"title": f"納品物{number}"} for number in range(1, 7)]


@pytest.mark.parametrize(
    ("visible_kinds", "expects_links"),
    [
        pytest.param(ALL_KINDS, True, id="all_kinds"),
        pytest.param(KINDS_WITHOUT_DECISIONS_TASKS_DOCS, False, id="kinds_hidden"),
    ],
)
def test_overview_screen_when_kinds_hidden(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    visible_kinds: list[str],
    expects_links: bool,
) -> None:
    """表示しない種類へのリンクだけを外し、タイルは残す（正常系）。"""
    # 準備
    settings = {
        **valid_settings,
        "goal": {"phase": "構成", "summary": "作り始められる", "deliverables": DELIVERABLES},
    }
    data = make_data(
        settings=settings,
        decisions=[
            make_item(
                "D-1", target="mindmap", category="データ構造", phase="要件", status="要見直し"
            )
        ],
        tasks=[make_item("T-1", status="進行中")],
    )
    # 納品物のチェックリストと、カテゴリー別の進捗の表に出す値
    data["derived"]["goal"].update(
        {
            "has_goal": True,
            "reached": False,
            "remaining_deliverables": [
                {"title": entry["title"], "doc": None} for entry in DELIVERABLES
            ],
            "phase_progress": [{"phase": "要件", "settled": 1, "total": 2}],
        }
    )
    data["derived"]["progress"] = [
        {
            "category": "データ構造",
            "cells": [
                {"phase": "目的", "settled": 0, "total": 0},
                {"phase": "要件", "settled": 1, "total": 2},
                {"phase": "構成", "settled": 0, "total": 0},
            ],
            "settled": 1,
            "total": 2,
        }
    ]
    load_preview_scripts()
    # 実行
    observed = preview_page.evaluate(
        """({data, kinds}) => {
            const index = MindmapPreview.buildIndex(data);
            const screen = MindmapPreview.overviewScreen({
                index,
                visibleKinds: new Set(kinds),
                on: {open: () => {}, navigate: () => {}},
            });
            document.body.append(screen);
            const tile = (id) => screen.querySelector(`#${id}`);
            const progress = tile("tile-progress");
            return {
                reviewRow: tile("tile-review")?.querySelector('button[data-id="D-1"]') != null,
                runningRow: tile("tile-running")?.querySelector('button[data-id="T-1"]') != null,
                goalTile: tile("tile-goal")?.textContent.includes("納品物") ?? false,
                showAllCount: [...screen.querySelectorAll("button")].filter((button) =>
                    button.textContent.trim().startsWith("すべて表示")
                ).length,
                progressButtons: progress.querySelectorAll("button").length,
                progressText: progress.textContent,
                progressHasBar: progress.querySelector("i b") !== null,
            };
        }""",
        {"data": data, "kinds": visible_kinds},
    )
    # 検証
    assert observed["reviewRow"] is True
    assert observed["runningRow"] is True
    assert observed["goalTile"] is True
    assert observed["progressText"].count("1/2") >= 1
    assert observed["progressHasBar"] is True
    assert (observed["showAllCount"] > 0) is expects_links
    assert (observed["progressButtons"] > 0) is expects_links
