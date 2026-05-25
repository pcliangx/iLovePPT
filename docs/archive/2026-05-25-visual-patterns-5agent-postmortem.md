# Visual Patterns 5-agent RAG Extension Postmortem

| 项 | 值 |
|---|---|
| Date | 2026-05-25 |
| Spec | `docs/archive/2026-05-25-visual-patterns-5agent-design.md` |
| Plan | `docs/archive/2026-05-25-visual-patterns-5agent-plan.md` |
| pre tag | `pre-visual-patterns-5agent`(commit 3afba5c) |
| post tag | `post-visual-patterns-5agent`(本 commit) |
| Branch | `feat/visual-patterns-5agent` |
| Total commits | 10(协议 1 + brainstorm/author×2/critic/iloveppt/audience 6 agent + CLAUDE.md 1 + postmortem 1 + spec/plan 1) |
| Phase 4 baseline | **SKIPPED**(用户决策:跳过实测,直接 postmortem template;TBD 字段未来实跑填) |

---

## 1. 迁移成果

### 1.1 协议层(Phase 1)

- `.claude/pipeline-protocol.md` 387 → 422 行(+35 行,+9%):
  - §4.3 brainstorm yaml 加 `pattern_hints_for_author`(category list)
  - §4.3 author yaml 加 `pattern_hints`(per-chapter selected/rationale)
  - §4.3 critic yaml 加 `suggested_alternative_patterns`(数组 · advisory)
  - §4.3 iloveppt yaml 加 `visual_step4.capability.rag_patterns` + `rag_fallback_used`(第 4 路)
  - §4.3 audience yaml 加 `needs_visual_redo_pages[N].suggested_alternative_pattern`(嵌入式 · advisory)
  - §3.3 加 Pattern cherry-pick gate(主线程必须展示用户决定)
- `.claude/skills/pptx-deck/content-writing.md`:outline.md schema per-chapter 加 `pattern_hints` 字段(selected/rationale/alternatives)

### 1.2 Agent 改造(Phase 2 · 6 commits)

| agent | 改了什么 |
|---|---|
| **iloveppt-brainstorm** | Step 3.5 新增:dispatch_author 前跑 search.sh hybrid top-5,取 category 列表,Edit brief.md frontmatter `pattern_hints_for_author`,dispatch_author yaml 同步透传 |
| **iloveppt-author** Stage C | Step 1A.5 新增:写完 outline 后对每章 search.sh hybrid top-5,LLM 选 1-2(优先命中 brainstorm category),Edit outline.md per-chapter `pattern_hints`,yaml 数组同步 |
| **iloveppt-author** Stage D/rework | Step 1B + Step 1D 加 `accept_alternative_pattern` 分支:user_response 含 `{page, suggest}` → 改 outline pattern_hints + 改 content `<!-- pattern: -->` 注释 + 重 Pyramid 自检 |
| **iloveppt-critic** | 维度 5 新增:Read author selected pattern.yaml 验匹配 → search.sh 重跑 top-5 → 选 1 alternative;yaml 加 `suggested_alternative_patterns`(数组 advisory 不计 verdict) |
| **iloveppt** | Step 4.2.5 新增:三路降级 + visual_qa.passed<14/17 + library 可用时 → search.sh top-3,preview.png 作 hero(layout 支持时)或 reference_only;Step 5 yaml 加 visual_step4 字段 |
| **iloveppt-audience** | Step 3.5 新增:triage 后对每个 needs_visual_redo 页 search.sh top-3,选 1 alternative 嵌入 `needs_visual_redo_pages[N].suggested_alternative_pattern`(纯 advisory 不影响 overall_score) |

### 1.3 主线程(Phase 3)

- `CLAUDE.md` 主线程派发规则段加 Pattern cherry-pick gate 提示(链接到 pipeline-protocol §3.3)

### 1.4 关键不变量

- author 唯一**写者**(可改 outline/content),其他 4 agent 都是**评者**(只给 advisory,不改 .md)
- 主线程是**仲裁人**:任何 alternative 必须展示用户 → 用户拍板才派 author rework
- 统一 SOP:`Bash bash search.sh --mode hybrid --top-k 5 --format json`
- 5 处降级:任一 agent search.sh 失败 → 字段为空/null,**不阻塞流水线**

---

## 2. Phase 4 实测结果

**SKIPPED**(用户决策:hybrid Phase 4 已烧 600k token / 25 分钟,本 spec 改造性质是 mechanical prompt 增量,static 验证已 sufficient;Phase 4 实测留到下一次跑实际 deck 时滚动收集)。

未实测的验证维度(TBD):

| 维度 | 期望 | 实测 |
|---|---|---|
| brainstorm brief.md `pattern_hints_for_author` 命中数 | 3-5 个 category | TBD |
| author outline `pattern_hints` 命中 search.sh top-5 | 100%(LLM 必须从 top-5 选) | TBD |
| critic Stage C/D alternative 数量 | 0-N(取决于 author 选准度) | TBD |
| iloveppt visual_step4.rag_fallback_used | ≥ 1 个(若三路全 disable + 该页 visual_qa <14) | TBD |
| audience needs_visual_redo_pages[N] alternative | 仅 needs_visual_redo 页给 | TBD |
| 主线程 cherry-pick gate 触发数 | 0-N(取决于 critic/iloveppt/audience advisory 数) | TBD |
| 用户接受 alternative 的比例 | 50-100%(若库 quality 高);< 50%(若 21 库太小) | TBD |
| 总 token 增量 | ~50k / deck(估算,5 处 RAG × ~3k token + LLM 选择推理) | TBD |
| Wall-clock 增量 | ~30s-60s / deck(search.sh 调用 + LLM 选择) | TBD |

**实测触发时机**:下次跑实际 deck(非 fixture)时,记录实际数据填回此 postmortem 表。

---

## 3. 关键 findings(实测中暴露的问题)

(待实测后填。预期方向):

### F1(预测): search.sh 命中率受 library 21 patterns 限制
- 现象:critic / audience 大量给同样几个 patterns 作 alternative(库小天花板)
- 缓解:扩库 spec(已标 follow-up)

### F2(预测): cherry-pick gate 频繁触发可能拖慢用户
- 现象:每个 alternative 都要用户答 → 单 deck 可能 cherry-pick 5-10 次
- 缓解:UI 层批量展示(主线程一次问 N 个,不是 N 次问 1 个)

### F3(预测): hybrid 模式 yaml schema 偏差延续(继承 hybrid F4 finding)
- 现象:5 agent return yaml 字段名 / 结构跟 §4 schema 偏差(已见 hybrid Phase 4)
- 缓解:hybrid postmortem F4 后续 spec 一起解决(structured output / JSON schema)

---

## 4. Audit GAP 修复情况

| Audit GAP / Spec 目标 | post-visual-patterns 状态 | 备注 |
|---|---|---|
| RAG 库利用率(1 agent → 5 agent) | **直接修复**(static 层面) | 实际命中率待实测 |
| Audit B4 并行而非串行 | 仍 GAP | 不在本 spec scope |
| Audit D1-D5 效率 | 不变 | 本 spec 不涉及 |
| Audit E4 MAST 14 项 checklist 化 | 不变 | 不在本 spec scope |
| Audit G1-G6 可观测性 | 不变 | 不在本 spec scope |
| hybrid F4 yaml schema 偏差 | 延续 | 跟 hybrid spec 一起后续解决 |

---

## 5. 下一步(post-merge follow-up,按紧迫程度)

### 5.1 高优先级(本次 merge 后立刻启动)

1. **patterns 库扩库 spec**(独立 PR,2-3 周)
   - patterns 21 → 50-100
   - INDEX.md 重组按 content intent 分类(不只按视觉结构)
   - 扩库流程:`library/visual-patterns/ingest_workflow.md` 已有 → 跑 N 次 ingest
   - **本 spec 的隐性前置**:5 agent 命中率受 library 大小限制

2. **第一次实际 deck 跑通**(非 fixture,真实用户场景)
   - 收集 Phase 4 TBD 字段实数据
   - 回填本 postmortem § 2 表 + § 3 findings

### 5.2 中期(1 个月内)

3. **structured output / JSON schema 强制校验**(hybrid F4 后续 spec)
   - 跟本 spec 5 处新字段一起一次性校验
   - 解决 5 agent yaml schema 偏差问题

4. **cherry-pick UI 批量化**(若 F2 实测严重)
   - 主线程一次性展示所有 alternative,而不是逐个问

### 5.3 长期(平台层 / backlog)

5. **runtime.log 平台层 telemetry**(hybrid F3,非项目可控)
6. **章节并行拓写**(audit B4 Layer 2)

---

## 6. 决策记录

| 决策点 | 选择 | 备注 |
|---|---|---|
| patterns 库前置 | 5 agent 一次性上,不等扩库 | 用户接受 21 库风险;扩库独立 follow-up |
| 决策权 | author 唯一写,其他 advisory + 用户 cherry-pick | 避免 MAST FM-1.3 step repetition |
| RAG 调用 | 统一 SOP search.sh hybrid top-k=5 | 5 agent 一致性高 |
| Phase 4 实测 | SKIPPED,留到下次实跑滚动填 | static 已 sufficient + hybrid Phase 4 经验:fixture 烧 600k token |
| Postmortem 填充时机 | 本 commit template,实测后回填 | 不阻塞 merge |

---

## 7. 总结

本 spec **完成 mechanical 层 5 agent RAG 集成**:协议层 5 处 yaml schema + 1 处 gate / 5 agent prompt 段全加 / 主线程协议更新 / 文档同步。**故意跳过 Phase 4 实测**(成本不值,留到自然跑实际 deck 滚动收集)。

**真正价值**不在本次 commit,而在:
- 给 author 一个**写前看库**的反射弧(不是事后才发现 pattern 选错)
- 给 critic 第 5 维度的 second-opinion 视角(对照库验 author 选准没)
- 给 iloveppt 第 4 路 fallback(三路全失败不再 0 视觉)
- 给 audience 给 iloveppt 的"具体配方"(不再"加 icon"空话)
- 给 brainstorm 提前预判 deck 视觉走向

**完整效果**取决于 **patterns 库大小 + INDEX.md quality**(本 spec 隐性前置)。21 库下保守期望命中率 30-50%;扩到 50+ 后期望 60-80%。

下次跑实际 deck 时填回 § 2 / § 3 数据,真正 close loop。
