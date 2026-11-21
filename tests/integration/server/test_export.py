"""export（配る書き出し）の結合テスト。

正常系と、書き出す前に jsDelivr から取る異常系は、実際の jsDelivr へ HTTPS で届く環境で動かす。
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from .fixture_types import CallTool, MakeItem, MakeWorkspace, SnapshotTree, StartServer
from .http_helpers import http_request
from workspace_fixtures import DEFAULT_TIMESTAMP, RECORD_DIR

# このファイルから見たリポジトリの直下（tests/integration/server の 3 つ上）
REPO_ROOT_PARENT_DEPTH = 3
PREVIEW_DIR = (
    Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH]
    / "plugins"
    / "mindstella"
    / "skills"
    / "mindmap"
    / "preview"
)

# 書き出し用のビルドと、描画のライブラリの一覧
EXPORT_HTML_PATH = PREVIEW_DIR / "export" / "index.html"
LIBRARIES_PATH = PREVIEW_DIR / "libraries.json"

# 埋め込み先・ライセンスの表示の要素の開きタグ
DATA_ELEMENT_OPEN = '<script type="application/json" id="mindmap-data">'
LICENSES_ELEMENT_OPEN = '<script type="text/plain" id="mindmap-licenses">'
MDMARK_ELEMENT_OPEN = '<script type="text/plain" id="mindmap-mdmark">'
MDMARK_CSS_ELEMENT_OPEN = '<style id="mindmap-mdmark-css">'

# 配る書き出しが中身を持つ mdmark の部品の名前
MDMARK_PARTS = ("map", "view", "comments")

# 配る書き出しが書き出し用のビルドに足す `</script>` を持つ要素の数（mdmark の JavaScript・部品の 3 つ・描画のライブラリの 3 つ・記録・ライセンスの表示）
EXPORT_ADDED_ELEMENTS = 9

# ライセンスの表示の、React の画面が中に持つライブラリの見出しと、その中にあるライブラリの例
FRONTEND_LICENSES_HEADING = "React の画面が中に持つライブラリ"
FRONTEND_LICENSE_EXAMPLE = "## react - "

# 設定の mdmark のバージョンが無いとき（latest）に読む mdmark の ref（develop の先頭の commit の SHA。問い合わせられなければ develop）
MDMARK_LATEST_REF = re.compile(r"mdmark (?:[0-9a-f]{40}|develop)\n")

# 資料の本文（要素を閉じる文字列を含む）
BODY_WITH_SCRIPT_TAG = "本文に </script> を含む\n"

# HTML で書いた資料の本文（`<style>` と `<script>` と段落を持つ。`</script>` で埋め込みの要素を閉じない）
HTML_BODY = (
    "<style>p { color: red; }</style>\n"
    "<script>window.opened = true;</script>\n"
    "<p>一覧の画面</p>\n"
)

# jsDelivr に届かないようにする環境変数（届かない宛先のプロキシを通す）
UNREACHABLE_PROXY_ENV = {
    "HTTPS_PROXY": "http://127.0.0.1:9",
    "https_proxy": "http://127.0.0.1:9",
}

# 中に持つライブラリごとの、表示に出るライセンスの名前と著作権の表示（libraries.json のパッケージ名 → 表示）
EXPECTED_LICENSES = {
    "marked": ("marked", "MIT", "Copyright (c) 2018+, MarkedJS"),
    "mermaid": ("mermaid", "MIT", "Copyright (c) 2014 - 2022 Knut Sveidqvist"),
    "diff": ("jsdiff", "BSD-3-Clause", "Copyright (c) 2009-2015, Kevin Decker"),
}

# 書き換えのまとまりを 1 つ持つ `changes.yaml`
COMMITTED_CHANGES = (
    "last_seq: 0\nsets:\n- id: V-1\n  at: '2026-10-01T00:00:00+00:00'\n  summary: 足す\n"
    "  until_seq: 0\n  added: [D-1]\n  changed: []\npending:\n  added: []\n  changed: []\n"
)

# mdmark の表示に出るライセンスの名前と著作権の表示
EXPECTED_MDMARK_LICENSE = ("mdmark", "MIT", "Copyright (c) 2026 shuhei1101")

# mdmark の配布物が中に束ねた依存のライセンスの本文の先頭の行（`THIRD_PARTY_LICENSES.txt` の最初の依存）
MDMARK_BUNDLED_LICENSES_HEAD = "dayjs 1.11.23 (MIT)"


class _ExternalReferences(HTMLParser):
    """script・img の src と link の href を持つ要素を集める。"""

    def __init__(self) -> None:
        """集めた要素のタグ名と属性の並びと、import map の要素の数を空で持つ。"""
        super().__init__()
        self.found: list[tuple[str, dict[str, str | None]]] = []
        self.import_maps = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """外のファイルや URL を指す属性を持つ要素と、import map の要素を控える。"""
        values = dict(attrs)
        if tag == "script" and values.get("type") == "importmap":
            self.import_maps += 1
        if (tag in ("script", "img") and "src" in values) or (tag == "link" and "href" in values):
            self.found.append((tag, values))


def _stamped(item: dict[str, Any]) -> dict[str, Any]:
    """項目に、history.yaml の行の作成日時・更新日時（make_workspace の既定の日時）を合わせた形を返す。"""
    return {**item, "created": DEFAULT_TIMESTAMP, "updated": DEFAULT_TIMESTAMP}



def _read_element(html: str, open_tag: str) -> str:
    """HTML の指定した script 要素の中身を返す。"""
    return html.split(open_tag, 1)[1].split("</script>", 1)[0]


def _library_versions() -> dict[str, str]:
    """描画のライブラリの一覧から、パッケージ名 → バージョンを読む。"""
    rows = json.loads(LIBRARIES_PATH.read_text(encoding="utf-8"))
    return {row["package"]: row["version"] for row in rows}


def _build_closes() -> int:
    """書き出し用のビルドの中の `</script>` の数を返す。"""
    return EXPORT_HTML_PATH.read_text(encoding="utf-8").count("</script>")


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    tmp_path: Path,
    valid_settings: dict[str, Any],
) -> None:
    """記録・画面・描画のライブラリ・ライセンスの表示を中に持つ 1 枚の HTML を `out` へ書き出す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("T-1"),
        make_item("R-1"),
        make_item("A-1"),
        make_item("G-1"),
        make_item("N-1"),
        make_item("L-1"),
        bodies={"A-1.mark.md": BODY_WITH_SCRIPT_TAG},
        raw_files={"changes.yaml": COMMITTED_CHANGES},
    )
    before = snapshot_tree(root)
    out = tmp_path / "配る.html"
    # 実行
    result = call_tool("export", workspace=str(root), out=str(out))
    # 検証
    assert result.is_error is False, result.text
    assert result.data == {"path": str(out)}
    html = out.read_text(encoding="utf-8")
    data = json.loads(_read_element(html, DATA_ELEMENT_OPEN))
    assert data["settings"] == valid_settings
    assert data["decisions"] == [_stamped(make_item("D-1"))]
    assert data["tasks"] == [_stamped(make_item("T-1"))]
    assert data["research"] == [_stamped(make_item("R-1"))]
    assert data["docs"] == [_stamped(make_item("A-1"))]
    assert data["terms"] == [_stamped(make_item("G-1"))]
    assert data["notes"] == [_stamped(make_item("N-1"))]
    assert data["logs"] == [_stamped(make_item("L-1"))]
    assert data["bodies"] == {"../docs/A-1.mark.md": BODY_WITH_SCRIPT_TAG}
    assert [entry["id"] for entry in data["changes"]["sets"]] == ["V-1"]
    # script・link・img が外のファイルや URL を指さず、import map も無い
    references = _ExternalReferences()
    references.feed(html)
    assert references.found == []
    assert references.import_maps == 0
    # 本文の </script> で要素が閉じていない（書き出し用のビルドの閉じタグの数に、足した要素の 9 つを足した数）
    assert html.count("</script>") == _build_closes() + EXPORT_ADDED_ELEMENTS
    # mdmark の JavaScript と部品の要素が中身を持つ
    assert _read_element(html, MDMARK_ELEMENT_OPEN) != ""
    for part in MDMARK_PARTS:
        assert _read_element(html, f'<script type="text/plain" id="mindmap-mdmark-{part}">') != ""
    # mdmark の CSS が id を持つ `<style>` の中身になる
    assert html.split(MDMARK_CSS_ELEMENT_OPEN, 1)[1].split("</style>", 1)[0] != ""
    # ライセンスの表示に、ライブラリごとの名前・版・著作権の表示・ライセンスの名前がある
    licenses = _read_element(html, LICENSES_ELEMENT_OPEN)
    versions = _library_versions()
    for package, (name, license_name, notice) in EXPECTED_LICENSES.items():
        assert f"{name} {versions[package]}" in licenses
        assert notice in licenses
        assert f"License: {license_name}" in licenses
    # mdmark は、名前・版・著作権の表示・ライセンスの名前と、配布物が中に束ねた依存のライセンスの本文を持つ
    _, mdmark_license, mdmark_notice = EXPECTED_MDMARK_LICENSE
    # 設定のバージョンが無いワークスペースは develop の最新（先頭の commit）を書き出す
    assert MDMARK_LATEST_REF.search(licenses) is not None, licenses[:500]
    assert mdmark_notice in licenses
    assert f"License: {mdmark_license}" in licenses
    assert MDMARK_BUNDLED_LICENSES_HEAD in licenses
    # React の画面が中に束ねたライブラリのライセンスが、見出しの後に続く
    assert FRONTEND_LICENSES_HEADING in licenses
    assert FRONTEND_LICENSE_EXAMPLE in licenses.split(FRONTEND_LICENSES_HEADING, 1)[1]
    # ワークスペースは書き換えない
    assert snapshot_tree(root) == before


def test_normal_when_html_body(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    serve_preview: Callable[[Path], str],
    tmp_path: Path,
) -> None:
    """HTML の本文も、原文と行の印を足したものを埋め込みのデータに入れる（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1", body="../docs/A-1.html"), bodies={"A-1.html": HTML_BODY}
    )
    out = tmp_path / "配る.html"
    # 実行
    result = call_tool("export", workspace=str(root), out=str(out))
    # 検証
    assert result.is_error is False, result.text
    html = out.read_text(encoding="utf-8")
    data = json.loads(_read_element(html, DATA_ELEMENT_OPEN))
    assert data["bodies"]["../docs/A-1.html"] == HTML_BODY
    # 『記録の取得』と同じ行の印つきの本文を持つ
    records = http_request(serve_preview(root), "/api/records").json()
    assert data["marked_bodies"]["../docs/A-1.html"] == records["marked_bodies"]["../docs/A-1.html"]
    # 本文の `</script>` で埋め込みの要素が閉じていない
    assert html.count("</script>") == _build_closes() + EXPORT_ADDED_ELEMENTS


def test_error_when_out_not_html(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
    tmp_path: Path,
) -> None:
    """書き出す先が .html で終わらないと、何も書かずに終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    out = tmp_path / "配る.txt"
    # 実行
    result = call_tool("export", workspace=str(root), out=str(out))
    # 検証
    assert result.is_error is True
    assert "out" in result.text
    assert not out.exists()
    assert snapshot_tree(root) == before


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すと何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out = out_dir / "配る.html"
    # 実行
    result = call_tool("export", workspace=str(root), out=str(out))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text
    assert not out.exists()


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    tmp_path: Path,
) -> None:
    """手で崩した YAML があると、前に書き出した `out` のファイルを残して終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    out = tmp_path / "配る.html"
    assert call_tool("export", workspace=str(root), out=str(out)).is_error is False
    before = out.read_bytes()
    (root / RECORD_DIR / "decisions.yaml").write_text(
        yaml.safe_dump({"items": [make_item("D-1", status="完了")]}, allow_unicode=True),
        encoding="utf-8",
    )
    # 実行
    result = call_tool("export", workspace=str(root), out=str(out))
    # 検証
    assert result.is_error is True
    assert "decisions.yaml: items[0].status:" in result.text
    assert out.read_bytes() == before


def test_error_when_out_dir_missing(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    tmp_path: Path,
) -> None:
    """`out` の親のフォルダが無いと、フォルダを作らずに終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    out = tmp_path / "無い" / "配る.html"
    # 実行
    result = call_tool("export", workspace=str(root), out=str(out))
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert str(out) in result.text
    assert "Traceback" not in result.text
    assert not (tmp_path / "無い").exists()


def test_error_when_download_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    call_tool: CallTool,
    start_server: StartServer,
    tmp_path: Path,
) -> None:
    """jsDelivr に届かないと、何も書かずに終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    out = tmp_path / "配る.html"
    assert call_tool("export", workspace=str(root), out=str(out)).is_error is False
    before = out.read_bytes()
    # 届かない宛先のプロキシを通すため、環境変数を足したサーバーを立てる
    offline_server = start_server(extra_env=UNREACHABLE_PROXY_ENV)
    # 実行
    result = offline_server.call("export", workspace=str(root), out=str(out))
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: ")
    assert "https://cdn.jsdelivr.net/" in result.text
    assert "Traceback" not in result.text
    assert out.read_bytes() == before
