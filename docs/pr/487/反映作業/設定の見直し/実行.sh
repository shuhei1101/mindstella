#!/bin/sh
set -u
DIR=$(dirname "$0")

# 前提確認
if [ $# -gt 1 ] || { [ $# -eq 1 ] && [ "$1" != "--dry-run" ]; }; then
  echo "前提確認: failed"
  exit 1
fi
echo "前提確認: ok"

# 計画（--dry-run もここを通る）。今の settings.yaml が読めるなら、増えたキーは既定値の settings で補われているため何もしない
if sh "$DIR/確認.sh"; then
  echo "設定の見直し: skipped"
  exit 0
fi
if [ "${1:-}" = "--dry-run" ]; then
  echo "設定の見直し: changed"
  exit 0
fi

# 適用。足すキーと値は誤りの内容で決まるため、シェルからは書き換えず止める
echo "設定の見直し: failed（誤りが指すキーを settings.yaml に足してから確認を流し直す）"
exit 1
