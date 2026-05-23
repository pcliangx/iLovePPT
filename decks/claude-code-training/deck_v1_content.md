---
title: Claude Code · 不只是 copilot,是 agentic coding platform
subtitle: 50 分钟带你从"装上"到"用它跑 multi-step task"
audience: general
duration_min: 50
theme: tech_blue
output: ./deck_v1.pptx
top_recommendation: Claude Code 是一个能跑 plan → act → verify 循环的 agentic coding platform,不只是 chat,要用 6 件套(commands/skills/agents/hooks/MCP/plugins)解锁
footer_meta:
  classification: INTERNAL
  project: Claude Code Training
  version: v1.0
based_on: deck_v1_outline.md
---

# Content

## [cover]
- title: Claude Code · 不只是 copilot
- subtitle: 它是 agentic coding platform
- prepared_by: 培训组
- date: 2026-05-23
- version: v1.0
- classification: INTERNAL

## [toc]
- 什么是 Claude Code
- ≠ Copilot · 3 个根本差别
- 心智 1 · Agentic loop
- 心智 2 · 6 件套扩展能力
- 心智 3 · 真实 case

## [section_divider]
- num: 1
- title: 什么是 Claude Code

## 1. 五端可用的 agentic coding tool
<!-- layout: cards -->

- **定义**: agentic 编码工具
- **能力**: 读 / 改 / 跑 / 验
- **场景**: 多步开发任务

> 数据:Source: code.claude.com/docs/en/overview

## 2. 一套 Claude · 五个 surface 跑
<!-- layout: cards -->

- **Terminal**: CLI 全功能
- **VS Code**: 插件嵌入
- **JetBrains**: 同上跨 IDE
- **Desktop**: 独立 app + 视觉 diff
- **Web / iOS**: 云端 + 手机

> 数据:Source: 官方 overview 文档

## 3. 跟 Claude.ai 和 API 是三回事
<!-- layout: compare -->

- title: Claude.ai
  body: 聊天为主无文件权限
- title: Claude Code
  body: 五端 agentic 跑任务
- title: Claude API
  body: 程序员调模型自建 app

> 数据:Source: 官方对比表

## [section_divider]
- num: 2
- title: ≠ Copilot · 3 个根本差别

## 4. Copilot 给建议 · Claude Code 干活
<!-- layout: cards -->

- **单步 vs 多步**: 补全 vs 跑全流程
- **写 vs 全干**: 只生成 vs 读改跑验
- **IDE 内 vs 五端**: 单点 vs 跨场景

> 数据:Source: 官方 vs Copilot 定位

## [section_divider]
- num: 3
- title: 心智 1 · Agentic loop

## 5. Plan → Act → Verify · 闭环跑到目标
<!-- layout: pic_text -->

![Agentic loop 流程](_assets/charts/agentic_loop.png)

- **Plan**: 读 codebase 理解
- **Act**: 改文件跑命令
- **Verify**: 跑测试看结果
- **循环**: 不达标继续

## 6. /goal 命令 · 扔目标自己跑
<!-- layout: single_focus -->

- big_text: /goal "全测试过再停"
- big_number: v2.1.139+
- explanation: 设完成条件让 Claude 持续干,达标才返回

> 数据:Source: code.claude.com/docs/en/commands

## [section_divider]
- num: 4
- title: 心智 2 · 6 件套扩展能力

## 7. 它是 platform · 不是 chat
<!-- layout: pic_text -->

![6 件套架构](_assets/charts/six_pack.png)

- **6 个 building block**: 各管一段
- **官方核心**: 不是周边
- **可组合**: 1 + 1 > 2

## 8. Commands + Skills · 触发与复用
<!-- layout: cards -->

- **Commands**: 30+ 内置 slash
- **/help · /goal**: 常用入门
- **Skills**: 自定义工作流
- **frontmatter**: 控制行为

> 数据:Source: docs 30+ commands 全集

## 9. Sub-agents + Hooks · 隔离与自动化
<!-- layout: cards -->

- **Sub-agents**: 独立上下文
- **工具限制**: 安全 + 聚焦
- **Hooks**: 31 events
- **事件驱动**: 自动化全流

> 数据:Source: docs sub-agents + hooks

## 10. MCP + Plugins · 连外部与生态
<!-- layout: cards -->

- **MCP**: open standard
- **连外部工具**: 数据 / API
- **Plugins**: marketplace
- **v2.1.100+**: 装一包带全套

> 数据:Source: docs mcp + plugins

## 11. 6 件套何时用 · 一表速查
<!-- layout: table -->

- title: 何时用哪个
- headers: [需求, 用什么]
- rows:
  - [一句话快捷, Commands]
  - [可复用工作流, Skills]
  - [独立子任务, Sub-agents]
  - [事件触发自动化, Hooks]
  - [连外部工具, MCP]
  - [整包生态, Plugins]

## [section_divider]
- num: 5
- title: 心智 3 · 真实 case · iLovePPT

## 12. 起点 · v2 单 agent 痛点真实存在
<!-- layout: bullet_list -->

- 单 agent 端到端体感粗
- yaml 接口用户读不懂
- 视觉规范缺标准
- 模板复用零支持

> 数据:Source: 本仓库 git history

## 13. 演进 · 1 session 6 milestone
<!-- layout: pic_text -->

![iLovePPT 演进时间线](_assets/charts/evolution_timeline.png)

- **commits**: 15 → 82
- **tests**: 42 → 68
- **agents**: 1 → 4
- **release**: v0.1 + v0.2

## 14. v2 vs v3.1 · 架构演进对比
<!-- layout: compare -->

- title: v2 单 agent
  body: 端到端拓写视觉 QA
- title: v3.1 三 agent
  body: 主线程分发独立上下文

> 数据:Source: docs/agent-internals.zh.md

## 15. 真实成绩 · 1 个 session 跑出
<!-- layout: table -->

- title: 关键数据
- headers: [维度, v2 起点, v0.2.0 终点]
- rows:
  - [Agent 数, 1, 4]
  - [Tests 数, 42, 68]
  - [Docs 数, 8, 28]
  - [Release 数, 0, 2]
  - [模板复刻, 0%, 75%]

> 数据:Source: 本仓库实际统计

## [summary]
- agentic loop 是核心心智
- 6 件套远不只 chat
- 1 session 出 2 release

## [closing]
- subtitle: Q&A · 下一步动作
- next_steps:
  - action: 装 Claude Code 跑一次 /goal demo
    owner: 每人
    due: 本周
  - action: 看 docs 6 件套各自细节
    owner: 进阶者
    due: 本月
  - action: 用本 case 复制一个自己的项目流程
    owner: 兴趣组
    due: 下个月
