#!/usr/bin/env bash
# 并行跑 text + image embed(不同表 text_emb / image_emb · 不冲突)
#
# P3-6 · WAL 后真正并发不冲突,可放心并跑
#   · journal_mode=WAL · 写不阻塞读 · 多 reader / 单 writer 并发
#   · busy_timeout=10000 · 元数据写(tpl_templates / tpl_pages)若撞锁等 10s 兜底
#   text_emb / image_emb 两表本就不冲突;元数据写有 busy_timeout 兜住 — 见 qwen_embedding.open_db
#
# 用法:
#   parallel_embed.sh                              # 两 kb 全跑
#   parallel_embed.sh pptx-templates               # 只 pptx-templates
#   parallel_embed.sh pptx-templates template_xyz  # 单模板
#
# 输出:
#   /tmp/embed_text.log
#   /tmp/embed_image.log
#   stdout 总结
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB="${SCRIPT_DIR}/../.."
VENV_PY="${LIB}/_rag/.venv/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
  echo "ERROR: venv python not found at $VENV_PY" >&2
  echo "  跑 cd library/_rag && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

KB="${1:-}"
ID="${2:-}"

# 注:set -u 下 ${ARR[@]} 空数组解引用要用 ${ARR[@]+"${ARR[@]}"} 兜底
EXTRA_ARGS=()
if [[ -n "$KB" ]]; then
  EXTRA_ARGS+=(--kb "$KB")
fi
if [[ -n "$ID" ]]; then
  EXTRA_ARGS+=(--id "$ID")
fi

TEXT_LOG=/tmp/embed_text.log
IMAGE_LOG=/tmp/embed_image.log

echo "[parallel_embed] starting · kb=${KB:-<all>} id=${ID:-<all>}"
echo "[parallel_embed] text log → $TEXT_LOG"
echo "[parallel_embed] image log → $IMAGE_LOG"

START=$(date +%s)

"$VENV_PY" "${LIB}/_rag/embed_text.py" ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"} > "$TEXT_LOG" 2>&1 &
TEXT_PID=$!

"$VENV_PY" "${LIB}/_rag/embed_image.py" ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"} > "$IMAGE_LOG" 2>&1 &
IMAGE_PID=$!

TEXT_OK=0
IMAGE_OK=0
wait $TEXT_PID && TEXT_OK=1 || true
wait $IMAGE_PID && IMAGE_OK=1 || true

END=$(date +%s)
ELAPSED=$((END - START))

echo ""
echo "=== text  $([[ $TEXT_OK = 1 ]] && echo OK || echo FAIL) ==="
tail -5 "$TEXT_LOG"
echo ""
echo "=== image $([[ $IMAGE_OK = 1 ]] && echo OK || echo FAIL) ==="
tail -5 "$IMAGE_LOG"
echo ""
echo "[parallel_embed] elapsed ${ELAPSED}s"

if [[ $TEXT_OK -ne 1 || $IMAGE_OK -ne 1 ]]; then
  echo "[parallel_embed] FAILED · 查日志 $TEXT_LOG / $IMAGE_LOG" >&2
  exit 1
fi
