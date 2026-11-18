"""graph.py（逆向きの参照・影響・決着の判定・着手できる検討事項）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest

import graph
import store
from fixture_types import MakeItem, MakeWorkspace
from workspace_fixtures import ADOPTED_OPTIONS


def test_build_reverse_edges(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """depends_on・parent・for を逆向きにし、related は含めない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("D-2", related=[{"to": "D-1", "type": "depends_on"}]),
        make_item("D-3", related=[{"to": "D-1", "type": "parent"}]),
        make_item("D-4", related=[{"to": "D-1", "type": "see_also"}]),
        make_item("T-1", related=[{"to": "D-1", "type": "for"}]),
    )
    workspace = store.load_workspace(root)
    # 実行
    edges = graph.build_reverse_edges(workspace)
    # 検証
    assert edges["D-1"] == [("D-2", "depends_on"), ("D-3", "parent"), ("T-1", "for")]


def test_trace_impact(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """間接の影響まで、経路つきで近い順に返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("D-2", title="直接の依存", related=[{"to": "D-1", "type": "depends_on"}]),
        make_item("D-3", title="派生", related=[{"to": "D-2", "type": "parent"}]),
        make_item("D-4", related=[{"to": "D-1", "type": "see_also"}]),
        make_item("T-1", title="進めるタスク", related=[{"to": "D-3", "type": "for"}]),
    )
    workspace = store.load_workspace(root)
    # 実行
    affected = graph.trace_impact(workspace, "D-1")
    # 検証
    assert affected == [
        graph.Affected(id="D-2", title="直接の依存", status="未決定", via=[], key="depends_on"),
        graph.Affected(id="D-3", title="派生", status="未決定", via=["D-2"], key="parent"),
        graph.Affected(
            id="T-1",
            title="進めるタスク",
            status="未着手",
            via=["D-2", "D-3"],
            key="for",
        ),
    ]


def test_trace_impact_when_cycle(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """循環があっても同じ項目を 2 度出さず終わる（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", related=[{"to": "D-2", "type": "depends_on"}]),
        make_item("D-2", title="循環の相手", related=[{"to": "D-1", "type": "depends_on"}]),
    )
    workspace = store.load_workspace(root)
    # 実行
    affected = graph.trace_impact(workspace, "D-1")
    # 検証
    assert affected == [
        graph.Affected(id="D-2", title="循環の相手", status="未決定", via=[], key="depends_on"),
    ]


@pytest.mark.parametrize(
    ("kind", "item", "expected"),
    [
        pytest.param("decision", {"status": "決定済み"}, True, id="decision_settled"),
        pytest.param("decision", {"status": "保留"}, False, id="decision_on_hold"),
        pytest.param("task", {"status": "中止"}, True, id="task_cancelled"),
        pytest.param("task", {"status": "進行中"}, False, id="task_in_progress"),
    ],
)
def test_is_settled(kind: str, item: dict[str, Any], expected: bool) -> None:
    """種類ごとの決着を見分ける（正常系）。"""
    # 実行
    settled = graph.is_settled(kind, item)
    # 検証
    assert settled is expected


def test_is_settled_when_missing() -> None:
    """無い項目は未完了として扱う（正常系）。"""
    # 実行
    settled = graph.is_settled("decision", None)
    # 検証
    assert settled is False



def test_list_ready(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """前提が決着した未決定だけを連番の順に返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", status="決定済み", options=ADOPTED_OPTIONS),
        make_item("D-2", related=[{"to": "D-4", "type": "depends_on"}]),
        make_item("D-3", related=[{"to": "D-1", "type": "depends_on"}]),
        make_item("D-4"),
        make_item("D-5", related=[{"to": "D-9", "type": "depends_on"}]),
    )
    workspace = store.load_workspace(root)
    # 実行
    ready = graph.list_ready(workspace)
    # 検証
    assert ready == ["D-3", "D-4"]
