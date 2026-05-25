# Visual Patterns RAG · 5-agent 调用扩展设计

| 项 | 值 |
|---|---|
| Date | 2026-05-25 |
| Status | Approved(设计阶段),待 implementation plan |
| 关联 spec | `docs/archive/2026-05-25-hybrid-team-subagent-migration-design.md`(前置:hybrid 架构已迁移) |
| 关联 postmortem | `docs/archive/2026-05-25-hybrid-migration-postmortem.md`(本 spec 是 hybrid 后第一个质量提升 spec) |
| 涉及范围 | 5 agent prompt + pipeline-protocol.md + content-writing.md + CLAUDE.md |
| 前置 anchor tag | `pre-visual-patterns-5agent`(Phase 0 创建) |
| 完成 anchor tag | `post-visual-patterns-5agent`(Phase 4 通过后创建) |

---

## 1. 背景与动机

### 1.1 触发问题

iLovePPT 的 `library/visual-patterns/`(21 patterns + hosted multimodal RAG)是输出**高质量 PPT** 的关键知识库。但当前**只有 author 一个 agent 在 Stage D / Step 1C 拓 content 时查 RAG**,其他 4 agent(brainstorm / critic / iloveppt / audience)完全不接入。

具体局限:
- **太晚**:Stage D 才查,Stage C outline 章节论点 + layout 已写死,选错的 pattern 来不及救
- **单视角**:author 自己选 pattern 没人 second-opinion;Phase 4 实测 page 8 chart HTML 裸露,本质是 author 选 pattern + iloveppt 渲染时没人复核 pattern 适配性
- **iloveppt Step 4 被动**:三路降级(iconify / Unsplash / brand)全 disable 时,RAG 库 21 个 preview.png 完全没作 fallback
- **audience 盲修**:needs_visual_redo 只能说"该页视觉单调",不知道库里有哪些 pattern,visual_redo 反复试

### 1.2 决策路径

经 4 轮 brainstorming 对齐:

| 决策点 | 选择 | 理由 |
|---|---|---|
| 前置:patterns 库 21 个够不够? | **5 agent 一次性上,不等扩库**(选 C) | 用户接受 21 库下 critic/audience 命中率不足风险 |
| 决策权归属(避免 step repetition) | **author 唯一写者,其他 agent 只 advisory + 用户 cherry-pick 才改** | author 是写作者本身;Lock-on-first 太死板,但 advisory 走用户拍板 |
| RAG 调用形式 | **统一 SOP:`search.sh --mode hybrid --top-k 5`** | 同输入同输出,5 agent 决策一致性高 |

### 1.3 不采用其他方案的理由

- **不选"先扩库后上 5 agent"**(选项 A):扩库是独立大项目(2-3 周),阻塞当下质量提升
- **不选 vote / hierarchy 决策权**:vote 劣币驱良币;hierarchy 把 audience(最能看出 pattern 错没错)放最低优先级,违反设计意图
- **不选混合 SOP(text + RAG)**:agent prompt 复杂,中间状态不一致
- **不选 image-only RAG(audience)**:audience × 14 页 × image RAG 太烧 token

---

## 2. 架构总览

### 2.1 5 agent 各自调用点

```
                  ┌──────────────────────────────────────────────────┐
                  │  统一 SOP:Bash search.sh --query <intent>        │
                  │             --mode hybrid --top-k 5 --format json│
                  │  全 5 agent 复用,确保同输入同输出                │
                  └──────────────────────────────────────────────────┘
                                          │
                                          ▼
brainstorm 收完 brief → 末尾扫一次 → brief.md 加 pattern_hints_for_author[] (3-5 category)
                                          │
                                          ▼ (dispatch_author 透传)
author Stage C 写 outline → 每章扫一次 → outline 加 pattern_hints[id] (1-2/章) ✏️ 可改
                                          │
                                          ▼ (Task critic Stage C)
critic Stage C 评 outline → 维度 5 "pattern 适配性" → suggested_alternative_patterns (advisory)
                                          │
                                          ▼ (Task author Stage D, rework 时可接受 alternative)
author Stage D 拓 content → 用 outline pattern_hints → content.md 嵌 <!-- pattern: <id> --> ✏️ 可改
                                          │
                                          ▼ (Task critic Stage D)
critic Stage D 评 content → 同 Stage C 维度 5
                                          │
                                          ▼ (Task iloveppt Step 0-4)
iloveppt Step 2 → 看 <!-- pattern --> → Read pattern.yaml → 按 fallback_rendering 渲染
iloveppt Step 4 → 低 visual_qa 页扫一次 → RAG 第 4 路 fallback (iconify/Unsplash/brand 之后)
                                          │
                                          ▼ (Task audience)
audience needs_visual_redo triage → 扫一次 → suggested_alternative_pattern (advisory)
                                          │
                                          ▼
主线程拿到 suggested_alternative_* → 展示给用户 cherry-pick
                                          │
              ┌───────────────────────────┴───────────────────────────┐
              ▼                                                       ▼
        用户答"改"                                              用户答"不改"
              │                                                       │
              ▼                                                       ▼
   Task author (stage=C_rework / D_rework)                继续派下一棒
   user_response 含 accept_alternative_pattern: <new-id>
              │
              ▼
   author 改 outline / content + 更新 pattern_hints + 重嵌注释
              │
              ▼
   下游 critic / iloveppt / audience 重跑(若已通过的 stage,需重派)
```

### 2.2 写权 vs 评权

| agent | 对 pattern 的权限 |
|---|---|
| **author** | **唯一写者** — Stage C/D/rework 任何派发都可改 outline `pattern_hints` + content `<!-- pattern -->` 注释 |
| **brainstorm** | 只**给候选 category**(brief.md 字段),不指 id;author 可参考也可不参考 |
| **critic** | 只在 yaml 给 `suggested_alternative_patterns`,**不改 .md** |
| **iloveppt** | Step 2 按现有注释渲染;Step 4 给 `rag_fallback_used`(辅助资产),**不改 .md** |
| **audience** | 只在 yaml triage 字段给 `suggested_alternative_pattern`,**不改 .md** |

### 2.3 主线程仲裁

- 任何 critic / iloveppt / audience yaml 含 `suggested_alternative_pattern(s)` → 主线程**永远展示给用户 cherry-pick**,不替用户决定
- 用户答"改" → 主线程派 author rework + user_response 含 `accept_alternative_pattern: <id>`
- 用户答"不改" → 继续派下一棒

---

## 3. 协议层 schema 改动

### 3.1 `pipeline-protocol.md` §4 yaml schema 新增字段

**brainstorm dispatch_author yaml**:
```yaml
agent: iloveppt-brainstorm
next_action: dispatch_author
artifacts:
  - path: <brief.md abs>
    kind: brief_md
brief_summary: <...>
pattern_hints_for_author:           # 新增 · category list(3-5)
  - process
  - cycle
  - comparison
```

**author Stage C yaml**:
```yaml
agent: iloveppt-author
next_action: ask_user_for_outline_approval
stage: C
artifacts:
  - path: <outline.md abs>
    kind: outline_md
pyramid_self_check: passed
pattern_hints:                      # 新增 · per-chapter
  - chapter: 1
    selected: [process-5-step-linear]
    rationale: "5 阶段流程,linear pattern 匹配"
  - chapter: 2
    selected: [cards-flag-4]
    rationale: "4A 4 维并列,cards 匹配"
```

**author Stage D yaml** 同上(rework 时若接受 alternative 也更新 `pattern_hints`)。

**critic Stage C/D yaml**(新增 advisory):
```yaml
agent: iloveppt-critic
verdict: pass_with_notes
suggested_alternative_patterns:     # 新增 · advisory
  - page: 3
    current: cards-flag-4
    suggest: matrix-2x2
    reason: "4A 不是并列而是因果矩阵(2 类风险 × 2 类应对),matrix-2x2 更准"
```

**iloveppt yaml**:
```yaml
agent: iloveppt
next_action: dispatch_audience
visual_step4:
  capability:
    cairosvg: disabled
    unsplash: disabled
    brand_assets: none
    rag_patterns: 21_available      # 新增 · 第 4 路状态
  scanned_4_categories: [...]
  rag_fallback_used:                # 新增 · 4th fallback
    - page: 6
      pattern_id: cards-flag-3
      preview_path: library/visual-patterns/patterns/cards-flag-3/preview.png
      usage: hero_reference
```

**audience yaml**:
```yaml
agent: iloveppt-audience
next_action: needs_visual_redo
triage: needs_visual_redo
needs_visual_redo_pages:
  - page: 8
    suggested_alternative_pattern:  # 新增 · advisory
      current: pic_text + drawio_chart
      suggest: process-5-step-linear
      reason: "draw.io HTML 标签裸露,直接换内置 pattern preview 一击命中"
```

### 3.2 `brief.md` frontmatter schema 新增

```yaml
---
deck_slug: <slug>
audience: executive
duration_min: 15
top_recommendation: <...>
# ...其他原字段
pattern_hints_for_author:           # 新增
  candidates: [process, cycle, comparison]
  source: brainstorm_search_top_5_categories
---
```

### 3.3 `outline.md` per-chapter schema 新增

(更新 `.claude/skills/pptx-deck/content-writing.md` 的 outline.md schema 描述)

```yaml
## 1. <action title>
- intent: <...>
- layout: <13 内置 layout>
- data: <...>
- diagram: <...>
- pattern_hints:                    # 新增
    selected: <pattern-id>
    rationale: <...>
    alternatives: [<id>, <id>]      # search.sh top-5 里没选的 4 个,给用户审 outline 时看候选
```

### 3.4 `content.md` 内嵌注释 schema(无改动,已有)

```markdown
## 1. <action title>
<!-- layout: cards -->
<!-- pattern: cards-flag-4 -->      # 已有,author Stage D 嵌入,iloveppt 读
- ...
```

### 3.5 `pipeline-protocol.md` §3.3 加 cherry-pick gate

新增 Gate 规则段:
```
任一 critic / iloveppt / audience yaml 含 suggested_alternative_pattern(s)
  → 主线程必须展示给用户(不允许跳过 / 主线程自决)
  → 用户答"改" → Task author rework + user_response 含 accept_alternative_pattern: <id>
  → 用户答"不改" → 继续派下一棒
  → 若用户答"改"且改动发生在 audience 阶段(deck 已 build)→ author rework + 必须重派 critic Stage D + 重派 audience
```

---

## 4. 5 agent 具体改造点

| # ROI 序 | agent | 加在哪 | 改动模板 |
|---|---|---|---|
| **1** | **author Stage C** | Step 1A 写完 outline 后,Pyramid 自检之前 | 加 Step 1A.5:对每章 `Bash search.sh --query "<章节 intent>" --mode hybrid --top-k 5 --format json` → LLM 从 5 候选选 1-2 个 → 写进 outline `pattern_hints` 字段 |
| **2** | **audience triage** | needs_visual_redo 生成 triage 时 | 对每个 needs_visual_redo 页 `Bash search.sh` → yaml `needs_visual_redo_pages[N].suggested_alternative_pattern` |
| **3** | **critic Stage C + D** | checklist 之后,4 维度判断之前 | 加 "维度 5 · pattern 适配性":对每章 Read library/visual-patterns/patterns/<author 选的 id>/pattern.yaml → 验证 intent 是否匹配 → 若有不匹配,`Bash search.sh` 找 alternative → yaml `suggested_alternative_patterns` |
| **4** | **iloveppt Step 4** | iconify/Unsplash/brand 三路降级**之后** | 对低 visual_qa 页(passed < 14/17)→ `Bash search.sh --query "<page intent>" --mode hybrid --top-k 3` → 拿 `patterns/<id>/preview.png` 作 hero 嵌入 → yaml `visual_step4.rag_fallback_used` |
| **5** | **brainstorm** | dispatch_author 之前(brief.md gate 完成后) | 加 Step 3.5:`Bash search.sh --query "<top_recommendation 关键词>" --mode hybrid --top-k 5 --format json` → parse 取 category list → 写 brief.md frontmatter `pattern_hints_for_author` |
| **6** | **author Stage D + D-rework** | Step 1C 拓 content 时(已有逻辑)+ rework 时新加 | 已有:看 outline `pattern_hints` 嵌 `<!-- pattern: <id> -->`。**rework 时新加**:若 user_response 含 `accept_alternative_pattern: <new-id>` → 改 outline `pattern_hints` + 改 content 注释 + Pyramid 自检 |

### 4.1 关键不变量

- brainstorm / critic / iloveppt / audience **只调 search.sh + 写 yaml 字段**,**不改任何 .md 文件**
- 只有 author 改 .md(outline + content)
- 主线程拿到 `suggested_alternative_pattern(s)` 后**展示给用户**,不替用户决定
- author 任何 stage 派发都可改 pattern(不被 Lock)

### 4.2 字段命名规则(单数 vs 复数)

- **`suggested_alternative_patterns`**(critic 复数,数组):critic 评全 outline / content,可能跨多页给多个 alternative
- **`suggested_alternative_pattern`**(audience 单数,嵌在每个 page triage block 里):audience triage 是 per-page 结构,每页最多给 1 个 alternative
- 主线程 parse 时按 yaml block 所属层级判断,不会冲突

### 4.2 Token 估算(每 deck 增量)

| agent | 触发 | 估算 |
|---|---|---|
| brainstorm | dispatch_author 前 1 次 search.sh | ~3k |
| author Stage C | N 章 × search.sh | ~15k(5 章假设) |
| critic Stage C/D | 各 N 章,若有 mismatch | ~15k |
| iloveppt Step 4 | M 低分页 × search.sh | ~9k(3 页假设) |
| audience | N 个 needs_visual_redo 页 × search.sh | ~9k(3 页假设) |
| **总增量** | — | **~50k token / deck(占 hybrid 实测 600k 总量 ~8%)** |

---

## 5. 实施 Phase

### Phase 0:安全网(10 分钟)

- `git checkout -b feat/visual-patterns-5agent`
- `git tag pre-visual-patterns-5agent`(anchor)
- `python3 -m pytest tests/ -q` 确认 72/72 baseline

### Phase 1:协议层(半天)

- `pipeline-protocol.md` §4 加新 yaml 字段(brainstorm/author/critic/iloveppt/audience 5 处)
- `pipeline-protocol.md` §3.3 加 cherry-pick gate 流程
- `.claude/skills/pptx-deck/content-writing.md` 加 outline.md per-chapter `pattern_hints` schema
- commit:`feat(protocol): add visual-patterns RAG 5-agent schemas + cherry-pick gate`

### Phase 2:5 agent prompt 改造(1-1.5 天,**按依赖顺序**,不是按 ROI)

> 注:§4 表是 ROI 顺序(展示哪个 agent 收益最大);Phase 2 实施必须按**依赖顺序**(下游 agent 用上游字段)。

- **Task 2.1 brainstorm**(Step 3.5 新增 RAG 预选,brief.md frontmatter `pattern_hints_for_author`)
- **Task 2.2 author Stage C**(Step 1A.5 新增 RAG 选 hints,outline per-chapter `pattern_hints`;依赖 brainstorm 字段)
- **Task 2.3 author Stage D + D-rework**(已有 Step 1C 嵌注释逻辑 + rework 接受 `accept_alternative_pattern`)
- **Task 2.4 critic Stage C/D**(维度 5 pattern 适配性 + `suggested_alternative_patterns`;依赖 author outline 字段)
- **Task 2.5 iloveppt Step 4**(第 4 路 rag_fallback;独立)
- **Task 2.6 audience triage**(needs_visual_redo `suggested_alternative_pattern`;独立)
- 每个 task 一个 commit

### Phase 3:主线程协议(半天)

- `CLAUDE.md` 派发规则段提示 cherry-pick gate
- 加 "cherry-pick 阶段" 说明:任何 alternative_pattern 必须问用户

### Phase 4:验证(30 分钟)

- 跑同一 fixture `01-exec-decision`
- 对比 vs `evals/agents/baseline/01-exec-decision-post-hybrid/`
- 验收维度:
  - brainstorm brief.md 含 `pattern_hints_for_author`
  - author outline `pattern_hints` 命中 search.sh top-5
  - critic 至少给 1 个 `suggested_alternative`(因 21 库 quality 不足,可能命中)
  - iloveppt Step 4 `visual_step4.rag_fallback_used` 有数据(本次 hybrid 跑下来 Step 4 三路全降级,RAG 第 4 路就应该被触发)
  - audience triage 含 `suggested_alternative`
  - 端到端跑通,产物完整
- `git tag post-visual-patterns-5agent`
- 删 anchor branch

### Phase 5:postmortem(15 分钟)

- 写 `docs/archive/2026-05-26-visual-patterns-5agent-postmortem.md`
- 记录:
  - 命中率(author 选的 pattern 跟 RAG top-5 重合度)
  - alternative 数量(critic / iloveppt / audience 各自给了几个)
  - 用户接受 alternative 的比例
  - token 增量实测
  - hybrid postmortem 同样格式,findings 滚动累积

---

## 6. 验证容差

| 维度 | 容差 |
|---|---|
| brainstorm pattern_hints_for_author 数量 | 3-5 个 category(不能空) |
| author 每章 pattern_hints | 1-2 个 id(不能空,不能 > 3) |
| critic alternative 数量 | 0-N 个(全 pass 也可接受,意味着 author 选得对) |
| iloveppt RAG fallback used | ≥ 1 个(若库非空 + Step 4 三路降级) |
| audience alternative 数量 | 仅 needs_visual_redo 页给 |
| 总 token 增量 | < 100k(估算 ~50k,留 2× buffer) |

---

## 7. 回退路径

| 风险 | 回退 |
|---|---|
| Phase 2 某个 agent 改坏(单 task) | `git revert <commit>`,跳过该 agent 上其他 4 个 |
| Phase 4 整体 fail | `git reset --hard pre-visual-patterns-5agent` |
| 库 21 个命中率太低,critic / audience 反复给 alternative → step repetition | 用户决定停;协议加 "alternative 上限 3 个 / deck" 的 cap |
| token 增量超 100k(超预算) | 降级:Phase 2 只保留 author + audience 两个(回到原 ROI #1+#2 推荐),其他 3 个回滚 |

---

## 8. 不在范围内(YAGNI)

明确**不解决**:

- **patterns 库扩库**(从 21 → 50-100):独立 spec,本次 merge 后立刻启动
- **INDEX.md 重组按 content intent 分类**:同上,跟扩库一起
- **structured output / JSON schema 强制校验**(F4 hybrid finding):另一个 spec
- **runtime.log 平台层 telemetry**(F3 hybrid finding):非项目可控,等 Claude Code 平台
- **章节并行拓写**(audit B4 Layer 2):另一个 spec

---

## 9. 后续(post-merge 跟进)

按本次 brainstorming 决策(用户选"5 agent 一次性上,不等扩库"),**merge 后立刻启动扩库 spec**(独立 PR,2-3 周):

- patterns/<id> 从 21 → 50-100
- INDEX.md 重组按 content intent 分类
- 这是本 spec 的隐性前置,会在 postmortem 显式标 "follow-up required"

---

## 10. 决策记录

| 决策点 | 选择 | 理由 |
|---|---|---|
| patterns 库前置条件 | 5 agent 一次性上,不等扩库 | 用户接受 21 库下风险,扩库独立项目 |
| 决策权归属 | author 唯一写者;其他 advisory + 用户 cherry-pick | 避免 MAST FM-1.3 step repetition |
| RAG 调用形式 | 统一 SOP `search.sh --mode hybrid --top-k 5` | agent 间一致性高 |
| Phase 2 改造顺序 | 按 ROI(author Stage C → audience → critic → iloveppt → brainstorm → author rework) | 高 ROI 先上,失败可只回滚后半 |
| spec 归档位置 | `docs/archive/` | 遵循 CLAUDE.md "约定"节 |
| pattern_hints alternative 数量上限 | 不显式 cap(实测后 postmortem 再说) | YAGNI,risk 章节有兜底 |
