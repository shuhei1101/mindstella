"""フックの結合テストの共通の関数（受け取った引数を記録するコマンドと、記録を待って読む関数）。"""

from __future__ import annotations

import shlex
import sys
import time
from pathlib import Path

# 記録を待つ上限秒数
HOOK_WAIT_SEC = 10

# 記録を読み直す間隔の秒数
HOOK_POLL_SEC = 0.05

# 記録が増えないことを確かめるために待つ秒数
HOOK_SETTLE_SEC = 0.5

# 受け取った引数（先頭の記録先を除く）を 1 行にして、記録先へ書き足す Python のコード
RECORD_CODE = (
    "import sys; "
    "open(sys.argv[1], 'a', encoding='utf-8').write(' '.join(sys.argv[2:]) + '\\n')"
)


def recording_hook(record: Path) -> str:
    """末尾に足された引数を 1 行ずつ record へ書き足すフックのコマンドを、環境変数に入れる形で返す。"""
    return " ".join(
        shlex.quote(part) for part in (sys.executable, "-c", RECORD_CODE, str(record))
    )


def read_hook_lines(record: Path, *, count: int = 1) -> list[str]:
    """record に count 行以上が書かれるのを待ち、書かれた行を返す。上限を過ぎても足りなければ今ある行を返す。"""
    deadline = time.monotonic() + HOOK_WAIT_SEC
    lines: list[str] = []
    while time.monotonic() < deadline:
        if record.exists():
            lines = record.read_text(encoding="utf-8").splitlines()
            if len(lines) >= count:
                break
        time.sleep(HOOK_POLL_SEC)
    return lines


def read_settled_hook_lines(record: Path, *, count: int = 1) -> list[str]:
    """count 行が書かれた後も少し待ち、増えていないことを含めた行を返す。"""
    read_hook_lines(record, count=count)
    time.sleep(HOOK_SETTLE_SEC)
    return record.read_text(encoding="utf-8").splitlines() if record.exists() else []
