#!/usr/bin/env bash
# 一键启用 .githooks/ · 把 git config core.hooksPath 指过去
#
# 用法:
#   bash scripts/install-hooks.sh
#
# 卸载:
#   git config --unset core.hooksPath
#
# 详见 docs/security/secrets-protection.md

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

if [[ ! -d .githooks ]]; then
    echo "[install-hooks] ERR · 当前目录没 .githooks/ · 是不是在仓库根目录?" >&2
    exit 1
fi

# 确保 hook 脚本可执行
chmod +x .githooks/* 2>/dev/null || true

git config core.hooksPath .githooks

current=$(git config --get core.hooksPath)
echo "[install-hooks] ok · core.hooksPath = $current"
echo "[install-hooks] 已启用的 hooks:"
ls -1 .githooks/ | sed 's/^/  - /'
echo ""
echo "如需关闭: git config --unset core.hooksPath"
echo "如需单次 bypass: git commit --no-verify"
