"""ワークスペースの記録を 1 つの JSON にまとめ、書き出し用のビルドに差し込んで配る書き出しを書く。"""

from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, replace
from http import HTTPStatus
from pathlib import Path
from typing import Any, cast

import store
from errors import ArgumentError, DownloadFailedError
from graph import list_ready
from history import load_changes, load_item_history, merge_item_history
from html_body import mark_lines
from kinds import KINDS, SETTINGS_FILE
from mdmark_ref import MDMARK_REPO, resolve_ref
from presets import preset_counts
from store import NowFn, Workspace, now_utc

# このファイルから見た `skills/mindmap/preview/`
PREVIEW_DIR = Path(__file__).resolve().parent.parent / "preview"

# プレビューのフォルダからの相対パス。React の画面の JS・CSS を中に持つ 1 枚の HTML
EXPORT_HTML_FILE = "export/index.html"

# プレビューのフォルダからの相対パス。描画のライブラリごとの package・version・url・integrity・global を並べた JSON の配列
LIBRARIES_FILE = "libraries.json"

# プレビューのフォルダからの相対パス。書き出し用のビルドのときに生成し、ライセンスの表示の最後に続ける
FRONTEND_LICENSES_FILE = "export/licenses.md"

# 配る書き出しに置く、記録の JSON を中身に持つ要素の開きタグ（閉じタグは `</script>`）
DATA_OPEN = '<script type="application/json" id="mindmap-data">'

# 書き出し用のビルドの HTML から外す、Google Fonts の `<link>`
FONT_LINK = re.compile(r"<link[^>]*fonts\.(?:googleapis|gstatic)\.com[^>]*>\s*")

# 書き出し用のビルドの HTML の最後のこのタグの前に差し込む（ビルドの JavaScript が文字列の `</body>` を持つため最後のものを使う）
BODY_CLOSE = "</body>"

# 差し込む要素を閉じるタグ
CLOSE_TAG = "</script>"
STYLE_CLOSE_TAG = "</style>"

# jsDelivr への 1 回の要求で、接続と 1 回の読み取りをそれぞれ待つ秒数
FETCH_TIMEOUT_SEC = 30

# 1 つの URL への要求の回数の上限（1 回目 + 取り直し）
FETCH_ATTEMPTS = 3

# 取り直しの間隔の上限の基準（秒）。n 回目の後は 0〜基準 × 2^(n-1) 秒の乱数
FETCH_BACKOFF_BASE_SEC = 1.0

# 応答の Retry-After に従って待つ秒数の上限
FETCH_RETRY_AFTER_MAX_SEC = 10.0

# 取り直す HTTP の状態コード（ほかに 5xx も取り直す）
FETCH_RETRY_STATUSES = frozenset({HTTPStatus.FORBIDDEN, HTTPStatus.REQUEST_TIMEOUT, HTTPStatus.TOO_MANY_REQUESTS})

# サーバーのエラー（5xx）の範囲の上端（この値は含まない）
SERVER_ERROR_STATUS_END = 600

# jsDelivr の、版を固定したパッケージの中のファイルの URL の形（ライセンスの本文を取るのに使う）
CDN_PACKAGE_URL = "https://cdn.jsdelivr.net/npm/{package}@{version}/{path}"

# jsDelivr の、タグを固定した GitHub のリポジトリの中のファイルの URL の形（mdmark の配布物と同梱物のライセンスを取るのに使う）
CDN_REPO_URL = "https://cdn.jsdelivr.net/gh/{package}@{version}/{path}"

# 配る書き出しに置く、ライセンスの表示を中身に持つ要素の開きタグ（画面には出ない）
LICENSES_OPEN = '<script type="text/plain" id="mindmap-licenses">'

# 配る書き出しに置く、mdmark の JavaScript を中身に持つ要素の開きタグ（閉じタグは `</script>`）。画面の JavaScript が中身から Blob の URL を作って `import()` する
MDMARK_OPEN = '<script type="text/plain" id="mindmap-mdmark">'

# 配る書き出しに置く、mdmark の CSS を中身に持つ要素の開きタグ（閉じタグは `</style>`）。画面の JavaScript が資料の HTML のエクスポートでこの中身を使う
MDMARK_CSS_OPEN = '<style id="mindmap-mdmark-css">'

# `CDN_REPO_URL` の `package` に入れる mdmark のリポジトリ
MDMARK_PACKAGE = MDMARK_REPO

# `dist/index.js` が隣から `import()` する部品の配布ファイル
MDMARK_PART_FILES = ("map.js", "view.js", "comments.js")

# 配る書き出しに置く、mdmark の部品を中身に持つ要素の開きタグ（`{name}` に部品の名前）
MDMARK_PART_OPEN = '<script type="text/plain" id="mindmap-mdmark-{name}">'

# 差し込む中身が、script 要素を閉じる・開くタグを含むかを見る文字列（小文字で比べる）
_SCRIPT_TAGS = ("</script", "<script")

# 差し込む CSS が、style 要素を閉じるタグを含むかを見る文字列（小文字で比べる）
_STYLE_TAGS = ("</style",)


@dataclass(frozen=True, slots=True, kw_only=True)
class VendorLibrary:
    """描画のライブラリ 1 つの、ライセンスの表示に使う値。"""

    # libraries.json の package と mdmark のリポジトリと結ぶ（npm はパッケージ名、GitHub は `{owner}/{repo}`）
    package: str
    # 表示する名前
    name: str
    # 著作権の表示
    notice: str
    # 配るときのライセンスの名前（選べるライセンスを持つときは選んだもの）
    license: str
    # パッケージの中のライセンスの本文のファイル。取らずに `license_file` から読むライブラリは None
    license_path: str | None
    # ライセンスの本文を取らずに読む、プレビューのフォルダからの相対パス。`license_path` が None のライブラリだけが持つ
    license_file: str | None
    # 配布物が中に束ねた依存のライセンスを並べた、パッケージの中のファイル（取る）。`bundled_license_file` と両方は持たない。無ければ None
    bundled_license_path: str | None
    # 配布ファイルが中に束ねた依存のライセンスを並べたファイル（プレビューのフォルダからの相対パス）。無ければ None
    bundled_license_file: str | None
    # ソースコードのリポジトリの URL
    repository: str
    # 版のタグの形（`{version}` に外の読み込みの版を入れる）
    tag: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ExternalScript:
    """libraries.json の描画のライブラリ 1 つ。"""

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


# 配る書き出しに入れるライブラリ（`package` で mdmark と libraries.json の行と結ぶ。版・URL・integrity は設定と libraries.json が持つ）
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
    workspace: Workspace,
    *,
    built_at: str,
    mdmark_ref: str,
    settings_problem: list[str] | None = None,
) -> dict[str, Any]:
    """設定・7 種類・本文・まとまり・画面に出す値・プリセットの件数・読んだ日時・設定の問題・mdmark の ref を 1 つの辞書にまとめる（送信は含めない）。"""
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
    # プリセットごとの該当する項目の件数（保存せずそのつど数える）
    data["preset_counts"] = preset_counts(workspace)
    data["built_at"] = built_at
    # config.yaml がスキーマに合わないときの、合わない箇所の行（合うときと配る書き出しは null）
    data["settings_problem"] = settings_problem
    # 画面が読み込む mdmark の ref（設定の mdmark のバージョンを解決したもの）
    data["mdmark_ref"] = mdmark_ref
    return data


def read_records(
    root: Path,
    *,
    last_settings: dict[str, Any] | None = None,
    now: NowFn = now_utc,
    resolve: Callable[[str | None], str] = resolve_ref,
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
        settings = cast("dict[str, Any]", last_settings)
        return collect_preview_data(
            replace(workspace, settings=settings),
            built_at=now(),
            mdmark_ref=resolve(_mdmark_version(settings)),
            settings_problem=lines,
        )
    return collect_preview_data(
        workspace, built_at=now(), mdmark_ref=resolve(_mdmark_version(workspace.settings))
    )


def _mdmark_version(settings: dict[str, Any]) -> str | None:
    """設定の `mdmark.version` を返す（無ければ None）。"""
    mdmark_settings = settings.get("mdmark") or {}
    version = mdmark_settings.get("version")
    return version if isinstance(version, str) else None


def escape_for_script(json_text: str) -> str:
    """JSON の文字列の `<`・`>`・`&` を、JSON の Unicode エスケープに置き換える。"""
    # `&` を先に置き換える（後の置き換えが作る文字を巻き込まない）
    return json_text.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")


def mdmark_dist_url(ref: str, path: str) -> str:
    """解決した mdmark の ref の、jsDelivr の `dist/{path}` の URL を返す。"""
    return CDN_REPO_URL.format(package=MDMARK_PACKAGE, version=ref, path=f"dist/{path}")


def derive_preview_values(workspace: Workspace) -> dict[str, Any]:
    """表に出す着手できる検討事項を、記録の取得の `derived` にして返す。"""
    return {"ready": list_ready(workspace)}


def validate_export_out(out: Path) -> Path:
    """`out` が `.html` で終わることを確かめ、`resolve()` した絶対パスにして返す。"""
    # 拡張子は大文字・小文字を区別しない
    if out.suffix.lower() != ".html":
        raise ArgumentError("out", f".html のファイルを指してください: {out}")
    return out.resolve()


def _retry_after(error: urllib.error.HTTPError) -> float | None:
    """応答の Retry-After（秒）を `FETCH_RETRY_AFTER_MAX_SEC` を上限に返す。無いか秒で読めなければ None。"""
    value = error.headers.get("Retry-After") if error.headers is not None else None
    if value is None or not value.strip().isdigit():
        return None
    return min(float(value.strip()), FETCH_RETRY_AFTER_MAX_SEC)


def _is_retryable_status(status: int) -> bool:
    """一時的な失敗として取り直す状態コードか（403・408・429・5xx）。"""
    return status in FETCH_RETRY_STATUSES or HTTPStatus.INTERNAL_SERVER_ERROR <= status < SERVER_ERROR_STATUS_END


def fetch_url(url: str, timeout: float = FETCH_TIMEOUT_SEC) -> bytes:
    """URL を GET し、一時的な失敗は取り直して本文のバイト列を返す。"""
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        wait: float | None = None
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                status = response.status
                body = response.read()
        except urllib.error.HTTPError as error:
            # 200 以外が返った（HTTPError は URLError の子なので先に分ける）
            reason: object = f"HTTP {error.code}"
            if not _is_retryable_status(error.code):
                raise DownloadFailedError(f"取れませんでした: {url}（{reason}）") from error
            wait = _retry_after(error)
            last_error: BaseException = error
        except (OSError, http.client.HTTPException) as error:
            # 届かない・待ちの上限を超えた
            reason = getattr(error, "reason", None) or error
            last_error = error
        else:
            # 200 以外の成功（204 など）も、配布ファイルとして使えない
            if status != HTTPStatus.OK:
                raise DownloadFailedError(f"取れませんでした: {url}（HTTP {status}）")
            return body
        if attempt == FETCH_ATTEMPTS:
            raise DownloadFailedError(f"取れませんでした: {url}（{reason}）") from last_error
        # 間を空けて取り直す（Retry-After が無ければ指数バックオフ + full jitter）
        time.sleep(wait if wait is not None else random.uniform(0, FETCH_BACKOFF_BASE_SEC * 2 ** (attempt - 1)))
    raise AssertionError("unreachable")


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
    """ライブラリのライセンスの本文と束ねた依存のライセンスを、取るかプレビューのフォルダから読んで返す（本文・本文の出どころ・束ねた依存・その出どころ）。

    出どころは、取ったなら URL、読んだならプレビューのフォルダからの相対パス（無害化の確かめのメッセージに使う）。
    """
    # ライセンスの本文: 取る（license_path）か、プレビューのフォルダから読む（license_file）か
    if library.license_path is not None:
        license_source = base_url.format(package=library.package, version=version, path=library.license_path)
        license_text = fetch(license_source).decode("utf-8")
    else:
        license_source = library.license_file or ""
        license_text = (preview_dir / license_source).read_text(encoding="utf-8")
    # 束ねた依存のライセンス: 取る（bundled_license_path）か、プレビューのフォルダから読む（bundled_license_file）か
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


def load_libraries(*, preview_dir: Path = PREVIEW_DIR) -> list[ExternalScript]:
    """`LIBRARIES_FILE` を読み、並びの順に `ExternalScript` にして返す。"""
    path = preview_dir / LIBRARIES_FILE
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"描画のライブラリの一覧が読めません: {error}") from error
    # 同梱の一覧の誤り: 配列でない
    if not isinstance(rows, list):
        raise ValueError("描画のライブラリの一覧が読めません: 配列ではありません")
    scripts: list[ExternalScript] = []
    for row in cast("list[Any]", rows):
        values = {key: row.get(key) if isinstance(row, dict) else None for key in ("package", "version", "url", "integrity")}
        missing = [key for key, value in values.items() if not isinstance(value, str)]
        # 同梱の一覧の誤り: 必要なキーが無い
        if missing:
            raise ValueError(f"描画のライブラリの一覧が読めません: {', '.join(missing)} がありません（{row}）")
        prefix = CDN_PACKAGE_URL.format(package=values["package"], version=values["version"], path="")
        # 同梱の一覧の誤り: バージョンを固定した jsDelivr の URL でない
        if not values["url"].startswith(prefix):
            raise ValueError(f"描画のライブラリの一覧が読めません: バージョンを固定した URL ではありません（{values['url']}）")
        scripts.append(ExternalScript(**values))
    return scripts


def assemble_export_html(
    data: dict[str, Any],
    *,
    preview_dir: Path = PREVIEW_DIR,
    libraries: tuple[VendorLibrary, ...] = VENDOR_LIBRARIES,
    fetch: FetchFn = fetch_url,
    mdmark_ref: str,
) -> str:
    """書き出し用のビルドに、取った mdmark・描画のライブラリ・記録・ライセンスの表示を差し込んだ HTML を返す。"""
    html = FONT_LINK.sub("", (preview_dir / EXPORT_HTML_FILE).read_text(encoding="utf-8"))
    position = html.rfind(BODY_CLOSE)
    # 同梱のビルドの誤り: 差し込む位置が無い
    if position < 0:
        raise ValueError("書き出し用のビルドに </body> がありません")
    scripts = load_libraries(preview_dir=preview_dir)
    # 取る前に、mdmark とライブラリごとのライセンスの表示の材料（VendorLibrary）を引く
    by_package = {library.package: library for library in libraries}
    for package in (MDMARK_PACKAGE, *(script.package for script in scripts)):
        if package not in by_package:
            raise ValueError(f"ライセンスの表示が無い描画のライブラリ: {package}")

    # mdmark は解決した ref の配布ファイルを取る（integrity は確かめない）
    mdmark_files: dict[str, str] = {}
    for name in ("index.css", "index.js", *MDMARK_PART_FILES):
        url = mdmark_dist_url(mdmark_ref, name)
        text = fetch(url).decode("utf-8")
        # 取った中身が script 要素を閉じる・開くタグ（CSS は style 要素を閉じるタグ）を含むと、埋め込んだ要素が壊れる
        _reject_tags(source=url, text=text, tags=_STYLE_TAGS if name.endswith(".css") else _SCRIPT_TAGS)
        mdmark_files[name] = text
    blocks = [_license_block(by_package[MDMARK_PACKAGE], CDN_REPO_URL, mdmark_ref, preview_dir, fetch)]

    script_elements: list[str] = []
    for script in scripts:
        dist_text = _fetch_checked(fetch=fetch, url=script.url, integrity=script.integrity).decode("utf-8")
        _reject_tags(source=script.url, text=dist_text, tags=_SCRIPT_TAGS)
        script_elements.append(f"<script>{dist_text}{CLOSE_TAG}")
        blocks.append(_license_block(by_package[script.package], CDN_PACKAGE_URL, script.version, preview_dir, fetch))

    frontend_licenses = (preview_dir / FRONTEND_LICENSES_FILE).read_text(encoding="utf-8")
    _reject_tags(source=FRONTEND_LICENSES_FILE, text=frontend_licenses, tags=_SCRIPT_TAGS)
    licenses = (
        f"{format_licenses(blocks)}\n\nReact の画面が中に持つライブラリ\n\n{frontend_licenses.rstrip()}\n"
    )
    parts = "".join(
        f"{MDMARK_PART_OPEN.format(name=Path(name).stem)}{mdmark_files[name]}{CLOSE_TAG}"
        for name in MDMARK_PART_FILES
    )
    json_text = escape_for_script(json.dumps(data, ensure_ascii=False))
    inserted = (
        f"{MDMARK_CSS_OPEN}{mdmark_files['index.css']}{STYLE_CLOSE_TAG}"
        f"{MDMARK_OPEN}{mdmark_files['index.js']}{CLOSE_TAG}"
        f"{parts}"
        + "".join(script_elements)
        + f"{DATA_OPEN}{json_text}{CLOSE_TAG}"
        f"{LICENSES_OPEN}{licenses}{CLOSE_TAG}"
    )
    return html[:position] + inserted + html[position:]


def _license_block(
    library: VendorLibrary, base_url: str, version: str, preview_dir: Path, fetch: FetchFn
) -> LicenseBlock:
    """ライブラリのライセンスの本文と束ねた依存のライセンスを取るか読み、タグを含まないことを確かめて返す。"""
    license_text, license_source, bundled_text, bundled_source = _license_texts(
        library=library, base_url=base_url, version=version, preview_dir=preview_dir, fetch=fetch
    )
    for source, text in ((license_source, license_text), (bundled_source, bundled_text)):
        _reject_tags(source=source, text=text, tags=_SCRIPT_TAGS)
    return LicenseBlock(library=library, version=version, license_text=license_text, bundled_text=bundled_text)


def export_preview(
    workspace: Workspace,
    *,
    out: Path,
    built_at: str,
    preview_dir: Path = PREVIEW_DIR,
    fetch: FetchFn = fetch_url,
    resolve: Callable[[str | None], str] = resolve_ref,
) -> Path:
    """検証してから、書き出し用のビルドに描画のライブラリ・ライセンスの表示・記録を差し込み、`out` を置き換える。"""
    # 問題があるときは取らず、書かない（前の out を残す）
    problems = store.validate_workspace(workspace)
    if problems:
        raise store.build_mismatch_error(problems, workspace)

    # 取れないときは DownloadFailedError がそのまま上がる（書かない）
    ref = resolve(_mdmark_version(workspace.settings))
    data = collect_preview_data(workspace, built_at=built_at, mdmark_ref=ref)
    html = assemble_export_html(data, preview_dir=preview_dir, fetch=fetch, mdmark_ref=ref)
    replace_file(out, html)
    return out
