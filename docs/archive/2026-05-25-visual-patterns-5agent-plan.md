# Visual Patterns RAG · 5-agent 扩展 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 visual-patterns RAG 库调用从 author 1 agent 扩到 5 agent 全接入(brainstorm 预选 + author 候选 + critic 校验 + iloveppt 第 4 路 fallback + audience triage 建议),Lock-on-first 规则下 author 唯一写者,其他 agent 只 advisory。

**Architecture:** 统一 SOP `Bash search.sh --query <intent> --mode hybrid --top-k 5 --format json`。5 agent 共享调用模板。新协议字段 `pattern_hints` / `suggested_alternative_pattern(s)` 加入 pipeline-protocol.md §4 yaml schema。主线程 cherry-pick gate(任何 alternative 必须问用户)。

**Tech Stack:** Bash (调 `library/visual-patterns/search.sh`)、markdown (agent prompts / 协议文档 / brief.md / outline.md)、yaml (handoff schema)、python-pptx (build.py 不改,通过 `<!-- pattern: <id> -->` 注释路径不变)。

**Spec:** `docs/archive/2026-05-25-visual-patterns-5agent-design.md`(必读)
**Hybrid baseline 参考:** `docs/archive/2026-05-25-hybrid-migration-postmortem.md`(继承 yaml schema 偏差等 finding)

---

## File Structure

### 改动文件总览

| 文件 | 动作 | 说明 |
|---|---|---|
| `.claude/pipeline-protocol.md` | 修改 | §4 加新 yaml 字段(5 处)+ §3.3 加 cherry-pick gate |
| `.claude/skills/pptx-deck/content-writing.md` | 修改 | outline.md per-chapter schema 加 `pattern_hints` |
| `.claude/agents/iloveppt-brainstorm.md` | 修改 | Step 3.5 新增 RAG 预选 + brief.md frontmatter `pattern_hints_for_author` |
| `.claude/agents/iloveppt-author.md` | 修改 | Step 1A.5(Stage C 新加 RAG 选 hints) + Step 1D / rework 路径(接受 `accept_alternative_pattern`) |
| `.claude/agents/iloveppt-critic.md` | 修改 | 加 "维度 5 pattern 适配性" + `suggested_alternative_patterns` 字段 |
| `.claude/agents/iloveppt.md` | 修改 | Step 4 加 RAG 第 4 路 fallback(iconify/Unsplash/brand 之后) |
| `.claude/agents/iloveppt-audience.md` | 修改 | triage needs_visual_redo 加 `suggested_alternative_pattern` |
| `CLAUDE.md` | 修改 | 派发规则段加 cherry-pick gate 提示 |
| `docs/archive/2026-05-25-visual-patterns-5agent-postmortem.md` | **创建** | Phase 5 |
| `evals/agents/baseline/01-exec-decision-post-visual-patterns/` | **创建** | Phase 4 baseline 关键产物 |

### 验证用 fixture

- `evals/agents/fixtures/01-exec-decision`(同 hybrid Phase 4)
- 对比 baseline:`evals/agents/baseline/01-exec-decision-post-hybrid/`(hybrid 跑过的)

### Git tag

- `pre-visual-patterns-5agent`(Phase 0)
- `post-visual-patterns-5agent`(Phase 4 通过后)

---

# Phase 0:安全网

**目标**:打 anchor tag,确认基础测试 OK。

---

## Task 0.1:checkout 新 branch + tag anchor

- [ ] **Step 1:从 main 创建新 branch**

Run:
```bash
git checkout main
git status   # 必须 clean
git checkout -b feat/visual-patterns-5agent
```

Expected:成功切到 feat/visual-patterns-5agent。

- [ ] **Step 2:打 anchor tag**

Run:
```bash
git tag -a pre-visual-patterns-5agent -m "Anchor: state before visual-patterns 5-agent RAG extension"
git tag --list | grep visual-patterns
```

Expected:看到 `pre-visual-patterns-5agent`。

- [ ] **Step 3:确认 pytest 通过 baseline**

Run:
```bash
python3 -m pytest tests/ -q
```

Expected:`72 passed`。若 fail → 立即停,先修。

- [ ] **Step 4:确认 library/visual-patterns 可用**

Run:
```bash
ls library/visual-patterns/patterns/ | wc -l   # 期望 21
bash library/visual-patterns/search.sh --query "process flow" --mode hybrid --top-k 3 --format json 2>&1 | head -20
```

Expected:21 patterns,search.sh 跑通返回 JSON(若 sqlite 没初始化 / venv 没装 → 立即停,先修)。

---

# Phase 1:协议层

**目标**:`pipeline-protocol.md` §4 加 5 处新字段 + §3.3 cherry-pick gate;`content-writing.md` outline.md schema 加 `pattern_hints`。

---

## Task 1.1:pipeline-protocol.md §4.3 加 brainstorm `pattern_hints_for_author`

**Files:**
- Modify: `.claude/pipeline-protocol.md`(§4.3 brainstorm 段)

- [ ] **Step 1:Read 当前 brainstorm yaml schema 段**

Run:
```bash
grep -A 10 "brainstorm 的 dispatch_author" .claude/pipeline-protocol.md
```

Expected:看到现有 brainstorm dispatch_author yaml 示例。

- [ ] **Step 2:Edit 加 `pattern_hints_for_author` 字段**

替换 `pipeline-protocol.md` 中 brainstorm dispatch_author yaml block:

旧:
```yaml
agent: iloveppt-brainstorm
status: ok
next_action: dispatch_author
artifacts:
  - path: <abs path to brief.md>
    kind: brief_md
brief_summary: <一句话 brief 概要>
```

新:
```yaml
agent: iloveppt-brainstorm
status: ok
next_action: dispatch_author
artifacts:
  - path: <abs path to brief.md>
    kind: brief_md
brief_summary: <一句话 brief 概要>
pattern_hints_for_author:           # 新增 · category list,brainstorm RAG 预选,3-5 个
  - process
  - cycle
  - comparison
```

- [ ] **Step 3:验证**

Run:
```bash
grep -A 3 "pattern_hints_for_author" .claude/pipeline-protocol.md
```

Expected:看到新字段。

---

## Task 1.2:pipeline-protocol.md §4.3 加 author `pattern_hints`

**Files:**
- Modify: `.claude/pipeline-protocol.md`(§4.3 author 段)

- [ ] **Step 1:Edit author Stage C yaml block 加字段**

替换 author yaml 通用 block:

旧:
```yaml
agent: iloveppt-author
status: ok
next_action: ask_user_for_outline_approval | ask_user_for_content_approval | dispatch_critic
stage: C | D | D_rework
artifacts:
  - path: <abs path to outline.md or content.md>
    kind: outline_md | content_md
rounds_used: <int>
pyramid_self_check: passed | failed  # Stage D 必填
```

新:
```yaml
agent: iloveppt-author
status: ok
next_action: ask_user_for_outline_approval | ask_user_for_content_approval | dispatch_critic
stage: C | D | D_rework
artifacts:
  - path: <abs path to outline.md or content.md>
    kind: outline_md | content_md
rounds_used: <int>
pyramid_self_check: passed | failed  # Stage D 必填
pattern_hints:                       # 新增 · Stage C 必填,Stage D 透传 outline,rework 可改
  - chapter: 1
    selected: [process-5-step-linear]
    rationale: "5 阶段流程,linear pattern 匹配"
  - chapter: 2
    selected: [cards-flag-4]
    rationale: "4A 4 维并列,cards 匹配"
```

- [ ] **Step 2:验证**

Run:
```bash
grep -B 1 -A 6 "pattern_hints:" .claude/pipeline-protocol.md | head -20
```

Expected:看到新字段在 author 段。

---

## Task 1.3:pipeline-protocol.md §4.3 加 critic `suggested_alternative_patterns`

**Files:**
- Modify: `.claude/pipeline-protocol.md`(§4.3 critic 段)

- [ ] **Step 1:Edit critic yaml block 加字段**

在 critic 必加字段 block 末尾(rounds_used 之后)追加:

```yaml
suggested_alternative_patterns:      # 新增 · advisory(用户 cherry-pick 才采纳)
  - page: 3
    current: cards-flag-4
    suggest: matrix-2x2
    reason: "4A 不是并列而是因果矩阵(2 类风险 × 2 类应对),matrix-2x2 更准"
```

- [ ] **Step 2:验证**

Run:
```bash
grep "suggested_alternative_patterns" .claude/pipeline-protocol.md
```

Expected:1 处(critic 段)。

---

## Task 1.4:pipeline-protocol.md §4.3 加 iloveppt `rag_fallback_used`

**Files:**
- Modify: `.claude/pipeline-protocol.md`(§4.3 iloveppt 段)

- [ ] **Step 1:Edit iloveppt yaml block 加字段**

替换 iloveppt 必加字段 block:

旧:
```yaml
agent: iloveppt
status: ok
next_action: dispatch_audience | hard_stop
artifacts:
  - path: <abs path to deck_v{N}.pptx>
    kind: pptx
  - path: <abs path to render dir>
    kind: render_dir
build_iterations: <int>
pyramid_check: passed | failed
visual_qa:
  passed: <int>
  total: <int>
```

新:
```yaml
agent: iloveppt
status: ok
next_action: dispatch_audience | hard_stop
artifacts:
  - path: <abs path to deck_v{N}.pptx>
    kind: pptx
  - path: <abs path to render dir>
    kind: render_dir
build_iterations: <int>
pyramid_check: passed | failed
visual_qa:
  passed: <int>
  total: <int>
visual_step4:                       # 新增 · Step 4 三路 + RAG 第 4 路状态
  capability:
    cairosvg: enabled | disabled
    unsplash: enabled | disabled
    brand_assets: <count> | none
    rag_patterns: <count>_available  # patterns 库当前可用数(库为空时 0_available)
  rag_fallback_used:                # 新增 · 第 4 路实际使用(三路降级时)
    - page: 6
      pattern_id: cards-flag-3
      preview_path: library/visual-patterns/patterns/cards-flag-3/preview.png
      usage: hero_reference
```

- [ ] **Step 2:验证**

Run:
```bash
grep "rag_fallback_used\|rag_patterns" .claude/pipeline-protocol.md
```

Expected:2 处(visual_step4 内)。

---

## Task 1.5:pipeline-protocol.md §4.3 加 audience `suggested_alternative_pattern`

**Files:**
- Modify: `.claude/pipeline-protocol.md`(§4.3 audience 段)

- [ ] **Step 1:Edit audience triage block 加字段**

audience yaml `per_page_scores` 之后追加:

```yaml
needs_visual_redo_pages:            # 已有,但每个 entry 加 suggested_alternative_pattern
  - page: 8
    issue: <原描述>
    suggested_alternative_pattern:  # 新增 · advisory(给 iloveppt mode=visual_redo 用)
      current: pic_text + drawio_chart
      suggest: process-5-step-linear
      reason: "draw.io HTML 标签裸露,直接换内置 pattern preview 一击命中"
```

(注:`needs_visual_redo_pages` 是 hybrid 设计已加的字段;本次只是给每个 entry 嵌入 `suggested_alternative_pattern` 子字段)

- [ ] **Step 2:验证**

Run:
```bash
grep -B 1 -A 3 "suggested_alternative_pattern:" .claude/pipeline-protocol.md
```

Expected:看到嵌在 needs_visual_redo_pages 下的字段。

---

## Task 1.6:pipeline-protocol.md §3.3 加 cherry-pick gate

**Files:**
- Modify: `.claude/pipeline-protocol.md`(§3.3 Gate 规则段)

- [ ] **Step 1:Edit §3.3 Gate 规则表追加 1 行**

定位 §3.3 表 "audience overall_score | ≥ 9" 后追加一行:

```markdown
| Pattern cherry-pick | critic / iloveppt / audience 任一 yaml 含 `suggested_alternative_pattern(s)` → 主线程**必须展示给用户**,不替用户决定;用户答"改" → Task author rework + user_response 含 `accept_alternative_pattern: <id>`;用户答"不改" → 继续派下一棒。若 audience 阶段触发改 → author rework 后必须重派 critic D + audience |
```

- [ ] **Step 2:验证**

Run:
```bash
grep "Pattern cherry-pick" .claude/pipeline-protocol.md
```

Expected:1 处。

---

## Task 1.7:content-writing.md outline.md per-chapter schema 加 `pattern_hints`

**Files:**
- Modify: `.claude/skills/pptx-deck/content-writing.md`

- [ ] **Step 1:Read 当前 outline.md schema 段**

Run:
```bash
grep -B 1 -A 10 "## outline.md schema\|outline.md 的 schema\|outline.md.*\(章节骨架\)" .claude/skills/pptx-deck/content-writing.md | head -30
```

(注:实际节标题取决于文档结构,可能是 "outline.md schema" 或 "outline.md(章节骨架)")

Expected:看到 outline.md 章节示例 block。

- [ ] **Step 2:Edit 加 `pattern_hints` 字段到 per-chapter 示例**

在 outline.md 章节示例(包含 intent / layout / data / diagram 的)末尾加:

```markdown
- pattern_hints:                    # 新增 · author Stage C 用 search.sh 选,1-2 id/章
    selected: <pattern-id>          # 从 search.sh top-5 选 1-2 个
    rationale: <一句话理由>
    alternatives: [<id>, <id>]      # search.sh top-5 里没选的 3-4 个,给用户审 outline 时看候选
```

- [ ] **Step 3:验证**

Run:
```bash
grep "pattern_hints:" .claude/skills/pptx-deck/content-writing.md
```

Expected:至少 1 处。

---

## Task 1.8:Commit Phase 1

- [ ] **Step 1:Run pytest 确认协议改动不破现有测试**

Run:
```bash
python3 -m pytest tests/ -q
```

Expected:72 passed。

- [ ] **Step 2:Commit**

Run:
```bash
git add .claude/pipeline-protocol.md .claude/skills/pptx-deck/content-writing.md
git commit -m "feat(protocol): add visual-patterns RAG 5-agent schemas + cherry-pick gate

- pipeline-protocol.md §4: brainstorm pattern_hints_for_author / author pattern_hints
  / critic suggested_alternative_patterns / iloveppt visual_step4.rag_fallback_used
  / audience needs_visual_redo_pages[N].suggested_alternative_pattern
- pipeline-protocol.md §3.3: Pattern cherry-pick gate (any alternative → user decides)
- content-writing.md: outline.md per-chapter pattern_hints schema (selected / rationale / alternatives)"
```

Expected:commit 成功。

---

# Phase 2:5 agent prompt 改造(按依赖顺序 6 个 task)

**目标**:按依赖顺序(brainstorm → author Stage C → author rework → critic → iloveppt → audience)改 prompt。

---

## Task 2.1:brainstorm Step 3.5 新增 RAG 预选

**Files:**
- Modify: `.claude/agents/iloveppt-brainstorm.md`

- [ ] **Step 1:Read brainstorm 当前 Step 3 段**

Run:
```bash
grep -n "### Step 3\|### Step B" .claude/agents/iloveppt-brainstorm.md
```

Expected:看到 Step 3(brief.md gate)位置。

- [ ] **Step 2:在 brief.md write 之后 + dispatch_author 之前插入 Step 3.5**

定位 brainstorm prompt 中 "Step B.1 Write brief.md" 落盘成功之后、"Step B.2 ask_user_for_brief_approval" 之前,插入:

```markdown
### Step 3.5 · RAG 预选 pattern category hints(brief 已写完后)

Write brief.md 成功 + 用户确认 OK 之后,**dispatch_author 之前**,做一次 RAG 预选:

1. 用 top_recommendation 关键词 + SCQA situation/complication 摘要构造 query
   ```bash
   QUERY="<top_recommendation 动+宾 + SCQA 关键词,如 '5 阶段 落地 评审办法 流程'>"
   Bash: bash ${CLAUDE_PROJECT_DIR}/library/visual-patterns/search.sh \
         --query "$QUERY" \
         --mode hybrid \
         --top-k 5 \
         --format json
   ```
2. parse JSON 结果,取每个 pattern 的 `category` 字段(去重)
3. 选出 3-5 个 category(若 top-5 都同 category,扩 top-k 到 10 重选)
4. 在 dispatch_author yaml 加 `pattern_hints_for_author: [category1, ...]` 字段
5. 同时在 brief.md frontmatter 加:
   ```yaml
   pattern_hints_for_author:
     candidates: [process, cycle, comparison]
     source: brainstorm_search_top_5_categories
   ```
6. dispatch_author 时 brief_md_path 透传给 author(author 读 brief.md frontmatter 拿到 hints)

**降级**:若 search.sh 调用失败(library/visual-patterns 不存在 / sqlite 没初始化 / venv 缺失)→ pattern_hints_for_author 为空数组,brief.md frontmatter 写 `source: brainstorm_search_failed`,brainstorm 不阻塞,继续 dispatch_author。
```

- [ ] **Step 3:验证**

Run:
```bash
grep "Step 3.5\|pattern_hints_for_author" .claude/agents/iloveppt-brainstorm.md
```

Expected:Step 3.5 段 + pattern_hints_for_author 字段(至少 2 处)。

- [ ] **Step 4:Commit**

Run:
```bash
git add .claude/agents/iloveppt-brainstorm.md
git commit -m "feat(agent): brainstorm Step 3.5 - RAG 预选 pattern category hints

- Add Step 3.5 between brief.md write and dispatch_author
- Query: top_recommendation + SCQA keywords
- Output: pattern_hints_for_author (3-5 categories) in dispatch_author yaml
        + brief.md frontmatter
- Fallback: search.sh fail → empty array, source=brainstorm_search_failed, do not block"
```

Expected:commit 成功。

---

## Task 2.2:author Stage C Step 1A.5 新增 RAG 选 hints

**Files:**
- Modify: `.claude/agents/iloveppt-author.md`

- [ ] **Step 1:Read author Stage C Step 1A 段**

Run:
```bash
grep -n "### Step 1A\|### Step 1A · Stage C\|Pyramid 自检" .claude/agents/iloveppt-author.md | head -10
```

Expected:看到 Step 1A 位置。

- [ ] **Step 2:在 Step 1A 写完 outline + Pyramid 自检之前插入 Step 1A.5**

定位 "写完 outline.md 文件" 之后、"Pyramid 7 项自检" 之前,插入:

```markdown
### Step 1A.5 · 对每章 RAG 选 pattern hints(Pyramid 自检之前)

写完 outline.md 之后,对每章跑一次 RAG:

1. 读 brief.md frontmatter `pattern_hints_for_author.candidates`(brainstorm 给的 category 候选,可空)
2. 对 outline 每章(`## N. <action title>`):
   ```bash
   QUERY="<章节 action title + intent 关键词,可加 brainstorm hints 里的 category 限定>"
   Bash: bash ${CLAUDE_PROJECT_DIR}/library/visual-patterns/search.sh \
         --query "$QUERY" \
         --mode hybrid \
         --top-k 5 \
         --format json
   ```
3. parse JSON 结果(5 个候选 pattern id + score + rationale)
4. **LLM 从 top-5 选 1-2 个最贴合**(看每个 pattern.yaml 的 intent / fallback_rendering / 适用场景),写 rationale
5. 在 outline.md 章节 metadata 加 `pattern_hints` 字段:
   ```yaml
   ## 1. <action title>
   - intent: <...>
   - layout: <13 内置 layout>
   - data: <...>
   - diagram: <...>
   - pattern_hints:
       selected: <pattern-id>
       rationale: <为什么选这个,一句话>
       alternatives: [<id>, <id>, <id>]   # top-5 里没选的 3-4 个,作 candidates
   ```
6. yaml return 时同步加 `pattern_hints` 数组(per-chapter,见 §4 schema)

**降级**:若某章 search.sh 调用失败 → 该章 `pattern_hints.selected = null` + `rationale: search_failed`,**不阻塞**整体 Stage C 完成。
```

- [ ] **Step 3:验证**

Run:
```bash
grep "Step 1A.5\|pattern_hints:" .claude/agents/iloveppt-author.md | head -10
```

Expected:Step 1A.5 段 + pattern_hints 字段。

- [ ] **Step 4:Commit**

Run:
```bash
git add .claude/agents/iloveppt-author.md
git commit -m "feat(agent): author Stage C Step 1A.5 - RAG 选 pattern hints per chapter

- After outline write, before Pyramid self-check
- Per chapter: search.sh hybrid top-5 + LLM select 1-2
- Write to outline.md frontmatter pattern_hints (selected/rationale/alternatives)
- yaml return adds pattern_hints array per chapter
- Fallback: search.sh fail per chapter → selected=null, do not block"
```

Expected:commit 成功。

---

## Task 2.3:author Stage D + D-rework 接受 `accept_alternative_pattern`

**Files:**
- Modify: `.claude/agents/iloveppt-author.md`

- [ ] **Step 1:Read author Stage D / Step 1B / Step 1D 段**

Run:
```bash
grep -n "### Step 1B\|### Step 1C\|### Step 1D\|D_rework\|user_response.*改动" .claude/agents/iloveppt-author.md | head -10
```

Expected:看到 Step 1B (Stage C 接收反馈) / Step 1D (Stage D 接收反馈) 位置。

- [ ] **Step 2:在 Step 1B + Step 1D 用户反馈解析逻辑里加 alternative 路径**

定位 Step 1B "user_response 含改动指令" 段(line ~250),在判断逻辑中加新分支:

```markdown
- `user_response` 含 `accept_alternative_pattern: <new-id>` → **接受 critic / audience 提议的 alternative pattern**:
  1. Read outline.md(或 content.md, 看 stage)拿当前 pattern_hints
  2. 找到 user_response 里指定 page/chapter 对应章节
  3. 更新该章 `pattern_hints.selected = <new-id>` + `rationale` 加注 "user_accepted_alternative_from_<source-agent>"
  4. 若 stage=D / D_rework,同步改 content.md 嵌入注释 `<!-- pattern: <new-id> -->`(原 pattern 注释替换)
  5. 重跑 Pyramid 自检(改 pattern 一般不影响 Pyramid,但走一遍)
  6. yaml return 含更新后 pattern_hints
```

(注:`Step 1D` Stage D 反馈也加同样分支,逻辑相同只是改 content.md 而非 outline.md)

- [ ] **Step 3:验证**

Run:
```bash
grep "accept_alternative_pattern" .claude/agents/iloveppt-author.md
```

Expected:至少 1 处(Step 1B 或 Step 1D 中)。

- [ ] **Step 4:Commit**

Run:
```bash
git add .claude/agents/iloveppt-author.md
git commit -m "feat(agent): author Stage C/D rework - accept_alternative_pattern path

- user_response containing accept_alternative_pattern: <id>
- Update outline.md / content.md pattern_hints.selected
- Replace content.md inline comment <!-- pattern: <old> --> with <new-id>
- Re-run Pyramid self-check
- yaml return includes updated pattern_hints"
```

Expected:commit 成功。

---

## Task 2.4:critic Stage C/D 加 维度 5 + `suggested_alternative_patterns`

**Files:**
- Modify: `.claude/agents/iloveppt-critic.md`

- [ ] **Step 1:Read critic 现有评审维度段**

Run:
```bash
grep -n "### Step 1\|### Step 2\|维度 [0-9]\|judgmental" .claude/agents/iloveppt-critic.md | head -15
```

Expected:看到现有 4 维度位置(论据强度 / 节奏感 / 措辞质感 / 整体平衡)。

- [ ] **Step 2:在 4 维度后加 "维度 5 · pattern 适配性"**

定位 "维度 4 · 整体平衡" 段末尾,追加:

```markdown
#### 维度 5 · pattern 适配性(2026-05-25 新增,需 library/visual-patterns 库)

看 author 给的 outline / content 中 `pattern_hints` 是否真的最匹配本章 intent。问自己:**作者选的 pattern 跟章节论点是不是同源?有没有更准的?**

**触发信号**:
- author selected pattern 的 fallback_rendering 跟章节 layout 不匹配(如 selected 是 matrix 但 layout 是 cards)
- selected pattern 的 intent 跟章节 action title 语义偏差大(如 selected 是 cycle 但章节明显是 linear process)
- selected pattern 是 author 因 "candidates 里第一个就选了" 而非真匹配(可看 alternatives list 里有没有更准的)

**evidence 模板**:`page X 章节 "Y": author selected <id-A>,但 intent 是 "5 阶段串行",<id-A> 是矩阵 pattern,RAG search.sh 重跑 top-5 含 <id-B> linear pattern,后者 fallback_rendering 跟 layout: pic_text 更兼容。建议 alternative`

**怎么查**:
1. Read library/visual-patterns/patterns/<author selected id>/pattern.yaml,看 intent / fallback_rendering
2. 若 author selected 跟章节明显不符,重跑 `Bash search.sh --query "<章节 intent>" --mode hybrid --top-k 5`
3. parse top-5,选出 1 个明显更优的 alternative(若 top-5 都不如 author 已选,**不**报 alternative,这维度 0 issue)
4. 在 yaml return 加 `suggested_alternative_patterns` 字段(advisory,不替 author 决定)

**注意 advisory 性质**:你只**建议**,不能改 outline.md / content.md;主线程拿到你的建议会展示给用户 cherry-pick。
```

- [ ] **Step 3:Edit critic yaml return block 加 `suggested_alternative_patterns` 字段**

(三档 verdict 的 yaml block 都加,字段在 rounds_used 之后)

```yaml
suggested_alternative_patterns:      # 新增 · advisory · 维度 5 输出
  - page: 3
    current: cards-flag-4
    suggest: matrix-2x2
    reason: "4A 不是并列而是因果矩阵,matrix-2x2 更准(RAG top-5 第 2 候选)"
```

(若维度 5 评审无 issue,该字段为空数组 `[]`)

- [ ] **Step 4:验证**

Run:
```bash
grep "维度 5\|suggested_alternative_patterns" .claude/agents/iloveppt-critic.md
```

Expected:至少 2 处(段 + yaml 字段)。

- [ ] **Step 5:Commit**

Run:
```bash
git add .claude/agents/iloveppt-critic.md
git commit -m "feat(agent): critic 维度 5 pattern 适配性 + suggested_alternative_patterns

- Add 维度 5 after 4 维度判断性评审段
- Check author selected pattern.yaml intent / fallback_rendering match
- Re-query search.sh if mismatch; pick 1 alternative from top-5 if obvious better
- yaml return adds suggested_alternative_patterns array (advisory, not modify .md)
- 0 issue case: empty array, do not block verdict"
```

Expected:commit 成功。

---

## Task 2.5:iloveppt Step 4 加 RAG 第 4 路 fallback

**Files:**
- Modify: `.claude/agents/iloveppt.md`

- [ ] **Step 1:Read iloveppt Step 4 现有三路降级段**

Run:
```bash
grep -n "### Step 4\|iconify\|Unsplash\|brand_assets\|三路降级" .claude/agents/iloveppt.md | head -10
```

Expected:看到 Step 4 三路(iconify / Unsplash / brand_assets)位置。

- [ ] **Step 2:在三路降级**之后**加第 4 路 RAG fallback**

定位 Step 4 三路降级判断逻辑(iconify 失败 → Unsplash → brand → ???)之后,追加:

```markdown
#### Step 4 第 4 路 · RAG patterns fallback(2026-05-25 新增)

**触发条件**:
- 三路降级全部 disabled(cairosvg/unsplash/brand 全失败)
- **且** 某页 visual_qa 评分低(visual_qa.passed < 14/17,即至少 3 项 fail)
- **且** library/visual-patterns/ 存在 + search.sh 可调

**做法**:
1. 对每个低分页:
   ```bash
   PAGE_INTENT="<该页章节 intent + action title 关键词>"
   Bash: bash ${CLAUDE_PROJECT_DIR}/library/visual-patterns/search.sh \
         --query "$PAGE_INTENT" \
         --mode hybrid \
         --top-k 3 \
         --format json
   ```
2. parse top-3,看每个 patterns/<id>/preview.png:
   - 若该 page layout 支持 hero 图(pic_text / single_focus)→ 嵌入 preview.png 作 hero
   - 若 layout 不支持 hero(table / bullet_list)→ preview.png 仅作 reference,不嵌入,但记录在 yaml `rag_fallback_used.usage = reference_only`
3. yaml return 加 `visual_step4.rag_fallback_used`:
   ```yaml
   visual_step4:
     capability:
       cairosvg: disabled
       unsplash: disabled
       brand_assets: none
       rag_patterns: 21_available     # 当前库 patterns 数
     rag_fallback_used:
       - page: 6
         pattern_id: cards-flag-3
         preview_path: library/visual-patterns/patterns/cards-flag-3/preview.png
         usage: hero_reference        # 或 reference_only
   ```

**降级**:若 search.sh 调用失败 → rag_patterns: 0_available + rag_fallback_used: [],不阻塞 Step 4 完成。
```

- [ ] **Step 3:Edit iloveppt yaml return block 加 visual_step4 完整字段**

(替换原 visual_step4 block,加 capability.rag_patterns + rag_fallback_used)

- [ ] **Step 4:验证**

Run:
```bash
grep "rag_fallback_used\|rag_patterns" .claude/agents/iloveppt.md
```

Expected:至少 2 处(段 + yaml 字段)。

- [ ] **Step 5:Commit**

Run:
```bash
git add .claude/agents/iloveppt.md
git commit -m "feat(agent): iloveppt Step 4 第 4 路 - RAG patterns fallback

- Trigger: 3 paths disabled + page visual_qa.passed < 14/17 + library available
- search.sh hybrid top-3, embed preview.png as hero (if layout supports) or reference_only
- yaml return adds visual_step4.capability.rag_patterns + rag_fallback_used array
- Fallback: search.sh fail → rag_patterns: 0_available, do not block Step 4"
```

Expected:commit 成功。

---

## Task 2.6:audience triage needs_visual_redo 加 `suggested_alternative_pattern`

**Files:**
- Modify: `.claude/agents/iloveppt-audience.md`

- [ ] **Step 1:Read audience triage 段**

Run:
```bash
grep -n "triage\|needs_visual_redo\|Step 4\|Step 5" .claude/agents/iloveppt-audience.md | head -10
```

Expected:看到 triage 生成 needs_visual_redo 段。

- [ ] **Step 2:在生成 needs_visual_redo 页清单时,对每页跑 RAG 找 alternative**

定位 audience prompt 中 "生成 triage" 段(通常在 Step 3 / Step 4),追加:

```markdown
### Step 3.5 · 对 needs_visual_redo 每页 RAG 找 alternative pattern(2026-05-25 新增)

triage 已划分出 needs_visual_redo 页清单后,**对每页跑一次 RAG**:

1. 用该页 layout + page issue 关键词构造 query
   ```bash
   PAGE_QUERY="<page issue 关键词,如 '5 阶段流程图 PNG 渲染破损' 或 '4 维 cards 视觉单调'>"
   Bash: bash ${CLAUDE_PROJECT_DIR}/library/visual-patterns/search.sh \
         --query "$PAGE_QUERY" \
         --mode hybrid \
         --top-k 3 \
         --format json
   ```
2. parse top-3,选出 1 个最匹配的 alternative pattern
3. 在 needs_visual_redo_pages 该页 entry 加:
   ```yaml
   needs_visual_redo_pages:
     - page: 8
       issue: "draw.io 流程图 HTML 标签裸露"
       suggested_alternative_pattern:
         current: pic_text + drawio_chart
         suggest: process-5-step-linear
         reason: "draw.io HTML 标签裸露,直接换内置 pattern preview 一击命中(RAG top-1)"
   ```

**降级**:若 search.sh 失败 / top-3 没合适候选 → 不写 `suggested_alternative_pattern` 字段(留空,iloveppt mode=visual_redo 走自己的 Step 4 第 4 路)。

**advisory 性质**:你只**建议**,不能改任何 .md / 调 iloveppt;主线程拿到建议展示给用户 cherry-pick。
```

- [ ] **Step 3:验证**

Run:
```bash
grep "Step 3.5\|suggested_alternative_pattern" .claude/agents/iloveppt-audience.md
```

Expected:至少 2 处(段 + yaml 字段)。

- [ ] **Step 4:Commit**

Run:
```bash
git add .claude/agents/iloveppt-audience.md
git commit -m "feat(agent): audience Step 3.5 - needs_visual_redo per-page RAG alternative

- After triage classifies needs_visual_redo pages
- Per page: search.sh hybrid top-3 + pick 1 alternative
- Embed in needs_visual_redo_pages[N].suggested_alternative_pattern
- Advisory only, do not modify .md / call iloveppt
- Fallback: empty field if search.sh fail / no good top-3"
```

Expected:commit 成功。

---

# Phase 3:主线程入口改造

**目标**:CLAUDE.md 加 cherry-pick gate 提示,让主线程行为对齐协议。

---

## Task 3.1:CLAUDE.md 主线程派发规则段加 cherry-pick gate 提示

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1:Read 现有主线程派发规则段**

Run:
```bash
grep -n "主线程派发规则\|主线程必须" CLAUDE.md | head -5
```

Expected:看到 "主线程派发规则(一句话总结)" 段。

- [ ] **Step 2:在派发规则段后追加 cherry-pick gate 提示**

在原一句话总结后追加一段:

```markdown
**Pattern cherry-pick gate**(2026-05-25 新增):任何 critic / iloveppt / audience subagent return yaml 含 `suggested_alternative_pattern(s)` 字段 → 主线程**必须**展示给用户决定,不允许自决。用户答"改" → Task author rework(user_response 含 `accept_alternative_pattern: <id>`);用户答"不改" → 继续派下一棒。完整流程见 [pipeline protocol §3.3 Pattern cherry-pick](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md#33-gate-规则)。
```

- [ ] **Step 3:验证**

Run:
```bash
grep "cherry-pick gate\|accept_alternative_pattern" CLAUDE.md
```

Expected:1-2 处。

- [ ] **Step 4:Commit**

Run:
```bash
git add CLAUDE.md
git commit -m "docs(CLAUDE): add Pattern cherry-pick gate to 主线程派发规则段"
```

Expected:commit 成功。

---

# Phase 4:验证

**目标**:跑同一 fixture 01-exec-decision,验证 5 个新调用点都触发 + yaml schema 主要字段 parse + 端到端跑通。

---

## Task 4.1:跑 fixture 端到端

- [ ] **Step 1:确认 hybrid baseline 在**

Run:
```bash
ls evals/agents/baseline/01-exec-decision-post-hybrid/META.md
```

Expected:文件存在(hybrid Phase 4 产物)。

- [ ] **Step 2:跑 fixture 01-exec-decision(扮演 scripted user,按 fixture/brief.md 标准答)**

按 fixture `evals/agents/fixtures/01-exec-decision/brief.md` 表 user_responses 跑全程:
- 触发主线程:贴 `user_initial_request`
- brainstorm 问字段:按表答 audience=executive / duration=15 / mode=speaker / top_recommendation 等
- brief 批准 → outline 批准 → critic notes 处理 → content 批准 → critic D notes → iloveppt build → audience triage

**新增观察点**:
- brief.md frontmatter 是否含 `pattern_hints_for_author`(Task 2.1 验证)
- outline.md per-chapter 是否含 `pattern_hints` 字段(Task 2.2 验证)
- critic Stage C/D yaml 是否含 `suggested_alternative_patterns`(Task 2.4 验证)
- iloveppt yaml 是否含 `visual_step4.rag_fallback_used`(Task 2.5 验证)
- audience yaml `needs_visual_redo_pages[N]` 是否含 `suggested_alternative_pattern`(Task 2.6 验证)
- 主线程拿到 alternative 时是否展示给用户(Task 3.1 验证)

- [ ] **Step 3:复制产物 + 收集 5 处新字段证据**

Run:
```bash
WORK=decks/eval-<timestamp>-01-exec-decision
DST=evals/agents/baseline/01-exec-decision-post-visual-patterns
mkdir -p $DST/{brainstorm,author,critic,builder,audience}
cp $WORK/brainstorm/brief.md $WORK/brainstorm/state.json $DST/brainstorm/
cp $WORK/author/deck_v*_outline.md $WORK/author/deck_v*_content.md $WORK/author/state.json $DST/author/
cp $WORK/critic/critic_report_*.md $DST/critic/
cp $WORK/builder/deck_plan.json $WORK/builder/visual_report_*.md $DST/builder/
cp $WORK/audience/audience_review_*.md $DST/audience/
echo "=== 5 处新字段检查 ==="
echo "1. brief.md pattern_hints_for_author:"
grep -A 3 "pattern_hints_for_author" $DST/brainstorm/brief.md
echo "2. outline.md pattern_hints:"
grep -A 3 "pattern_hints:" $DST/author/deck_v1_outline.md | head -10
echo "3. critic suggested_alternative_patterns:"
grep "suggested_alternative_patterns" $DST/critic/*.md
echo "4. iloveppt visual_step4.rag_fallback_used:"
grep "rag_fallback_used\|rag_patterns" $DST/builder/visual_report_*.md
echo "5. audience suggested_alternative_pattern:"
grep -A 3 "suggested_alternative_pattern:" $DST/audience/audience_review_*.md
```

Expected:5 处都有数据。

- [ ] **Step 4:写 META.md**

Create `$DST/META.md`:
```markdown
# Post-visual-patterns-5agent baseline · 01-exec-decision

| 项 | 值 |
|---|---|
| Date | <填> |
| Mode | Hybrid + Visual Patterns 5-agent RAG |
| Wall-clock | ~分钟 |
| Total token (estimated) | ~hybrid baseline + ~50k |
| 5 处新字段触发 | brainstorm pattern_hints_for_author: yes/no
                  author pattern_hints: yes/no
                  critic suggested_alternative_patterns: <count>
                  iloveppt rag_fallback_used: <count>
                  audience suggested_alternative_pattern: <count> |
| 主线程 cherry-pick gate 触发 | <count> 次 |
| 用户接受 alternative | <count>/<total> |
| 与 hybrid baseline 产物 diff | brief.md 加 frontmatter 字段;outline.md 加 per-chapter 字段;其他 .md 内容差异看实测 |
```

---

## Task 4.2:Tag + 收尾

- [ ] **Step 1:Commit baseline + META**

Run:
```bash
git add evals/agents/baseline/01-exec-decision-post-visual-patterns/
git commit -m "test(evals): add post-visual-patterns-5agent baseline for 01-exec-decision

5 处新字段验证:
- brainstorm brief.md pattern_hints_for_author: ...
- author outline.md per-chapter pattern_hints: ...
- critic yaml suggested_alternative_patterns: ...
- iloveppt yaml visual_step4.rag_fallback_used: ...
- audience yaml needs_visual_redo_pages[N].suggested_alternative_pattern: ...

主线程 cherry-pick gate 触发 N 次,用户接受 M/N alternatives。"
```

Expected:commit 成功。

- [ ] **Step 2:Tag post-visual-patterns-5agent**

Run:
```bash
git tag -a post-visual-patterns-5agent -m "Visual Patterns 5-agent RAG extension validated by fixture 01-exec-decision"
git tag --list | grep visual-patterns
```

Expected:看到 pre + post 两个 tag。

---

# Phase 5:Postmortem

---

## Task 5.1:写 postmortem

**Files:**
- Create: `docs/archive/2026-05-25-visual-patterns-5agent-postmortem.md`

- [ ] **Step 1:写 postmortem 文件**

Create 文件,含以下章节:

```markdown
# Visual Patterns 5-agent RAG Extension Postmortem

| 项 | 值 |
|---|---|
| Date | <填> |
| Spec | docs/archive/2026-05-25-visual-patterns-5agent-design.md |
| Plan | docs/archive/2026-05-25-visual-patterns-5agent-plan.md |
| pre tag | pre-visual-patterns-5agent |
| post tag | post-visual-patterns-5agent |
| Branch | feat/visual-patterns-5agent |
| Total commits | ~10 |

## 1. 迁移成果

### 1.1 协议层
- pipeline-protocol.md §4: 加 5 处 yaml 字段(brainstorm/author/critic/iloveppt/audience)
- pipeline-protocol.md §3.3: 加 Pattern cherry-pick gate
- content-writing.md: outline.md per-chapter pattern_hints schema

### 1.2 Agent 改造
- brainstorm Step 3.5: 新增 RAG 预选
- author Stage C Step 1A.5: 新增 RAG 选 hints
- author Stage D/rework: 接受 accept_alternative_pattern
- critic 维度 5: pattern 适配性 + alternative
- iloveppt Step 4 第 4 路: rag_fallback
- audience Step 3.5: needs_visual_redo alternative

### 1.3 主线程
- CLAUDE.md 加 Pattern cherry-pick gate 提示

## 2. Phase 4 实测结果(fixture 01-exec-decision)

### 2.1 5 处新字段触发情况
(填实测数据)

### 2.2 RAG 命中率 / 用户接受率
(填实测数据)

### 2.3 Token 增量实测
(填实测数据)

### 2.4 跟 hybrid baseline 对比
(填关键 diff)

## 3. 关键 findings(实测中暴露的问题)

(待实测后填)

## 4. Audit GAP 修复情况

| Audit GAP | post-visual-patterns 状态 |
|---|---|
| RAG 库利用率 | 直接修复(从 1 agent → 5 agent) |
| (其他 audit GAP) | 不变(本 spec 不涉及) |

## 5. 下一步(post-merge follow-up)

### 5.1 立刻启动:patterns 库扩库 spec
- patterns 21 → 50-100
- INDEX.md 重组按 content intent 分类
- 独立 PR,2-3 周

### 5.2 后续 backlog
- structured output / JSON schema 强制 (F4 hybrid finding)
- runtime.log 平台层 telemetry (F3 hybrid finding)
- 章节并行拓写 (audit B4 Layer 2)

## 6. 总结
(待实测后填)
```

- [ ] **Step 2:Commit**

Run:
```bash
git add docs/archive/2026-05-25-visual-patterns-5agent-postmortem.md
git commit -m "docs(archive): visual-patterns 5-agent RAG extension postmortem template

待实测后填:
- 5 处新字段触发情况
- RAG 命中率 / 用户接受率
- Token 增量实测
- Findings"
```

Expected:commit 成功。

---

# 完成验收

- [ ] **Step 1:全部 commit 检查**

Run:
```bash
git log --oneline pre-visual-patterns-5agent..HEAD
git tag --list | grep visual-patterns
wc -l .claude/pipeline-protocol.md   # 应该 387 + 新增几行
ls evals/agents/baseline/01-exec-decision-post-visual-patterns/
```

Expected:
- 看到 ~10 个 commits(每个 task 一个)
- 看到 pre + post 两个 tag
- pipeline-protocol.md 在 400-420 行(原 387 + 新增字段)
- baseline 目录有数据

- [ ] **Step 2:pytest 全套确认**

Run:
```bash
python3 -m pytest tests/ -q
```

Expected:72 passed。

- [ ] **Step 3:invoke finishing-a-development-branch skill** 让用户决定 merge / PR / 保留

Expected:进入收尾。

---

# 风险与回退

| 风险 | 应对 |
|---|---|
| Phase 1 协议字段 schema 写错 | `git revert <commit>` 重写 |
| Phase 2 某个 agent prompt 改坏 | 单 task revert(每个 task 独立 commit) |
| Phase 2 search.sh 全失败(library 不可用)| 各 agent 降级到 "search_failed" 状态,不阻塞实测继续 |
| Phase 4 fixture 跑不通 | 定位是哪个 agent yaml schema 偏差;主线程容错 parse;或单 task revert |
| token 增量超 100k | 降级:只保留 author + audience(回到原 ROI #1+#2),其他 3 个 revert |
| 21 库命中率太低 | postmortem 标 "follow-up: 立即启动扩库 spec" |
