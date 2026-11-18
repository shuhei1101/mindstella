#!/bin/sh
set -u

PYTHON="$HOME/.mindmap/venv/bin/python"

if [ ! -x "$PYTHON" ]; then
  echo "仮想環境の Python: failed"
  echo "$PYTHON がありません"
  exit 1
fi
echo "仮想環境の Python: ok"

if ! out=$("$PYTHON" -m pip --version 2>&1); then
  echo "仮想環境の pip: failed"
  echo "$out"
  exit 1
fi
echo "仮想環境の pip: ok"

if ! out=$("$PYTHON" -m pip index versions Jinja2 2>&1); then
  echo "PyPI の Jinja2: failed"
  echo "$out"
  exit 1
fi
echo "PyPI の Jinja2: ok"
