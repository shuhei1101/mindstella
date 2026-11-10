#!/bin/sh
set -u

if git -C /mnt/c/Users/shuhe/repo/ai-monitor rev-parse --verify -q v0.3.0 >/dev/null; then
  echo "配布元のクローンのタグ: ok"
else
  echo "配布元のクローンのタグ: failed"
  exit 1
fi
if ls "$HOME"/.claude*/plugins/installed_plugins.json >/dev/null 2>&1; then
  echo "インストール済みのプラグインの一覧: ok"
else
  echo "インストール済みのプラグインの一覧: failed"
  exit 1
fi
