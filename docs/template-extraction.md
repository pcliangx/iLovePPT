# 模板摄入完整指南(Stage T · Tier 1)

> 当用户在 brief 里要"按某个 .pptx 模板出稿"时,**iLovePPT 自动跑 Stage T**(模板摄入):L1 媒体提取 + L2 扩展 token + probe 渲染 + agent 视觉分析。结果写进 `templates/<name>.yaml`,供后续 author 拓写时利用。

## 触发条件

**自动触发**:`iloveppt-brainstorm` Stage A 问"对模板有要求吗?",用户答"是"+ 提供 `.pptx` 路径时:

- 若 `templates/<name>.yaml` 已存在且 `probe.visual_observations` 已填 → **跳过 Stage T**(已 enriched,直接用)
- 否则 → 派发 `iloveppt-template-extractor`,跑完后回 brainstorm

**手动触发**(CLI,适合 CI / 不走 agent 场景):

```bash
python3 skills/pptx-deck/extract_template.py templates/company_a.pptx
python3 skills/pptx-deck/extract_template.py templates/company_a.pptx --no-probe
```

## 4 个 Level

```
┌──────────────────────────────────────────────────────────┐
│ L1 · 媒体提取(extract_template.py 自动)                  │
│ unzip ppt/media/* → _assets/template_<name>/             │
│ 包括所有 .png / .jpg / .svg / icon                       │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ L2 · 扩展 XML token 提取                                  │
│ 抽 accent1-6 / dk1 / lt1 / 字号阶梯 / 背景类型            │
│ → templates/<name>.yaml 的 extracted.tokens              │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ probe deck · 8 页探针(8 种 layout 各一)                  │
│ 用提取后的 theme 跑 build.py                             │
│ → /tmp/probe_<name>/probe_render/page-*.jpg              │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ agent 视觉分析(template-extractor agent)                  │
│ Read 8 张 PNG → 描述模板视觉风格                          │
│ → 写进 templates/<name>.yaml 的 probe.visual_observations │
│ → 同时给 recommended_usage(hero/icons/decorative_bg)     │
└──────────────────────────────────────────────────────────┘

(Tier 2 · L3 复刻 layout,需人工 1-3 天,见 writing-custom-themes.md)
```

## enriched `<name>.yaml` 结构

```yaml
# templates/company_a.yaml(摄入后)

# === 用户手填(保留) ===
name: 公司外部提案模板
desc: 用于客户演示 / 销售提案 / 路演
recommended_for: [executive, sales]
owner: 销售部 (alice@example.com)
notes: |
  封面深色,subtitle 字号偏小(建议 ≤ 25 字)
  数据图建议浅色背景

# === extractor 自动填 ===
extracted:
  source_pptx: /abs/path/to/templates/company_a.pptx
  media_files: [cover_hero.png, icon_1.png, icon_2.png, section_bg.png, ...]
  media_dir: _assets/template_company_a/
  tokens:
    accent1: "#0B5BCC"           # → BRAND_PRIMARY
    accent2: "#FF6B35"           # → ACCENT_2(新)
    accent3: "#28A745"
    dk1: "#1A1A1A"
    lt1: "#FFFFFF"
    font_ea: Source Han Sans CN  # → FONT_CN
    title_size_pt: 44            # 若 master 显式定义
    body_size_pt: 18
    background_type: image       # solid/gradient/image/theme_ref
  recommended_usage:             # extractor agent 写,主动提示 author
    hero_image: _assets/template_company_a/cover_hero.png
    icons:
      - _assets/template_company_a/icon_1.png
      - _assets/template_company_a/icon_2.png
    decorative_bg: _assets/template_company_a/section_bg.png

# === extractor agent 视觉分析后填 ===
probe:
  render_dir: /tmp/probe_company_a/probe_render
  page_count: 8
  visual_observations: |
    封面深色背景 + 浅色标题,48pt 在 Source Han Sans CN 下偏紧,
    建议 ≤ 16 字
    cards 在该模板下 16pt body 略小,建议 ≤ 14 字保持平衡
    section_divider 主色对比 7.5:1 AAA,single_focus 也可用
    icon 库 12 个图标可用,author 拓写 cards 时可在标题前嵌
    封面 hero_image 高质量插图,推荐 cover 后第 1 页 pic_text 嵌入
```

## author 怎么用 enriched yaml

`iloveppt-author` Step 0 自动:

1. Read `templates/<theme>.yaml`
2. Read `<working_dir>/_assets/template_<name>/` 列媒体清单
3. Stage D 拓写时:
   - **cover 后第 1 页**:若 `recommended_usage.hero_image` 存在,用 `pic_text` layout 嵌入
   - **cards 拓写**:若 `recommended_usage.icons` 有,标题前嵌图标
   - **section_divider**:若 `recommended_usage.decorative_bg`,标注 author 选用(但当前 layout 不一定支持背景图,记 review_needed)
4. 拓写每节文案时,尊重 `notes` 和 `visual_observations` 里的约束(字数 / 字号建议)

## 摄入失败处理

| 失败 | extract_template.py 行为 | extractor agent 后续 |
|---|---|---|
| .pptx 损坏 / 不存在 | 退出 code 2 + stderr | 返回 error,主线程展示给用户 |
| L1 unzip 失败 | 警告 + 继续 L2 | 部分提取,标 template_ready: partial |
| L2 XML 解析失败 | 静默退回 best-effort | extracted.tokens 部分为空 |
| probe build 失败(soffice 缺) | 警告 + 跳 probe | yaml 无 probe 段,template_ready: true(L1+L2 OK) |
| probe 渲染失败 | 警告 + 跳 visual analysis | yaml 无 probe.visual_observations |

无论哪种失败,extractor agent **都返回 dispatch_brainstorm**,带 `template_ready: true/partial/false` 标志,主线程展示给用户决定是否继续。

## 与 Tier 2 的边界

| 维度 | Tier 1(本文档) | Tier 2(`writing-custom-themes.md`) |
|---|---|---|
| 目标 | 让 agent "看到"模板,合理利用模板素材 | "复刻"模板视觉,layout 真按模板样式 |
| 工作量 | 全自动,~1min/模板 | 手工 1-3 天 / 模板 |
| 改动范围 | yaml + _assets/ 文件 | 新写 themes/<name>.py(~800 行) |
| 成品视觉 | tech_blue layout + 模板色字 + 模板素材点缀 | 完全模板风(封面 layout / 章节扉页 / 卡片样式 跟着模板) |
| 适用 | 简洁 / 中等视觉模板 | 重视觉 / 长期项目模板 |

**99% 用例 Tier 1 够用**。只有"模板视觉极重 + 长期复用"才走 Tier 2。
