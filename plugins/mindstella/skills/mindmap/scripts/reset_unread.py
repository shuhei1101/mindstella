"""SessionStart のフックが呼ぶ。作業フォルダとその直下のワークスペースのスレッドの書き込みを未読へ戻す。

使い方（フックが標準入力に `cwd` を持つ JSON を渡す）:
  {仮想環境の Python} reset_unread.py
標準出力には何も書かず、いつも終了コード 0 で終える。飛ばした理由は標準エラーに書く。
"""

from __future__ import annotations

import fcntl
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from errors import MindmapError
from kinds import SETTINGS_FILE, records_root
from store import LOCK_FILE
from threads import reset_unread

# ワークスペースごとにロックを待つ秒数
LOCK_WAIT_SEC = 2.0

# 取れなかったロックを試し直す間隔の秒数
LOCK_POLL_SEC = 0.05


def find_workspaces(cwd: Path) -> list[Path]:
    """作業フォルダとその直下のフォルダのうち、ワークスペースを返す。"""
    # 作業フォルダがフォルダでない: 探すものが無い
    if not cwd.is_dir():
        return []
    candidates = [cwd]
    try:
        # 直下のフォルダ（シンボリックリンクを辿らず、`.` で始まる名前を除く）を名前の順に足す
        candidates += sorted(
            (
                child
                for child in cwd.iterdir()
                if not child.name.startswith(".") and child.is_dir() and not child.is_symlink()
            ),
            key=lambda child: child.name,
        )
    except OSError:
        # 直下を読めない: 作業フォルダだけを見る
        candidates = [cwd]
    return [path for path in candidates if (records_root(path) / SETTINGS_FILE).is_file()]


def reset_workspace(
    root: Path,
    *,
    wait_sec: float = LOCK_WAIT_SEC,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> str | None:
    """ワークスペースのロックを上限まで待って取り、書き込みを未読へ戻す。飛ばしたときは理由を返す。"""
    lock_path = records_root(root) / LOCK_FILE
    try:
        stream = lock_path.open("a", encoding="utf-8")
    except OSError as error:
        return f"ロックファイルを開けませんでした: {lock_path}（{error}）"
    with stream:
        started = clock()
        # 上限までロックを試し続ける
        while True:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                # 取れない: 上限を過ぎていれば飛ばし、そうでなければ待って試し直す
                if clock() - started >= wait_sec:
                    return f"ロックを取れませんでした: {lock_path}"
                sleep(LOCK_POLL_SEC)
        try:
            reset_unread(root)
        except MindmapError as error:
            # 読めない・書けない: 飛ばして理由を返す
            return "\n".join(error.lines) if error.lines else str(error)
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)
    return None


def main(stdin: TextIO = sys.stdin, stderr: TextIO = sys.stderr) -> int:
    """フックの標準入力の `cwd` から見つけたワークスペースを順に未読へ戻す。いつも 0 を返す。"""
    try:
        cwd = json.load(stdin)["cwd"]
        # `cwd` が文字列でない
        if not isinstance(cwd, str):
            raise TypeError("cwd が文字列ではありません")
    except (ValueError, KeyError, TypeError) as error:
        print(f"[mindstella] フックの入力を読めませんでした: {error!r}", file=stderr)
        return 0
    for root in find_workspaces(Path(cwd)):
        reason = reset_workspace(root)
        # 飛ばした: 理由を出して次へ進む
        if reason is not None:
            print(f"[mindstella] 未読へ戻せませんでした: {root}: {reason}", file=stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
