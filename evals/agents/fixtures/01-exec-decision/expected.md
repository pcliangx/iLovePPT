# Fixture 01 · Expected Output

跑完 fixture 01 后,按下面这些"必出 / 应有"项检查产出 → 给 5 维度评分。

## brief.md 应有

```yaml
audience: executive
duration_min: 15
top_recommendation: 应当本季度落地 AI 4A 评审办法,5 阶段每阶段 ≤ 3 天,降 60% 人力
theme: tech_blue
presentation_mode: speaker
asset_inventory:
  - csv: _assets/raw/q4_reviews.csv
  - image: _assets/refs/current_arch.png
SCQA 线索:推断出来,Situation/Complication 应跟"AI 评审耗时增加 + 通过率下降"相关
```

## outline.md 应有

- **章节数**:3-5(典型 4 章)
- **章节标题**:每条结论句(✗ "AI 评审现状" / ✓ "AI 评审周期已从 8 天涨到 11 天")
- **Pyramid 7 项自检**全过(或 unchecked 项有豁免)
- **footer_meta** frontmatter 默认填(classification: INTERNAL / project: <slug> / version: v1.0)
- 章节排列方式选**时间序**或**演绎序**(executive 喜欢 "为什么 → 怎么做 → 落地节奏")

**典型期望章节**(参考):
1. 当前 AI 评审周期失控(背景 + 数据)
2. 4A 覆盖范围 + 责任分工(范围)
3. 5 阶段串行 + 阶段 ≤ 3 天(方案)
4. Q3 试点 + Q4 全公司(节奏)
+ summary(收口结论)

## content.md 应有

- 总页数:15 min × 1.5 ≈ **22 页 ± 3**(包括 cover/toc/section_divider/summary/closing)
- **每数据 page 有 `> 数据:Source: ...` 引文**(Q4 数据 page 必须)
- **字数遵守 speaker mode**(cards body ≤ 18 / bullet items ≤ 12)
- 至少 1 张图:Q4 评审趋势 chart(matplotlib 出)+ 现有架构图(参考)
- summary 给 3-5 条带数字的结论(✗ 复列章节名)

## critic_report_C.md / critic_report_D.md 应有

- **Section A 7 项全 evidence-based**(每项引文 + 出处)
- **Section B 适用项跑齐**(Stage C 跑 B1/B6/B7;Stage D 跑全 7 项)
- **5 维度判断性 issue ≥ 3 个**(带三要素)
- **verdict 合理**:
  - Stage C 期望 `pass_with_notes`(初稿可能维度 3 措辞会有 med)
  - Stage D 期望 `pass` 或 `pass_with_notes`(经 1 轮调整后)

## builder/visual_report_r1.md 应有(iloveppt-builder Step 4 产出)

- **icon_prefix 单一**:全 deck icon 同一套(lucide / phosphor / tabler / heroicons 选一)
- **visual_edits[] count**:典型 4-8 处(cards 加 icon + section_divider 加装饰)
- **rolled_back[] count**:理想 0(或 1-2 是自检 fresh Read PNG 后变糟回滚)
- **`visual_step4.capability` 三路状态完整**(cairosvg / unsplash / brand_assets;RAG 第 4 路已退役,见 [pipeline-protocol.md §3.3](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md))
- **风格统一**:染色 BRAND_PRIMARY / GRAY_700(helpers.py SSOT)

## audience_review.md 应有

- **按 executive profile 评分**(info_density 阈值偏严苛,visual_appeal 要求高)
- **overall_score ≥ 8.5**(executive 视角苛刻,本 fixture 目标 8.5+)
- 三类反馈分流清晰(若有 issue)
- 4 维度评分细节(comprehension_5s / info_density / visual_appeal / flow_coherence)

## 评分锚点

按 score_rubric.md 5 维度评:

| 维 | 这个 fixture 期望 |
|---|---|
| 1 Brief 准确度 | ≥ 8(top_rec 是完整推荐句,executive 不能错填 general) |
| 2 Outline 结构 | ≥ 8(MECE 不重叠,4 章节合理) |
| 3 Content 拓写 | ≥ 7(speaker 字数严守,数据 Source 引文必有) |
| 4 Critic 评审深度 | ≥ 7(判断性 issue 至少 3 个) |
| 5 Audience overall | ≥ 8.5(executive 视角) |
| **总分** | ≥ **38** |

总分 < 36 算这个 fixture 退化。
