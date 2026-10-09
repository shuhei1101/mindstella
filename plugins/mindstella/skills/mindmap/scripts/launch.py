"""起動スクリプト（`bin/mindstella`）が呼ぶ、プラグインのフォルダ・セッションの名前・MCP の設定の手助け。

使い方（起動スクリプトが仮想環境の Python で起動し、`claude plugin list --json` の出力を標準入力へ渡す）:
  {python_path} launch.py --python {python_path} --folder {ワークスペースのフォルダ}
標準出力にプラグインのフォルダ・セッションの名前・MCP の設定のパスを 1 行ずつこの順で出す。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TextIO

# `claude plugin list --json` の要素の `id` で引く値
PLUGIN_ID = "mindstella@mindstella"

# プラグインのフォルダからの MCP サーバーの入口の相対パス
SERVER_SCRIPT = "skills/mindmap/scripts/server.py"

# MCP の設定の `env` に書く環境変数の名前（`serve.py` の同じ名前の定数と合わせる）
EXTERNAL_ENV_KEYS = (
    "MINDSTELLA_ALLOWED_HOSTS",
    "MINDSTELLA_PREVIEW_START_HOOK",
    "MINDSTELLA_PREVIEW_STOP_HOOK",
)

# tmux のセッションの名前の頭
SESSION_PREFIX = "mindstella-"

# セッションの名前に付ける、絶対パスの SHA-256 の 16 進の先頭の桁数
PATH_HASH_DIGITS = 6

# 標準エラーに出すエラーの行の頭
ERROR_PREFIX = "[mindstella] エラー: "

# プラグインがインストールされていないときに案内するコマンド
INSTALL_GUIDE = (
    "インストールするには: claude plugin marketplace add shuhei1101/mindstella"
    " && claude plugin install mindstella@mindstella"
)


class PluginNotInstalledError(Exception):
    """`claude plugin list --json` に `PLUGIN_ID` が無い。"""


def find_plugin_dir(listing: list[dict[str, Any]]) -> Path:
    """`claude plugin list --json` の一覧から、インストールした mindstella の今の版のフォルダを引く。"""
    for plugin in listing:
        if plugin.get("id") == PLUGIN_ID:
            return Path(plugin["installPath"])
    raise PluginNotInstalledError(f"プラグイン {PLUGIN_ID} がインストールされていません")


def session_name(folder: Path) -> str:
    """ワークスペースのフォルダから tmux のセッションの名前を作る。"""
    # シンボリックリンクを解いた絶対パスで、同じ名前の別の場所のフォルダを見分ける
    resolved = folder.resolve()
    digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:PATH_HASH_DIGITS]
    # tmux が名前の区切りに使う `.`・`:` は `-` にする
    name = resolved.name.replace(".", "-").replace(":", "-")
    return f"{SESSION_PREFIX}{name}-{digest}"


def external_env(environ: Mapping[str, str]) -> dict[str, str]:
    """`EXTERNAL_ENV_KEYS` のうち、空でない値が設定されているものだけを返す。"""
    return {key: environ[key] for key in EXTERNAL_ENV_KEYS if environ.get(key)}


def write_mcp_config(
    python_path: Path,
    plugin_dir: Path,
    *,
    temp_root: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    """この起動だけの MCP の設定を一時フォルダに書き、そのパスを返す。env が空でなければ MCP サーバーへ渡す環境変数にする。"""
    config_dir = Path(tempfile.mkdtemp(prefix=SESSION_PREFIX, dir=temp_root))
    server_config: dict[str, Any] = {
        "command": str(python_path),
        "args": [str(plugin_dir / SERVER_SCRIPT)],
    }
    if env:
        server_config["env"] = dict(env)
    config = {"mcpServers": {"mindstella": server_config}}
    path = config_dir / "mcp.json"
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def run_launch(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    """標準入力のプラグインの一覧から、3 つの値を作って標準出力に 1 行ずつ出す。"""
    parser = argparse.ArgumentParser(description="起動スクリプトの手助け")
    parser.add_argument("--python", type=Path, required=True, help="MCP サーバーを動かす Python")
    parser.add_argument("--folder", type=Path, required=True, help="ワークスペースのフォルダ")
    parser.add_argument("--format", choices=["lines"], default="lines", help="出力の形")
    args = parser.parse_args(argv)

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

    name = session_name(args.folder)
    config = write_mcp_config(
        args.python, plugin_dir, env=external_env(os.environ if environ is None else environ)
    )
    # 起動スクリプトが `read` で 1 行ずつ受ける
    print(plugin_dir)
    print(name)
    print(config)
    return 0


if __name__ == "__main__":
    sys.exit(run_launch())
