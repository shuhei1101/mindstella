"""claude-balancer の設定の clients に mindstella を足し、変わったときだけバックエンドを止めて監視役に起動し直させる。

使い方:
# 変わる差分と結果の行だけを出す
python3 -B 実行.py --dry-run
# 適用する
python3 -B 実行.py
"""

from __future__ import annotations

import difflib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

# 書き換える設定ファイル
SETTINGS = Path.home() / ".config" / "claude-balancer" / "settings.yaml"

# 差分の見出しに出す設定ファイルの場所（ホームのフォルダを出さない）
SETTINGS_LABEL = "~/.config/claude-balancer/settings.yaml"

# 足すクライアントの名前
CLIENT = "mindstella"

# claude-balancer の待ち受け
URL = "http://127.0.0.1:8770"

# 止めると監視役が起動し直すバックエンドの window
BACKEND_WINDOW = "=claude-balancer:backend"

# 起動し直しを待つ上限の秒数（監視役の確認の間隔 15 秒の 4 回分）
RESTART_WAIT_SEC = 60.0

# 待つ間に確かめる間隔の秒数
POLL_SEC = 2.0

# 設定を YAML として検証する Python（PyYAML を持つ mindstella の仮想環境）
VALIDATOR = Path.home() / ".mindmap" / "venv" / "bin" / "python"


def main() -> int:
    """前提確認 → 計画 → 適用の順に進め、手順ごとの結果を 1 行ずつ出す。"""
    args = sys.argv[1:]
    # 前提確認: 引数は無しか --dry-run だけ、設定ファイルに clients の並びがある
    if args not in ([], ["--dry-run"]) or not SETTINGS.is_file():
        print("前提確認: failed")
        print(f"引数: {args} / 設定ファイル: {SETTINGS_LABEL}")
        return 1
    text = SETTINGS.read_text(encoding="utf-8")
    planned = plan(text)
    if planned is None:
        print("前提確認: failed")
        print("clients: の並びが見つかりません")
        return 1
    print("前提確認: ok")

    # 計画（--dry-run もここを通る）
    if planned == text:
        print("clients への追加: skipped")
        return 0
    sys.stdout.writelines(
        difflib.unified_diff(
            text.splitlines(keepends=True), planned.splitlines(keepends=True), SETTINGS_LABEL, SETTINGS_LABEL
        )
    )
    if args == ["--dry-run"]:
        print("clients への追加: changed")
        print("バックエンドの起動し直し: changed")
        return 0

    # 適用（一時ファイル → 検証 → 退避 → 置き換え）
    handle, temp = tempfile.mkstemp(dir=SETTINGS.parent, prefix=".settings.", suffix=".yaml")
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        stream.write(planned)
    check = subprocess.run(
        [str(VALIDATOR), "-c", "import sys, yaml; d = yaml.safe_load(open(sys.argv[1])); assert sys.argv[2] in d['clients']", temp, CLIENT],
        capture_output=True,
        text=True,
        check=False,
    )
    if check.returncode != 0:
        Path(temp).unlink(missing_ok=True)
        print("検証: failed")
        print(check.stderr)
        return 1
    print("検証: ok")
    shutil.copy2(SETTINGS, SETTINGS.with_name(f"settings.yaml.bak-{time.strftime('%Y%m%d-%H%M%S')}"))
    os.replace(temp, SETTINGS)
    print("clients への追加: changed")

    # 起動し直し: バックエンドを止め、監視役が新しい設定で起動し直すのを待つ
    stop = subprocess.run(["tmux", "send-keys", "-t", BACKEND_WINDOW, "C-c"], capture_output=True, text=True, check=False)
    if stop.returncode != 0:
        print("バックエンドの起動し直し: failed")
        print(f"$ tmux send-keys -t {BACKEND_WINDOW} C-c")
        print(stop.stderr)
        return 1
    deadline = time.monotonic() + RESTART_WAIT_SEC
    while time.monotonic() < deadline:
        time.sleep(POLL_SEC)
        if CLIENT in read_clients():
            print("バックエンドの起動し直し: changed")
            return 0
    print("バックエンドの起動し直し: failed")
    print(f"{RESTART_WAIT_SEC:g} 秒以内に GET {URL}/clients に {CLIENT} が入りませんでした")
    return 1


def plan(text: str) -> str | None:
    """clients の並びの末尾に CLIENT を足した設定を返す。既にあればそのまま、並びが無ければ None。"""
    lines = text.splitlines(keepends=True)
    try:
        start = next(index for index, line in enumerate(lines) if line.rstrip() == "clients:")
    except StopIteration:
        return None
    end = start + 1
    items: list[str] = []
    while end < len(lines) and lines[end].lstrip().startswith("- "):
        items.append(lines[end].strip()[2:].strip())
        end += 1
    if not items:
        return None
    if CLIENT in items:
        return text
    indent = lines[start + 1][: len(lines[start + 1]) - len(lines[start + 1].lstrip())]
    return "".join([*lines[:end], f"{indent}- {CLIENT}\n", *lines[end:]])


def read_clients() -> list[str]:
    """GET /clients の clients を返す。読めなければ空の並び。"""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"{URL}/clients", timeout=5) as response:
            return list(json.loads(response.read()).get("clients") or [])
    except (OSError, ValueError):
        return []


if __name__ == "__main__":
    sys.exit(main())
