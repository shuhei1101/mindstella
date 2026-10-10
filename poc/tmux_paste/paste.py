"""サーバーの代わりに、受け継いだ TMUX・TMUX_PANE で Claude Code のペインへ文字列を貼って確定する。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# 貼り付けに使う tmux のバッファの名前
BUFFER_NAME = "mindstella-poc"


def paste(env_file: Path, text: str, enter_delay_ms: int) -> float:
    """文字列をブラケットペーストで貼り、待ってから Enter を送る。かかった秒を返す。"""
    inherited = json.loads(env_file.read_text(encoding="utf-8"))
    env = {**os.environ, "TMUX": inherited["TMUX"]}
    pane = inherited["TMUX_PANE"]
    started = time.monotonic()
    subprocess.run(
        ["tmux", "load-buffer", "-b", BUFFER_NAME, "-"],
        input=text.encode("utf-8"),
        env=env,
        check=True,
    )
    subprocess.run(
        ["tmux", "paste-buffer", "-p", "-d", "-b", BUFFER_NAME, "-t", pane], env=env, check=True
    )
    time.sleep(enter_delay_ms / 1000)
    subprocess.run(["tmux", "send-keys", "-t", pane, "Enter"], env=env, check=True)
    return time.monotonic() - started


def main() -> None:
    """引数: 環境のファイル・貼る文字列のファイル・Enter までの待ち（ミリ秒）。"""
    elapsed = paste(
        Path(sys.argv[1]), Path(sys.argv[2]).read_text(encoding="utf-8"), int(sys.argv[3])
    )
    print(f"{elapsed:.3f}")


if __name__ == "__main__":
    main()
