# iLovePPT Pipeline Protocol (Hybrid edition)

> 协议适用于:主线程派发 agent 时的派发规则、handoff 格式、gate 条件、失败处理。
> 不适用于:agent 内部行为(在各 agent 的 prompt 文件)。
>
> **架构**:Phase A team(brainstorm 多轮对话)+ Phase B subagent(其余 5 agent + extractor)。

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
主线程 Task(iloveppt-builder)                          → return yaml(pptx_path)
主线程 Task(audience)                          → return yaml(overall_score)
   loop until overall_score ≥ 9
```

**关键规则**:
- Phase A → Phase B 切换信号:brainstorm SendMessage 返回 `next_action: dispatch_author`
- 切换时主线程**立即关闭 brainstorm team**(YAGNI:audience 三类分流目前无回 brainstorm 路径)
- 模板 extractor 中途介入(用户在 Phase A 期间提供模板路径):主线程 `Task(extractor)` → return yaml → SendMessage 给仍在线的 brainstorm team
- "主线程是 team-lead" 这层语义只在 Phase A 内对 brainstorm team 成立;Phase B 主线程对其他 agent 是 Task 调用方(同步等待 return,无 team-lead/member 关系)

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
| critic D `pass` 或 `pass_with_notes` | `Task(iloveppt-builder, args={content_md_path: ..., critic_d_report: ...})` | `dispatch_audience` 或 `hard_stop` |
| iloveppt-builder `dispatch_audience` | `Task(iloveppt-audience, args={pptx_path: ..., render_dir: ...})` | `delivered` 或 `needs_*` |
| audience `delivered`(overall_score ≥ 9) | 主线程交付 .pptx 路径给用户 | — |
| audience `needs_author_rewrite` | `Task(iloveppt-author, args={stage: "D_rework", audience_report: ...})` | 同 author Stage D |
| audience `needs_visual_redo` | `Task(iloveppt-builder, args={mode: "visual_redo", audience_report: ...})` | `dispatch_audience` |
| audience `needs_theme_fix` | 主线程跟用户确认改 theme(主线程自己干,不派 agent) | — |
| brainstorm 返回 `dispatch_template_extractor`(Phase A 期间用户给了 .pptx 模板路径) | `Task(iloveppt-template-extractor, args={template_path, name})` → 完整 ingest 入 `library/pptx-templates/items/<name>/` → 用户审 draft → 主线程跑 embed_text/embed_image 入库 → `SendMessage(brainstorm team, extractor_summary)` | happy path:extractor return `user_review_drafts`;失败兜底:return `dispatch_brainstorm`(两者互斥);brainstorm 续聊 |
| critic `needs_revision`(任何 stage) | `Task(iloveppt-author, args={stage: <same>, critic_report: ...})` | 同 author Stage C/D |

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

---

## §3. Phase B 协议(subagent 流水线)

**适用范围**:author / critic / iloveppt-builder / audience / extractor 这 5 个 agent。

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
| 5 轮 cap | critic Stage C / Stage D / audience 各独立计数,达 5 轮强制询问用户四选一(继续改 / 接受当前版本 quality_grade=B / 终止 / 回 brainstorm 改 brief) |
| **Pattern cherry-pick** | critic / iloveppt-builder / audience 任一 yaml 含 `suggested_alternative_pattern(s)` → 主线程**必须**展示给用户决定,不允许自决;用户答"改" → Task author rework + user_response 含 `accept_alternative_pattern: <id>`;用户答"不改" → 继续派下一棒;若 audience 阶段触发改 → author rework 后必须重派 critic D + audience |
| **library/search.sh 强制规则** | 下列 3 处必须走 `library/search.sh`,不允许 agent 凭空造 pattern 引用:① brainstorm Stage A 列模板(`--kb pptx-templates --type template --query <主题>` 排序)② author Stage D 拓写(`--preferred-template <brief.theme> --type page` 模板优先 + vp fallback)③ iloveppt-builder Step 4 加视觉(读 `<!-- pattern: vp:/tpl: -->` 注释 → 查 DB → 渲染)。content.md 的 pattern 注释 id **必须**带 `vp:` 或 `tpl:` 前缀,iloveppt-builder 拒绝无前缀 id |

### §3.4 Pyramid 单点收口

Pyramid 质量门**仅** critic 一处:
- critic Section A 7 项(Stage C 评 outline / Stage D 评 content)是唯一判定
- author Stage C 按 Pyramid 5 件套**设计** outline,但不再跑 7 项自检 gate(取消 `pyramid_self_check` / `pyramid_known_issues`)
- iloveppt-builder Step 0 不再重跑 Pyramid;只读 `critic_d_report.verdict ∈ {pass, pass_with_notes}` 作准入

动机:避免 MAST FM-3.x step repetition(同一 Pyramid 判定在 3 个 agent 重复跑、报告 3 次给用户),且 critic 是 partner 级评审最权威。critic 5 轮 cap 是质量兜底(详 §3.3)。

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

---

## §4. handoff yaml schema(Phase A SendMessage / Phase B Task return 共用)

### §4.1 通用顶层字段

每个 agent return 的最后 yaml block 必须含:

```yaml
agent: <agent-name>          # 谁返回的(brainstorm/author/critic/iloveppt-builder/audience/extractor)
status: ok | error           # 这轮跑没跑成
next_action: <enum>          # 主线程下一步该做什么(见各 agent 枚举)
errors: []                   # status=error 时填,数组每项含 code/message/suggestion
artifacts:                   # 本轮产物(可空)
  - path: <abs path>
    kind: brief_md | outline_md | content_md | critic_report | audience_report | pptx | render_dir | yaml | source_pptx | cover_thumbnail
```

### §4.2 各 agent next_action 枚举

(同 §1 派发表,这里强调 agent 侧返回什么 vs 主线程做什么)

| agent | next_action | 主线程动作 |
|---|---|---|
| brainstorm (team) | `ask_user` | 转发 message_to_user + questions 原文给用户 |
| brainstorm (team) | `dispatch_template_extractor` | Task(iloveppt-template-extractor),return 后 SendMessage 回 brainstorm team |
| brainstorm (team) | `dispatch_author` | **关闭 brainstorm team**,Task(author, stage=C) |
| brainstorm (team) | `terminate` | 用户在 `[system] template_extractor_failed` 兜底分支选了"终止",关 team,告知用户任务终止 |
| extractor | `user_review_drafts` | 展示 `.draft` 路径给用户审 → 用户改完 → 主线程跑 `embed_text` + `embed_image` 入库 → SendMessage 回 brainstorm team(传 extractor 摘要) |
| extractor | `dispatch_brainstorm` | 失败兜底:SendMessage 给仍在线的 brainstorm team(摘要含 `[system] template_extractor_failed` 前缀);若 team 已关 → 先 TeamCreate 重启 |
| author | `ask_user_for_outline_approval` | 给 outline.md 路径,等用户 OK |
| author | `ask_user_for_content_approval` | 给 content.md 路径,等用户 OK |
| author | `ask_user` | 大改决策点(改动跨 ≥ 3 页 / 顶端论点变 / 章节增删 / 用户说"重做"):转发 message_to_user 问用户"v{N} 上 Edit"或"开 v{N+1} 平行版本" |
| author | `dispatch_critic` | Task(critic, args 含 stage=C/D + outline_md_path 或 content_md_path) |
| critic | `pass` | 转下一棒(详见 §1 派发表) |
| critic | `pass_with_notes` | 展示 notes 给用户做 cherry-pick,然后转下一棒 |
| critic | `needs_revision` | Task(author) 带 critic 报告路径 |
| iloveppt-builder | `dispatch_audience` | Task(audience) |
| iloveppt-builder | `hard_stop` | 展示 errors 给用户三选一 |
| audience | `delivered` | 交付 .pptx 给用户 |
| audience | `needs_author_rewrite` | Task(author) |
| audience | `needs_visual_redo` | Task(iloveppt-builder, mode=visual_redo) |
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
pattern_hints_for_author:           # category list,brainstorm RAG 预选,3-5 个
  - process
  - cycle
  - comparison
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
suggested_alternative_patterns:     # advisory(用户 cherry-pick 才采纳)
  - page: 3
    current: cards-flag-4
    suggest: matrix-2x2
    reason: "4A 不是并列而是因果矩阵(2 类风险 × 2 类应对),matrix-2x2 更准"
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
needs_visual_redo_pages:            # triage=needs_visual_redo 时填(多类 triage 时也填)
  - page: 8
    issue: "draw.io 流程图 HTML 标签裸露"
    suggested_alternative_pattern:  # advisory(给 iloveppt-builder mode=visual_redo 用)
      current: pic_text + drawio_chart
      suggest: process-5-step-linear
      reason: "draw.io HTML 标签裸露,直接换内置 pattern preview 一击命中"
rounds_used: <int>
```

**iloveppt-builder 必加字段**:
```yaml
agent: iloveppt-builder
status: ok
next_action: dispatch_audience | hard_stop
artifacts:
  - path: <abs path to deck_v{N}.pptx>
    kind: pptx
  - path: <abs path to render dir>
    kind: render_dir
build_iterations: <int>
deck_plan_edits: [...]              # Step 3 改 deck_plan.json 的清单
review_needed_pages: [...]          # 3 轮仍 fail · category: architectural / needs_author_rewrite
visual_qa:
  passed: <int>
  total: <int>
visual_step4:                       # Step 4 三路 + RAG 第 4 路状态
  capability:
    cairosvg: enabled | disabled
    unsplash: enabled | disabled
    brand_assets: <count> | none
    rag_patterns: <count>_available  # patterns 库当前可用数(库为空时 0_available)
  rag_fallback_used:                # 第 4 路实际使用(三路降级 + 该页 visual_qa 低分时)
    - page: 6
      pattern_id: cards-flag-3
      preview_path: library/visual-patterns/items/cards-flag-3/preview.png
      usage: hero_reference | reference_only
```

**extractor 必加字段**:
```yaml
agent: iloveppt-template-extractor
status: ok | error
next_action: user_review_drafts | dispatch_brainstorm   # happy=user_review_drafts, 失败兜底=dispatch_brainstorm
artifacts:
  - path: <abs path to library/pptx-templates/_source/<name>.pptx>
    kind: source_pptx
  - path: <abs path to library/pptx-templates/items/<name>/preview.png>
    kind: cover_thumbnail
template_ready: false                                   # happy 也是 false(还差用户审 + embed);完成入库后才 true

# === Step 2.5 advisory(declared/rendered 对账)===
declared_pages: 39                                      # unzip -p .pptx ppt/presentation.xml | grep -oc '<p:sldId '
rendered_pages: 32                                      # ls items/<name>/pages/*/preview.png | wc -l
discrepancy: 7                                          # declared - rendered;非 0 时 summary 必提示用户审
discrepancy_resolution: pending                         # pending | confirmed_tool_pages | confirmed_real_loss
                                                        # 严禁 agent 自己解释为 "hidden/master/layout slides"(全是历史幻觉)

# === Step 3 聚合 ===
low_confidence_pages: [3, 7]                            # 页号数组(非整数);confidence < 0.6 的页
failed_pages: []                                        # Read 失败的页号(非空时 status 应为 error 或 partial)

drafts:                                                 # happy path 必填 — 主线程展示 .draft 列表给用户审
  - library/pptx-templates/items/<name>/meta.yaml.draft
  - library/pptx-templates/items/<name>/pages/<NN-slug>/meta.yaml.draft

summary: |
  <name> 渲染 K/N 页(若 discrepancy 非 0 必提示),起草 1 个 template-level + K 个 per-page meta.yaml.draft
  ⚠️ 低置信度页:第 03 / 07 页,请优先审
  失败时 summary 用 [system] template_extractor_failed 前缀,主线程整段转给 brainstorm 走兜底分支
```

**extractor error code 枚举**(`status: error` 时 `errors[].code` 必从下方选):
| code | 含义 | 主线程行为 |
|---|---|---|
| `NAME_INVALID_CHARS` | name 含 `__`(跟 page id 分隔符冲突) | 让用户改名重派 |
| `PPTX_CORRUPTED` | unzip 失败,.pptx 损坏 | 让用户重新提供文件 |
| `RENDER_CLI_NOT_FOUND` | soffice/pdftoppm 不在 PATH | 报环境问题 |
| `RENDER_TOTAL_FAILURE` | LibreOffice 渲染 0 页 | 报环境问题 |
| `PAGE_READ_TIMEOUT` | 某页 Read PNG timeout | 可重派 |
| `SCHEMA_VALIDATION_FAILED` | Step 3.3 self-check 失败(YAML 语法 / 必填字段缺 / enum 违规 / id 重复 / confidence 非数字) | 不放行,详见 errors[].message |

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
pattern_hints:                      # Stage C 必填,Stage D 透传 outline,rework 可改
  - chapter: 1
    selected: [process-5-step-linear]
    rationale: "5 阶段流程,linear pattern 匹配"
  - chapter: 2
    selected: [cards-flag-4]
    rationale: "4A 4 维并列,cards 匹配"
```


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
│   ├── deck_v{N}_outline.md    # Stage C 产出;N 默认 1,文件存在则 +1
│   └── deck_v{N}_content.md    # Stage D 产出
├── critic/
│   ├── critic_report_C_r{N}.md # 每轮编号保留(_r1, _r2, ...)
│   └── critic_report_D_r{N}.md
├── builder/
│   ├── deck_v{N}.pptx
│   ├── deck_plan.json          # iloveppt-builder Step 3 字数 / 视觉修复直接改这里(单一文件,不分 v)
│   ├── visual_report_r{N}.md   # iloveppt-builder Step 0-4 详细报告(每次 build 一份)
│   └── deck_v{N}_render/       # PNG 渲染
└── audience/
    └── audience_review_r{N}.md
```

**关键规则**:
- author 产出用 `deck_v{N}_<kind>.md`(`v{N}` 由 author 决定,平行版本时 +1);其他每轮产物用 `_r{N}.md` 编号保留,不覆盖(便于事后追溯 / git diff)
- `state.json` 仅 brainstorm 用(Phase A 单 agent 跨 ask_user 恢复)
- Phase B agent 不维护跨 turn state(每次 Task 调用都是新 context,所需信息从 artifacts 路径读)

---

## §6. 主线程派发禁区

### §6.1 必须派 agent 的场景

- "做 PPT" 意图首次出现 → 必须 TeamCreate(brainstorm),**不允许**主线程自己写 brief
- brief 完成后任何阶段 → 必须 Task 对应 agent,**不允许**主线程自己写 outline / content / 跑 QA / 加视觉资产

### §6.2 主线程直接干的场景

- 改仓库代码(helpers.py / themes / build.py / tests / agent prompts / 协议文档) → 主线程直接干(跨文件一致性)
- trivial rebuild(< 3 页改动,且仅微调,无新增章节) → 主线程可直接跑 `python3 .claude/skills/pptx-deck/build.py <deck_plan.json>`,不必派 iloveppt-builder
- 用户问问题 / 解释 / 调试 → 主线程直接答(不需要派 agent)

### §6.3 主线程禁忌

- 不允许在该 delegate 的任务上自己动手("快"心态导致越权)
- 不允许跳过 user-in-loop gate(brief / outline / content / 9 分阈值)
- 不允许并行 dispatch 互相依赖的 agent(例:critic 还没 pass 就 Task iloveppt-builder)
- 不允许吃掉 agent 的 error(必须展示给用户三选一)
