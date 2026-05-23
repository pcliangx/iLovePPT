# iLovePPT

> 端到端 PPT 生成系统 · Claude Code 三 agent 流水线 · 对标 BCG/McKinsey 视觉规范

[![Release](https://img.shields.io/github/v/release/pcliangx/iLovePPT)](https://github.com/pcliangx/iLovePPT/releases/latest)
[![Tests](https://img.shields.io/badge/tests-62%20passed-brightgreen)](#)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

把一句话需求变成完整 `.pptx`。用户跟主线程 Claude 对话,3 个 agent 接力完成需求挖掘 → 出 markdown → 构建,内容遵循麦肯锡金字塔原理,视觉对标 BCG/McKinsey 咨询稿规范。

---

## 30 秒理解

```
[主线程 Claude = thin dispatcher]      [3 agents · 独立上下文 · 多次派发]

用户:"帮我做个 X 的 PPT"
   │
   ▼
派发 iloveppt-brainstorm      ──→    Stage A 多轮挖需求 + Stage B 收素材
   ↻ 多次派发                          state: .iloveppt_dialog_state.json
   ▼
派发 iloveppt-author          ──→    Stage C 出 outline.md → 你审 →
   ↻ outline 审 → content 审            Stage D 出 content.md → 你审
   ▼
派发 iloveppt(builder)        ──→    Stage E:Pyramid 自检 →
                                       md→deck_plan.json → build.py →
                                       视觉 QA × ≤ 3 轮
   ▼
交付 .pptx + auto_md_edits + review_needed
```

## 三大特性

| 特性 | 内容 |
|---|---|
| **三 Agent 接力** | brainstorm 挖需求 + author 出 markdown + builder 构建,主线程只 router 不持业务 |
| **Markdown 双 checkpoint** | 用户审 `outline.md`(章节)+ `content.md`(全文 + 嵌入图)再 build,避免成品出错才发现 |
| **BCG/McKinsey 视觉规范** | AAA 对比度 · body 18pt · footer 自动加 · source 引文 · 17 项视觉 QA · 麦肯锡金字塔原理硬约束 |

## 快速试跑

```bash
git clone https://github.com/pcliangx/iLovePPT.git
cd iLovePPT
bash skills/pptx/scripts/check_deps.sh                # 检查依赖
python3 skills/pptx-deck/build.py skills/pptx-deck/examples/demo_plan.json
# → skills/pptx-deck/examples/sample_output.pptx + 渲染图
```

依赖:`python-pptx` / `lxml` / LibreOffice / poppler / Microsoft YaHei(macOS 需手动装)。

## Agent 用法

把本仓库的 `.claude/agents/` 链接到目标项目的 `.claude/agents/` 下(或在仓库内直接用),然后在 Claude Code 里:

```
帮我做个 X 主题的 PPT
```

主线程自动派发 `iloveppt-brainstorm`,后续接力到 `.pptx` 交付。详细用户操作见 [`docs/MANUAL.zh.md`](docs/MANUAL.zh.md)。

## 11 种 Layout

`cover` · `toc` · `section_divider` · `single_focus` · `compare` · `cards` · `bullet_list` · `table` · `pic_text` · `summary` · `closing`

各 layout 字段约束 + markdown schema 见 [`skills/pptx-deck/content-writing.md`](skills/pptx-deck/content-writing.md)。

## 内容规范 · 麦肯锡金字塔原理(硬约束)

每份 deck 必须遵循 Pyramid 5 件套,**author 出 outline + builder 收 content** 两层自检:

- ① 单一顶端论点 · ② SCQA 开场 · ③ 答案在前(BLUF)
- ④ 横向 MECE(3-5 章节)· ⑤ 纵向疑问/回答链
- ⑥ 字段完整 · ⑦ action title ≤ 24 字

任一不过 → builder hard stop,**不允许自动修复**(动观点是越界)。

## 视觉规范 · BCG/McKinsey(17 项)

- **字号** body 18pt · page title 32pt · cover 48pt
- **配色** BRAND_PRIMARY `#0A52BF`(AAA 7:1 投影达标)
- **页脚** `N / TOTAL` + 可选 `classification · project · version`
- **数据 source** 自动渲染 `Source: ...`(MBB 硬要求)
- **Cover 元数据** `prepared_by / date / version / project_code / classification`
- **Closing** `next_steps[]` 替代"谢谢"墙
- **matplotlib SSOT** `apply_iloveppt_style()` 一行套上 BRAND_* + YaHei + 极简风
- **12-col grid** `grid_columns()` 锚定跨页对齐
- **视觉 QA 17 项**(12 基础 + 5 进阶 + 3 deck-level 一致性)

完整 checklist 见 [`skills/pptx-deck/visual-qa.md`](skills/pptx-deck/visual-qa.md)。

## 文档地图

| 文档 | 给谁看 |
|---|---|
| [`docs/MANUAL.zh.md`](docs/MANUAL.zh.md) | **用户**(PM / 设计 / 讲者)— 操作手册 |
| [`docs/agent-internals.zh.md`](docs/agent-internals.zh.md) | **改造者** — 系统架构与工作原理 |
| [`docs/superpowers/specs/2026-05-23-iloveppt-v3-markdown-first.md`](docs/superpowers/specs/2026-05-23-iloveppt-v3-markdown-first.md) | **设计权威** — v3.1 spec + 8 决策记录 |
| [`CLAUDE.md`](CLAUDE.md) | **Claude Code** — 仓库代码地图 + 不变式 |
| [`skills/pptx-deck/workflow.md`](skills/pptx-deck/workflow.md) | 5 阶段主流程 + dispatcher 协议 |
| [`skills/pptx-deck/content-writing.md`](skills/pptx-deck/content-writing.md) | 11 layout 字数规则 + markdown schema |
| [`skills/pptx-deck/visual-qa.md`](skills/pptx-deck/visual-qa.md) | 视觉自检 17 项 |
| [`skills/diagram/SKILL.md`](skills/diagram/SKILL.md) | draw.io / matplotlib / Mermaid 出图工具链 |
| [`skills/pptx/helpers.py`](skills/pptx/helpers.py) | 设计 token SSOT(色 / 字体 / 几何) |

## 仓库结构

```
iLovePPT/
├── .claude/agents/                 # 3 agent system prompt
│   ├── iloveppt-brainstorm.md      # Stage A+B
│   ├── iloveppt-author.md          # Stage C+D
│   └── iloveppt.md                 # Stage E builder
├── skills/
│   ├── pptx-deck/                  # deck 编排 + build.py + theme
│   ├── pptx/                       # .pptx 底层 helpers + 设计 token
│   └── diagram/                    # draw.io / matplotlib / mermaid 出图
├── docs/                           # 文档(MANUAL + agent-internals + spec)
├── tests/                          # 62 测试
├── evals/                          # 视觉回归 eval(固定 plan + scorecard)
└── CLAUDE.md                       # 给 Claude Code 看的代码地图
```

## 测试 + 回归

```bash
python3 -m pytest tests/ -q        # 62/62 pass
bash evals/run_eval.sh             # 视觉回归:跑 8 个固定 deck_plan → 对比 baseline
```

## License

[MIT](LICENSE) · © 2026 pcliangx

## Release

最新版本:**[v0.1.0](https://github.com/pcliangx/iLovePPT/releases/latest)** · 2026-05-23 · 架构代号 v3.1
