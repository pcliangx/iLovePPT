# Hybrid Migration Postmortem

| 项 | 值 |
|---|---|
| Date | 2026-05-25 |
| Plan | `docs/archive/2026-05-25-hybrid-migration-plan.md` |
| Audit baseline | `docs/agent-team-evaluation-checklist.zh.md` |
| pre tag | `pre-hybrid-migration`(commit `c707d81`) |
| post tag | `post-hybrid-migration`(本 commit) |
| Branch | `feat/hybrid-migration` |
| Total commits | 12(协议 1 + agent 5 + CLAUDE.md 1 + hook 1 + 文档 3 + 此 postmortem 1) |
| Phase 0 baseline | **SKIPPED**(用户决策:跳过严格 baseline,Phase 4 改为端到端跑通验证) |
| Phase 4 baseline | `evals/agents/baseline/01-exec-decision-post-hybrid/`(108KB,12 文本报告) |

---

## 1. 迁移成果

### 1.1 协议层

| 维度 | 旧(team) | 新(hybrid) |
|---|---|---|
| 行数 | 700+ | 387(`.claude/pipeline-protocol.md`) |
| 章节 | 0-13 散 | §0-§6 集中 |
| 删 | idle 协议 / SendMessage / 窗口生命周期 / 邮局规则 / "你的 transcript 对 team-lead 不可见"(对其他 5 agent) | — |
| 加 | §0 二段论 / §4 统一 yaml schema(Phase A SendMessage / Phase B Task return 共用) / §3.3 Gate 集中 / §6 派发禁区(继承旧 §12) | — |
| 旧文件 | 重命名为 `.claude/pipeline-protocol.team-legacy.md.bak`(已删除,见 1.5) | — |

### 1.2 Agent 改造

| agent | 改 | 调用方式 |
|---|---|---|
| `iloveppt-brainstorm` | **0 行** | TeamCreate(team) — 保留 |
| `iloveppt-template-extractor` | 删 SendMessage / 加 Output format / yaml 改 §4 + 失败 case status=error | Task |
| `iloveppt-critic` | 同上 + 重写 Step 5 三种 verdict yaml | Task |
| `iloveppt-audience` | 同上 + yaml 加 delivered / single triage / multi-triage 三种 case | Task |
| `iloveppt` | 同上 + yaml 重写 dispatch_audience / hard_stop 两种 case,保留 evidence 字段 | Task |
| `iloveppt-author` | 同上 + 多 yaml block 全部对齐(Stage C/D × ask_user_for_*_approval / dispatch_critic / ask_user) | Task |

总 diff:5 agent + 1030 insertions / 643 deletions。

### 1.3 主线程入口

| 文件 | 改动 |
|---|---|
| `CLAUDE.md` | "Agent 流水线" 节加 Hybrid 二段论说明 + TeamCreate vs Task 分列;"主线程派发规则" 改为 TeamCreate(brainstorm) + Task others |
| `.claude/settings.json` | Stop hook 加 5 字段(tokens_in/out/cached/duration_ms/tool_uses),用 `${VAR:-na}` 容错 |

### 1.4 文档同步

| 文件 | 改动 |
|---|---|
| `docs/agent-internals.zh.md` | 加 Hybrid 架构 callout + §1.1 dispatch list 加 Phase A/B 分列 |
| `docs/MANUAL.zh.md` | §1 加 Hybrid 用户层简述 + 术语表 "主线程 Claude" 补 Phase A/B 行为 |
| `README.md` | agent-internals link 条目改 "Hybrid:1 brainstorm team + 5 subagent + 1 旁路 subagent" |

### 1.5 临时备份清理

- `pipeline-protocol.team-legacy.md.bak`:Phase 4 验证通过后删除(本 commit 含)

---

## 2. Phase 4 实测结果(fixture 01-exec-decision)

### 2.1 端到端跑通

| 阶段 | 结果 |
|---|---|
| Phase A TeamCreate brainstorm + 多轮 ask_user | ✓ |
| brainstorm 收齐 6 必填字段 + brief.md gate | ✓ |
| Phase A → Phase B 切换(shutdown_request → approved)| ✓ |
| Task author Stage C → outline(5 章 MECE)| ✓ |
| Task critic Stage C → pass_with_notes(2 med + 2 low)| ✓ |
| Task author Stage D → content(15 页 + 2 chart)| ✓ |
| Task critic Stage D r1 → needs_revision(1 high + B7 fail)| ✓(critic 真敢狠) |
| Task author Stage D rework → must-fix 修复 | ✓ |
| Task critic Stage D r2 → pass_with_notes | ✓ |
| Task iloveppt Step 0-4 → .pptx 595KB + 14 页 render | ✓ |
| Task audience(executive)→ overall 6.4 + triage 完整 | ✓ |

### 2.2 端到端不通过

- audience overall_score 6.4 < 9 → 按 fixture 设计本应进修复环路 1-2 轮 polish 到 ≥9。**用户决策跳过修复环路**,因 hybrid 协议验证目标已达,quality polish 不是本 Phase 范围。

---

## 3. 关键 findings(Hybrid 在实际 Claude Code 环境暴露的问题)

> **这是本 postmortem 的核心**。所有 findings 都来自 Phase 4 实测,不是事前推断。

### F1 · brainstorm SendMessage 漏发(高频)

**现象**:Phase A 每轮 brainstorm 处理用户回信后,**经常只发 idle_notification 不发正经 SendMessage**(报 next_action)。主线程 ping 一次才会补发。

**频次**:Phase A 跑了 4 轮,有 **3 轮需要主线程 ping** 才拿到正经回信。

**影响**:
- 拖慢 Phase A 整体时长(每轮多一次 SendMessage 来回)
- 主线程必须 fallback 读 state.json 才能知道 brainstorm 实际进度(违反 §2.4 "state 只是 brainstorm 内部恢复用,不是主线程 polling 接口")
- 增加 brainstorm token 消耗(被 ping 后重跑一次)

**根因推测**:Claude Code Agent 工具的 idle 机制 = 处理完入站消息后 turn 结束就 idle,**不强制要求 idle 前出口动作**。我们 prompt §2.3 写了"idle 前必须 SendMessage"但运行时不强制。

**建议修复**:
1. **短期**:protocol §2.3 改为容错描述"brainstorm 多数情况会 SendMessage,如未收到主线程需要 ping 或 fallback 读 state.json"(实事求是)
2. **中期**:brainstorm prompt 加强 "SendMessage 是 turn 最后一步,不允许 idle 前跳过"(可能仍不 100% 生效)
3. **长期**:Claude Code 暴露 "idle hook" 允许 hook 强制 idle 前必须 SendMessage(非项目可控)

### F2 · brainstorm SendMessage 内容与 state.json 不一致

**现象**:有 2 次 brainstorm 发的 SendMessage 跟 state.json **新状态不符**:
- Round 2 state.json 已更新 collected 含 theme/mode/output,但 SendMessage 内容**重发了 Round 2 之前的 ask_user**(还在问 theme/mode/output)
- Round 3 brief_approved=true,但 SendMessage 内容**重发了 brief_gate ask_user**(还在问"OK 批准吗")

**影响**:
- 主线程被 SendMessage 误导以为状态没推进,会发多余 ping
- 如果主线程完全信任 SendMessage 不读 state.json,会陷入 deadlock

**根因推测**:brainstorm prompt 跨 turn 状态恢复 + return yaml 生成的逻辑分离,有 race。或者 brainstorm 重新组装 ask_user 时用了旧 buffer 而非最新 state。

**建议修复**:
1. 主线程 SOP:**收到 brainstorm SendMessage 时,同时 Read state.json 交叉验证**。state.json 是 SSOT
2. brainstorm prompt:强调 "SendMessage 内容必须实时反映本 turn state.json,不允许用上 turn 缓存"

### F3 · runtime.log hook 不工作(Stop hook env vars 未暴露)

**现象**:Phase 4 全程跑下来,`.claude/runtime.log` 新增的所有行**仍全部** `agent=main, session=unknown`,新加的 5 字段(tokens_in/out/cached/duration_ms/tool_uses)**全部 = na**。

**影响**:
- audit clipboard G1/G2/D2/D4/H5 GAP 修复**失败**(原指望 Hybrid + 增强 hook 解锁 telemetry)
- 无法事后统计 per-agent token / latency / tool_uses 占比
- 无法做 "subagent vs team 模式哪个 token 更省" 的对比分析

**根因确诊**:**Claude Code 当前不向 Stop hook env 暴露 `CLAUDE_AGENT_NAME` / `CLAUDE_TOKEN_INPUT` 等环境变量**。Stop hook 只在 main session idle 时触发,subagent 完成不触发 hook;即使触发,env 也是 main 的,不是 subagent 的。

**建议修复**:
1. **短期**:接受 limitation,在 postmortem 明确记录"Hybrid 架构 telemetry GAP 未解决,根因在 Claude Code 平台层"
2. **中期**:在 subagent prompt 内加 "返回时把 token usage / duration 写进 yaml"(从 Anthropic SDK 拿不到自报数据,准确度有限)
3. **长期**:等 Claude Code 平台支持 subagent 完成事件 hook + 完整 env vars 注入(非项目可控,需要平台 issue)

### F4 · Phase B agent yaml schema 偏差(6 个 agent 各有不同)

**现象**:Phase B 5 个 subagent 的 return yaml 都跟 plan §4 schema 有不同程度偏差。

| agent | 偏差 |
|---|---|
| `iloveppt-author` | `status: ask_user_for_outline_approval`(应该 `status: ok`,把 next_action 值塞 status) |
| `iloveppt-critic` r1 | `status: ok` ✓;但 `next_action: pass_with_notes` ✓ |
| `iloveppt-critic` r2 + r1(D) | `status: complete` / `next_action: report_complete`(都不在 §4 枚举) |
| `iloveppt-critic` | `issues:` 用 dict `{high: 0, med: 2, ...}` 而非 list of `{severity, section, description, suggestion}` |
| `iloveppt-critic` | `artifacts:` 用 `report_path: <abs>` 而非 list of `{path, kind}` |
| `iloveppt` | yaml block **不在 return 最后**(放在中间或被叙述包围) |
| `iloveppt-author` rework | **没有 yaml block**(纯叙述结尾) |
| `iloveppt-audience` | `triage:` 用 dict `{needs_author_rewrite: {pages: [], reason: ""}}` 而非 enum + 补充字段 |
| `iloveppt-audience` | `next_action: needs_visual_redo` 但 needs_author_rewrite 也有页(本应 next_action=needs_author_rewrite 按优先级) |
| `iloveppt-template-extractor` | (未在 Phase 4 跑,无数据) |

**影响**:
- 主线程读 yaml 时**主体字段(agent / verdict / pptx_path 等)能 parse**,但**细节字段(issues / per_page_scores)需要兼容多种格式**
- 如果主线程严格按 §4 schema parse,会失败 / 丢字段
- audience triage 多类时未按优先级 → 主线程派下家时容易派错(派 visual_redo 但其实有 needs_author_rewrite 页)

**根因推测**:agent prompt 是文档示意,LLM 实际产出 yaml 时偶尔"创造性"用其他字段名 / 结构。没有 schema 强制校验。

**建议修复**(按 ROI):
1. **立刻**:protocol §4 schema 加 "**严格枚举**" 措辞(`status` ∈ {ok, error};`next_action` ∈ {...};不允许其他值)
2. **agent prompt**:每个 agent 加 1 个完整 yaml 示例放在 prompt 顶部 "Output format" 段(已加,但需要再加"反例"示意"不要写 status: complete / done / ask_user_*")
3. **主线程**:加 yaml 容错 parser,接受常见变体(complete→ok, report_complete→infer next_action, dict issues → list)
4. **长期**:用 structured output(Anthropic SDK 支持 JSON schema 强制),把 yaml block 换成 JSON + schema 校验

### F5 · author yaml block 缺失

**现象**:author Stage D rework return 是叙述描述,**完全没 yaml block**。

**根因**:rework prompt 没明确说"return 必须含 yaml",author 当成"完成报告"任务返回叙述。

**影响**:主线程要从叙述里推断状态(实际推断成功,但容错风险高)。

**建议修复**:Phase 2 改 author prompt 时 "Output format" 段加一句 "**任何时候 return 都必须含 yaml block,包括 rework / 出错 / 中途询问**"。

### F6 · iloveppt yaml block 位置

**现象**:iloveppt return 是 ```yaml block 不在最后`,被叙述围绕(末尾还有"next_action: dispatch_audience" 总结句)。

**影响**:主线程 parse 时如果按"最后一段 yaml block"严格找,会找到正确 block;但如果叙述里嵌入了 yaml-like text,会被误 parse。

**建议修复**:protocol §3.1 + 各 agent prompt "Output format" 段:**强调 "yaml block **必须**是 return 的 closing element,后面不能跟任何叙述"**。

---

## 4. Baseline 对比

### 4.1 没有 pre-hybrid baseline

按 plan Phase 0 SKIPPED 决策,**没有 pre 数据可对比**。可对比项:

| 项 | pre(推断) | post(实测) |
|---|---|---|
| 协议行数 | 700+ | 387 ✓ 瘦身 -45% |
| Stop hook 字段 | 3(time/agent/session) | 8(+ tokens × 3 + duration + tool_uses) ✓ 字段加但全 na |
| runtime.log 实际可用 | NO(team 模式)| **NO**(hybrid 仍 GAP,见 F3) |
| brainstorm 调用方式 | TeamCreate | TeamCreate ✓ 不变 |
| 其他 5 agent 调用方式 | TeamCreate + SendMessage | Task ✓ |
| 主线程协议复杂度(主观)| 高(邮局 + idle + 窗口生命周期 + SendMessage)| 中(Phase A 还有邮局;Phase B 减半)|

### 4.2 post baseline

完整产物 `evals/agents/baseline/01-exec-decision-post-hybrid/`(12 文本报告,108KB,见 META.md)。

---

## 5. Audit GAP 修复情况(对照 `docs/agent-team-evaluation-checklist.zh.md`)

| Audit GAP | Hybrid 后状态 | 备注 |
|---|---|---|
| B4 并行而非串行 | 仍 GAP | Hybrid 不涉及并行,留给下个 spec |
| B6 Orchestrator SPOF | 部分缓解 | Phase B Task 主线程直接拿 return,不卡;Phase A 仍有 idle 黑洞(F1) |
| C5 Role overlap | 仍 PASS | 边界不变 |
| D1 Token 预算 | 仍 GAP | F3:hook env vars 未暴露 |
| D2 Tool call 监控 | 仍 GAP | 同 F3 |
| D3 Tool description 优化 | 仍 UNKNOWN | 无数据 |
| D4 P95 latency | 仍 GAP | 同 F3 |
| D5 简单任务回退 | 部分缓解 | trivial rebuild 仍 §6.2 保留 |
| E1 Resume 而非 Restart | 仍 GAP | 无 durable execution |
| E4 失败模式分类(MAST)| 仍 GAP | critic prompt 未加 MAST 5 项,留给下个 spec |
| E5 单 worker 失败不卡全队 | 改善 | Task 返回 status=error 主线程直接处理 |
| F2 Eval 集 ≥ 20 | 仍 PARTIAL | 13 个 fixture |
| F5 Lead 主动抽查 | 仍 PARTIAL | "邮局不当海关" 未变 |
| G1 全链路 trace | 仍 GAP | F3 |
| G2 OTel | 仍 GAP | F3 |
| G3 三粒度评估 | 仍 PARTIAL | 同上 |
| G5 Deterministic replay | 仍 GAP | 无 |
| G6 灰度部署 | 仍 GAP | 无 |
| H3 Context leakage | 部分缓解 | iloveppt + author 仍多职责,但 subagent context 隔离更强 |
| H5 Token blow-up 不可见 | 仍 GAP | F3 |
| L1 80/80(token usage)| 仍 GAP | F3 |
| L3 MAST 14 项覆盖率 | 仍 GAP | 未做 |

**汇总**:迁移**直接修复的 Audit GAP 数量 = 0**(原期望通过 hybrid + 增强 hook 解锁 telemetry,F3 表明平台层不支持)。

**间接收益**:
- 协议复杂度 -45%(700→387 行)
- Phase B 5 agent context 隔离更彻底(subagent 天然 fresh context)
- E5 单 worker 失败处理改善

---

## 6. 下一步(按发现的紧迫程度)

### 6.1 立刻(高紧迫,1-2 天)

1. **修 F4 + F5 + F6 yaml schema 偏差**:5 agent prompt "Output format" 段加 "**反例 + 严格枚举**" 示例,主线程加容错 parser
2. **修 F1**:protocol §2.3 改为实事求是描述 + 主线程 SOP:收到 brainstorm SendMessage 时 fallback Read state.json
3. **修 F2**:同上,主线程实现 state.json 交叉验证

### 6.2 中期(1 周内)

4. **F3 短期 mitigation**:在 5 个 subagent prompt 内自报 token / duration,写进 yaml(精度有限但聊胜于无)
5. **接 audit J 节优先级**:跑 5 个 agents fixture 填 `evals/agents/baseline/*.json` baseline 数字(现在有 1 个 post-hybrid baseline 可参考)
6. **接 audit B4 Layer 1**:iloveppt Step 4 / author 出图多 Bash 一条消息并行(零风险加速)

### 6.3 长期(1 个月+ / 平台层)

7. **F3 长期**:跟 Claude Code 团队反馈 Stop hook env vars 需求(F3 根因在平台层,非项目可控)
8. **F4 长期**:用 Anthropic SDK structured output / JSON schema 强制 yaml schema 校验(可能要 agent SDK 大改)
9. **audit B4 Layer 2**:章节并行拓写(需 F3 telemetry 数据做 A/B 验证)
10. **audit H3**:重审 author / iloveppt 多职责拆分(需新 spec)

---

## 7. 总结

- **协议简化达成**:700→387 行,team 模式专属基建删除
- **5 agent 转 subagent 达成**:Task 调用 + yaml return 流程跑通
- **Phase A → Phase B 切换达成**:TeamCreate + shutdown_request 路径有效
- **端到端跑通达成**:fixture 01-exec-decision 完整跑出 .pptx 595KB + 14 页 render
- **Telemetry 解锁失败**:F3 是关键 GAP,根因在 Claude Code 平台层
- **yaml schema 不严格**:F4-F6 暴露 6 类偏差,需主线程容错 + agent prompt 严格化

**这次迁移的真正价值不是修复 audit GAP,而是把"agent 流水线的实际行为"显性化** —— 我们现在知道 Hybrid 在 Claude Code 实际运行的 6 个 yaml 偏差 / SendMessage 不主动 / hook env 不暴露这些事,这些都是 future spec 的依据。
