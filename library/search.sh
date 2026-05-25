#!/usr/bin/env bash
# library/search.sh · 顶层检索 router wrapper(自动用 _rag/.venv)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="${SCRIPT_DIR}/_rag/.venv/bin/python"

if [ ! -x "${VENV_PY}" ]; then
    echo "ERROR: venv 未建。先跑:" >&2
    echo "  cd ${SCRIPT_DIR}/_rag && python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi

exec "${VENV_PY}" "${SCRIPT_DIR}/search.py" "$@"
