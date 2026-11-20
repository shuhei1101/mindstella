#!/bin/sh
# 常駐サーバーを止める → 古い控えの公開を取り下げる → フックを置き換える → 常駐サーバーを起動する、の順で行う
set -eu

TARGET="$HOME/.local/bin/mindstella-gw-hook"
SOURCE="$(dirname "$0")/新しいフック.sh"
GW="$HOME/.local/bin/gw"
UNIT="mindstella.service"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/mindstella-gw-hook"
NEW=$(mktemp)
LISTING=$(mktemp)
trap 'rm -f "$NEW" "$LISTING"' EXIT

# 前提確認
if [ $# -gt 1 ] || { [ $# -eq 1 ] && [ "$1" != "--dry-run" ]; }; then
  echo "前提確認: failed"
  exit 1
fi
if [ ! -f "$TARGET" ] || [ ! -f "$SOURCE" ] || [ ! -x "$GW" ]; then
  echo "前提確認: failed"
  ls -la "$TARGET" "$SOURCE" "$GW" >&2 || true
  exit 1
fi
if ! "$GW" ls >"$LISTING" 2>&1; then
  echo "前提確認: failed"
  echo "$GW ls" >&2
  cat "$LISTING" >&2
  exit 1
fi
echo "前提確認: ok"

# 計画（--dry-run もここを通る）
cp "$SOURCE" "$NEW"
HOOK_CHANGED=1
if cmp -s "$TARGET" "$NEW"; then
  HOOK_CHANGED=0
else
  diff -u --label "$TARGET" --label "$TARGET" "$TARGET" "$NEW" || true
fi
# 古い控え: ポートの数字だけの名前のファイル（全てのワークスペースが同じポートになる前の控え）
OLD_FILES=$(find "$STATE_DIR" -maxdepth 1 -type f -regex '.*/[0-9]+' 2>/dev/null | sort || true)
for file in $OLD_FILES; do
  echo "古い控え: $file → $(cat "$file")"
done
if [ "$HOOK_CHANGED" -eq 0 ] && [ -z "$OLD_FILES" ]; then
  echo "フックの書き換え: skipped"
  exit 0
fi
if [ "${1:-}" = "--dry-run" ]; then
  echo "常駐サーバーの停止: changed"
  [ -n "$OLD_FILES" ] && echo "古い控えの取り下げ: changed"
  [ "$HOOK_CHANGED" -eq 1 ] && echo "フックの書き換え: changed"
  echo "常駐サーバーの起動: changed"
  exit 0
fi

# 適用
if ! bash -n "$NEW" 2>/tmp/mindstella-gw-hook-check.err; then
  echo "検証: failed"
  echo "bash -n $NEW" >&2
  cat /tmp/mindstella-gw-hook-check.err >&2
  exit 1
fi
echo "検証: ok"

# 1. 常駐サーバーを止める（動いている版のフックの呼び方で、配っている分を取り下げさせる）
if ! systemctl --user stop "$UNIT" 2>/tmp/mindstella-gw-hook-stop.err; then
  echo "常駐サーバーの停止: failed"
  echo "systemctl --user stop $UNIT" >&2
  cat /tmp/mindstella-gw-hook-stop.err >&2
  exit 1
fi
echo "常駐サーバーの停止: changed"

# 2. 残った古い控えの公開を取り下げる（gw の一覧にある名前だけを rm する。同じ名前を指す控えがあるため、毎回一覧を引き直す）
for file in $(find "$STATE_DIR" -maxdepth 1 -type f -regex '.*/[0-9]+' 2>/dev/null | sort || true); do
  name=$(cat "$file")
  "$GW" ls >"$LISTING" 2>&1 || true
  if [ -n "$name" ] && awk 'NR>1 {print $1}' "$LISTING" | grep -qx "$name"; then
    if ! "$GW" rm "$name" 2>/tmp/mindstella-gw-hook-rm.err; then
      echo "古い控えの取り下げ: failed"
      echo "$GW rm $name" >&2
      cat /tmp/mindstella-gw-hook-rm.err >&2
      exit 1
    fi
  fi
  rm -f "$file"
done
echo "古い控えの取り下げ: changed"

# 3. フックを置き換える（退避してから）
if [ "$HOOK_CHANGED" -eq 1 ]; then
  cp -p "$TARGET" "$TARGET.bak-$(date +%Y%m%d-%H%M%S)"
  chmod 755 "$NEW"
  mv "$NEW" "$TARGET"
  echo "フックの書き換え: changed"
else
  echo "フックの書き換え: skipped"
fi

# 4. 常駐サーバーを起動する（起動時に登録済みのワークスペースを配り始め、新しいフックで公開する）
if ! systemctl --user start "$UNIT" 2>/tmp/mindstella-gw-hook-start.err; then
  echo "常駐サーバーの起動: failed"
  echo "systemctl --user start $UNIT" >&2
  cat /tmp/mindstella-gw-hook-start.err >&2
  exit 1
fi
echo "常駐サーバーの起動: changed"
