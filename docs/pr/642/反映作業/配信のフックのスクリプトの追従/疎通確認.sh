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
