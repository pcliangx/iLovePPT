#!/usr/bin/env bash
# Wrapper · 自动用 _rag/.venv 跑 search.py,agent 不用关心 Python 路径。
#
# 用法(同 search.py):
#   ${CLAUDE_PROJECT_DIR}/library/visual-patterns/search.sh --query "PDCA" --top-k 3 --format json
#
# 找不到 venv 时 fallback 到 system python3(可能会 ImportError,引导用户装 venv)。

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$SCRIPT_DIR/_rag/.venv/bin/python"

if [ -x "$VENV_PY" ]; then
    exec "$VENV_PY" "$SCRIPT_DIR/search.py" "$@"
else
    echo "WARN: _rag/.venv 不存在,fallback 到 system python3。若失败请按 README 装 venv:" >&2
    echo "  cd $SCRIPT_DIR/_rag && python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exec python3 "$SCRIPT_DIR/search.py" "$@"
fi
