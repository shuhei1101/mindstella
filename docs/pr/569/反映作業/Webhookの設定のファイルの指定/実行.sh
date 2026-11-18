#!/bin/sh
set -eu

DROPIN_DIR=/home/shuhei2441/.config/systemd/user/mindstella.service.d
DROPIN="$DROPIN_DIR/discord-webhook.conf"
WEBHOOK_FILE=/home/shuhei2441/.config/web-hook/mindstella.ini
UNIT=mindstella.service
NEW=$(mktemp)
trap 'rm -f "$NEW"' EXIT

# 前提確認
if [ $# -gt 1 ] || { [ $# -eq 1 ] && [ "$1" != "--dry-run" ]; }; then
  echo "前提確認: failed"
  echo "受け付ける引数は無しか --dry-run だけ: $*"
  exit 1
fi
if ! err=$(systemctl --user cat "$UNIT" 2>&1 >/dev/null); then
  echo "前提確認: failed"
  echo "systemctl --user cat $UNIT"
  echo "$err"
  exit 1
fi
if [ ! -r "$WEBHOOK_FILE" ]; then
  echo "前提確認: failed"
  echo "$WEBHOOK_FILE が無い"
  exit 1
fi
echo "前提確認: ok"

# 計画（--dry-run もここを通る）
printf '[Service]\nEnvironment=MINDSTELLA_DISCORD_WEBHOOK_FILE=%s\n' "$WEBHOOK_FILE" > "$NEW"
if [ -f "$DROPIN" ] && cmp -s "$DROPIN" "$NEW"; then
  echo "drop-in の書き込み: skipped"
  echo "常駐サーバーの起動し直し: skipped"
  exit 0
fi
if [ -f "$DROPIN" ]; then
  diff -u --label "$DROPIN" --label "$DROPIN" "$DROPIN" "$NEW" || true
else
  diff -u --label /dev/null --label "$DROPIN" /dev/null "$NEW" || true
fi
if [ "${1:-}" = "--dry-run" ]; then
  echo "drop-in の書き込み: changed"
  echo "常駐サーバーの起動し直し: changed"
  exit 0
fi

# 適用（検証 → 退避 → 置き換え → 起動し直し）
if ! grep -qx "Environment=MINDSTELLA_DISCORD_WEBHOOK_FILE=$WEBHOOK_FILE" "$NEW"; then
  echo "検証: failed"
  exit 1
fi
echo "検証: ok"
mkdir -p "$DROPIN_DIR"
if [ -f "$DROPIN" ]; then
  cp -p "$DROPIN" "$DROPIN.bak"
fi
mv "$NEW" "$DROPIN"
echo "drop-in の書き込み: changed"
for cmd in "daemon-reload" "restart $UNIT"; do
  # shellcheck disable=SC2086
  if ! err=$(systemctl --user $cmd 2>&1); then
    echo "常駐サーバーの起動し直し: failed"
    echo "systemctl --user $cmd"
    echo "$err"
    exit 1
  fi
done
echo "常駐サーバーの起動し直し: changed"
