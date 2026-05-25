#!/usr/bin/env bash
# 批量跑 evals/plans/*.json → build + render → 出 scorecard 模板
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLANS_DIR="$ROOT/evals/plans"
OUT_DIR="$ROOT/evals/_run"
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

SCORECARD="$OUT_DIR/scorecard.md"
echo "# Eval Scorecard（待 Claude 按 rubric.md 填）" > "$SCORECARD"
echo "" >> "$SCORECARD"

if [ ! -d "$PLANS_DIR" ] || [ -z "$(ls -A "$PLANS_DIR"/*.json 2>/dev/null)" ]; then
    echo "无 eval plan（evals/plans/*.json 为空）。先做 Task 6。"
    exit 0
fi

for plan in "$PLANS_DIR"/*.json; do
    name="$(basename "$plan" .json)"
    echo "== $name =="
    if python3 "$ROOT/.claude/skills/pptx-deck/build.py" "$plan"; then
        echo "## $name" >> "$SCORECARD"
        echo "渲染图见 evals/plans/${name}_render/。逐页按 rubric.md 记录 fail 项号：" >> "$SCORECARD"
        echo "" >> "$SCORECARD"
    else
        echo "  构建失败"
        echo "## $name —— 构建失败" >> "$SCORECARD"
        echo "" >> "$SCORECARD"
    fi
done

echo ""
echo "完成。scorecard 模板：$SCORECARD"
echo "下一步：Claude 用 Read 看各 *_render/page-*.jpg,按 rubric.md 填 scorecard。"
