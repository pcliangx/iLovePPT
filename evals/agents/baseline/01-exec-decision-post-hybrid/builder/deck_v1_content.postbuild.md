---
title: AI 4A 评审办法落地提案
subtitle: 本季度落地 AI 4A,5 阶段 ≤ 3 天,降 60% 人力
audience: executive
duration_min: 15
theme: tech_blue
output: /Users/pc2026/Documents/DevTools/iLovePPT/decks/eval-20260525-1351-01-exec-decision/builder/deck_v1.pptx
top_recommendation: 应当本季度落地 AI 4A 评审办法,5 阶段每阶段 ≤ 3 天,降 60% 人力
scqa:
  situation: 公司现行评审流程依赖人工委员会,Q4 每月评审 11-15 件,评审员人时投入 156-194h/月
  complication: Q4 三个月评审周期持续延长(8.2→11.3天),初审通过率持续下滑(42%→31%),质量与效率双双恶化,趋势未见改善拐点
  question: 如何在不增加人力的前提下,扭转评审质量与效率双下滑局面,并提供可本季度落地的决策依据?
  answer: 应当本季度落地 AI 4A 评审办法,5 阶段每阶段 ≤ 3 天,降 60% 人力
footer_meta:
  classification: INTERNAL
  project: eval-20260525-1351-01-exec-decision
  version: v1.0
based_on: deck_v1_outline.md
---

# Content

## [cover]
- title: AI 4A 评审办法落地提案
- subtitle: 本季度落地 AI 4A,5 阶段 ≤ 3 天,降 60% 人力
- prepared_by: 技术部
- date: 2026-05-25
- version: v1.0
- classification: INTERNAL

## [toc]
- 评审周期恶化 37%,人工模式已到瓶颈
- 4A 覆盖全闭环:应用/架构/认证/授权无盲区
- 5 阶段串行,全程 ≤ 8 天(含整改回路)
- AI 预审替代人工初筛,评审人力降 60%
- Q3 试点 2 业务线,Q4 全公司落地

## [section_divider]
- num: 1
- title: 现状诊断

## 1. 评审周期恶化 37%,人工模式已到瓶颈
<!-- layout: pic_text -->

![Q4 评审质量双指标恶化趋势](charts/review_trend.png)

- **周期**: Q4 均值 8.2→11.3 天,3 个月恶化 37%
- **通过率**: 初审通过率 42%→31%,下滑 11pp
- **人力**: 评审员投入 156-194h/月,峰值触顶
- **拐点**: 三月无改善信号,趋势线仍向下

> 数据:Source: _assets/raw/q4_reviews.csv(Q4 2025-10 至 12 内部数据)

## [section_divider]
- num: 2
- title: 方案范围

## 2. 4A 覆盖全闭环:应用/架构/认证/授权无盲区
<!-- layout: cards -->

- **Application(应用)**: API 边界扫描,缺失致漏洞扩大
- **Architecture(架构)**: 拓扑与单点,缺失致扩容崩溃
- **Authentication(认证)**: Token 机制,缺失致未授权访问
- **Authorization(授权)**: 最小权限,缺失致越权合规险

> 数据:Source: 4A 维度定义参照 NIST SP 800-207(零信任架构标准)[示意映射]

## [section_divider]
- num: 3
- title: 执行流程

## 3. 5 阶段串行,全程 ≤ 8 天(含整改回路)
<!-- layout: pic_text -->

![AI 4A 评审 5 阶段流程](charts/review_flow_5stage.png)

- **① AI 预审**: 自动扫描提交件,≤ 1 天
- **② 委员会预审**: AI 报告人工核校,≤ 2 天
- **③ 4A 全维评审**: App/Arch/AuthN/AuthZ,≤ 3 天
- **④ 决议裁定**: 通过/整改/驳回,≤ 1 天
- **⑤ 归档反馈**: 结论入库供 AI 持续学习,≤ 1 天

> 数据:Source: 流程 SLA 参照内部试运行推算;Q3 试点将实测验证

## [section_divider]
- num: 4
- title: 人力保障

## 4. AI 预审替代人工初筛,评审人力降 60%
<!-- layout: compare_pk -->

- left:
  - title: 现状(人工主导)
  - body: 194h/月评审员投入;初审由人工逐一核查;通过率 31%,返工占 69%;无法并行处理多件
- right:
  - title: 目标(AI 预审)
  - body: <80h/月人力目标;AI 预筛通过件直送委员会;初审通过率目标 70%+(推算)

> 数据:Source: 现状数据来自 _assets/raw/q4_reviews.csv;目标 <80h/月 基于 60% 降幅推算;初审 70%+ 参照业内 AI 辅助评审基准[示意],Q3 试点将实测

## [section_divider]
- num: 5
- title: 落地节奏

## 5. Q3 试点 2 业务线,Q4 全公司落地
<!-- layout: bullet_list -->

- Q3 M1:工具部署 + 培训
- Q3 M2-3:A/B 试点各 4 件
- Q3 末:通过率 ≥ 65% 成功
- Q4 M1:全公司正式切换
- Q4 持续:月度指标复盘

> 数据:Source: 里程碑节点由内部项目组规划[示意],CTO 本次需确认 Q3 启动授权

## [summary]
- 周期恶化 37%、通过率跌 11pp
- 4A 4 维各防一类典型风险
- 5 阶段 ≤ 8 天,人力降 60%
- Q3 试点,Q4 全公司落地

## [closing]
- subtitle: 请 CTO 批准 Q3 试点授权,技术部本周内完成工具部署启动
- next_steps:
  - action: 批准 Q3 试点(业务线 A/B)
    owner: CTO
    due: 2026-05-30
  - action: 完成工具部署 + 委员会培训
    owner: 技术部
    due: 2026-06-30
  - action: 提交试点阶段性报告
    owner: 技术部
    due: 2026-09-30
