# PPTX Templates Library

用户预置的 .pptx 模板知识库(按模板名分类)。被 brainstorm(列模板)、author(选页)、iloveppt-builder(Step 4 加视觉)调用。

## 目录结构

```
library/pptx-templates/
├── README.md  INDEX.md  ingest_workflow.md
├── items/<name>/
│   ├── meta.yaml                      ← 模板级 metadata(入 git)
│   ├── preview.png                    ← cover 缩略图(gitignored · `preview*.png` 规则)
│   └── pages/<NN-slug>/
│       ├── meta.yaml                  ← 页级 metadata(入 git)
│       └── preview.png                ← 该页渲染 PNG(gitignored · 单页 ~100-300KB)
└── _source/<name>.pptx                ← gitignored · build.py:load_theme() 读这里
```

> **注**:`.gitignore` line 17 `preview*.png` 当前忽略全部 preview;line 55 的注释意图是"入 git"但跟当前规则不一致。若要让 items/*/preview.png 入 git,需在 `.gitignore` 加一条 `!library/*/items/**/preview.png` 例外。

每个模板严格 1:1 对应一个 .pptx 源(放 `_source/<name>.pptx`)。

## 用法

```bash
# 列模板 + 按用户主题相关性排
library/search.sh --kb pptx-templates --type template --query "<主题>" --top-k 5

# 已选 template_golden, 找最适合"数据冲击"的页
library/search.sh --query "数据冲击" --preferred-template template_golden --type page
```

## load_theme 集成

`.claude/skills/pptx-deck/build.py:load_theme(name)` 第 4 位查找 `library/pptx-templates/_source/<name>.pptx`。

## ingest 流程

见 [`ingest_workflow.md`](ingest_workflow.md)。
