# Agent Eval 评分标准

跑完 1 个 fixture 的完整流水线后,按下面 5 维度评分,每维 1-10 分,总分 50。

---

## 维度 1 · Brief 准确度(brainstorm 产出)

**评的是 `brief.md`**。看 brainstorm 收齐字段是否准 + 是否跟 fixture 预期一致。

| 分 | 标准 |
|---|---|
| 10 | 6 必填字段全收齐,top_recommendation 是完整推荐句(动+宾+边界),asset_inventory 完整 |
| 8-9 | 字段齐,top_recommendation 略不够锐 |
| 6-7 | 缺 1 个字段,或 audience 判断有偏差 |
| 4-5 | 缺 2 个字段,或 top_recommendation 是议题陈述非推荐 |
| 1-3 | 缺 3+ 字段,或 brainstorm 替用户填了关键字段 |

**重点 check**:
- `top_recommendation` 是结论还是议题?
- `audience` 跟 fixture 预期是否一致?
- `presentation_mode` 是否明确问过?

---

## 维度 2 · Outline 结构(author Stage C 产出)

**评的是 `deck_v1_outline.md`**。Pyramid 5 件套 + MECE + 章节数。

| 分 | 标准 |
|---|---|
| 10 | Pyramid 7 项全过,3-5 章节,MECE 严格,每条 action title 是结论句 |
| 8-9 | 7 项过 6 项 / 章节略多或少 / 1 条 action title 是话题 |
| 6-7 | 章节有 1-2 处重叠 / 2-3 条 action title 是话题 |
| 4-5 | MECE 失败 / 多数 action title 是话题 / 章节排列方式混乱 |
| 1-3 | Pyramid 自检完全跑偏 / 缺 SCQA / 章节是话题堆叠 |

**重点 check**:
- 章节标题串读能否讲完整故事(ghost deck test)?
- 顶端论点是否在 cover.subtitle 出现(BLUF)?
- 是否有 footer_meta 默认填好?

---

## 维度 3 · Content 拓写(author Stage D 产出)

**评的是 `deck_v1_content.md`**。字数 + 数字密度 + Source 引文。

| 分 | 标准 |
|---|---|
| 10 | 所有 layout 字数严守(speaker / handout 对应表)+ 数字 > 形容词 + 每数据 page 有 Source 引文 |
| 8-9 | 字数 1-2 项轻微超标 / 1-2 处形容词没换数字 |
| 6-7 | 字数 3-5 项超 / 多处形容词堆 / 缺 Source 引文 |
| 4-5 | 字数大面积超标 / 引入 brief 外的事实 / 配图缺失 |
| 1-3 | 严约束违反(引入新论点 / 没引文 / 字数乱) |

**重点 check**:
- 抽 3 页测字数(cards body / bullet items / summary)
- 数据 page 是否有 `> 数据:Source: ...`
- 是否引入 brief 没说的事实?

---

## 维度 4 · Critic 评审深度(critic 产出)

**评 `critic_report_C.md` + `critic_report_D.md`**。看 critic 是不是真"评审员"还是"checklist runner"。

| 分 | 标准 |
|---|---|
| 10 | 14 项 checklist 全跑 + 5 维度判断性 ≥ 5 个 issue(高质量带三要素)+ verdict 合理(三档区分清) |
| 8-9 | 14 项全跑 + 5 维度 3-4 个 issue + verdict 合理 |
| 6-7 | 14 项跑了 + 5 维度只 1-2 个 issue / 部分 issue 没三要素 |
| 4-5 | 14 项有遗漏 / 5 维度没跑 / issue 是空话 |
| 1-3 | 只是 checklist 打勾 / verdict 直接 pass 没 evidence |

**重点 check**:
- 5 维度判断性 issue 是否带 evidence(具体引文 / 出处)?
- 每个 issue 是否有 severity + impact + suggestion 三要素?
- 三档 verdict 是否合理(不是非黑即白)?

---

## 维度 5 · 最终 deck 质量(audience overall_score)

**直接用 audience agent 第 1 轮的 `overall_score`**(0-10 分)。

这是端到端的产物质量信号。9+ 算优秀,7-8 算合格,< 7 需要返工。

**重点 check**:
- audience 给的 4 维度评分(comprehension_5s / info_density / visual_appeal / flow_coherence)各是多少?
- top_3_must_fix 是否合理?
- 是否区分了 needs_author_rewrite / needs_visual_redo / needs_theme_fix?

---

## 总分 50 的 baseline 解读

| 总分 | 性质 |
|---|---|
| 45-50 | 优秀,改动 prompt 后达这个分说明系统级提升 |
| 40-44 | 良好,baseline 应该在这个区间 |
| 35-39 | 合格,有改进空间但可用 |
| 30-34 | 需关注,通常某 1-2 维显著拉低 |
| < 30 | 系统性问题,某 agent 大幅 regression |

---

## 评分人是谁

两种模式:

### 模式 A · 人工评(主)

跑完 fixture 后,人工对照本 rubric 给每维打分。每个 fixture 大约 15-20 分钟评完。

### 模式 B · LLM 评(辅,可重复)

把 fixture 跑完的所有产出 + 本 rubric 喂给一个独立的 Claude Sonnet / Opus 实例,让它评分。

LLM 评的好处:**可重复 + 快**。坏处:**对"判断性"维度评不准**(尤其维度 4 critic 评审深度)。

**推荐**:维度 1/2/3/5 用 LLM 评(可量化);维度 4 必须人工评。
