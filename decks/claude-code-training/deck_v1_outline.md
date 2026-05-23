---
title: Claude Code · 不只是 copilot,是 agentic coding platform
subtitle: 50 分钟带你从"装上"到"用它跑 multi-step task"
audience: general
duration_min: 50
theme: tech_blue
output: ./deck_v1.pptx
top_recommendation: Claude Code 是一个能跑 plan → act → verify 循环的 agentic coding platform,不只是 chat,要用 6 件套(commands/skills/agents/hooks/MCP/plugins)解锁
scqa:
  situation: 团队都在用 GitHub Copilot 等 IDE 内 AI 补全工具,以为 Claude Code 是"另一个 copilot"
  complication: 但 Claude Code 在 terminal/IDE/desktop/web/iOS 五端可用,能跑 multi-step agentic loop(读代码 → 改文件 → 跑命令 → 验证),还能装 plugins / 派 subagents / 配 hooks,按 copilot 用法用它会浪费 90% 能力
  question: 那它到底是什么?该用什么心智?能扩展到什么程度?
  answer: 把它当 "agentic coding platform",学 agentic loop(心智 1)+ 6 件套扩展能力(心智 2)+ 看一个真实 case(心智 3)
footer_meta:
  classification: INTERNAL
  project: Claude Code Training
  version: v1.0
---

# Outline

## 1. 什么是 Claude Code · 一个 agentic coding tool

- intent: 让 general audience 知道 Claude Code 在哪运行 / 是个啥 / 怎么开始 / 跟 Claude.ai / Claude API 什么关系
- layout: cards + bullet_list 混搭
- data: 官方定义 "agentic coding tool that reads codebase, edits files, runs commands, integrates with dev tools"(code.claude.com/docs/en/overview);5 端 terminal/VS Code/JetBrains/Desktop/Web/iOS;Pro $20/月 起或团队版
- diagram: 无(用 cards 排比 5 个 surface)
- estimated_pages: 3 内容页 + 1 section_divider = 4 页

## 2. ≠ Copilot · 3 个根本差别

- intent: 校准听众对"AI 编码工具"心智 — 这不是 inline 补全,是多步执行 agent
- layout: cards(三张对比 Copilot vs Claude Code)
- data: 单步建议 vs 多步执行 / 写代码 vs 读+写+跑+判断 / IDE 内 vs 5 端跨场景
- diagram: 无(cards 视觉对比足够)
- estimated_pages: 1 内容页 + 1 section_divider = 2 页

## 3. 心智 1 · Agentic loop(plan → act → verify)

- intent: 入门段 — 用真实示例展示"agentic loop"概念,这是 Claude Code 工作原理的核心
- layout: pic_text(展示一次完整 loop 截图)+ bullet
- data: agentic loop 3 步 / `/goal` 命令设完成条件让 Claude 持续干(v2.1.139+)/ Agent View `/agents` 看所有 sessions
- diagram: drawio - agentic loop 流程图(gather context → take action → verify → repeat 闭环)
- estimated_pages: 2 内容页 + 1 section_divider = 3 页

## 4. 心智 2 · 6 件套扩展能力(它是 platform 不是 chat)

- intent: 进阶段 — 展示 Claude Code 的 6 个 building block,这是它跟其他 AI 工具的根本差别
- layout: cards(6 件套总览)+ pic_text(关系图)
- data: commands(slash 触发,30+ 内置)/ skills(`.claude/skills/`,自定义工作流)/ sub-agents(`.claude/agents/`,独立上下文 + 工具限制)/ hooks(`.claude/settings.json`,31 events)/ MCP(open standard 连外部工具)/ plugins(2.1.100+ marketplace 体系,装一包带全套)
- diagram: drawio - 6 件套架构图(用户 → 主线程 → 6 个 building block,标各自职责 + 何时用)
- estimated_pages: 5 内容页(1 总览 cards + 1 关系图 pic_text + 2 重点深挖 cards/skills/agents + 1 扩展 hooks/MCP/plugins)+ 1 section_divider = 6 页

## 5. 心智 3 · 真实 case · iLovePPT v2 → v3.1

- intent: 实战段 — 用本 session 真实演进证明 6 件套都 work,Pyramid 内容 + BCG 视觉规范如何落地
- layout: pic_text + table + summary 混搭
- data: 起点 v2 单 agent → 协同设计补 Pyramid + 视觉规范对标 → 拆 3 agent + dispatcher → 模板复刻 Phase 2 → 数据 68 tests / 4 agents / 28 docs / 2 release
- diagram: matplotlib chart(commits / tests / agents 增长时间线)+ drawio(v2→v3.1 架构演进对比)
- estimated_pages: 4 内容页(1 起点痛点 + 1 演进时间线 + 1 数据成绩 table + 1 关键 learning 列表)+ 1 section_divider = 5 页

# Pyramid 自检
- [x] ① 单一顶端论点:"Claude Code 是 agentic coding platform,不只是 chat,要用 6 件套解锁"(完整推荐句:动宾 + 具体边界 "6 件套")
- [x] ② SCQA 完整:S 大家把它当 copilot / C 它 5 端可用 + agentic loop + 6 扩展件 / Q 该用什么心智 / A = 顶端论点
- [x] ③ 答案在前:cover.subtitle "50 分钟带你从'装上'到'用它跑 multi-step task'" — 含目标 + 顶端论点呼应
- [x] ④ MECE(5 章节):
    - ch1 是什么(基础)
    - ch2 跟 copilot 差别(认知校准)
    - ch3 心智 1:loop(怎么工作)
    - ch4 心智 2:6 件套(怎么扩展)
    - ch5 心智 3:真实 case(怎么落地)
    - 两两不重叠,合起来覆盖 audience 从 "没用过" 到 "知道怎么深入用"
- [x] ⑤ 纵向疑问/回答链:标题串读 "它是 agentic tool / 跟 copilot 不一样 / 它跑 agentic loop / 它有 6 件套扩展 / 真这么 work" ✓
- [x] ⑥ 字段完整:所有 section 有 intent/layout/data/estimated_pages
- [x] ⑦ action title ≤ 24 字逐条:
    - ch1 "什么是 Claude Code · 一个 agentic coding tool" 21 字 ✓
    - ch2 "≠ Copilot · 3 个根本差别" 14 字 ✓
    - ch3 "心智 1 · Agentic loop(plan → act → verify)" 23 字 ✓
    - ch4 "心智 2 · 6 件套扩展能力(它是 platform 不是 chat)" 23 字 ✓
    - ch5 "心智 3 · 真实 case · iLovePPT v2 → v3.1" 22 字 ✓

# 页数预估(校准后)
- cover(1) + toc(1) + 章节扉页 × 5(5) + 内容页(3+1+2+5+4=15) + summary(1) + closing(1) = **24 页**
- 50 min 演讲,公式 50 × 1.5 = 75 估算最大;实际 24 页节奏 ~2 min/页,留 10-15 min Q&A + demo 演示余量
- 比 v1 outline 多 1 页(因加 ch1 "是什么"),仍偏精简

# diagram_plan
- ch3:drawio - agentic loop 流程图(plan → act → verify 闭环)
- ch3:pic_text - 一次真实 loop 截图(可从本 session iLovePPT 演进过程截一张 multi-tool 调用)
- ch4:drawio - 6 件套架构图(用户 → 主线程 → 6 个 building block,标各自职责)
- ch5:matplotlib chart - commits/tests/agents 增长时间线(本 session 真数据)
- ch5:drawio - v2 单 agent vs v3.1 三 agent 对比图

# 关键校准点(基于官方文档)
- "agentic coding tool" 是官方表述,不是我编的(code.claude.com/docs/en/overview.md)
- 三层体系实际是**6 件套**(我之前漏了 hooks / MCP / plugins),官方都列为核心能力
- plugins / marketplace 是 v2.1.100+ 新加的,值得专门讲(否则听众错过这个生态)
- `/goal` 命令(v2.1.139+)是入门 demo 极好素材,体现"扔目标自己跑"
- Agent View `/agents` 命令(v2.1.139+)展示 multi-session 管理
- vs Copilot 官方角度:Full agentic loop + MCP/plugin extensibility + Opus reasoning(不是我编的)

# 引用源
- https://code.claude.com/docs/en/overview.md (产品定义)
- https://code.claude.com/docs/en/how-claude-code-works.md (agentic loop)
- https://code.claude.com/docs/en/commands.md (commands 全集)
- https://code.claude.com/docs/en/skills.md
- https://code.claude.com/docs/en/sub-agents.md
- https://code.claude.com/docs/en/hooks.md (31 events)
- https://code.claude.com/docs/en/mcp.md
- https://code.claude.com/docs/en/plugins.md
- https://code.claude.com/docs/en/changelog.md (新功能)
