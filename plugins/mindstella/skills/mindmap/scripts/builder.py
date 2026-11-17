"""ワークスペースの記録を 1 つの JSON にまとめ、プレビューの雛形に差し込み、配る書き出しを書く。"""

from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import re
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from html.parser import HTMLParser
from http import HTTPStatus
from pathlib import Path
from typing import Any, cast

import store
from errors import ArgumentError, DownloadFailedError
from graph import is_settled, judge_goal, list_next_candidates
from history import load_changes, load_item_history, merge_item_history
from html_body import mark_lines
from kinds import KINDS, SETTINGS_FILE
from store import NowFn, Workspace, now_utc

# このファイルから見た `skills/mindmap/preview/`
PREVIEW_DIR = Path(__file__).resolve().parent.parent / "preview"

# 雛形のフォルダの中の雛形の HTML
TEMPLATE_FILE = "template.html"

# 雛形がちょうど 1 つ持つ、中身が空の埋め込み先の要素
DATA_ELEMENT = '<script type="application/json" id="mindmap-data"></script>'

# 差し込む CSS（雛形のフォルダからの相対パス。並びの順につなぐ）
STYLE_FILES = ("tokens.css", "style.css")

# 差し込む JavaScript（tsc が `.ts` から生成した `.js`。並びの順につなぎ、起動する `app.js` が最後）
SCRIPT_FILES = (
    "core/dom.js",
    "core/records.js",
    "core/libs.js",
    "core/doc-export.js",
    "core/diff.js",
    "core/router.js",
    "core/api.js",
    "core/edits.js",
    "core/lock.js",
    "core/voice.js",
    "components/view-switch.js",
    "components/duplicate-id-notice.js",
    "components/topbar.js",
    "components/diff-mark.js",
    "components/removed-band.js",
    "components/withdrawn-badge.js",
    "components/comment-mark.js",
    "components/tag-list.js",
    "components/chips-input.js",
    "components/history-dialog.js",
    "components/table.js",
    "components/filter-drawer.js",
    "components/send-form.js",
    "components/reply-form.js",
    "components/thread-row.js",
    "components/thread-post.js",
    "components/review-body-fold.js",
    "components/selection-comment.js",
    "components/term-tip.js",
    "components/settings-panel.js",
    "components/settings-confirm.js",
    "components/body-format-badge.js",
    "components/html-body-frame.js",
    "components/html-body-diff.js",
    "components/markdown-body.js",
    "components/doc-export-menu.js",
    "components/body-diff-layout-switch.js",
    "components/side-by-side-body-diff.js",
    "components/diff-minimap.js",
    "components/pending-mark.js",
    "screens/overview.js",
    "screens/decisions.js",
    "screens/tasks.js",
    "screens/docs.js",
    "screens/records.js",
    "screens/detail-edit.js",
    "screens/detail.js",
    "screens/comments.js",
    "screens/pending-edits.js",
    "screens/workspace-settings.js",
    "screens/settings.js",
    "screens/search.js",
    "screens/diagram-viewer.js",
    "graph/looks.js",
    "graph/graph.js",
    "app.js",
)

# `template.html` がちょうど 1 つ持つ、CSS を入れる空の要素
STYLE_SLOT = '<style id="mindmap-style"></style>'

# `template.html` がちょうど 1 つ持つ、JavaScript を入れる空の要素（埋め込み先より後ろ）
SCRIPT_SLOT = '<script id="mindmap-app"></script>'

# 埋め込み先・差し込み口の要素を閉じるタグ
CLOSE_TAG = "</script>"
STYLE_CLOSE_TAG = "</style>"

# jsDelivr への 1 回の要求で、接続と 1 回の読み取りをそれぞれ待つ秒数
FETCH_TIMEOUT_SEC = 30

# jsDelivr の、版を固定したパッケージの中のファイルの URL の形（ライセンスの本文を取るのに使う）
CDN_PACKAGE_URL = "https://cdn.jsdelivr.net/npm/{package}@{version}/{path}"

# jsDelivr の、タグを固定した GitHub のリポジトリの中のファイルの URL の形（mdmark の配布物と同梱物のライセンスを取るのに使う）
CDN_REPO_URL = "https://cdn.jsdelivr.net/gh/{package}@{version}/{path}"

# `template.html` がちょうど 1 つ持つ、外の読み込み（mdmark の差し込み口・描画のライブラリの `<script src>` と文字の `<link>`）の前後に置くコメント
EXTERNAL_START = "<!-- mindmap-external:start -->"
EXTERNAL_END = "<!-- mindmap-external:end -->"

# 配る書き出しに置く、ライセンスの表示を中身に持つ要素の開きタグ（画面には出ない）
LICENSES_OPEN = '<script type="text/plain" id="mindmap-licenses">'

# 配る書き出しに置く、mdmark の JavaScript を中身に持つ要素の開きタグ（閉じタグは `</script>`）。画面の JavaScript が中身から Blob の URL を作って `import()` する
MDMARK_OPEN = '<script type="text/plain" id="mindmap-mdmark">'

# 配る書き出しに置く、mdmark の CSS を中身に持つ要素の開きタグ（閉じタグは `</style>`）。画面の JavaScript が資料の HTML のエクスポートでこの中身を使う
MDMARK_CSS_OPEN = '<style id="mindmap-mdmark-css">'

# 雛形の外の読み込みの間に 1 つだけ置く、mdmark の読み込みの差し込み口
MDMARK_SLOT = "<!-- mindmap-mdmark -->"

# 画面が mdmark の JavaScript の URL と `mount` に指定する `map` を読む JSON の要素の開きタグ（閉じタグは `</script>`）
MDMARK_CONFIG_OPEN = '<script type="application/json" id="mindmap-mdmark-config">'

# `CDN_REPO_URL` の `package` に入れる mdmark のリポジトリ
MDMARK_PACKAGE = "shuhei1101/mdmark"

# `dist/index.js` が隣から `import()` する部品の配布ファイル
MDMARK_PART_FILES = ("map.js", "view.js", "comments.js")

# 設定の mdmark のバージョンの既定と、`latest` が指す mdmark のブランチ
MDMARK_LATEST = "latest"
MDMARK_LATEST_REF = "develop"

# 配る書き出しに置く、mdmark の部品を中身に持つ要素の開きタグ（`{name}` に部品の名前）
MDMARK_PART_OPEN = '<script type="text/plain" id="mindmap-mdmark-{name}">'

# 雛形の外の読み込みの `src`（jsDelivr の版を固定した URL）を、パッケージ名・版・ファイルに分ける
_EXTERNAL_SRC = re.compile(
    r"^https://cdn\.jsdelivr\.net/npm/(?P<package>(?:@[^/@]+/)?[^/@]+)@(?P<version>[^/]+)/.+$"
)

# 差し込む中身が、script 要素を閉じる・開くタグを含むかを見る文字列（小文字で比べる）
_SCRIPT_TAGS = ("</script", "<script")

# 差し込む CSS が、style 要素を閉じるタグを含むかを見る文字列（小文字で比べる）
_STYLE_TAGS = ("</style",)


@dataclass(frozen=True, slots=True, kw_only=True)
class VendorLibrary:
    """雛形の描画のライブラリ 1 つの、ライセンスの表示に使う値。"""

    # 雛形の外の読み込みの URL のパッケージ名と結ぶ（npm はパッケージ名、GitHub は `{owner}/{repo}`）
    package: str
    # 表示する名前
    name: str
    # 著作権の表示
    notice: str
    # 配るときのライセンスの名前（選べるライセンスを持つときは選んだもの）
    license: str
    # パッケージの中のライセンスの本文のファイル。取らずに `license_file` から読むライブラリは None
    license_path: str | None
    # ライセンスの本文を取らずに読む、雛形のフォルダからの相対パス。`license_path` が None のライブラリだけが持つ
    license_file: str | None
    # 配布物が中に束ねた依存のライセンスを並べた、パッケージの中のファイル（取る）。`bundled_license_file` と両方は持たない。無ければ None
    bundled_license_path: str | None
    # 配布ファイルが中に束ねた依存のライセンスを並べたファイル（雛形のフォルダからの相対パス）。無ければ None
    bundled_license_file: str | None
    # ソースコードのリポジトリの URL
    repository: str
    # 版のタグの形（`{version}` に外の読み込みの版を入れる）
    tag: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ExternalScript:
    """雛形の外の読み込みの `<script src integrity>` 1 つ。"""

    url: str
    # `sha384-{Base64}`
    integrity: str
    package: str
    version: str


@dataclass(frozen=True, slots=True, kw_only=True)
class LicenseBlock:
    """ライブラリ 1 つのライセンスの表示を組み立てる材料。"""

    library: VendorLibrary
    # 外の読み込みの版
    version: str
    # 取ったか `license_file` から読んだライセンスの本文
    license_text: str
    # 束ねた依存のライセンス（`bundled_license_file` の中身か、`bundled_license_path` から取った本文）。無ければ None
    bundled_text: str | None


# 配る書き出しに入れるライブラリ（`package` で mdmark と雛形の外の読み込みと結ぶ。版・URL・integrity は設定と雛形が持つ）
VENDOR_LIBRARIES = (
    VendorLibrary(
        package="shuhei1101/mdmark",
        name="mdmark",
        notice="Copyright (c) 2026 shuhei1101",
        license="MIT",
        license_path=None,
        license_file="licenses/mdmark-LICENSE.txt",
        bundled_license_path="dist/THIRD_PARTY_LICENSES.txt",
        bundled_license_file=None,
        repository="https://github.com/shuhei1101/mdmark",
        tag="{version}",
    ),
    VendorLibrary(
        package="marked",
        name="marked",
        notice="Copyright (c) 2018+, MarkedJS / Copyright (c) 2011-2018, Christopher Jeffrey",
        license="MIT",
        license_path="LICENSE",
        license_file=None,
        bundled_license_path=None,
        bundled_license_file=None,
        repository="https://github.com/markedjs/marked",
        tag="v{version}",
    ),
    VendorLibrary(
        package="elkjs",
        name="elkjs",
        notice="(c) Kiel University and others",
        license="EPL-2.0",
        license_path="LICENSE.md",
        license_file=None,
        bundled_license_path=None,
        bundled_license_file=None,
        repository="https://github.com/kieler/elkjs",
        tag="{version}",
    ),
    VendorLibrary(
        package="mermaid",
        name="mermaid",
        notice="Copyright (c) 2014 - 2022 Knut Sveidqvist",
        license="MIT",
        license_path="LICENSE",
        license_file=None,
        bundled_license_path=None,
        bundled_license_file="licenses/mermaid-bundled.txt",
        repository="https://github.com/mermaid-js/mermaid",
        tag="mermaid@{version}",
    ),
    VendorLibrary(
        package="diff",
        name="jsdiff",
        notice="Copyright (c) 2009-2015, Kevin Decker",
        license="BSD-3-Clause",
        license_path="LICENSE",
        license_file=None,
        bundled_license_path=None,
        bundled_license_file=None,
        repository="https://github.com/kpdecker/jsdiff",
        tag="v{version}",
    ),
)

# URL を受けて本文のバイト列を返す関数（取れなければ DownloadFailedError を送る）
type FetchFn = Callable[[str], bytes]


def replace_file(path: Path, text: str) -> None:
    """同じフォルダの一時ファイルに書いてから `os.replace` で置き換える（途中で止まっても前のファイルを壊さない）。"""
    temp: Path | None = None
    try:
        temp = store.write_temp(path, text)
        os.replace(temp, path)
    except OSError as error:
        # 書き込みか置き換えに失敗した（親のフォルダが無いときも）: 残った一時ファイルを消す
        if temp is not None:
            temp.unlink(missing_ok=True)
        raise store.write_failed(path, error) from error


def collect_preview_data(
    workspace: Workspace, *, built_at: str, settings_problem: list[str] | None = None
) -> dict[str, Any]:
    """設定・7 種類・本文・まとまり・画面に出す値・読んだ日時・設定の問題を 1 つの辞書にまとめる（送信は含めない）。"""
    data: dict[str, Any] = {"settings": workspace.settings}
    rows = load_item_history(workspace.root)
    # 種類ごとの items を、ファイル名から `.yaml` を落としたキーで、history.yaml の行を合わせて入れる
    for kind, spec in KINDS.items():
        data[spec.file.removesuffix(".yaml")] = [
            merge_item_history(item, rows) for item in workspace.items[kind]
        ]
    # 項目の body が指す本文だけを集める（読めないものは入れない）
    bodies: dict[str, str] = {}
    marked_bodies: dict[str, str] = {}
    for kind in KINDS:
        for item in workspace.items[kind]:
            body = item.get("body")
            if not isinstance(body, str):
                continue
            text = store.read_body(workspace, body)
            if text is not None:
                bodies[body] = text
                # HTML の本文は、開きタグに原文の行の印を足したものも渡す
                if store.body_format(body) == "html":
                    marked_bodies[body] = mark_lines(text)
    data["bodies"] = bodies
    data["marked_bodies"] = marked_bodies
    # 書き換えのまとまり（項目の `history` は項目に合わせて入っている）
    data["changes"] = load_changes(workspace.root)
    data["derived"] = derive_preview_values(workspace)
    data["built_at"] = built_at
    # config.yaml がスキーマに合わないときの、合わない箇所の行（合うときと配る書き出しは null）
    data["settings_problem"] = settings_problem
    return data


def read_records(
    root: Path, *, last_settings: dict[str, Any] | None = None, now: NowFn = now_utc
) -> dict[str, Any]:
    """ワークスペースをその場で読んで検証し、記録の取得の辞書にして返す。config.yaml だけが合わないときは last_settings で返す。"""
    workspace = store.load_workspace(root)
    problems = store.validate_workspace(workspace)
    # config.yaml の問題とそれ以外に分ける
    settings_problems = [problem for problem in problems if problem.file == SETTINGS_FILE]
    other_problems = [problem for problem in problems if problem.file != SETTINGS_FILE]
    # config.yaml 以外に問題があるときは返さない
    if other_problems:
        raise store.build_mismatch_error(other_problems, workspace)
    # config.yaml が合わないが、最後に検査に通った設定が無いときも返さない
    if settings_problems and last_settings is None:
        raise store.build_mismatch_error(settings_problems, workspace)
    # config.yaml だけが合わない: 最後に検査に通った設定に差し替え、合わない箇所を添える
    if settings_problems:
        lines = [
            f"{problem.file}: {problem.key or store.WHOLE_PATH}: {problem.detail}"
            for problem in settings_problems
        ]
        return collect_preview_data(
            replace(workspace, settings=cast("dict[str, Any]", last_settings)),
            built_at=now(),
            settings_problem=lines,
        )
    return collect_preview_data(workspace, built_at=now())


def escape_for_script(json_text: str) -> str:
    """JSON の文字列の `<`・`>`・`&` を、JSON の Unicode エスケープに置き換える。"""
    # `&` を先に置き換える（後の置き換えが作る文字を巻き込まない）
    return json_text.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")


def embed_data(template: str, data: dict[str, Any]) -> str:
    """雛形の `DATA_ELEMENT` の中身にデータの JSON を入れた HTML を返す。"""
    count = template.count(DATA_ELEMENT)
    # 同梱の雛形の誤り: 埋め込み先が 1 つだけでない
    if count != 1:
        raise ValueError(f"雛形に埋め込み先が 1 つだけありません（{count} 個）")
    json_text = escape_for_script(json.dumps(data, ensure_ascii=False))
    opened = DATA_ELEMENT.removesuffix(CLOSE_TAG)
    return template.replace(DATA_ELEMENT, f"{opened}{json_text}{CLOSE_TAG}")


def mdmark_dist_url(version: str | None, path: str) -> str:
    """設定の mdmark のバージョン（`latest` と `None` は develop）の、jsDelivr の `dist/{path}` の URL を返す。"""
    return CDN_REPO_URL.format(package=MDMARK_PACKAGE, version=_mdmark_ref(version), path=f"dist/{path}")


def _mdmark_ref(version: str | None) -> str:
    """設定の mdmark のバージョンから、jsDelivr の ref を決める。"""
    return MDMARK_LATEST_REF if version in (None, MDMARK_LATEST) else str(version)


def assemble_template(
    *, mdmark_settings: dict[str, Any] | None = None, preview_dir: Path = PREVIEW_DIR
) -> str:
    """`template.html` に CSS・JavaScript と、設定のバージョンの mdmark の読み込みを差し込んだ HTML を返す（`DATA_ELEMENT` は空のまま）。"""
    template = (preview_dir / TEMPLATE_FILE).read_text(encoding="utf-8")
    styles = [(name, (preview_dir / name).read_text(encoding="utf-8")) for name in STYLE_FILES]
    scripts = [(name, (preview_dir / name).read_text(encoding="utf-8")) for name in SCRIPT_FILES]
    # 同梱の雛形の誤り: 差し込む中身が、差し込み先の要素を閉じてしまう
    for files, close_tag in ((styles, STYLE_CLOSE_TAG), (scripts, CLOSE_TAG)):
        for name, text in files:
            if close_tag.removesuffix(">") in text.lower():
                raise ValueError(f"雛形の {name} が {close_tag.removesuffix('>')} を含みます")
    # 同梱の雛形の誤り: 差し込み口が 1 つだけでない
    for slot in (STYLE_SLOT, SCRIPT_SLOT, MDMARK_SLOT):
        count = template.count(slot)
        if count != 1:
            raise ValueError(f"雛形に差し込み口 {slot} が 1 つだけありません（{count} 個）")
    css = "\n".join(text for _, text in styles)
    js = "\n".join(text for _, text in scripts)
    template = template.replace(STYLE_SLOT, f'<style id="mindmap-style">{css}{STYLE_CLOSE_TAG}')
    template = template.replace(SCRIPT_SLOT, f'<script id="mindmap-app">{js}{CLOSE_TAG}')
    return template.replace(MDMARK_SLOT, _mdmark_loading(mdmark_settings or {}))


def _mdmark_loading(mdmark_settings: dict[str, Any]) -> str:
    """設定のバージョンの mdmark の CSS の `<link>` と、JavaScript の URL と `map` を持つ読み込みの設定の要素を返す。"""
    version = mdmark_settings.get("version")
    css_url = mdmark_dist_url(version, "index.css")
    config = {"js": mdmark_dist_url(version, "index.js"), "map": mdmark_settings.get("map") or {}}
    config_text = escape_for_script(json.dumps(config, ensure_ascii=False))
    return (
        f'<link rel="stylesheet" href="{css_url}" crossorigin="anonymous">'
        f"{MDMARK_CONFIG_OPEN}{config_text}{CLOSE_TAG}"
    )


def derive_preview_values(workspace: Workspace) -> dict[str, Any]:
    """概要と表に出す次の候補・ゴールまで・カテゴリー別の進み具合を、コマンドと同じ関数で計算する。"""
    next_candidates = [
        asdict(candidate) for candidate in list_next_candidates(workspace, limit=None)
    ]
    report = judge_goal(workspace)
    goal = asdict(report)
    # 判定に入れたフェーズごとの、決着した検討事項の数と全体の数
    goal["phase_progress"] = [_count_decisions(workspace, phase) for phase in report.phases]
    # カテゴリーごとに、フェーズの順のセルと合計を並べる
    progress = []
    for category in workspace.settings.get("categories", []):
        cells = [
            _count_decisions(workspace, phase, category=category["name"])
            for phase in workspace.settings.get("phases", [])
        ]
        progress.append(
            {
                "category": category["name"],
                "cells": cells,
                "settled": sum(cell["settled"] for cell in cells),
                "total": sum(cell["total"] for cell in cells),
            }
        )
    return {"next": next_candidates, "goal": goal, "progress": progress}


def _count_decisions(
    workspace: Workspace, phase: str, *, category: str | None = None
) -> dict[str, Any]:
    """フェーズ（と、あればカテゴリー）の検討事項のうち、決着した数と全体の数を返す。"""
    rows = [
        item
        for item in workspace.items["decision"]
        if item.get("phase") == phase and (category is None or item.get("category") == category)
    ]
    settled = sum(1 for item in rows if is_settled("decision", item))
    return {"phase": phase, "settled": settled, "total": len(rows)}


def validate_export_out(out: Path) -> Path:
    """`out` が `.html` で終わることを確かめ、`resolve()` した絶対パスにして返す。"""
    # 拡張子は大文字・小文字を区別しない
    if out.suffix.lower() != ".html":
        raise ArgumentError("out", f".html のファイルを指してください: {out}")
    return out.resolve()


def fetch_url(url: str, timeout: float = FETCH_TIMEOUT_SEC) -> bytes:
    """URL を GET して本文のバイト列を返す（取り直さない）。"""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            status = response.status
            body = response.read()
    except (OSError, http.client.HTTPException) as error:
        # 届かない・待ちの上限を超えた・200 以外が返った（HTTPError も OSError）
        reason = getattr(error, "reason", None) or error
        raise DownloadFailedError(f"取れませんでした: {url}（{reason}）") from error
    # 200 以外の成功（204 など）も、配布ファイルとして使えない
    if status != HTTPStatus.OK:
        raise DownloadFailedError(f"取れませんでした: {url}（HTTP {status}）")
    return body


class _ExternalScriptParser(HTMLParser):
    """外の読み込みの範囲の `<script src integrity>` を、並びの順に集める。"""

    def __init__(self) -> None:
        """集めた `src` と `integrity` の並びを空で持つ。"""
        super().__init__()
        # (src, integrity) の並び
        self.found: list[tuple[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """src を持つ script の開きタグの src と integrity を控える。"""
        if tag != "script":
            return
        values = dict(attrs)
        # src を持たない script（読み込みの設定など中身を持つもの）は外の読み込みの script ではない
        if values.get("src") is not None:
            self.found.append((values["src"] or "", values.get("integrity")))


def _external_range(template: str) -> str:
    """雛形の外の読み込みの印の間（印を含む）を返す。印が 1 つずつでないか順が逆なら ValueError にする。"""
    start = template.find(EXTERNAL_START)
    end = template.find(EXTERNAL_END)
    # 同梱の雛形の誤り: 印が 1 つずつでないか、順が逆
    if template.count(EXTERNAL_START) != 1 or template.count(EXTERNAL_END) != 1 or start > end:
        raise ValueError("雛形に外の読み込みの印が 1 つずつありません")
    return template[start:end]


def list_external_scripts(template: str) -> list[ExternalScript]:
    """雛形の外の読み込みの印の間の `<script src integrity>` を、並びの順に返す（`src` を持たない `<script>` と `<link>` は読まない）。"""
    parser = _ExternalScriptParser()
    parser.feed(_external_range(template))
    parser.close()
    scripts: list[ExternalScript] = []
    for src, integrity in parser.found:
        matched = _EXTERNAL_SRC.match(src)
        # 同梱の雛形の誤り: integrity が無いか、版を固定した jsDelivr の URL でない
        if integrity is None or matched is None:
            raise ValueError(
                f"雛形の外の読み込みが版を固定した jsDelivr の URL と integrity を持ちません: {src}"
            )
        scripts.append(
            ExternalScript(
                url=src,
                integrity=integrity,
                package=matched["package"],
                version=matched["version"],
            )
        )
    return scripts


def _fetch_checked(*, fetch: FetchFn, url: str, integrity: str) -> bytes:
    """URL の中身を取り、sha384 を Base64 にした `sha384-{値}` が integrity と同じことを確かめて返す。違えば DownloadFailedError にする。"""
    content = fetch(url)
    digest = base64.b64encode(hashlib.sha384(content).digest()).decode("ascii")
    if f"sha384-{digest}" != integrity:
        raise DownloadFailedError(f"integrity が合いません: {url}")
    return content


def _license_texts(
    *, library: VendorLibrary, base_url: str, version: str, preview_dir: Path, fetch: FetchFn
) -> tuple[str, str, str | None, str | None]:
    """ライブラリのライセンスの本文と束ねた依存のライセンスを、取るか雛形のフォルダから読んで返す（本文・本文の出どころ・束ねた依存・その出どころ）。

    出どころは、取ったなら URL、読んだなら雛形のフォルダからの相対パス（無害化の確かめのメッセージに使う）。
    """
    # ライセンスの本文: 取る（license_path）か、雛形のフォルダから読む（license_file）か
    if library.license_path is not None:
        license_source = base_url.format(package=library.package, version=version, path=library.license_path)
        license_text = fetch(license_source).decode("utf-8")
    else:
        license_source = library.license_file or ""
        license_text = (preview_dir / license_source).read_text(encoding="utf-8")
    # 束ねた依存のライセンス: 取る（bundled_license_path）か、雛形のフォルダから読む（bundled_license_file）か
    bundled_source: str | None
    if library.bundled_license_path is not None:
        bundled_source = base_url.format(package=library.package, version=version, path=library.bundled_license_path)
        bundled_text: str | None = fetch(bundled_source).decode("utf-8")
    elif library.bundled_license_file is not None:
        bundled_source = library.bundled_license_file
        bundled_text = (preview_dir / bundled_source).read_text(encoding="utf-8")
    else:
        bundled_source = None
        bundled_text = None
    return license_text, license_source, bundled_text, bundled_source


def assemble_standalone_template(
    *,
    preview_dir: Path = PREVIEW_DIR,
    libraries: tuple[VendorLibrary, ...] = VENDOR_LIBRARIES,
    fetch: FetchFn = fetch_url,
    mdmark_settings: dict[str, Any] | None = None,
) -> str:
    """`assemble_template` の外の読み込みを、取った mdmark の CSS・JavaScript・部品、描画のライブラリの `<script>` とライセンスの表示の要素に置き換える。"""
    settings = mdmark_settings or {}
    template = assemble_template(mdmark_settings=settings, preview_dir=preview_dir)
    scripts = list_external_scripts(template)
    # 取る前に、mdmark と外の読み込みごとのライセンスの表示の材料（VendorLibrary）を引く
    by_package = {library.package: library for library in libraries}
    for package in (MDMARK_PACKAGE, *(script.package for script in scripts)):
        if package not in by_package:
            raise ValueError(f"ライセンスの表示が無い外の読み込み: {package}")

    # mdmark は設定のバージョンの配布ファイルを取る（integrity は確かめない）
    version = settings.get("version")
    mdmark_files: list[tuple[str, str]] = []
    for name in ("index.css", "index.js", *MDMARK_PART_FILES):
        url = mdmark_dist_url(version, name)
        text = fetch(url).decode("utf-8")
        # 取った中身が script 要素を閉じる・開くタグ（CSS は style 要素を閉じるタグ）を含むと、埋め込んだ要素が壊れる
        _reject_tags(source=url, text=text, tags=_STYLE_TAGS if name.endswith(".css") else _SCRIPT_TAGS)
        mdmark_files.append((name, text))
    blocks: list[LicenseBlock] = []
    mdmark_ref = _mdmark_ref(version)
    license_text, license_source, bundled_text, bundled_source = _license_texts(
        library=by_package[MDMARK_PACKAGE],
        base_url=CDN_REPO_URL,
        version=mdmark_ref,
        preview_dir=preview_dir,
        fetch=fetch,
    )
    for source, text in ((license_source, license_text), (bundled_source, bundled_text)):
        _reject_tags(source=source, text=text, tags=_SCRIPT_TAGS)
    blocks.append(
        LicenseBlock(
            library=by_package[MDMARK_PACKAGE],
            version=mdmark_ref,
            license_text=license_text,
            bundled_text=bundled_text,
        )
    )

    script_elements: list[str] = []
    for script in scripts:
        library = by_package[script.package]
        dist_text = _fetch_checked(fetch=fetch, url=script.url, integrity=script.integrity).decode("utf-8")
        license_text, license_source, bundled_text, bundled_source = _license_texts(
            library=library,
            base_url=CDN_PACKAGE_URL,
            version=script.version,
            preview_dir=preview_dir,
            fetch=fetch,
        )
        for source, text in (
            (script.url, dist_text),
            (license_source, license_text),
            (bundled_source, bundled_text),
        ):
            _reject_tags(source=source, text=text, tags=_SCRIPT_TAGS)
        script_elements.append(f"<script>{dist_text}{CLOSE_TAG}")
        blocks.append(
            LicenseBlock(
                library=library,
                version=script.version,
                license_text=license_text,
                bundled_text=bundled_text,
            )
        )

    # 印から印まで（両方を含む。mdmark の `<link>` と読み込みの設定の要素も消える）を、取った中身とライセンスの表示に置き換える
    start = template.index(EXTERNAL_START)
    end = template.index(EXTERNAL_END) + len(EXTERNAL_END)
    contents = dict(mdmark_files)
    parts = "".join(
        f"{MDMARK_PART_OPEN.format(name=Path(name).stem)}{contents[name]}{CLOSE_TAG}"
        for name in MDMARK_PART_FILES
    )
    config_text = escape_for_script(json.dumps({"map": settings.get("map") or {}}, ensure_ascii=False))
    licenses = f"{LICENSES_OPEN}{format_licenses(blocks)}{CLOSE_TAG}"
    return (
        template[:start]
        + f"{MDMARK_CSS_OPEN}{contents['index.css']}{STYLE_CLOSE_TAG}"
        + f"{MDMARK_OPEN}{contents['index.js']}{CLOSE_TAG}"
        + parts
        + f"{MDMARK_CONFIG_OPEN}{config_text}{CLOSE_TAG}"
        + "".join(script_elements)
        + licenses
        + template[end:]
    )


def _reject_tags(*, source: str | None, text: str | None, tags: tuple[str, ...]) -> None:
    """text が tags のどれかを含むときは ValueError にする（大文字・小文字を区別しない）。"""
    if text is None:
        return
    lowered = text.lower()
    for tag in tags:
        if tag in lowered:
            raise ValueError(f"取った {source} が {tag} を含みます")


def format_licenses(blocks: list[LicenseBlock]) -> str:
    """ライブラリごとの名前・版・著作権・ライセンス・入手先・本文・束ねた依存のライセンスを並べた文字列を返す。"""
    texts: list[str] = []
    for block in blocks:
        library = block.library
        tag = library.tag.replace("{version}", block.version)
        lines = [
            f"{library.name} {block.version}",
            library.notice,
            f"License: {library.license}",
            f"Source: {library.repository}/tree/{tag}",
            "",
            block.license_text.rstrip("\n"),
        ]
        # 束ねた依存のライセンスを持つライブラリは、本文の後に見出しと一緒に続ける
        if block.bundled_text is not None:
            lines += [
                "",
                f"{library.name} が中に持つライブラリ",
                "",
                block.bundled_text.rstrip("\n"),
            ]
        texts.append("\n".join(lines))
    return "\n\n".join(texts)


def export_preview(
    workspace: Workspace,
    *,
    out: Path,
    built_at: str,
    preview_dir: Path = PREVIEW_DIR,
    fetch: FetchFn = fetch_url,
) -> Path:
    """検証してから、描画のライブラリとライセンスの表示を中に持つ雛形にデータを埋め込み、`out` を置き換える。"""
    # 問題があるときは取らず、書かない（前の out を残す）
    problems = store.validate_workspace(workspace)
    if problems:
        raise store.build_mismatch_error(problems, workspace)

    # 取れないときは DownloadFailedError がそのまま上がる（書かない）
    template = assemble_standalone_template(
        preview_dir=preview_dir, fetch=fetch, mdmark_settings=workspace.settings.get("mdmark") or {}
    )
    data = collect_preview_data(workspace, built_at=built_at)
    replace_file(out, embed_data(template, data))
    return out
