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

让 LLM 一次性出完整 .pptx,通常是"看着像但读起来空、视觉糙、论据弱"。**iLovePPT 把"写 PPT"拆成 5 专业 agent + 1 旁路接力流水线**:brainstorm 收需求 → author 出稿 → critic 评审 → iloveppt 构建 + 加视觉 → audience 评分,四重 markdown 接缝 + 双闸门质量门(critic 14 项 + audience 9 分硬阈值),内容遵循麦肯锡金字塔原理,视觉对标 BCG/McKinsey。

---

## Quick Start

```bash
# 1. clone + 装依赖
git clone https://github.com/pcliangx/iLovePPT.git
cd iLovePPT
pip install -e ".[diagram,dev]"

# 2. 检查外部依赖(LibreOffice / poppler / Microsoft YaHei)
bash .claude/skills/pptx/scripts/check_deps.sh

# 3. (可选)跑一遍 demo 验证安装
python3 .claude/skills/pptx-deck/build.py .claude/skills/pptx-deck/examples/demo_plan.json

# 4. 在仓库根目录打开 Claude Code,跟主线程说一句话:
#    "帮我做个 Claude Code 培训的 PPT,15 分钟,技术受众"
#    主线程会自动派 5 agent 接力,产出在 decks/<slug>/builder/deck_v1.pptx
```

依赖:`python-pptx` / `lxml` / LibreOffice / poppler / Microsoft YaHei(macOS 需手动装,Linux 通常自带)。

## 流水线一览

在仓库根目录跟 Claude Code 说一句话(如"帮我做个 Claude Code 培训的 PPT,15 分钟,技术受众"),主线程自动派 5 agent + 1 旁路接力:

```mermaid
flowchart TB
    U([用户 · 一句话需求]) --> BS["<b>1 · brainstorm</b><br/>多轮挖 brief"]
    BS --> AU["<b>2 · author</b><br/>出 outline + 拓 content"]
    AU --> CR{{"<b>3 · critic</b><br/>Stage C/D 双 gate · 14 项 + 4 维度判断"}}
    CR -->|pass| BD["<b>4 · iloveppt</b><br/>build.py + 17 项机械 QA<br/>+ Step 4 主动加视觉(iconify/Unsplash/brand)"]
    BD --> AD{{"<b>5 · audience</b><br/>9 分硬阈值"}}
    AD -->|≥ 9 + 用户 OK| OUT([.pptx 交付])
    AD -.->|< 9 反馈| AU

    classDef agent fill:#F8FAFC,stroke:#64748B,stroke-width:1.5px,color:#0F172A
    classDef gate fill:#FEF3C7,stroke:#D97706,stroke-width:2px,color:#78350F
    classDef io fill:#DCFCE7,stroke:#16A34A,stroke-width:2px,color:#14532D

    class BS,AU,BD agent
    class CR,AD gate
    class U,OUT io
```

详细操作手册见 [docs/MANUAL.zh.md](docs/MANUAL.zh.md)。

## 文档地图

| 文档 | 给谁看 |
|---|---|
| [docs/MANUAL.zh.md](docs/MANUAL.zh.md) | **用户** — 怎么对话、审稿、收稿 |
| [docs/agent-internals.zh.md](docs/agent-internals.zh.md) | **改造者** — 流水线架构(Hybrid:1 brainstorm team + 5 subagent + 1 旁路 subagent)+ agent 职责 + 4 协作机制 + 6 设计决策 |
| [docs/agent-team-evaluation-checklist.zh.md](docs/agent-team-evaluation-checklist.zh.md) | **评审者** — 8 维度(A-H)审计框架 + L1-L3 母法则,适用任何 multi-agent system |
| [.claude/pipeline-protocol.md](.claude/pipeline-protocol.md) | **Claude Code 主线程 AI** — 派发顺序 / handoff / gate 权威活协议 |
| [CLAUDE.md](CLAUDE.md) | **Claude Code** — 仓库导航 + 不变式 + 约定 |
| [library/visual-patterns/README.md](library/visual-patterns/README.md) | Visual Patterns RAG(hosted multimodal,text/image/hybrid 3 mode) |

## License

[MIT](LICENSE) · © 2026 pcliangx
