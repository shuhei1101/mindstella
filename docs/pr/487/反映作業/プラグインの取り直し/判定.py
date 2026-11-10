"""インストール済みの ai-monitor プラグインが、AI Monitor v0.3.0 の内容を含むかを判定して 1 行出す。"""

import json
import subprocess
import sys
from pathlib import Path

# 配布元のクローンと、判定の基準のタグ
SOURCE = "/mnt/c/Users/shuhe/repo/ai-monitor"
TAG = "v0.3.0"
STEP = sys.argv[1]


def main() -> int:
    # 1. タグの親（develop 側と release 側）を引く
    parents = subprocess.run(
        ["git", "-C", SOURCE, "rev-list", "--parents", "-n1", TAG],
        capture_output=True, text=True, check=True,
    ).stdout.split()[1:]
    # 2. 全ての Claude Code の設定の、インストール済みの ai-monitor の commit を引く
    shas = []
    for path in Path.home().glob(".claude*/plugins/installed_plugins.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("plugins", {}).get("ai-monitor@ai-monitor", []):
            shas.append(entry.get("gitCommitSha", ""))
    shas = sorted(set(shas))
    if not shas:
        print(f"{STEP}: failed（インストール済みの ai-monitor が無い）")
        return 1
    # 3. 全ての commit がタグの親を全て含むかを判定する
    missing = [
        sha[:12] for sha in shas
        if any(
            subprocess.run(["git", "-C", SOURCE, "merge-base", "--is-ancestor", p, sha]).returncode != 0
            for p in parents
        )
    ]
    if missing:
        print(f"{STEP}: failed（{TAG} を含まない commit: {', '.join(missing)}）")
        return 1
    print(f"{STEP}: ok（{', '.join(s[:12] for s in shas)} は {TAG} を含む）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
