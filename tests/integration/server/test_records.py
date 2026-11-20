"""記録の取得（GET /api/records）の結合テスト。"""

from __future__ import annotations

import re
from collections.abc import Callable
from http import HTTPStatus
from pathlib import Path
from typing import Any

from workspace_fixtures import DEFAULT_TIMESTAMP, RECORD_DIR, write_yaml

from .fixture_types import CallTool, MakeItem, MakeWorkspace, StartMdmarkRefServer
from .history_helpers import DECISION_ITEM, add_item, commit, read_history, read_items, update_item
from .http_helpers import http_request
from .mdmark_ref_helpers import FAKE_HEAD_SHA, fake_github, fake_jsdelivr
from record_write_helpers import write_tool

# 検討事項 D-1 の本文
DECISION_BODY = "## 経緯\n\n種類ごとに分ける案を考えた。\n"


def _stamped(item: dict[str, Any]) -> dict[str, Any]:
    """項目に、history.yaml の行の作成日時・更新日時（make_workspace の既定の日時）を合わせた形を返す。"""
    return {**item, "created": DEFAULT_TIMESTAMP, "updated": DEFAULT_TIMESTAMP}



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
        make_item("D-1", body="../docs/D-1.mark.md"),
        make_item("T-1"),
        make_item("R-1"),
        make_item("A-1"),
        make_item("G-1"),
        make_item("N-1"),
        make_item("L-1"),
        bodies={"D-1.mark.md": DECISION_BODY, "A-1.mark.md": "資料の本文\n"},
    )
    url = serve_preview(root)
    # 実行
    result = http_request(url, "/api/records")
    # 検証
    assert result.status == 200
    records = result.json()
    assert records["settings"] == valid_settings
    assert records["decisions"] == [_stamped(make_item("D-1", body="../docs/D-1.mark.md"))]
    assert records["tasks"] == [_stamped(make_item("T-1"))]
    assert records["research"] == [_stamped(make_item("R-1"))]
    assert records["docs"] == [_stamped(make_item("A-1"))]
    assert records["terms"] == [_stamped(make_item("G-1"))]
    assert records["notes"] == [_stamped(make_item("N-1"))]
    assert records["logs"] == [_stamped(make_item("L-1"))]
    assert records["bodies"]["../docs/D-1.mark.md"] == DECISION_BODY
    # 前提を持たない未決定の D-1 は着手できる。次の候補・ゴール・進捗は返さない
    assert records["derived"] == {"ready": ["D-1"]}


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
    # 項目は history.yaml の行を合わせた形で返る
    rows = read_history(root)
    assert records["decisions"] == [{**item, **rows[item["id"]]} for item in read_items(root, "decisions.yaml")]
    assert len(records["decisions"][0]["history"]) == 1
    assert [entry["summary"] for entry in records["changes"]["sets"]] == ["足す"]
    assert records["changes"]["sets"][0]["added"] == ["D-1"]
    assert records["changes"]["pending"]["changed"] == ["D-1"]


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
        "status": "未決定",
        "options": [{"key": "A", "content": "案 A"}],
    }
    # 実行
    added = write_tool(call_tool, "add", workspace=str(root), kind="decision", item=new_decision)
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
        make_item("A-2", body="../docs/A-2.html"),
        bodies={"A-1.mark.md": markdown_body, "A-2.html": html_body},
    )
    url = serve_preview(root)
    # 実行
    result = http_request(url, "/api/records")
    # 検証
    assert result.status == 200
    records = result.json()
    assert records["bodies"]["../docs/A-1.mark.md"] == markdown_body
    assert records["bodies"]["../docs/A-2.html"] == html_body
    assert list(records["marked_bodies"]) == ["../docs/A-2.html"]
    marked = records["marked_bodies"]["../docs/A-2.html"]
    # 複数行にまたがる開きタグの印は、中身が始まる行（開きタグが閉じる行）と、閉じタグが始まる行
    assert '<p data-line="4" data-line-end="4"' in marked
    # `<style>` の中には行の印を足さない
    assert "<style>p { color: red; }</style>" in marked
    # 行の印を取り除くと原文に戻る
    assert re.sub(r' data-line(?:-end)?="\d+"', "", marked) == html_body


def test_normal_when_mdmark_ref(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    start_mdmark_ref_server: StartMdmarkRefServer,
) -> None:
    """設定が latest のとき、develop の先頭の commit の SHA を mdmark_ref に返す（正常系）。"""
    # 準備
    github = fake_github()
    jsdelivr = fake_jsdelivr()
    github.start()
    jsdelivr.start()
    try:
        server = start_mdmark_ref_server(github.base_url, jsdelivr.base_url)
        settings = {**valid_settings, "mdmark": {"version": "latest"}}
        served = server.call("preview_url", workspace=str(make_workspace(settings=settings)))
        assert served.is_error is False, served.text
        assert served.data is not None
        # 実行
        result = http_request(str(served.data["url"]), "/api/records")
    finally:
        github.stop()
        jsdelivr.stop()
    # 検証
    assert result.status == HTTPStatus.OK
    records = result.json()
    assert records["mdmark_ref"] == FAKE_HEAD_SHA
    assert records["settings"]["mdmark"]["version"] == "latest"
