# pptx-deck 主流程(6 agent + 1 旁路 + markdown-first)

端到端:用户一句话 → 主线程 dispatcher 调度 6 agent + 1 旁路 → 用户审 markdown → 交付 .pptx。
**"智能"全部放进 6 个 agent**(brainstorm / author / critic / builder / designer / audience + template-extractor 旁路),主线程退化为 router。

权威活协议见 [`${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md`](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md);markdown-first 接缝设计 rationale 见 [设计史档](${CLAUDE_PROJECT_DIR}/docs/archive/2026-05-23-iloveppt-v3-markdown-first.md)。

## 5 阶段 / 6 agent + 1 旁路 全景

```
[主线程 = pure dispatcher]              [6 agents · 独立上下文]
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

主线程**不做 PPT 业务逻辑**。它只是个状态机,支持 5 个 next_action:

```
loop:
  agent_return = dispatch(current_agent, current_args)
  switch agent_return.next_action:
    case "ask_user":
      show(agent_return.message_to_user + questions)
      user_reply = wait_for_user()
      current_args["user_response"] = user_reply
      # 同一个 agent,带新答案再派发
    case "dispatch_brainstorm" | "dispatch_template_extractor" |
         "dispatch_author" | "dispatch_builder":
      current_agent = agent_return.dispatch.agent
      current_args = agent_return.dispatch.args
    case "done":
      show(agent_return.pptx_path + auto_md_edits + review_needed)
      break
    case "error":
      show(agent_return.error + message)
      break
```

主线程**不存任何中间状态**——agent 自己用 `<working_dir>/brainstorm/state.json` / `author/state.json` 跨派发记忆。

**典型派发序列**(无模板):
```
brainstorm × N → author × M → builder × 1 → done
```

**典型派发序列**(有模板,新模板首次用):
```
brainstorm(收到模板路径)
  → template_extractor × 1(Stage T 一次性提取)
  → brainstorm(继续收齐字段)
  → author × M → builder × 1 → done
```

**典型派发序列**(有模板,模板已 enriched 过):
```
brainstorm(直接用 enriched yaml)× N → author × M → builder × 1 → done
```

主线程**第一次入口**(用户扔一句话时):

```
派发 iloveppt-brainstorm,initial_request="<用户的一句话>",
                          working_dir=<deck 工作目录,主线程帮选 or 用户指定>
```

之后跟着 agent 返回的 `next_action` 走。

## Stage A · 需求挖掘(iloveppt-brainstorm)

详见 [iloveppt-brainstorm agent](${CLAUDE_PROJECT_DIR}/.claude/agents/iloveppt-brainstorm.md)。

收齐字段:audience / duration_min / top_recommendation / theme / output。
对话中识别素材需求 → prompt 用户提供。

## Stage B · 素材摄入(iloveppt-brainstorm 继续)

agent 在对话中识别用户素材 → 引导提供 → `Read` 校验 → 落 `_assets/{raw,refs}/` → 加入 inventory。

## Stage C · 内容规划(iloveppt-author Stage C)

详见 [iloveppt-author agent](${CLAUDE_PROJECT_DIR}/.claude/agents/iloveppt-author.md)。

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
- 严守 13 layout 字数规则
- 关键 stat 加 `> 数据:Source: ...` 引文

产出 `deck_v1_content.md` → ask_user 审。

## Stage E · 终稿构建(iloveppt builder)

详见 [iloveppt agent](${CLAUDE_PROJECT_DIR}/.claude/agents/iloveppt.md)。

content 批准后,author 返回 `next_action: dispatch_builder`,主线程派发:

```
iloveppt
content_md_path: <working_dir>/author/deck_v1_content.md
output_pptx: <working_dir>/builder/deck_v1.pptx
theme: tech_blue
footer_meta: { classification, project, version }
```

builder 5 步:Pyramid 自检 → md→JSON → build.py → 视觉 QA(≤ 3 轮,自动改 md 重 build)→ 返回。

主线程展示成品 + `auto_md_edits` + `review_needed`。

## 接缝:为什么是 markdown 而不是 yaml

| 维度 | 选 markdown 而非 yaml 的原因 |
|---|---|
| 用户可读性 | markdown 是自然文档,可直接阅读;yaml 是结构化数据,需先理解字段 |
| 编辑工具 | 任何 markdown editor / Obsidian / VS Code 都能编辑;yaml 要小心格式 |
| 版本对比 | markdown git diff 逐段易读;yaml 嵌套字段 diff 难读 |
| 多人协作 | markdown merge 相对友好;yaml 容易冲突 |
| 用户能直接审什么 | 完整文案(2000-5000 字),不是只看框架(120 字) |

## build.py 的能力边界

build.py 是纯机械:`deck_plan.json → .pptx + PNG`,不调 LLM。`deck_plan.json` 由 agent 从 markdown 生成。

CLI:`python3 build.py deck_plan.json [--no-render]`

## 13 种 layout

cover / toc / section_divider / single_focus / compare / compare_pk / matrix_2x2 / cards / bullet_list / table / pic_text / summary / closing。字段约束与 markdown 表达形式见 [content-writing.md](content-writing.md)。

## Anti-prompt

- 主线程不要把 PPT 业务逻辑写进自己的回复 —— 全部交给 6 agent
- 主线程不要跳过 brainstorm 直接派 iloveppt builder —— builder 会 reject(缺 content.md)
- 主线程不要在 dispatcher 角色之外做事(主线程**只**做 router + 转发 message)
- 主线程不要混淆 6 个 agent 的角色;按 `next_action` 严格派发(参考 [`${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md`](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md) §12 派发表)
- iloveppt-brainstorm 不要做大纲设计 —— 那是 author 的事
- iloveppt-author 不要做 brief 收集 / 视觉构建 —— 各有边界
- iloveppt 不要做 brief 解析 / 大纲设计 / 文案拓写 —— 只做 build
- 任何 agent 不要忽略 state file —— 每次派发必须先 Read,最后必须 Write
- 配图必须在 Stage D 写 content.md 之前由 author 生成好
