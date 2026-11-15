"""起動のコマンド（`bin/mindstella`）が呼ぶ、プラグインのフォルダの検索と MindStella の API の呼び出しの手助け。

使い方（起動のコマンドが仮想環境の Python で起動する）:
# `claude plugin list --json` の出力を標準入力へ渡し、インストールした今の版のフォルダを 1 行出す
{python_path} launch.py --find-plugin
# ワークスペースと MindStella のセッションを作り、画面の URL とつなぐペインを 1 行ずつ出す
{python_path} launch.py --start {ワークスペースのフォルダ} [--flow {配信元の ID}#{文書の ID}] [--mcp-config {ファイル}] [--plugin-dir {フォルダ}]...
# 常駐サーバーの状態を出す
{python_path} launch.py --server-status
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from http import HTTPStatus
from pathlib import Path
from typing import Any, TextIO

# `claude plugin list --json` の要素の `id` で引く値
PLUGIN_ID = "mindstella@mindstella"

# 標準エラーに出す行の頭
MESSAGE_PREFIX = "[mindstella] "
ERROR_PREFIX = "[mindstella] エラー: "

# プラグインがインストールされていないときに案内するコマンド
INSTALL_GUIDE = (
    "インストールするには: claude plugin marketplace add shuhei1101/mindstella"
    " && claude plugin install mindstella@mindstella"
)

# MINDSTELLA_PORT が無いときのポート
DEFAULT_PORT = 8784

# MindStella のセッションの準備を待つ上限（常駐サーバーの既定）に足す秒数
REQUEST_MARGIN_SEC = 10.0

# MindStella のセッションの準備を待つ上限の既定の秒数
READY_TIMEOUT_SEC = 30.0

# 常駐サーバーの状態の経路
STATUS_PATH = "/_admin/status"

# 状態の GET を打ち切る秒数
STATUS_TIMEOUT_SEC = 2.0

# 代理を通さずに 127.0.0.1 へつなぐ開き方
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

# MindStella の API を呼ぶ関数の型（ポート・メソッド・パス・本文・打ち切りの秒数）
Request = Callable[..., tuple[int, dict[str, Any]]]


class PluginNotInstalledError(Exception):
    """`claude plugin list --json` に `PLUGIN_ID` が無い。"""


def find_plugin_dir(listing: list[dict[str, Any]]) -> Path:
    """`claude plugin list --json` の一覧から、インストールした mindstella の今の版のフォルダを引く。"""
    for plugin in listing:
        if plugin.get("id") == PLUGIN_ID:
            return Path(plugin["installPath"])
    raise PluginNotInstalledError(f"プラグイン {PLUGIN_ID} がインストールされていません")


def api_request(
    port: int,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    timeout: float = STATUS_TIMEOUT_SEC,
) -> tuple[int, dict[str, Any]]:
    """`http://127.0.0.1:{port}{path}` へ JSON を送り、ステータスと JSON の本文を返す（パスの ASCII でない文字は百分率で符号化する）。"""
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{urllib.parse.quote(path, safe='/?=&%')}",
        data=None if body is None else json.dumps(body).encode("utf-8"),
        method=method,
        headers={"Content-Type": "application/json", "Host": f"127.0.0.1:{port}"},
    )
    try:
        with _OPENER.open(request, timeout=timeout) as response:
            return response.status, _parse(response.read())
    except urllib.error.HTTPError as error:
        # 200 番台でない応答: problem+json の本文を返す
        return error.code, _parse(error.read())


def run_start(
    argv: list[str],
    *,
    environ: Mapping[str, str],
    stdout: TextIO,
    stderr: TextIO,
    request: Request = api_request,
) -> int:
    """ワークスペースと MindStella のセッションを作り、画面の URL とつなぐペインを 1 行ずつ出す。"""
    parser = argparse.ArgumentParser(
        prog="mindstella", description="ワークスペースで MindStella のセッションを起動する"
    )
    parser.add_argument("folder", help="ワークスペースのフォルダ")
    parser.add_argument("--flow", help="進め方の文書（{配信元の ID}#{文書の ID}）")
    parser.add_argument("--mcp-config", help="追加の MCP の定義の JSON のファイル")
    parser.add_argument(
        "--plugin-dir", action="append", default=[], help="追加のプラグインのフォルダ（何度でも）"
    )
    args = parser.parse_args(argv)
    port = int(environ.get("MINDSTELLA_PORT") or DEFAULT_PORT)
    timeout = READY_TIMEOUT_SEC + REQUEST_MARGIN_SEC

    try:
        body = _workspace_body(args)
    except (OSError, ValueError) as error:
        print(f"{ERROR_PREFIX}{error}", file=stderr)
        return 1
    try:
        status, created = request(port, "POST", "/workspaces", body, timeout)
        # ワークスペースを作れない: 理由を出す
        if status not in (HTTPStatus.OK, HTTPStatus.CREATED):
            print(f"{ERROR_PREFIX}{created.get('detail') or created}", file=stderr)
            return 1
        workspace_id = str(created["id"])
        url = str(created.get("url") or "")
        print(f"{MESSAGE_PREFIX}ワークスペース: {workspace_id}", file=stderr)
        config_dir = environ.get("CLAUDE_CONFIG_DIR") or None
        session_body = {
            "claude_config_dir": str(Path(config_dir).absolute()) if config_dir else None
        }
        path = f"/workspaces/{workspace_id}/sessions"
        status, session = request(port, "POST", path, session_body, timeout)
    except OSError as error:
        print(f"{ERROR_PREFIX}常駐サーバーへつながりません（ポート {port}）: {error}", file=stderr)
        return 1
    # 既にある: そのペインへつなぐ
    if status == HTTPStatus.CONFLICT and session.get("stage") == "exists":
        print(
            f"{MESSAGE_PREFIX}既にある MindStella のセッションへつなぎます: {session.get('session')}",
            file=stderr,
        )
    # 作れない: 理由と画面の URL を出す
    elif status != HTTPStatus.CREATED:
        print(f"{ERROR_PREFIX}{session.get('detail') or session}", file=stderr)
        print(f"画面: {url}", file=stderr)
        return 1
    else:
        print(f"{MESSAGE_PREFIX}MindStella のセッション: {session.get('session')}", file=stderr)
    print(url, file=stdout)
    print(session.get("pane"), file=stdout)
    return 0


def run_server_status(
    environ: Mapping[str, str], stdout: TextIO, *, request: Request = api_request
) -> int:
    """常駐サーバーの状態（ポート・バージョン・プラグインのフォルダ・配信）を出す。待ち受けていなければ 1。"""
    port = int(environ.get("MINDSTELLA_PORT") or DEFAULT_PORT)
    try:
        status, body = request(port, "GET", STATUS_PATH, None, STATUS_TIMEOUT_SEC)
    except OSError as error:
        print(
            f"{ERROR_PREFIX}常駐サーバーが待ち受けていません（ポート {port}）: {error}",
            file=sys.stderr,
        )
        return 1
    if status != HTTPStatus.OK:
        print(
            f"{ERROR_PREFIX}常駐サーバーの状態を読めません（ポート {port}・ステータス {status}）",
            file=sys.stderr,
        )
        return 1
    print(f"ポート: {body.get('port', port)}", file=stdout)
    print(f"バージョン: {body.get('version')}", file=stdout)
    print(f"プラグインのフォルダ: {body.get('plugin_root')}", file=stdout)
    previews = body.get("previews") or []
    print(f"配信: {len(previews)} 件", file=stdout)
    for preview in previews:
        if isinstance(preview, dict):
            print(f"  {preview.get('workspace')} ポート {preview.get('port')}", file=stdout)
    return 0


def run_launch(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    """--find-plugin・--start・--server-status のどれかを実行する。"""
    raw = sys.argv[1:] if argv is None else argv
    env = os.environ if environ is None else environ
    # 先頭の引数で動きを分ける（--start の残りは run_start が読む）
    if raw[:1] == ["--start"]:
        return run_start(raw[1:], environ=env, stdout=sys.stdout, stderr=sys.stderr)
    if raw[:1] == ["--server-status"]:
        return run_server_status(env, sys.stdout)
    parser = argparse.ArgumentParser(description="起動のコマンドの手助け")
    parser.add_argument(
        "--find-plugin",
        action="store_true",
        required=True,
        help="インストールした今の版のフォルダを出す",
    )
    parser.parse_args(raw)

    source = sys.stdin if stdin is None else stdin
    try:
        listing = json.loads(source.read())
    except ValueError:
        listing = None
    # 読めないか、配列でない
    if not isinstance(listing, list):
        print(f"{ERROR_PREFIX}claude plugin list --json の出力を読めません", file=sys.stderr)
        return 1
    try:
        plugin_dir = find_plugin_dir(listing)
    except PluginNotInstalledError as error:
        # プラグインが無い: 案内を出して、何も書かない
        print(f"{ERROR_PREFIX}{error}", file=sys.stderr)
        print(INSTALL_GUIDE, file=sys.stderr)
        return 1
    print(plugin_dir)
    return 0


def _workspace_body(args: argparse.Namespace) -> dict[str, Any]:
    """引数から『ワークスペースの作成』の本文を作る。"""
    body: dict[str, Any] = {
        "folder": str(Path(args.folder).expanduser().absolute()),
        "plugin_dirs": [str(Path(value).expanduser().absolute()) for value in args.plugin_dir],
    }
    if args.flow is not None:
        source, separator, doc = args.flow.partition("#")
        if not separator or not source or not doc:
            raise ValueError(f"--flow は {{配信元の ID}}#{{文書の ID}} にしてください: {args.flow}")
        body["flow"] = {"source": source, "doc": doc}
    if args.mcp_config is not None:
        body["mcp_config"] = json.loads(
            Path(args.mcp_config).expanduser().read_text(encoding="utf-8")
        )
    return body


def _parse(raw: bytes) -> dict[str, Any]:
    """本文を JSON のオブジェクトとして読む。読めなければ空のオブジェクト。"""
    try:
        value = json.loads(raw) if raw else {}
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


if __name__ == "__main__":
    sys.exit(run_launch())
