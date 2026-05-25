# Hybrid Team + Subagent 架构迁移 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 iLovePPT 流水线从 6-agent team 模式迁移到 Hybrid 架构(brainstorm 保留 team / 其余 5 agent 转 subagent),解锁 telemetry,简化协议,保持端到端行为等价。

**Architecture:** Phase A(brainstorm team via TeamCreate/SendMessage)→ Phase B(author/critic/iloveppt/audience/extractor via Task tool,return yaml block 携带 next_action)。主线程 parse return yaml 决定下一步派发。

**Tech Stack:** Claude Code(TeamCreate / Task / Hook / SendMessage)、markdown(agent prompts、协议文档、产物)、python-pptx(已有 build 流水线,不动)、bash hooks(`.claude/settings.json`)。

**Spec:** `docs/archive/2026-05-25-hybrid-team-subagent-migration-design.md`(必读)
**Audit baseline:** `docs/agent-team-evaluation-checklist.zh.md`

---

## File Structure

### 改动文件总览

| 文件 | 动作 | 说明 |
|---|---|---|
| `.claude/pipeline-protocol.md` | **完全重写** | 新文件 ~250 行,§0-§6 hybrid 骨架 |
| `.claude/pipeline-protocol.team-legacy.md.bak` | **创建(临时)** | 旧文件改名备份,Phase 4 通过后删 |
| `.claude/agents/iloveppt-brainstorm.md` | **不动** | Hybrid 关键决策 — Phase A 保留 team |
| `.claude/agents/iloveppt-template-extractor.md` | 修改 | 转 subagent(删 SendMessage/idle 段) |
| `.claude/agents/iloveppt-critic.md` | 修改 | 转 subagent |
| `.claude/agents/iloveppt-audience.md` | 修改 | 转 subagent |
| `.claude/agents/iloveppt.md` | 修改 | 转 subagent |
| `.claude/agents/iloveppt-author.md` | 修改 | 转 subagent(改动量最大) |
| `CLAUDE.md` | 修改 | 派发规则段 + 二段论说明 |
| `.claude/settings.json` | 修改 | hook 增强,Phase B 利用 Task 元数据 |
| `README.md` | 修改 | 措辞调整 |
| `docs/agent-internals.zh.md` | 修改 | 同步二段论 |
| `docs/MANUAL.zh.md` | 修改 | 同步 |
| `docs/archive/2026-05-25-hybrid-migration-postmortem.md` | **创建** | Phase 5 记录决策与对比数据 |

### 验证用 fixture

- `evals/agents/fixtures/01-exec-decision`(已存在,Phase 0 / Phase 4 用)
- Phase 0 baseline 产物落到 `evals/agents/baseline/01-exec-decision-pre-hybrid/`(新建目录)
- Phase 4 新产物落到 `evals/agents/baseline/01-exec-decision-post-hybrid/`(新建目录)

### Git tag

- `pre-hybrid-migration` — Phase 0 末尾
- `post-hybrid-migration` — Phase 4 通过后

---

# Phase 0:安全网

**目标**:跑迁移前 baseline,留全套产物,打 git tag。任何后续 phase 失败可 revert 到这里。

---

## Task 0.1:确认 fixture 与目录就绪

**Files:**
- Check: `evals/agents/fixtures/01-exec-decision/`
- Check: `evals/agents/baseline/`
- Create: `evals/agents/baseline/01-exec-decision-pre-hybrid/`

- [ ] **Step 1:确认 fixture 存在**

Run:
```bash
ls evals/agents/fixtures/01-exec-decision/
```

Expected:看到 fixture 的 input 文件(brief 模拟输入 / expected.md 等)。如果目录为空,**停止整个 plan**,先去补 fixture。

- [ ] **Step 2:确认当前 main 分支干净**

Run:
```bash
git status
```

Expected:`working tree clean` 或仅有 `.claude/skills/pptx-deck/examples/sample_output.pptx` 等已知未追踪文件。**有未提交改动 → 先 commit 或 stash**。

- [ ] **Step 3:创建 pre-hybrid baseline 目录**

Run:
```bash
mkdir -p evals/agents/baseline/01-exec-decision-pre-hybrid/
```

Expected:目录创建成功,无 error。

---

## Task 0.2:跑当前 team 流水线 baseline

**Files:**
- Output: `evals/agents/baseline/01-exec-decision-pre-hybrid/*`

- [ ] **Step 1:在 Claude Code 主线程执行 fixture**

在 Claude Code 里输入 fixture 的标准 brief(从 `evals/agents/fixtures/01-exec-decision/` 读取模拟用户输入)。让流水线完整跑完(brainstorm → author Stage C → critic C → author Stage D → critic D → iloveppt → audience)。

由于这是 **manual fixture run**(需要人扮演用户回答 brainstorm 的 ask_user),建议:
- 用 `time` 包住整个 session 估算 wall-clock
- 全程留 Claude Code transcript(用 Claude Code 的 `/export` 或截屏)

- [ ] **Step 2:把所有产物复制到 baseline 目录**

Run(假设产物在 `decks/01-exec-decision-pre-hybrid/`):
```bash
cp -r decks/01-exec-decision-pre-hybrid/ evals/agents/baseline/01-exec-decision-pre-hybrid/products/
```

Expected:目录下应包含 `brainstorm/brief.md` + `author/outline_r*.md` + `author/content_r*.md` + `critic/critic_report_C_r*.md` + `critic/critic_report_D_r*.md` + `builder/deck_v*.pptx` + `builder/render/` + `audience/audience_review_r*.md`。

- [ ] **Step 3:留 telemetry 快照**

Run:
```bash
cp .claude/runtime.log evals/agents/baseline/01-exec-decision-pre-hybrid/runtime.log.pre
wc -l .claude/runtime.log
```

Expected:记录当前 runtime.log 行数(预期跟之前一样 ~5 行全 `agent=main`,作为 "team 模式 telemetry 不工作" 的证据)。

- [ ] **Step 4:写 baseline 元数据**

Create file `evals/agents/baseline/01-exec-decision-pre-hybrid/META.md`:
```markdown
# Pre-hybrid baseline · 01-exec-decision

- Date: <填实际日期>
- Mode: team (pre-migration)
- Wall-clock: <分钟>
- Total rounds:
  - brainstorm: <N>
  - critic Stage C: <N>
  - critic Stage D: <N>
  - audience: <N>
- Final audience overall_score: <N>
- Final critic Stage D verdict: <pass/pass_with_notes>
- Runtime.log usable: NO(全 agent=main,无 token/duration)
```

---

## Task 0.3:Git tag pre-hybrid-migration

- [ ] **Step 1:提交 baseline 产物**

Run:
```bash
git add evals/agents/baseline/01-exec-decision-pre-hybrid/
git commit -m "test(evals): add pre-hybrid baseline for 01-exec-decision"
```

Expected:commit 成功。

- [ ] **Step 2:打 tag**

Run:
```bash
git tag -a pre-hybrid-migration -m "Baseline before team→subagent hybrid migration"
git tag --list | grep pre-hybrid
```

Expected:看到 `pre-hybrid-migration` 出现在 tag 列表。

---

# Phase 1:协议层重写

**目标**:写新 pipeline-protocol.md(~250 行),旧文件改名备份。

---

## Task 1.1:备份旧协议文件

**Files:**
- Rename: `.claude/pipeline-protocol.md` → `.claude/pipeline-protocol.team-legacy.md.bak`

- [ ] **Step 1:重命名旧文件**

Run:
```bash
git mv .claude/pipeline-protocol.md .claude/pipeline-protocol.team-legacy.md.bak
```

Expected:旧文件已重命名,`git status` 显示一个 rename。

- [ ] **Step 2:验证文件位置**

Run:
```bash
ls .claude/pipeline-protocol*
```

Expected:看到 `.claude/pipeline-protocol.team-legacy.md.bak`,无 `.claude/pipeline-protocol.md`(还没创建)。

---

## Task 1.2:写新 pipeline-protocol.md §0 二段论

**Files:**
- Create: `.claude/pipeline-protocol.md`

- [ ] **Step 1:创建新文件并写入 §0**

Create `.claude/pipeline-protocol.md` 含以下内容:

```markdown
# iLovePPT Pipeline Protocol (Hybrid edition)

> 协议适用于:主线程派发 agent 时的派发规则、handoff 格式、gate 条件、失败处理。
> 不适用于:agent 内部行为(在各 agent 的 prompt 文件)。
>
> **架构**:Phase A team(brainstorm 多轮对话)+ Phase B subagent(其余 5 agent + extractor)。
> 设计 rationale:`docs/archive/2026-05-25-hybrid-team-subagent-migration-design.md`

---

## §0. 架构二段论

```
Phase A:收 brief(team 模式,持续窗口)
─────────────────────────────────────────
用户 "做 PPT"
   ↓
主线程 TeamCreate({agents: ["iloveppt-brainstorm"]})
   ↓ SendMessage(brainstorm, user_intent)
brainstorm team window 持续在线
   ↓ ask_user 多轮(单进程,state.json 跨轮恢复)
brainstorm Write brief.md
   ↓ SendMessage(main, next_action: dispatch_author, brief_md_path)
主线程关闭 brainstorm team

Phase B:流水线(subagent 模式,Task 调用)
─────────────────────────────────────────
主线程 Task(author, stage=C, brief_md_path)  → return yaml
用户审批 outline
主线程 Task(critic, stage=C)                  → return yaml(verdict)
主线程 Task(author, stage=D)                  → return yaml
用户审批 content
主线程 Task(critic, stage=D)                  → return yaml(verdict)
主线程 Task(iloveppt)                          → return yaml(pptx_path)
主线程 Task(audience)                          → return yaml(overall_score)
   loop until overall_score ≥ 9
```

**关键规则**:
- Phase A → Phase B 切换信号:brainstorm SendMessage 返回 `next_action: dispatch_author`
- 切换时主线程**立即关闭 brainstorm team**(YAGNI:audience 三类分流目前无回 brainstorm 路径)
- 模板 extractor 中途介入(用户在 Phase A 期间提供模板路径):主线程 `Task(extractor)` → return yaml → SendMessage 给仍在线的 brainstorm team
```

Expected:文件创建成功,§0 章节写入。

- [ ] **Step 2:验证 markdown 格式**

Run:
```bash
head -50 .claude/pipeline-protocol.md
```

Expected:看到 §0 完整内容,无格式错位。

---

## Task 1.3:写 §1 主线程派发表

- [ ] **Step 1:追加 §1 到 .claude/pipeline-protocol.md**

Append:
```markdown

---

## §1. 主线程派发表

| 触发条件 | 调谁 | 期望返回 next_action |
|---|---|---|
| "做 PPT" 意图 + brief.md 未生成 | `TeamCreate({agents: ["iloveppt-brainstorm"]})` → `SendMessage(brainstorm, user_intent)` | `ask_user` 或 `dispatch_author` |
| 用户答完 brainstorm 问题 | `SendMessage(brainstorm team, user_response)` | `ask_user` 或 `dispatch_author` |
| brainstorm `dispatch_author` 返回 | 关闭 brainstorm team → `Task(iloveppt-author, args={stage: "C", brief_md_path: ...})` | `ask_user_for_outline_approval` |
| outline.md 已批准 | `Task(iloveppt-critic, args={stage: "C", outline_md_path: ...})` | `pass` / `pass_with_notes` / `needs_revision` |
| critic C `pass` 或 `pass_with_notes` | `Task(iloveppt-author, args={stage: "D", outline_md_path: ..., critic_c_report: ...})` | `ask_user_for_content_approval` |
| content.md 已批准 | `Task(iloveppt-critic, args={stage: "D", content_md_path: ...})` | `pass` / `pass_with_notes` / `needs_revision` |
| critic D `pass` 或 `pass_with_notes` | `Task(iloveppt, args={content_md_path: ..., critic_d_report: ...})` | `dispatch_audience` 或 `hard_stop` |
| iloveppt `dispatch_audience` | `Task(iloveppt-audience, args={pptx_path: ..., render_dir: ...})` | `delivered` 或 `needs_*` |
| audience `delivered`(overall_score ≥ 9) | 主线程交付 .pptx 路径给用户 | — |
| audience `needs_author_rewrite` | `Task(iloveppt-author, args={stage: "D_rework", audience_report: ...})` | 同 author Stage D |
| audience `needs_visual_redo` | `Task(iloveppt, args={mode: "visual_redo", audience_report: ...})` | `dispatch_audience` |
| audience `needs_theme_fix` | 主线程跟用户确认改 theme(主线程自己干,不派 agent) | — |
| 用户提供模板路径(Phase A 期间) | `Task(iloveppt-template-extractor, args={template_path: ...})` → `SendMessage(brainstorm team, extractor_summary)` | extractor return `dispatch_brainstorm`;brainstorm 续聊 |
| critic `needs_revision`(任何 stage) | `Task(iloveppt-author, args={stage: <same>, critic_report: ...})` | 同 author Stage C/D |
```

Expected:§1 追加成功。

---

## Task 1.4:写 §2 Phase A 协议(brainstorm team)

- [ ] **Step 1:追加 §2 到 .claude/pipeline-protocol.md**

Append:
```markdown

---

## §2. Phase A 协议(brainstorm team 模式)

**适用范围仅限 brainstorm 这一个 agent**。其他 agent 全部走 Phase B(subagent)。

### §2.1 TeamCreate 参数

```python
TeamCreate({
    agents: ["iloveppt-brainstorm"],
    team_name: "brainstorm-<deck_slug>",  # 用 deck slug 区分多 deck 场景
})
```

主线程立即 `SendMessage(brainstorm, user_intent)` 触发 brainstorm 启动。

### §2.2 SendMessage 转发规则

brainstorm 在 ask_user 时返回 yaml(见 §4 schema):
```yaml
next_action: ask_user
message_to_user: |
  <原话>
questions:
  - <一行一问>
state_round: <int>
```

主线程**原话转发** `message_to_user` + `questions` 给用户(不用 `AskUserQuestion` 包装成结构化多选)。原因:brainstorm 是有性格的对话方,主线程只做透明转发。

用户回信后,主线程 `SendMessage(brainstorm team, user_response)`,brainstorm 续聊。

### §2.3 idle 通知规则

brainstorm 每轮处理完必须**在 idle 前**至少调一次 SendMessage(报 `ask_user` 或 `dispatch_*` 或 `error`)。idle 前没发消息 = brainstorm 这轮等于没干,主线程会以为卡死。

### §2.4 state.json 跨轮恢复

brainstorm 维护 `decks/<slug>/brainstorm/state.json`,记录 `round` / `collected` / `asset_inventory` / `brief_md_path` / `brief_approved`。每轮 brainstorm 启动时先 Read 该文件重建 context。

### §2.5 软上限

`brainstorm/state.json` 里 `round` 字段每轮 +1。主线程在 `round >= 10` 时,转发 brainstorm 问题前**附加一行**给用户:

> "我们已经聊到第 10 轮还没收齐字段。要继续答,还是直接让 author 用当前已知信息开工(缺的字段走默认值)?"

用户选叫停 → 主线程 SendMessage 给 brainstorm `{force_dispatch: true}`,brainstorm 用 state 里已有字段 + 默认值组装 brief,直接 `dispatch_author`。

### §2.6 阶段切换信号

brainstorm 返回 `next_action: dispatch_author` → 主线程**立即关闭 brainstorm team**,转 Phase B:

```python
# 关闭 team(具体 API 视 Claude Code 实现)
# 然后启动 Phase B
Task(iloveppt-author, args={stage: "C", brief_md_path: <from yaml>})
```

### §2.7 brief.md gate

brainstorm 在返回 `dispatch_author` **之前**必须完成两步(brainstorm prompt 内部逻辑,主线程不感知):
1. 先 `Write brief.md`(文件落盘成功)
2. 后返回 `ask_user` 让用户在 brief.md 直接编辑或回复 OK

用户回 OK 后,brainstorm 下次 SendMessage 返回 `dispatch_author`。
```

Expected:§2 追加成功。

---

## Task 1.5:写 §3 Phase B 协议(subagent 流水线)

- [ ] **Step 1:追加 §3 到 .claude/pipeline-protocol.md**

Append:
```markdown

---

## §3. Phase B 协议(subagent 流水线)

**适用范围**:author / critic / iloveppt / audience / extractor 这 5 个 agent。

### §3.1 Task 调用方式

```python
Task(<agent-name>, args={...})
# 同步等待 agent 跑完,return 是一段文本
```

主线程拿到 return text 后,**parse 文本最后一段的 ```yaml ``` block** 决策下一步。yaml 之前的 summary 文本是给人看的(进 log,不影响决策)。

### §3.2 handoff yaml schema

见 §4(完整 schema)。所有 Phase B agent 的 return 都遵循这个 schema。

### §3.3 Gate 规则

| Gate | 通过条件 |
|---|---|
| outline.md 用户审批 | 主线程展示 outline.md 摘要,用户回 OK / 在文件直接改 |
| content.md 用户审批 | 同上 |
| critic verdict | `pass` 或 `pass_with_notes` |
| audience overall_score | ≥ 9 |
| 5 轮 cap | critic Stage C / Stage D / audience 各独立计数,达 5 轮强制询问用户四选一(继续 / 接受当前 / 回 outline / 终止) |

### §3.4 Pyramid 3 层防线

content / structure 质量靠三层冗余防线(质量优先,接受冗余):
1. author 自检(Stage D 内部 Pyramid 7 项)
2. critic A1-A7(Stage C 评 outline / Stage D 评 content)
3. iloveppt Step 0 在 build 前最后一次 Pyramid 自检

任一层 fail 都拦截下一步。Step 0 fail → `next_action: hard_stop`,主线程问用户三选一(按 suggestion 改 / 自己指令 / 终止)。

### §3.5 错误传播

agent 内部错误必须返回:
```yaml
status: error
errors:
  - code: <enum>
    message: <human readable>
    suggestion: <next step>
```

主线程展示 errors 给用户,问三选一(重试 / 跳过 / 终止)。**不自动重试**。

### §3.6 subagent 进程级失败

Task 工具返回 timeout / crash → 主线程 abort 并提示用户。**无自动 retry**。
```

Expected:§3 追加成功。

---

## Task 1.6:写 §4 handoff yaml schema(完整版)

- [ ] **Step 1:追加 §4 到 .claude/pipeline-protocol.md**

Append:
````markdown

---

## §4. handoff yaml schema(Phase A SendMessage / Phase B Task return 共用)

### §4.1 通用顶层字段

每个 agent return 的最后 yaml block 必须含:

```yaml
agent: <agent-name>          # 谁返回的(brainstorm/author/critic/iloveppt/audience/extractor)
status: ok | error           # 这轮跑没跑成
next_action: <enum>          # 主线程下一步该做什么(见各 agent 枚举)
errors: []                   # status=error 时填,数组每项含 code/message/suggestion
artifacts:                   # 本轮产物(可空)
  - path: <abs path>
    kind: brief_md | outline_md | content_md | critic_report | audience_report | pptx | render_dir | yaml
```

### §4.2 各 agent next_action 枚举

(同 §1 派发表,这里强调 agent 侧返回什么 vs 主线程做什么)

| agent | next_action | 主线程动作 |
|---|---|---|
| brainstorm (team) | `ask_user` | 转发 message_to_user + questions 原文给用户 |
| brainstorm (team) | `dispatch_extractor` | Task(extractor),return 后 SendMessage 回 brainstorm team |
| brainstorm (team) | `dispatch_author` | **关闭 brainstorm team**,Task(author, stage=C) |
| extractor | `dispatch_brainstorm` | SendMessage 给仍在线的 brainstorm team(传 extractor 摘要);若 team 已关 → 先 TeamCreate 重启 |
| author | `ask_user_for_outline_approval` | 给 outline.md 路径,等用户 OK |
| author | `ask_user_for_content_approval` | 给 content.md 路径,等用户 OK |
| author | `dispatch_critic` | Task(critic, args 含 stage=C/D + outline_md_path 或 content_md_path) |
| critic | `pass` | 转下一棒(详见 §1 派发表) |
| critic | `pass_with_notes` | 展示 notes 给用户做 cherry-pick,然后转下一棒 |
| critic | `needs_revision` | Task(author) 带 critic 报告路径 |
| iloveppt | `dispatch_audience` | Task(audience) |
| iloveppt | `hard_stop` | 展示 errors 给用户三选一 |
| audience | `delivered` | 交付 .pptx 给用户 |
| audience | `needs_author_rewrite` | Task(author) |
| audience | `needs_visual_redo` | Task(iloveppt, mode=visual_redo) |
| audience | `needs_theme_fix` | 主线程跟用户确认改 theme |

### §4.3 agent 特有字段

**brainstorm 的 ask_user**(Phase A SendMessage 消息体):
```yaml
agent: iloveppt-brainstorm
status: ok
next_action: ask_user
message_to_user: |
  <brainstorm 给用户的原话,保留 brainstorm 的"性格"措辞>
questions:
  - <一行一问>
state_round: <int>
collected_summary: <一句话总结当前已收字段>
```

**brainstorm 的 dispatch_author**:
```yaml
agent: iloveppt-brainstorm
status: ok
next_action: dispatch_author
artifacts:
  - path: <abs path to brief.md>
    kind: brief_md
brief_summary: <一句话 brief 概要>
```

**critic 必加字段**:
```yaml
agent: iloveppt-critic
status: ok
next_action: pass | pass_with_notes | needs_revision
stage: C | D
verdict: pass | pass_with_notes | needs_revision  # 等同 next_action,冗余便于读
artifacts:
  - path: <abs path to critic_report_C_r{N}.md or critic_report_D_r{N}.md>
    kind: critic_report
issues:
  - severity: high | med | low
    section: <文档章节>
    description: <一句话>
    suggestion: <修改建议>
rounds_used: <int>  # 当前 stage 第几轮
```

**audience 必加字段**:
```yaml
agent: iloveppt-audience
status: ok
next_action: delivered | needs_author_rewrite | needs_visual_redo | needs_theme_fix
overall_score: <int 1-10>
verdict: excellent | good | needs_minor | needs_major
triage: needs_author_rewrite | needs_visual_redo | needs_theme_fix | none
artifacts:
  - path: <abs path to audience_review_r{N}.md>
    kind: audience_report
per_page_scores:
  - page: <int>
    comprehension_5s: <int 1-10>
    info_density: <int 1-10>
    visual_appeal: <int 1-10>
    flow_coherence: <int 1-10>
rounds_used: <int>
```

**iloveppt 必加字段**:
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

**extractor 必加字段**:
```yaml
agent: iloveppt-template-extractor
status: ok | error
next_action: dispatch_brainstorm
artifacts:
  - path: <abs path to extractor_summary.yaml>
    kind: yaml
template_ready: true | false
summary: |
  <一段给 brainstorm 看的模板摘要:有什么 layout / 媒体数 / 主色调>
```

**author 必加字段**:
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
````

Expected:§4 追加成功,所有 6 个 agent 的 yaml schema 都有完整例子。

---

## Task 1.7:写 §5 工作目录与产物 + §6 派发禁区

- [ ] **Step 1:追加 §5 §6 到 .claude/pipeline-protocol.md**

Append:
```markdown

---

## §5. 工作目录与产物

```
decks/<slug>/
├── brainstorm/
│   ├── state.json              # 跨 ask_user 轮恢复(仅 Phase A 用)
│   └── brief.md                # brainstorm 产出,user 审批后冻结
├── extractor/                  # 可选,用户提供模板时
│   ├── extractor_summary.yaml
│   └── media/                  # 模板媒体抽取
├── author/
│   ├── outline_r{N}.md         # 每轮编号保留(_r1, _r2, ...)
│   └── content_r{N}.md
├── critic/
│   ├── critic_report_C_r{N}.md
│   └── critic_report_D_r{N}.md
├── builder/
│   ├── deck_v{N}.pptx
│   ├── deck_plan_v{N}.json
│   └── render/                 # PNG 渲染
└── audience/
    └── audience_review_r{N}.md
```

**关键规则**:
- 每轮产物用 `_r{N}.md` 编号保留,不覆盖(便于事后追溯 / git diff)
- `state.json` 仅 brainstorm 用(Phase A 单 agent 跨 ask_user 恢复)
- Phase B agent 不维护跨 turn state(每次 Task 调用都是新 context,所需信息从 artifacts 路径读)

---

## §6. 主线程派发禁区

### §6.1 必须派 agent 的场景

- "做 PPT" 意图首次出现 → 必须 TeamCreate(brainstorm),**不允许**主线程自己写 brief
- brief 完成后任何阶段 → 必须 Task 对应 agent,**不允许**主线程自己写 outline / content / 跑 QA / 加视觉资产

### §6.2 主线程直接干的场景

- 改仓库代码(helpers.py / themes / build.py / tests / agent prompts / 协议文档) → 主线程直接干(跨文件一致性)
- trivial rebuild(< 3 页改动,且仅微调,无新增章节) → 主线程可直接跑 `python3 .claude/skills/pptx-deck/build.py <deck_plan.json>`,不必派 iloveppt
- 用户问问题 / 解释 / 调试 → 主线程直接答(不需要派 agent)

### §6.3 主线程禁忌

- 不允许在该 delegate 的任务上自己动手("快"心态导致越权)
- 不允许跳过 user-in-loop gate(brief / outline / content / 9 分阈值)
- 不允许并行 dispatch 互相依赖的 agent(例:critic 还没 pass 就 Task iloveppt)
- 不允许吃掉 agent 的 error(必须展示给用户三选一)
```

Expected:§5 §6 追加成功。

- [ ] **Step 2:验证行数**

Run:
```bash
wc -l .claude/pipeline-protocol.md
```

Expected:总行数在 250-350 之间。若 < 200 → 某段写漏了;若 > 400 → 写啰嗦了,精简。

- [ ] **Step 3:Commit Phase 1**

Run:
```bash
git add .claude/pipeline-protocol.md .claude/pipeline-protocol.team-legacy.md.bak
git commit -m "feat(protocol): rewrite pipeline-protocol for hybrid team+subagent architecture"
```

Expected:commit 成功。

---

# Phase 2:5 个 agent prompt 改造

**目标**:把 extractor / critic / audience / iloveppt / author 转 subagent。brainstorm 不动。

**通用改造模板**(每个 task 都用):

**删除段**:
- "idle 前必须 SendMessage" 段
- agent 自己用 SendMessage 跟 main 通信的协议(subagent 通过 Task return 传 yaml,不发 SendMessage)
- "你的 transcript 对 team-lead 不可见" 类描述
- 窗口生命周期相关("每轮新建" / "跑完关闭" — 因为 subagent 天然如此)

**新增段**(每个 agent 都加):
```markdown
## Output format

你是 subagent,通过 Task 工具被主线程调用。你的输出(return text)的**最后一段必须是** ` ```yaml ``` ` block,主线程只 parse 这一段做决策。yaml 之前的文本是给人看的 summary,进 log 不影响决策。

yaml schema 见 `.claude/pipeline-protocol.md` §4(本 agent 的特有字段段)。

示例 return:

<人话 summary,~3-5 句>

```yaml
agent: <agent-name>
status: ok
next_action: <enum>
artifacts:
  - path: <abs path>
    kind: <kind>
<本 agent 特有字段>
```
```

**保留段**:职责定义、五件套(objective / output format / tool guidance / task boundary / effort scaling)、工具权限清单、agent 内部步骤、失败处理。

---

## Task 2.1:转 extractor 为 subagent

**Files:**
- Modify: `.claude/agents/iloveppt-template-extractor.md`

- [ ] **Step 1:读取当前 extractor prompt 找需要改的段**

Run:
```bash
grep -n "SendMessage\|idle\|team-lead\|窗口" .claude/agents/iloveppt-template-extractor.md
```

Expected:列出所有 team-specific 行。记下行号准备改。

- [ ] **Step 2:删 idle 前必须 SendMessage 段**

定位类似这段:
```markdown
2. idle 前**必须至少**发一次 SendMessage(本 agent 报 ...,失败也要发),否则 team-lead 以为你卡死
```

替换为:
```markdown
2. 本 agent 是 subagent,通过 Task 工具调用,return text 最后一段必须是 ```yaml ``` block(见 Output format 段)
```

- [ ] **Step 3:加 Output format 段**

在 prompt 合适位置(通常在"职责"段之后)插入:
````markdown
## Output format

你是 subagent,通过 Task 工具被主线程调用。你的输出(return text)的**最后一段必须是** ```yaml ``` block,主线程只 parse 这一段做决策。yaml 之前的文本是给人看的 summary。

yaml schema 见 `.claude/pipeline-protocol.md` §4(extractor 特有字段)。

示例 return:

我跑完了模板摄入。共抽出 14 个媒体文件,识别 3 种 layout(cover, content, summary)。模板主色调:#003366。摘要写到 `decks/<slug>/extractor/extractor_summary.yaml`。

```yaml
agent: iloveppt-template-extractor
status: ok
next_action: dispatch_brainstorm
artifacts:
  - path: <abs path to extractor_summary.yaml>
    kind: yaml
template_ready: true
summary: |
  共 14 个媒体文件 / 3 种 layout / 主色 #003366
```
````

- [ ] **Step 4:验证改动**

Run:
```bash
grep -c "SendMessage" .claude/agents/iloveppt-template-extractor.md
grep -c "Output format" .claude/agents/iloveppt-template-extractor.md
```

Expected:`SendMessage` count = 0(已删干净);`Output format` count = 1(新增段存在)。

- [ ] **Step 5:Commit**

Run:
```bash
git add .claude/agents/iloveppt-template-extractor.md
git commit -m "refactor(agent): convert template-extractor to subagent (Task return yaml)"
```

Expected:commit 成功。

---

## Task 2.2:转 critic 为 subagent

**Files:**
- Modify: `.claude/agents/iloveppt-critic.md`

- [ ] **Step 1:读取当前 critic prompt 找需要改的段**

Run:
```bash
grep -n "SendMessage\|idle\|team-lead\|窗口" .claude/agents/iloveppt-critic.md
```

Expected:列出 team-specific 行。

- [ ] **Step 2:删 idle 前必须 SendMessage 段**

定位类似 line 56:
```markdown
2. idle 前**必须至少**发一次 SendMessage(本 agent 报 **verdict / report 路径 / 错误**),否则 team-lead 以为你卡死
```

替换为:
```markdown
2. 本 agent 是 subagent,通过 Task 工具调用,return text 最后一段必须是 ```yaml ``` block(见 Output format 段),含 verdict / report 路径 / 错误
```

- [ ] **Step 3:加 Output format 段**

插入:
````markdown
## Output format

你是 subagent,通过 Task 工具被主线程调用。你的输出(return text)的**最后一段必须是** ```yaml ``` block,主线程只 parse 这一段做决策。yaml 之前的文本是给人看的 summary。

yaml schema 见 `.claude/pipeline-protocol.md` §4(critic 特有字段)。

示例 return(verdict = pass_with_notes):

我评了 Stage D content。A1-A7 金字塔检查全过;B1-B7 brief 对齐 6 过 1 中等(B5 用户痛点表述偏弱);4 维度判断:论据强度 8/10、节奏 7/10、措辞 8/10、平衡 9/10。建议接受 pass_with_notes,3 项 medium 建议见报告。报告写到 `decks/<slug>/critic/critic_report_D_r1.md`。

```yaml
agent: iloveppt-critic
status: ok
next_action: pass_with_notes
stage: D
verdict: pass_with_notes
artifacts:
  - path: <abs path to critic_report_D_r1.md>
    kind: critic_report
issues:
  - severity: med
    section: §3 痛点
    description: 用户痛点表述偏弱,缺乏具体场景
    suggestion: 加 1-2 个用户原话引用
  - severity: med
    section: §4 方案
    description: ...
    suggestion: ...
rounds_used: 1
```
````

- [ ] **Step 4:验证改动**

Run:
```bash
grep -c "SendMessage" .claude/agents/iloveppt-critic.md
grep -c "Output format" .claude/agents/iloveppt-critic.md
```

Expected:`SendMessage` count = 0;`Output format` count = 1。

- [ ] **Step 5:Commit**

Run:
```bash
git add .claude/agents/iloveppt-critic.md
git commit -m "refactor(agent): convert critic to subagent (Task return yaml)"
```

Expected:commit 成功。

---

## Task 2.3:转 audience 为 subagent

**Files:**
- Modify: `.claude/agents/iloveppt-audience.md`

- [ ] **Step 1:读取当前 audience prompt 找需要改的段**

Run:
```bash
grep -n "SendMessage\|idle\|team-lead\|窗口" .claude/agents/iloveppt-audience.md
```

- [ ] **Step 2:删 idle 前必须 SendMessage 段**

定位类似 line 83:
```markdown
2. idle 前**必须至少**发一次 SendMessage(本 agent 报 **评分 / review.md 路径 / 错误**),否则 team-lead 以为你卡死
```

替换为:
```markdown
2. 本 agent 是 subagent,通过 Task 工具调用,return text 最后一段必须是 ```yaml ``` block(见 Output format 段),含 overall_score / review.md 路径 / triage
```

- [ ] **Step 3:加 Output format 段**

插入:
````markdown
## Output format

你是 subagent,通过 Task 工具被主线程调用。你的输出(return text)的**最后一段必须是** ```yaml ``` block,主线程只 parse 这一段做决策。yaml 之前的文本是给人看的 summary。

yaml schema 见 `.claude/pipeline-protocol.md` §4(audience 特有字段)。

示例 return(overall_score = 8,需要 visual redo):

我作为目标 CTO 受众读完 12 页 deck。整体 overall 8/10。优点:论证逻辑清晰、章节扉页醒目。问题:§4 方案页文字密度过高(11/15 行),§7 数据图配色对比不足,5 秒内抓不到 key takeaway。triage 判断为 needs_visual_redo(文字基本 OK,主要是视觉)。报告写到 `decks/<slug>/audience/audience_review_r1.md`。

```yaml
agent: iloveppt-audience
status: ok
next_action: needs_visual_redo
overall_score: 8
verdict: good
triage: needs_visual_redo
artifacts:
  - path: <abs path to audience_review_r1.md>
    kind: audience_report
per_page_scores:
  - page: 4
    comprehension_5s: 5
    info_density: 4
    visual_appeal: 6
    flow_coherence: 8
  - page: 7
    comprehension_5s: 6
    info_density: 7
    visual_appeal: 5
    flow_coherence: 8
rounds_used: 1
```
````

- [ ] **Step 4:验证改动**

Run:
```bash
grep -c "SendMessage" .claude/agents/iloveppt-audience.md
grep -c "Output format" .claude/agents/iloveppt-audience.md
```

Expected:`SendMessage` count = 0;`Output format` count = 1。

- [ ] **Step 5:Commit**

Run:
```bash
git add .claude/agents/iloveppt-audience.md
git commit -m "refactor(agent): convert audience to subagent (Task return yaml)"
```

Expected:commit 成功。

---

## Task 2.4:转 iloveppt 为 subagent

**Files:**
- Modify: `.claude/agents/iloveppt.md`

- [ ] **Step 1:读取当前 iloveppt prompt 找需要改的段**

Run:
```bash
grep -n "SendMessage\|idle\|team-lead\|窗口" .claude/agents/iloveppt.md
```

- [ ] **Step 2:删 idle 前必须 SendMessage 段**

定位类似 line 36:
```markdown
2. idle 前**必须至少**发一次 SendMessage(本 agent 报 **完成 / hard stop ... / auto_md_edits / 错误**),否则 team-lead 以为你卡死
```

替换为:
```markdown
2. 本 agent 是 subagent,通过 Task 工具调用,return text 最后一段必须是 ```yaml ``` block(见 Output format 段),含 pptx_path / visual_qa / pyramid_check / hard_stop 或错误
```

- [ ] **Step 3:加 Output format 段**

插入:
````markdown
## Output format

你是 subagent,通过 Task 工具被主线程调用。你的输出(return text)的**最后一段必须是** ```yaml ``` block,主线程只 parse 这一段做决策。yaml 之前的文本是给人看的 summary。

yaml schema 见 `.claude/pipeline-protocol.md` §4(iloveppt 特有字段)。

示例 return(成功 build + Step 4 视觉增强完成):

我跑完 Step 0-4:Step 0 Pyramid 自检过、Step 1 md→JSON 转换 14 页、Step 2 build 出 .pptx、Step 3 视觉 QA(17/17 项过)、Step 4 视觉增强(icon × 8 / hero × 2 / brand × 1)。.pptx 路径 `decks/<slug>/builder/deck_v1.pptx`,render PNG 在 `decks/<slug>/builder/render/`。

```yaml
agent: iloveppt
status: ok
next_action: dispatch_audience
artifacts:
  - path: <abs path to deck_v1.pptx>
    kind: pptx
  - path: <abs path to render dir>
    kind: render_dir
build_iterations: 1
pyramid_check: passed
visual_qa:
  passed: 17
  total: 17
```

示例 return(Pyramid fail 触发 hard_stop):

我在 Step 0 Pyramid 自检发现 A3(全文动宾一致)失败,§4 方案 3 个 bullet 名词性混入动宾。建议 hard_stop,让 author 改后重派。

```yaml
agent: iloveppt
status: ok
next_action: hard_stop
pyramid_check: failed
errors:
  - code: pyramid_a3_fail
    message: §4 方案有 3 个 bullet 名词性混入动宾
    suggestion: dispatch author 改 content §4 §5 bullet 句式后重派
```
````

- [ ] **Step 4:验证改动**

Run:
```bash
grep -c "SendMessage" .claude/agents/iloveppt.md
grep -c "Output format" .claude/agents/iloveppt.md
```

Expected:`SendMessage` count = 0;`Output format` count = 1。

- [ ] **Step 5:Commit**

Run:
```bash
git add .claude/agents/iloveppt.md
git commit -m "refactor(agent): convert iloveppt builder to subagent (Task return yaml)"
```

Expected:commit 成功。

---

## Task 2.5:转 author 为 subagent

**Files:**
- Modify: `.claude/agents/iloveppt-author.md`

**注意**:author 是 5 个改造里最复杂的,因为 Stage C 和 Stage D 各自需要 return yaml(两个不同 next_action)。

- [ ] **Step 1:读取当前 author prompt 找需要改的段**

Run:
```bash
grep -n "SendMessage\|idle\|team-lead\|窗口\|主线程会再派我一次" .claude/agents/iloveppt-author.md
```

- [ ] **Step 2:删 idle 前必须 SendMessage 段**

定位类似 line 62:
```markdown
2. idle 前**必须至少**发一次 SendMessage(本 agent 报 **ask_user / dispatch / 错误**),否则 team-lead 以为你卡死
```

替换为:
```markdown
2. 本 agent 是 subagent,通过 Task 工具调用,return text 最后一段必须是 ```yaml ``` block(见 Output format 段)。Stage C 和 Stage D 各自一次 Task 调用,return 各自一份 yaml。
```

- [ ] **Step 3:删 Stage C/D 硬隔离原因段(改措辞)**

原 line 354 段:
```markdown
- **Stage C 与 Stage D 硬隔离**:Stage C 批准后**返回主线程**(`stage_c_approved`),不在同一次派发里续 Stage D
```

替换为:
```markdown
- **Stage C 与 Stage D 是两次独立 Task 调用**(自然实现"硬隔离"):Stage C return `ask_user_for_outline_approval`;用户批准后主线程再 Task 调一次,stage=D
```

- [ ] **Step 4:加 Output format 段(双示例)**

插入:
````markdown
## Output format

你是 subagent,通过 Task 工具被主线程调用。你的输出(return text)的**最后一段必须是** ```yaml ``` block,主线程只 parse 这一段做决策。yaml 之前的文本是给人看的 summary。

yaml schema 见 `.claude/pipeline-protocol.md` §4(author 特有字段)。

### Stage C return 示例(outline 生成完):

我按 brief 生成了 outline。14 章节、Pyramid 3 层(背景 / 问题-方案-验证 / 总结-CTA)、ghost deck 测试通过。outline 写到 `decks/<slug>/author/outline_r1.md`,请用户审。

```yaml
agent: iloveppt-author
status: ok
next_action: ask_user_for_outline_approval
stage: C
artifacts:
  - path: <abs path to outline_r1.md>
    kind: outline_md
rounds_used: 1
```

### Stage D return 示例(content 拓写完):

我按 outline 拓写了 content。14 章节全文 3200 字,Pyramid 自检 7 项过(action title 全动宾、bullet 句式统一、数字 > 形容词)。配 4 张图(matplotlib × 2 + draw.io × 2)。content 写到 `decks/<slug>/author/content_r1.md`,请用户审。

```yaml
agent: iloveppt-author
status: ok
next_action: ask_user_for_content_approval
stage: D
artifacts:
  - path: <abs path to content_r1.md>
    kind: content_md
rounds_used: 1
pyramid_self_check: passed
```

### dispatch_critic return 示例(用户批准 outline/content 后):

content 已通过用户审批。请主线程 Task critic 评 Stage D。

```yaml
agent: iloveppt-author
status: ok
next_action: dispatch_critic
stage: D
artifacts:
  - path: <abs path to content_r1.md>
    kind: content_md
rounds_used: 1
```
````

- [ ] **Step 5:验证改动**

Run:
```bash
grep -c "SendMessage" .claude/agents/iloveppt-author.md
grep -c "Output format" .claude/agents/iloveppt-author.md
```

Expected:`SendMessage` count = 0;`Output format` count = 1。

- [ ] **Step 6:Commit**

Run:
```bash
git add .claude/agents/iloveppt-author.md
git commit -m "refactor(agent): convert author to subagent (Stage C/D as two Task calls)"
```

Expected:commit 成功。

---

# Phase 3:主线程入口改造

**目标**:CLAUDE.md 派发规则同步;hook 增强 Phase B telemetry。

---

## Task 3.1:CLAUDE.md 派发规则段更新

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1:更新 "Agent 流水线" 段说明二段论**

定位 line 71-95(架构 → Agent 流水线 节)。把 "5 agent + 1 旁路" 描述更新,加二段论说明。

替换原段(line 73-94 大致):
```markdown
### Agent 流水线(5 agent + 1 旁路)

`${CLAUDE_PROJECT_DIR}/.claude/agents/` 是项目的运行时流水线。**模型分层**:critic / iloveppt 用 opus(深度推理 / 多职责),author / brainstorm / audience 用 sonnet,template-extractor 用 haiku。

| agent | 角色 | model |
|---|---|---|
| `iloveppt-brainstorm` | Stage A-B:多轮对话收 brief + 素材,出 brief.md 让用户确认 | sonnet |
...
```

改为:
```markdown
### Agent 流水线(Hybrid:1 team + 5 subagent + 1 旁路 subagent)

`${CLAUDE_PROJECT_DIR}/.claude/agents/` 是项目的运行时流水线,**Hybrid 架构**:

- **Phase A (team 模式)**:brainstorm 用 `TeamCreate` 持续窗口,多轮 SendMessage 跟用户聊收 brief。
- **Phase B (subagent 模式)**:author / critic / iloveppt / audience / template-extractor 用 `Task` 工具调用,每次跑完 return yaml(主线程 parse 决定下一步)。

**模型分层**:critic / iloveppt 用 opus(深度推理 / 多职责),author / brainstorm / audience 用 sonnet,template-extractor 用 haiku。

| agent | 角色 | 调用方式 | model |
|---|---|---|---|
| `iloveppt-brainstorm` | Stage A-B:多轮对话收 brief + 素材,出 brief.md | TeamCreate(team) | sonnet |
| `iloveppt-author` | Stage C-D:出 outline.md + 拓写 content.md(两次独立 Task) | Task | sonnet |
| `iloveppt-critic` | Stage C/D 各一次,partner 评审 | Task | opus |
| `iloveppt` | Stage E:机械 build + 视觉 QA + 视觉增强 | Task | opus |
| `iloveppt-audience` | 模拟受众读 deck 评分(9 分硬阈值) | Task | sonnet |
| `iloveppt-template-extractor` | 旁路:摄入 .pptx 模板 token | Task | haiku |

阶段切换信号:brainstorm SendMessage 返回 `next_action: dispatch_author` → 主线程关闭 brainstorm team → Task(author, stage=C) 进入 Phase B。
```

- [ ] **Step 2:更新 "主线程派发规则" 段**

定位 line 96-100(主线程派发规则 节)。把现有一句话总结更新:

原:
```markdown
### 主线程派发规则(一句话总结)

用户表达"做 PPT"意图时 → 主线程**必须** `TeamCreate` 建 team 并派 agent(**不要**自己写 brief / 写 content / 跑视觉 QA)。改仓库代码(helpers.py / themes / build.py / tests)时 → 主线程直接干(跨文件一致性)。
```

改为:
```markdown
### 主线程派发规则(一句话总结)

用户表达"做 PPT"意图时 → 主线程**必须**先 `TeamCreate(brainstorm)` 跑 Phase A,brainstorm `dispatch_author` 后关闭 team,转 `Task` 调 author/critic/iloveppt/audience 跑 Phase B(**不要**自己写 brief / 写 content / 跑视觉 QA)。改仓库代码(helpers.py / themes / build.py / tests / agent prompts / 协议文档)时 → 主线程直接干(跨文件一致性)。

完整派发表 + 理由:见 [pipeline protocol §1](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md#1-主线程派发表)。
```

- [ ] **Step 3:验证 CLAUDE.md 改动**

Run:
```bash
grep -n "Hybrid\|Task\|Phase A\|Phase B" CLAUDE.md
```

Expected:看到二段论关键词都出现。

- [ ] **Step 4:Commit**

Run:
```bash
git add CLAUDE.md
git commit -m "docs(CLAUDE): update dispatch rules for hybrid architecture"
```

Expected:commit 成功。

---

## Task 3.2:settings.json hook 增强

**Files:**
- Modify: `.claude/settings.json`

- [ ] **Step 1:读现有 hook 配置**

Run:
```bash
cat .claude/settings.json
```

Expected:看到当前 Stop hook 的 command(预期是 `printf` 输出 timestamp + agent + session 到 runtime.log)。

- [ ] **Step 2:增强 Stop hook 利用 Task 元数据**

把现有 Stop hook command 改为支持 Phase A / Phase B 双格式。具体 hook 改动取决于 Claude Code 暴露给 hook 的环境变量。

如果 Claude Code Task 完成时把 `token_usage_input` / `token_usage_output` / `duration_ms` 注入 hook 环境:
```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "printf '%s | agent=%s | session=%s | input_tokens=%s | output_tokens=%s | duration_ms=%s\\n' \"$(date -u +%FT%TZ)\" \"${CLAUDE_AGENT_NAME:-main}\" \"${CLAUDE_SESSION_ID:-unknown}\" \"${CLAUDE_TOKEN_INPUT:-na}\" \"${CLAUDE_TOKEN_OUTPUT:-na}\" \"${CLAUDE_DURATION_MS:-na}\" >> .claude/runtime.log"
          }
        ]
      }
    ]
  }
}
```

**注意**:Claude Code hook 环境变量名以实际为准。如果 Claude Code 没暴露 token / duration,这一步只能保持现有 hook,Phase B telemetry 需通过其他方式补(例如 subagent prompt 内部 echo 自报)。**Phase 4 验证时如果 telemetry 仍是空的,在 postmortem 里记录这一发现**。

- [ ] **Step 3:验证 hook 配置 JSON 合法**

Run:
```bash
python3 -c "import json; json.load(open('.claude/settings.json'))"
```

Expected:无 error,JSON 合法。

- [ ] **Step 4:Commit**

Run:
```bash
git add .claude/settings.json
git commit -m "feat(hook): enhance Stop hook to record token/duration for subagent telemetry"
```

Expected:commit 成功。

---

## Task 3.3:小烟测验证 hook 工作

**Files:**
- Check: `.claude/runtime.log`

- [ ] **Step 1:清空 runtime.log 准备观察**

Run:
```bash
> .claude/runtime.log
wc -l .claude/runtime.log
```

Expected:0 行。

- [ ] **Step 2:跑一个简单的 Task 调用做烟测**

在 Claude Code 主线程跑:
```
请 Task 调用 iloveppt-critic,args 给个最小的 fake input(就是让它 return error: missing_input),只验证 hook 是否工作。
```

(具体怎么触发取决于 Claude Code 用法。如果 Phase 2 改完 critic 后,critic 看到 fake input 会立即 return error yaml。)

- [ ] **Step 3:检查 runtime.log**

Run:
```bash
cat .claude/runtime.log
```

Expected:看到至少 2 行,一行 `agent=main`,一行 `agent=iloveppt-critic`。如果有 token / duration 字段,best case;如果仍是 na,在 Phase 5 postmortem 记录。

**如果 runtime.log 仍全 main**:hook 注入失败,Phase B telemetry 收益打折扣,继续 Phase 4 但 Phase 5 postmortem 里记录此 limitation。

---

# Phase 4:验证 + baseline 对比

**目标**:跑 Phase 0 同一 fixture,新流水线产出对比 baseline,通过则打 tag。

---

## Task 4.1:跑新流水线 fixture

**Files:**
- Output: `evals/agents/baseline/01-exec-decision-post-hybrid/`

- [ ] **Step 1:创建 post-hybrid baseline 目录**

Run:
```bash
mkdir -p evals/agents/baseline/01-exec-decision-post-hybrid/
```

- [ ] **Step 2:重置 runtime.log 准备记录**

Run:
```bash
cp .claude/runtime.log evals/agents/baseline/01-exec-decision-post-hybrid/runtime.log.before
> .claude/runtime.log
```

- [ ] **Step 3:跑同一 fixture(新流水线)**

在 Claude Code 主线程跑 Phase 0 同一 fixture 的标准 brief。预期流程:
1. 主线程 TeamCreate(brainstorm) → Phase A 对话
2. brief 批准 → 主线程关闭 team → Task(author, stage=C)
3. 用户审 outline → Task(critic, stage=C)
4. critic pass → Task(author, stage=D)
5. 用户审 content → Task(critic, stage=D)
6. critic pass → Task(iloveppt)
7. iloveppt 完成 → Task(audience)
8. audience overall ≥ 9 → 交付

全程注意:**主线程不要偷跑**,每一步都按派发表来。如果发现派发卡顿或 yaml parse 错误,记下来。

- [ ] **Step 4:复制产物到 post-hybrid 目录**

Run:
```bash
cp -r decks/01-exec-decision-post-hybrid/ evals/agents/baseline/01-exec-decision-post-hybrid/products/
cp .claude/runtime.log evals/agents/baseline/01-exec-decision-post-hybrid/runtime.log.after
```

Expected:产物落盘,runtime.log 留底。

---

## Task 4.2:对比 baseline

**Files:**
- Check: `evals/agents/baseline/01-exec-decision-pre-hybrid/` vs `evals/agents/baseline/01-exec-decision-post-hybrid/`

- [ ] **Step 1:对比 brief.md(必须 100% 一致)**

Run:
```bash
diff evals/agents/baseline/01-exec-decision-pre-hybrid/products/brainstorm/brief.md \
     evals/agents/baseline/01-exec-decision-post-hybrid/products/brainstorm/brief.md
```

Expected:**无 diff 输出**(brainstorm prompt 没改,行为应一致)。

**若有 diff**:brainstorm prompt 被意外修改 / 用户回答路径不同(后者可接受,前者必须查)。

- [ ] **Step 2:对比 outline / content(允许微差)**

Run:
```bash
diff evals/agents/baseline/01-exec-decision-pre-hybrid/products/author/outline_r1.md \
     evals/agents/baseline/01-exec-decision-post-hybrid/products/author/outline_r1.md | head -30
```

Expected:可能有 diff(LLM 输出有随机性),但**章节数 / 标题语义应一致**。如果章节数变了 / 主题漂移 → fail。

- [ ] **Step 3:对比 critic verdict(必须一致)**

Run:
```bash
grep -E "^verdict|^next_action" \
  evals/agents/baseline/01-exec-decision-pre-hybrid/products/critic/*.md \
  evals/agents/baseline/01-exec-decision-post-hybrid/products/critic/*.md
```

Expected:同 fixture 的 verdict 应一致(都 pass 或都 pass_with_notes)。

- [ ] **Step 4:对比 audience overall_score(±1 容差)**

Run:
```bash
grep -E "^overall_score" \
  evals/agents/baseline/01-exec-decision-pre-hybrid/products/audience/*.md \
  evals/agents/baseline/01-exec-decision-post-hybrid/products/audience/*.md
```

Expected:两次评分差 ≤ 1 分。

- [ ] **Step 5:对比 .pptx 视觉(< 5% 像素差)**

Run(把 render PNG 做 hash 对比):
```bash
for page in evals/agents/baseline/01-exec-decision-pre-hybrid/products/builder/render/*.jpg; do
  basename=$(basename $page)
  pre=$(md5 -q $page)
  post=$(md5 -q "evals/agents/baseline/01-exec-decision-post-hybrid/products/builder/render/$basename")
  echo "$basename: pre=$pre post=$post $([ "$pre" = "$post" ] && echo MATCH || echo DIFF)"
done
```

Expected:大部分 MATCH;DIFF 项手动看 PNG(允许文字微差,但 layout / 颜色 / 字体应一致)。

**容差**:同 fixture 的视觉差异 < 5% 像素 = 通过(LLM 输出文字微差导致渲染像素差,正常)。> 5% → 查是哪个 layout 出问题。

- [ ] **Step 6:对比 runtime.log telemetry**

Run:
```bash
wc -l evals/agents/baseline/01-exec-decision-pre-hybrid/runtime.log.pre
wc -l evals/agents/baseline/01-exec-decision-post-hybrid/runtime.log.after
```

Expected:post 行数应明显增加(每个 Task 调用一行),且应看到不同 `agent=` 值(不再全 main)。

- [ ] **Step 7:写 META.md 记录对比结果**

Create `evals/agents/baseline/01-exec-decision-post-hybrid/META.md`:
```markdown
# Post-hybrid baseline · 01-exec-decision

- Date: <填实际日期>
- Mode: hybrid (brainstorm team + 5 subagent)
- Wall-clock: <分钟> (pre 是 <分钟>,diff: <±X 分钟>)
- Total rounds:
  - brainstorm: <N> (pre <N>)
  - critic Stage C: <N> (pre <N>)
  - critic Stage D: <N> (pre <N>)
  - audience: <N> (pre <N>)
- Final audience overall_score: <N> (pre <N>)
- Final critic Stage D verdict: <pass/pass_with_notes> (pre <pass/pass_with_notes>)
- brief.md diff: <empty/non-empty>
- outline/content semantic match: <yes/no>
- pptx visual hash match rate: <X/N pages>
- runtime.log usable: <YES/NO>(post 行数 / 是否含 token / 是否含 duration)
- 总评:PASS / FAIL
```

---

## Task 4.3:Phase 4 通过路径

- [ ] **Step 1:确认对比通过(全部容差内)**

确认 Task 4.2 所有步骤通过(brief 100% / outline-content 语义一致 / critic verdict 一致 / audience ±1 / 视觉 <5% / runtime.log 有改善)。

- [ ] **Step 2:删除 legacy bak**

Run:
```bash
git rm .claude/pipeline-protocol.team-legacy.md.bak
git commit -m "chore(protocol): remove legacy team-mode protocol backup"
```

- [ ] **Step 3:Commit post-hybrid baseline 产物**

Run:
```bash
git add evals/agents/baseline/01-exec-decision-post-hybrid/
git commit -m "test(evals): add post-hybrid baseline for 01-exec-decision"
```

- [ ] **Step 4:Git tag post-hybrid-migration**

Run:
```bash
git tag -a post-hybrid-migration -m "Hybrid migration validated by 01-exec-decision baseline diff"
git tag --list | grep hybrid
```

Expected:看到两个 tag(pre / post)。

---

## Task 4.4(条件):Phase 4 失败处理

**仅当 Task 4.2 任意步骤 fail 时执行。**

- [ ] **Step 1:定位失败维度**

按 fail 维度归因:
- brief 不一致 → 检查 brainstorm prompt 是否被意外动 → `git diff pre-hybrid-migration .claude/agents/iloveppt-brainstorm.md`(预期 empty)
- outline / content 漂移 → 检查 critic / author 改造时是否引入了 prompt 语义变化
- critic verdict 不一致 → 检查 critic prompt 改造,可能误删 checklist 项
- audience > 1 分差 → 检查 audience prompt 改造,可能误删评分维度
- 视觉 > 5% → 检查 iloveppt prompt 改造,可能 Step 4 视觉增强行为变了

- [ ] **Step 2:决策:fix forward 还是 revert**

Fix forward(推荐):定位是哪个 commit 引入问题,git revert 该 commit 或重新跑该 task。

Full revert(最后手段):
```bash
git reset --hard pre-hybrid-migration
```
然后从 Phase 1 重新走,把 fail 维度的 fix 提前规划进去。

- [ ] **Step 3:重跑 Task 4.1 + Task 4.2 直到通过**

---

# Phase 5:文档更新

**目标**:同步面向用户 / 开发者的文档。

---

## Task 5.1:更新 docs/agent-internals.zh.md

**Files:**
- Modify: `docs/agent-internals.zh.md`

- [ ] **Step 1:读现状定位需要改的段**

Run:
```bash
grep -n "TeamCreate\|SendMessage\|agent team\|窗口" docs/agent-internals.zh.md
```

Expected:列出当前讲 team 模式的段。

- [ ] **Step 2:加二段论说明 + 修订调用方式**

在合适的位置(通常是"架构"或"流水线"节)加一段:
```markdown
## Hybrid 架构(2026-05-25 起)

iLovePPT 用 Hybrid 架构:

- **Phase A (brainstorm team)**:用户表达"做 PPT"意图,主线程 `TeamCreate(brainstorm)` 跑多轮对话收 brief。brainstorm 是有性格的对话方,持续窗口跨 ask_user 用 state.json 恢复。
- **Phase B (subagent 流水线)**:brief 批准后,主线程关闭 team,Task 调 author/critic/iloveppt/audience(可选 extractor 旁路)。每次 Task return 一段文本,最后是 yaml block,主线程 parse 决定下一步。

为什么这么分:brainstorm 的"多轮对话"语义在 team 模式下延迟最低、token 最省;其他 agent 都是"单次跑完即关"的 subagent 行为,team 协议的窗口管理 / idle 通知反而是纯负担。Hybrid 用 20% 的额外协议复杂度换 brainstorm 100% 的对话体验。

完整协议见 [`.claude/pipeline-protocol.md`](.claude/pipeline-protocol.md)。
```

(把现有 team 模式描述里的 "TeamCreate 调所有 agent" 类描述更新或删掉。)

- [ ] **Step 3:Commit**

Run:
```bash
git add docs/agent-internals.zh.md
git commit -m "docs(agent-internals): sync hybrid architecture"
```

---

## Task 5.2:更新 docs/MANUAL.zh.md

**Files:**
- Modify: `docs/MANUAL.zh.md`

- [ ] **Step 1:读现状**

Run:
```bash
grep -n "TeamCreate\|SendMessage\|agent team\|窗口" docs/MANUAL.zh.md
```

- [ ] **Step 2:更新"系统怎么跑"段说明二段论**

在合适位置(通常是"使用流程"节)加一段简洁说明:
```markdown
## 系统怎么跑(Hybrid)

跟主线程说"做 PPT" 后:

1. **brainstorm 跟你聊**(team 模式):主线程开一个 brainstorm 持续窗口,brainstorm 多轮问你字段(受众 / 时长 / 风格 / 素材 / 模板),写 brief.md 让你审。
2. **流水线接力**(subagent 模式):brief 批准后,主线程关闭 brainstorm,依次 Task 调 author(出 outline → 你审 → 拓 content → 你审)、critic(评 content)、iloveppt(build .pptx)、audience(评分,< 9 自动回派修复)。
3. **交付**:audience ≥ 9 分时,主线程把 .pptx 路径给你。
```

(删/改现有"全程 agent team"类描述。)

- [ ] **Step 3:Commit**

Run:
```bash
git add docs/MANUAL.zh.md
git commit -m "docs(manual): sync hybrid architecture user-facing description"
```

---

## Task 5.3:更新 README.md 措辞

**Files:**
- Modify: `README.md`

- [ ] **Step 1:读现状**

Run:
```bash
grep -n "agent team\|TeamCreate\|6 agent" README.md
```

- [ ] **Step 2:更新仓库定位措辞**

定位类似 "agent team 帮你写 PPT 的开源工具" 这种 tagline,改为:

```markdown
iLovePPT 是一个 **brainstorm 跟你聊 + 流水线 subagent 接力帮你写 PPT 的开源工具**。
```

或保守版:
```markdown
iLovePPT 是一个 **AI agent 帮你写 PPT 的开源工具**(brainstorm 对话 + 5 个 subagent 接力)。
```

- [ ] **Step 3:同步 README 里其他 team 模式描述**

把"6 agent"统一为"1 brainstorm(team) + 5 subagent + 1 旁路 subagent"。

- [ ] **Step 4:Commit**

Run:
```bash
git add README.md
git commit -m "docs(readme): update tagline for hybrid architecture"
```

---

## Task 5.4:写 postmortem

**Files:**
- Create: `docs/archive/2026-05-25-hybrid-migration-postmortem.md`

- [ ] **Step 1:创建 postmortem 文件**

Create `docs/archive/2026-05-25-hybrid-migration-postmortem.md`:

```markdown
# Hybrid Migration Postmortem

| 项 | 值 |
|---|---|
| Date | <填实际日期> |
| Spec | `docs/archive/2026-05-25-hybrid-team-subagent-migration-design.md` |
| Plan | `docs/archive/2026-05-25-hybrid-migration-plan.md` |
| Audit | `docs/agent-team-evaluation-checklist.zh.md` |
| pre tag | `pre-hybrid-migration` |
| post tag | `post-hybrid-migration` |

## 1. 迁移成果

### 1.1 协议层
- pipeline-protocol.md 从 700+ 行瘦身到 <填实际行数> 行
- 删 idle / SendMessage / 窗口生命周期 ~40% 内容
- 新增 §4 yaml schema 统一 Phase A SendMessage / Phase B Task return

### 1.2 Agent 改造
- brainstorm:**0 行修改**(Hybrid 关键)
- 其余 5 agent:删 team-specific 段 + 加 Output format 段 + yaml 示例
- 总 diff lines: <填>

### 1.3 Telemetry
- runtime.log 从 5 行全 main → <填新行数> 行,含 <填具体新字段:agent / token / duration ...>
- 修复 Audit GAP: <填如 G1 / D2 / H5 / I.3 等>

### 1.4 Baseline 对比(Phase 4 fixture 01-exec-decision)

| 维度 | Pre | Post | Diff |
|---|---|---|---|
| brief.md | <hash> | <hash> | <empty/non-empty> |
| outline.md 章节数 | <N> | <N> | <±X> |
| content 字数 | <N> | <N> | <±X%> |
| critic Stage C verdict | <V> | <V> | <same/diff> |
| critic Stage D verdict | <V> | <V> | <same/diff> |
| audience overall_score | <N> | <N> | <±X> |
| pptx 视觉 hash 一致率 | n/a | <X/N> | — |
| Wall-clock | <分> | <分> | <±X 分> |
| 总 token | n/a | <N> | — |

## 2. 没解决的问题(留给后续 spec)

(从 spec §9 YAGNI list 抄过来,标注哪些已变得更紧迫)

- 章节并行拓写(Audit B4 Layer 2)— 优先级:中
- iloveppt Step 4 / author 出图多 Bash 并行(Audit B4 Layer 1)— **建议下个 sprint 做**
- MAST 14 项 checklist 化(Audit E4 / I.5)
- pass^k 回归套件(Audit B1 / I.2)— **现在可做**,新 baseline 提供基础
- author / iloveppt 多职责拆分(Audit H3)

## 3. 意外发现 / 设计 trade-off

(填实际迁移中遇到的问题。例如:)
- <hook 是否真的拿到了 token / duration?如否,为什么?>
- <Phase A → Phase B 切换有无 race?>
- <模板 extractor 中途介入路径有无实际跑过?>
- <yaml schema 在 5 个 agent 实际产出中有无字段缺失?>

## 4. 下一步

按 Audit J 节优先级:
1. 跑 5 个 agents fixture 填 `evals/agents/baseline/*.json` baseline 数字
2. pass^k 套件(3 brief × 5 次)
3. MAST 5 项纳入 critic prompt
4. 评估章节并行
```

- [ ] **Step 2:Commit**

Run:
```bash
git add docs/archive/2026-05-25-hybrid-migration-postmortem.md
git commit -m "docs(archive): hybrid migration postmortem with baseline diff"
```

---

# 完成验收

- [ ] **Step 1:全部 Phase 通过检查**

Run:
```bash
git log --oneline pre-hybrid-migration..HEAD
git tag --list | grep hybrid
wc -l .claude/pipeline-protocol.md
ls evals/agents/baseline/
ls -la .claude/pipeline-protocol*.bak 2>&1 | head -5  # 应该 No such file
```

Expected:
- 看到 ~15 个 commits(每个 task 一个)
- 看到 `pre-hybrid-migration` 和 `post-hybrid-migration` 两个 tag
- pipeline-protocol.md 在 250-350 行
- baseline 目录有 pre + post 两份
- 没有 `.bak` 文件残留

- [ ] **Step 2:运行测试套件确认无回归**

Run:
```bash
python3 -m pytest tests/ -q
```

Expected:全 72 passed(协议 / agent prompt 改动不影响 build.py 测试)。

- [ ] **Step 3:Optional — 跑 02-tech-architecture extended baseline**

跑第二个 fixture 做额外验证(spec §7.3 提到的 optional)。

完成后报告:`Phase 5 完成 — hybrid migration validated. Audit GAP 修复:<列哪些>`。

---

# 风险与回退一览

| 风险 | 应对 |
|---|---|
| Phase 1 协议写错(漏段 / 矛盾) | git revert HEAD;参考 pipeline-protocol.team-legacy.md.bak 重写 |
| Phase 2 某个 agent prompt 改坏 | git revert 该 task commit;只重做该 agent |
| Phase 3 hook 注入失败(runtime.log 仍空) | 不阻塞 Phase 4;在 postmortem 记 limitation,后续优化 |
| Phase 4 baseline 对比 fail | 按 Task 4.4 流程定位 + fix forward;最坏 `git reset --hard pre-hybrid-migration` |
| Phase 5 文档同步遗漏 | 不阻塞产品功能,后续 PR 补 |
