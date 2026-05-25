# Visual Patterns Library

跨模板复用的视觉模式知识库(timeline / pdca / funnel / cards / 等)。被 iloveppt-author / iloveppt-builder(Step 4 加视觉)在拓写时调用。

## 目录结构

```
library/visual-patterns/
├── README.md  INDEX.md  ingest_workflow.md
├── items/<id>/{meta.yaml, preview.png}        ← 资产 · 入 git
└── _source/<id>.<ext>                         ← gitignored · 1:N inspiration 归档
```

RAG 基础设施(venv / DB / 凭据)在 `library/_rag/`,跨 kb 共享。

## 用法

唯一检索入口是 `library/search.sh`,不要直接调本 kb 私有脚本(已无)。

```bash
# 查 PDCA 循环 pattern
library/search.sh --query "PDCA 循环" --kb visual-patterns --top-k 5
```

## ingest 流程

见 [`ingest_workflow.md`](ingest_workflow.md)。
