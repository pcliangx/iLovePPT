# pptx-deck 主流程(v3:三 agent 流水线 + markdown-first)

端到端:用户一句话 → 主线程 dispatcher 调度 3 agent → 用户审 markdown → 交付 .pptx。
**v3 把"智能"全部放进 3 个 agent**,主线程退化为 router。

详细设计见 [v3 spec](../../docs/superpowers/specs/2026-05-23-iloveppt-v3-markdown-first.md)。

## 5 阶段 / 3 agent 全景

```
[主线程 = pure dispatcher]              [3 agents · 独立上下文]
────────────────────────                 ─────────────────────

用户一句话需求
  │
  ▼
派发 iloveppt-brainstorm   ◄────────►   Stage A 需求挖掘
  ↻ 多次派发 + state file               Stage B 素材摄入
  ◄────────────────────────  返回 next_action: dispatch_author + brief
  │
  ▼
派发 iloveppt-author(C)   ◄────────►   Stage C 内容规划
  ↻ 多次派发(出 outline / 改)         出 deck_v1_outline.md
  ◄────────────────────────  ask_user 审 outline
  │ 用户批准
  ▼
派发 iloveppt-author(D)   ◄────────►   Stage D 全文拓写
  ↻ 多次派发(出 content / 改 / 出图)  出 deck_v1_content.md + _assets/charts/*.png
  ◄────────────────────────  ask_user 审 content
  │ 用户批准
  ▼
派发 iloveppt(builder)    ◄────────►   Stage E 终稿构建
  单次派发(内含 ≤ 3 轮 QA)            Read content.md → Pyramid 自检 →
                                          md→JSON → build.py → 视觉 QA
  ◄────────────────────────  next_action: done + pptx_path + auto_md_edits
  │
  ▼
展示成品 + auto_md_edits 报告给用户
```

## 主线程 dispatcher 协议(关键)

主线程**不做 PPT 业务逻辑**。它只是个状态机:

```
loop:
  agent_return = dispatch(current_agent, current_args)
  switch agent_return.next_action:
    case "ask_user":
      show(agent_return.message_to_user + questions)
      user_reply = wait_for_user()
      current_args["user_response"] = user_reply
      # 同一个 agent,带新答案再派发
    case "dispatch_brainstorm" | "dispatch_author" | "dispatch_builder":
      current_agent = agent_return.dispatch.agent
      current_args = agent_return.dispatch.args
    case "done":
      show(agent_return.pptx_path + auto_md_edits + review_needed)
      break
    case "error":
      show(agent_return.error + message)
      break
```

主线程**不存任何中间状态**——agent 自己用 `<working_dir>/.iloveppt_dialog_state.json` / `.iloveppt_author_state.json` 跨派发记忆。

主线程**第一次入口**(用户扔一句话时):

```
派发 iloveppt-brainstorm,initial_request="<用户的一句话>",
                          working_dir=<deck 工作目录,主线程帮选 or 用户指定>
```

之后跟着 agent 返回的 `next_action` 走。

## Stage A · 需求挖掘(iloveppt-brainstorm)

详见 [iloveppt-brainstorm agent](../../.claude/agents/iloveppt-brainstorm.md)。

收齐字段:audience / duration_min / top_recommendation / theme / output。
对话中识别素材需求 → prompt 用户提供。

## Stage B · 素材摄入(iloveppt-brainstorm 继续)

agent 在对话中识别用户素材 → 引导提供 → `Read` 校验 → 落 `_assets/{raw,refs}/` → 加入 inventory。

## Stage C · 内容规划(iloveppt-author Stage C)

详见 [iloveppt-author agent](../../.claude/agents/iloveppt-author.md)。

按金字塔原理 5 件套设计 outline:

- ① 单一顶端论点(`top_recommendation`)
- ② SCQA 开场
- ③ 答案在前(BLUF)
- ④ 横向 MECE(3-5 章节)
- ⑤ 纵向疑问/回答链

加 ⑥ 字段完整性 + ⑦ action title ≤ 24 字 = **Pyramid 自检 7 项**。

产出 `deck_v1_outline.md`(schema 见 [content-writing.md](content-writing.md#deck_vnoutlinemd-schema))→ ask_user 审。

## Stage D · 全文拓写(iloveppt-author Stage D)

基于已批准 outline,author 拓写每节文案:

- 每节按 layout 选型规则(content-writing.md)
- 数据图先调 matplotlib_rc 出 PNG → `_assets/charts/`
- 严守 11 layout 字数规则
- 关键 stat 加 `> 数据:Source: ...` 引文

产出 `deck_v1_content.md` → ask_user 审。

## Stage E · 终稿构建(iloveppt builder)

详见 [iloveppt agent](../../.claude/agents/iloveppt.md)。

content 批准后,author 返回 `next_action: dispatch_builder`,主线程派发:

```
iloveppt
content_md_path: <working_dir>/deck_v1_content.md
output_pptx: <working_dir>/deck_v1.pptx
theme: tech_blue
footer_meta: { classification, project, version }
```

builder 5 步:Pyramid 自检 → md→JSON → build.py → 视觉 QA(≤ 3 轮,自动改 md 重 build)→ 返回。

主线程展示成品 + `auto_md_edits` + `review_needed`。

## 接缝:为什么是 markdown 而不是 yaml(v2 旧设计)

| 接缝介质 | v2 yaml | v3 markdown |
|---|---|---|
| 用户可读性 | 差(技术语言) | 强(自然文档) |
| 编辑工具 | 必须用文本编辑器谨慎改 | 任何 markdown editor / Obsidian / VS Code |
| 版本对比 | git diff 难读(嵌套字段) | git diff 易读(逐段) |
| 多人协作 | 容易冲突 | markdown merge 相对友好 |
| 用户能直接审什么 | 框架(120 字) | 完整文案(2000-5000 字) |
| 改 1 个字成本 | 整个 deck rebuild | 改 md → rebuild 仍要 3-5 min,但**用户已知道改什么** |

## build.py 的能力边界(不变)

build.py 仍是纯机械:`deck_plan.json → .pptx + PNG`。v3 没改 build.py 接口;只是输入的 `deck_plan.json` 由 agent 从 md 生成(v2 是 agent 从 brief 拓写)。

CLI:`python3 build.py deck_plan.json [--no-render]`

## 11 种 layout(不变)

cover / toc / section_divider / single_focus / compare / cards / bullet_list / table / pic_text / summary / closing。字段约束与 markdown 表达形式见 [content-writing.md](content-writing.md)。

## v2 → v3 主要差异速查

| 维度 | v2 | v3 |
|---|---|---|
| 用户入口 | `@agent-iloveppt 帮我做 X` | "帮我做 X"(主线程会自动派发 iloveppt-brainstorm) |
| Agent 数量 | 1(端到端) | **3**(brainstorm / author / iloveppt builder) |
| 谁做 brief 解析 | agent Phase 1 | iloveppt-brainstorm |
| 谁做大纲设计 | agent Phase 1 | iloveppt-author Stage C |
| 谁做文案拓写 | agent Phase 2 | iloveppt-author Stage D |
| 谁做构建 | agent Phase 2 | iloveppt(builder) |
| 用户审什么 | YAML outline | outline.md + content.md(2 个 checkpoint) |
| 主线程角色 | trigger 派发 | thin dispatcher(状态机 router) |
| 多轮对话怎么实现 | ❌ subagent 单次派发硬做 | **多次派发 + state file**(每次 agent Read state) |
| 主线程上下文 | 干净 | 干净(v3 把对话推给 agent,主线程不持有) |
| 接缝 | brief → agent → pptx | content.md → builder → pptx |
| 视觉修复 | agent 改 deck_plan.json | builder 改 content.md(用户最终源是 md) |

## Anti-prompt

- 主线程不要把 PPT 业务逻辑写进自己的回复 —— 全部交给 3 agent
- 主线程不要跳过 brainstorm 直接派 iloveppt builder —— builder 会 reject(缺 content.md)
- 主线程不要在 dispatcher 角色之外做事(主线程**只**做 router + 转发 message)
- 主线程不要混淆 3 个 agent 的角色;按 `next_action` 严格派发
- iloveppt-brainstorm 不要做大纲设计 —— 那是 author 的事
- iloveppt-author 不要做 brief 收集 / 视觉构建 —— 各有边界
- iloveppt 不要做 brief 解析 / 大纲设计 / 文案拓写 —— 只做 build
- 任何 agent 不要忽略 state file —— 每次派发必须先 Read,最后必须 Write
- 配图必须在 Stage D 写 content.md 之前由 author 生成好
