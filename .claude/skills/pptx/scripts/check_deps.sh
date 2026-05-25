#!/usr/bin/env bash
# 一键探测 pptx skill 依赖

set -e
echo "== iLovePPT pptx skill 依赖检查 =="

check_py() {
    if python3 -c "import $1" 2>/dev/null; then
        echo "  ✅ python -m $1"
    else
        echo "  ❌ python -m $1  → pip3 install $2"
    fi
}

check_bin() {
    if command -v "$1" >/dev/null 2>&1; then
        echo "  ✅ $1"
    else
        echo "  ❌ $1  → $2"
    fi
}

check_py pptx python-pptx
check_py lxml lxml
check_py markitdown "'markitdown[pptx]'"
check_py PIL Pillow

check_bin soffice "brew install --cask libreoffice"
check_bin pdftoppm "brew install poppler"

# 字体检查（macOS）
if [[ "$(uname)" == "Darwin" ]]; then
    if fc-list 2>/dev/null | grep -qi "microsoft yahei"; then
        echo "  ✅ 微软雅黑"
    else
        echo "  ⚠️  微软雅黑未装（LibreOffice 渲染中文会 fallback）"
        echo "      手动方案：放雅黑字体到 ~/Library/Fonts/，或接受 fallback"
    fi
fi

echo "完成。"
