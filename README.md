# KillPPTs

端到端 PPT 生成 skill 库 — 复制人类快速生成 PPT 的能力。给主题/要点,自动产出含视觉自检的完整 .pptx。

## 三个 Skill

| Skill | 一句话职责 |
|---|---|
| [`skills/pptx-deck/`](skills/pptx-deck/) | 端到端生成器：brief → 完整 .pptx,含逐页视觉自检 |
| [`skills/pptx/`](skills/pptx/) | 底层 .pptx 读写：从零创建 / 模板编辑 / 提取内容 |
| [`skills/diagram/`](skills/diagram/) | 架构图 / 流程图 / 可视化（draw.io / mermaid / matplotlib / pptx-native） |

## 快速开始

主入口是 `skills/pptx-deck/workflow.py`；`tech_blue` 主题开箱即用；`demo_brief.yaml` 提供可运行示例；`sample_output.pptx` 是 12 页参考成品。

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
cd skills/pptx-deck
python3 workflow.py examples/demo_brief.yaml
```

产物：`skills/pptx-deck/examples/sample_output.pptx`（12 页参考成品）。workflow.py 执行后同目录下可见该文件。

### 3. 自定义 brief

复制 `skills/pptx-deck/brief.example.yaml`,改字段：

```yaml
title: "你的 PPT 主题"
outline:
  - "章节 1"
  - "章节 2"
  - "..."
theme: tech_blue
output: ./my_deck.pptx
```

然后跑：

```bash
python3 skills/pptx-deck/workflow.py my_brief.yaml
```

## 在 Claude Code 中使用

将本仓库 `skills/` 拷贝到目标项目 `.claude/skills/` 下,或符号链接：

```bash
# 拷贝
cp -R /path/to/KillPPTs/skills/* /path/to/your-project/.claude/skills/

# 或符号链接
ln -s /path/to/KillPPTs/skills/pptx       /path/to/your-project/.claude/skills/pptx
ln -s /path/to/KillPPTs/skills/pptx-deck  /path/to/your-project/.claude/skills/pptx-deck
ln -s /path/to/KillPPTs/skills/diagram    /path/to/your-project/.claude/skills/diagram
```

Claude 自动按 frontmatter 触发关键词识别 skill。常见触发：
- "做一份 PPT" / "汇报 deck" / "路演" → `pptx-deck`
- "读 .pptx" / "提取文字" → `pptx`
- "架构图" / "流程图" / "可视化" → `diagram`

## 设计文档

- 完整设计：[`docs/superpowers/specs/2026-05-21-killppts-skill-design.md`](docs/superpowers/specs/2026-05-21-killppts-skill-design.md)
- 实现计划：[`docs/superpowers/plans/2026-05-21-killppts-skill.md`](docs/superpowers/plans/2026-05-21-killppts-skill.md)

## 默认风格

- **主题**：`tech_blue`（深海蓝 `#0B2A4A` + 科技蓝 `#1E6FE0` + 青绿点睛 `#00D1C1`）
- **字体**：Microsoft YaHei（macOS 渲染前请装雅黑,否则 LibreOffice fallback 到 PingFang SC,与 Windows PowerPoint 显示不一致）
- **其他色板**：见 [`skills/pptx/design-system.md`](skills/pptx/design-system.md) 10 套预设（商务深蓝 / 党政红 / 极简白 / 咨询黑 / 莫兰迪灰 / 薄荷绿 / 暖橙 / 灰盐 / 酒红）

切换色板：改 `skills/pptx/helpers.py` 顶部 `BRAND_*` 常量。

## 仓库结构

```
KillPPTs/
├── README.md                        # 本文件
├── docs/superpowers/
│   ├── specs/                       # 设计文档
│   └── plans/                       # 实现计划
└── skills/
    ├── pptx-deck/                   # 端到端生成（主入口）
    │   ├── SKILL.md
    │   ├── workflow.{md,py}
    │   ├── content-writing.md / visual-qa.md / template-ingest.md
    │   ├── themes/tech_blue.py
    │   ├── brief.example.yaml
    │   └── examples/{demo_brief.yaml, sample_output.pptx}
    ├── pptx/                        # 底层读写
    │   ├── SKILL.md
    │   ├── creating.md / editing.md / reading.md / design-system.md
    │   ├── helpers.py
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

# 端到端 smoke
python3 skills/pptx-deck/workflow.py skills/pptx-deck/examples/demo_brief.yaml
```

## 兼容性

- **OS**：macOS 主测；Linux/Windows 理论可用,字体需手动配置
- **Python**：3.10+
- **PowerPoint**：生成的 .pptx 兼容 PowerPoint 2016+ / Keynote / WPS / LibreOffice

## 鸣谢

设计与方法论沉淀来源（已全量去业务化重构）：
- [Anthropic pptx skill](https://github.com/anthropics) 的 `scripts/office/*` 工具
- 内部 PPT 生成实战经验中的 12 个 helper / 7 致丑反模式 / 8 大致丑坑

## License

MIT
