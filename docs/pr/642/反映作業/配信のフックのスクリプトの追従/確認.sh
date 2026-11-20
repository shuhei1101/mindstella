#!/bin/sh
set -eu

TARGET="$HOME/.local/bin/mindstella-gw-hook"
if grep -q '"$#" -ne 4' "$TARGET" && grep -q -- '--path "$PAGE_PATH"' "$TARGET"; then
  echo "フックの引数と公開するパス: ok"
else
  echo "フックの引数と公開するパス: failed"
  grep -n 'ne [0-9]\|--path' "$TARGET" || true
  exit 1
fi
