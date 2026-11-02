"""起動スクリプト（`bin/mindstella`）が呼ぶ、プラグインのフォルダ・セッションの名前の手助け。

使い方（起動スクリプトが仮想環境の Python で起動し、`claude plugin list --json` の出力を標準入力へ渡す）:
  {python_path} launch.py --folder {ワークスペースのフォルダ}
標準出力にプラグインのフォルダ・セッションの名前を 1 行ずつこの順で出す。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TextIO

# `claude plugin list --json` の要素の `id` で引く値
PLUGIN_ID = "mindstella@mindstella"

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


def session_name(folder: Path, *, config_dir: Path | None = None) -> str:
    """ワークスペースのフォルダと Claude Code の設定のフォルダ（アカウント）から tmux のセッションの名前を作る。"""
    # シンボリックリンクを解いた絶対パスで、同じ名前の別の場所のフォルダを見分ける
    resolved = folder.resolve()
    hashed = str(resolved)
    # 設定のフォルダがあれば改行を挟んでつなぎ、同じフォルダでもアカウントごとに別の名前にする
    if config_dir is not None:
        hashed += "\n" + str(config_dir.resolve())
    digest = hashlib.sha256(hashed.encode("utf-8")).hexdigest()[:PATH_HASH_DIGITS]
    # tmux が名前の区切りに使う `.`・`:` は `-` にする
    name = resolved.name.replace(".", "-").replace(":", "-")
    return f"{SESSION_PREFIX}{name}-{digest}"


def run_launch(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    """標準入力のプラグインの一覧から、プラグインのフォルダ・セッションの名前を作って標準出力に 1 行ずつ出す。"""
    parser = argparse.ArgumentParser(description="起動スクリプトの手助け")
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

    env = os.environ if environ is None else environ
    # CLAUDE_CONFIG_DIR が空でなければ、アカウントとしてセッションの名前に入れる
    config_dir = Path(env["CLAUDE_CONFIG_DIR"]) if env.get("CLAUDE_CONFIG_DIR") else None
    name = session_name(args.folder, config_dir=config_dir)
    # 起動スクリプトが `read` で 1 行ずつ受ける
    print(plugin_dir)
    print(name)
    return 0


if __name__ == "__main__":
    sys.exit(run_launch())
