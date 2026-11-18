#!/bin/sh
set -u

PYTHON="$HOME/.mindmap/venv/bin/python"
BEFORE="$HOME/.mindmap/venv-before-jinja2.txt"

if [ ! -f "$BEFORE" ]; then
  echo "入れる前の一覧: failed"
  echo "$BEFORE がありません"
  exit 1
fi
# 入れる前に無かったパッケージ（Jinja2 とその依存）だけを消す
added=$("$PYTHON" -m pip freeze | grep -v -i -x -F -f "$BEFORE" | sed 's/==.*//')
if [ -z "$added" ]; then
  echo "Jinja2 の削除: skipped"
  exit 0
fi
if ! out=$("$PYTHON" -m pip uninstall -y $added 2>&1); then
  echo "Jinja2 の削除: failed"
  echo "$PYTHON -m pip uninstall -y $added"
  echo "$out"
  exit 1
fi
echo "Jinja2 の削除: changed"
