#!/bin/sh
set -eu

if [ -f "$HOME/.local/bin/mindstella-gw-hook" ]; then
  echo "フックのスクリプト: ok"
else
  echo "フックのスクリプト: failed"
  ls -la "$HOME/.local/bin/" >&2 || true
  exit 1
fi
if [ -x "$HOME/.local/bin/gw" ]; then
  echo "gw: ok"
else
  echo "gw: failed"
  exit 1
fi

# 起動し直す常駐サーバーが、ワークスペースを /w/{workspace} で配る版のプラグインを指しているか（旧版なら新しいフックを 3 つの引数で呼び、公開が登録されない）
UNIT_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/mindstella.service"
SERVER_PY=$(sed -n 's/^ExecStart=[^ ]* \(.*server\.py\)$/\1/p' "$UNIT_FILE" 2>/dev/null || true)
SERVE_PY="$(dirname "$SERVER_PY")/serve.py"
if [ -n "$SERVER_PY" ] && grep -q '^PREVIEW_PREFIX = "/w"' "$SERVE_PY" 2>/dev/null; then
  echo "常駐サーバーのプラグインの版: ok"
else
  echo "常駐サーバーのプラグインの版: failed"
  echo "ユニット $UNIT_FILE が指す $SERVE_PY に PREVIEW_PREFIX が無い。プラグインを更新して mindstella server restart でユニットを書き直してから実行する" >&2
  exit 1
fi
