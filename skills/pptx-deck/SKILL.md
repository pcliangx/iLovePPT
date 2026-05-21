---
name: pptx-deck
description: 端到端 PPT 生成器。用户给主题/要点/brief.yaml/参考 .pptx 模板,skill 自动产出完整 .pptx：拓写每页文案、生成架构图、套用风格、逐页视觉自检与优化。内置 tech_blue 科技蓝主题,支持模板学风格（从用户 .pptx 萃取设计 token）。触发：做一份 PPT / 帮我写 PPT / 路演 deck / 汇报 / 提案 / brief.yaml / .pptx 模板。
---

# pptx-deck — 端到端 PPT 生成器

复制人类快速生成 PPT 的能力：用户给主题或参考模板,skill 自动产出含视觉自检的完整 .pptx。

## 何时用本 skill

| 场景 | 用本 skill | 备选 |
|---|:--:|---|
| 用户给主题 + 要点,要完整 deck | ✅ | — |
| 用户给 brief.yaml | ✅ | — |
| 用户给参考 .pptx 模板让仿照风格 | ✅ | — |
| 只读已有 .pptx 提取内容 | — | [[pptx]] reading.md |
| 模板局部改文字 | — | [[pptx]] editing.md |
| 单独生成 1 张架构图 / 流程图 | — | [[diagram]] |
| 已有 outline 想自己排版 | — | [[pptx]] creating.md |

## 输入接口（双路）

### 路 A：自由对话
LLM 与用户对话补齐必填字段（title / outline / theme / output）。缺哪问哪,问完即开始生成。

字段补齐 prompt 模板见 [workflow.md](workflow.md) Step 1。

### 路 B：brief.yaml
用户直接给 yaml。schema 见 [brief.example.yaml](brief.example.yaml),demo 见 [examples/demo_brief.yaml](examples/demo_brief.yaml)。

## 主流程 6 步

详见 [workflow.md](workflow.md)。可跑骨架 [workflow.py](workflow.py):

```bash
python3 workflow.py examples/demo_brief.yaml
```

简版流程图:
```
brief 解析 → 选 theme → 拓 outline → 逐页 generate+render+vision_check+fix → deck_review → save
```

## 依赖检查

```bash
bash ../pptx/scripts/check_deps.sh
```

额外确认（diagram skill 工具链）：
- `ls /Applications/draw.io.app` — 架构图工具
- `which mmdc` — Mermaid CLI
- `python3 -c "import matplotlib"` — 数据可视化

## 共识 token

- **字体**：默认 Microsoft YaHei（macOS 渲染前装雅黑,详见 [[pptx]] creating.md）
- **色板**：内置 tech_blue（PRIMARY #1E6FE0 / DEEP #0B2A4A / TINT #E6F0FC / ACCENT #00D1C1）
- **其他色板**：见 [[pptx]] design-system.md 10 套预设
- **字号体系**：与 [[pptx]] design-system.md 同源

## 子文档导航

| 文档 | 用途 |
|---|---|
| [workflow.md](workflow.md) | 主流程 6 步 + workflow.py 引用 |
| [content-writing.md](content-writing.md) | 11 layout 文案规则 + 拓写 prompt |
| [visual-qa.md](visual-qa.md) | 单页 vision 自检 prompt + 12 项 checklist |
| [template-ingest.md](template-ingest.md) | 用户 .pptx 学风格 6 步流程 |

## 内置主题

[themes/tech_blue.py](themes/tech_blue.py) — 11 个 make_* layout 函数：
- `make_cover` / `make_toc` / `make_section_divider`
- `make_single_focus` / `make_two_col_compare` / `make_three_col_cards`
- `make_bullet_list` / `make_table` / `make_pic_text`
- `make_summary` / `make_closing`

切换其他色板：改 `themes/tech_blue.py` 顶部 PRIMARY_* 常量,或从 [[pptx]] design-system.md 10 色板挑一套覆盖。

## 与 [[pptx]] / [[diagram]] 的关系

```
pptx-deck（本 skill）
  ├─ 调 [[pptx]] helpers.py（set_font / card / bullets / table_modern ...）
  ├─ 调 [[pptx]] scripts/office/soffice.py（渲染验证）
  ├─ 调 [[diagram]] drawio/mermaid/matplotlib（出图）
  └─ 调 [[pptx]] reading.md + 本 skill template-ingest.md（学模板风格）
```

## 交付前 checklist

- [ ] brief 必填字段全到位（title / outline / theme / output）
- [ ] theme 加载成功（tech_blue 或用户 .pptx 模板）
- [ ] outline → page_specs 全部生成（覆盖 cover/toc/各 section/summary/closing）
- [ ] 逐页 vision QA 通过（或加入 review_needed 清单）
- [ ] deck_review 通过：字体一致 + 页脚完整 + 章节配对
- [ ] 最终 .pptx 用 PowerPoint 打开验证（可选,Windows 端确认无 fallback）
- [ ] review_needed 清单给用户人工核审

## Anti-prompt — 让 Claude 不要做的事

- 不要跳过 vision_check 直接交付 — 一定要逐页渲染看图
- 不要在 vision_check 失败 ≥ 3 次时还硬重试 — 直接降级标 review_needed
- 不要 cover/section_divider/closing 用同一种 layout — 节奏感很关键
- 不要堆 5+ 种饱和色 — 用单一品牌色 + 1 强调色 + 灰阶
- 不要假设 macOS 渲染 = Windows 渲染 — Microsoft YaHei 在 macOS 默认 fallback
- 不要内嵌 LLM API 调用到 workflow.py — vision_check 由 Claude 框架做
- 不要 ingest 用户模板时复制其内容 — 只学色板/字体/layout

## 触发关键词

deck / 演示 / PPT / 幻灯片 / 提案 / 路演 / 汇报 / 提报 / 提交报告 / brief.yaml / 自动生成 PPT / 帮我写 PPT
