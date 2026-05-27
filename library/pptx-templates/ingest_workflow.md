# PPTX Templates Ingest Workflow

用户:"把 template_X.pptx 入库"。流程 1:1(一份 .pptx → 一个模板 + N 个页 items)。

由 `iloveppt-template-extractor` agent 主导,主线程 dispatch。

## 模式

| mode | 用途 | step 范围 |
|---|---|---|
| `full` | 默认 · 完整 ingest 新模板 | 0-5 全跑 |
| `placeholder_map_only` | 回填工程 · 给已 ingest 模板补 placeholder_map.yaml.draft | Step 0 / 3.0 / 3.1.5 / 3.3 / 5 |
| `dry_run` | 看模板有几页 · 不写任何 draft | Step 0-2.5 + return preview |
| `re_render_only` | 只重渲染 PNG · 保留 meta(LibreOffice 升级 / dpi 调整) | Step 0-2.5,skip Step 3 |

## 步骤

**关键脚本**:
- `library/pptx-templates/scripts/inspect_placeholders.py` —— Step 3.1.5 产 placeholder_map.yaml.draft 骨架
- `library/pptx-templates/scripts/extractor_self_check.py` —— Step 3.3 自检 · exit code 0/1/2/3/4
- `library/_rag/render_pages.py` —— Step 2 渲染 PNG(soffice/pdftoppm 已加 timeout)

```
1. 用户提供 .pptx 路径
2. agent 复制到 library/pptx-templates/_source/<name>.pptx
   (<name> 不允许含 __ · 跟 page id 分隔符冲突)
3. soffice --headless --convert-to pdf <pptx> + pdftoppm -png -r 120
   渲染每页 → library/pptx-templates/items/<name>/pages/<NN-slug>/preview.png
4. Claude(LLM)看 PNG:
   (a) 总览所有页 → 产 template-level meta.yaml 草稿
   (b) 逐页 → 产 page-level meta.yaml 草稿 + 决定 page slug
5. agent 把草稿展示给用户审 / 改 / 弃
6. 通过的写入:
       library/pptx-templates/items/<name>/meta.yaml
       library/pptx-templates/items/<name>/preview.png   (cover 缩略图)
       library/pptx-templates/items/<name>/pages/<NN-slug>/meta.yaml
       library/pptx-templates/items/<name>/pages/<NN-slug>/preview.png
7. 入库:
       library/_rag/.venv/bin/python library/_rag/embed_text.py  --kb pptx-templates --id <name>
       library/_rag/.venv/bin/python library/_rag/embed_image.py --kb pptx-templates --id <name>
8. 更新 INDEX.md 加一行
```

## 🔑 必填字段(直接进 embedding · 缺则 RAG 检索失效)

`library/_rag/qwen_embedding.py` 的 `build_text_doc_*` 函数会拼接以下字段成 text_doc 喂给 embedding 模型。**任一缺失,该字段在检索时彻底失声**。

**模板级必填**(`build_text_doc_tpl_template`):
- `id` — 主键,**不含 `__`**,embed 时 `INSERT OR REPLACE` 用
- `name` — 人类可读名(开头拼接)
- `category` — 拼接为 "类别 X"
- `content_intent[]` — 每条直接拼接
- `when_to_use[]` — 拼接为 "适用 X"
- `visual_signature[]` — 拼接为 "视觉 X"
- `recommended_for[]` — 拼接为 "推荐 X"
- `keywords[]` — 每条直接拼接

**页级必填**(`build_text_doc_tpl_page`):
- `id` — 主键,格式 `<template_name>__<NN-slug>`(`__` 是分隔符)
- `name` — 人类可读名
- `layout_type` — 拼接为 "布局 X" · **必须从下方受控 enum 选**
- `content_intent[]` — 每条直接拼接
- `when_to_use[]` — 拼接为 "适用 X"
- `native_elements[]` — 拼接为 "元素 X"
- `keywords[]` — 每条直接拼接

## 🎯 layout enum(权威 · 17 个 + 兜底)

| 类别 | enum 值 | 含义 |
|---|---|---|
| structural | `cover` | 封面 / 标题页 |
| structural | `toc` | 目录 / 议程 |
| structural | `section_divider` | 章节分隔页 |
| structural | `summary` | 总结 / 收尾要点 |
| structural | `closing` | Thank you / 结束页 |
| structural | `quote` | 引言 / 客户证言 |
| content | `single_focus` | 单一焦点(大图 / 大字 / KV) |
| content | `cards` | 卡片网格(2/3/4/6 张),用 `variant` 字段细分 |
| content | `bullet_list` | 项目符号正文 |
| content | `data` | 数据图表 / 表格 / KPI |
| diagram | `timeline` | 时间轴 / 阶段演进 |
| diagram | `pyramid` | 金字塔层级 / Maslow |
| diagram | `venn` | 文氏交集图 |
| diagram | `radial` | 中心辐射 / 环形分布 |
| diagram | `process_flow` | 流程箭头 / 步骤推进 |
| diagram | `quadrant` | 2×2 矩阵 / SWOT / BCG |
| diagram | `comparison` | 左右对比 / 双栏 / before-after |
| 兜底 | `other` | **必须同时设** `needs_manual_review: true` **且**在 `layout_hint` 写自创描述 |

不允许在 yaml 里写 enum 之外的值(如 `comparison_venn` / `objective_pyramid` / `horizontal_timeline`)。

## 模板级 meta.yaml schema

```yaml
# === Gate(extractor → 用户审 → embed)===
status: draft                       # draft | approved | embedded
                                    # 文件名后缀 + 字段双轨,embed gate:
                                    #   meta.yaml.draft + status=draft  → extractor 刚写完
                                    #   meta.yaml      + status=approved → 用户审过,主线程可 embed
                                    #   meta.yaml      + status=embedded → 已入 db,可被 RAG 检索

# === Provenance(防 silent failure)===
provenance:
  schema_version: v1                # SemVer
  embedding_model: tongyi-embedding-vision-plus
  embedding_dim: 1152               # 不是 embedding_dimension
  ingested_at: 2026-05-26T10:30:00Z # ISO8601
  source_pptx_sha256: <64-hex>      # shasum -a 256 _source/<name>.pptx
  source_pptx_size_bytes: <int>

# === Extraction summary(advisory · 用户审 gate 必看)===
extraction:
  declared_pages: 39                # unzip -p _source/<name>.pptx ppt/presentation.xml | grep -oc '<p:sldId '
  rendered_pages: 32                # ls items/<name>/pages/*/preview.png | wc -l
  discrepancy: 7                    # declared - rendered;非 0 时必须用户决定
  discrepancy_resolution: pending   # pending | confirmed_tool_pages | confirmed_real_loss
                                    #   confirmed_tool_pages → 漏的是 iSlide / 元素库 / 工具说明页
                                    #   confirmed_real_loss  → 真渲染失败,需修字体 / 重跑
  low_confidence_pages: []          # 页号数组,如 [3, 7]
  failed_pages: []                  # Read 失败的页号

# === P0 必填:进 embedding,缺则 RAG 失声 ===
id: <name>                          # 同目录名 · 不含 __
name: <人类可读 · 例 "Tech Blue · 企业级深蓝">
category: enterprise-modern | training | marketing | sales | academic | ...
content_intent:                     # 模板适合什么内容场景(2-5 条)
  - <例:产品发布会演讲 deck>
when_to_use:                        # 何时该选这个模板(2-5 条)
  - <例:面向高管 / 投资人>
keywords:                           # 检索关键词(5-15 个)
  - <例:深蓝, 企业, 科技>
recommended_for:                    # 受众 / 用途(2-5 条)
  - executive
  - sales
visual_signature:                   # 视觉辨识元素(3-7 条)
  - <例:深蓝 (#1a3a52) 主色>
  - <例:大留白 + 几何装饰>

# === 辅助字段(不进 embedding,但 builder / brainstorm 可能读)===
desc: <一句话简述,可选>
visual_tokens:                      # 从 .pptx 抽
  primary: '#234666'
  accent: '#AD9B5D'
  font_ea: 'Microsoft YaHei'
  title_size_pt: 28
  body_size_pt: 18
assets:
  source_pptx: ../../_source/<name>.pptx
  total_pages: <N>                  # 等于 extraction.rendered_pages
  cover_thumbnail: pages/01-cover/preview.png
pages:                              # 页清单(目录名,按 NN 升序)
  - 01-cover
  - 02-toc
  - ...
implementation:
  tier2_python_theme: null          # 若有 .claude/skills/pptx-deck/themes/<name>.py 写路径
  iLovePPT_can_replicate_pct: null  # 0-100 综合可复刻度
```

## 页级 meta.yaml schema

```yaml
# === Gate ===
status: draft                       # draft | approved | embedded

# === LLM 自评 ===
confidence: 0.92                    # 严格 0.0-1.0 数字 · 不许 high/medium/low 字符串
needs_manual_review: false          # confidence < 0.6 必须 true

# === P0 必填:进 embedding,缺则 RAG 失声 ===
id: <name>__<NN-slug>               # 例: template_golden__01-cover
                                    # 主键,embed 时 INSERT OR REPLACE 用
name: <人类可读 · 例 "Cover · 深蓝 + 白字标题">
layout_type: cover                  # ← 必须从 enum 17 选,违反则用 other + needs_manual_review:true
content_intent:                     # 这页适合放什么内容(2-5 条)
  - <例:产品发布开场,展示产品名 + 一句 slogan>
when_to_use:                        # 何时该用这页(2-5 条)
  - <例:deck 第 1 页 · KV 视觉>
keywords:                           # 检索关键词(3-10 个)
  - <例:封面, 标题, 深蓝>
native_elements:                    # 模板原页面的视觉元素(3-7 条)
  - <例:深蓝渐变背景>
  - <例:右下角白色装饰条>

# === 辅助字段(可选,不进 embedding)===
layout_hint: null                   # layout_type=other 时必填,写自创名留痕
variant: null                       # cards 类细分(如 "3-cols" / "4-icons" / "grid")
page_number: 1                      # = page_index
template_name: <name>               # 反向引用,= 父目录名
fallback_rendering:
  method: native_pptx | diagram | manual
  notes: ...
matches_iloveppt_layout: null       # 若匹配某个 iLovePPT 内置 layout 名
iLovePPT_can_replicate_pct: null    # 0-100 可复刻度
copy_constraints:
  title_max_chars: <N>
  subtitle_max_chars: <N>
```

## 验收 checklist(extractor 跑完 self-check)

不再内嵌 bash · 跑外部脚本:
```bash
library/_rag/.venv/bin/python \
  library/pptx-templates/scripts/extractor_self_check.py <name>
```

Exit code: 0=全过 / 1=字段 enum / list element type / shape_id resolve 错 / 2=pmap tree_path 错 / 3=YAML 语法 / 4=目录不存在。
脚本会校验 11 项:
1. YAML 语法
2. 模板字段必填
3. 页字段必填
4. enum(`layout_type` 17 种 + `other`)
5. id 格式 + 唯一
6. confidence 数字 + 范围 [0,1]
7. `provenance.embedding_dim == 1152`
8. extraction 算式自洽(`declared - rendered == discrepancy`)
9. pmap tree_path resolve(**仅 `.draft` 文件**;approved `.yaml` 文件由 #11 兜底)
10. **list element type**(`keywords / content_intent / when_to_use / native_elements / recommended_for / visual_signature` 每个 element 必须是 `str`,防 `[..., 1]` int 混入导致下游 embed crash)
11. **shape_id resolve**(`.yaml` + `.yaml.draft` 都查;每个 slot `shape_id`(非 null)必须能在 source `.pptx` 对应 slide 找到;`shape_id: null` 允许作 fallback,但若 source `.pptx` 缺失则报 `SOURCE_PPTX_MISSING`)
