"""builder.py（プレビューのデータの収集・埋め込み・書き出し）の単体テスト。"""

from __future__ import annotations

import http.server
import json
import re
import socket
import threading
from collections import Counter
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, ClassVar

import pytest
import yaml

import builder
import errors
import read_point
import store
from errors import SchemaMismatchError, WriteFailedError
from export_helpers import (
    Mdmark,
    Script,
    dist_url,
    export_html,
    integrity_of,
    make_fetch,
    make_library,
    make_responses,
    mdmark_url,
    write_export_preview_dir,
)
from fixture_types import MakeItem, MakeWorkspace, SnapshotTree
from workspace_fixtures import ADOPTED_OPTIONS, DEFAULT_TIMESTAMP, RECORD_DIR

# 書き出した日時
BUILT_AT = "2026-10-02T08:00:00+00:00"


def _read_embedded(html: str) -> dict[str, Any]:
    """HTML の mindmap-data の要素の中身を JSON として読む。"""
    inner = html.split(builder.DATA_OPEN, 1)[1].split("</script>", 1)[0]
    return json.loads(inner)


def test_read_records(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """その場で読んだ記録を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    first = builder.read_records(root, now=lambda: BUILT_AT)
    (root / RECORD_DIR / "decisions.yaml").write_text(
        yaml.safe_dump(
            {"items": [make_item("D-1"), make_item("D-2")]}, allow_unicode=True, sort_keys=False
        ),
        encoding="utf-8",
    )
    second = builder.read_records(root, now=lambda: BUILT_AT)
    # 検証
    assert [item["id"] for item in first["decisions"]] == ["D-1"]
    assert [item["id"] for item in second["decisions"]] == ["D-1", "D-2"]
    assert second["built_at"] == BUILT_AT


def test_read_records_when_schema_mismatch(
    make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """スキーマに合わなければ返さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", status="完了"))
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        builder.read_records(root, now=lambda: BUILT_AT)
    assert exc_info.value.lines[0].startswith("decisions.yaml: items[0].status:")


def _settings_with_kinds(base: dict[str, Any], kinds: list[str] | None) -> dict[str, Any] | None:
    """表示する種類の既定を kinds にした設定を返す。kinds が None なら None を返す。"""
    if kinds is None:
        return None
    return {**base, "display": {"visible_kinds": kinds}}


def _read_records_or_lines(root: Path, last_settings: dict[str, Any] | None) -> dict[str, Any]:
    """記録を読んで返す。SchemaMismatchError のときは lines だけを持つ辞書で返す。"""
    try:
        return builder.read_records(root, last_settings=last_settings, now=lambda: BUILT_AT)
    except SchemaMismatchError as error:
        return {"error_lines": error.lines}


@pytest.mark.parametrize(
    ("last_kinds", "expected_kinds", "problem_key"),
    [
        pytest.param(["decisions"], ["decisions"], "settings_problem", id="with_last_settings"),
        pytest.param(None, None, "error_lines", id="without_last_settings"),
    ],
)
def test_read_records_when_settings_invalid(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    last_kinds: list[str] | None,
    expected_kinds: list[str] | None,
    problem_key: str,
) -> None:
    """config.yaml だけが合わなければ最後に通った設定で返す（正常系）。"""
    # 準備
    root = make_workspace(settings=_settings_with_kinds(valid_settings, ["rainbow"]))
    last_settings = _settings_with_kinds(valid_settings, last_kinds)
    # 実行
    outcome = _read_records_or_lines(root, last_settings)
    # 検証
    assert outcome.get("settings", {}).get("display", {}).get("visible_kinds") == expected_kinds
    assert outcome[problem_key][0].startswith("config.yaml: display.visible_kinds")


def test_collect_preview_data(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """種類ごとのキーと、指された本文だけを集める（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1", body="../docs/A-1.mark.md"),
        make_item("R-1", body="../docs/R-1.mark.md"),
        bodies={"A-1.mark.md": "資料の本文\n", "X-1.mark.md": "どこからも指されない本文\n"},
    )
    workspace = store.load_workspace(root)
    # 実行
    data = builder.collect_preview_data(workspace, built_at=BUILT_AT, mdmark_ref="develop")
    # 検証
    assert set(data) == {
        "settings",
        "decisions",
        "tasks",
        "research",
        "docs",
        "terms",
        "notes",
        "logs",
        "bodies",
        "marked_bodies",
        "changes",
        "derived",
        "preset_counts",
        "built_at",
        "settings_problem",
        "mdmark_ref",
    }
    assert data["mdmark_ref"] == "develop"
    assert data["bodies"] == {"../docs/A-1.mark.md": "資料の本文\n"}
    assert data["marked_bodies"] == {}
    assert data["settings_problem"] is None


def test_collect_preview_data_with_html_body(
    make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """HTML の本文は原文を bodies に、行の印つきを marked_bodies に入れる（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1", body="../docs/A-1.mark.md"),
        make_item("A-2", body="../docs/A-2.html"),
        bodies={"A-1.mark.md": "資料の本文\n", "A-2.html": "<p>a</p>"},
    )
    workspace = store.load_workspace(root)
    # 実行
    data = builder.collect_preview_data(workspace, built_at=BUILT_AT, mdmark_ref="develop")
    # 検証
    assert data["bodies"] == {"../docs/A-1.mark.md": "資料の本文\n", "../docs/A-2.html": "<p>a</p>"}
    assert data["marked_bodies"] == {"../docs/A-2.html": '<p data-line="1" data-line-end="1">a</p>'}


def test_collect_preview_data_with_changes(
    make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """まとまりと変更履歴を含める（正常系）。"""
    # 準備
    entry = {"seq": 1, "at": BUILT_AT, "before": {"status": "未決定"}}
    changes = {
        "last_seq": 1,
        "sets": [
            {
                "id": "V-1",
                "at": BUILT_AT,
                "summary": "決める",
                "until_seq": 1,
                "added": [],
                "changed": ["D-1"],
            }
        ],
        "pending": {"added": [], "changed": []},
    }
    root = make_workspace(
        make_item("D-1", status="決定済み", history=[entry]),
        raw_files={"changes.yaml": yaml.safe_dump(changes, allow_unicode=True, sort_keys=False)},
    )
    workspace = store.load_workspace(root)
    # 実行
    data = builder.collect_preview_data(workspace, built_at=BUILT_AT, mdmark_ref="develop")
    # 検証
    assert data["changes"] == {**changes, "turn_seq": 0, "turn_at": None}
    assert data["decisions"][0]["history"] == [entry]



@pytest.mark.parametrize(
    ("record", "expected"),
    [
        pytest.param(lambda root: None, (0, None), id="missing"),
        pytest.param(
            lambda root: read_point.save_turn_point(root, 3, "2026-11-28T05:50:00+00:00"),
            (3, "2026-11-28T05:50:00+00:00"),
            id="recorded",
        ),
    ],
)
def test_collect_preview_data_turn_point(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    record: Callable[[Path], None],
    expected: tuple[int, str | None],
) -> None:
    """今回の差分の始まりを changes に入れる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    record(root)
    workspace = store.load_workspace(root)
    # 実行
    data = builder.collect_preview_data(workspace, built_at=BUILT_AT, mdmark_ref="develop")
    # 検証
    assert (data["changes"]["turn_seq"], data["changes"]["turn_at"]) == expected

def test_escape_for_script() -> None:
    """置き換えた文字列は </script> を含まず、JSON として読むと元に戻る（正常系）。"""
    # 準備
    original = {"a": "</script>&<b>"}
    json_text = json.dumps(original, ensure_ascii=False)
    # 実行
    escaped = builder.escape_for_script(json_text)
    # 検証
    assert "<" not in escaped
    assert ">" not in escaped
    assert "&" not in escaped
    assert json.loads(escaped) == original


def test_derive_preview_values(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """着手できる検討事項だけを返し、削除した値を持たない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", status="決定済み", options=ADOPTED_OPTIONS),
        make_item("D-2", related=[{"to": "D-1", "type": "depends_on"}]),
        make_item("D-3", related=[{"to": "D-4", "type": "depends_on"}]),
        make_item("D-4"),
    )
    workspace = store.load_workspace(root)
    # 実行
    derived = builder.derive_preview_values(workspace)
    # 検証
    assert derived == {"ready": ["D-2", "D-4"]}


# 配る書き出しのテストが libraries.json に置く描画のライブラリ（実物の VENDOR_LIBRARIES にあるパッケージ）
MARKED_SCRIPTS: list[Script] = [("marked", b"/* marked */")]

# 配る書き出しのテストが取る mdmark の中身（JavaScript・CSS）
MDMARK: Mdmark = (b"/* mdmark */", b".mdmark{}")

# 組み立てのテストの mdmark の ref と中身（ライセンスはプレビューのフォルダのファイルから読み、束ねた依存は取る）
MDMARK_VERSION = "v0.13.0"
MODULE: Mdmark = (b"/* m */", b".m{}")

# 手元の HTTP サーバーが 200 で返す本文
SERVED_BODY = b"abc"


class _Handler(http.server.BaseHTTPRequestHandler):
    """/a.js は 200 で本文を、/no-content は 204 を返し、それ以外は 404 を返す手元の HTTP サーバーの処理。

    /flaky-{状態コード} は 1 回目だけその状態コード（429 は `Retry-After: 1` を付ける）で、2 回目から 200 で本文を返す。
    /always-403 は何回でも 403 を返す。パスごとの要求の回数を `requests` に数える。
    """

    requests: ClassVar[Counter[str]] = Counter()

    def do_GET(self) -> None:
        """GET を受けて、パスで 200 か 404 かを決める。"""
        self.requests[self.path] += 1
        if self.path.startswith("/flaky-") and self.requests[self.path] == 1:
            # 1 回目だけ一時的な失敗を返す
            status = int(self.path.removeprefix("/flaky-"))
            self.send_response(status)
            if status == 429:
                self.send_header("Retry-After", "1")
            self.end_headers()
            return
        if self.path.startswith("/flaky-"):
            # 2 回目からは取れる
            self.send_response(200)
            self.end_headers()
            self.wfile.write(SERVED_BODY)
            return
        if self.path == "/always-403":
            # 何回でも 403
            self.send_error(403)
            return
        # /a.js だけが取れる
        if self.path == "/a.js":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(SERVED_BODY)
        elif self.path == "/no-content":
            # 200 以外の成功（本文が無い）
            self.send_response(204)
            self.end_headers()
        else:
            # それ以外は 404
            self.send_error(404)

    def log_message(self, format: str, *args: Any) -> None:
        """標準エラーへのアクセスログを出さない。"""


def _failing_fetch(url: str) -> bytes:
    """どの URL も取れない fetch の代わり。"""
    raise errors.DownloadFailedError(f"取れませんでした: {url}")


def _assert_in_order(text: str, parts: list[str]) -> None:
    """parts の各文字列が、text の中にこの順で現れることを確かめる。"""
    positions = [text.index(part) for part in parts]
    assert positions == sorted(positions)


def _export_responses() -> dict[str, bytes]:
    """配る書き出しで取る URL → 中身（marked・mdmark の配布ファイルとライセンスの本文）を返す。"""
    responses = make_responses(MARKED_SCRIPTS, mdmark=MDMARK)
    responses[mdmark_url("THIRD_PARTY_LICENSES.txt")] = "束ねた本文".encode()
    return responses


@pytest.fixture
def export_preview_dir(tmp_path: Path) -> Path:
    """書き出し用のビルド・marked の 1 行の libraries.json・React の画面のライセンスを置いたプレビューのフォルダを返す。"""
    folder = tmp_path / "preview"
    write_export_preview_dir(folder, MARKED_SCRIPTS)
    return folder


@pytest.fixture
def local_server(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """127.0.0.1 の空きポートで HTTP サーバーを立て、`http://127.0.0.1:{ポート}` を返す。"""
    # 環境のプロキシを通さずに、手元のサーバーへ届かせる
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    _Handler.requests.clear()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.fixture
def closed_url(monkeypatch: pytest.MonkeyPatch) -> str:
    """誰も待ち受けていないポートの URL を返す。"""
    # 環境のプロキシを通さずに、手元のポートへ届かせる
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"http://127.0.0.1:{port}/a.js"


@pytest.fixture
def waits(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """取り直しの `time.sleep` を待たずに秒数を記録する差し替えにし、`random.uniform` を上限を返す差し替えにして、記録を返す。"""
    recorded: list[float] = []
    monkeypatch.setattr(builder.time, "sleep", recorded.append)
    monkeypatch.setattr(builder.random, "uniform", lambda low, high: high)
    return recorded


def test_replace_file(tmp_path: Path) -> None:
    """中身を書いて置き換える（正常系）。"""
    # 準備
    path = tmp_path / "a.html"
    path.write_text("古い", encoding="utf-8")
    # 実行
    builder.replace_file(path, "新しい")
    # 検証
    assert path.read_text(encoding="utf-8") == "新しい"
    assert list(tmp_path.glob("*.tmp")) == []


def test_replace_file_when_parent_missing(tmp_path: Path) -> None:
    """親のフォルダが無ければフォルダを作らずに失敗する（異常系）。"""
    # 準備
    path = tmp_path / "無い" / "a.html"
    # 実行・検証
    with pytest.raises(WriteFailedError, match=r"a\.html"):
        builder.replace_file(path, "新しい")
    assert not (tmp_path / "無い").exists()


def test_export_preview(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    export_preview_dir: Path,
    tmp_path: Path,
) -> None:
    """記録と取ったライブラリとライセンスの表示を持つ HTML を out に書き、ワークスペースは触らない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("A-1", body="../docs/A-1.mark.md"),
        bodies={"A-1.mark.md": "本文 </script>\n"},
    )
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    out = tmp_path / "配る.html"
    fetch, _calls = make_fetch(_export_responses())
    # 実行
    path = builder.export_preview(
        workspace, out=out, built_at=BUILT_AT, preview_dir=export_preview_dir, fetch=fetch
    )
    # 検証
    assert path == out
    html = out.read_text(encoding="utf-8")
    data = _read_embedded(html)
    assert data["decisions"] == [
        {**make_item("D-1"), "created": DEFAULT_TIMESTAMP, "updated": DEFAULT_TIMESTAMP}
    ]
    assert data["bodies"] == {"../docs/A-1.mark.md": "本文 </script>\n"}
    assert "src=" not in html
    assert "href=" not in html
    assert builder.LICENSES_OPEN in html
    assert snapshot_tree(root) == before


def test_export_preview_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    export_preview_dir: Path,
    tmp_path: Path,
) -> None:
    """問題があれば取らずに前の out を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", status="完了"))
    workspace = store.load_workspace(root)
    out = tmp_path / "配る.html"
    out.write_text("前の配る\n", encoding="utf-8")
    fetch, calls = make_fetch(make_responses(MARKED_SCRIPTS))
    # 実行・検証
    with pytest.raises(SchemaMismatchError):
        builder.export_preview(
            workspace, out=out, built_at=BUILT_AT, preview_dir=export_preview_dir, fetch=fetch
        )
    assert out.read_text(encoding="utf-8") == "前の配る\n"
    assert calls == []


def test_export_preview_when_download_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    export_preview_dir: Path,
    tmp_path: Path,
) -> None:
    """取れなければ前の out を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    workspace = store.load_workspace(root)
    out = tmp_path / "配る.html"
    out.write_text("前の配る\n", encoding="utf-8")
    # 実行・検証
    with pytest.raises(errors.DownloadFailedError):
        builder.export_preview(
            workspace,
            out=out,
            built_at=BUILT_AT,
            preview_dir=export_preview_dir,
            fetch=_failing_fetch,
        )
    assert out.read_text(encoding="utf-8") == "前の配る\n"


def test_export_preview_when_out_dir_missing(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    export_preview_dir: Path,
    tmp_path: Path,
) -> None:
    """out の親のフォルダが無ければ書かない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    workspace = store.load_workspace(root)
    out = tmp_path / "無い" / "配る.html"
    fetch, _calls = make_fetch(_export_responses())
    # 実行・検証
    with pytest.raises(WriteFailedError):
        builder.export_preview(
            workspace, out=out, built_at=BUILT_AT, preview_dir=export_preview_dir, fetch=fetch
        )
    assert not (tmp_path / "無い").exists()


def test_validate_export_out(tmp_path: Path) -> None:
    """大文字の拡張子も受け、絶対パスにする（正常系）。"""
    # 実行
    result = builder.validate_export_out(tmp_path / "sub" / ".." / "配る.HTML")
    # 検証
    assert result == tmp_path / "配る.HTML"


def test_validate_export_out_when_invalid(tmp_path: Path) -> None:
    """html でない out を弾く（異常系）。"""
    # 実行・検証
    with pytest.raises(errors.ArgumentError, match=r"out.*\.html"):
        builder.validate_export_out(tmp_path / "配る.txt")


def test_fetch_url(local_server: str) -> None:
    """本文を返す（正常系）。"""
    # 実行
    body = builder.fetch_url(f"{local_server}/a.js")
    # 検証
    assert body == SERVED_BODY


@pytest.mark.parametrize(
    ("make_url", "expected_waits"),
    [
        pytest.param(lambda base, closed: closed, [1.0, 2.0], id="closed_port"),
        pytest.param(lambda base, closed: f"{base}/missing", [], id="not_found"),
        pytest.param(lambda base, closed: f"{base}/no-content", [], id="no_content"),
    ],
)
def test_fetch_url_when_unreachable(
    local_server: str,
    closed_url: str,
    waits: list[float],
    make_url: Callable[[str, str], str],
    expected_waits: list[float],
) -> None:
    """届かないか 200 以外なら DownloadFailedError にする。届かないときだけ取り直す（異常系）。"""
    # 準備
    url = make_url(local_server, closed_url)
    # 実行・検証
    with pytest.raises(errors.DownloadFailedError, match=re.escape(url)):
        builder.fetch_url(url)
    # 取り直したときだけ間隔を待つ（閉じたポートは 3 回の要求、404・204 は 1 回）
    assert waits == expected_waits
    path = url.removeprefix(local_server)
    if path != url:
        assert _Handler.requests[path] == 1


@pytest.mark.parametrize(
    ("path", "expected_waits"),
    [
        pytest.param("/flaky-403", [1.0], id="forbidden"),
        pytest.param("/flaky-429", [1.0], id="too_many_requests"),
        pytest.param("/flaky-503", [1.0], id="service_unavailable"),
    ],
)
def test_fetch_url_when_transient_failure(
    local_server: str, waits: list[float], path: str, expected_waits: list[float]
) -> None:
    """一時的な失敗の後に取り直して本文を返す（正常系）。"""
    # 実行
    body = builder.fetch_url(f"{local_server}{path}")
    # 検証
    assert body == SERVED_BODY
    assert _Handler.requests[path] == 2
    assert waits == expected_waits


def test_fetch_url_when_retries_exhausted(local_server: str, waits: list[float]) -> None:
    """上限まで取れなければ DownloadFailedError にする（異常系）。"""
    # 準備
    url = f"{local_server}/always-403"
    # 実行・検証
    with pytest.raises(errors.DownloadFailedError, match=re.escape(url) + r".*403"):
        builder.fetch_url(url)
    assert _Handler.requests["/always-403"] == 3
    assert waits == [1.0, 2.0]


def test_format_licenses() -> None:
    """ライブラリごとに名前・版・著作権・ライセンス・入手先・本文を並べる（正常系）。"""
    # 準備
    first = builder.LicenseBlock(
        library=make_library(
            "a",
            name="A",
            notice="(c) A",
            license="MIT",
            repository="https://example.com/a",
            tag="v{version}",
        ),
        version="1.2.3",
        license_text="本文 A",
        bundled_text=None,
    )
    second = builder.LicenseBlock(
        library=make_library(
            "b",
            name="B",
            notice="(c) B",
            license="EPL-2.0",
            repository="https://example.com/b",
            tag="{version}",
        ),
        version="4.5.6",
        license_text="本文 B",
        bundled_text="束ねた本文",
    )
    # 実行
    text = builder.format_licenses([first, second])
    # 検証
    _assert_in_order(
        text,
        [
            "A 1.2.3",
            "(c) A",
            "License: MIT",
            "Source: https://example.com/a/tree/v1.2.3",
            "本文 A",
            "\n\nB 4.5.6",
            "(c) B",
            "License: EPL-2.0",
            "Source: https://example.com/b/tree/4.5.6",
            "本文 B",
            "B が中に持つライブラリ",
            "束ねた本文",
        ],
    )
    assert "A が中に持つライブラリ" not in text


# jsDelivr の mdmark の配布物の URL の頭
MDMARK_CDN = "https://cdn.jsdelivr.net/gh/shuhei1101/mdmark"


@pytest.mark.parametrize(
    ("ref", "path", "expected"),
    [
        pytest.param(
            "0123456789abcdef0123456789abcdef01234567",
            "index.js",
            f"{MDMARK_CDN}@0123456789abcdef0123456789abcdef01234567/dist/index.js",
            id="commit",
        ),
        pytest.param("develop", "index.css", f"{MDMARK_CDN}@develop/dist/index.css", id="branch"),
        pytest.param("v0.13.0", "map.js", f"{MDMARK_CDN}@v0.13.0/dist/map.js", id="tag"),
    ],
)
def test_mdmark_dist_url(ref: str, path: str, expected: str) -> None:
    """ref をそのまま URL に入れる（正常系）。"""
    # 実行・検証
    assert builder.mdmark_dist_url(ref, path) == expected


def test_load_libraries(tmp_path: Path) -> None:
    """一覧を並びの順に読む（正常系）。"""
    # 準備
    scripts: list[Script] = [("b", b"/* b */"), ("a", b"/* a */")]
    write_export_preview_dir(tmp_path, scripts)
    # 実行
    result = builder.load_libraries(preview_dir=tmp_path)
    # 検証
    assert [(row.package, row.version, row.url, row.integrity) for row in result] == [
        ("b", "1.0.0", "https://cdn.jsdelivr.net/npm/b@1.0.0/b.js", integrity_of(b"/* b */")),
        ("a", "1.0.0", "https://cdn.jsdelivr.net/npm/a@1.0.0/a.js", integrity_of(b"/* a */")),
    ]


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(None, id="missing"),
        pytest.param('{"package": "a"}', id="not_list"),
        pytest.param(
            '[{"package": "a", "version": "1.0.0", "url": "https://cdn.jsdelivr.net/npm/a@1.0.0/a.js"}]',
            id="integrity_missing",
        ),
        pytest.param(
            '[{"package": "a", "version": "1.0.0", "url": "https://cdn.jsdelivr.net/npm/a/a.js",'
            ' "integrity": "sha384-AAA"}]',
            id="version_missing",
        ),
    ],
)
def test_load_libraries_when_invalid(tmp_path: Path, content: str | None) -> None:
    """形式の違う一覧（異常系）。"""
    # 準備
    if content is not None:
        (tmp_path / builder.LIBRARIES_FILE).write_text(content, encoding="utf-8")
    # 実行・検証
    with pytest.raises(ValueError, match="描画のライブラリの一覧が読めません"):
        builder.load_libraries(preview_dir=tmp_path)


def test_libraries_match_vendor_libraries() -> None:
    """本物の一覧と VENDOR_LIBRARIES が 1 対 1 で結べる（正常系）。"""
    # 準備
    libraries = builder.VENDOR_LIBRARIES
    # 実行
    scripts = builder.load_libraries()
    # 検証
    assert [builder.MDMARK_PACKAGE, *(script.package for script in scripts)] == [
        library.package for library in libraries
    ]
    # ライセンスの本文は、取る（license_path）か読む（license_file）かのちょうど一方
    assert [
        library.package
        for library in libraries
        if (library.license_path is None) == (library.license_file is None)
    ] == []
    local_files = [
        name
        for library in libraries
        for name in (library.license_file, library.bundled_license_file)
        if name is not None
    ]
    assert [name for name in local_files if not (builder.PREVIEW_DIR / name).is_file()] == []


# 組み立てのテストの描画のライブラリ（2 つのパッケージ）
ASSEMBLE_SCRIPTS: list[Script] = [("a", b"/* a */"), ("b", b"/* b */")]


def _assemble_mdmark_library() -> builder.VendorLibrary:
    """ライセンスをプレビューのフォルダの licenses/m.txt から読み、束ねた依存のライセンスを dist/T.txt から取る mdmark を返す。"""
    return make_library(
        builder.MDMARK_PACKAGE,
        license_path=None,
        license_file="licenses/m.txt",
        bundled_license_path="dist/T.txt",
    )


def _assemble_preview_dir(
    tmp_path: Path, html: str | None = None, scripts: list[Script] = ASSEMBLE_SCRIPTS
) -> Path:
    """組み立てのテストのプレビューのフォルダ（scripts の libraries.json と licenses/m.txt）を返す。"""
    folder = tmp_path / "preview"
    write_export_preview_dir(folder, scripts, html)
    (folder / "licenses" / "m.txt").write_text("本文 m", encoding="utf-8")
    return folder


def _assemble_responses(scripts: list[Script]) -> dict[str, bytes]:
    """組み立てのテストで取る URL → 中身（mdmark・配布ファイル・ライセンスの本文）を返す。"""
    responses = make_responses(scripts, mdmark=MODULE, mdmark_ref=MDMARK_VERSION)
    responses[mdmark_url("T.txt", MDMARK_VERSION)] = "束ねた本文 m".encode()
    return responses


def test_assemble_export_html(tmp_path: Path) -> None:
    """最後の </body> の前に mdmark・ライブラリ・記録・ライセンスを差し込む（正常系）。"""
    # 準備
    folder = _assemble_preview_dir(tmp_path, export_html('<script>const s = "</body>";</script>'))
    fetch, _calls = make_fetch(_assemble_responses(ASSEMBLE_SCRIPTS))
    libraries = (_assemble_mdmark_library(), make_library("a"), make_library("b"))
    data = {"bodies": {"../docs/A-1.mark.md": "本文 </script>\n"}}
    # 実行
    html = builder.assemble_export_html(
        data, preview_dir=folder, libraries=libraries, fetch=fetch, mdmark_ref=MDMARK_VERSION
    )
    # 検証
    assert "https://" not in html
    assert "fonts.googleapis.com" not in html
    assert '<script>const s = "</body>";</script>' in html
    assert html.endswith("</body></html>")
    _assert_in_order(
        html,
        [
            '<script>const s = "</body>";</script>',
            ".m{}",
            "/* m */",
            "/* a */",
            "/* b */",
            builder.DATA_OPEN,
            builder.LICENSES_OPEN,
            "</body></html>",
        ],
    )
    assert _read_embedded(html) == data
    licenses = html.split(builder.LICENSES_OPEN, 1)[1].split("</script>", 1)[0]
    _assert_in_order(licenses, ["本文 m", "束ねた本文 m", "本文 a", "本文 b", "React の画面が中に持つライブラリ"])
    assert licenses.rstrip().endswith("React の依存")


@pytest.mark.parametrize(
    ("html", "listed", "fetched", "error", "match"),
    [
        pytest.param(
            "<html><body></html>",
            ASSEMBLE_SCRIPTS,
            ASSEMBLE_SCRIPTS,
            ValueError,
            "</body> がありません",
            id="body_missing",
        ),
        pytest.param(
            None,
            ASSEMBLE_SCRIPTS,
            [("a", b"/* x */"), ("b", b"/* b */")],
            errors.DownloadFailedError,
            re.escape(dist_url("a")),
            id="integrity_mismatch",
        ),
        pytest.param(
            None,
            [("a", b"/* a */"), ("b", b"x </SCRIPT> y")],
            [("a", b"/* a */"), ("b", b"x </SCRIPT> y")],
            ValueError,
            re.escape(dist_url("b")),
            id="closing_tag",
        ),
    ],
)
def test_assemble_export_html_when_invalid(
    tmp_path: Path,
    html: str | None,
    listed: list[Script],
    fetched: list[Script],
    error: type[Exception],
    match: str,
) -> None:
    """ビルド・配布ファイルが違う（異常系）。"""
    # 準備
    # libraries.json の integrity は listed の中身のもの。取る中身は fetched にする
    folder = _assemble_preview_dir(tmp_path, html, listed)
    fetch, _calls = make_fetch(_assemble_responses(fetched))
    libraries = (_assemble_mdmark_library(), make_library("a"), make_library("b"))
    # 実行・検証
    with pytest.raises(error, match=match):
        builder.assemble_export_html(
            {}, preview_dir=folder, libraries=libraries, fetch=fetch, mdmark_ref=MDMARK_VERSION
        )
