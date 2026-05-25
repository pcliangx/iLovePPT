---
name: pptx-deck
description: pptx-deck 知识库 —— 13 个 layout 的主题(tech_blue)、build.py 机械构建器、文案/图层/视觉 QA/模板提取的参考文档。**主入口是 [[iloveppt]] agent**(@agent-iloveppt 派发,带大纲 checkpoint 自动跑完全程);本 SKILL.md 仅作 skill-mode 后备入口供主线程 Claude 直接读用。触发由 agent 的 description 接管;本 skill 不再做自动委派。
---

# pptx-deck — 端到端 PPT 生成器

> **主入口:`@agent-iloveppt`**(独立上下文跑 Stage C(出 outline 等批准)→ Stage D(拓写 content)→ Stage E(构建 .pptx + 机械视觉 QA)→ designer + audience)。本 skill 仍可被主线程 Claude 直接读用作 skill-mode 后备入口;触发关键词已搬到 agent 的 description。
> agent 设计见 [iLovePPT Agent 设计](${CLAUDE_PROJECT_DIR}/docs/archive/2026-05-23-iloveppt-agent-design.md)。

复制人类快速生成 PPT 的能力：用户给主题或参考模板,skill 自动产出含视觉自检的完整 .pptx。Claude 产出 `deck_plan.json`，`build.py` 机械地将其渲染为 `.pptx` + PNG。

## 核心原则：一图胜千文

能用图形表达的观点,就不要用文字堆——凡涉及结构、流程、关系、数据对比的内容,主动调用 AI 绘图能力（[[diagram]] skill）出图。判断犹豫时倾向于画图。这条原则由主流程第 3 步「图层规划」强制兑现,见 [diagram-planning.md](diagram-planning.md)。

## 何时用本 skill

| 场景 | 用本 skill | 备选 |
|---|:--:|---|
| 用户给主题 + 要点,要完整 deck | ✅ | — |
| 用户给 brief.md(主用)或 brief.yaml(兼容) | ✅ | — |
| 用户给参考 .pptx 模板让仿照风格 | ✅ | — |
| 只读已有 .pptx 提取内容 | — | [[pptx]] reading.md |
| 模板局部改文字 | — | [[pptx]] editing.md |
| 单独生成 1 张架构图 / 流程图 | — | [[diagram]] |
| 已有 outline 想自己排版 | — | [[pptx]] creating.md |

## 输入接口（双路）

### 路 A：自由对话
LLM 与用户对话补齐必填字段（title / outline / theme / output）。缺哪问哪,问完即开始生成。

字段补齐 prompt 模板见 [workflow.md](workflow.md) Step 1。

### 路 B：brief.md(主用)/ brief.yaml(兼容)
主流程由 iloveppt-brainstorm agent 多轮对话产出 `brief.md`(markdown-first);仍兼容用户直接给 `brief.yaml`,schema 见 [brief.example.yaml](brief.example.yaml),deck_plan demo 见 [examples/demo_plan.json](examples/demo_plan.json)。

## 主流程 7 步

详见 [workflow.md](workflow.md)。构建步骤（mechanical iloveppt）：

```bash
python3 build.py deck_plan.json
# 可选：仅生成 .pptx 不渲染 PNG
python3 build.py deck_plan.json --no-render
```

简版流程图:
```
brief 解析 → 选 theme → 图层规划 → 拓 outline → Claude 产出 deck_plan.json → build.py 渲染 .pptx+PNG → vision QA → fix deck_plan.json → rebuild
```

读完 brief 后第 3 步「图层规划」会主动判断哪些章节该配架构图 / 流程图 / 数据图,详见 [diagram-planning.md](diagram-planning.md)。

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
| [workflow.md](workflow.md) | 主流程 7 步 + build.py / deck_plan.json 衔接 |
| [diagram-planning.md](diagram-planning.md) | 图层规划：判断哪些章节配图 + 4 类图决策规则 |
| [content-writing.md](content-writing.md) | 13 layout 文案规则 + 拓写 prompt |
| [visual-qa.md](visual-qa.md) | 单页 vision 自检 prompt + 17 项 checklist |
| [template-extract.md](template-extract.md) | 从用户 .pptx 提取主色与字体 6 步流程 |

## 内置主题

[themes/tech_blue.py](themes/tech_blue.py) — 13 个 make_* layout 函数：
- `make_cover` / `make_toc` / `make_section_divider`
- `make_single_focus` / `make_compare` / `make_compare_pk` / `make_matrix_2x2`
- `make_cards` / `make_bullet_list` / `make_table` / `make_pic_text`
- `make_summary` / `make_closing`

切换其他色板：改 `themes/tech_blue.py` 顶部 PRIMARY_* 常量,或从 [[pptx]] design-system.md 10 色板挑一套覆盖。

## 与 [[pptx]] / [[diagram]] 的关系

```
pptx-deck（本 skill）
  ├─ 调 [[pptx]] helpers.py（set_font / card / bullets / table_modern ...）
  ├─ 调 [[pptx]] scripts/office/soffice.py（渲染验证）
  ├─ 调 [[diagram]] drawio/mermaid/matplotlib（出图）
  └─ 调 [[pptx]] reading.md + 本 skill template-extract.md（提取主色与字体）
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

- 不要跳过视觉 QA 直接交付 — 一定要逐页 Read PNG 检查
- 不要在视觉 check 失败 ≥ 3 次时还硬重试 — 直接降级标 review_needed
- 不要 cover/section_divider/closing 用同一种 layout — 节奏感很关键
- 不要堆 5+ 种饱和色 — 用单一品牌色 + 1 强调色 + 灰阶
- 不要假设 macOS 渲染 = Windows 渲染 — Microsoft YaHei 在 macOS 默认 fallback
- 不要在 build.py 内嵌 LLM API 调用 — vision QA 由 Claude 框架做
- 不要 extract 用户模板时复制其内容 — 只提取主色/字体/layout token

## 触发关键词

deck / 演示 / PPT / 幻灯片 / 提案 / 路演 / 汇报 / 提报 / 提交报告 / brief.md / brief.yaml / 自动生成 PPT / 帮我写 PPT
