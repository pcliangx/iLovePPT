# 模板摄入完整指南(Stage T · Tier 1)

> 当用户在 brief 里要"按某个 .pptx 模板出稿"时,**iLovePPT 自动跑 Stage T**(模板摄入):复制源文件 → 每页渲染 → 起草双层 meta.yaml(draft)→ 用户审 → 主线程 embed 入库。结果写进 `${CLAUDE_PROJECT_DIR}/library/pptx-templates/items/<name>/`,供后续 author / iloveppt-builder / brainstorm 检索利用。

## 触发条件

**自动触发**:`iloveppt-brainstorm` Stage A 问"对模板有要求吗?",用户答"是"+ 提供 `.pptx` 路径时:

- 若 `${CLAUDE_PROJECT_DIR}/library/pptx-templates/items/<name>/meta.yaml` 已存在(且已 embedded 入 DB)→ **跳过 Stage T**(已 enriched,直接用)
- 否则 → 派发 `iloveppt-template-extractor`(`next_action: dispatch_template_extractor`),跑完后回 brainstorm

**手动触发**(CLI 摄入新模板):

```bash
# 1. 复制源 pptx 到 _source
cp /path/to/company_a.pptx library/pptx-templates/_source/company_a.pptx

# 2. 渲染每页 PNG
library/_rag/.venv/bin/python library/_rag/render_pages.py company_a --dpi 120

# 3.(可选)抽取 L1 媒体 + L2 token
python3 .claude/skills/pptx-deck/extract_template.py library/pptx-templates/_source/company_a.pptx

# 4. LLM 起草 meta.yaml.draft(由 extractor agent 或手工写)
# 5. 用户审 draft → 改名去 .draft 后缀
# 6. 跑 embed 入 DB
library/_rag/.venv/bin/python library/_rag/embed_text.py --kb pptx-templates --id company_a
library/_rag/.venv/bin/python library/_rag/embed_image.py --kb pptx-templates --id company_a
```

## 4 个 Level

```
┌──────────────────────────────────────────────────────────┐
│ L1 · 媒体提取(extract_template.py 可选)                  │
│ unzip ppt/media/* → items/<name>/media/                  │
│ 包括所有 .png / .jpg / .svg / icon                       │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ L2 · 扩展 XML token 提取(extract_template.py 可选)        │
│ 抽 accent1-6 / dk1 / lt1 / 字号阶梯 / 背景类型            │
│ → items/<name>/meta.yaml 的 visual_tokens                │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ L3 · 每页渲染(render_pages.py · soffice)                  │
│ 用 LibreOffice 把每页转 PNG                              │
│ → items/<name>/pages/<NN-slug>/preview.png               │
│ (`__` 开头的 slug 跳过 ingest,如 `__hidden_template`)    │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ L4 · agent 视觉分析(template-extractor agent)             │
│ Read 每页 PNG → 描述模板视觉风格 + per-page intent       │
│ → 起草 items/<name>/meta.yaml.draft(模板级)             │
│ → 起草 items/<name>/pages/<NN>/meta.yaml.draft(每页)    │
│ → 返回 user_review_drafts,主线程让用户审 → 用户批后     │
│   主线程跑 embed 入 DB(text + image)                    │
└──────────────────────────────────────────────────────────┘

(Tier 2 · 复刻 layout,需人工 1-3 天,见 writing-custom-themes.md)
```

## enriched 结构(v2 schema · 权威见 [`library/pptx-templates/ingest_workflow.md`](${CLAUDE_PROJECT_DIR}/library/pptx-templates/ingest_workflow.md))

```yaml
# library/pptx-templates/items/company_a/meta.yaml(模板级)

# === Gate ===
status: draft                                    # draft | approved | embedded

# === Provenance(防 silent failure)===
provenance:
  schema_version: v1
  embedding_model: tongyi-embedding-vision-plus
  embedding_dim: 1152
  ingested_at: 2026-05-26T10:30:00Z
  source_pptx_sha256: <64-hex>                   # shasum -a 256
  source_pptx_size_bytes: 1810473

# === Extraction summary(Step 2.5 + Step 3 聚合 · 用户审 gate 必看)===
extraction:
  declared_pages: 39                             # unzip <p:sldId 数
  rendered_pages: 32                             # ls preview.png 数
  discrepancy: 7                                 # 非 0 时用户审,可能是 iSlide 工具页 / 真渲染失败
  discrepancy_resolution: pending                # pending | confirmed_tool_pages | confirmed_real_loss
  low_confidence_pages: []
  failed_pages: []

# === 必填(进 embedding · build_text_doc_tpl_template 拿这些)===
id: company_a
name: 公司外部提案模板
category: enterprise-modern                      # 自由 string,常用 enterprise-modern/training/marketing/sales
content_intent: [客户演示 / 销售提案 / 路演]
when_to_use: [面向客户决策者, 需冷色稳重视觉]
keywords: [深蓝, 企业, 路演, 销售]
recommended_for: [executive, sales]
visual_signature:
  - 封面深色蓝调 + 浅色标题(48pt Source Han Sans CN ≤ 16 字)
  - 装饰元素少,整体冷色

# === 辅助(不进 embedding)===
visual_tokens:
  primary: '#0B5BCC'
  accent: '#FF6B35'
  font_ea: 'Microsoft YaHei'                     # 或 'Source Han Sans CN' 若模板内嵌
  title_size_pt: 44
  body_size_pt: 18
assets:
  source_pptx: ../../_source/company_a.pptx
  total_pages: 32
  cover_thumbnail: pages/01-cover/preview.png
pages: [01-cover, 02-toc, 03-cards, ...]
```

```yaml
# library/pptx-templates/items/company_a/pages/03-cards/meta.yaml(页级)
status: draft
confidence: 0.92                                 # 严格 0.0-1.0 数字(不许 high/medium/low 字符串)
needs_manual_review: false                       # confidence < 0.6 必须 true

# === 必填(进 embedding · build_text_doc_tpl_page 拿这些)===
id: company_a__03-cards                          # <template_name>__<NN-slug> · __ 是 page id 分隔符
name: "Cards · 4-Column Process Steps"
layout_type: cards                               # ← 必须从 17 enum 选:cover/toc/section_divider/summary/closing/quote/single_focus/cards/bullet_list/data/timeline/pyramid/venn/radial/process_flow/quadrant/comparison + other 兜底
content_intent: [列举并列项(3-5 个)]
when_to_use: [process 步骤, 多卡片 grid]
keywords: [并列, process, 步骤, cards]
native_elements:
  - 卡片 4 列,每列 ≤ 14 字 body 保持平衡
  - 标题前留 24px icon 位

# === 辅助(可选,不进 embedding)===
layout_hint: null                                # layout_type=other 时必填
variant: "4-cols"                                # cards 细分(如 "3-cols" / "4-icons" / "grid")
page_number: 3
template_name: company_a
fallback_rendering:
  method: native_pptx                            # native_pptx | diagram | manual
  matches_iloveppt_layout: cards
```

## author 怎么用 enriched yaml

`iloveppt-author` Stage D Step 1C 自动:

1. Read `${CLAUDE_PROJECT_DIR}/library/pptx-templates/items/<theme>/meta.yaml` 取 `visual_signature` / `visual_tokens` / `recommended_usage`
2. 调 `library/search.sh --preferred-template <theme> --type page` 检索模板内匹配页(score 高的优先用)
3. Stage D 拓写时:
   - **cover 后第 1 页**:若 `recommended_usage.hero_image` 存在,用 `pic_text` layout 嵌入
   - **cards 拓写**:若 `recommended_usage.icons` 有,标题前嵌图标
   - 每页紧跟 `<!-- pattern: tpl:<theme>__<NN-slug> -->` 注释,iloveppt-builder Step 2 按 pattern 渲染
4. 拓写每节文案时,尊重 `visual_observations` 里的字数 / 字号约束

## 摄入失败处理(v2 · error code 枚举)

| code | 触发场景 | 主线程行为 |
|---|---|---|
| `NAME_INVALID_CHARS` | name 含 `__`(跟 page id 分隔符冲突) | 让用户改名重派 |
| `PPTX_CORRUPTED` | unzip 失败,.pptx 损坏 | 让用户重新提供文件 |
| `RENDER_CLI_NOT_FOUND` | soffice/pdftoppm 不在 PATH | 报环境问题(`bash .claude/skills/pptx/scripts/check_deps.sh`)|
| `RENDER_TOTAL_FAILURE` | LibreOffice 渲染 0 页 | 报环境问题 |
| `PAGE_READ_TIMEOUT` | 某页 Read PNG timeout | 可重派 |
| `SCHEMA_VALIDATION_FAILED` | Step 3.3 self-check 失败(YAML 语法 / 必填字段缺 / enum 违规 / id 重复 / confidence 非数字) | 不放行,详见 errors[].message |

**注意**:**Step 2.5 declared vs rendered mismatch 不再是 error**(advisory 设计 · v1 → v2 改动)。`declared != rendered` 时仍跑 Step 3,数字记进 `extraction.{declared_pages, rendered_pages, discrepancy, discrepancy_resolution: pending}`,**让用户审 gate 判断**是"iSlide 工具页(confirmed_tool_pages)"还是"真渲染失败(confirmed_real_loss)"。唯一 hard_stop 是 `rendered == 0`(`RENDER_TOTAL_FAILURE`)。

失败时,extractor agent 通过 `[system] template_extractor_failed` 前缀的 SendMessage 回 brainstorm team,brainstorm 走兜底分支(用户三选一:装好依赖后重试 / 降级 tech_blue / 终止)。

## 与 Tier 2 的边界

| 维度 | Tier 1(本文档) | Tier 2(`writing-custom-themes.md`) |
|---|---|---|
| 目标 | 让 agent "看到"模板,合理利用模板素材 + 检索模板页 | "复刻"模板视觉,layout 真按模板样式 |
| 工作量 | 全自动 + 用户审 draft,~3-5min/模板 | 手工 1-3 天 / 模板 |
| 改动范围 | items/<name>/ yaml + media + preview | 新写 themes/<name>.py(~800 行) |
| 成品视觉 | tech_blue layout + 模板色字 + 模板素材点缀 + 模板页参考嵌入 | 完全模板风(封面 layout / 章节扉页 / 卡片样式 跟着模板) |
| 适用 | 简洁 / 中等视觉模板 | 重视觉 / 长期项目模板 |

**99% 用例 Tier 1 够用**。只有"模板视觉极重 + 长期复用"才走 Tier 2。
