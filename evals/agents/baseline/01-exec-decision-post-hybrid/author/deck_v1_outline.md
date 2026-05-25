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
---

# Outline

## 1. 评审周期恶化 37%,人工模式已到瓶颈
- intent: 用 Q4 实测数据建立紧迫感;让 CTO 认同"现状不可持续"(SCQA S+C)
- layout: table
- data: review_days_avg 8.2→9.5→11.3天,passed_first_round_pct 42%→38%→31%,reviewer_hours 156-194h/月,reviews_count 11-15件/月
- diagram: matplotlib:line_chart(评审周期趋势线,3月数据)

## 2. 4A 覆盖全闭环:应用/架构/认证/授权无盲区
- intent: 定义 AI 4A 评审的覆盖边界,让 CTO 理解"4A"是什么,为什么这 4 个维度构成完整闭环
- layout: cards
- data: 4 个 A = Application/Architecture/Authentication/Authorization
- diagram: 无

## 3. 5 阶段串行,每阶段 ≤ 3 天,全程 ≤ 1 周
- intent: 拆解 5 阶段流程的操作细节,让 CTO 看到"怎么跑"并相信 ≤3天/阶段可达
- layout: pic_text
- data: 5 阶段流程,每阶段 ≤ 3 天,卡点不超 1 周
- diagram: drawio:flow(5阶段水平流程图,含阶段名+时间 SLA)

## 4. AI 预审替代人工初筛,评审人力降 60%
- intent: 量化人力收益;compare_pk 呈现"现状 vs 目标"鲜明对比,让 CTO 看到 ROI
- layout: compare_pk
- data: 现状 reviewer_hours 194h/月,目标 <80h/月;初审通过率从 31% 回升至 70%+
- diagram: 无

## 5. Q3 试点 2 业务线,Q4 全公司落地
- intent: 给出具体落地时间轴和成功判断标准,让 CTO 有清晰的决策抓手
- layout: bullet_list
- data: Q3:2个业务线试点;Q4:全公司;关键 milestone 节点
- diagram: 无

# Pyramid 自检

- [x] ① 单一顶端论点:top_recommendation 字段非空,是完整推荐句(本季度落地 AI 4A + 5阶段≤3天 + 降60%人力,动宾结构+边界清晰)
- [x] ② SCQA 完整:四字段全部非空;C(评审周期恶化+通过率下滑)是真实冲突不是S的复述;A==顶端论点
- [x] ③ 答案在前:cover.subtitle 已含顶端论点精简版;5 个章节标题均是结论句,非话题标签
- [x] ④ MECE:共 5 章节(3-5 范围内);Ch1=现状诊断/Ch2=方案范围/Ch3=执行流程/Ch4=组织人力/Ch5=落地节奏,两两不重叠,加起来完整支撑顶端论点;排列方式=演绎序(问题→范围→流程→保障→时间轴)
- [x] ⑤ 纵向疑问链:Ch1"现状恶化"→引出Ch2"4A覆盖什么"→Ch3"怎么跑"→Ch4"人力怎么保障"→Ch5"何时落地",串读成完整故事
- [x] ⑥ 字段完整:frontmatter 含 title/subtitle/audience/duration_min/theme/output/top_recommendation/scqa/footer_meta,各字段均非空
- [x] ⑦ 全部 action title ≤ 24 字:Ch1(15字)✓ Ch2(17字)✓ Ch3(17字)✓ Ch4(18字)✓ Ch5(16字)✓
