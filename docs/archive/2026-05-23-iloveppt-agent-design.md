# iLovePPT Agent 设计文档

> 📜 **设计史档**(2026-05-23) · 本文记录从 skill 库到 Claude Code agent 的拆分 rationale。
> 现状协议见 [`.claude/pipeline-protocol.md`](../../../.claude/pipeline-protocol.md);现状工作原理见 [`docs/agent-internals.zh.md`](../../agent-internals.zh.md)。

**日期**:2026-05-23
**动因**:把 iLovePPT 做成真正的 **Claude Code agent**(独立上下文、可显式派发、自主跑完循环),并加一个**大纲 checkpoint** 减少"理解跑偏白做一整份"的风险。

---

## 1. 目标

把 iLovePPT 从 skill 库改造成 Claude Code 项目内 agent。**最小改动**:加一个 agent 定义文件 + 重定向入口文档;build.py / 主题 / 几何 / 文档主体一行不动。agent 在自己的隔离上下文里跑完 brief → 大纲(checkpoint)→ 拓写 → build → QA → 交付。

非目标:不做插件分发(后续可加),不重写 build.py,不动 #3(内容自适应布局,另议)。

---

## 2. 架构

```
.claude/agents/iloveppt.md   ★新增——agent 定义(orchestrator)
skills/pptx-deck/             保留作为 agent 参考库
  ├─ build.py / themes/ / helpers / layout / evals  ← 完全不动
  └─ workflow.md / content-writing.md /              ← agent 按需读
     diagram-planning.md / visual-qa.md /
     template-extract.md
skills/pptx/  skills/diagram/  保留——既是 agent 的参考库,也仍可独立用
```

**agent = orchestrator,取代"主线程 Claude 读 SKILL.md 编排"。**
- agent 在独立上下文里:读文档 → 写 deck_plan.json → 跑 build.py → 看渲染 PNG → QA 循环 → 交付
- 现有 3 个 skill 不消亡,继续作为"agent 的参考库 + 可独立使用的 skill"两种形态共存(Claude Code 原生支持 agent + skill 共存)

---

## 3. agent 定义

文件:`.claude/agents/iloveppt.md`

### frontmatter

| 字段 | 值 |
|---|---|
| `name` | `iloveppt` |
| `description` | 触发词覆盖:做 PPT / 帮我写 PPT / 路演 deck / 汇报 / 提案 / brief.yaml / 参考 .pptx 模板 等。措辞写成 Claude 能自动委派的形式(含"Use proactively when..." 之类提示) |
| `tools` | `Bash, Read, Write, Edit, Glob, Grep, Skill`(跑 build.py / 写 deck_plan.json / 读渲染 PNG / 调 diagram skill) |
| `model` | `opus`——视觉 QA + 内容判断密集,需判断力 |
| `color` | 任选(例 `blue`) |

**不用 `skills:` 预加载字段。** 预加载会把多个 md 文档全灌进启动上下文。agent 按步骤现读,保持启动精简。

### system prompt 正文(描述要点,具体措辞在实施阶段定)

- **persona**:"你是 iLovePPT,端到端 PPT 生成 agent"。
- **运行模式识别**:派发入参里若无"已批准大纲",跑 Phase 1;若有,跑 Phase 2(见 §4)。
- **Phase 1 步骤**:读 workflow.md、content-writing.md 的「deck 级论证结构」、diagram-planning.md;**按麦肯锡金字塔原理 5 件套**(单一顶端论点 / SCQA / 答案在前 / 横向 MECE / 纵向疑问回答链)**设计大纲**,跑 Pyramid 自检表 7 项;规划图层;**输出大纲 + 图层计划 + 顶端论点 + SCQA + Pyramid 自检结果 + 提议页数,等用户批准**。任一自检项不过 → 列入 `missing_fields`,不交付。
- **Phase 2 步骤**:按大纲生成图(diagram skill / drawio / mmdc)→ 逐页拓写 → 写 deck_plan.json → 跑 `python3 skills/pptx-deck/build.py deck_plan.json` → 视觉自检循环(每页按 `evals/rubric.md` 的 Design 维 + `visual-qa.md` 12 项打分,有 fail 就改 deck_plan.json 重跑 build.py)→ **至多 3 轮**,仍不过的页加入 review-needed → 返回最终 .pptx 路径 + review-needed 清单。
- **交付格式**:Phase 1 返回 = 大纲 + 图层计划;Phase 2 返回 = .pptx 路径 + review-needed 清单 + 各页 QA 评分摘要。
- **anti-prompt**:不跳过视觉 QA;不在 QA 失败 ≥ 3 次仍硬重试;不内嵌 LLM API 调用(build.py 仍是纯机械);不复制用户模板内容(只提取主色 + 字体)。

---

## 4. 运行流程(带 outline checkpoint)

Claude Code 的 subagent 是隔离上下文、单次派发跑完返回。两阶段 = 两次派发,中间由用户(经主线程 Claude 中转)做闸口。

```
用户:"做一份 X 的 PPT" / @agent-iloveppt
   │
   ▼ 主线程 Claude 派发 agent(Phase 1)
[agent 实例 #1,隔离上下文]
   读文档 → 设计 outline + diagram_plan + 页数预估
   返回:outline + diagram_plan
   ▼
主线程 Claude 把 outline 展示给用户,征求批准
   │ 用户:批准 / 改 / 否
   ▼ 主线程 Claude 派发 agent(Phase 2,入参含已批准 outline)
[agent 实例 #2,隔离上下文]
   生成图 → 拓写 → 写 deck_plan.json → build.py → 视觉 QA 循环(≤ 3 轮)
   返回:.pptx 路径 + review-needed 清单
   ▼
用户:拿走 .pptx
```

**agent 自己负责区分两个 Phase**(看派发入参里有没有"已批准的 outline" 结构);主线程 Claude 负责"把 Phase 1 输出展示、收用户决定、再派 Phase 2"——这步通常由用户在主线程里几句话完成,不需要额外脚手架。

### Phase 1 → Phase 2 之间传什么

Phase 1 返回(也即 Phase 2 派发的输入)需含下列结构,**具体格式(markdown / JSON)由实施阶段定**,但内容必须覆盖:

- `theme`(`"tech_blue"` 或 `.pptx` 路径)、`output`(目标 .pptx 路径)
- **金字塔原理 5 件套字段**(`bypass_pyramid: false` 时全部必填):
  - `top_recommendation`:单一顶端论点(完整推荐句,动宾 + 边界)
  - `scqa: {situation, complication, question, answer}`:4 字段非空,`answer == top_recommendation`
  - `mece_check_passed: true`:章节横向 MECE 自检通过(3-5 节,两两不重叠)
  - `pyramid_check_passed: true`:Pyramid 自检表 7 项全过
  - `bypass_pyramid: false`:仅 `structure_mode in {data_report, tutorial, catalog}` 可设 true
- `sections[]`:每节 `{标题, action_title, 意图, 建议 layout, 是否配图}`(action_title 是顶端论点的"为什么/怎么做/是什么"回答)
- `diagram_plan[]`:每张图 `{所属节, diagram_type(arch/flow/chart/relation), tool, 简述}`
- `target_page_count`、`audience`、其他 brief 字段
- `missing_fields[]`:Pyramid 自检不过项或 brief 缺字段,非空则用户应先补

### 关键约束

- subagent **不能再派 subagent**——agent 内部不用嵌套派发;diagram 工具用 `Skill` 或 `Bash` 直接调。
- subagent 上下文有限,长 deck(20+ 页)的视觉 QA 阶段读图量大——按 batch 读、读完即弃,避免塞满。
- subagent 自带 context compaction(~95% 触发),作兜底。

---

## 5. 文件级改动

| 文件 | 改动 |
|---|---|
| `.claude/agents/iloveppt.md` | **新增**(agent 定义,按 §3) |
| `skills/pptx-deck/SKILL.md` | 重写入口段:做 deck 时通过 `@agent-iloveppt` 派发(触发关键词搬到 agent 的 `description`),pptx-deck 本身降级为 agent 的工具 + 知识库(build.py + 参考文档);用户若不用 agent,主线程 Claude 也能照本 SKILL.md 走 skill-mode |
| `skills/pptx-deck/workflow.md` | 微调:仍是 workflow SSOT(描述 Claude 该怎么干这件事);消费者从"主线程 Claude"扩展为"agent 或主线程 Claude"。加一句说明:agent 模式有大纲 checkpoint。 |
| `README.md` | 主入口改为 agent;skill-mode 列为备用 |
| `USAGE.zh.md` | 同上;加"如何 @ agent / 如何让别的项目用上"段(目前是手动拷 `.claude/agents/iloveppt.md`,后续可考虑插件) |
| `CLAUDE.md` | 「架构」段加一节描述 agent 层 |
| `pptx/SKILL.md` / `diagram/SKILL.md` | **不动**(继续独立可用) |
| `content-writing.md` / `visual-qa.md` / `diagram-planning.md` / `template-extract.md` / `evals/` / build.py / helpers / layout / themes | **不动** |

总改动:1 个新文件 + 4-5 个文档轻改;0 行 Python 代码。

---

## 6. 验证

- **手动 e2e**:在本仓库(或目标项目链接到的 `.claude/agents/`)调用 `@agent-iloveppt`,给一个简单 brief。验证:
  - Phase 1 返回大纲 + 图层计划,内容合理
  - 用户批准后 Phase 2 跑完,产出 .pptx
  - review-needed 清单合理(或为空)
- **现有 eval 集照常工作**——`bash evals/run_eval.sh` 测的是 build.py 代码回归,与 agent 层无关,继续生效。
- **不做**:agent 的自动化测试。agent 跑起来需要 Claude Code runtime,自动化代价高;手动 smoke 测够。

---

## 7. 显式不做(YAGNI)

- ❌ 打成插件分发(后续可加;现在 `.claude/agents/` 项目内即可)
- ❌ 完全自主无 checkpoint(用户明确要 checkpoint)
- ❌ 多 agent 编排(subagent 不能再派 subagent;一个 orchestrator 足够)
- ❌ 持久化 memory(暂不用 `memory:` 字段;每次派发干净起手)
- ❌ #3 内容自适应布局(独立功能,后续单独 brainstorm)
- ❌ 改 build.py 加 LLM 调用——纯机械边界是 v2 的核心决定,保持

---

## 8. 已知限制 / 风险

- **agent system prompt 的具体措辞**没在本 spec 中钉死——属实施细节,实施阶段拟稿后跑通 e2e 即调即定。
- **两阶段派发的 UX**:Phase 1 → Phase 2 之间靠用户(经主线程 Claude)中转。实际用起来如果觉得"两次派发"太 ceremonial,可在 agent 系统提示里加"如果用户在派发时直接说『跳过 checkpoint』就一路跑完",作为 escape hatch。本 spec 默认不加,先用最干净的模型。
- **长 deck 的 context 风险**:20+ 页时视觉 QA 阶段读图量大,可能撞到 agent context 上限。先观察实际表现;若真撞,Phase 2 内部分批 read+discard 是兜底。

---

## 9. 与 v2 设计的关系

本 spec 不推翻 [v2 设计](2026-05-22-iloveppt-v2-design.md),只**叠加一层**。v2 确立的「机械 build.py + Claude 智能驱动」分离照旧成立——agent 就是"Claude 智能驱动"那一侧的更具像化的实现:把"主线程 Claude 读文档 + 跑流程"换成"独立 agent 跑相同的流程"。skill 库继续作为 agent 的知识库存在。
