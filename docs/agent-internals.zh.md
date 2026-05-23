# iLovePPT Agent 工作原理(v3)

> 这份文档讲清楚 iLovePPT 系统**怎么工作的**——主线程 dispatcher + 3 agent 架构、5 阶段流程、关键设计决策。
> 适合想理解(或后续改造)系统的人;不是用户操作手册(那个看 [`MANUAL.zh.md`](MANUAL.zh.md))。
>
> **v3(2026-05-23)重大改动**:
> - 从"agent 端到端"变成 **3 agent 流水线**(brainstorm + author + builder)
> - 主线程**退化为 thin dispatcher**(只 router 消息,不持有业务逻辑)
> - 多轮对话通过"**多次派发 + state file**"实现(每 agent Read 自己的 state.json 跨派发记忆)
>
> 旧 v2 设计仍在 [v2 agent design](superpowers/specs/2026-05-23-iloveppt-agent-design.md)。
> v3 spec:[v3 markdown-first](superpowers/specs/2026-05-23-iloveppt-v3-markdown-first.md)。
>
> **决策 1 订正记录(同日)**:v3 spec 初稿曾选"主线程做 Stage A-D"(决策 1a),后发现错误归因(subagent 其实可以通过多次派发+state 实现多轮),订正为**1c:三 agent 拆分**。详见 v3 spec 顶部订正记录。

---

## 目录

- [1. 四层架构:主线程 / agent / skill / build.py](#1-四层架构主线程--agent--skill--buildpy)
- [2. 入口:用户怎么发起一次任务](#2-入口用户怎么发起一次任务)
- [3. 5 阶段流程(Stage A-E)—— 主线程做前 4 个,agent 做最后 1 个](#3-5-阶段流程stage-a-e--主线程做前-4-个agent-做最后-1-个)
- [4. Stage A-D 详解:主线程怎么协同用户出 markdown](#4-stage-a-d-详解主线程怎么协同用户出-markdown)
- [5. Stage E 详解:agent 怎么把 markdown 变 .pptx](#5-stage-e-详解agent-怎么把-markdown-变-pptx)
- [6. 关键设计决策:为什么这么设计](#6-关键设计决策为什么这么设计)
- [7. 一次完整调用的 timeline 示例](#7-一次完整调用的-timeline-示例)
- [8. 这套设计避开了哪些常见坑](#8-这套设计避开了哪些常见坑)
- [9. 进一步阅读](#9-进一步阅读)
- [10. v2 → v3 变迁说明](#10-v2--v3-变迁说明)

---

## 1. 四层架构:主线程 / 3 agent / skill / build.py

v3 的核心架构:**主线程 = router**,**3 个 agent = 智能**,**skill = 知识库 + 工具**,**build.py = 纯机械构建器**:

```mermaid
flowchart TB
    M["<b>主线程 Claude</b>(thin dispatcher)<br/>只 router 消息 · 不持有 PPT 业务逻辑<br/>看 agent 返回的 next_action,转发用户答 / 派下一个 agent"]
    BS["<b>iloveppt-brainstorm</b>(Stage A+B)<br/>多次派发 · state: .iloveppt_dialog_state.json<br/>多轮对话挖需求 / 引导素材 / 落 _assets/"]
    AU["<b>iloveppt-author</b>(Stage C+D)<br/>多次派发 · state: .iloveppt_author_state.json<br/>按 Pyramid 出 outline.md → 拓写 content.md → 出图"]
    BD["<b>iloveppt</b>(Stage E builder)<br/>单次派发(内含 ≤ 3 轮视觉 QA)<br/>读 content.md → Pyramid 自检 → md→JSON → build.py → 视觉 QA"]
    SK["<b>Skill 层</b>(共享知识库)<br/>skills/pptx-deck · pptx · diagram<br/>content-writing.md · visual-qa.md · helpers.py · matplotlib_rc.py"]
    BP["<b>build.py</b>(纯机械)<br/>deck_plan.json → .pptx + PNG<br/>不调 LLM"]
    M -->|派发| BS
    BS -->|next_action: dispatch_author| M
    M -->|派发| AU
    AU -->|next_action: dispatch_builder| M
    M -->|派发| BD
    BS -.->|读| SK
    AU -.->|读| SK
    BD -.->|读| SK
    BD -->|调| BP
    classDef main fill:#FFF,stroke:#888,stroke-width:1.5px,color:#444
    classDef stage1 fill:#DCFCE7,stroke:#16A34A,stroke-width:2px,color:#14532D
    classDef stage2 fill:#FCE7F3,stroke:#BE185D,stroke-width:2px,color:#831843
    classDef stage3 fill:#E6F0FC,stroke:#1E6FE0,stroke-width:2px,color:#0B2A4A
    classDef skill fill:#F5F5F5,stroke:#555,stroke-width:1.5px,color:#222
    classDef tool fill:#FFF4E6,stroke:#D97706,stroke-width:1.5px,color:#7C2D12
    class M main
    class BS stage1
    class AU stage2
    class BD stage3
    class SK skill
    class BP tool
```

**关键认知**:
- **主线程** 是 router —— 不知道 PPT 怎么做,只按 agent 返回的 `next_action` 派下一步
- **3 个 agent** 分别管 Stage A+B / C+D / E,**各自维护 state file**,在多次派发间记忆
- **skill** 是所有 agent 实时 Read 的"运行手册 + 工具箱"
- **build.py** 是 builder agent 调用的纯机械工具

为什么 3 agent 而非 1 个端到端?因为 brainstorm 和 author 都需要**多轮交互**,通过多次派发 + state file 实现;builder 是单次派发完成。三者角色 / 频率 / 复杂度差异大,拆开维护更清晰。详见 §6.6。

---

## 2. 入口:用户怎么发起一次任务

用户输入一句话需求 → 主线程识别意图 → **派发 iloveppt-brainstorm**(第 1 个 agent)。之后主线程跟着 agent 返回的 `next_action` 走:

```mermaid
flowchart TB
    U[用户:"帮我做个 X 的 PPT"] --> M["主线程 Claude<br/>识别 PPT 意图 +<br/>选 working_dir"]
    M --> D1[派发 iloveppt-brainstorm<br/>初次:initial_request=用户的一句话]
    D1 --> R1{agent 返回什么?}
    R1 -->|next_action: ask_user| Q1[展示问题给用户<br/>收答]
    Q1 --> D1
    R1 -->|next_action: dispatch_author| D2[派发 iloveppt-author<br/>带 brief + assets]
    D2 --> R2{agent 返回什么?}
    R2 -->|ask_user| Q2[展示 outline/content<br/>收用户改/批]
    Q2 --> D2
    R2 -->|dispatch_builder| D3[派发 iloveppt<br/>带 content_md_path]
    D3 --> R3[builder 单次派发<br/>内部 ≤ 3 轮视觉 QA]
    R3 --> Done([next_action: done<br/>pptx + auto_md_edits])
    classDef start fill:#FFF,stroke:#333,stroke-width:1.5px
    classDef main fill:#F5F5F5,stroke:#888,stroke-width:1.5px
    classDef stage1 fill:#DCFCE7,stroke:#16A34A,stroke-width:2px,color:#14532D
    classDef stage2 fill:#FCE7F3,stroke:#BE185D,stroke-width:2px,color:#831843
    classDef stage3 fill:#E6F0FC,stroke:#1E6FE0,stroke-width:2px,color:#0B2A4A
    classDef gate fill:#FFF4E6,stroke:#D97706,stroke-width:1.5px,color:#7C2D12
    class U,Done start
    class M main
    class D1,Q1 stage1
    class D2,Q2 stage2
    class D3,R3 stage3
    class R1,R2 gate
```

**3 个 agent 的 description 各管一段**:

| Agent | description 关键词 | 触发条件 |
|---|---|---|
| `iloveppt-brainstorm` | "需求挖掘 / 素材摄入 / FIRST agent" | 用户说"做 PPT" → 主线程派发 |
| `iloveppt-author` | "内容规划 / 全文拓写 / SECOND agent" | brainstorm 返回 `dispatch_author` → 主线程派发 |
| `iloveppt` | "终稿构建 / builder / THIRD agent" | author 返回 `dispatch_builder` → 主线程派发 |

**关键变化(vs v2)**:
- 用户**不直接 `@agent-iloveppt`**(那是 builder,会因缺 content.md 而 reject)
- 主线程**不持有任何 PPT 业务逻辑**——它只是状态机的转发者
- agent 的"多轮"通过**多次派发 + state file** 实现(详见 §3)

---

## 3. 5 阶段流程(Stage A-E,3 agent 分工)

5 个阶段分到 3 个 agent,**两个用户 checkpoint**(outline.md 审 + content.md 审)。多轮交互通过"多次派发同一 agent + state file"实现:

```mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant M as 主线程<br/>(dispatcher)
    participant BS as iloveppt-<br/>brainstorm
    participant AU as iloveppt-<br/>author
    participant BD as iloveppt<br/>(builder)

    U->>M: "帮我做 X 的 PPT"
    rect rgb(220, 252, 231)
        Note over BS: <b>Stage A+B</b><br/>需求挖掘 + 素材摄入
        loop ≥ 1 次派发 + state.json
            M->>+BS: dispatch(initial 或 user_response)
            Note over BS: Read state.json → 问下一批<br/>或收齐 → 准备移交
            BS-->>-M: ask_user 或 dispatch_author
            M->>U: 转发问题
            U->>M: 答 / 提供素材
        end
    end
    rect rgb(252, 231, 243)
        Note over AU: <b>Stage C+D</b><br/>outline.md + content.md
        loop ≥ 2 次派发(Stage C → 审 → D → 审)
            M->>+AU: dispatch(stage + brief 或 user_response)
            Note over AU: Read state.json → 出 outline/content<br/>或改;Pyramid 自检;调 matplotlib 出图
            AU-->>-M: ask_user(审) 或 dispatch_builder
            M->>U: 转发 md 路径
            U->>M: 批准 / 改
        end
    end
    rect rgb(230, 240, 252)
        Note over BD: <b>Stage E</b><br/>终稿构建
        M->>+BD: dispatch(content_md_path)
        Note over BD: Pyramid 自检 → md→JSON →<br/>build.py → 视觉 QA × ≤3 轮<br/>(自动改 content.md)
        BD-->>-M: done(pptx + auto_md_edits)
    end
    M->>U: 交付成品 + agent 自动改动报告
```

### 多轮通过"多次派发 + state file"实现的细节

每个对话密集 agent(brainstorm / author)被多次派发,**每次都是全新的隔离 context**。靠 state file 跨派发记忆:

```
Round 1:
  主线程 → 派发 iloveppt-brainstorm(initial_request)
  agent:
    - Read .iloveppt_dialog_state.json → 不存在,初始化
    - 解析 initial_request 提取部分字段
    - Write state(round=1, collected={...})
    - 返回 ask_user(还缺哪几个字段的问题)

Round 2:
  主线程 → 派发 iloveppt-brainstorm(user_response="技术团队 / 15 分钟")
  agent:
    - Read .iloveppt_dialog_state.json → 有,载入 round=1 状态
    - 解析 user_response → audience/duration 补上
    - Write state(round=2, collected={... audience, duration})
    - 返回 ask_user(还缺顶端论点等)

... 直到 status=complete → 返回 dispatch_author
```

这套机制让 **agent 既能多轮对话,主线程又不持有 PPT 业务逻辑**。

### Builder 不需要 state file

iloveppt(builder)是**单次派发完成**:Read content.md → Pyramid 自检 → md→JSON → build.py → 视觉 QA × ≤ 3 轮(全在一次 dispatch 内)→ 返回 done。

视觉 QA 循环中改 content.md 的所有变更记录到返回的 `auto_md_edits[]`,无需 state file。

---

## 4. Stage A-D 详解:brainstorm + author 两 agent 怎么出 markdown

主线程 Claude 在用户对话中跑 Stage A-D,产出两份用户可读的 markdown:

```mermaid
flowchart TB
    I([用户:一句话需求]) --> A
    A["<b>Stage A · 需求挖掘</b><br/>调 brainstorming skill<br/>多轮问 audience/duration/<br/>top_recommendation/theme/output<br/>未收齐 → 不进 B"] --> B
    B["<b>Stage B · 素材摄入</b><br/>对话中识别用户素材<br/>prompt:数据 / 图 / 模板 / 文档<br/>落到 _assets/{raw,charts,refs}/"] --> C
    C["<b>Stage C · 内容规划</b><br/>按 Pyramid 5 件套设计 outline<br/>产出 deck_v1_outline.md"] --> UC{用户审 outline}
    UC -->|改| C
    UC -->|批准| D["<b>Stage D · 全文拓写</b><br/>每节按 layout 字数规则展开<br/>调 matplotlib 出图嵌入 md<br/>关键数据加 Source 引文<br/>产出 deck_v1_content.md"]
    D --> UD{用户审 content}
    UD -->|改某节| D
    UD -->|批准| OUT([派发 agent 跑 Stage E])
    classDef io fill:#FFF,stroke:#333,stroke-width:1.5px,color:#222
    classDef stage fill:#DCFCE7,stroke:#16A34A,stroke-width:2px,color:#14532D
    classDef gate fill:#FFF4E6,stroke:#D97706,stroke-width:2px,color:#7C2D12
    class I,OUT io
    class A,B,C,D stage
    class UC,UD gate
```

**关键产出**:
- `deck_v1_outline.md` —— 大纲 + Pyramid 自检 checkbox 列表
- `deck_v1_content.md` —— 完整文案(每页 h2 + 正文 + 嵌入图)
- `_assets/charts/*.png` —— 图表素材

详细 schema 见 [content-writing.md v3 markdown schema 章节](../skills/pptx-deck/content-writing.md#-v3-markdown-schema主线程--agent-接口契约)。

---

## 5. Stage E 详解:agent 怎么把 markdown 变 .pptx

agent 在独立上下文中跑 5 步。**Step 0 是质量门**(Pyramid 自检),不过则 hard stop 返回主线程,不允许"自动修复内容"。

### 5.1 Stage E 主流程

```mermaid
flowchart TB
    I([入参:<br/>content_md_path + output_pptx + theme + footer_meta]) --> S0
    S0["<b>Step 0</b> · 质量门<br/>Read content.md + content-writing.md<br/>跑 Pyramid 自检 7 项"] --> P
    P{自检全过?}
    P -->|否| HS["<b>hard stop</b><br/>返回 error: pyramid_check_failed<br/>列 failed_items + suggestion<br/>不试图自动修复(动观点是越界)"]
    P -->|是| S1["<b>Step 1</b> · md → deck_plan.json<br/>严约束:不引入新论点 / 不放大字数<br/>layout 推断 + 图片路径透传<br/>反向 diff 校验(差异 > 5% 报错)"]
    S1 --> S2["<b>Step 2</b> · 跑 build.py<br/>python3 skills/pptx-deck/build.py &lt;deck_plan.json&gt;<br/>→ .pptx + 渲染 PNG<br/>build.py 自动加 footer/页码/source 引文"]
    S2 --> S3["<b>Step 3</b> · 视觉 QA 循环(≤ 3 轮)<br/>详见 §5.2 与 §5.3"]
    S3 --> S4["<b>Step 4</b> · 返回 YAML<br/>pptx_path · qa_rounds<br/>auto_md_edits[] · review_needed[]<br/>pyramid_check 结果"]
    classDef io fill:#FFF,stroke:#333,stroke-width:1.5px
    classDef step fill:#F5F5F5,stroke:#555
    classDef gate fill:#FFF4E6,stroke:#D97706,stroke-width:2px,color:#7C2D12
    classDef fail fill:#FEE2E2,stroke:#DC2626,stroke-width:1.5px,color:#7F1D1D
    class I,S4 io
    class S0,S1,S2,S3 step
    class P gate
    class HS fail
```

### 5.2 Step 3 视觉 QA 循环细节(v3:修 md 而非 JSON)

```mermaid
flowchart TB
    Start([每页渲染图 page-N.jpg]) --> Read[Read PNG<br/>对照 17 项 checklist<br/>基础 12 + 进阶 5]
    Read --> Q{发现 issues?}
    Q -->|无| Next[标记本页通过]
    Q -->|有| Cnt{该页修过<br/>&lt; 3 次?}
    Cnt -->|是| AE{允许的格式修复?<br/>(见 §5.3 边界表)}
    AE -->|是| Fix["改 content.md 该 slide<br/>记入 auto_md_edits[]"]
    AE -->|否| Deg
    Fix --> Re1[重跑 md → deck_plan.json] --> Re2[rerun build.py] --> Read
    Cnt -->|否| Deg["<b>降级</b><br/>加入 review_needed<br/>接受当前版本"]
    Deg --> Next
    Next --> Loop{还有页?}
    Loop -->|是| Start
    Loop -->|否| Done([QA 完成 → Step 4])
    classDef io fill:#FFF,stroke:#333,stroke-width:1.5px
    classDef act fill:#F5F5F5,stroke:#555
    classDef gate fill:#FFF4E6,stroke:#D97706,stroke-width:2px,color:#7C2D12
    classDef pass fill:#DCFCE7,stroke:#16A34A,stroke-width:1.5px,color:#14532D
    classDef fail fill:#FEE2E2,stroke:#DC2626,stroke-width:1.5px,color:#7F1D1D
    class Start,Done io
    class Read,Fix,Re1,Re2 act
    class Q,Cnt,AE,Loop gate
    class Next pass
    class Deg fail
```

**v2 vs v3 的关键差异**:v2 改 `deck_plan.json`(用户审过的源是 outline yaml,JSON 是 agent 自己写的,改它无所谓);v3 改 `content.md`(用户审过的源就是 md,**改 md 等于改用户审过的内容**——所以有严格边界,见 §5.3)。

### 5.3 Agent 自动改 content.md 的边界(决策 8a)

| ✅ 允许(纯格式修正) | ❌ 禁止(动观点 / 数据) |
|---|---|
| 缩短 action title(超 24 字) | 改 action title 立场 / 语义 |
| bullet 字数超限 → 截短 | 删整条 bullet |
| 合并连续 bullet(超数量) | 改 bullet 顺序(= 改论证) |
| layout 推断错改 layout 注释 | 加删整张 slide |
| 修 markdown 语法错(missing dash 等) | 改 source 引文 / 数据值 |
| 切换字号/颜色(通过 layout 注释) | 改 frontmatter(top_recommendation / SCQA 等) |

每次自动改都要:
- 记录到返回 yaml 的 `auto_md_edits[]`,含 `page / issue / before / after`
- 主线程展示给用户(可批量批准或回退某条)
- 用户可以"接受 + 继续"或"回退到 agent 改前的 md 版本重新介入"

### 5.4 Cross-cutting concerns:build.py 在 fn 调用后自动加的东西

`build.py` 调完 `theme.make_<layout>()` 后,**还会自动处理 3 类"横切关注点"** —— theme `make_*` 函数完全不感知,职责干净:

```mermaid
flowchart TB
    F[make_<layout>(prs, **fields) 返回] --> P1{slide 有 source 字段?}
    P1 -->|是| SC[H.source_citation<br/>渲染 'Source: ...' 在 footer 上方<br/>italic / GRAY_500 / 9pt]
    P1 -->|否| P2
    SC --> P2{layout 在 FOOTERED_LAYOUTS?<br/>(8 种内容页,排除 cover/divider/closing)}
    P2 -->|是| FT[H.footer<br/>分隔线 + 'N / TOTAL' 右对齐<br/>+ classification·project·version 左侧<br/>(从 plan.footer_meta 读)]
    P2 -->|否| END([本 slide 完成])
    FT --> END
    classDef io fill:#FFF,stroke:#333,stroke-width:1.5px
    classDef gate fill:#FFF4E6,stroke:#D97706,stroke-width:2px,color:#7C2D12
    classDef act fill:#E6F0FC,stroke:#1E6FE0,stroke-width:2px,color:#0B2A4A
    class F,END io
    class P1,P2 gate
    class SC,FT act
```

**为什么 build.py 集中做,而不是放进每个 `make_*`?**

- theme `make_*` 只关心**布局视觉**(把 title/items 摆好);footer 和 source 是**规范层关注**(每页都要有),不该让每个 layout 函数都重复处理
- 想新增一种 cross-cutting(比如水印 / classification 徽标),改 build.py 一处即可,11 个 layout 一起生效
- agent 写 `deck_plan.json` 时,这些字段是**通用 slot**(任何 layout 都可加 `source`),不需要为每种 layout 各想一遍

**v3 下这套机制依然成立**:agent 在 Step 1 (md→JSON) 把 md 里的 `> 数据:Source: ...` 写成 JSON 的 `source` 字段;`footer_meta` 从 frontmatter 透传到 plan 顶层。build.py 后续的渲染流程没变。

---

## 6. 关键设计决策:为什么这么设计

### 6.1 build.py 是"纯机械",智能全在 agent

**问的人最多的问题:为什么 build.py 不内嵌 LLM 调用?**

答:**因为接缝必须诚实。**

```mermaid
flowchart LR
    A["<b>Agent</b><br/>(智能侧)<br/>brief 解析 · 文案拓写<br/>视觉 QA 判断"]
    B["<b>build.py</b><br/>(机械侧)<br/>JSON → .pptx + PNG<br/>无 LLM 调用"]
    A -->|"<b>deck_plan.json</b><br/>纯数据,无歧义"| B
    classDef agent fill:#E6F0FC,stroke:#1E6FE0,stroke-width:2px,color:#0B2A4A
    classDef tool fill:#FFF4E6,stroke:#D97706,stroke-width:2px,color:#7C2D12
    class A agent
    class B tool
```

- **可重放**:agent 死了,你拿着 `deck_plan.json` 自己 `python3 build.py` 也能出一模一样的 .pptx
- **可调试**:出问题先看 `deck_plan.json` —— 是 agent 没拓写好,还是 build.py 渲染错?一目了然
- **可测试**:`evals/run_eval.sh` 跑固定 deck_plan,验证 build.py 没回归——不掺 LLM 不确定性

如果 build.py 内嵌 LLM 调用,这 3 条全废了。

### 6.1.1 v3 多了一个接缝:content.md(用户接口)vs deck_plan.json(构建接口)

v2 只有 1 个接缝:`deck_plan.json`(agent ↔ build.py)。

v3 有 **2 个接缝**:

```mermaid
flowchart LR
    U[用户] -->|审 markdown| MD["<b>content.md</b><br/>(用户接口)<br/>人类可读"]
    MD -->|agent 转换| JSON["<b>deck_plan.json</b><br/>(构建接口)<br/>JSON,机器读"]
    JSON -->|build.py| PPTX[".pptx"]
    classDef u fill:#FFF,stroke:#333
    classDef interface fill:#E6F0FC,stroke:#1E6FE0,stroke-width:2px,color:#0B2A4A
    classDef tool fill:#FFF4E6,stroke:#D97706,stroke-width:2px,color:#7C2D12
    class U u
    class MD,JSON interface
    class PPTX tool
```

**为什么不直接 content.md → .pptx,省一个接缝?**

- `deck_plan.json` 仍是 build.py 的契约,**已经测试 + 评估覆盖**(`evals/run_eval.sh` 跑固定 JSON)
- markdown → JSON 转换里有"严约束"(不引入新论点),正好用 JSON 做"用户审过的内容的事实快照"
- 未来若要支持其他源(如 Notion API / Confluence),只需写新的 `X → JSON` 转换,不动 build.py

### 6.2 deck_plan.json 这个"接缝"是设计核心

```json
{
  "theme": "tech_blue",
  "output": "./deck.pptx",
  "footer_meta": {
    "classification": "INTERNAL",
    "project": "Project Atlas",
    "version": "v2.0"
  },
  "slides": [
    {"layout": "cover", "title": "...", "subtitle": "...",
     "prepared_by": "...", "date": "...", "version": "...",
     "project_code": "...", "classification": "INTERNAL"},
    {"layout": "cards", "title": "...", "cards": [{"title":"...","body":"..."}]},
    {"layout": "table", "title": "...", "headers": [...], "rows": [...],
     "source": "Source: 公司财报 2025 Q4"},
    {"layout": "closing", "subtitle": "Q&A",
     "next_steps": [{"action":"...","owner":"Alice","due":"2026-06-15"}]}
  ]
}
```

每个 slide 对象的 schema 由 `layout` 字段决定——这就是 agent 和 build.py 之间的"接口契约"。

11 种 layout 的字段约束写在 `content-writing.md`,agent 拓写时必须遵守。

**两类字段**:

- **layout-specific**:`cards.cards[]` / `table.headers` 等 —— 进 `make_<layout>(**fields)`
- **cross-cutting**:`source`(数据 slide 引文)/ `footer_meta`(顶层,机密/项目/版本)/ cover 的 `prepared_by/date/version/...` / closing 的 `next_steps[]` —— build.py 或对应 make_* 单独处理(详见 §5.3)

### 6.3 Skill docs 是产品,不是文档

`.md` 文档不是"参考材料"——**它们是 agent 在运行时实时 Read 的"运行手册"**。

改 `content-writing.md` 的金字塔自检规则 → agent 下次跑 Phase 1 时就按新规则跑。这就是为什么这些 `.md` 写得像"操作指令"而不是"概念解释"。

### 6.4 视觉 QA 为什么是 Claude 做,不是脚本?

因为视觉问题(文字溢出、字体 fallback、留白失衡、颜色对比度)用 Python 规则识别极其脆弱,而 Claude 多模态读 PNG 直接判断又快又准。

**循环逻辑**:

```
fix → rebuild → recheck → if still bad after 3 rounds → review_needed
```

3 轮上限是**反死循环兜底**——3 轮还修不好,多半是 layout 选错(改字号 / 位置都救不了),降级让人审。

### 6.5 SSOT(单一权威源)防漂移

颜色 / 字体 / 尺寸有且只有一份定义,在 `skills/pptx/helpers.py`:

```python
BRAND_PRIMARY = RGBColor(0x0A, 0x52, 0xBF)   # AAA 7.00:1 对比度(投影必过)
ACCENT        = RGBColor(0x00, 0x7A, 0x6D)   # AA 5.2:1
FONT_CN       = "Microsoft YaHei"            # 系统兼容默认
FONT_CN_DESIGN= "Source Han Sans CN"         # 设计感更强(opt-in)
SLIDE_W       = Inches(13.333)
FOOTER_TOP    = Inches(7.0)
```

所有 theme / helper / build.py 都引用这些常量,不复制。改一处全 deck 生效。

**两条独立 SSOT 链**(2026-05-23 拆分):

- **`helpers.py`** —— `.pptx` 渲染域的字体 / 色 / 尺寸 / 几何常量
- **`skills/diagram/matplotlib_rc.py`** —— matplotlib 数据图域,从 `helpers.py` 抄录 hex 字符串供 matplotlib 用,保证 chart 与 slide 视觉一致(字体 / 配色 / 网格风格)

为什么拆?matplotlib 用 `font.sans-serif` 列表 / hex 字符串,跟 python-pptx 的 `RGBColor` / `<a:ea typeface>` 类型不兼容,无法直接共享对象。所以 matplotlib_rc 是"helpers.py 的派生镜像"——改 helpers 后需手动同步(改色值时 grep `_hex(H.` 找到所有 mirror 点)。

### 6.6.1 v3:为什么 3 agent 拆分 + dispatcher,而非 1 个端到端 / 或塞主线程

最初(v1/v2)直觉:agent 跑端到端,用户只看 outline 一次。后来发现:

| 问题 | 原因 |
|---|---|
| 用户不会写 brief | 一句话扔进来,缺关键字段 |
| 用户审 outline 是盲批 | YAML 不可读 |
| 文案没 sign-off | 用户没在 .pptx 前看到文案 |
| 改 1 个字 = rebuild 全 deck | 用户介入的颗粒度太粗 |

**v3 spec 初稿曾错误归因**:把"无法多轮对话"归因到"subagent 是单次派发",从而提出"全部搬主线程"(决策 1a)。

但实际上 **subagent 完全可以多轮** —— 通过"多次派发 + state file"(v2 的 Phase 1 → 审 → Phase 2 就是 2 次派发)。把这套扩到 N 次完全可行。

**1a 的真实代价**(我们后来才意识到):

- 主线程上下文膨胀(每个 PPT 加 ~30K tokens 永久 context)
- 不可移植(每个新 session 用户得重新对话,没有清晰入口)
- 不可发现(没有 `@agent` trigger,用户不知道有这功能)
- 主线程做重活(拓写 / 跑 matplotlib),与"主线程是普通 chat"定位冲突

**订正后的 v3(决策 1c)** = 3 agent 拆分 + 主线程 thin dispatcher:

| 任务 | v2 | v3 初稿(1a 错) | v3 订正(1c 对) |
|---|---|---|---|
| 多轮挖需求 | agent 硬塞 1 次(失败) | 主线程做 | iloveppt-brainstorm 多次派发 |
| 大纲设计 | agent Phase 1 单向 | 主线程做 | iloveppt-author Stage C 多次派发 |
| 文案拓写 | agent Phase 2 内部 | 主线程做 | iloveppt-author Stage D 多次派发 |
| 视觉构建 | agent Phase 2 末尾 | agent(简化) | iloveppt builder 单次派发 |
| 主线程承重 | 几乎零 | 全部对话 + 拓写 | 零(纯 router) |

**v3 订正后的核心收益**:
- agent 各自独立上下文 → 主线程清洁,可同时跟用户聊别的
- 3 个 agent 角色窄,test/debug/optimize 更聚焦
- 多轮通过 state file 实现 → 跨 session / 跨用户重启都能恢复
- 用户可以 `@agent-iloveppt-brainstorm` 显式启动(可发现可移植)

**代价**:多次派发有 overhead(每次 agent 启动要 Read 文档)。但 agent 内部可以缓存(读完写到 state),减轻问题。

### 6.7 字号 / 色 / 字段都对标 BCG/McKinsey

2026-05-23 全面对标行业最佳实践,17 项调整落地:

| 调整 | 旧 → 新 | 依据 |
|---|---|---|
| body 字号 | 14pt → 18pt | BCG/Beautiful.ai/BrightCarbon 最低投影标准 |
| 页标题 | 28pt → 32pt | MBB action title 标准 |
| BRAND_PRIMARY | `#1E6FE0`(AA) → `#0A52BF`(AAA 7:1) | WebAIM 投影建议 |
| Source 引文 | 无 → 自动加在 footer 上方 | MBB 数据 slide 硬要求 |
| Cover 元数据 | 无 → prepared_by/date/version/project_code/classification | 咨询稿标准 |
| Closing 结构 | "谢谢"+ subtitle → 可选 next_steps 列表 | closing = call to action |
| Footer 左侧 | 仅 page num → +classification·project·version | MBB 标准 footer |
| matplotlib 风格 | 用 default → matplotlib_rc SSOT(BRAND_*  配色 + YaHei) | 防 chart 与 deck 视觉割裂 |
| action title | 无字数上限 → ≤ 24 字硬约束 | 防换行破布局 |
| 12-col grid | 无 → `grid_columns()` 锚定 | 防跨页对不齐 |
| 视觉 QA | 12 项 → 17 项 | + 留白 / 热区 / 主色比例 / 跨页一致 |

完整对标过程见会话历史(执行前做了 web research + 18 项 gap audit)。

---

## 7. 一次完整调用的 timeline 示例(v3)

假设你说:`帮我做一份"评审办法 v1.0"的 PPT,15 分钟,技术受众`

```
=== Stage A · 需求挖掘(主线程对话) ===
T+0s     用户输入一句话
T+5s     主线程:"给谁看?有数据吗?有现成图吗?预期多长?"
T+30s    用户答 → 主线程接着问
T+2min   字段收齐(audience/duration/top_recommendation/theme)

=== Stage B · 素材摄入 ===
T+2.5m   主线程:"你提到 Q4 数据,可以粘贴或给文件路径吗?"
T+3min   用户给 ./q4_revenue.csv → 主线程 Read + 解析
T+3.5m   主线程:"5 阶段流程图,你想画还是用 draw.io 现画?"
T+4min   用户:"现画" → 主线程稍后调

=== Stage C · 内容规划 ===
T+4.5m   主线程跑 Pyramid 设计 outline
T+5min   写 deck_v1_outline.md(7 章节 + Pyramid 自检 checkbox)
T+5min   "Outline 在 deck_v1_outline.md,审一下"
─── 你审 outline,改第 3 节标题,回 "批准" ───
T+8min   

=== Stage D · 全文拓写 ===
T+8min   主线程基于 outline 展开每节文案
T+9min   调 matplotlib 出 Q4 revenue chart → _assets/charts/q4.png
T+10min  调 draw.io 出 5 阶段流程图 → _assets/charts/review_flow.png
T+11min  写 deck_v1_content.md(20 页 + 嵌入 2 张图 + Source 引文)
T+11min  "全文在 deck_v1_content.md,逐页审"
─── 你审 content,改第 5 页一个数字,回 "批准" ───
T+15min

=== Stage E · agent 派发构建 ===
T+15min  主线程派发 agent(content_md_path + theme + footer_meta)
T+15.5m  Agent 启动,Read content.md + Pyramid 自检 → 全过
T+16min  md → deck_plan.json(20 slide 字段)
T+17min  跑 build.py → .pptx + 20 张 PNG(~60s)
T+18min  视觉 QA 第 1 轮:Read 20 PNG,发现 page-5 action title 27 字超限
T+18.5m  auto_md_edit:改 content.md page 5 标题为 18 字 → 重 build
T+19.5m  视觉 QA 第 2 轮:全部通过
T+20min  返回 .pptx 路径 + auto_md_edits[1 条] + review_needed: []

=== 主线程交付 ===
T+20min  "成品 /tmp/deck_v1.pptx;agent 自动改了 content.md page 5
         标题从 'X' 改成 'Y'(超 24 字限制),已记录。如要回退说一声。"
```

**对比 v2**:v2 全程 ~5 分钟(纯 agent),但用户只在 outline 一次 sign-off。v3 全程 ~20 分钟,**用户在对话中投入 5-10 分钟**,但拿到的成品是真正"协同设计"出来的。

---

## 8. 这套设计避开了哪些常见坑

### 流程层

| 坑 | 这套设计的防御 |
|---|---|
| 一口气跑完,大纲跑偏要等成品才发现 | 两阶段 + checkpoint |
| LLM 出 .pptx 不可重放、不可调试 | `deck_plan.json` 接缝,build.py 纯机械 |
| 大纲是话题堆叠没论证 | 金字塔原理 5 件套 + Pyramid 自检表 7 项 |
| 全是文字 bullet 没图 | Phase 1 强制图层规划,4 类图决策表 |
| 视觉 fallback、字体错、留白歪 | Phase 2 视觉自检循环,最多 3 轮 |
| 无限循环改不动 | 3 轮上限 + review_needed 降级 |
| 改一处颜色要改 10 个文件 | SSOT in helpers.py + matplotlib_rc.py |
| agent 一直跑成本失控 | subagent 隔离上下文 + 自带 ~95% compaction 兜底 |

### 视觉规范层(2026-05-23 对标 BCG/McKinsey 后补)

| 坑 | 这套设计的防御 |
|---|---|
| body 11-14pt 在投影上看不清 | 默认 body 18pt(行业最低),字数上限同步收紧 30% |
| 主色对比度不过 AAA,投影泛白 | BRAND_PRIMARY 强制 `#0A52BF` (7:1),有单元测试守护 |
| 数据 slide 不标 source,违反咨询合规 | `source` 字段任何 layout 可加,build.py 自动渲染 |
| 内容页没页码 / 页脚,看不出"第几页" | build.py 自动加 footer + "N / TOTAL"(8 种 layout) |
| 机密文件分发缺 classification 徽标 | `footer_meta: {classification, project, version}` 每页 footer 显示 |
| 封面/封底缺咨询元素(准备方/日期/版本) | `make_cover` 加 5 个可选 meta 字段;`make_closing` 支持 next_steps |
| chart 风格与 slide 视觉割裂 | `matplotlib_rc.apply_iloveppt_style()` 单一 SSOT,BRAND_* 配色 + YaHei 字体 |
| action title 太长换行破布局 | ≤ 24 字硬约束(content-writing.md 写入 Pyramid 自检) |
| 跨页元素对不齐(cards 第一卡 x 坐标各页不同) | `grid_columns()` 12-col grid 锚定,跨页一致 |
| 视觉 QA 只看单页,deck-level 不一致漏检 | 17 项 checklist + Deck-level 一致性 3 项(配色比例 / 字号层级 / 同 layout 对齐) |
| 主色泛滥(单页 60% BRAND_PRIMARY) | 60-30-10 视觉 QA 项(主色面积 ≤ 30%) |

### 协同设计层(v3 新增)

| 坑 | 这套设计的防御 |
|---|---|
| 用户不会写 brief | iloveppt-brainstorm 多轮派发问到收齐 |
| 用户审 YAML 看不懂(盲批) | 改成 markdown 双 checkpoint(outline.md + content.md) |
| 数据图 / 用户已有图没入口 | brainstorm Stage B 显式引导,落 `_assets/{raw,charts,refs}/` |
| 文案错字要等 .pptx 出来才发现 | author Stage D 出 content.md,审过才进 builder |
| 手改 .pptx 后 agent 重跑覆盖 | 用户改的是 content.md,builder 永远从 md 派生 |
| 多版本管理乱(deck.pptx 覆盖) | `deck_v1.md` / `deck_v2.md` 显式版本号 |
| builder 改了 md 用户不知道 | `auto_md_edits[]` 返回 + 主线程展示 |
| author 拓写引入用户没说的话 | md → JSON 严约束 + 反向 diff 校验(差异 > 5% 报错) |
| 用户绕过流程直接 `@iloveppt`(builder) | builder 检查入参缺 content_md_path 直接 reject |
| 主线程被 PPT 任务污染 | 3 agent 拆分 + 主线程纯 dispatcher,主线程不持有 PPT 逻辑 |
| 多次派发 overhead | agent state file 可缓存已 Read 的文档摘要,减重派开销 |

---

**一句话总结(v3 订正后)**:iLovePPT 把"写 PPT"拆成 **3 个 agent**(brainstorm 挖需求 + author 出 markdown + builder 出 pptx),**主线程退化为 thin dispatcher**(只 router 不持有业务逻辑)。多轮交互通过"**多次派发 + state file**"实现。两个用户 checkpoint(outline.md / content.md)+ 两个接缝(content.md / deck_plan.json)+ SSOT(helpers.py + matplotlib_rc.py)+ 17 项视觉规范 + Pyramid 自检 + md→JSON 严约束防各种漂移。

---

## 9. 进一步阅读

每一块都有更深入的权威文档:

| 想了解 | 看 |
|---|---|
| **v3 设计 spec(权威,8 决策 + 接口契约)** | `docs/superpowers/specs/2026-05-23-iloveppt-v3-markdown-first.md` |
| Agent 完整 system prompt(v3 简化为 builder-only) | `.claude/agents/iloveppt.md` |
| Agent 旧 v2 设计 rationale(供对比) | `docs/superpowers/specs/2026-05-23-iloveppt-agent-design.md` |
| 5 阶段主流程(Stage A-E) | `skills/pptx-deck/workflow.md` |
| markdown schema(outline.md + content.md)+ 11 layout 字段 | `skills/pptx-deck/content-writing.md` |
| 金字塔原理 5 件套 + 自检表 | `skills/pptx-deck/content-writing.md` |
| 图层规划 4 类决策表 | `skills/pptx-deck/diagram-planning.md` |
| 视觉自检 17 项 checklist + fix 循环 | `skills/pptx-deck/visual-qa.md` |
| 模板提取(主色 + 字体) | `skills/pptx-deck/template-extract.md` |
| draw.io / Mermaid / matplotlib 出图细节 | `skills/diagram/SKILL.md` |
| matplotlib 风格 SSOT | `skills/diagram/matplotlib_rc.py` + `skills/diagram/matplotlib.md` |
| 底层 .pptx 读写 + footer/source helper | `skills/pptx/SKILL.md` + `skills/pptx/helpers.py` |
| 12-col grid 原语 | `skills/pptx/layout.py: grid_columns()` |
| 设计 token(SSOT 源头) | `skills/pptx/helpers.py` |
| 仓库架构与代码约定 | `CLAUDE.md`(根目录) |
| 用户操作手册(v3 流程) | `docs/MANUAL.zh.md` |

---

## 10. v2 → v3 变迁说明

如果你熟悉 v2 设计,这是关键变化:

### 架构层

| | v2 | v3 |
|---|---|---|
| Agent 数量 | 1(端到端) | **3**(brainstorm / author / iloveppt builder) |
| 智能放哪 | 全在 agent(Phase 1 + Phase 2) | 拆 3 个 agent;主线程退化 thin dispatcher |
| 主线程角色 | 用户对接 + trigger 派发 | 纯 router(不持有 PPT 业务逻辑) |
| 用户入口 | 直接 `@agent-iloveppt` | "做 PPT"(主线程自动派发 iloveppt-brainstorm) |
| 多轮对话怎么实现 | ❌ subagent 单次硬塞 | **多次派发 + state file**(每 agent 有 .iloveppt_*_state.json) |
| Checkpoint 数 | 1(outline yaml 审) | 2(outline.md 审 + content.md 审) |
| 接缝介质 | `deck_plan.json` | `content.md` + `deck_plan.json` 两层 |
| 素材摄入 | 无 | brainstorm Stage B 显式对话收集 |
| 多版本管理 | 无 | `deck_v{N}_*.md` 显式 |

### 复用 v2 资产

下列 v2 资产**完全保留,不动**:
- `helpers.py` 设计 token / footer / source_citation
- `tech_blue.py` 11 个 make_* layout 函数
- `build.py` 接收 deck_plan.json 出 .pptx(接口完全不变)
- `matplotlib_rc.py` 数据图 SSOT
- `layout.py` grid_columns + 几何原语
- `visual-qa.md` 17 项 checklist
- 字号 / 色 / 字段对标 BCG 的全套规范

### 废弃 v2 字段

下列 v2 schema 字段不再使用:
- agent Phase 1 输出的 `top_recommendation` / `scqa` / `mece_check_passed` / `pyramid_check_passed` / `bypass_pyramid` 字段
  → 改成 markdown frontmatter + 自检 checkbox 列表(用户可读)
- `ghost_deck_test_passed` 独立字段
  → 合并进 Pyramid 自检 7 项的第 ⑤ 项

### 迁移路径

v2 现有 deck 不需迁移——`build.py` 接口不变,旧 `deck_plan.json` 仍能跑。
新 deck 默认走 v3 流程(主线程 brainstorming 入口)。
v2 `brief.yaml` 仍可作为主线程 Stage A 的输入(主线程会读 yaml 然后正常进入 Stage C 跳过 brainstorming)。

---

*文档版本:**3.1** · 2026-05-23 决策 1 订正:3 agent 拆分 + thin dispatcher · 替代 v2 端到端流程*
