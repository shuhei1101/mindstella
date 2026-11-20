#!/bin/sh
set -eu

TARGET="$HOME/.local/bin/mindstella-gw-hook"
LATEST=$(ls -1 "$TARGET".bak-* 2>/dev/null | sort | tail -n 1 || true)
if [ -z "$LATEST" ]; then
  echo "退避したファイル: failed"
  exit 1
fi
cp -p "$LATEST" "$TARGET"
echo "フックの書き戻し: changed"
