#!/bin/sh
set -eu

DROPIN=/home/shuhei2441/.config/systemd/user/mindstella.service.d/discord-webhook.conf
UNIT=mindstella.service

if [ -f "$DROPIN.bak" ]; then
  cp -p "$DROPIN.bak" "$DROPIN"
  echo "drop-in の書き戻し: changed"
elif [ -f "$DROPIN" ]; then
  rm -f "$DROPIN"
  echo "drop-in の削除: changed"
else
  echo "drop-in の削除: skipped"
  exit 0
fi
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
