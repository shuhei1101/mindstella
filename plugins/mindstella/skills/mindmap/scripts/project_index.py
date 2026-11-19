"""project-index の端末の設定の API と読み取り API を呼ぶ。"""

from __future__ import annotations

import fnmatch
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from pathlib import Path
from collections.abc import Mapping
from typing import Any, Literal

import yaml

logger = logging.getLogger("mindstella.project_index")

# `PROJECT_INDEX_PORT` が無いときのポート
DEFAULT_PORT = 8786

# project-index への 1 回の HTTP を打ち切る秒数（配信元を読み直してから返すので、読み直しの時間を見込む）
REQUEST_TIMEOUT_SEC = 10.0

# 端末の設定の配信元の行の API
SOURCES_PATH = "/settings/sources"

# 版が古いときのステータス
CONFLICT = HTTPStatus.CONFLICT

# 同じ ID の行があるときの `result`
EXISTS_RESULT = "exists"

# 端末の設定のファイルで、許可するフォルダを持つキー
SETTINGS_KEY = "mindstella"
ALLOWED_DIRS_KEY = "allowed_dirs"

# scope のパスの後ろに付く、その下の全てに当たる glob
RECURSIVE_SUFFIX = "/**"

# 代理を通さずに 127.0.0.1 へつなぐ開き方
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class ProjectIndexError(Exception):
    """project-index へつながらない・想定していないステータスを返した。"""

    def __init__(self, status: int | None, detail: str) -> None:
        """ステータス（つながらないときは None）と理由を持つ。"""
        super().__init__(detail)
        self.status = status
        self.detail = detail


def get_settings(port: int) -> dict[str, Any]:
    """`GET /settings/sources` の応答（`settingsPath`・`sources[]`・`version`）を返す。"""
    status, body = _request(port, "GET", SOURCES_PATH)
    # 200 でない: 読めない
    if status != HTTPStatus.OK:
        raise _failed("GET", SOURCES_PATH, status, body)
    return body


def add_source(
    port: int, row: dict[str, Any]
) -> Literal["added", "exists_same", "exists_different"]:
    """今の版を引いて配信元の行を 1 行追加する。同じ ID の行があれば、内容が同じかを返す。版が古ければ 1 回だけ引き直して送り直す。"""
    status, body = _post_source(port, row)
    # 版が古い（同じ ID の行があるのではない 409）: 引き直して送り直す
    if status == CONFLICT and body.get("result") != EXISTS_RESULT:
        logger.warning("mindstella.project_index.version_conflict", extra={"source_id": row.get("id")})
        status, body = _post_source(port, row)
    # 追加した
    if status == HTTPStatus.CREATED:
        return "added"
    # 同じ ID の行がある: 内容が同じかで分ける
    if status == CONFLICT and body.get("result") == EXISTS_RESULT:
        return "exists_same" if body.get("same") else "exists_different"
    raise _failed("POST", SOURCES_PATH, status, body)


def _post_source(port: int, row: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """今の版を引き、`expectedVersion` を添えて行の追加を送る。"""
    version = get_settings(port).get("version")
    return _request(port, "POST", SOURCES_PATH, {"source": row, "expectedVersion": version})


def patch_source(port: int, source_id: str, changes: dict[str, Any]) -> None:
    """今の版を引いて行を変える。版が古ければ 1 回だけ引き直して送り直す。"""
    path = f"{SOURCES_PATH}/{urllib.parse.quote(source_id, safe='')}"
    for attempt in range(2):
        version = get_settings(port).get("version")
        status, body = _request(
            port, "PATCH", path, {"expectedVersion": version, "source": changes}
        )
        # 変えた
        if status == HTTPStatus.OK:
            return
        # 1 回目の版が古い: 引き直して送り直す
        if status == CONFLICT and attempt == 0:
            logger.warning(
                "mindstella.project_index.version_conflict", extra={"source_id": source_id}
            )
            continue
        raise _failed("PATCH", path, status, body)


def reload_sources(port: int) -> None:
    """端末の設定のファイルの行をそのまま `PUT /settings/sources` に送り、全ての配信元を再読み込みさせる。

    `GET /settings/sources` の応答の行は状態を含む camelCase の形で `PUT` の要求の行と違うので、
    行は応答ではなく `settingsPath` のファイルから読む。版が古ければ 1 回だけ引き直して送り直す。
    """
    for attempt in range(2):
        settings = get_settings(port)
        rows = read_source_rows(Path(str(settings.get("settingsPath"))))
        status, body = _request(
            port,
            "PUT",
            SOURCES_PATH,
            {"expectedVersion": settings.get("version"), "sources": rows},
        )
        # 読み直させた
        if status == HTTPStatus.OK:
            return
        # 1 回目の版が古い: 引き直して送り直す
        if status == CONFLICT and attempt == 0:
            logger.warning("mindstella.project_index.version_conflict", extra={"source_id": None})
            continue
        raise _failed("PUT", SOURCES_PATH, status, body)


def settings_file(environ: Mapping[str, str]) -> Path:
    """端末の設定のファイルの場所を、project-index と同じ環境変数の優先順で返す。"""
    # PROJECT_INDEX_CONFIG があれば、その場所を使う
    explicit = environ.get("PROJECT_INDEX_CONFIG")
    if explicit:
        return Path(explicit)
    # 無ければ XDG_CONFIG_HOME（未設定なら ~/.config）の下の project-index/settings.yaml
    config_home = environ.get("XDG_CONFIG_HOME") or str(
        Path(environ.get("HOME") or Path.home()) / ".config"
    )
    return Path(config_home) / "project-index" / "settings.yaml"


def read_source_rows(settings_path: Path) -> list[Any]:
    """端末の設定のファイルの `sources` の並びを返す。読めないか並びでなければ ProjectIndexError。"""
    try:
        data = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ProjectIndexError(
            None, f"端末の設定のファイルを読めません: {settings_path}（{error}）"
        ) from error
    rows = data.get("sources") if isinstance(data, dict) else None
    # sources が並びでない: 送らない
    if not isinstance(rows, list):
        raise ProjectIndexError(None, f"端末の設定のファイルの sources が並びではありません: {settings_path}")
    return rows


def find_doc_path(port: int, source: str, doc_id: str) -> str | None:
    """配信元の文書の一覧から、`doc_id` の文書のパスを返す。無ければ `None`。"""
    path = f"/sources/{urllib.parse.quote(source, safe='')}/docs"
    status, body = _request(port, "GET", path)
    if status != HTTPStatus.OK:
        raise _failed("GET", path, status, body)
    for doc in body.get("documents") or []:
        if isinstance(doc, dict) and doc.get("id") == doc_id:
            return str(doc.get("path"))
    return None


def doc_exists(port: int, source: str, path: str, doc_id: str) -> bool:
    """文書 1 件が 200 なら真、404 なら偽を返す。"""
    route = (
        f"/sources/{urllib.parse.quote(source, safe='')}/docs/{urllib.parse.quote(path)}"
        f"?{urllib.parse.urlencode({'id': doc_id})}"
    )
    status, body = _request(port, "GET", route)
    if status == HTTPStatus.OK:
        return True
    if status == HTTPStatus.NOT_FOUND:
        return False
    raise _failed("GET", route, status, body)


def scope_includes(patterns: list[str], folder: Path) -> bool:
    """`scope.read` の並び（パスか `/**` の付いた glob）に、フォルダが当たるかを返す。"""
    target = str(folder)
    for pattern in patterns:
        # その下の全て: パターンの頭のフォルダかその下
        if pattern.endswith(RECURSIVE_SUFFIX):
            base = pattern[: -len(RECURSIVE_SUFFIX)]
            if target == base or target.startswith(base + "/"):
                return True
        # glob の記号を持つ: そのまま照らす
        elif any(mark in pattern for mark in "*?["):
            if fnmatch.fnmatchcase(target, pattern):
                return True
        # ただのパス: そのフォルダだけ
        elif target == pattern:
            return True
    return False


def read_allowed_dirs(settings_path: Path) -> list[Path]:
    """端末の設定のファイルの `mindstella.allowed_dirs` を返す。キーもファイルも無ければ空の並び。"""
    try:
        text = settings_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    data = yaml.safe_load(text)
    section = data.get(SETTINGS_KEY) if isinstance(data, dict) else None
    values = section.get(ALLOWED_DIRS_KEY) if isinstance(section, dict) else None
    # キーが無いか並びでない: どのフォルダも許可しない
    if not isinstance(values, list):
        return []
    return [Path(str(value)).expanduser().resolve() for value in values]


def _request(
    port: int, method: str, path: str, body: dict[str, Any] | None = None
) -> tuple[int, dict[str, Any]]:
    """JSON を送り、ステータスと JSON の本文を返す。つながらなければ ProjectIndexError。"""
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with _OPENER.open(request, timeout=REQUEST_TIMEOUT_SEC) as response:
            return response.status, _parse(response.read())
    except urllib.error.HTTPError as error:
        # 200 番台でない応答: ステータスと本文を返す
        return error.code, _parse(error.read())
    except (urllib.error.URLError, OSError) as error:
        # つながらない・打ち切った
        reason = str(getattr(error, "reason", error))
        logger.warning(
            "mindstella.project_index.request_failed",
            extra={"method": method, "path": path, "status": None, "reason": reason},
        )
        raise ProjectIndexError(
            None, f"project-index へつながりません（ポート {port}）: {reason}"
        ) from error


def _parse(raw: bytes) -> dict[str, Any]:
    """本文を JSON のオブジェクトとして読む。読めなければ空のオブジェクト。"""
    try:
        value = json.loads(raw) if raw else {}
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _failed(method: str, path: str, status: int, body: dict[str, Any]) -> ProjectIndexError:
    """想定していないステータスの ProjectIndexError を作り、記録する。"""
    reason = str(body.get("detail") or body.get("title") or body)
    logger.warning(
        "mindstella.project_index.request_failed",
        extra={"method": method, "path": path, "status": status, "reason": reason},
    )
    return ProjectIndexError(
        status, f"project-index が {status} を返しました（{method} {path}）: {reason}"
    )
