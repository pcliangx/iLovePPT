# iLovePPT

> Claude Code 多 agent 流水线,把一句话需求变成 BCG 咨询稿质感的 `.pptx`。

[![Release](https://img.shields.io/github/v/release/pcliangx/iLovePPT)](https://github.com/pcliangx/iLovePPT/releases/latest)
[![Stars](https://img.shields.io/github/stars/pcliangx/iLovePPT?style=flat&logo=github)](https://github.com/pcliangx/iLovePPT/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/pcliangx/iLovePPT)](https://github.com/pcliangx/iLovePPT/commits/main)
[![Tests](https://img.shields.io/badge/tests-72%20passed-brightgreen)](#)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

[![Built with Claude Code](https://img.shields.io/badge/built%20with-Claude%20Code-D97757)](https://claude.com/claude-code)
[![Content: Pyramid Principle](https://img.shields.io/badge/content-Pyramid%20Principle-0A52BF)](https://en.wikipedia.org/wiki/Pyramid_principle)
[![Visual Patterns: Multimodal RAG](https://img.shields.io/badge/RAG-multimodal%20(text%2Fimage)-FBCFE8)](library/visual-patterns/README.md)

让 LLM 一次性出完整 .pptx,通常是"看着像但读起来空、视觉糙、论据弱"。**iLovePPT 把"写 PPT"拆成 6 专业 agent + 1 旁路接力流水线**:brainstorm 收需求 → author 出稿 → critic 评审 → builder 构建 → designer 加视觉 → audience 评分,四重 markdown 接缝 + 双闸门质量门(critic 14 项 + audience 9 分硬阈值),内容遵循麦肯锡金字塔原理,视觉对标 BCG/McKinsey。

---

## Quick Start

```bash
git clone https://github.com/pcliangx/iLovePPT.git
cd iLovePPT
bash skills/pptx/scripts/check_deps.sh                                    # 检查依赖
python3 skills/pptx-deck/build.py skills/pptx-deck/examples/demo_plan.json   # → demo .pptx + PNG
```

依赖:`python-pptx` / `lxml` / LibreOffice / poppler / Microsoft YaHei(macOS 需手动装)。

## Agent 用法

把仓库的 `.claude/agents/` 链接到你目标项目的 `.claude/agents/` 下(或直接在仓库内用),然后在 Claude Code 里说一句话:

```
帮我做个 Claude Code 培训的 PPT,15 分钟,技术受众
```

主线程自动派发 6 agent 接力,从需求挖掘到 .pptx 交付:

```mermaid
flowchart TB
    U([用户:帮我做个 X 的 PPT]) --> BS
    BS["<b>brainstorm</b><br/>多轮挖需求<br/>brief.md gate"] --> AU1
    AU1["<b>author</b> Stage C<br/>出 outline.md<br/>用户审"] --> CR1
    CR1["<b>critic</b> Stage C<br/>14 项 + 4 维度判断性"] --> AU2
    AU2["<b>author</b> Stage D<br/>拓 content.md<br/>用户审"] --> CR2
    CR2["<b>critic</b> Stage D<br/>全套评审"] --> BD
    BD["<b>builder</b><br/>md → deck_plan.json → build.py<br/>17 项机械视觉 QA × ≤ 3 轮"] --> DS
    DS["<b>designer</b><br/>iconify / Unsplash / brand<br/>加 icon / hero / 装饰"] --> AD
    AD["<b>audience</b><br/>9 分硬阈值<br/>三类反馈分流"] -->|≥ 9 + 用户 OK| OUT
    OUT([交付 .pptx + audience_review])

    classDef user fill:#FFF,stroke:#333,color:#000
    classDef stage1 fill:#DCFCE7,stroke:#16A34A,color:#14532D
    classDef stage2 fill:#FCE7F3,stroke:#BE185D,color:#831843
    classDef stage3 fill:#CFFAFE,stroke:#0891B2,color:#0E4F62
    classDef stage4 fill:#E6F0FC,stroke:#1E6FE0,color:#0B2A4A
    classDef stage45 fill:#FBCFE8,stroke:#C026D3,color:#701A75
    classDef stage5 fill:#FED7AA,stroke:#EA580C,color:#7C2D12

    class U,OUT user
    class BS stage1
    class AU1,AU2 stage2
    class CR1,CR2 stage3
    class BD stage4
    class DS stage45
    class AD stage5
```

详细操作手册见 [docs/MANUAL.zh.md](docs/MANUAL.zh.md)。

## 文档地图

| 文档 | 给谁看 |
|---|---|
| [docs/MANUAL.zh.md](docs/MANUAL.zh.md) | **用户** — 怎么对话、审稿、收稿 |
| [docs/agent-internals.zh.md](docs/agent-internals.zh.md) | **改造者** — 流水线架构 + agent 职责 + 4 协作机制 + 6 设计决策 |
| [.claude/pipeline-protocol.md](.claude/pipeline-protocol.md) | **Claude Code 主线程 AI** — 派发顺序 / handoff / gate 权威活协议 |
| [CLAUDE.md](CLAUDE.md) | **Claude Code** — 仓库导航 + 不变式 + 约定 |
| [library/visual-patterns/README.md](library/visual-patterns/README.md) | Visual Patterns RAG(hosted multimodal,text/image/hybrid 3 mode) |

## License

[MIT](LICENSE) · © 2026 pcliangx
