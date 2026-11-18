#!/bin/sh
set -u

WEBHOOK_FILE=/home/shuhei2441/.config/web-hook/mindstella.ini
UNIT=mindstella.service
STATUS_URL=http://127.0.0.1:8784/_admin/status
# 1 回の打ち切り 5 秒 × 6 回（常駐サーバーの準備を待つ上限 30 秒に合わせる）
TRIES=6
TIMEOUT=5

env_line=$(systemctl --user show "$UNIT" -p Environment 2>&1)
case "$env_line" in
  *"MINDSTELLA_DISCORD_WEBHOOK_FILE=$WEBHOOK_FILE"*)
    echo "常駐サーバーの環境変数: ok" ;;
  *)
    echo "常駐サーバーの環境変数: failed"
    echo "systemctl --user show $UNIT -p Environment"
    echo "$env_line" | sed 's/MINDSTELLA_DISCORD_WEBHOOK_FILE=[^ ]*/MINDSTELLA_DISCORD_WEBHOOK_FILE=…/'
    exit 1 ;;
esac

i=0
code=""
body=""
while [ "$i" -lt "$TRIES" ]; do
  i=$((i + 1))
  body=$(curl -sS -m "$TIMEOUT" -w '\n%{http_code}' "$STATUS_URL" 2>/tmp/mindstella-confirm-err.$$) || true
  code=$(printf '%s' "$body" | tail -n 1)
  body=$(printf '%s' "$body" | sed '$d')
  if [ "$code" = "200" ] && [ -n "$body" ]; then
    echo "常駐サーバーの待ち受け: ok"
    rm -f /tmp/mindstella-confirm-err.$$
    exit 0
  fi
  sleep "$TIMEOUT"
done
echo "常駐サーバーの待ち受け: failed"
echo "curl -sS -m $TIMEOUT $STATUS_URL"
echo "HTTP の状態: ${code:-なし}"
printf '%s\n' "$body" | head -c 200
cat /tmp/mindstella-confirm-err.$$ 2>/dev/null
rm -f /tmp/mindstella-confirm-err.$$
exit 1
