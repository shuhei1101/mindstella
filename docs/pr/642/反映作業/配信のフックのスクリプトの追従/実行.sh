#!/bin/sh
set -eu

TARGET="$HOME/.local/bin/mindstella-gw-hook"
SOURCE="$(dirname "$0")/新しいフック.sh"
NEW=$(mktemp)
trap 'rm -f "$NEW"' EXIT

# 前提確認
if [ $# -gt 1 ] || { [ $# -eq 1 ] && [ "$1" != "--dry-run" ]; }; then
  echo "前提確認: failed"
  exit 1
fi
if [ ! -f "$TARGET" ] || [ ! -f "$SOURCE" ]; then
  echo "前提確認: failed"
  ls -la "$TARGET" "$SOURCE" >&2 || true
  exit 1
fi
echo "前提確認: ok"

# 計画（--dry-run もここを通る）
cp "$SOURCE" "$NEW"
if cmp -s "$TARGET" "$NEW"; then
  echo "フックの書き換え: skipped"
  exit 0
fi
diff -u --label "$TARGET" --label "$TARGET" "$TARGET" "$NEW" || true
if [ "${1:-}" = "--dry-run" ]; then
  echo "フックの書き換え: changed"
  exit 0
fi

# 適用（検証 → 退避 → 置き換え）
if ! bash -n "$NEW" 2>/tmp/mindstella-gw-hook-check.err; then
  echo "検証: failed"
  echo "bash -n $NEW" >&2
  cat /tmp/mindstella-gw-hook-check.err >&2
  exit 1
fi
echo "検証: ok"
cp -p "$TARGET" "$TARGET.bak-$(date +%Y%m%d-%H%M%S)"
chmod 755 "$NEW"
mv "$NEW" "$TARGET"
echo "フックの書き換え: changed"
