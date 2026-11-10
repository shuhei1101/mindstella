#!/bin/sh
set -u
DIR=$(dirname "$0")

# 前提確認
if [ $# -gt 1 ] || { [ $# -eq 1 ] && [ "$1" != "--dry-run" ]; }; then
  echo "前提確認: failed"
  exit 1
fi
echo "前提確認: ok"

# 計画（--dry-run もここを通る）。既に v0.3.0 を含むなら何もしない
if python3 "$DIR/判定.py" "インストール済みのプラグイン" >/dev/null; then
  python3 "$DIR/判定.py" "インストール済みのプラグイン"
  echo "プラグインの取り直し: skipped"
  exit 0
fi
python3 "$DIR/判定.py" "インストール済みのプラグイン" || true
if [ "${1:-}" = "--dry-run" ]; then
  echo "プラグインの取り直し: changed"
  exit 0
fi

# 適用。取り直しは MCP update_plugins でしか行えないため、シェルからは止める
echo "プラグインの取り直し: failed（MCP update_plugins を呼んでから確認を流し直す）"
exit 1
