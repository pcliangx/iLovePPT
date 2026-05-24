# iLovePPT

> 端到端 PPT 生成系统 · Claude Code 6 agent + 1 旁路 流水线 · 对标 BCG/McKinsey 视觉规范

[![Release](https://img.shields.io/github/v/release/pcliangx/iLovePPT)](https://github.com/pcliangx/iLovePPT/releases/latest)
[![Tests](https://img.shields.io/badge/tests-72%20passed-brightgreen)](#)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

把一句话需求变成完整 `.pptx`。用户跟主线程 Claude 对话,6 个 agent 接力完成需求挖掘 → 出 markdown → 评审 → 构建 → 视觉优化 → 受众评分,内容遵循麦肯锡金字塔原理,视觉对标 BCG/McKinsey 咨询稿规范,并配 Visual Patterns 知识库(hosted multimodal RAG)。

---

## 30 秒理解

```
[主线程 Claude = thin dispatcher]      [6 agents · 独立上下文 · 多次派发]

用户:"帮我做个 X 的 PPT"
   │
   ▼
派发 iloveppt-brainstorm           ──→  Stage A 多轮挖需求 + Stage B 收素材
   ↻ 多次派发                              state: .iloveppt_dialog_state.json
   ▼
派发 iloveppt-author               ──→  Stage C 出 outline.md
   ↓
派发 iloveppt-critic(Stage C)     ──→  outline 14 项 + 4 维度判断性评审
   ↓ 用户审 outline
派发 iloveppt-author               ──→  Stage D 拓写 content.md
   ↓
派发 iloveppt-critic(Stage D)     ──→  content 全套两次评审
   ↓ 用户审 content
派发 iloveppt(builder)             ──→  Stage E:md→deck_plan.json → build.py →
                                          17 项机械视觉 QA × ≤ 3 轮
   ↓
派发 iloveppt-designer             ──→  iconify / Unsplash / brand 搜素材 →
                                          改 deck_plan.json 加 icon / hero / 装饰
   ↓
派发 iloveppt-audience             ──→  模拟目标受众读 deck · 9 分硬阈值
                                          反馈 3 分类(author / designer / theme)
   ▼
交付 .pptx + auto_md_edits + review_needed + audience_score

旁路:iloveppt-template-extractor — 用户给 .pptx 模板时摄入 4 级 token
```

## 三大特性

| 特性 | 内容 |
|---|---|
| **6 Agent 流水线 + 1 旁路** | brainstorm / author / critic(C·D 双 gate)/ builder / designer(自动视觉)/ audience(9 分阈值)+ template-extractor 旁路;主线程只 router 不持业务 |
| **Markdown 双 checkpoint + critic 双 gate** | 用户审 `outline.md` + `content.md`,critic 在每个 checkpoint 跑 14 项 checklist + 4 维度判断性评审(论据强度 / 节奏 / 措辞 / 平衡) |
| **BCG/McKinsey 视觉规范 + Visual Patterns RAG** | AAA 对比度 · body 18pt · footer 自动加 · source 引文 · 17 项视觉 QA · 麦肯锡金字塔原理硬约束;接入 `library/visual-patterns/` hosted multimodal RAG(text/image/hybrid 3 种检索) |

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

## 13 种 Layout

`cover` · `toc` · `section_divider` · `single_focus` · `compare` · `compare_pk` · `matrix_2x2` · `cards` · `bullet_list` · `table` · `pic_text` · `summary` · `closing`

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
| [`.claude/pipeline-protocol.md`](.claude/pipeline-protocol.md) | **AI 运行时活协议** — 6 agent 派发 / handoff / gate 权威定义 |
| [`docs/archive/2026-05-23-iloveppt-v3-markdown-first.md`](docs/archive/2026-05-23-iloveppt-v3-markdown-first.md) | **历史设计** — markdown-first spec + 8 决策记录(供溯源) |
| [`CLAUDE.md`](CLAUDE.md) | **Claude Code** — 仓库代码地图 + 不变式 |
| [`skills/pptx-deck/workflow.md`](skills/pptx-deck/workflow.md) | 5 阶段主流程 + dispatcher 协议 |
| [`skills/pptx-deck/content-writing.md`](skills/pptx-deck/content-writing.md) | 13 layout 字数规则 + markdown schema |
| [`skills/pptx-deck/visual-qa.md`](skills/pptx-deck/visual-qa.md) | 视觉自检 17 项 |
| [`skills/diagram/SKILL.md`](skills/diagram/SKILL.md) | draw.io / matplotlib / Mermaid 出图工具链 |
| [`skills/pptx/helpers.py`](skills/pptx/helpers.py) | 设计 token SSOT(色 / 字体 / 几何) |
| [`library/visual-patterns/README.md`](library/visual-patterns/README.md) | Visual Patterns RAG(hosted multimodal) |

## 仓库结构

```
iLovePPT/
├── .claude/
│   ├── pipeline-protocol.md          # AI 运行时活协议(6 agent 派发 / handoff)
│   └── agents/                       # 6 agent + 1 旁路 system prompt
│       ├── iloveppt-brainstorm.md    # Stage A+B 需求与素材
│       ├── iloveppt-author.md        # Stage C+D outline + content
│       ├── iloveppt-critic.md        # Stage C/D 双 gate 评审(14 项 + 4 维度)
│       ├── iloveppt.md               # Stage E builder + 机械视觉 QA
│       ├── iloveppt-designer.md      # builder 后自动视觉优化
│       ├── iloveppt-audience.md      # 模拟受众评分(9 分阈值)
│       └── iloveppt-template-extractor.md  # 旁路:模板摄入
├── skills/
│   ├── pptx-deck/                    # deck 编排 + build.py + theme
│   ├── pptx/                         # .pptx 底层 helpers + 设计 token
│   └── diagram/                      # draw.io / matplotlib / mermaid 出图
├── library/visual-patterns/          # Visual Patterns RAG(hosted multimodal)
├── docs/                             # 文档(MANUAL + agent-internals + spec)
├── tests/                            # 72 测试
├── evals/                            # 视觉回归 eval(固定 plan + scorecard)
└── CLAUDE.md                         # 给 Claude Code 看的代码地图
```

## 测试 + 回归

```bash
python3 -m pytest tests/ -q        # 72/72 pass
bash evals/run_eval.sh             # 视觉回归:跑固定 deck_plan → 对比 baseline
```

## License

[MIT](LICENSE) · © 2026 pcliangx

## Release

Release tag 见 [GitHub releases](https://github.com/pcliangx/iLovePPT/releases)。架构与功能演进可追溯历史 commit。
