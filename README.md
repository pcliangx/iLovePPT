# iLovePPT

端到端 PPT 生成 skill 库 — 复制人类快速生成 PPT 的能力。给主题/要点，Claude 产出 `deck_plan.json`，`build.py` 机械地渲染为 `.pptx` + PNG，再由 Claude 逐页视觉自检。

## 三个 Skill

| Skill | 一句话职责 |
|---|---|
| [`skills/pptx-deck/`](skills/pptx-deck/) | 端到端生成器：brief → 完整 .pptx，含逐页视觉自检 |
| [`skills/pptx/`](skills/pptx/) | 底层 .pptx 读写：从零创建 / 模板编辑 / 提取内容 |
| [`skills/diagram/`](skills/diagram/) | 架构图 / 流程图 / 可视化（draw.io / mermaid / matplotlib / pptx-native） |

## 快速开始

主入口是 `skills/pptx-deck/build.py`；`tech_blue` 主题开箱即用；`demo_plan.json` 提供可运行示例；`sample_output.pptx` 是参考成品。

### 1. 装依赖

```bash
bash skills/pptx/scripts/check_deps.sh
```

输出 ✅/❌/⚠️ 列表。缺啥按提示装：

```bash
# Python deps
pip3 install python-pptx lxml 'markitdown[pptx]' Pillow pyyaml

# Render
brew install --cask libreoffice
brew install poppler

# Diagram (按需)
brew install --cask drawio
brew install mermaid-cli
pip3 install matplotlib
```

### 2. 跑 demo

```bash
python3 skills/pptx-deck/build.py skills/pptx-deck/examples/demo_plan.json
```

产物：`deck_plan.json` 中 `output` 字段指定的路径（默认 `skills/pptx-deck/examples/sample_output.pptx`）。

加 `--no-render` 只生成 .pptx 跳过 PNG 渲染：

```bash
python3 skills/pptx-deck/build.py skills/pptx-deck/examples/demo_plan.json --no-render
```

### 3. 自定义 brief

复制 `skills/pptx-deck/brief.example.yaml`，改字段，然后告诉 Claude "帮我按这个 brief 生成 PPT"。Claude 读取 brief，经过 7 步流程（见下）产出 `deck_plan.json`，再调用 build.py 渲染。

## 流水线说明

```
用户 brief（brief.yaml 或自由对话）
    │
    ▼  Claude 驱动（读 brief → 图层规划 → 拓写文案 → 视觉决策）
    │
    ▼  Claude 产出
deck_plan.json
    │
    ▼  build.py 机械执行（无 LLM）
.pptx + PNG
    │
    ▼  Claude 视觉 QA（逐页 Read PNG，对照 12 项 checklist）
最终产物
```

**build.py 是纯机械构建器**：`deck_plan.json → .pptx + PNG`，不含任何 AI 逻辑。内容规划、图层决策、文案拓写、视觉自检均由 Claude 驱动。架构图不会自动生成——Claude 在工作流第 2 步判断哪些章节需要图，调用 `diagram` skill 生成 PNG 后引用到 `pic_text` 页。

## 7 步 Claude 工作流

1. 读 brief → 补齐必填字段
2. 图层规划 → 判断哪些章节需要架构图/流程图/数据图
3. 拓写文案 → 按 layout 文案约束产出每页内容
4. 写 `deck_plan.json`
5. `python3 skills/pptx-deck/build.py deck_plan.json`
6. 视觉 QA → 逐页 Read PNG，按 12 项 checklist 找问题，修 deck_plan.json 后 rebuild
7. 交付产物 + `review_needed` 清单

## 在 Claude Code 中使用

将本仓库 `skills/` 拷贝到目标项目 `.claude/skills/` 下，或符号链接：

```bash
# 拷贝
cp -R /path/to/iLovePPT/skills/* /path/to/your-project/.claude/skills/

# 或符号链接
ln -s /path/to/iLovePPT/skills/pptx       /path/to/your-project/.claude/skills/pptx
ln -s /path/to/iLovePPT/skills/pptx-deck  /path/to/your-project/.claude/skills/pptx-deck
ln -s /path/to/iLovePPT/skills/diagram    /path/to/your-project/.claude/skills/diagram
```

Claude 自动按 frontmatter 触发关键词识别 skill。常见触发：
- "做一份 PPT" / "汇报 deck" / "路演" → `pptx-deck`
- "读 .pptx" / "提取文字" → `pptx`
- "架构图" / "流程图" / "可视化" → `diagram`

## 设计文档

- 完整设计：[`docs/superpowers/specs/2026-05-21-iloveppt-skill-design.md`](docs/superpowers/specs/2026-05-21-iloveppt-skill-design.md)
- 实现计划：[`docs/superpowers/plans/2026-05-21-iloveppt-skill.md`](docs/superpowers/plans/2026-05-21-iloveppt-skill.md)

## 默认风格

- **主题**：`tech_blue`（深海蓝 `#0B2A4A` + 科技蓝 `#1E6FE0` + 青绿点睛 `#00D1C1`）
- **字体**：Microsoft YaHei（macOS 渲染前请装雅黑，否则 LibreOffice fallback 到 PingFang SC，与 Windows PowerPoint 显示不一致）
- **其他色板**：见 [`skills/pptx/design-system.md`](skills/pptx/design-system.md) 10 套预设（商务深蓝 / 党政红 / 极简白 / 咨询黑 / 莫兰迪灰 / 薄荷绿 / 暖橙 / 灰盐 / 酒红）

切换色板：改 `skills/pptx/helpers.py` 顶部 `BRAND_*` 常量。

## 仓库结构

```
iLovePPT/
├── README.md                        # 本文件
├── docs/superpowers/
│   ├── specs/                       # 设计文档
│   └── plans/                       # 实现计划
├── evals/                           # 回归 eval 集
│   └── run_eval.sh                  # eval runner
└── skills/
    ├── pptx-deck/                   # 端到端生成（主入口）
    │   ├── SKILL.md
    │   ├── build.py                 # 机械构建器：deck_plan.json → .pptx + PNG
    │   ├── workflow.md              # 7 步 Claude 工作流文档
    │   ├── content-writing.md / visual-qa.md / template-extract.md
    │   ├── themes/tech_blue.py
    │   ├── brief.example.yaml
    │   └── examples/{demo_plan.json, sample_output.pptx}
    ├── pptx/                        # 底层读写
    │   ├── SKILL.md
    │   ├── creating.md / editing.md / reading.md / design-system.md
    │   ├── helpers.py
    │   ├── layout.py                # 几何图元（geometry primitives）
    │   ├── examples/minimal_deck.py
    │   └── scripts/{thumbnail,clean,add_slide,check_deps,office/...}
    └── diagram/                     # 架构图 / 可视化
        ├── SKILL.md
        ├── drawio.md / mermaid.md / matplotlib.md / pptx-native.md
        └── examples/{minimal.drawio, render.sh}
```

## 测试

```bash
# 单 skill smoke tests
python3 -m pytest tests/ -v

# 端到端 smoke（build.py + demo_plan.json）
python3 skills/pptx-deck/build.py skills/pptx-deck/examples/demo_plan.json

# 回归 eval 集
bash evals/run_eval.sh
```

## 兼容性

- **OS**：macOS 主测；Linux/Windows 理论可用，字体需手动配置
- **Python**：3.10+
- **PowerPoint**：生成的 .pptx 兼容 PowerPoint 2016+ / Keynote / WPS / LibreOffice

## 鸣谢

设计与方法论沉淀来源（已全量去业务化重构）：
- [Anthropic pptx skill](https://github.com/anthropics) 的 `scripts/office/*` 工具
- 内部 PPT 生成实战经验中的 12 个 helper / 7 致丑反模式 / 8 大致丑坑

## License

MIT
