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

## enriched 结构

```yaml
# library/pptx-templates/items/company_a/meta.yaml(模板级)

# === 用户手填 / extractor 起草 ===
name: 公司外部提案模板
desc: 用于客户演示 / 销售提案 / 路演
recommended_for: [executive, sales]
owner: 销售部 (alice@example.com)

# === extractor 自动填 ===
visual_signature: |
  封面深色背景 + 浅色标题(48pt 在 Source Han Sans CN 偏紧建议 ≤ 16 字),
  整体冷色系蓝调,装饰元素少
visual_tokens:
  accent1: "#0B5BCC"           # → BRAND_PRIMARY
  accent2: "#FF6B35"
  dk1: "#1A1A1A"
  lt1: "#FFFFFF"
  font_ea: Source Han Sans CN  # → FONT_CN
  title_size_pt: 44
  body_size_pt: 18
recommended_usage:             # extractor agent 写,主动提示 author
  hero_image: items/company_a/media/cover_hero.png
  icons:
    - items/company_a/media/icon_1.png
    - items/company_a/media/icon_2.png
```

```yaml
# library/pptx-templates/items/company_a/pages/03-cards-process/meta.yaml(每页)
layout_type: cards
intent: 列举并列项(3-5 个)
keywords: [并列, process, 步骤]
visual_observations: |
  卡片 4 列,每列 ≤ 14 字 body 保持平衡;
  标题前留 24px icon 位
fallback_rendering:
  method: native_pptx
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

## 摄入失败处理

| 失败 | render_pages.py / extract_template.py 行为 | extractor agent 后续 |
|---|---|---|
| .pptx 损坏 / 不存在 | 退出 code 2 + stderr | 返回 `error` + `[system] template_extractor_failed` 前缀,主线程展示给用户 |
| L1 unzip 失败 | 警告 + 继续 | 部分提取,标 `template_ready: partial` |
| L2 XML 解析失败 | 静默退回 best-effort | `visual_tokens` 部分为空 |
| L3 渲染失败(soffice 缺) | 报错 + 跳渲染 | 无 preview.png,标 `template_ready: false` |
| L4 视觉分析失败 | — | meta.yaml.draft 无 `visual_observations` |

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
