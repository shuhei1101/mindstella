"""記録の取得（GET /api/records）の結合テスト。"""

from __future__ import annotations

import gzip
import http.client
import json
import re
from collections.abc import Callable
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from workspace_fixtures import DEFAULT_TIMESTAMP, RECORD_DIR, STATE_SESSION_PATH, McpServer, workspace_id_of, write_yaml

from .fixture_types import CallTool, MakeItem, MakeWorkspace, StartMdmarkRefServer
from .history_helpers import DECISION_ITEM, add_item, commit, read_history, read_items, update_item
from .http_helpers import HTTP_TIMEOUT_SEC, EventStream, http_request, workspace_path
from .preset_helpers import eq, ne, tags, with_presets
from .mdmark_ref_helpers import FAKE_HEAD_SHA, fake_github, fake_jsdelivr
from .transcriber_helpers import bind_closed_port
from record_write_helpers import write_tool

# 書き換えの知らせを待つ上限秒数
CHANGED_WITHIN_SEC = 10

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
    root = make_workspace(settings={**valid_settings, "display": {"visible_kinds": ["decisions"]}})
    url = serve_preview(root)
    write_yaml(
        root / RECORD_DIR / "config.yaml",
        {**valid_settings, "display": {"visible_kinds": ["rainbow"]}},
    )
    before = (root / RECORD_DIR / "config.yaml").read_bytes()
    # 実行
    result = http_request(url, "/api/records")
    # 検証
    assert result.status == 200
    records = result.json()
    assert records["settings"]["display"]["visible_kinds"] == ["decisions"]
    assert any(
        line.startswith("config.yaml: display.visible_kinds")
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


# 設定の mdmark のバージョンに指すタグ
MDMARK_TAG = "v0.13.0"


def _records(server: Any, root: Path) -> Any:
    """ワークスペースを配って `/api/records` を GET した結果を返す。"""
    served = server.call("preview_url", workspace=str(root))
    assert served.is_error is False, served.text
    assert served.data is not None
    return http_request(str(served.data["url"]), "/api/records")


def test_normal_when_github_unreachable(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    start_mdmark_ref_server: StartMdmarkRefServer,
) -> None:
    """develop の先頭の commit を問い合わせられないときは、`develop` を mdmark_ref に返す（正常系）。"""
    # 準備
    held = bind_closed_port()
    jsdelivr = fake_jsdelivr()
    jsdelivr.start()
    try:
        server = start_mdmark_ref_server(f"http://127.0.0.1:{held.getsockname()[1]}", jsdelivr.base_url)
        root = make_workspace(settings={**valid_settings, "mdmark": {"version": "latest"}})
        # 実行
        result = _records(server, root)
    finally:
        held.close()
        jsdelivr.stop()
    # 検証
    assert result.status == HTTPStatus.OK
    assert result.json()["mdmark_ref"] == "develop"
    warnings = [line for line in server.stderr_text().splitlines() if "mdmark の ref を問い合わせられない" in line]
    assert len(warnings) == 1, server.stderr_text()


def test_normal_when_mdmark_version_tag(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    start_mdmark_ref_server: StartMdmarkRefServer,
) -> None:
    """設定の mdmark のバージョンがタグのときは、GitHub に問い合わせずにタグを mdmark_ref に返す（正常系）。"""
    # 準備
    github = fake_github()
    jsdelivr = fake_jsdelivr()
    github.start()
    jsdelivr.start()
    try:
        server = start_mdmark_ref_server(github.base_url, jsdelivr.base_url)
        root = make_workspace(settings={**valid_settings, "mdmark": {"version": MDMARK_TAG}})
        # 実行
        result = _records(server, root)
    finally:
        github.stop()
        jsdelivr.stop()
    # 検証
    assert result.status == HTTPStatus.OK
    assert result.json()["mdmark_ref"] == MDMARK_TAG
    assert github.paths == []


def test_normal_when_dist_not_served(
    make_workspace: MakeWorkspace,
    start_mdmark_ref_server: StartMdmarkRefServer,
) -> None:
    """問い合わせた commit を jsDelivr が配らないときは、`develop` を mdmark_ref に返す（正常系）。"""
    # 準備
    github = fake_github()
    jsdelivr = fake_jsdelivr(HTTPStatus.FORBIDDEN)
    github.start()
    jsdelivr.start()
    try:
        server = start_mdmark_ref_server(github.base_url, jsdelivr.base_url)
        root = make_workspace()
        # 実行
        result = _records(server, root)
    finally:
        github.stop()
        jsdelivr.stop()
    # 検証
    assert result.status == HTTPStatus.OK
    assert result.json()["mdmark_ref"] == "develop"
    warnings = [line for line in server.stderr_text().splitlines() if "jsDelivr が配らない" in line]
    assert len(warnings) == 1, server.stderr_text()


def _raw_get(url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
    """記録の取得を圧縮したまま 1 回読み、ステータス・ヘッダー（小文字）・本文の bytes を返す。"""
    parts = urlsplit(url)
    connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=HTTP_TIMEOUT_SEC)
    try:
        connection.request("GET", workspace_path(url, "/api/records"), headers=headers)
        response = connection.getresponse()
        body = response.read()
        return response.status, {name.lower(): value for name, value in response.getheaders()}, body
    finally:
        connection.close()


def test_normal_when_revalidated(
    make_workspace: MakeWorkspace, make_item: MakeItem, serve_preview: Callable[[Path], str]
) -> None:
    """圧縮して返し、同じ ETag の再検証には 304 を返し、保持した応答を使う（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", body="../docs/D-1.mark.md"), bodies={"D-1.mark.md": DECISION_BODY})
    url = serve_preview(root)
    # 実行
    first_status, first_headers, first_body = _raw_get(url, {"Accept-Encoding": "gzip"})
    second_status, second_headers, second_body = _raw_get(
        url, {"Accept-Encoding": "gzip", "If-None-Match": first_headers["etag"]}
    )
    body_path = root / "docs" / "D-1.mark.md"
    body_path.chmod(0)
    try:
        third_status, _, third_body = _raw_get(url, {})
    finally:
        body_path.chmod(0o644)
    # 検証
    assert first_status == HTTPStatus.OK
    assert first_headers["content-encoding"] == "gzip"
    assert first_headers["vary"] == "Accept-Encoding"
    assert first_headers["cache-control"] == "no-cache"
    first = json.loads(gzip.decompress(first_body))
    assert first["bodies"]["../docs/D-1.mark.md"] == DECISION_BODY
    assert second_status == HTTPStatus.NOT_MODIFIED
    assert second_body == b""
    assert second_headers["etag"] == first_headers["etag"]
    assert third_status == HTTPStatus.OK
    third = json.loads(third_body)
    assert third["bodies"] == first["bodies"]
    assert third["built_at"] == first["built_at"]


def test_normal_when_cache_invalidated(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    serve_preview: Callable[[Path], str],
    open_events: Callable[[str], EventStream],
) -> None:
    """ワークスペースを書き換えると保持した応答を捨て、次の要求で ETag の違う応答を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    url = serve_preview(root)
    _, first_headers, _ = _raw_get(url, {})
    stream = open_events(url)
    decisions = yaml.safe_load((root / RECORD_DIR / "decisions.yaml").read_text(encoding="utf-8"))
    decisions["items"].append(make_item("D-2"))
    write_yaml(root / RECORD_DIR / "decisions.yaml", decisions)
    assert stream.wait_for_changed(CHANGED_WITHIN_SEC) is True
    # 実行
    status, headers, body = _raw_get(url, {"If-None-Match": first_headers["etag"]})
    # 検証
    assert status == HTTPStatus.OK
    assert [item["id"] for item in json.loads(body)["decisions"]] == ["D-1", "D-2"]
    assert headers["etag"] != first_headers["etag"]


def test_normal_when_presets(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    serve_preview: Callable[[Path], str],
) -> None:
    """設定のプリセットと、種類をまたいだプリセットごとの件数を返す（正常系）。"""
    # 準備
    presets = [
        {"name": "画面の設計", "filter": {"and": [eq("画面"), ne("廃止")]}},
        {"name": "古い分類", "filter": eq("廃止したタグ")},
    ]
    root = make_workspace(
        make_item("A-1", tags=tags("画面")),
        make_item("A-2", tags=tags("画面", "廃止")),
        make_item("D-1", tags=tags("画面")),
        settings=with_presets(valid_settings, *presets),
    )
    url = serve_preview(root)
    # 実行
    records = http_request(url, "/api/records").json()
    # 検証
    assert records["settings"]["presets"] == presets
    assert records["preset_counts"] == {"画面の設計": 2, "古い分類": 0}


# 今回の差分の始まりとして書いておく連番と日時
TURN_SEQ = 3
TURN_AT = "2026-11-28T05:50:00+00:00"


def _workspace_with_two_sets(make_workspace: MakeWorkspace, call_tool: CallTool, name: str) -> Path:
    """まとまり V-1・V-2 を持つワークスペースを作る。"""
    root = make_workspace(name=name)
    add_item(call_tool, root, "decision", DECISION_ITEM)
    commit(call_tool, root, "1 回目")
    update_item(call_tool, root, "D-1", {"title": "書き換えた問い"})
    commit(call_tool, root, "2 回目")
    return root


def test_normal_when_turn_point(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    mcp_server: McpServer,
    serve_preview: Callable[[Path], str],
) -> None:
    """turn_point.json の連番と日時を changes に入れ、無ければ 0 と null を返す（正常系）。"""
    # 準備（1 つ目は turn_point.json が無く、2 つ目は配信の前に書いておく）
    without_point = _workspace_with_two_sets(make_workspace, call_tool, "始まりなし")
    with_point = _workspace_with_two_sets(make_workspace, call_tool, "始まりあり")
    assert mcp_server.state_home is not None
    state_dir = mcp_server.state_home.joinpath(*STATE_SESSION_PATH, workspace_id_of(with_point))
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "turn_point.json").write_text(
        json.dumps({"turn_seq": TURN_SEQ, "at": TURN_AT}), encoding="utf-8"
    )
    # 実行
    first = http_request(serve_preview(without_point), "/api/records").json()["changes"]
    second = http_request(serve_preview(with_point), "/api/records").json()["changes"]
    # 検証
    assert (first["turn_seq"], first["turn_at"]) == (0, None)
    assert (second["turn_seq"], second["turn_at"]) == (TURN_SEQ, TURN_AT)
