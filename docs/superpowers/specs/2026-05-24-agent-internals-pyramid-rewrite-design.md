# agent-internals.zh.md 金字塔重写 · 设计 spec

> **任务**:把 `${CLAUDE_PROJECT_DIR}/docs/agent-internals.zh.md`(当前 1172 行 / 9 章)按麦肯锡金字塔原理全面重写。
>
> **创建**:2026-05-24
> **状态**:待执行(spec 已批准)

---

## 1. 重写目标

让一份文档同时服务三类读者,各取所需:

- **新人 onboarding** —— 顶端论点 + SCQA 开场 30 秒看明白系统是干什么的
- **iLovePPT 仓库开发者** —— 改 agent / 加站点 / debug 时直接定位到具体章节
- **Claude Code 主线程 AI** —— 跳读该派哪个 agent / 何时 handoff,跟 `${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md` 互补不重叠

---

## 2. 重写参数(brainstorming 已对齐)

| 维度 | 决策 |
|---|---|
| **顶端论点** | 架构论:iLovePPT 是 thin dispatcher 协调下的 6 专业 agent + 1 旁路接力流水线 |
| **MECE 切分** | 按"读者疑问链"切 5 章:流水线是什么 / 每个 agent 干啥 / 怎么协作 / 为啥这么设计 / 怎么查用 |
| **重写粒度** | L3 全面重写(文字措辞 / 例子 / 表格 / mermaid 都重做) |
| **章节标题风格** | 结论句(BCG/McKinsey 标准 action title),不用疑问句 |
| **mermaid 图** | 全部重画(以金字塔为线,体现 child question) |
| **Quick start** | 不要(SCQA 已是 30 秒摘要,加 quick start 是重复) |
| **参考性内容** | 放 §5(跟 timeline / 进一步阅读 同章),不抽附录 |

---

## 3. 顶端论点 + SCQA 开场(草稿)

```markdown
# iLovePPT Agent 工作原理

> 这份文档讲清楚 iLovePPT 怎么工作的 —— 6 agent 流水线 + thin dispatcher
> 协作机制 + 关键设计决策 + 接口契约。适合想理解或改造系统的人;不是用户
> 操作手册(那个看 [MANUAL.zh.md](${CLAUDE_PROJECT_DIR}/docs/MANUAL.zh.md))。
>
> *运行时活协议(权威):${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md*

让 LLM 一次性生成完整 PowerPoint deck,通常是"看着像但读起来空 + 视觉糙 +
论据弱"——单 agent 既要拓写又要自检,有结构盲区(自己写的自己评不出来)、
有窗口污染(对话上下文挤掉细节)、有质量门含糊(没有"何时该 fail")。

**iLovePPT 把"写 PPT"拆成 thin dispatcher 协调下的 6 专业 agent + 1 旁路
接力流水线**:每个 agent 独立窗口、单一职责;通过 next_action 路由 + state
file + brief.md / outline.md / content.md / deck_plan.json 四重接缝协作;
critic 双 gate + audience 9 分硬阈值 + 用户最终确认共同把质量底线托起来。
```

---

## 4. 5 章 outline + 每章 child question + 内容归宿

### § 1. 流水线是 thin dispatcher 协调下的 6 agent + 1 旁路接力

**Child question**:流水线长什么样?

**子节**:
- 1.1 thin dispatcher 是中枢,只路由 next_action 不持业务
- 1.2 6 agent + 1 旁路按"内容 → 评审 → 构建 → 视觉 → 受众"五段接力
- 1.3 [总架构 mermaid 图]

**新内容来源**:原 §1 30 秒理解 + §2 核心架构主图

### § 2. 每个 agent 承担互不重叠的单一职责

**Child question**:每个 agent 干什么?

**子节(7 个 agent)**:
- 2.1 brainstorm 用多轮对话收 brief + 素材,gate 在 brief.md 用户确认
- 2.2 author 在 Stage C/D 硬隔离下出 outline + content
- 2.3 critic 是 partner 评审员,14 项 checklist + 4 维度判断性 + 三档 verdict
- 2.4 builder 是机械构建器,Step 0 硬阻塞 + 视觉 QA 限机械项
- 2.5 designer 主动加视觉,iconify / Unsplash / brand 三路降级 + 风格统一硬规则
- 2.6 audience 模拟受众评分,9 分硬阈值 + 三类反馈分流
- 2.7 extractor 旁路一次性提取 .pptx 模板 4 级 token

**每个 agent 子节带内部流程 mermaid + 反例(避坑)inline**

**新内容来源**:原 §3 6 agent 各自角色(整章平移,标题改结论句)+ §8 避坑表(打散到各 agent inline)

### § 3. agent 间通过 4 个机制协作

**Child question**:它们怎么协作?

**子节(4 个机制 MECE)**:
- 3.1 多次派发 + state file 让单次派发 agent 实现多轮对话
- 3.2 next_action 是主线程统一路由协议(7 种动作)
- 3.3 多重接缝(brief→outline→content→deck_plan→pptx)让错误在低代价窗口修
- 3.4 critic 双 gate + audience 9 分硬阈值 + 用户确认 共同构成三层质量门

**新内容来源**:原 §4 关键机制(4 个子机制平移)+ §6 部分(critic 三档 + audience 双闸门)

### § 4. 6 条关键设计决策让这套架构成立

**Child question**:为什么这么设计?

**子节(6 条决策)**:
- 4.1 build.py 纯机械、不调 LLM(可重放 / 可测试 / 可调试)
- 4.2 主线程退化为 thin dispatcher(主线程 context 不被 PPT 任务污染)
- 4.3 critic 是 partner 评审员而非合规检查员(beyond checklist 的判断性)
- 4.4 视觉 QA 三方严格分工(机械 builder / 主动 designer / 认知 audience)
- 4.5 cherry-pick 不强耦合(critic/audience 不命令 author/designer,用户决策)
- 4.6 SSOT 在 helpers.py(代码层一份定义 vs 文档层多份引用)

**新内容来源**:原 §6 关键设计决策(10 条 → 6 条,合并 6.7+6.8 / 6.9+6.10 / 6.11 跟 §2 designer 章节合并)

### § 5. 怎么查 / 怎么用(参考章节)

**Child question**:怎么读 / 怎么用?

**子节**:
- 5.1 一次典型调用 timeline(22 分钟 case)
- 5.2 主线程 → agent 入参契约
- 5.3 state file schema + 工作目录布局
- 5.4 进一步阅读(权威协议 + agent prompt + skill 文档)

**新内容来源**:原 §5 接口契约 + §7 timeline + §9 进一步阅读

---

## 5. 删除/合并的内容(L3 重写允许)

| 删/合并对象 | 处理 | 理由 |
|---|---|---|
| § 1 "30 秒理解"整章 | 删 | SCQA 开场已覆盖,避免顶层重复 |
| "6 层比喻"(咨询 senior / 排版工程师 / 邮局) | 删 | 过于俏皮,不是金字塔结论 |
| § 8 "避坑表" 4 大类 70 行 | 打散到 § 2/§ 3/§ 4 inline | 避坑论是各设计决策的副产品,不该独立成顶层 MECE 章 |
| § 6.7-6.11 重叠决策 5 条 | 合并为 § 4.3-4.6 4 条 | 原 6.8(critic 双 gate)/ 6.9(audience 9 分)跟 §4 机制章已经讲过,§4 决策章只留 rationale |

---

## 6. Mermaid 图重画清单

| 新章节 | 图内容 | 跟原图关系 |
|---|---|---|
| § 1.3 总架构图 | thin dispatcher + 6 agent + 1 旁路 + skill 层 + build.py | 改写自原 §2 主图,标识 child question 路径 |
| § 2.1-2.7 各 agent 内部流程 | 每 agent 一个 internal flow(7 个图) | 改写自原 §3 各小节图,统一 step 命名 + 加 BLUF caption |
| § 3.1 多次派发 sequence | 主线程 ↔ agent ↔ state file 三方 sequenceDiagram | 平移自原 §4.1 |
| § 3.3 接缝流程图 | brief → outline → content → deck_plan → pptx 五接缝 + 各 gate 标记 | 改写自原 §4.3 |
| § 3.4 三层质量门图 | critic Stage C/D + audience 9 分 + 用户确认 双闸门 | 改写自原 §4.4 + §4.5 合并 |

---

## 7. 执行步骤

1. 备份当前 `${CLAUDE_PROJECT_DIR}/docs/agent-internals.zh.md`(commit 已经在 git 里,无需额外备份)
2. 按 outline 重写,**直接覆盖 agent-internals.zh.md**(不开 v2 文件)
3. 内容来源:
   - 80% 复用原文实事(facts / 决策 / agent 行为描述)
   - 20% 新写(SCQA 开场、章节 action title、各章 BLUF 首句、三层质量门表)
4. mermaid 全部重画,统一 classDef 配色(沿用原 stage1-stage5 配色保持视觉连续)
5. 写完用户审,可能 iterate

---

## 8. 验收标准

- [ ] 文件首段就是 SCQA + 顶端论点(< 200 字)
- [ ] 每章标题是结论句,不是疑问句或话题标签
- [ ] 每章开头有 1 句 BLUF 答复 child question
- [ ] §1 + §2 + §3 + §4 + §5 共 5 章,不多不少
- [ ] §2 章 7 个子节(6 agent + 1 旁路 extractor)+ §3 章 4 个机制 + §4 章 6 条决策(MECE 数量都对)
- [ ] 不再有"30 秒理解"独立章节
- [ ] 不再有"避坑表"独立章节(避坑散到各 agent / 机制 inline 反例)
- [ ] 全文新 mermaid 图 ≥ 10 个(总图 1 + agent 内部 7 + 机制图 3)
- [ ] 路径引用全部 `${CLAUDE_PROJECT_DIR}/...`(沿用上一轮迁移成果,不引入裸路径)
- [ ] 末尾"进一步阅读" 表格仍在 §5.4(链接到权威协议 / agent prompts / skill docs)

---

## 9. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 全面重写丢失原文里的隐性事实(如某条 critic 5 轮 cap 的细节)| 重写时左屏开原文,右屏写新文,逐章对照不遗漏 |
| 新 outline 跟 pipeline-protocol.md 重叠 | agent-internals 偏 rationale(为什么这么设计),pipeline-protocol 偏运行协议(主线程派发顺序),角色不重 |
| mermaid 重画跟现有 5 段配色不连续 | 沿用原 classDef stage1-stage5(brainstorm DCFCE7 / author FCE7F3 / critic CFFAFE / builder E6F0FC / audience FED7AA / designer FBCFE8 / extractor FEF3C7),不引入新色 |
| 重写后丢用户已 review 过的"voice"(俏皮 / 反例尖锐) | 反例 inline 保留尖锐(用 "**反例**:" 标),voice 整体专业化但不无趣 |
