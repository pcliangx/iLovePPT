# iLovePPT v3 设计:对话引导 + Markdown-first

> 状态:**采纳 (2026-05-23) · 决策 1 已订正(1a → 1c)**
> 上一版:[v2 agent 设计](2026-05-23-iloveppt-agent-design.md)
> 实施跟踪:本文档下方"实施计划"小节
>
> **2026-05-23 订正记录(同日):**
> 决策 1 原选 1a("Stage A 对话在主线程"),后发现错误归因——
> 我误以为 subagent 单次派发无法多轮对话。**实际上 v2 已经证明 subagent 可以通过"多次派发 + 状态文件"实现多轮**(Phase 1 → 审 → Phase 2 派发就是 2 次派发)。
> 把这套扩到 N 次完全可行。
>
> 1a 的真实代价:主线程上下文膨胀、不可移植、不可发现、用户跟主线程聊别的时被 PPT 上下文污染。
>
> **采纳 1c:三 agent 拆分**。Stage A-E 分到 3 个 agent,主线程退化成 dispatcher。详情见下方决策记录。

## 背景:v2 流程的真实痛点

v2 是 agent 端到端的两阶段流程(Phase 1 出大纲 → 用户审 → Phase 2 build)。跑了一段时间,真实痛点:

| 站 | v2 痛点 |
|---|---|
| 用户输入 | 80% 用户不会写 brief.yaml,扔一句话进来,缺 audience/duration/数据来源等关键字段 |
| Phase 1 大纲生成 | agent 单方面决定章节数/顺序/配图,用户没参与 |
| 用户审 outline | YAML schema(`top_recommendation` / `scqa` / `mece_check_passed`)对非技术用户全是黑话 |
| **文案审缺失** | 用户批 outline 时只看到 120 字框架,实际生成 2000-5000 字文案没有 sign-off,改一个错字要 rebuild 全 deck(3-5 min) |
| **素材摄入缺失** | 没有数据表 / 图 / 参考模板的对话式输入入口 |
| 手改 .pptx 冲突 | 用户在 PowerPoint 里手改 → agent 再跑覆盖手改 |
| iteration 代价 | 改 1 个字 = rebuild 全 deck = 3-5 min |

核心结论:v2 把**协同设计**做成了**单向审批**。

## 8 决策(锁定)

| # | 决策 | 选定 | 原因 |
|---|---|---|---|
| 1 | Stage A-D 谁来做? | **c · 三 agent 拆分**(订正后) | 主线程做会膨胀;v2 已证明 subagent 多次派发 + state file 可实现多轮 |
| 2 | markdown 一次出还是分步? | **b · outline.md → content.md 两步** | 早发现大方向错,避免 5000 字白写 |
| 3 | markdown → JSON 谁做? | **a · agent LLM 推** | 严格 parser 要求用户学元语法,反人类;LLM 推时强约束"不允许引入新论点" |
| 4 | 图表在 md 里如何呈现? | **c · 预渲染 PNG 嵌入** | 用户在 markdown viewer 里就能审视觉 |
| 5 | 素材输入方式? | **c · 文件路径 + 粘贴兼容** | 用户体验最大化 |
| 6 | Pyramid 自检保留? | **a · agent 内部跑** | 用户不再看 SCQA 黑话,但质量门仍在 |
| 7 | 多版本管理? | **a · `deck_v1.md` / `v2.md` 显式** | 简单 + git-friendly |
| 8 | 视觉问题反馈循环? | **a · agent 自动改 md 重 build** | 用户不必为换行/字数超限手动改 md |

### 决策 1 详解:三 agent 拆分

三个 agent 各管一段,**主线程退化为 thin dispatcher**:

| Agent | 阶段 | 角色 |
|---|---|---|
| `iloveppt-brainstorm` | Stage A + B | 多轮对话挖需求 / 引导用户提素材 / 落 `_assets/` |
| `iloveppt-author` | Stage C + D | 按 Pyramid 5 件套出 outline.md / 拓写 content.md / 调 matplotlib 出图 |
| `iloveppt` | Stage E | 接收 content.md → Pyramid 自检 → md→JSON → build → 视觉 QA |

**多轮通过"多次派发 + 状态文件"实现**:

```
Round 1:
  主线程 → 派发 iloveppt-brainstorm(初始 brief)
  agent → 写 .iloveppt_dialog_state.json,问"audience? duration? ..."
  agent → 返回 {next_action: ask_user, questions: [...]}
  
Round 2:
  主线程展示 questions → 用户答
  主线程 → 派发 iloveppt-brainstorm(带用户答)
  agent → Read state.json,补字段,问下一批
  agent → 返回 {next_action: ask_user, questions: [...]}

...

Round N:
  agent 收齐字段 → 返回 {next_action: dispatch_author, brief: {...}, assets: [...]}
  
主线程 → 派发 iloveppt-author(brief + assets)
  ...
```

每个 agent 在被派发时,**第一件事是 Read 自己的 state file**(若存在),知道上次到哪。第二件是 Read 必要文档。整个流程主线程不持有 PPT 相关 context,只做 router。

**状态文件位置**(都在 deck 工作目录):
- `.iloveppt_dialog_state.json` —— brainstorm agent 状态
- `.iloveppt_author_state.json` —— author agent 状态(stage C/D 进度、是否批准等)
- `deck_v{N}_outline.md` / `deck_v{N}_content.md` —— 用户审过的产物
- `_assets/{raw,charts,refs}/*` —— 素材

完成的状态文件可以删(或者保留作为"我们当时怎么定的"记录,git-friendly)。

## v3 流程:5 阶段 / 3 agent

```
[主线程 = pure dispatcher]                  [Agents(独立上下文)]
═══════════════════════════                  ═════════════════════

用户一句话需求
    │
    ▼
派发 iloveppt-brainstorm     ◄──────────►  agent: 读 state.json
                                            (若初次,无 state)
                                            问第 1 批问题
    ◄──────────────────────────────────── 返回 {ask_user, questions}
                                            
展示问题给用户 → 收答 → 再派发                                  
    ↻ 循环到 state=complete                ↻ 每次 Read state.json
                                            补字段,问下一批
                                                              │
                                            Stage A · 需求挖掘
                                            Stage B · 素材摄入
                                                              │
    ◄──────────────────────────────────── 返回 {dispatch_author, brief, assets}
    │
    ▼
派发 iloveppt-author          ◄──────────►  agent: 读 state.json
(Stage C: 出 outline)                       按 Pyramid 设计 outline
                                            写 deck_v1_outline.md
    ◄──────────────────────────────────── 返回 {ask_user_review, outline_path}
                                            
展示 outline.md 给用户 → 收批准 / 改                          
    ↻ 派发 author 改;批准后 → 派发 author Stage D
                                            Stage C / D 切换由 state 标记
                                                              │
    ▼                                       Stage D · 全文拓写
派发 iloveppt-author (Stage D: 出 content)  调 matplotlib 出图
                                            写 deck_v1_content.md
    ◄──────────────────────────────────── 返回 {ask_user_review, content_path}
                                            
展示 content.md 给用户 → 收批准 / 改                          
    ↻ 改循环                                                  
                                                              │
    │                                       Stage E · build
    ▼
派发 iloveppt(builder)        ◄──────────►  Read content.md
                                            Pyramid 自检 → md→JSON
                                            build.py → 视觉 QA × 3
                                            (自动改 content.md 重 build)
    ◄──────────────────────────────────── 返回 {pptx_path, auto_md_edits, review_needed}
    │
    ▼
展示成品 + auto_md_edits 报告给用户
```

主线程**只做 router**:接受 agent 返回的 `next_action`,把 message 转给用户,把用户答 / 批准转给下一次 agent 派发。**不持有任何 PPT 业务逻辑**。

## 接口契约

### 主线程 ↔ agents(统一协议)

所有 agent 派发都遵守以下协议。**派发入参**:

```yaml
# 通用必填
working_dir: /abs/path/to/deck-工作目录       # 所有 state file / 产物的根目录

# 多轮场景:用户对上一轮 next_action 的响应
user_response: "用户答内容 或 '批准' / '改 X' 等"     # 可选,初次派发缺省

# Stage E 特有(派发 iloveppt 时必填)
content_md_path: /abs/path/to/deck_v1_content.md
output_pptx: /abs/path/to/deck_v1.pptx
theme: tech_blue                               # 或 .pptx 模板路径
footer_meta:                                    # 可选,deck 级
  classification: INTERNAL
  project: ...
  version: v1.0
```

**返回**(所有 agent 统一 schema):

```yaml
# 必填:告诉主线程下一步该干嘛
next_action: ask_user | dispatch_brainstorm | dispatch_author | dispatch_builder | done

# next_action 为 ask_user 时:
message_to_user: "<给用户的话>"
questions: [...] | "<开放问题>"                # 让用户答的具体内容

# next_action 为 dispatch_* 时:
dispatch:
  agent: iloveppt-brainstorm | iloveppt-author | iloveppt
  args: { ... }                                # 派发参数

# next_action 为 done 时(只有 iloveppt builder 会出):
pptx_path: /abs/path/to/deck_v1.pptx
auto_md_edits: [...]
review_needed: [...]
pyramid_check: {...}

# 错误返回
error: <error_code>
message: <人类可读>
```

主线程拿到返回后:
- `ask_user` → 把 `message_to_user` + `questions` 转给用户;收答后,把答放进 `user_response`,**重新派发同一个 agent**
- `dispatch_*` → 派发 `dispatch.agent`,带 `dispatch.args`
- `done` → 把 pptx_path / auto_md_edits / review_needed 转给用户,任务结束
- `error` → 把错误转给用户

### Agent 内部 state file 格式

每个 agent 在 `working_dir` 下维护自己的 state file:

**`.iloveppt_dialog_state.json`** (brainstorm 用):
```json
{
  "agent": "iloveppt-brainstorm",
  "round": 3,
  "collected": {
    "audience": "technical",
    "duration_min": 15,
    "top_recommendation": "...",
    "theme": "tech_blue",
    "output": "./deck_v1.pptx"
  },
  "pending": [],
  "asset_inventory": [
    {"type": "csv", "path": "_assets/raw/q4.csv", "desc": "Q4 revenue", "summary": "..."},
    {"type": "image", "path": "_assets/refs/arch.png", "desc": "现有架构图"}
  ],
  "history": [
    {"q": "给谁看?", "a": "技术团队"},
    {"q": "多长?", "a": "15 分钟"},
    {"q": "有数据吗?", "a": "Q4 营收数据在 ./q4.csv"}
  ],
  "status": "complete"
}
```

**`.iloveppt_author_state.json`** (author 用):
```json
{
  "agent": "iloveppt-author",
  "stage": "C" | "D",
  "outline_md_path": "deck_v1_outline.md",
  "content_md_path": null,
  "approvals": {"outline": true, "content": false},
  "iteration": 2,
  "user_revisions_received": [
    "第 3 节标题改成 ...",
    "加一节关于 ... 在第 5 后"
  ]
}
```

builder agent 不需要 state file —— 它是无状态的单次派发(虽然内部有视觉 QA 循环,但 ≤ 3 轮在一次 dispatch 内完成)。

### markdown schema:`deck_v{N}_outline.md`

```markdown
---
title: AI 4A 架构评审办法 v1.0
subtitle: 技术 + 业务 协同评审机制
audience: technical          # executive | technical | general | sales
duration_min: 15
theme: tech_blue
output: ./deck_v1.pptx
top_recommendation: 应当本季度落地 AI 4A 评审办法,5 阶段每阶段 ≤ 3 天
scqa:
  situation: AI 工具铺开,研发提速 30%
  complication: 架构评审仍靠人审,质量飘移
  question: 怎么让评审跟上节奏又不放低质量?
  answer: 应当本季度落地 AI 4A 评审办法,5 阶段每阶段 ≤ 3 天
footer_meta:
  classification: INTERNAL
  project: Project Atlas
  version: v1.0
---

# Outline

## 1. AI 工具铺开,但架构评审仍靠人

- intent: 让管理层认可:这件事必须做
- layout: bullet_list
- data: 研发提速 30% / 评审排期 ≥ 1 周 / 上线返工率 +20%
- diagram: 无

## 2. 覆盖 4A:Application/Architecture/Auth-N/Auth-Z 全闭环

- intent: 划清边界,避免后续扯皮
- layout: cards
- diagram: 无

## 3. 5 阶段串行,每阶段 ≤ 3 天

- intent: 节奏可控
- layout: pic_text
- diagram: drawio flow chart, 5 阶段 + 角色 + 卡点
- data: 总周期 15 天 / 单阶段 ≤ 3 天 / 通过率 90%

# Pyramid 自检
- [x] ① 单一顶端论点
- [x] ② SCQA 完整
- [x] ③ 答案在前(cover.subtitle 已含)
- [x] ④ MECE(3-5 节,两两不重叠)
- [x] ⑤ 纵向疑问/回答链(各节标题串成论据)
- [x] ⑥ ghost deck test
- [x] ⑦ action title ≤ 24 字
```

### markdown schema:`deck_v{N}_content.md`

```markdown
---
# 继承 outline 的所有 frontmatter
title: AI 4A 架构评审办法 v1.0
# ...(同 outline)
based_on: deck_v1_outline.md
---

# Content

## [cover]
- title: AI 4A 架构评审办法 v1.0
- subtitle: 本季度落地,5 阶段每阶段 ≤ 3 天
- prepared_by: 技术部
- date: 2026-05-23
- version: v1.0
- classification: INTERNAL

## [toc]
- 背景与意义
- 评审范围
- 评审流程
- 组织保障
- 落地节奏

## [section_divider]
- num: 1
- title: 背景

## 1. AI 工具铺开,但架构评审仍靠人,质量飘移
<!-- layout: bullet_list -->

- 研发周期被 AI 工具压缩 30%
- 架构评审仍排期 ≥ 1 周
- 上线返工率从 8% 升至 24%

> 数据:Source: 公司 2025 Q4 研发月报

## 2. 覆盖 4A:Application/Architecture/Auth-N/Auth-Z 全闭环
<!-- layout: cards -->

- **Application**: 业务逻辑评审
- **Architecture**: 三层架构 + 数据流
- **Auth-N**: 身份认证 + SSO
- **Auth-Z**: 权限矩阵 + 最小授权

## 3. 5 阶段串行,每阶段 ≤ 3 天,卡点不超 1 周
<!-- layout: pic_text -->

![5 阶段流程图](_assets/charts/review_flow.png)

- **阶段 1**: 提案 / 立项
- **阶段 2**: 架构评审
- **阶段 3**: 安全评审
- **阶段 4**: 上线评审
- **阶段 5**: 回顾复盘

## [summary]
- 5 阶段 ≤ 15 天端到端
- AI 助手降 60% 人力
- Q3 试点 → Q4 全公司

## [closing]
- subtitle: Q&A · contact@example.com
- next_steps:
  - action: 完成 Phase 1 试点
    owner: Alice
    due: 2026-06-15
  - action: 评估扩展到 Phase 2
    owner: Bob
    due: 2026-07-01
```

**关键规则**:
- 每个 `##` h2 = 一张 slide
- h2 形如 `## [layout_name]` 表示特殊 layout(cover/toc/section_divider/summary/closing 不需 action title)
- h2 形如 `## N. action title 句` 表示内容页(N = 章节序号,可对应 outline)
- `<!-- layout: cards -->` HTML 注释指定 layout(可选,缺省按内容推断)
- 图片用标准 `![alt](path)` 语法,path 相对 deck 目录
- `> 数据:Source: ...` 表示数据 slide 引文,渲染时变 footer 上方 italic
- frontmatter YAML 提供 deck 级元数据

### 素材文件夹布局

```
<deck-工作目录>/
├── deck_v1_outline.md          # outline 文档
├── deck_v1_content.md          # 全文文档(终稿)
├── deck_v1.pptx                # build 产出
├── deck_v1_render/             # 渲染图(QA 用,不入库)
│   ├── page-01.jpg
│   └── ...
├── _assets/
│   ├── raw/                    # 用户提供的原始素材
│   │   ├── q4_revenue.csv
│   │   └── customer_logos.png
│   ├── charts/                 # matplotlib 生成的数据图
│   │   ├── q4_revenue.png
│   │   └── review_flow.png    (draw.io 出的也放这)
│   └── refs/                   # 参考文档(用户提供的 PDF / md)
│       └── industry_report.pdf
└── deck_v2_*.md / deck_v2.pptx # 后续迭代版本
```

### md → JSON 转换约束(决策 3a)

agent 在 Stage E Step 1 把 content.md 转 deck_plan.json,**必须遵守**:

1. **不引入新论点**:JSON 里的 title / body / bullet / card 文本必须能在 md 里找到出处(精确匹配 或 显然的压缩)
2. **不放大字数**:每个字段不超 md 原文长度的 110%
3. **layout 推断**:优先 `<!-- layout: X -->` 注释;无注释则按 md 结构推断(单列表 → bullet_list,粗体+冒号 → cards 等)
4. **图片路径透传**:`![alt](path)` 的 path 直接进 `image_path`,不重新生成
5. **生成完反向校验**:转完后 agent 必须 grep deck_plan.json 的所有文本,验证存在于 md 中(diff > 5% 报错)

## agent 自动改 md 的边界(决策 8a)

agent 在视觉 QA 循环发现问题时,**允许修改的 md 操作**:

| 允许 | 不允许 |
|---|---|
| 缩短 action title(超 24 字) | 改变 action title 的语义 / 立场 |
| bullet 字数超限 → 截短 | 删整条 bullet |
| 合并连续 bullet(超数量限制) | 改变 bullet 顺序(=改变论证逻辑) |
| layout 推断错改 layout | 改变 deck 结构(加删 slide) |
| 切换字号 / 颜色(通过 layout 改) | 改 source 引文 / 数据值 |
| 修复 markdown 语法错(missing dash 等) | 改 frontmatter |

每次 agent 改 md 都要:
- 记录到 `auto_md_edits[]` 返回给主线程
- 主线程必须把变更展示给用户(可批量批准)
- 用户可"接受"或"回退到 md 前一版"

## v2 → v3 迁移

**v2 关键产出**(保留可用):
- `helpers.py` 设计 token / footer / source_citation —— 完全保留
- `tech_blue.py` 11 个 make_* layout —— 完全保留
- `build.py` 接收 deck_plan.json 输出 .pptx —— **完全保留**(agent 只是改成从 md 派生 JSON)
- `matplotlib_rc.py` —— 完全保留
- `layout.py` grid —— 完全保留
- `visual-qa.md` 17 项 checklist —— 保留(Stage E 自检用)
- `content-writing.md` 11 layout 字数规则 —— 保留(agent md→JSON 时要遵守)

**v2 要改的**:
- `.claude/agents/iloveppt.md`:agent 行为彻底简化(从 Phase 1/2 改成只做 Stage E)
- `workflow.md`:加 Stage A-E 章节
- `content-writing.md`:加 markdown schema 章节(outline / content)
- `agent-internals.zh.md`:升 v3,讲清主线程 vs agent 分工
- `MANUAL.zh.md`:用户流程从"派发 agent → 审 YAML"改成"主线程对话 → 审 markdown → agent build"

**v2 要新增的**:
- `docs/markdown-schemas.zh.md`(可选):markdown 详细 schema 速查
- `examples/demo_v3_outline.md` + `demo_v3_content.md`:示范文档

**v2 要废弃的**:
- Phase 1 输出的复杂 YAML schema(`top_recommendation` / `scqa` / `mece_check_passed` / `pyramid_check_passed` / `ghost_deck_test_passed` 字段)→ Pyramid 自检搬到 agent 内部 + outline.md 末尾 checkbox 列表
- `bypass_pyramid` 字段(改成 main thread 自行判断是否走 Pyramid)

## 实施计划

| 任务 | 文件 | 估时 |
|---|---|---|
| 写 spec(本文件) | `docs/superpowers/specs/2026-05-23-iloveppt-v3-markdown-first.md` | 1h |
| 重写 agent | `.claude/agents/iloveppt.md`(预计 -50% 行数) | 1h |
| 定义 markdown schema | `skills/pptx-deck/content-writing.md` 加章节 | 30min |
| 更新 workflow | `skills/pptx-deck/workflow.md` 改 7 步为 5 阶段 | 20min |
| 升级 internals doc | `docs/agent-internals.zh.md` → v3 | 1h |
| 改用户手册 | `docs/MANUAL.zh.md` 4-5 章重写 | 1h |
| 测试 + 视觉抽检 + commit + push | tests + git | 30min |

**总估时**: 5h(单 session 可完成)

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| 主线程 Claude 在 Stage A 不擅长用 brainstorming + Pyramid | content-writing.md 写清楚 Pyramid 5 件套;主线程 Claude 读这份文档 |
| agent md→JSON 漂离(决策 3a 的固有风险) | 强约束 + 反向 diff 校验(见 md→JSON 转换约束第 5 条) |
| 用户 markdown 编辑能力差 | MANUAL 写清基本编辑 + 提供 demo md 示例 |
| Visual QA 自动改 md 越界 | 改动边界表(决策 8a 明确允许/不允许);每次都向用户报告 |
| v2 用户切换成本 | 老 brief.yaml 路径保留(主线程读 brief.yaml 后展开成 outline.md);agent 只认 markdown,不认 yaml brief |

## Anti-prompt

- agent 不要回到 Phase 1 出 YAML outline 的老路;outline.md 是主线程产出
- agent 不要自由发挥扩写 md 内容;只能格式类修正(决策 8a 边界)
- agent 不要假装跑过 Pyramid 自检;Stage E Step 0 必须真跑,失败必须 hard stop 返回主线程
- 主线程不要跳过 brainstorming 直接派 agent;agent 收到不完整 content.md 会拒绝构建
