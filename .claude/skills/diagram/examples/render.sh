#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRAWIO="/Applications/draw.io.app/Contents/MacOS/draw.io"

if [ ! -x "$DRAWIO" ]; then
    echo "❌ draw.io 未装。运行: brew install --cask drawio"
    exit 1
fi

cd "$SCRIPT_DIR"
"$DRAWIO" --export --format png --width 3200 \
    --output minimal.png minimal.drawio

echo "✅ 渲染产物：$SCRIPT_DIR/minimal.png"
