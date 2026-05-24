# 历史设计档案

本目录保存 iLovePPT 早期设计 spec 与实施 plan,供 rationale 溯源用。**这些不反映当前系统状态**。

当前系统形态:
- **运行时活协议(权威)**:[`.claude/pipeline-protocol.md`](../../.claude/pipeline-protocol.md)
- **工作原理**:[`../agent-internals.zh.md`](../agent-internals.zh.md)
- **用户手册**:[`../MANUAL.zh.md`](../MANUAL.zh.md)

## 档案清单

| 文件 | 日期 | 内容 |
|---|---|---|
| `2026-05-22-iloveppt-v2-design.md` | 2026-05-22 | v2 设计 spec ——"诚实 skill 重构",建立 `build.py` 机械 / Claude 智能分离 |
| `2026-05-22-iloveppt-v2.md` | 2026-05-22 | v2 实施 plan ——逐步重构步骤 |
| `2026-05-23-iloveppt-agent-design.md` | 2026-05-23 | v3 单 agent 设计 ——从 skill 库到 Claude Code agent |
| `2026-05-23-iloveppt-agent.md` | 2026-05-23 | v3 实施 plan ——单 agent 引入 |
| `2026-05-23-iloveppt-v3-markdown-first.md` | 2026-05-23 | v3 markdown-first 设计 ——拆 3 agent + brief.md/outline.md/content.md 接缝 |

后续从 3 agent 演进到 6 agent + 1 旁路(+ critic / designer / audience / template-extractor)+ Visual Patterns RAG 等迭代,直接在 `.claude/pipeline-protocol.md` 与 `docs/agent-internals.zh.md` 原地更新,不再单独立 spec。
