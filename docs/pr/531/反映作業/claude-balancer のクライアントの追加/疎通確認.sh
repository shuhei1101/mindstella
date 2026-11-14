#!/bin/sh
# claude-balancer の設定ファイル・待ち受け・tmux のバックエンドの window に、読み取りだけでつながるかを確かめる
set -eu

SETTINGS="$HOME/.config/claude-balancer/settings.yaml"
URL="http://127.0.0.1:8770"

if [ -r "$SETTINGS" ] && grep -q '^clients:' "$SETTINGS"; then
  echo "設定ファイル: ok"
else
  echo "設定ファイル: failed"
  echo "$ test -r $SETTINGS && grep -q '^clients:' $SETTINGS"
  exit 1
fi

if OUT=$(curl -sS --noproxy '*' --max-time 5 "$URL/clients" 2>&1); then
  echo "claude-balancer の GET /clients: ok"
else
  echo "claude-balancer の GET /clients: failed"
  echo "$ curl -sS $URL/clients"
  echo "$OUT"
  exit 1
fi

if tmux list-windows -t '=claude-balancer' -F '#{window_name}' 2>/dev/null | grep -qx backend; then
  echo "tmux の claude-balancer:backend: ok"
else
  echo "tmux の claude-balancer:backend: failed"
  echo "$ tmux list-windows -t =claude-balancer"
  exit 1
fi
