#!/bin/sh
set -u

if ! out=$(python3 plugins/mindstella/skills/mindmap/scripts/check_env.py 2>&1); then
  echo "依存の確認: failed"
  echo "$out"
  exit 1
fi
if ! echo "$out" | python3 -c "import json, sys; p = {x['name']: x for x in json.load(sys.stdin)['packages']}; print(p['Jinja2']); sys.exit(0 if p['Jinja2']['ok'] else 1)"; then
  echo "Jinja2: failed"
  exit 1
fi
echo "Jinja2: ok"
