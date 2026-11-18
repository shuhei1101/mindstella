#!/bin/sh
set -u

WEBHOOK_FILE=/home/shuhei2441/.config/web-hook/mindstella.ini
UNIT=mindstella.service
FAILED=0

if err=$(systemctl --user show-environment 2>&1 >/dev/null); then
  echo "systemd --user: ok"
else
  echo "systemd --user: failed"
  echo "systemctl --user show-environment"
  echo "$err"
  FAILED=1
fi

if err=$(systemctl --user cat "$UNIT" 2>&1 >/dev/null); then
  echo "常駐サーバーのユニット: ok"
else
  echo "常駐サーバーのユニット: failed"
  echo "systemctl --user cat $UNIT"
  echo "$err"
  FAILED=1
fi

# 中身（Webhook の URL）は出さない
if [ -r "$WEBHOOK_FILE" ] && head -n 1 "$WEBHOOK_FILE" | grep -Eq '^[[:space:]]*https?://'; then
  echo "Webhook の設定のファイル: ok"
else
  echo "Webhook の設定のファイル: failed"
  echo "$WEBHOOK_FILE が無いか、1 行目が http:// か https:// で始まらない"
  FAILED=1
fi

exit "$FAILED"
