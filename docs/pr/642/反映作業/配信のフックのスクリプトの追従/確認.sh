#!/bin/sh
set -eu

TARGET="$HOME/.local/bin/mindstella-gw-hook"
GW="$HOME/.local/bin/gw"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/mindstella-gw-hook"
STATUS=0

if grep -q '"$#" -ne 4' "$TARGET" && grep -q -- '--path "$PAGE_PATH"' "$TARGET"; then
  echo "フックの引数と公開するパス: ok"
else
  echo "フックの引数と公開するパス: failed"
  grep -n 'ne [0-9]\|--path' "$TARGET" || true
  STATUS=1
fi

OLD_FILES=$(find "$STATE_DIR" -maxdepth 1 -type f -regex '.*/[0-9]+' 2>/dev/null || true)
if [ -z "$OLD_FILES" ]; then
  echo "古い控え: ok"
else
  echo "古い控え: failed"
  echo "$OLD_FILES"
  STATUS=1
fi

# 起動時の配り始めは daemon のスレッドで進むため、新しい公開が出るまで上限つきで取り直す（2 秒 × 15 回）
i=0
while :; do
  LISTING=$("$GW" ls 2>&1 || true)
  NEW_ROWS=$(printf '%s\n' "$LISTING" | grep 'Mindstella' | grep -c ' /w/' || true)
  OLD_ROWS=$(printf '%s\n' "$LISTING" | grep 'Mindstella' | grep -c ' /mindstella.html' || true)
  if [ "$NEW_ROWS" -gt 0 ] || [ "$i" -ge 15 ]; then
    break
  fi
  i=$((i + 1))
  sleep 2
done
if [ "$NEW_ROWS" -gt 0 ] && [ "$OLD_ROWS" -eq 0 ]; then
  echo "gw の公開（画面のパス /w/ の行 $NEW_ROWS 件、古いパスの行 0 件）: ok"
else
  echo "gw の公開（画面のパス /w/ の行 $NEW_ROWS 件、古いパスの行 $OLD_ROWS 件）: failed"
  printf '%s\n' "$LISTING" | grep 'Mindstella' || true
  STATUS=1
fi
exit "$STATUS"
