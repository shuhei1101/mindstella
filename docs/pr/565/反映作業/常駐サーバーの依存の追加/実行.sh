#!/bin/sh
set -u

PYTHON="$HOME/.mindmap/venv/bin/python"
REQUIREMENT="Jinja2>=3.1"
# 入れる前の一覧（切り戻しで、この実行が入れたものだけを消すために使う）
BEFORE="$HOME/.mindmap/venv-before-jinja2.txt"

# 前提確認
if [ $# -gt 1 ] || { [ $# -eq 1 ] && [ "$1" != "--dry-run" ]; }; then
  echo "前提確認: failed"
  echo "受け付ける引数は --dry-run だけです: $*"
  exit 1
fi
if [ ! -x "$PYTHON" ]; then
  echo "前提確認: failed"
  echo "$PYTHON がありません"
  exit 1
fi
echo "前提確認: ok"

# 計画（--dry-run もここを通る）
if "$PYTHON" -c "import sys, importlib.metadata as m; v = tuple(int(x) for x in m.version('Jinja2').split('.')[:2]); sys.exit(0 if v >= (3, 1) else 1)" 2>/dev/null; then
  echo "Jinja2 の導入: skipped"
  exit 0
fi
if ! out=$("$PYTHON" -m pip install --dry-run "$REQUIREMENT" 2>&1); then
  echo "計画: failed"
  echo "$PYTHON -m pip install --dry-run $REQUIREMENT"
  echo "$out"
  exit 1
fi
echo "$out" | grep "^Would install"
if [ "${1:-}" = "--dry-run" ]; then
  echo "Jinja2 の導入: changed"
  exit 0
fi

# 適用（退避 → 導入）
"$PYTHON" -m pip freeze > "$BEFORE"
if ! out=$("$PYTHON" -m pip install "$REQUIREMENT" 2>&1); then
  echo "Jinja2 の導入: failed"
  echo "$PYTHON -m pip install $REQUIREMENT"
  echo "$out"
  exit 1
fi
echo "Jinja2 の導入: changed"
