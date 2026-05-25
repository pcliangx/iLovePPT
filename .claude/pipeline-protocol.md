# iLovePPT Pipeline Protocol

> **Location**: `${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md`(AI 运行时协议,跟 `${CLAUDE_PROJECT_DIR}/.claude/agents/*.md` 同性质)
> **Scope**: 主线程派发逻辑 + agent 之间的 handoff + 各 gate 规则
> **Audience**: Claude 主线程(派发时反复 reference) + 各 agent 文件(行为契约)
> **流水线形态**: 5 agent + 1 旁路 · brainstorm → author → critic(C/D)→ iloveppt(build+visual)→ audience(+ extractor 旁路)

本文档是 iLovePPT 流水线**当前运行时协议**的权威定义。当主线程 / agent 文件有歧义时,以本文档为准。

**跟 `${CLAUDE_PROJECT_DIR}/docs/archive/` 的区别**:那里是设计 rationale 史档(给人看,为什么这么做);这里是活协议(给 AI 看,**现在**怎么做)。流水线行为变化时本文档原地更新,设计 rationale 归档到 specs/。

`CLAUDE.md` 是导航文件,核心架构原则在那里;本文档是细则。

---

## 概览

```
brainstorm → author(C) → critic(C) → author(D) → critic(D) → iloveppt → audience
   ↑                       ↑                       ↑                       ↓
   └─ extractor 旁路 ─────┘ 5 轮 cap               5 轮 cap   build+视觉   9 分 cap
                          (4 选 1)               (4 选 1)    (一气呵成)  (5 轮后 4 选 1)
```

5 个 agent + 1 旁路:

| agent | 角色 | 何时派 |
|---|---|---|
| `iloveppt-brainstorm` | Stage A-B 收 brief + 素材 | 用户首次说"做 PPT" |
| `iloveppt-author` | Stage C-D 出 outline + content | brainstorm 收齐后 |
| `iloveppt-critic` | 评审员:14 项 checklist + 4 维度判断性 + 三档 verdict | Stage C 用户批准 outline 后跑一次;Stage D 用户批准 content 后跑一次 |
| `iloveppt` | Stage E:**机械构建 .pptx + 机械视觉 QA(Step 0-3) + 主动加视觉(Step 4)**(iconify / Unsplash / brand) | critic Stage D pass / pass_with_notes 后 |
| `iloveppt-audience` | 模拟受众读 deck 给评分 | iloveppt 完成后直接派(无 designer 中间层);评分 < 9 反馈给 author 或派 iloveppt mode=visual_redo |
| `iloveppt-template-extractor` | 旁路 · 提取 .pptx 模板 4 级 token | 用户给新 .pptx 模板时 |

agent 设计的源 rationale:`${CLAUDE_PROJECT_DIR}/docs/archive/2026-05-23-iloveppt-agent-design.md`。

---

## 0. 团队模式通信(权威规则,所有 agent 必读)

iLovePPT 流水线在 **`TeamCreate` + `Agent(team_name=...)` 常驻 teammate** 模式下运行,**不是** `Agent(prompt=...)` 单次调用模式。这点决定了 agent 之间所有通信的形式。

**1. 你的 transcript 对 team-lead 不可见** —— 你写到自己 transcript 的最终文字、YAML、报告内容,team-lead(主线程)**完全看不到**。必须用 `SendMessage(to="team-lead", message=<内容>)` 工具调用才能传出去。

**2. 所有 "return / 返回 yaml payload" 都是 SendMessage 调用的语义** —— agent 文档里所有形如:

```yaml
next_action: ask_user
message_to_user: |
  ...
questions: [...]
```

或

```yaml
next_action: dispatch_author
dispatch:
  agent: iloveppt-author
  args: {...}
```

**不是**写到自己的 transcript,而是这样发出去:

```
SendMessage(
  to="team-lead",
  summary="<5-10 字摘要,例:ask audience+duration>",
  message="<上面整段 yaml 的字符串>"
)
```

team-lead 收到后会按协议解析(`ask_user` → 转给用户;`dispatch_*` → 派下个 agent)。

**3. 收到 team-lead 的 SendMessage 入站消息后**:
- 把消息内容当作新的 `user_response` 或入参参数处理
- 跑你的流程(Read state file → 干活 → 写 state → SendMessage 回结果)
- **不允许只跑流程不发回信** —— 即使你只是 ack("已收到,正在处理 X"),也必须 SendMessage,否则 team-lead 卡死

**4. idle 之前必须 SendMessage** —— 你的 turn 结束自动 idle 是正常的,但 **idle 前必须至少调一次 SendMessage** 把这轮成果(问题 / dispatch / 报告路径 / 错误)告诉 team-lead。**idle 前没发消息 = 你这轮等于没干**,team-lead 收到的只是个空 `idle_notification`,会以为你卡死。

**5. 错误也要 SendMessage 出去** —— 工具失败 / 入参不全 / 检测到协议违反 → `SendMessage(to="team-lead", message="error: <reason>\n详情:...")`,让 team-lead 看到并决定下一步。不要静默卡住。

**6. `dispatch_<next_agent>` 不是你直接派下个 agent** —— 你 SendMessage 给 team-lead 说"该派 author 了 + 这是入参",team-lead 真正派下个 teammate。agent 之间不直接互派(嵌套派 agent 是反模式)。

**这条规则覆盖所有 agent 文件里 "return / 主线程会..." 的写法** —— 把那些都翻译成 SendMessage 工具调用。agent 文件里的 yaml payload 是**消息内容模板**,不是 transcript 模板。

---

## 0.5. 多轮迭代产物版本化(权威规则,所有 agent 必读)

iLovePPT 的 critic / iloveppt(visual_report) / audience 三个产物 多轮迭代产物**全保留**,文件名带 `_r{N}` 后缀(round)。全保留为了事后追溯收敛轨迹("为什么 r1 fail r2 pass")。

**命名规则**:

| Agent | 文件名格式 |
|---|---|
| critic Stage C | `<working_dir>/critic/critic_report_C_r{N}.md`(N=1,2,...,5) |
| critic Stage D | `<working_dir>/critic/critic_report_D_r{N}.md`(N=1,2,...,5) |
| iloveppt Step 4 visual | `<working_dir>/builder/visual_report_r{N}.md`(N=1,2,...,5) |
| audience | `<working_dir>/audience/audience_review_r{N}.md`(N=1,2,...,5) |

**r1 强制后缀**:第 1 轮也叫 `_r1.md`(不叫 `audience_review.md`),命名规则 100% 一致。

**agent 写入逻辑**(写时找下一轮 +1):

```python
# 伪代码(critic / iloveppt visual_report / audience 都遵守)
existing = glob(f"{working_dir}/<agent>/<prefix>_r*.md")
next_r = max([int(re.search(r'_r(\d+)\.md$', p).group(1)) for p in existing], default=0) + 1
output_path = f"{working_dir}/<agent>/<prefix>_r{next_r}.md"
Write(output_path, report_content)
```

agent 自己算 next_r,主线程不传该字段(避免依赖)。

**主线程派发逻辑**(传具体最新 r{N} 路径):

主线程在 dispatch 含"上一轮 / 当前最新"语义的入参时,**必须找最新轮**:

```python
# 伪代码(主线程内)
import glob, re
files = glob.glob(f"{working_dir}/critic/critic_report_D_r*.md")
files.sort(key=lambda p: int(re.search(r'_r(\d+)\.md$', p).group(1)))
latest = files[-1]    # e.g. critic_report_D_r3.md
# 然后 SendMessage 给 builder,入参 critic_d_report_path=<latest>
```

等价 shell:`ls critic_report_D_r*.md | sort -V | tail -1`。

**入参传具体 path**:

| 接收 agent | 入参字段 | 主线程传值 |
|---|---|---|
| iloveppt | `critic_d_report_path` | `<working_dir>/critic/critic_report_D_r{N}.md`(最新 pass 那轮)|
| iloveppt(mode=visual_redo) | `prev_audience_review_path` | `<working_dir>/audience/audience_review_r{N-1}.md`(上一轮)|
| iloveppt(mode=visual_redo) | `prev_visual_report_path` | `<working_dir>/builder/visual_report_r{N-1}.md` |

**不变化的命名**(已有版本逻辑,不动):

- `author/deck_v{N}_outline.md` / `content.md` —— N 由 author iteration 驱动(内容大改 = 大版本)
- `builder/deck_v{N}.pptx` / `deck_v{N}_render/` —— N 同 author
- `brainstorm/state.json` / `author/state.json` —— 一份,跨派发记忆
- `STATUS.md`(主线程交付摘要,一份)

完整设计 spec:`${CLAUDE_PROJECT_DIR}/docs/superpowers/specs/2026-05-25-version-mgmt-design.md`。

---

## 1. PPT 意图触发规则(强制)

**主线程 Claude 一旦判断用户有制作 PPT 的意图,必须先建 team 再派 agent,不允许在主进程里串行调用 agent**。

1. **建 team**:用 `TeamCreate` 创建一个 agent team,team 名建议 `iloveppt-<deck-slug>`(例:`iloveppt-claude-training`)。
2. **每个 teammate 独立窗口**:5 个 agent + 1 旁路按需各占一格,通过 `SendMessage` 跨窗口传递交付物路径(`brief.md` / `outline.md` / `content.md` / `deck_plan.json` / `.pptx` / report.md)。
3. **主线程退居协调**:只负责派单 + 在窗口间转发消息,不直接执行任何 stage 内的逻辑(不写 brief、不写 content、不做视觉 QA)。

**触发信号**(任一命中即触发):
- 关键词:做 PPT / 帮我写 deck / 提案 / 路演 / 幻灯片 / slides / 汇报材料
- 用户给了 `.pptx` 模板路径或要求"按这个模板出"
- 工作目录里已有 `brief.md` / `outline.md` / `content.md` 且用户要求继续推进

**例外**:用户明确说"不用 team / 你自己来 / 不开窗口"时尊重决定,但仍按下方派发表行事。

**触发后的启动序列**(主线程一气呵成,不要中间等用户):

1. **derive slug** — 从 `initial_request` 取关键短语 slugify(例:"做个 Claude Code 培训" → `claude-code-training`)。这只是命名,brainstorm 后续可提议改。若 `decks/<slug>/` 已存在,追加 `-2` 后缀。
2. **derive working_dir** — `${CLAUDE_PROJECT_DIR}/decks/<slug>/`。主线程负责 `mkdir`。
3. **TeamCreate** — `team_name: "iloveppt-<slug>"`。
4. **SendMessage 给 brainstorm**(首条消息只带三字段,不扩展):

   ```yaml
   working_dir: /abs/path/to/${CLAUDE_PROJECT_DIR}/decks/<slug>/
   iloveppt_root: /abs/path/to/${CLAUDE_PROJECT_DIR}/
   initial_request: |
     <用户原话逐字粘贴,含可能附带的文件路径>
   ```

   不传 `attached_files` / `user_profile_hints` / `previous_decks` 等扩展项 —— brainstorm 自己从 initial_request 解析、自己 Glob 找已有 deck/template。

---

## 2. brainstorm 内部循环协议

**续轮派发载荷** — 主线程 SendMessage 给 brainstorm 续轮时,只传最小集:

```yaml
working_dir: /abs/path
user_response: "<用户对上轮问题的答,逐字>"
```

不传 `iloveppt_root`、不传历史问题 —— brainstorm 自己从 `brainstorm/state.json` 捞。state file 是 SSOT,主线程不复述。

**ask_user 转发协议** — brainstorm 返回 `next_action: ask_user` 时,主线程把 `message_to_user` + `questions` **原文**贴给用户(brainstorm 的口吻直通,不用 `AskUserQuestion` 包装成结构化多选)。原因:brainstorm 是有性格的对话方,主线程只做透明转发。

**软上限兜底** — `brainstorm/state.json` 里维护 `round` 字段(brainstorm 每轮 +1)。主线程在 `round >= 10` 时,转发 brainstorm 问题前**附加一行**给用户:

> "我们已经聊到第 10 轮还没收齐字段。要继续答,还是直接让 author 用当前已知信息开工(缺的字段走默认值)?"

用户选叫停 → 主线程 SendMessage 给 brainstorm `{force_dispatch: true}`,brainstorm 用 state 里已有字段 + 默认值组装 brief,直接 `dispatch_author`。

---

## 3. brainstorm 收齐字段后的总结 + 确认 gate

brainstorm 在返回 `dispatch_author` **之前**必须**串行两步**(不允许并行、不允许跳过):

**Step 1(先)**:`Write` `<working_dir>/brainstorm/brief.md` —— 把结构化 brief + asset_inventory 序列化成人话(schema 见下方)。**等文件落盘成功后**再进 Step 2。

**Step 2(后)**:返回一次 `ask_user` 做最终确认 —— `message_to_user` 含 brief 节选(top_recommendation + 6 必填字段 + 素材数 + brief.md 路径),让用户"在 brief.md 直接编辑 或 回复 OK"。

收到用户 `OK` / `批准 brief` 类回复后,brainstorm 下一次派发才返回 `dispatch_author`。若用户在 brief.md 里直接改了文件,brainstorm 该轮 Read brief.md 重新加载 collected,再问"按改后版本批准?"。

**为什么需要这道 gate**:author 是流水线第一个昂贵动作(出图 + 大段拓写)。若 brief 有理解偏差,这里改的代价最低。增量复述是字段粒度;这道 gate 是组合粒度,catches "字段单独对、组合起来论点不成立"的情况。同时也是"主线程脑补 content"越权动作的预防 —— 有 brief.md,后续任何偏离都能 diff 出来。

**brief.md schema**:

```markdown
---
deck_slug: claude-code-training
created: 2026-05-24
---

# 顶端论点
<top_recommendation 完整句>

# 必填字段
- audience: technical
- duration_min: 15
- theme: tech_blue
- output: <working_dir>/builder/deck_v1.pptx
- presentation_mode: speaker

# 素材清单
- csv: _assets/raw/q4.csv — Q4 营收数据
- image: _assets/refs/arch.png — 现有架构图

# SCQA 线索(brainstorm 推断,author 拓写 cover 时用)
- Situation: ...
- Complication: ...
- Question: ...(隐含)
- Answer: 同顶端论点
```

---

## 4. brainstorm → author handoff

**brainstorm 窗口命运** — 收到 `dispatch_author` 后,主线程**关闭** brainstorm 窗口(不保留 idle)。`brainstorm/state.json` 是 SSOT,需要召回时重开窗口 + Read state 即可。

**主线程不做 brief 完整性校验** — brainstorm 自己 Step 2 已检查必填字段。若 brainstorm 返回不完整 brief,那是 brainstorm bug,在 brainstorm 修而不是主线程兜底。

**handoff 消息原文转发** — 主线程拿到 brainstorm 的 `dispatch.args`(`{working_dir, stage:C, brief, asset_inventory}`)整块 SendMessage 给 author。主线程当邮局,不当海关。

**author 不读 brainstorm 的 state file** — `brainstorm/state.json` 是 brainstorm 的内部记忆,不是 handoff 接口。author 只信入参里的 brief / asset_inventory,避免两个 agent 隐式耦合。

---

## 5. author Stage C → D 内部协议

**Stage 间硬隔离** — author 收到"批准 outline"后,不在同一次派发里继续拓 content。标 `approvals.outline=true` → 返回主线程 → **主线程再派一次** author(stage=D)才开始 Stage D。原因:Stage D 出图 + 拓 content 是分钟级动作,每个昂贵动作独立派发,主线程可见性 + 用户可中途叫停。

**md 文件是 SSOT,state 只记 approval** — author 不维护 md 的 hash/mtime。每次派发都 Read `deck_v{N}_outline.md` / `deck_v{N}_content.md` 当唯一真相源。`author/state.json` 只记 `{stage, outline_md_path, content_md_path, approvals: {outline: bool, content: bool}, iteration: N, pyramid_known_issues: [...]}`。用户在 md 里直接改了 → 下次派发 Read md 自然加载新内容,询问"批准当前版本?"。

**版本号迭代:author 判断 + 询问** — author 收到改动指令时:
- 改动小(改 page X / 改某段措辞)→ 就地 Edit,版本号不动
- 改动大(章节重组 / 论点重写 / 节奏推翻)→ author 主动问"这是大改,要在 v{N} 上 Edit 还是开 v{N+1} 平行版本?"
- 用户明确说"开 v2 / 重做" → 直接 +1,Write 新文件

判断"大改"的启发式:涉及顶端论点变更 / 章节增删 / 超过 3 个 page 的连锁改动。

**Stage C outline.md frontmatter 默认填 footer_meta** — author 出 outline 时默认写入(classification=`INTERNAL` / project=`<deck_slug>` / version=`v1.0`),用户可在审 outline 时改。这避免 brainstorm 多问 3 个低优先级字段;若 author 漏填,builder 透传无值不画 footer(双保险)。

**Pyramid 自检软阻塞 + audit** — 7 项有任一不过时:
- `Write outline.md` 时末尾 checkbox 标 unchecked
- 返回 `ask_user`,message 列明哪几项不过 + 原因,**强制用户二选一**:
  - "豁免第 X 项,理由:..." → 主线程把理由 SendMessage 回 author,author 写入 `state.pyramid_known_issues: [{item: 3, reason: "数据下周才有", approved_at: ...}]`,允许进 Stage D
  - "改第 X 项" → author 收用户指令 Edit outline 重新自检
- **不允许**用户回"先放着" / "不管它"含糊过关 —— 必须显式豁免 + 理由,留 audit 痕迹

---

## 6. author → builder handoff

**author 窗口保留到 builder Step 0 通过才能关** — author 的工作真正完成的标志,不是"用户批准 content",而是 **builder 跑过 Step 0 Pyramid 自检拿到内容层绿灯**。Step 0 若失败,author 窗口立即被召回,直接 Read state file + content.md 续接修改。Step 0 通过后主线程关闭 author 窗口。

**content.md 不被 builder 改 —— builder 写副本** — builder Step 3.4 的 `auto_md_edits` 不允许写回原文 `deck_v{N}_content.md`,而是写副本 `deck_v{N}_content.postbuild.md`:
- 原文 = 用户批准的最后版本(SSOT,不可变)
- 副本 = builder 自动调整后的实际构建版本(`deck_plan.json` 从副本生成)
- builder 返回主线程时附 `auto_md_edits[]` diff,主线程把"builder 自动调整了这些"展示给用户
- 用户决定:接受副本 → 后续 author 改动以副本为基础;拒绝 → 保留原文,author 后续按用户指令重改
- author 被召回时只 Read 原文 `deck_v{N}_content.md`,不读副本(避免污染)

**builder 入参 `footer_meta` 哪来** — author 在 Stage C `outline.md` frontmatter 里默认填(见上节)→ Stage D 拓写时透传到 `content.md` frontmatter → builder 从 content.md frontmatter 读取。author dispatch_builder 时不重复传 footer_meta,builder 自己 Read content.md 拿。

**builder hard stop 回主线程的处理** — builder Step 0 Pyramid fail 或反向 diff fail 返回 `error: ...` 时,主线程**不自动重派 author**,而是把错误展示给用户,**三选一**:
- "按 builder 的 suggestion 自动改" → 主线程 SendMessage 给 author,把 `failed_items + evidence + suggestion` 当 user_response 传入,author 按 suggestion Edit
- "我来指定怎么改" → 主线程接用户的指令,转发给 author
- "终止" → 主线程关 team,保留 working_dir 现状供后续手动处理

不允许"主线程自动按 suggestion 改"—— builder 的 suggestion 是机械建议(例如"合并章节 2 和 3"),用户可能不同意。

---

## 7. critic 双 gate

`iloveppt-critic` 是评审员 / partner critic,**不是合规检查员**。除了跑 14 项 checklist 底线,还要跑**判断性评审**(4 维度:论据强度 / 节奏感 / 措辞质感 / 整体平衡),给三档 verdict。

**位置**:Stage C 和 Stage D 都跑一次

```
author Stage C 出 outline.md → 用户批准
  ↓
主线程派 critic(stage=C)
  ↓ 评 outline 结构 + 适用对齐项 + 4 维度判断性(基于 outline 深度)
  ↓ 写 critic_report_C_r{N}.md → verdict
  ├── pass / pass_with_notes → 主线程派 author(stage=D)拓 content
  └── needs_revision → 用户 cherry-pick → author 改 outline → 重派 critic Stage C
                       第 5 轮还卡 → 主线程四选一(见下)

author Stage D 出 content.md → 用户批准
  ↓
主线程派 critic(stage=D)
  ↓ 评全套(14 项 + 4 维度全套)
  ↓ 写 critic_report_D_r{N}.md → verdict
  ├── pass / pass_with_notes → 主线程派 builder
  └── needs_revision → 用户 cherry-pick → author 改(stage 取决于改动深度,大改 +1 iteration) → 重派 critic Stage D
                       第 5 轮还卡 → 主线程四选一
```

Stage C / Stage D **独立计数**,各自 5 轮 cap。

**入参**:
```yaml
working_dir: /abs/path
stage: C | D                                # 必填
brief_md_path: <working_dir>/brainstorm/brief.md
outline_md_path: <working_dir>/author/deck_v{N}_outline.md
content_md_path: <working_dir>/author/deck_v{N}_content.md   # Stage D 必填,Stage C 可省
asset_inventory: [...]                      # Stage D 必填(主线程从 brainstorm dispatch 透传)
```

**checklist 底线**(每项必须 evidence):

**Section A · 金字塔结构审计(7 项,Stage C/D 都跑)**:
- A1 单一顶端论点 / A2 SCQA 完整 / A3 BLUF / A4 MECE 3-5 / A5 纵向疑问链 / A6 横向逻辑同类 / A7 action title ≤ 24 字

**Section B · brief → content 对齐(Stage C/D 适用项不同)**:
- B1 top_recommendation 字面一致(C/D 都跑)
- B2 SCQA 在 content 有承接(仅 D)/ B3 audience tone(仅 D)/ B4 asset_inventory 交代(仅 D)/ B5 无 brief 外新事实(仅 D)
- B6 duration × 1.5 ≈ 总页数(C/D 都跑,C 基于 outline 估算)
- B7 字数限制(C 仅 action title;D 抽 5 页全字段)

**判断性评审(4 维度,Stage C/D 都跑)**:每个 issue 强制三要素 `severity (high/med/low) + impact + suggestion`

- 维度 1 论据强度:章节论据是否 sharp?有"合 MECE 但弱论据"吗?
- 维度 2 节奏感:章节顺序 / 过渡 / 篇幅分布
- 维度 3 措辞质感:action title 是结论句还是话题?数字 vs 形容词比?
- 维度 4 整体平衡:章节篇幅 / summary 收口 / BLUF

**三档 verdict**:

| verdict | 触发 | 主线程怎么处理 |
|---|---|---|
| `pass` | checklist 全过 + 无 high severity 判断性 | 派下一步(C→author Stage D;D→builder) |
| `pass_with_notes` | checklist 全过 + 仅 low/med severity 判断性 | 展示 notes 给用户,**不阻塞**,用户选"接受 notes 进入下一步"或"先按 notes 改一遍" |
| `needs_revision` | 任一 checklist fail **或** 任一 high severity 判断性 | 展示 report,用户 cherry-pick,派 author 改 |

**3 层 Pyramid 防线**(质量优先,接受冗余):

| 层 | 何时 | 阻塞性 | 角色 |
|---|---|---|---|
| author Stage C 自检 | Stage C 出 outline 时 | 软阻塞(可豁免附理由) | 起草时早 catch |
| **critic(Stage C + Stage D)** | 用户批准 outline 后 / content 后 | 强阻塞(各 5 轮 cap) | 第三方独立评审 + brief 对齐 + 判断性 |
| builder Step 0 | 构建前 | 硬阻塞(hard stop) | 进 mechanical build 前最后保险 |

**用户 cherry-pick(跟 audience 一致)** — critic fail 时主线程不直接派 author。流程:
1. 主线程展示 `critic_report_{C|D}_r{N}.md` 摘要(must-fix + recommended)
2. 用户 cherry-pick:"接受 A6 / 维度 1 page 5 论据弱;A4 我觉得不是问题"
3. 用户筛过的部分作为 `user_response` 自然语言指令派给 author

**5 轮上限(各 stage 独立) + 反复改不收敛时给用户四选一**:

```
同 stage 第 5 轮 critic 仍 needs_revision → 主线程问用户:
  1) 继续改(计数器重置,新 5 轮)
  2) 接受当前版本(标 quality_grade: B,绕过 gate 进下一步)
  3) 终止保留中间态
  4) 回 brainstorm 改 brief(若 Stage C 卡死,大概率 brief 本身有歧义)
```

选 4) 时主线程把 `critic_report_{C|D}_r{N}.md` 路径作为 `[system] critic_blocked\nreport_path: ...\nstage: C|D` 标记 SendMessage 给 brainstorm,brainstorm 重开窗口、Read report 后跟用户对话调 brief。

**critic 窗口每轮新建**(跟 audience 一致) — 无状态,所有 state 在 `critic_report_{C|D}_r{N}.md`。

**builder Step 0 必须 Read critic_report_D_r{N}.md 确认 pass** — builder 启动时第一动作:
- 文件不存在 → 拒绝构建,return `error: critic_d_missing`
- `verdict == needs_revision` → 拒绝构建,return `error: critic_d_not_passed`
- `verdict == pass` 或 `pass_with_notes` → 继续 builder Step 0 自跑 Pyramid(3 层防线的第 3 层)

---

## 8. iloveppt 内部 + 视觉 QA 三方定位

iloveppt 合并了原 builder + 原 designer 职责。三套视觉 QA 严格分离:

| 维度 | iloveppt Step 3(机械)| iloveppt Step 4(主动加视觉)| audience(独立 agent · 认知)|
|---|---|---|---|
| 视角 | 作者视角(自检) | 设计师视角(主动加) | 读者视角(他检) |
| 关注 | **机械缺陷**:字号失衡 / 对齐错位 / 文字溢出 / 颜色违规 / layout 异常 | **缺什么补什么**:icon 缺失 / hero image 缺失 / 装饰过简 / 布局节奏同质 | **认知接收**:论点清晰度 / 节奏感 / 记忆点 / 哪页让我走神 |
| 自动修 | 是(决策 8a 边界内) | 是(iconify / Unsplash / brand 三路降级 · 改 deck_plan.json) | 否(回 author 大改 或 派 iloveppt mode=visual_redo) |
| 输出 | issues + auto_md_edits + review_needed | visual_edits[] + rolled_back[] | rubric 评分 + 走神点列表 + 三类反馈分流 |
| Checklist | visual-qa.md 17 项(机械) | 4 类机会(icon/hero/装饰/节奏) | 4 维评分(comprehension_5s / info_density / visual_appeal / flow_coherence) |

iloveppt Step 3 不评"这页论点不清"(那是 audience 的);Step 3 也不主动加 icon(那是 Step 4 的);audience 不标"字号 14 偏小"(那是 Step 3 的)。

**Pyramid 自检 builder 独立跑,但读 author 豁免状态** — builder Step 0 独立跑 7 项自检(基于当前 md 文件状态,含用户手改后版本),不信任 author 的自检结果(author 可能漏标 / 用户后续手改了 md)。但 builder Read author state(`author/state.json`)拿 `pyramid_known_issues`,若 builder 检出 fail 的项恰好是 author 已豁免的,错误信息加注:

```yaml
error: pyramid_check_failed
failed_items: [4]
evidence:
  item_4: "章节 2 与章节 3 评审范围重叠"
note: "author 已豁免此项(理由:数据下周才有)。builder 仍判定 fail,需用户最终决定:接受 author 豁免 跳过 / 改 md / 终止"
```

这是 **builder 唯一允许 Read author state 的场景**(handoff 隔离的例外)。

**`deck_plan.json` 持久化 + commit-worthy** — builder 生成 `<working_dir>/builder/deck_plan.json` 到工作目录,**不视为 ephemeral**。用户可绕过 author 直接手改 deck_plan.json 跑 `build.py` 重新出 .pptx(适用 mechanical tweak 场景,如调字号 / 微调位置)。这跟"the seam is deck_plan.json"的设计一致。

**`*_render/` 同目录 build 时覆盖** — `<working_dir>/<deck_name>_render/page-*.jpg` 每次 build 覆盖。不做版本化、不做自动清理。audience 后续 Read 这些 PNG,清理早会断流;清理交由用户手动处理。

---

## 9. iloveppt → audience handoff + 反馈环

**串行 + 9 分硬阈值** — iloveppt 完成(含 Step 4 视觉)后**直接派 audience**,无 designer 中间层。audience `overall_score < 9` 一律不交付,自动进入修复环,**直到拿到 ≥ 9 才允许交付**。

**audience 反馈三类分流**:
- `needs_author_rewrite: [page numbers]` → **文字 / 论点 / 结构问题**,派 author 改 content
- `needs_visual_redo: [page numbers]` → **视觉素材 / icon 选错 / 装饰过头**问题,派 iloveppt mode=visual_redo(跳 Step 0-3 只跑 Step 4 视觉)
- `needs_theme_fix: [page numbers]` → **theme 层视觉**(主线程改 themes/tech_blue.py),通常 ` make_*` 函数缺字段

**修复顺序**:author rewrite 先(若内容有问题)→ theme fix(若 theme 层视觉问题)→ visual redo(若仅视觉问题)→ 重派 iloveppt mode=full(若 author/theme 改了)或 mode=visual_redo(仅视觉)→ 重派 audience。

理由:author 改 content 后 iloveppt 要重新 Step 4 加 icon(因为 content 变了);theme 改完所有都要重 build。

**用户 cherry-pick audience 建议** — audience 返回 review.md 后,主线程**不**直接把 top_3_must_fix 转发给 author。流程:
1. 主线程把 `audience_review_r{N}.md` 路径 + `overall_score` + `top_3_must_fix` 摘要展示给用户
2. 用户 cherry-pick:"接受 page 5/13 的建议,page 8 我不改" / "全接受" / "全否决,直接交付当前版本"
3. 主线程把**用户筛过**的部分作为 `user_response` 字符串(自然语言指令)派给 author

不允许"audience 命令 author"的强耦合 —— audience 的反馈是给"作者 + 用户"两方看的建议,**用户是最终决策者**。

**5 轮上限 + 用户决定续命** — `audience → author → builder → audience` 这个循环上限 5 轮(主线程在 team 元数据里维护 `audience_round` 计数器)。第 5 轮 audience 仍 < 9 时,主线程**不自动继续**,问用户:

> "已迭代 5 轮,audience 评分 8.4,top remaining issues: ...。继续改 / 接受当前版本 / 终止保留中间态?"

用户选"继续改" → 计数器重置,新一轮 5 轮开始。

**audience 窗口每轮新建** — audience 评一次出一份 `audience_review_r{N}.md`,无状态(state 全在 review.md 里)。主线程每轮新派 audience 窗口、评完关、下轮新建。不保留 idle、不复用窗口。

---

## 10. template-extractor 旁路衔接

extractor 是嵌套 handoff:`brainstorm → extractor → brainstorm`。

**主线程当邮局,中转两跳** — agent 不允许嵌套派 agent。链路:

```
brainstorm 检测到新模板 → return { next_action: dispatch_template_extractor, dispatch.args: { working_dir, template_path } }
  ↓
主线程派 extractor(SendMessage 给 extractor 窗口,载荷 = dispatch.args 原文)
  ↓
extractor 一次性跑完,return { next_action: dispatch_brainstorm, dispatch.args: { working_dir, user_response: "模板已摄入..." }, template_ready: bool }
  ↓
主线程 SendMessage 回 brainstorm(载荷 = dispatch.args)
```

跟其他 handoff 一致(主线程不当海关,只当邮局)。

**brainstorm 窗口在 extractor 跑期间保留 idle**(handoff 通则的例外) — extractor 耗时 1-3 分钟(probe 渲染 + 8 张 PNG 视觉分析),且 extractor 完后立刻要回 brainstorm 续接,关闭再重开 brainstorm 是无谓开销。所以这是**唯一允许 brainstorm 保留 idle 的场景**。其他 handoff(dispatch_author)brainstorm 仍然关闭。

**extractor 窗口** — 一次性任务,跑完关闭,不保留。

**extractor 失败由 brainstorm 跟用户对话** — extractor 返回 `template_ready: false`(soffice 没装 / probe 失败 / 模板格式异常)时,主线程**不**自动降级、**不**自己问用户。而是 SendMessage 给 brainstorm:

```yaml
working_dir: <working_dir>
user_response: |
  [system] template_extractor_failed
  reason: <extractor 返回的 reason>
  yaml_partial_path: <若已写部分 yaml,给路径>
```

brainstorm 收到这种带 `[system]` 前缀的特殊 user_response,自动转换成跟用户的对话:

> "刚才模板摄入失败了,原因是 X(例:soffice 没装)。三选一:1)装好依赖重试 2)降级用 tech_blue 默认模板 3)终止本次任务"

理由:brainstorm 是跟用户对话的 agent,问最自然;主线程直接问会断层。

---

## 11. 整体退出 + 交付物

**正常退出 = 质量底线 + 用户最终确认(双闸门)**:

```
audience ≥ 9 + Pyramid pass + 无 architectural blocker
  ↓
主线程展示给用户:.pptx + audience_review_r{N}.md 摘要 + 改动 audit
  ↓
用户答 "OK 交付" / "我还想再改 page X"
  ↓ (OK 才结束)
交付完成,主线程关 team
```

第一道闸门(质量)是硬规则,audience < 9 强制进修复环;第二道闸门(用户确认)是软规则,用户始终是 ship 的最终决策者。即使 audience 给 9.5,用户也可以说"再调调",回 author。

**交付物 = 标准集**(主线程展示给用户的清单):

```
<working_dir>/   # = ${CLAUDE_PROJECT_DIR}/decks/<slug>/
├── STATUS.md                                ← 主线程写的交付摘要(见下)
├── brainstorm/
│   ├── state.json                             (brainstorm 轮次/已收字段)
│   └── brief.md                               ← 起始 brief
├── author/
│   ├── state.json                             (author stage/approval/pyramid_known_issues)
│   ├── deck_v{N}_outline.md                  ← 章节骨架
│   ├── deck_v{N}_content.md                  ← 用户批准版(SSOT)
│   └── charts/                                ← 出图 PNG(author 出的)
├── critic/
│   ├── critic_report_C_r{N}.md                    ← Stage C critic 评审(最后一轮)
│   └── critic_report_D_r{N}.md                    ← Stage D critic 评审(最后一轮)
├── builder/
│   ├── deck_v{N}.pptx                        ← 主交付:给客户/听众用
│   ├── deck_v{N}_content.postbuild.md        ← builder 自动调整版(副本)
│   ├── deck_plan.json                        ← mechanical seam,可手改重 build
│   └── deck_v{N}_render/                     ← 视觉 QA 用的逐页 PNG
│   ├── visual_report_r{N}.md                  ← iloveppt Step 4 最后一轮视觉优化报告
│   ├── icons/                                 ← icon PNG(iconify 搜)
│   └── hero/                                  ← hero 图(Unsplash 搜)
├── audience/
│   ├── audience_review_r{N}.md                    ← 最后一轮 audience 报告
│   ├── audience_review_r2.md                  (多轮迭代)
│   └── audience_review_rN.md
├── extractor/                                 ← 旁路(用户给模板时才有)
│   └── template_<name>/                       (extractor L1 提取的媒体)
└── _assets/                                   ← 用户提供,跨 agent 共享
    ├── raw/                                   (用户给的 csv / 原始素材)
    ├── brand/                                 (用户自带 brand assets,iloveppt Step 4 优先用)
    └── refs/                                  (用户直接给的参考图)
```

working_dir 不打包、不删 —— 留在 `${CLAUDE_PROJECT_DIR}/decks/<slug>/` 原地。主线程在最终给用户的消息里**列路径清单 + 一句话用途**,不要把所有文件内容贴出来。

**`STATUS.md` 主线程在每次退出(正常 / 叫停 / 失败)时写**:

```markdown
# Deck status · <slug>
status: delivered | paused | terminated
stopped_at: 2026-05-24T15:30:00
quality_grade: A | B | C
  A = audience ≥ 9, Pyramid pass, 无 known_issues
  B = audience 7-8.9 用户接受,或有豁免的 Pyramid 项
  C = audience < 7 用户强制接受,或 Step 0 fail 用户终止
audience_final_score: 9.2
pyramid_known_issues: []
review_needed_architectural: []

last_artifacts:
  - brainstorm/brief.md ✓
  - author/deck_v1_outline.md ✓ (approved)
  - author/deck_v1_content.md ✓ (approved)
  - builder/deck_v1.pptx ✓

how_to_resume: 跟主线程说"继续 deck <slug>",会从 stage X 续接
```

**非正常退出**(任何阶段叫停 / 失败):
- **不清理 working_dir**(所有半成品留下,STATUS.md 当书签)
- 主线程关 team(包括所有 idle 窗口)
- 主线程给用户最后一条消息含 STATUS.md 路径 + how_to_resume 摘要

**audience 5 轮后用户选"接受当前版本"**:
- 不在文件名加 `_known_issues` 后缀(避免用户拿出去用时尴尬)
- 在 `STATUS.md` 里标 `quality_grade: B` + 列具体 known_issues(audience 最后一轮的 top issues)
- 仍然走"用户最终确认"闸门,确认后才算 delivered

---

## 12. 主线程派发表

主线程在做 PPT 相关工作时,必须按下表派发,不允许自己干 agent 该干的事:

| 任务类型 | 谁干 | 原因 |
|---|---|---|
| 改 helpers.py / themes / build.py / pyproject / 加 tests | **主线程** | 系统改造需要 cross-file 一致性 + 完整 context |
| 用户首次说"做 PPT" / 没有 brief | 派 **iloveppt-brainstorm** | 多轮对话收 brief,主线程不该自己脑补字段 |
| 已有 brief,要出 outline / content | 派 **iloveppt-author** | content 拓写是独立 context 任务;主线程脑补容易跑偏 |
| 用户批准 outline 后 | 派 **iloveppt-critic (stage=C)** | 第三方评审 outline 结构 + 判断性问题;早 catch 代价低 |
| 用户批准 content 后 | 派 **iloveppt-critic (stage=D)** | 第三方全套评审(14 项 + 4 维度判断性)+ build 前最后内容把关 |
| critic Stage D pass / pass_with_notes,首次完整 build | 派 **iloveppt** mode=full | Step 0-3 机械 build + Step 4 主动加视觉(library-first 视觉优化,详见 §13.6 / §13.7) · 一气呵成 |
| **trivial rebuild**(content < 10% 改 / 仅 quick fix · §13.4) | **主线程自跑** `build.py` + 验证改动页 | **不派** iloveppt · 节省一轮 dispatch overhead |
| audience 反馈含 needs_visual_redo · 无 author/theme 改 | 派 **iloveppt** mode=visual_redo | 跳 Step 0-3,只跑 Step 4 + rebuild + final QA |
| audience 反馈仅 needs_author_rewrite | 派 **iloveppt-author** → trivial rebuild(§13.4)→ audience | 跳过 iloveppt Step 4 整轮(content 没大改不需要重加视觉)|
| audience 反馈含特定关键词(§13.3 表)| 主线程**自动**触发对应工具(WebSearch / library / theme 改)**先于** cherry-pick | 不让单一关键词浪费 audience cap |
| iloveppt 完成(含 Step 4 视觉),要评视觉认知 | 派 **iloveppt-audience** | 读者视角是新视角;iloveppt 的自检是作者视角,有盲区 |
| 用户给新 .pptx 模板 | 派 **iloveppt-template-extractor** | 模板提取是独立 4 级 token 流程 |

**反例**:主线程自己重写整份 deck 的 content + 自己跑 visual check。**应该派 author 写 content + 派 audience 评视觉**。

**反例 2**(本次 run 教训):4 轮 audience 把 17 个 issue 全打包 4 选 1 给用户 cherry-pick。**应该按 §13.1 三档 severity 分流(HIGH 自动接 / MED 主线程判 / LOW batch 问)**。

**反例 3**(历史教训):合并前 builder + designer 每轮分两次 dispatch · 4 轮 = 8 dispatch。**合并后 iloveppt 一次性 Step 0-4 跑完,4 轮 = 4 dispatch**,直接节省一半。

**例外**:如果用户明确说"你自己改"/"不用派 agent",尊重决定。

**关于 builder / designer 合并历史**:本协议 v0.5.6 之前 builder + designer 是两个独立 agent,跨 dispatch 接力。**v0.5.6 物理合并为单 iloveppt agent**,Step 4 内嵌"主动加视觉",一次 dispatch 完成机械 build + 视觉打磨。dispatch 效率直接翻倍。

---

## 13. dispatch 效率准则(主线程行为规范)

这一节是基于实际 run 复盘的**主线程行为规范**:agent 文件不动,但主线程在派发时**必须**按这里的规则做诊断和路由,否则会陷入"ticket forwarder 自动驾驶"模式(R1-R4 全是 +0.12-0.22 的低效 polish 循环,直到用户喊才跳出来)。

### 13.1 严重度三档分流(audience / critic 反馈)

**主线程收到 audience review.md 或 critic_report.md 后,先按 severity 自动分流,再决定要不要把所有 issue 一股脑给用户 cherry-pick**:

| severity | 主线程动作 | 不问用户的依据 |
|---|---|---|
| **HIGH**(needs_major / 多视角受影响 / build-blocker) | **默认接受 + 派 agent 改**,只汇报"已安排修" | 高 ROI · 不修肯定差 · 用户也只会说"接受" |
| **MED**(needs_minor / 单视角影响 / cosmetic 但抓眼) | 主线程**自己判断**:看是否在杠杆分析里(§13.2)。在 → 派改;不在 → batch 给用户 cherry-pick | 单 issue 影响小,但批量影响显著,主线程要算 |
| **LOW**(polish / 边际优化 / 单页 < 0.1 分) | **batch 给用户 cherry-pick** 或**主动跳过**注明"留 R5 buffer" | 用户该决策的是杠杆维度不是单个 polish 项 |

**反例**:R1-R4 我把 6+5+3+3 = 17 个 issue 全部打包 4 选 1 给用户。**应该 HIGH 自动接,MED 自己判,LOW batch 问**。

### 13.2 每轮 audience / critic 后必跑"杠杆分析",不只看 top 3

agent 给的 top 3 是"它视角内的优化"。主线程必须**额外**列出 agent 没用的工具维度:

| 工具维度 | 检查问题 |
|---|---|
| `library/visual-patterns/` | iloveppt Step 4 上轮 Read INDEX.md 了吗?有哪些 pattern 命中本 deck 但还没用? |
| WebSearch | audience 说"evidence 弱 / hand-wavey / 预估"了几次?该上 WebSearch 找实测数据了吗? |
| theme code | audience / builder 标了 architectural / theme_fix 项吗?主线程是否该改 themes/<name>.py? |
| layout swap | 当前 layout 是不是 audience 反复扣分的"信息平铺 / 同质 cards"类?换其他 layout 能不能 +0.3? |
| 跨页 hero 注入 | 8.0-8.5 的"good 区间" page 能不能注入 hero 数字 / 大字 anchor 推到 9? |

**输出格式**(给用户 4 选 1 之前主线程**必须先输出**):

```markdown
## 杠杆清单(R{N} audience 后 + 4 选 1 之前)

- audience-推荐 polish(top 3):预估 +0.X · 工作量 5-10 min
- library/visual-patterns 未挖掘:命中 N 个 pattern,预估 +0.Y · 工作量 30-90 min
- WebSearch evidence(audience 第 K 次说 evidence 弱):预估 +0.Z · 工作量 30 min
- theme code 改(若 architectural):预估 +0.W · 工作量 30-60 min
- W1 数据回填(若 pending_data 三页):预估 +0.5+ · 等 1 周

总收益上限 polish-only ≈ X | 跨工具 ≈ Y | + 数据回填 ≈ Z
```

**反例**:R3 audience 已经说"polish 到顶 + 需 W1 数据" 我没做杠杆分析,只给 4 选 1。**结果用户选 A 继续 polish 一轮才反应过来**。

### 13.3 audience 反馈含特定关键词 → 自动触发对应工具

audience review.md 含**任一**下表关键词,**主线程不进 cherry-pick 模板**,先派对应 agent 做工具维度补强:

| 关键词(任一命中) | 自动派 | 自动派的入参 |
|---|---|---|
| "hand-wavey" / "预估" / "evidence 弱" / "数据缺" / "需要数据" | 派 author + 强制要求 WebSearch | "audience 第 K 次说 evidence 弱, 用 WebSearch 找 <topic> 公开数据 / 行业基准 / 第三方 benchmark, 加同序级 anchor 到 source caption" |
| "同质化" / "审美疲劳" / "信息平铺" / "卡片堆" | 派 iloveppt mode=visual_redo + 强制要求 Read INDEX.md | "library/visual-patterns/INDEX.md, RAG search 当前 deck 弱点 page 的 content intent, 推荐 2-3 个 layout swap, 返给主线程评估是否实现 make_ 函数" |
| "字号小" / "label 难辨" / "diagram 模糊" | 派 iloveppt mode=visual_redo + 重画 diagram | "用 matplotlib / drawio 重生成 chart, label 字号 ≥ 14pt (2400×1500 base size)" |
| "BCG / 稳重感 / 卡通 / hero 数字" | 派 iloveppt mode=visual_redo 改 deck_plan.json + 视觉层 | "cover / closing visual,换 hero 数字 anchor 或换 layout,不动 theme 代码" |
| "结构 / MECE / pyramid / 论点不清" | 派 author + 标 R{N+1} 大改 | (这是 author 域,但说明 polish 救不了,要章节级重改) |

**第二次出现同一关键词** = 主线程上一轮 dispatch 没真正 fix,**升级**:派 agent 改之前先**主线程亲自做这个工具维度的工作**(WebSearch 主线程跑 / library 主线程查 / 改 theme 主线程做),然后再派 agent 用主线程发现的素材。

**反例**:audience R1/R2/R3/R4 共说了 4 次"evidence 弱",我直到 R5 才让 author WebSearch。**应该 R1 就触发**。

### 13.4 trivial rebuild 模式 · 跳过完整 builder dispatch

content.md 改动 < 10%(< 5 个字段 / < 3 页)或仅是 quick fix(typo / 字数压缩 / markdown literal cleanup),**主线程不派完整 builder**:

```
主线程直接:
1. 跑 `python3 ${ILOVEPPT_ROOT}/skills/pptx-deck/build.py <working_dir>/builder/deck_plan.json`
2. 跑 `soffice --headless --convert-to pdf ...` + `pdftoppm`
3. Read 改动页对应的 page-N.jpg 视觉验证
4. (可选)Read 1-2 张邻近页防回归
```

**不必跑**:Step 0 critic_report_D 校验(critic 上轮已 pass · 没动 content 结构)、Pyramid 7 项自检(content 微改不会破)、全 36 页 Read。

**触发条件**(主线程判断 trivial):
- 改 ≤ 5 个字段(content.md diff)
- 不新增 / 删除页
- 不改 action title / 章节标题 / 顶端论点
- 不改 layout 类型

**违反任一** → 走完整 builder dispatch(含 Step 0 + 36 页 visual QA)。

### 13.5 跨版本 build · 强制 36 页全 Read,禁止 spot check

`content.md → content.md v2`(版本号 +1 或 layout 类型新增 ≥ 1 类)的 build,**builder 必须 36 页全 Read**,**不允许 spot check**。

**理由**:R4→v2 的实际数据:author 只声称改 9 页,但 audience 实测 p11 也变了(9.0→7.5),这是 layout 改动的隐性连锁影响。**spot check 漏检 = 1 个 -1.5 单页打击,远大于 36 页全 Read 多花的 5 min**。

可选增强:每页 vs `<deck_v{N-1}_render>/page-N.jpg` 做 PNG diff,任何 visually changed 页都标 review_needed 给主线程审。

### 13.6 iloveppt Step 4 visual · library-first 协议

派 iloveppt mode=visual_redo 前,主线程**入参必须包含** `library_lookup_required: true` + 提示用 `${CLAUDE_PROJECT_DIR}/library/visual-patterns/INDEX.md` 或 RAG `search.sh` 查匹配 pattern:

```yaml
working_dir: ...
pptx_path: ...
library_lookup_required: true   # iloveppt Step 4 必须先 Read INDEX.md
library_lookup_focus: ["audience.weakest_pages", "audience.same_layout_repeated"]
# iloveppt Step 4 必须在 visual_report_r{N}.md 列:
#   - patterns_searched: [...]
#   - patterns_matched: [...]
#   - patterns_applied / patterns_rejected_with_reason: [...]
```

**iloveppt Step 4 不查 library = visual_report 视为部分完成**,主线程下轮 dispatch 时**强制要求**先查 library。

**反例**(合并前历史):R1-R4 designer 共 4 次 dispatch,**0 次 Read library/visual-patterns/INDEX.md**。R5 用户喊才挖出来,顶 +0.2 deck 收益。

### 13.7 trivial 改动时主线程自跑 build.py 不派 iloveppt

iloveppt(机械 build + 视觉)是顺序内部 Step 0-4(Step 0 critic gate → Step 1 md→JSON → Step 2 build.py → Step 3 机械 QA → Step 4 主动加视觉)。**主线程在以下场景跳 dispatch 自跑**:

| 场景 | 主线程动作 |
|---|---|
| 完整 build(首次 / 跨版本) | 派 **iloveppt mode=full**(入参带 library_lookup_required) · 跑 Step 0-5 一气呵成 |
| trivial rebuild(§13.4 条件)| 主线程**自跑** build.py,**不派** iloveppt · 直接进 audience(若是 audience 修复循环) |
| audience 反馈仅 needs_visual_redo(无 author / theme 改) | 派 **iloveppt mode=visual_redo** · 跳 Step 0-3,只跑 Step 4 + rebuild + final QA |
| audience 反馈仅 needs_author_rewrite | 派 author 改 content → trivial rebuild(§13.4)→ audience · 跳过 iloveppt Step 4(content 没大改不需要重加视觉)|

**合并前反例**:R1-R4 每轮都派 builder + 派 designer + audience,**4 轮 × 3 agent = 12 dispatch**。合并后 R1 iloveppt mode=full(2 dispatch,iloveppt + audience)+ R2-R4 mode=visual_redo 或 trivial(1-2 dispatch / 轮)= **5-8 dispatch 总数**(节省 ~50%)。

### 13.8 audience 5 轮 cap 用尽前的"polish 封顶诊断"

audience 自己在 R{N} 报告说"polish 收益递减 / 已封顶 / 9.0 需 W1 数据" → 主线程**不进下一轮 polish**,直接做杠杆分析(§13.2):
- 若**杠杆清单有未挖工具(library / WebSearch / theme code)** → 派对应 agent,**不消耗 audience cap**
- 若**杠杆清单全空** → 真的 polish 封顶,把"接受 + W1 后破 9"作为推荐路径给用户,**不再 polish**

**反例**:R3 audience 说封顶,我又 polish 一轮(R4)才真做杠杆分析,**浪费 1 个 audience cap**。

---

## 附录:相关设计文档

- markdown-first 接缝设计(brief.md → outline.md → content.md → deck_plan.json):`${CLAUDE_PROJECT_DIR}/docs/archive/2026-05-23-iloveppt-v3-markdown-first.md`
- agent 拆分整体 rationale:`${CLAUDE_PROJECT_DIR}/docs/archive/2026-05-23-iloveppt-agent-design.md`
- Visual Patterns 知识库 + RAG(hosted multimodal):`${CLAUDE_PROJECT_DIR}/library/visual-patterns/README.md`
