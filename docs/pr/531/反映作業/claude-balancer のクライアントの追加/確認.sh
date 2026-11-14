#!/bin/sh
# claude-balancer の GET /clients に mindstella があるかを確かめる
set -eu

if curl -sS --noproxy '*' --max-time 5 http://127.0.0.1:8770/clients | grep -q '"mindstella"'; then
  echo "GET /clients の mindstella: ok"
else
  echo "GET /clients の mindstella: failed"
  echo "$ curl -sS http://127.0.0.1:8770/clients"
  exit 1
fi
