#!/bin/sh
set -u

# 稼働中のモニターと同じ develop のコードで settings.yaml を読み、読み込みの誤りが出ないかを観測する
OUT=$(cd /mnt/c/Users/shuhe/repo/ai-monitor/.claude/worktrees/develop && PYTHONPATH=src timeout 120 uv run python -c "from ai_monitor.shared.settings import Settings; s = Settings(); print(len(s.projects))" 2>&1)
STATUS=$?
if [ $STATUS -eq 0 ]; then
  echo "settings.yaml の読み込み: ok（プロジェクト $(echo "$OUT" | tail -1) 件）"
else
  echo "settings.yaml の読み込み: failed"
  echo "$OUT" | tail -5
  exit 1
fi
