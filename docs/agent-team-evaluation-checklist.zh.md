# 评价 AI Agent Team「高效 × 稳定」的判定清单 v1

> 调研来源:Claude Code 官方文档(code.claude.com/docs) + Anthropic 工程博客 + 学术 benchmark(MAST / MultiAgentBench)+ 生产可观测性标准(OpenTelemetry GenAI)。
> 结构按**审计视角**组织 —— 每条都是 PASS / GAP 判定题,不是描述性最佳实践。
> 适用范围:任何 multi-agent / subagent 流水线;本仓库的具体应用对象是 iLovePPT 6-agent + 1 旁路。

---

## 0. 三个必背的母法则(先记住这三个,剩下都是推论)

| # | 法则 | 来源 |
|---|---|---|
| L1 | **80/80 定律**:80% 性能方差由 **token usage** 解释;80% 失败由 **interface ambiguity** 引起 | Anthropic Engineering;TheNewStack |
| L2 | **CLEAR 五维**:Cost / Latency / Efficacy / Assurance / Reliability —— 任何 agent team 都要在这五维上能打分,缺一维即 GAP | composio.dev |
| L3 | **MAST 三大类失败**:① specification(42%)② inter-agent misalignment(37%)③ verification(21%)—— 清单覆盖率不到 100% 不合格 | arxiv 2503.13657(UC Berkeley)|

---

## A. 角色定义(Specification, MAST 类 1)

- [ ] **A1 单一职责** — 每个 agent 是否只对应一个 domain(生成 / 校验 / transform / side-effect 必须分离)?
- [ ] **A2 显式契约** — 输入是否为 typed/serialized object(不是 free text)?输出是否过 schema 校验?
- [ ] **A3 description 可被 router 命中** — description 字段是否具体到能让主线程**自动**匹配(反例:"Expert reviewer";正例:"Security code reviewer for auth modules")?
- [ ] **A4 system prompt 五件套** — 是否齐备:objective + output format + tool guidance + task boundary + effort scaling 规则?(Anthropic 强制清单)
- [ ] **A5 tool 最小权限** — read-only agent 是否排除了 Edit/Write/Bash?写型 agent 是否排除了无关的网络/MCP?
- [ ] **A6 model 分层** — 是否 orchestrator 用强模型(Opus)+ worker 用弱模型(Sonnet/Haiku)?(Anthropic 实测此组合相对单 Opus **+90.2%**)

## B. 委派与协调(主线程 vs subagent 边界)

- [ ] **B1 主线程是协调者,不是执行者** — 主线程是否只做"分解 / 综合 / 抽查",不亲自跑 subagent 该跑的工作?
- [ ] **B2 Delegate 触发规则成文** — 何时 delegate / 何时主线程自己干,是否有写在 CLAUDE.md 的明确判定表(避免"凭感觉派发")?
- [ ] **B3 Context isolation 是刻意的** — 把 subagent 用于"隔离中间产物(搜索结果 / 长 trace),只把摘要返主线程"是否被显式使用?
- [ ] **B4 并行而非串行** — 独立任务是否在**一条消息内多个 tool call** 并发派出(Anthropic:复杂任务节省 90% 时长)?
- [ ] **B5 团队规模合理** — worker 数量是否在 3-5 个黄金区间,且每 worker 承担 ≥6 子任务(否则协调开销 > 收益)?
- [ ] **B6 Orchestrator 不是 SPOF** — 主线程是否会因单 agent 卡住而阻塞全 pipeline(synchronous block 反模式)?Anthropic 自己承认这是当前未解局限,要明示设计折中。

## C. Handoff 契约(Inter-agent Misalignment, MAST 类 2)

- [ ] **C1 Handoff 走结构化数据** — agent 之间传递的是 JSON / markdown 带明确 schema,还是 free-form 散文?
- [ ] **C2 上下文完整性可验证** — 接收 agent 能否在第一步检测出"上一棒没传我需要的字段"并 fail-fast,而不是默默用默认值?
- [ ] **C3 文件并发隔离** — 多 agent 并行编辑是否被分割到**不同文件 / 不同区段**?有无锁或冲突检测?
- [ ] **C4 任务依赖显式标注** — blocked task 是否在 upstream 完成时**自动解锁**,而非靠人工 ping?
- [ ] **C5 Role overlap 体检** — 任意两个 agent 的 description 是否会让 router 二选一摇摆?(若是,合并或重写 description)

## D. 效率(Cost & Latency)

- [ ] **D1 Token 预算成文** — 是否有"95% 任务 < N tokens / M tool calls"硬约束?**multi-agent 烧的 token 约 chat 的 15×,无预算 = 不可控**
- [ ] **D2 Tool call 数量监控** — 良设计 agent 单任务 tool call < 5;trajectory efficiency 指标是否定期跑?
- [ ] **D3 Tool description 优化过** — 是否做过 tool-testing(Anthropic 内部:改写 tool description 后任务时间 **-40%**)?
- [ ] **D4 P95 latency 已知** — 知不知道单任务 P50 / P95 / P99?长尾来源(long context / retry loop / 弱 routing)是否定位?
- [ ] **D5 不必要的 agent 数被裁** — 简单任务是否回退到 single session(不要为分层而分层)?

## E. 可靠性与错误恢复(Reliability & Assurance)

- [ ] **E1 Resume 而非 Restart** — 中间失败能否从 checkpoint 恢复?Anthropic 原话:"minor failures can be catastrophic" 没有 durable execution = GAP。
- [ ] **E2 Fail-fast** — schema 校验失败立即停 + 返回结构化 error;是否禁止"置信度低就降级输出"的 silent degradation?
- [ ] **E3 Retry 有上限** — 有无 retry budget?是否禁止无限循环 / 自我修正死循环?
- [ ] **E4 失败模式分类** — 团队是否对照 MAST 14 种 failure mode 做过一次自检(specification 缺漏 / handoff 丢字段 / 验证缺失)?
- [ ] **E5 单 worker 失败不卡全队** — 一个 subagent 崩了,任务是否能被重派 / 跳过 / 降级,而不是整条 pipeline 死亡?

## F. 评估与监督(Verification, MAST 类 3)

- [ ] **F1 LLM-as-judge 而非硬 checklist** — 评价标准是不是固定 if-else 规则?Anthropic 用 5 维 0.0-1.0(factual / citation / completeness / source quality / tool efficiency)
- [ ] **F2 Eval 集 ≥20 真实样本** — 不是单元测试,是真实用户 query 跑端到端
- [ ] **F3 Human-in-the-loop 抓 edge case** — 是否定期人工抽查(LLM judge 抓不到的 long-tail)?
- [ ] **F4 Critic / Verifier 是独立 agent** — 验证职责是否与生成职责**物理隔离**(同一 agent 自评是反模式)?
- [ ] **F5 Lead 主动抽查** — orchestrator 是否会主动拒收 worker 输出,而不是盲目透传?

## G. 可观测性(Observability)

- [ ] **G1 全链路 trace** — 每个 tool call / agent invocation / handoff 是否都有 span?
- [ ] **G2 符合 OTel GenAI 语义约定** — `invoke_agent` 顶层 span + `chat` + `execute_tool` 子 span;`gen_ai.usage.input_tokens` 等标准属性?
- [ ] **G3 三粒度评估** — session / trace / span 各自有 evaluator?
- [ ] **G4 隐私安全** — 监控 decision pattern / interaction structure,不存对话明文
- [ ] **G5 Deterministic replay** — 失败 trace 能否原样重放?(LangGraph 的 node-as-graph 是参考实现)
- [ ] **G6 灰度部署** — 升级 agent 时是否 rainbow deployment,不打断 in-flight 任务?

## H. 反模式自检(看到就扣分)

- [ ] **H1 Agent sprawl** — 是否存在 ≥2 个职责重叠 agent?
- [ ] **H2 Over-delegation** — 是否有 subagent 缺 objective / output format / tool guidance 就被派出去?
- [ ] **H3 Context leakage** — 单 agent 是否跨 domain(monolithic toolkit → attention decay + 幻觉)?
- [ ] **H4 主线程偷跑** — 主线程是否会在该 delegate 的任务上自己动手(常见于"快"心态)?
- [ ] **H5 Token blow-up 不可见** — 你能不能在不跑命令的情况下说出"上次跑这个 pipeline 烧了多少 token"?说不出 = GAP。
- [ ] **H6 Silent degradation** — 是否存在"低置信度就输出 N/A 或 placeholder"的代码路径?

---

## 一手参考(按优先级)

1. **Anthropic — How we built our multi-agent research system** https://www.anthropic.com/engineering/built-multi-agent-research-system
2. **MAST — Why Do Multi-Agent LLM Systems Fail?** https://arxiv.org/abs/2503.13657
3. **MultiAgentBench** https://arxiv.org/abs/2503.01935
4. **Claude Code: Subagents** https://code.claude.com/docs/en/agent-sdk/subagents.md
5. **Claude Code: Agent Teams** https://code.claude.com/docs/en/agent-teams.md
6. **OpenTelemetry GenAI Semantic Conventions** https://opentelemetry.io/blog/2026/genai-observability/
7. **Arize — Agent evaluation metrics** https://arize.com/resource-hub/agent-evaluation-metrics/
8. **TheNewStack — Why agentic LLM systems fail** https://thenewstack.io/why-agentic-llm-systems-fail-control-cost-and-reliability/

---

## I. 量化指标速查表(v2 追加,2026-05-25 调研)

> v1 章节(A–H)是定性 PASS / GAP 审计;本节是**带阈值的数字指标**,用于做监控告警与回归测试。每条指标可直接落到 trace pipeline 上。

### I.1 质量 Quality

| # | 指标 | 口径 | 参考阈值 | 来源 |
|---|---|---|---|---|
| Q1 | First-pass yield | critic 第一次 verdict = pass 的比例 | ≥ 70–80% | LangSmith 经验 |
| Q2 | Rework rate | 触发 `needs_*_rewrite` / 用户提迭代的比例 | < 10% | Anthropic agent-design |
| Q3 | Anthropic 5 维 rubric | factual / citation / completeness / source quality / tool efficiency,各 0.0–1.0 | 平均 ≥ 0.8 | [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) |
| Q4 | Critic 校准度 | critic 通过率与人工评分的 Kendall τ | ≥ 0.6 | τ-bench 改造 |
| Q5 | Reasoning-action match | critic 声明的 checklist 项是否有结构化证据回填 | 100% | MAST FM-2.6 |

### I.2 稳定性 Stability

| # | 指标 | 口径 | 参考阈值 | 来源 |
|---|---|---|---|---|
| S1 | **`pass^k`(关键!)** | 同一 brief 独立跑 k 次**全部**成功的概率 | pass^5 ≥ 0.8 | [τ-bench](https://arxiv.org/abs/2406.12045) |
| S2 | 构建失败率 | `.pptx` 异常(XML / 字体 / shape)比例 | < 2% | Managed Agents events |
| S3 | 可复现性方差 | 同 brief N 次的 wall-clock / token / 视觉 hash 方差 | < 15% | — |
| S4 | 僵死线程率 | `session.thread_status_terminated` 异常比例 | < 1% | Managed Agents events |
| S5 | `max_tokens` 截断率 | `stop_reason = max_tokens` 占比 | < 10% | Anthropic events API |
| S6 | Human assist 次数 | 单任务被人工接管的次数 | 趋零 | 业界通用 |

### I.3 效率 Efficiency

| # | 指标 | 口径 | 参考阈值 | 来源 |
|---|---|---|---|---|
| E1 | Token-per-task 预算 | 单 deck 的 in+out token 总和 | < 单轮 author × 30(基线 multi-agent ≈ 15× chat) | Anthropic multi-agent post |
| E2 | Cost-of-pass | `total_tokens / success_rate` | ≤ single-agent baseline | [Efficient Agents](https://arxiv.org/pdf/2508.02694) |
| E3 | Prompt cache 命中率 | `cached_input_tokens / input_tokens` | ≥ 40% | Anthropic usage API |
| E4 | Trajectory 冗余度 | 可裁剪的中间步 token 占比 | 可降 ≤ 40% 视作有优化空间 | [AgentDiet](https://arxiv.org/pdf/2509.23586) |
| E5 | Wall-clock E2E | brief 输入 → `.pptx` 落盘总时延 | 立 SLA(15min deck ≤ 8min) | LangSmith trace |
| E6 | 模型选型成本比 | Opus 调用成本 / Sonnet 调用成本 | < 1.5× | Anthropic usage API |
| E7 | Subagent 配比经验 | 简单 1 agent / 3–10 calls;比较 2–4 / 10–15;复杂 10+ | 越界告警 | Anthropic multi-agent post |

### I.4 可观测性 Observability

- **O1** 每个 agent 都有 trace tree(input / output / tool calls / latency / token)
- **O2** Trajectory eval:实际 step 序列 vs 期望序列子序列匹配度
- **O3** Single-step eval:critic 路由、author 章节决策等关键节点单独可评 — 参考 [LangChain Deep Agents](https://www.langchain.com/blog/evaluating-deep-agents-our-learnings)
- **O4** Handoff message log:`agent.thread_message_received/sent` 全量留痕,可 diff 跨 agent 信息丢失
- **O5** Token / latency 时序面板:P50 / P95 / P99 per-agent,按天聚合

### I.5 MAST 14 项失败模式 — 我们流水线的最相关映射

| MAST 项 | 在 iLovePPT 5-agent 流水线的体现 |
|---|---|
| FM-1.1 Disobey task spec | iloveppt 漏 layout / 渲染不按 deck_plan |
| FM-1.2 Disobey role spec | author 越权改大纲 |
| FM-1.3 Step repetition | iloveppt 反复改同一页 |
| FM-1.4 Loss of conversation history | brief.md 信息没传到 content.md |
| FM-1.5 Unaware of termination | 视觉 QA 死循环 |
| FM-2.1 Conversation reset | critic 反馈被新 author session 丢 |
| FM-2.2 Fail to ask for clarification | brainstorm 信息不全就交付 |
| FM-2.3 Task derailment | author 写了 brief 没要求的章节 |
| FM-2.4 Information withholding | critic 漏报 outline 硬伤 |
| FM-2.5 Ignored other agent's input | audience 反馈被吞 |
| **FM-2.6 Reasoning-action mismatch** | critic 声明"14 项 checklist 全过"实际只查了 8 项 — **最隐蔽** |
| FM-3.1 Premature termination | audience 没读完就打分 |
| FM-3.2 No / incomplete verification | 跳过视觉 QA |
| FM-3.3 Incorrect verification | critic 通过了劣质 content |

---

## J. 立刻该补的三件事(2026-05-25 调研建议优先级)

1. **`pass^k` 回归套件** — 挑 10 个标准 brief,每个独立跑 5 次,pass^5 ≥ 0.8 才算发布就绪。当前我们只看 pass@1。
2. **Critic 校准 baseline** — 挑 30 个历史 deck 让人工打分,算 critic verdict 与人评的 Kendall τ。τ < 0.6 → critic prompt 必须改。
3. **Token-per-deck 预算 + 越界告警** — 跑 10 个标准 brief 取中位数 × 1.5 作上限,超限触发 trace 审查。是 step-repetition / context-collapse 的早期信号。

---

## v2 新增的一手参考(2026-05-25)

- [τ-bench(arxiv 2406.12045)](https://arxiv.org/abs/2406.12045) — `pass^k` 可靠性指标
- [AgentBench(arxiv 2308.03688)](https://arxiv.org/pdf/2308.03688) — 8 环境完成率/步数
- [MultiAgentBench(arxiv 2503.01935)](https://arxiv.org/pdf/2503.01935) — milestone KPI
- [Beyond Accuracy / CLASSic(arxiv 2511.14136)](https://arxiv.org/html/2511.14136v1) — Cost/Latency/Accuracy/Stability/Security 五维
- [Efficient Agents(arxiv 2508.02694)](https://arxiv.org/pdf/2508.02694) — cost-of-pass 公式
- [AgentDiet(arxiv 2509.23586)](https://arxiv.org/pdf/2509.23586) — trajectory 剪枝实证
- [LangSmith — Evaluate a complex agent](https://docs.langchain.com/langsmith/evaluate-complex-agent) — final / trajectory / single-step 三维
- [Sierra blog — τ-bench shaping agent dev](https://sierra.ai/blog/tau-bench-shaping-development-evaluation-agents) — `pass^k` 实战
- [Anthropic — Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) — 架构警告(latency/cost 换 performance)

---

## 使用说明

- **第一次用**:对照清单逐项标 PASS / GAP / N/A,统计 GAP 数与所在维度。
- **复盘节奏**:每次 agent 流水线大改动后跑一次;每季度跑一次全量审计。
- **优先级**:L1-L3 母法则违反 > MAST 类 1/2/3 失败 > 反模式(H 区)> 可观测性补齐(G 区)。
- **本仓库专用应用**:iLovePPT 当前 pipeline(brainstorm → author → critic → iloveppt → designer → audience + extractor 旁路)逐项审计的报告,见 `docs/archive/`(每次审计时新增日期戳文件)。
