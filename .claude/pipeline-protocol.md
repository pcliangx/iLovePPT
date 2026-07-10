# iLovePPT Pipeline Protocol (Hybrid edition)

> 协议适用于:主线程派发 agent 时的派发规则、handoff 格式、gate 条件、失败处理。
> 不适用于:agent 内部行为(在各 agent 的 prompt 文件)。
>
> **架构**:Phase A team(brainstorm 多轮对话) + Phase B subagent(其余 5 agent + extractor)。

---

## §0. 架构二段论(9→7 步)

```
Phase A:收 brief(team 模式,持续窗口)
─────────────────────────────────────────
用户 "做 PPT"
   ↓
主线程 TeamCreate({agents: ["iloveppt-brainstorm"]})
   ↓ SendMessage(brainstorm, user_intent)
brainstorm team window 持续在线
   ↓ ask_user 多轮(单进程,state.json 跨轮恢复)
brainstorm Write brief.md + 跑 Step 3.6 brief self-audit(原 critic Stage B 已并入)
   ↓ SendMessage(main, next_action: dispatch_author, brief_md_path)
主线程关闭 brainstorm team

Phase B:流水线(subagent 模式,Task 调用 · P2-3 后 7 步)
─────────────────────────────────────────
1. 主线程 Task(author, stage=C, brief_md_path)            → return yaml(outline.md)
2. 用户审批 outline
3. 主线程 Task(author, stage=D, outline_md_path)          → return yaml(content.md)   # 自走 D,无中间 critic
4. 用户审批 content
5. 主线程 Task(critic, stage=cd)                          → return yaml(verdict)       # 合审 outline + content
6. 主线程 Task(iloveppt-builder)                          → return yaml(pptx_path)
7. 主线程 Task(audience)                                  → return yaml(overall_score) # 含 Step 0 spot-check
   loop until overall_score ≥ 9
```

**关键规则**:
- Phase A → Phase B 切换信号:brainstorm SendMessage 返回 `next_action: dispatch_author`(self-audit 通过)
- 切换时主线程**立即关闭 brainstorm team**(YAGNI:audience 三类分流目前无回 brainstorm 路径)
- 模板 extractor 中途介入(用户在 Phase A 期间提供模板路径):主线程 `Task(extractor)` → return yaml → SendMessage 给仍在线的 brainstorm team
- "主线程是 team-lead" 这层语义只在 Phase A 内对 brainstorm team 成立;Phase B 主线程对其他 agent 是 Task 调用方(同步等待 return,无 team-lead/member 关系)

---

## §0c. ~~主线程 spot-check gate~~(已并入 audience Step 0)

:主线程 spot-check 步骤**取消**,完整 spot-check 5 项检查已并入 audience agent 的 Step 0.0:

- placeholder 残留 grep(audience Step 0.0.1)
- 图源完整性(audience Step 0.0.2)
- ≥ 5 张 PNG 视觉破损 detect(audience Step 0.0.3)
- red_line_words grep(audience Step 0.0.4,复用原 Step 0.5)
- source 保真核对(audience Step 0.0.5,条件触发:有 `claims_path` 时跑 `scripts/check_source_fidelity.py`)

**新流程**:

```
builder return next_action: dispatch_audience
   ↓
主线程立即 Task(audience, ...) — 不做单独 spot-check
   ↓
audience Step 0.0 spot-check:任一 fail → 不评分,return needs_visual_redo
                                全 pass → 进 Step 1+ 正常评分
```

完整 spot-check 5 项 + verdict 流程见 [`iloveppt-audience.md` § Step 0.0](${CLAUDE_PROJECT_DIR}/.claude/agents/iloveppt-audience.md)。

---

## §0b. STATUS.md 顶级摘要(跨 session continue 救命)

**每个 deck 工作目录必须维护 `<deck>/STATUS.md`**,主线程在每轮 dispatch 后 update。新 session continue 时**第一件事 Read STATUS.md**,5 秒搞清 deck 当前状态。

### Schema

```markdown
# <deck-slug> STATUS

**当前 phase**: <Stage X · 描述>(如 "Stage F audience round 4 已 pass(9.13 加权 / 8.85 逐页)")

**Active 文件**:
- `author/deck_v{N}_outline.md` · `author/deck_v{N}_content.md`
- `builder/deck_v{N}.pptx` · `builder/deck_v{N}_plan.json`
- `audience/deck_v{N}_audience.r{R}.md`(最新轮)

**历史 round 演进**:
- audience: r1 7.40 → r2 8.20 → r3 8.85 → r4 9.13
- critic cd: r1 needs_revision(2 high) → r2 pass

**Known issues / TODO**:
- 7 张 chart 缺源文件(invariant 在 deck 后 enforce,不 backfill)
- p10 cover subtitle 手动调过(content.md 跟 deck out-of-sync 待回流)

**下一步建议(给下个 session)**:
- ship-as-is 或 修 3 张 minor / 续 sprint XYZ

**被打断的工作**: 无 / 描述
```

### 主线程维护规则

- 每次 subagent return + 派下一个 agent 前,**Edit STATUS.md** 更新 phase / active 文件 / known issues
- 改完 SSOT 文件(content.md / deck_plan.json / 等),同步 update STATUS.md 的 active 文件版本号
- audience round 跑完,update 历史 round 演进表
- ship 决策做完,update phase 到 `delivered`
- 反模式 ✗:STATUS.md 缺失 / 跟实际 active 文件不一致 / 留 "TBD" 不填

### Why

本次 session 跑了 24 + subagent + 4 audience round。如果隔天 continue:不 Read STATUS.md 起码 5 分钟才能搞清"现在哪是 active"。STATUS.md 是 deck 项目的 single source of "where we are"。

---

## §0a. 版本管理:统一命名 + 改前备份

**核心规则**:**过程文档 + 结果 .pptx 每次改动必须新增版本,上版本备份,不允许直接覆盖**(防 outline v1 被覆盖丢失这种事故再发生)。**所有文档遵循统一命名 schema**。

### 统一命名 schema(权威)

**通式**:`deck_v{N}_{kind}[.r{R}].{ext}`

| 字段 | 必填 | 含义 |
|---|---|---|
| `deck_v{N}` | ✓ | major iteration prefix(N=1,2,3...;章节增删 / 顶端论点变 → N+1) |
| `_{kind}` | ✓(.pptx 除外) | 文件类型,见下表 |
| `.r{R}` | minor revision 时必 | round number(state.json round 字段);active report 文件直接带 r{R},SSOT archive 文件 cp 时带 r{R} |
| `.{ext}` | ✓ | md / pptx / json / yaml |

**kind 字典**(权威,不允许新增同义词):

| kind | 产出方 | 例 |
|---|---|---|
| `brief` | brainstorm | `brainstorm/deck_v1_brief.md` |
| `outline` | author Stage C | `author/deck_v1_outline.md` |
| `content` | author Stage D | `author/deck_v1_content.md` |
| `state` | author / brainstorm | `author/deck_v1_state.json` |
| `plan` | builder Step 1 | `builder/deck_v1_plan.json`(替代旧 `deck_plan.json`) |
| (无 kind) | builder Step 2(.pptx) | `builder/deck_v1.pptx`(.pptx 文件 kind 隐含) |
| `render` | builder Step 5(目录) | `builder/deck_v1_render/`(目录,内含 page-NN.jpg) |
| `critic_cd` | critic stage=cd(单次合审) | `critic/deck_v1_critic_cd.r{R}.md` |
| `visual_qa` | builder Step 3 | `builder/deck_v1_visual_qa.r{R}.md` |
| `audience` | audience | `audience/deck_v1_audience.r{R}.md` |
| `claims` | author Stage D(条件产出 · brief 含已确认数据口径时) | `author/deck_v1_claims.yaml` |

**反模式 ✗**(过去本仓库出现过的命名混乱,**禁止再用**):
- `deck_plan.json` → 改为 `deck_v1_plan.json`
- `critic_report_C_r1.md` / `critic_report_D_r2.md` / `deck_v1_critic_C.r1.md` / `deck_v1_critic_D.r2.md` → 改为 `deck_v1_critic_cd.r1.md`(C+D 合并)
- `audience_report.md` / `audience_report_tier1.md` / `audience_report_tier1_r4.md` → 改为 `deck_v1_audience.r{R}.md`(_tier1 / _pilot 等后缀**禁用**;sprint / iteration 信息进 state.json 不进文件名)
- `visual_report_r1.md` / `visual_report_tier1_pilot.md` → 改为 `deck_v1_visual_qa.r{R}.md`
- `deck_v1_r2_backup.pptx` / `deck_v1_r2_pre_r3.pptx` / `deck_v1_副本.pptx` → 一律 `archive/deck_v1.r{R}.pptx`

### 两层版本

**Major iteration**(大改 = 章节增删 / 顶端论点变 / SCQA 变 / 跨页 >3 连锁):
- iteration `N` → `N+1`,**新文件**:`deck_v{N+1}_outline.md` / `deck_v{N+1}_content.md` / `deck_v{N+1}.pptx`
- v{N} 原文件**保留不动**作对照(不放 archive,放主目录平行版本)
- 触发场景:用户明确说"加章节" / "改主题方向" / "重做" 等;author 协议要求 ask_user "v{N} in-place 还是 v{N+1} 平行"

**Minor revision**(小改 = 措辞 / 单页字段 / bug fix / placeholder 调):
- iteration 不动,**改前** cp 当前文件到 `archive/<basename>.r{round_num}.<ext>`
- round_num 取 state.json 里的当前 round(每次 subagent 派发 +1),无 round 则用 timestamp
- 反模式 ✗:直接 `sed -i` / `Write` 覆盖 / `mv` 重命名后改 — 必须先 cp 到 archive

### 受规则约束的文件(全部按统一 schema 命名)

| Active 文件(current) | 改动者 | 备份方式 |
|---|---|---|
| `brainstorm/deck_v{N}_brief.md` | brainstorm | minor: archive |
| `author/deck_v{N}_outline.md` | author Stage C | minor: archive;major: `deck_v{N+1}_outline.md` 新文件平行 |
| `author/deck_v{N}_content.md` | author Stage D | 同上 |
| `author/deck_v{N}_state.json` | author / brainstorm | minor: archive(state 自带 edit_history 仍 cp 留 snapshot) |
| `author/charts/X.{drawio,py,mmd,png,source.yaml}` | author 改图 | minor: archive;源文件 + 渲染 PNG 同步更新 |
| `builder/deck_v{N}_plan.json` | builder Step 1/3/4 + 主线程手动 | 每次改前 archive |
| `builder/deck_v{N}.pptx` | builder build | 每次 build 前 cp current 到 archive(`deck_v{N}.r{R}.pptx`) |
| **不需要 archive(每轮天然独立)** | | |
| `builder/deck_v{N}_visual_qa.r{R}.md` | builder QA | 每轮直接新文件 |
| `critic/deck_v{N}_critic_cd.r{R}.md` | critic stage=cd | 每轮直接新文件 |
| `audience/deck_v{N}_audience.r{R}.md` | audience | 每轮直接新文件 |

### 目录结构(强制,统一命名)

```
<deck-工作目录>/
├── brainstorm/
│   ├── deck_v1_brief.md              # active
│   └── archive/deck_v1_brief.r{R}.md
├── author/
│   ├── deck_v1_outline.md            # active(current)
│   ├── deck_v1_content.md            # active
│   ├── deck_v1_state.json            # active
│   ├── deck_v2_outline.md            # major iteration 平行(不放 archive)
│   ├── deck_v2_content.md
│   ├── charts/X.{py,drawio,mmd,png,source.yaml}
│   └── archive/                      # minor revision 改前 snapshot
│       ├── deck_v1_outline.r1.md
│       ├── deck_v1_outline.r2.md
│       ├── deck_v1_content.r3.md
│       ├── deck_v1_state.r1.json
│       └── ...
├── critic/                           # 每轮 r{R} 文件天然独立,不需 archive
│   ├── deck_v1_critic_cd.r1.md
│   └── deck_v1_critic_cd.r2.md       # rework 后第 2 轮
├── builder/
│   ├── deck_v1.pptx                  # active
│   ├── deck_v1_plan.json             # active(原 deck_plan.json 已弃用)
│   ├── deck_v1_render/               # 渲染图目录(.gitignore'd)
│   ├── deck_v1_visual_qa.r1.md       # builder QA round 1 报告
│   ├── deck_v1_visual_qa.r2.md
│   └── archive/                      # active 改前 snapshot
│       ├── deck_v1.r1.pptx
│       ├── deck_v1.r2.pptx
│       ├── deck_v1_plan.r1.json
│       └── deck_v1_plan.r2.json
└── audience/                         # 每轮 r{R} 文件天然独立,不需 archive
    ├── deck_v1_audience.r1.md
    ├── deck_v1_audience.r2.md
    └── ...
```

### 写前备份(标准做法)

每次改 SSOT 前(author / builder agent 内部 + 主线程手动改):
```bash
# 取 round 号(从 state.json 或自增)
ROUND=$(jq -r '.round' <working_dir>/author/state.json)
# cp 到 archive
mkdir -p <working_dir>/author/archive
cp <working_dir>/author/deck_v1_outline.md \
   <working_dir>/author/archive/deck_v1_outline.r${ROUND}.md
# 然后再改
```

### Escape hatch(可覆盖的例外)

- typo fix(单字 / 标点) + trivial bug fix(< 5 行)→ 可覆盖,但 state.json edit_history 加 `no_backup: true` 标记
- 主线程修 deck_plan.json text_map 的微小字段(不动 layout / 不动 structure)→ 同上
- 反模式 ✗ 不能用 escape hatch:章节增删 / 顶端论点变 / >3 页连锁 / 覆盖 author 上版完整产物

### 跟 author iteration 协议的关系

author "小改 in-place / 大改 v{N+1} 平行" 协议**不变**,新加的是"改前 cp 到 archive"的备份层。author 小改不升 iteration 但每次写文件前必须备份;大改升 iteration 写新文件保留上版。两层叠加 = 任何改动都能 traceback。

---

## §0d. Cost budget 检查

**每次 subagent return 后,主线程必须跑 budget status 检查**(brainstorm Phase A 内 SendMessage idle 不算 return,仅 Phase B Task return 后 + Phase A `dispatch_author` 返回时跑):

```bash
${CLAUDE_PROJECT_DIR}/python3 \
    ${CLAUDE_PROJECT_DIR}/scripts/track_cost.py \
    status --deck <working_dir>
```

**Exit code 语义**:
- `0` → ok,继续派下一棒
- `2` → **OVER BUDGET(cost_usd >= budget_usd)**,主线程**立即暂停**,询问用户三选一:
  ```
  ⚠ 当前 cost ${cost} 已超 budget ${budget}({pct}%)。三选一:
  (1) 继续(不再 warn,本次 deck 不再检查 budget)
  (2) 终止(保留已生成文件,不再派 agent)
  (3) 提 budget 到 ${new}(track_cost.py set-budget --state <state.json> --budget <new>)
  ```

**预算 SSOT**:`<deck>/author/deck_v1_state.json`(优先)/ `<deck>/brainstorm/state.json` / `<deck>/state.json` 之一的 `cost.budget_usd` 字段,brainstorm 收 brief 时填(详 `iloveppt-brainstorm.md § Step 2`)。默认 10 USD。

**Warning 阈值**:50% / 80% / 100% — 每次 `track_cost.py update` 跨过(未 warn 过)时 stderr warn + state.cost.warnings[] append。

**主线程"继续"决策的记账**:用户选 (1) 后,本次 deck 主线程**跳过**后续 `status` 检查(`<deck>/.budget_overridden` 文件 sentinel,主线程检测到 sentinel 不再跑 status)。下次 reset / 新 deck 重新生效。

**完整文档**:[`docs/cost-budget.md`](${CLAUDE_PROJECT_DIR}/docs/cost-budget.md)。

---

## §0. 并行优先(适用于所有派发场景)

**默认并行,不是顺序**。任何时候面对 ≥ 2 个**独立** subagent 工作(无 shared state / 无 sequential 依赖)→ 1 条消息里多 Agent tool call 并行起,**最多 5 实例**同时跑;不要顺序串。

**5 实例上限的原因**:context overhead + 主线程综合负担在 5 之后边际收益负;经验值 3-5 平衡最优。

**并行 vs 顺序的判定**:
- ✓ **可并行**:Explore agent 各扫不同范围 / author 改 content.md 跟 builder 改 deck_plan.json 不冲突 / 多个独立 layout 的 placeholder_map.yaml 各写各的
- ✗ **不可并行**:author Stage D 跟 critic Stage D(critic 等 D 产物)/ builder 重 build 跟 audience 评分(audience 等 .pptx)/ 改同一文件的两个 agent
- ⚠ **半并行**:Stream B 改 content.md + Stream A 改 deck_plan + Stream C 只读分析,A 必须等 B+C 完成再开工 — 仍并行起 B+C,A 在 prompt 内标"等 /path/to/output 存在再开工"

**反模式 ✗**:Task subagent 1 → 等 return → Task subagent 2(纯顺序);用户提示"加大并行度"才并行(应该默认并行)。

**例外**:critic / audience 这类 hard gate 在流水线 critical path 上,**顺序**走是流水线协议要求,不算反模式。

## §1. 主线程派发表(7 步 · 9→7)

**入参 path 字段全部用 §0a 统一命名 schema**(以 deck v1 为例,deck v2 平行版本同 schema 替 v 号)。

| # | 触发条件 | 调谁 | 期望返回 next_action |
|---|---|---|---|
| 1 | "做 PPT" 意图 + brief 未生成 | `TeamCreate({agents: ["iloveppt-brainstorm"]})` → `SendMessage(brainstorm, user_intent)`,产 `brainstorm/deck_v1_brief.md`(含 Step 3.6 self-audit) | `ask_user` 或 `dispatch_author` 或 `dispatch_research` 或 `needs_self_revision` |
| – | 用户答完 brainstorm 问题 | `SendMessage(brainstorm team, user_response)` | 同上 |
| – | brainstorm `needs_self_revision`(self-audit fail) | 主线程展示 must_fix → 用户改 brief.md 或续 dialog → SendMessage 给 brainstorm | 直至 `dispatch_author` |
| 1.5 | brainstorm `dispatch_research`(素材不足 OR 用户显式要研究 · Phase 3 bypass) | 关 brainstorm team → `Task(research, args={working_dir, topic, scqa, audience, user_attachments, depth})` → 产 `research/research_manuscript.md`(网搜+PDF 解析+抓取 · --- 分页 · source 标注) | `dispatch_author_with_research` |
| – | research return | 主线程拿 `research_manuscript` path,并入下一步 author Stage C 入参(透传) | (续 row 2) |
| 2 | brainstorm `dispatch_author` 返回(或 research 完后续) | 关 brainstorm team → `Task(author, args={stage: "C", brief_md_path: ..., research_manuscript: <path|null>})`(透传 brainstorm `author_dispatch_preview` + research 的 manuscript;pattern_hints 已随 RAG 退役,author 从 `layout_variants.yaml` 受控词典自选 layout),产 `author/deck_v1_outline.md` | `ask_user_for_outline_approval` |
| 3 | outline 已批准 | author return `dispatch_self_stage_d` → 主线程立即 `Task(author, args={stage: "D", outline_md_path: ...})` 续走(无中间 critic),产 `author/deck_v1_content.md` | `ask_user_for_content_approval` |
| 4 | content 已批准 | `Task(critic, args={stage: "cd", outline_md_path: ..., content_md_path: ..., report_path: "critic/deck_v1_critic_cd.r{R}.md"})` | `pass` / `pass_with_notes` / `needs_revision` |
| 5 | critic cd `pass` 或 `pass_with_notes` | **按 `brief.track` 路由**(Phase 1):`track=pptx`(默认)→ `Task(builder, args={content_md_path:..., critic_cd_report:..., output_pptx:builder/deck_v1.pptx, ...})`;`track ∈ {html, lark-slides, lark-whiteboard}` → `Task(designer, args={track, content_md_path:..., theme:..., critic_cd_report:..., working_dir:..., mode:full})`(designer 收敛产 `builder/deck_v{N}_render/page-*.jpg`,audience track-agnostic) | `dispatch_audience` 或 `hard_stop` |
| 6 | builder/designer `dispatch_audience` | `Task(audience, args={rendered_dir: "builder/deck_v1_render/", deck_plan_path: ..., builder_visual_edits: [...], audience: <type>, top_recommendation: ..., brief, content_md_path: ..., brief_md_path: ..., claims_path: "author/deck_v1_claims.yaml"(有则传), report_path: "audience/deck_v1_audience.r{R}.md"})`(入参含 spot-check 所需 deck_plan_path + builder_visual_edits + content_md_path + brief_md_path + claims_path) | `delivered` 或 `needs_*` |
| 7 | audience `delivered`(overall_score ≥ 9) | 主线程交付 .pptx 路径给用户 | — |
| – | audience `needs_author_rewrite` | `Task(iloveppt-author, args={stage: "D_rework", audience_report: ...})` | 同 author Stage D |
| – | audience `needs_visual_redo` | `Task(iloveppt-builder, args={mode: "visual_redo", audience_report: ...})` | `dispatch_audience` |
| – | audience `needs_theme_fix` | 主线程跟用户确认改 theme(改 `themes/<name>.yaml` token,主线程自己干,不派 agent)→ **改完必走闭环**:`Task(builder, mode=visual_redo)` 重 build + 重渲染 → 重派 audience | `dispatch_audience` → 回 row 6 |
| – | brainstorm 返回 `dispatch_template_extractor`(Phase A 期间用户给了 .pptx 模板路径) | `Task(iloveppt-template-extractor, args={template_path, name})` → 完整 ingest 入 `library/pptx-templates/items/<name>/` → 用户审 draft → 主线程跑 embed_text/embed_image 入库 → `SendMessage(brainstorm team, extractor_summary)` | happy path:extractor return `user_review_drafts`;失败兜底:return `dispatch_brainstorm` |
| – | critic cd `needs_revision` | `Task(iloveppt-author, args={stage: "D_rework", critic_report: "critic/deck_v1_critic_cd.r{R}.md"})` | 同 author Stage D |

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

用户选叫停 → 主线程 SendMessage 给 brainstorm `{force_dispatch: true}`,brainstorm 用 state 里已有字段 + 默认值组装 brief,**仍跑 Step 3.6 brief self-audit**(默认值组的 brief 更容易踩 B.1-B.5 fail; self-audit 是兜底,不再有外部 critic Stage B)。self-audit 通过后 return `dispatch_author`。

### §2.6 阶段切换信号

brainstorm 返回 `next_action: dispatch_author`(self-audit pass / pass_with_notes 后)→ 主线程**立即关闭 brainstorm team**,转 Phase B 直接派 author Stage C:

```python
# 关闭 team(具体 API 视 Claude Code 实现)
# 然后启动 Phase B:直接派 author Stage C(P2-3.1 后无中间 critic Stage B)
Task(iloveppt-author, args={
    stage: "C",
    brief_md_path: <from yaml>,
    # 透传 brainstorm 的 author_dispatch_preview(pattern_hints 已随 RAG 退役)
    asset_inventory: [...],
})
```

若 brainstorm 返回 `needs_self_revision`(self-audit 5 项有 fail / high severity)→ 主线程展示 must_fix 给用户,用户答"我自己改 brief.md" / "续 dialog 调字段" → SendMessage 给 brainstorm 续聊,直至 brainstorm 返回 `dispatch_author`。

### §2.7 brief.md gate

brainstorm 在返回 `dispatch_author` **之前**必须完成两步 + self-audit(brainstorm prompt 内部逻辑,主线程不感知):
1. 先 `Write brief.md`(文件落盘成功)
2. 跑 Step 3.6 brief self-audit 5 项(原 critic Stage B 已并入;Step 3.5 RAG pattern 预选已退役)
3. self-audit pass / pass_with_notes → 返回 `dispatch_author`;needs_self_revision → 返回 `needs_self_revision` 给用户改

用户回 OK 后,brainstorm 下次 SendMessage 返回 `dispatch_author`。**注意**self-audit 5 项(必填字段 / 内部一致性 / theme tier / red_line / top×audience 张力)由 brainstorm 自己跑,不再有 critic Stage B hard gate(合并)。

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
| critic verdict | `pass` 或 `pass_with_notes`(只跑 stage=cd 一次)|
| audience overall_score | ≥ 9(含 Step 0 spot-check pre-gate) |
| 5 轮 cap | critic stage=cd / audience 各独立计数,达 5 轮强制询问用户四选一(继续改 / 接受当前版本 quality_grade=B / 终止 / 回 brainstorm 改 brief) |
> **Pattern cherry-pick gate / library/search.sh 强制规则已退役**(RAG+tier1 切除):历史 critic/builder/audience 的 `suggested_alternative_pattern` + `<!-- pattern: vp:/tpl: -->` 注释 + search.sh 检索闭环已移除;author 直接从 `layout_variants.yaml` 受控词典选 layout,builder 只认 `<!-- layout: X -->`。

### §3.4 Pyramid 单点收口

Pyramid 质量门**仅** critic 一处:
- critic stage=cd Section A 7 项(合审 outline + content)是唯一判定
- author Stage C 按 Pyramid 5 件套**设计** outline,但不再跑 7 项自检 gate(取消 `pyramid_self_check` / `pyramid_known_issues`)
- iloveppt-builder Step 0 不再重跑 Pyramid;只读 `critic_cd_report.verdict ∈ {pass, pass_with_notes}` 作准入

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

### §3.7 Haiku helper 错误恢复路径

主流水线 6 agent **不直接派** Haiku helpers;主线程在以下**工程错误恢复**场景 dispatch:

#### §3.7.1 yaml-fixer dispatch

**触发**:主线程 parse 任一 agent return text 末尾的 ```yaml ``` block 时,`yaml.safe_load` 抛异常(int 误识 str / colon 误识 dict / quote 不闭合 / trailing comma / bool 大小写歧义等字面问题)。

**流程**:

```
原 agent return text 末尾的 yaml block 解析失败
   ↓
主线程把 yaml 文本写盘到 <working_dir>/_tmp/broken_return.yaml
   ↓
Task(iloveppt-yaml-fixer, args={
    yaml_path: <working_dir>/_tmp/broken_return.yaml,
    failure_report: [{rule: yaml_safe_load_error, message: <exception str>}]
})
   ↓
yaml-fixer return:
  - next_action: rerun_self_check + parse_still_fails=false → 主线程重 parse 修后的 yaml(应能成功),按原 agent 的 next_action 继续派下一棒
  - next_action: hard_stop + parse_still_fails=true → 字面修不动 → 主线程重派原 agent(Task 工具 retry,一次),仍失败 → abort 提示用户
```

**约束**:
- yaml-fixer **只动字面**,不动业务字段值;主流水线 agent 的决策(`next_action` / `verdict` 等)由 yaml-fixer 保留原值
- yaml-fixer 修完后**必须**经主线程重 parse 验证;不允许 yaml-fixer 自己声明"修好了"绕过 parse
- 同一份 yaml 最多派 yaml-fixer **1 次**(防死循环);第二次仍 fail → abort

#### §3.7.2 self-check 批量校验 dispatch

**触发**:extractor 一次入 N 个模板(brainstorm Phase A 时用户连给多份 .pptx) / 主线程要批量校验已 ingest 的 items / pre-commit 风格的 CI 校验。

**流程**:

```
主线程列出 N 个待校验 target(items 目录 / content.md / 其他)
   ↓
并行派 self-check(单次最多 5 实例,按 §0 并行规则):
  Task(iloveppt-self-check, args={check_type, targets: [batch]})
   ↓
self-check return 每条 target 的 pass/fail + failures 列表
   ↓
主线程按 suggestion 分流:
  - needs_yaml_fix → §3.7.1 yaml-fixer
  - needs_extractor_rerun → 重派 extractor
  - hard_stop → 展示用户三选一
```

**约束**:
- self-check **不修文件**,只跑校验 + 解析;修文件是 yaml-fixer 或 extractor 的边界
- self-check 单 Task 内**串行**跑 targets,要并行就主线程派多个 self-check Task(各自 fresh context)
- self-check 不解释"为什么 schema fail",只复述脚本 stdout

#### §3.7.3 主流水线 vs Haiku helper 隔离

- **主流水线 6 agent 链路上**(brainstorm → author → critic → builder → audience + extractor 旁路):**禁止**链路上的 agent 派 Haiku helper(那是主线程的活,subagent 不能起 subagent)
- **主线程派发表 §1** 不变(7 步流水线全是 Opus agent)
- Haiku helpers 只活在**主线程的错误恢复 / 工程批处理**层

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
| brainstorm (team) | `dispatch_author` | **关闭 brainstorm team**,用 brainstorm yaml 里 `author_dispatch_preview` 直接派 author Stage C(无中间 critic Stage B,self-audit 已并入) |
| brainstorm (team) | `needs_self_revision` | 新增 · brief self-audit 5 项有 fail / high severity;主线程展示 must_fix → 用户改 brief 或续 dialog → SendMessage 回 brainstorm |
| brainstorm (team) | `terminate` | 用户在 `[system] template_extractor_failed` 兜底分支选了"终止",关 team,告知用户任务终止 |
| extractor | `user_review_drafts` | 展示 `.draft` 路径给用户审 → 用户改完 → 主线程跑 `embed_text` + `embed_image` 入库 → SendMessage 回 brainstorm team(传 extractor 摘要) |
| extractor | `dispatch_brainstorm` | 失败兜底:SendMessage 给仍在线的 brainstorm team(摘要含 `[system] template_extractor_failed` 前缀);若 team 已关 → 先 TeamCreate 重启 |
| author | `ask_user_for_outline_approval` | 给 outline.md 路径,等用户 OK |
| author | `ask_user_for_content_approval` | 给 content.md 路径,等用户 OK |
| author | `ask_user` | 大改决策点(改动跨 ≥ 3 页 / 顶端论点变 / 章节增删 / 用户说"重做"):转发 message_to_user 问用户"v{N} 上 Edit"或"开 v{N+1} 平行版本" |
| author | `dispatch_self_stage_d` | 新增 · outline 批准后自走 Stage D,无中间 critic;主线程立即 Task(author, stage=D) |
| author | `dispatch_critic` | Task(critic, args={stage: "cd", outline_md_path, content_md_path}) |
| critic | `pass` | 转下一棒(详见 §1 派发表) |
| critic | `pass_with_notes` | 展示 notes 给用户做 cherry-pick,然后转下一棒 |
| critic | `needs_revision` | Task(author) 带 critic 报告路径(D_rework) |
| iloveppt-builder | `dispatch_audience` | Task(audience)— 无中间 spot-check |
| iloveppt-builder | `hard_stop` | 展示 errors 给用户三选一 |
| audience | `delivered` | 交付 .pptx 给用户 |
| audience | `needs_author_rewrite` | Task(author) |
| audience | `needs_visual_redo` | Task(iloveppt-builder, mode=visual_redo)(:audience Step 0 spot-check fail 时也走此路径) |
| audience | `needs_theme_fix` | 主线程跟用户确认改 theme yaml → builder mode=visual_redo 重 build → 重派 audience(闭环) |

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

**brainstorm 的 dispatch_author**(;含 brief self-audit 结果):
```yaml
agent: iloveppt-brainstorm
status: ok
next_action: dispatch_author
artifacts:
  - path: <abs path to brief.md>
    kind: brief_md
brief_md_path: <abs path to brief.md>
brief_audit:                        # P2-3.1 inlined self-audit 结果(原 critic Stage B)
  verdict: pass | pass_with_notes
  section_b1_required_fields: pass
  section_b2_internal_consistency: pass
  section_b3_theme_tier: pass
  section_b4_red_line_words: pass
  section_b5_top_audience_tension: pass
  notes: []                         # pass_with_notes 时填 med/low severity items
author_dispatch_preview:
  agent: iloveppt-author
  args:
    working_dir: <abs path>
    stage: C
    brief: {...}
    asset_inventory: [...]
brief_summary: <一句话 brief 概要>
pattern_hints_for_author: []        # 恒空(RAG 退役;author 从 layout_variants.yaml 自选 layout)
```

**brainstorm 的 needs_self_revision**(;self-audit 5 项有 fail / high severity):
```yaml
agent: iloveppt-brainstorm
status: ok
next_action: needs_self_revision
brief_audit:
  verdict: needs_self_revision
  must_fix:
    - section: B.1.audience
      observed: "brief 第 4 行 audience 字段空白"
      suggestion: "改 brief.md 第 4 行 audience: executive / technical / general / sales 选一"
message_to_user: |
  brief self-audit 发现 N 项 must_fix(列上面),请选...
```

**critic 必加字段**(只支持 stage=cd):
```yaml
agent: iloveppt-critic
status: ok
next_action: pass | pass_with_notes | needs_revision
scores:                              # P0-1 · 机器可读 · validate_agent_return.py 据此重算 verdict
  - {id: A1, severity: 0}            # 20 项全列(A1-A7 + B1-B9 + J1-J4)· severity int 0-3
  # ...(其余 19 项)
stage: cd
verdict: pass | pass_with_notes | needs_revision  # 等同 next_action,冗余便于读
artifacts:
  - path: <abs path to deck_v{N}_critic_cd.r{R}.md>
    kind: critic_report
issues:
  - severity: high | med | low
    section: <文档章节,如 A6 / B9 / 维度 1>
    description: <一句话>
    suggestion: <修改建议>
rounds_used: <int>  # 当前 stage=cd 第几轮
suggested_alternative_layouts:      # advisory(用户 cherry-pick 才采纳;layout 从 17 enum 选)
  - page: 3
    current: cards
    suggest: quadrant
    reason: "4A 不是并列而是因果矩阵(2 类风险 × 2 类应对),quadrant 更准"
```

> `scores` 是 report .md 里 20 项量化 severity 的机器可读镜像;`issues`(high/med/low)是人读摘要。verdict 由 `scores` 按 critic-rubric.yaml 公式算(A1-A7 + B1-B9 + J1-J4;历史 J5 已随 RAG 退役)。

**audience 必加字段**(含 Step 0 spot-check;权威 schema 在 [`iloveppt-audience.md` Step 5](${CLAUDE_PROJECT_DIR}/.claude/agents/iloveppt-audience.md),此处为镜像摘要):
```yaml
agent: iloveppt-audience
status: ok
next_action: delivered | needs_author_rewrite | needs_visual_redo | needs_theme_fix
overall_score: <float 1-10 · 0 = 被 Step 0 spot-check 中止占位>
deck_score_10: <float · 单 persona = deck_score;multi-persona = min 聚合>
verdict: excellent | good | needs_minor | needs_major | blocked_by_spot_check | blocked_by_red_line_words
triage: needs_author_rewrite | needs_visual_redo | needs_theme_fix | none
persona_used: <persona key · multi-persona 时另出 per_persona_scores>
artifacts:
  - path: <abs path to deck_v{N}_audience.r{R}.md>
    kind: audience_report
spot_check:                         # 必填 · Step 0 五项 spot-check 结果
  placeholder_grep: pass | fail | skipped
  chart_sources: pass | fail | skipped
  png_breakage: pass | fail | skipped
  red_line_grep: pass | fail | skipped
  source_fidelity: pass | fail | skipped
  failures: []                      # 任一 fail 时填,verdict 走 blocked_by_*
per_page_scores:                    # 12 项 × 0-3 + evidence(spot-check fail 时空数组)
  - page: <int>
    layout: <layout>
    persona: <persona key>
    scores:
      - {dim: <维度名>, score: <int 0-3>, evidence: "<引文>"}
      # ... 12 项
    page_score_avg: <float>
    page_score_weighted: <float>    # persona 权重加权
    page_score_10: <float>
    verdict: excellent | good | needs_minor | needs_major
needs_visual_redo_pages:            # triage=needs_visual_redo 时填(多类 triage 时也填)
  - page: 8
    issue: "draw.io 流程图 HTML 标签裸露"
    suggestion: "换 17 enum 内 process_flow layout 或重出 PNG"
rounds_used: <int>
```

> 反模式 ✗:旧 4 维 × 10 分(comprehension_5s / info_density / visual_appeal /
> flow_coherence)已被 12 项 × 0-3 取代,旧 schema 出现 = 评审作废(audience.md 明文)。

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

**author 必加字段**(含 dispatch_self_stage_d):
```yaml
agent: iloveppt-author
status: ok
next_action: ask_user_for_outline_approval | ask_user_for_content_approval | dispatch_self_stage_d | dispatch_critic
stage: C | D | D_rework
artifacts:
  - path: <abs path to outline.md or content.md>
    kind: outline_md | content_md
rounds_used: <int>
stage_d_args:                       # P2-3.2 后 · next_action=dispatch_self_stage_d 时填
  stage: D
  brief_md_path: <abs>
  outline_md_path: <abs>
  asset_inventory: [...]
critic_args:                        # next_action=dispatch_critic 时填(stage=cd 唯一)
  stage: cd
  brief_md_path: <abs>
  outline_md_path: <abs>
  content_md_path: <abs>
  asset_inventory: [...]
pattern_hints: []                   # 恒空(RAG 退役);layout 选择进 per_chapter_layout
per_chapter_layout:                 # Stage C 产出 · layout 从 layout_variants.yaml 受控词典选
  - chapter: 1
    layout: process_flow
    rationale: "5 阶段流程,process_flow 匹配"
  - chapter: 2
    layout: cards
    rationale: "4A 4 维并列,cards 匹配"
```


---

## §5. 工作目录与产物

```
decks/<slug>/
├── brainstorm/
│   ├── state.json              # 跨 ask_user 轮恢复(仅 Phase A 用)
│   └── brief.md                # brainstorm 产出,user 审批后冻结
├── author/
│   ├── deck_v{N}_outline.md    # Stage C 产出;N 默认 1,文件存在则 +1
│   └── deck_v{N}_content.md    # Stage D 产出
├── critic/                     # P2-3.2 后只剩 cd 合审报告
│   └── deck_v{N}_critic_cd.r{R}.md  # 每轮编号保留(.r1, .r2, ...)
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
