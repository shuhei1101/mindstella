"""記録の取得（GET /api/records）の結合テスト。"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from workspace_fixtures import ADOPTED_OPTIONS, RECORD_DIR, write_yaml

from .fixture_types import CallTool, MakeItem, MakeWorkspace
from .history_helpers import DECISION_ITEM, add_item, commit, read_items, update_item
from .http_helpers import http_request

# 検討事項 D-1 の本文
DECISION_BODY = "## 経緯\n\n種類ごとに分ける案を考えた。\n"


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    serve_preview: Callable[[Path], str],
    valid_settings: dict[str, Any],
) -> None:
    """全ての種類と本文と導いた値を返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", body="D-1.md"),
        make_item("T-1"),
        make_item("R-1"),
        make_item("A-1"),
        make_item("G-1"),
        make_item("N-1"),
        make_item("L-1"),
        bodies={"D-1.md": DECISION_BODY, "A-1.md": "資料の本文\n"},
    )
    url = serve_preview(root)
    # 実行
    result = http_request(url, "/api/records")
    # 検証
    assert result.status == 200
    records = result.json()
    assert records["settings"] == valid_settings
    assert records["decisions"] == [make_item("D-1", body="D-1.md")]
    assert records["tasks"] == [make_item("T-1")]
    assert records["research"] == [make_item("R-1")]
    assert records["docs"] == [make_item("A-1")]
    assert records["terms"] == [make_item("G-1")]
    assert records["notes"] == [make_item("N-1")]
    assert records["logs"] == [make_item("L-1")]
    assert records["bodies"]["D-1.md"] == DECISION_BODY
    next_result = call_tool("next", workspace=str(root))
    assert next_result.data is not None
    assert records["derived"]["next"] == next_result.data["candidates"]
    goal_result = call_tool("goal", workspace=str(root))
    assert goal_result.data is not None
    goal = records["derived"]["goal"]
    assert {key: goal[key] for key in goal_result.data} == goal_result.data
    assert "phase_progress" in goal


def test_normal_when_history(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    serve_preview: Callable[[Path], str],
) -> None:
    """変更履歴とまとまりを、項目に載せたまま返す（正常系）。"""
    # 準備
    root = make_workspace()
    add_item(call_tool, root, "decision", DECISION_ITEM)
    commit(call_tool, root, "足す")
    update_item(call_tool, root, "D-1", {"answer": "種類ごとに分ける"})
    url = serve_preview(root)
    # 実行
    result = http_request(url, "/api/records")
    # 検証
    assert result.status == 200
    records = result.json()
    assert records["decisions"] == read_items(root, "decisions.yaml")
    assert len(records["decisions"][0]["history"]) == 1
    assert [entry["summary"] for entry in records["changes"]["sets"]] == ["足す"]
    assert records["changes"]["sets"][0]["added"] == ["D-1"]
    assert records["changes"]["pending"]["changed"] == ["D-1"]


def test_normal_when_no_goal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    serve_preview: Callable[[Path], str],
    valid_settings: dict[str, Any],
) -> None:
    """ゴールが無いときは has_goal が偽で、phase_progress が全フェーズになる（正常系）。"""
    # 準備
    settings = {
        **{key: value for key, value in valid_settings.items() if key != "goal"},
        "phases": ["目的", "要件"],
    }
    root = make_workspace(
        make_item("D-1", phase="目的", status="決定済み", options=ADOPTED_OPTIONS),
        make_item("D-2", phase="要件", status="未決定"),
        settings=settings,
    )
    url = serve_preview(root)
    # 実行
    result = http_request(url, "/api/records")
    # 検証
    assert result.status == 200
    goal = result.json()["derived"]["goal"]
    assert goal["has_goal"] is False
    assert goal["reached"] is None
    assert goal["phase_progress"] == [
        {"phase": "目的", "settled": 1, "total": 1},
        {"phase": "要件", "settled": 0, "total": 1},
    ]
    goal_result = call_tool("goal", workspace=str(root))
    assert goal_result.data is not None
    assert {key: goal[key] for key in goal_result.data} == goal_result.data


def test_normal_when_rewritten(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    serve_preview: Callable[[Path], str],
) -> None:
    """ツールで書き換えると、次に読んだ記録に書き換えが入っている（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    first = http_request(url, "/api/records").json()
    new_decision = {
        "title": "新しい問い",
        "target": "mindmap",
        "category": "データ構造",
        "phase": "要件",
        "status": "未決定",
        "options": [{"key": "A", "content": "案 A"}],
    }
    # 実行
    added = call_tool("add", workspace=str(root), kind="decision", item=new_decision)
    second = http_request(url, "/api/records").json()
    # 検証
    assert added.is_error is False
    assert [item["id"] for item in second["decisions"]] == ["D-1", "D-2"]
    assert second["built_at"] >= first["built_at"]


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """手で崩した YAML があると、合わない箇所を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", status="完了"))
    url = serve_preview(root)
    # 実行
    result = http_request(url, "/api/records")
    # 検証
    assert result.status == 422
    assert result.headers["content-type"].startswith("application/problem+json")
    detail_lines = result.json()["detail"].splitlines()
    assert any(line.startswith("decisions.yaml: items[0].status:") for line in detail_lines)


def test_normal_when_config_invalid(
    make_workspace: MakeWorkspace,
    serve_preview: Callable[[Path], str],
    valid_settings: dict[str, Any],
) -> None:
    """配信中に config.yaml を崩しても、最後に検査に通った設定で記録を返し、合わない箇所を添える（正常系）。"""
    # 準備
    root = make_workspace(settings={**valid_settings, "display": {"network_look": "starlight"}})
    url = serve_preview(root)
    write_yaml(
        root / RECORD_DIR / "config.yaml",
        {**valid_settings, "display": {"network_look": "rainbow"}},
    )
    before = (root / RECORD_DIR / "config.yaml").read_bytes()
    # 実行
    result = http_request(url, "/api/records")
    # 検証
    assert result.status == 200
    records = result.json()
    assert records["settings"]["display"]["network_look"] == "starlight"
    assert any(
        line.startswith("config.yaml: display.network_look: ")
        for line in records["settings_problem"]
    )
    assert (root / RECORD_DIR / "config.yaml").read_bytes() == before


def test_normal_when_html_body(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
) -> None:
    """HTML の本文は原文を `bodies` に、行の印を足したものを `marked_bodies` に返す（正常系）。"""
    # 準備
    markdown_body = "資料の本文\n"
    html_body = (
        "<!doctype html>\n<style>p { color: red; }</style>\n"
        '<p\n  class="lead">一覧の画面</p>\n'
    )
    root = make_workspace(
        make_item("A-1"),
        make_item("A-2", body="A-2.html"),
        bodies={"A-1.md": markdown_body, "A-2.html": html_body},
    )
    url = serve_preview(root)
    # 実行
    result = http_request(url, "/api/records")
    # 検証
    assert result.status == 200
    records = result.json()
    assert records["bodies"]["A-1.md"] == markdown_body
    assert records["bodies"]["A-2.html"] == html_body
    assert list(records["marked_bodies"]) == ["A-2.html"]
    marked = records["marked_bodies"]["A-2.html"]
    # 複数行にまたがる開きタグの印は、中身が始まる行（開きタグが閉じる行）と、閉じタグが始まる行
    assert '<p data-line="4" data-line-end="4"' in marked
    # `<style>` の中には行の印を足さない
    assert "<style>p { color: red; }</style>" in marked
    # 行の印を取り除くと原文に戻る
    assert re.sub(r' data-line(?:-end)?="\d+"', "", marked) == html_body
