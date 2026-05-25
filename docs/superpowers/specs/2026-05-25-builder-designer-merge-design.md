# builder + designer 合并为单 iloveppt agent · 设计 spec

> **任务**:把 `iloveppt`(builder)和 `iloveppt-designer` 两个 agent 合并为单 `iloveppt` agent。流水线从 6 agent + 1 旁路 缩为 **5 agent + 1 旁路**。
>
> **创建**:2026-05-25
> **分支**:`feat/optimization`
> **状态**:待执行(spec 已批准)

---

## 1. 重构目标

当前 builder 跟 designer 在流水线上是相邻两步,且都对同一个 `deck_plan.json` / `.pptx` 操作 —— builder 出机械版,designer 自动跑一次加视觉。两个 agent 是**串行强耦合**(builder done → 主线程 auto-dispatch designer)。

**目标**:把两者合并为单 agent `iloveppt`(扩展原 builder 流程加 Step 4 "主动加视觉")。流水线简化,跨 agent handoff 减一层,语义内聚("做 .pptx + 打磨视觉" 是同一职责)。

---

## 2. 重构参数(brainstorming 已对齐)

| 维度 | 决策 |
|---|---|
| **合并方式** | `iloveppt`(builder) 吞并 `iloveppt-designer`,**保留 `iloveppt` 名**(不改 dispatcher / agent name 引用)|
| **audience 反馈分流** | `needs_designer_revision` → **`needs_visual_redo`**(语义不变,改名)|
| **mode 字段** | iloveppt 入参加 `mode: full | visual_redo`(full=Step 0-5 全跑;visual_redo=跳 Step 0-3,只跑 Step 4 + rebuild)|
| **目录 + 命名** | `designer/` 目录消失,产物全归 `builder/`;`designer_report_r{N}.md` → `visual_report_r{N}.md` |
| **改动范围** | 全范围(agent / 协议 / agent-internals / MANUAL / README)|

---

## 3. 新 iloveppt agent 流程

### 3.1 Step 0-5(原 builder 5 步 + 原 designer Step 1-5 整合为 Step 4)

```
Step 0 · 强前置 gate
  0.0 Read 入参 critic_d_report_path → verdict 检查
  0.1 Read content_md_path + author/state.json (pyramid_known_issues)
  0.2 Pyramid 自检 7 项(独立跑,3 层防线第 3 层)

Step 1 · md → deck_plan.json
  解析 content.md 按 content-writing.md schema → deck_plan.json
  反向 diff 校验(差异 > 5% 报错)

Step 2 · 跑 build.py
  python3 ${CLAUDE_PROJECT_DIR}/skills/pptx-deck/build.py <deck_plan.json>
  → .pptx + render PNG

Step 3 · 机械视觉 QA × ≤ 3 轮
  字号 / 对齐 / 颜色 / 溢出 / footer / chart 破损
  自动改副本 .postbuild.md(原文不动)

Step 4 · 主动加视觉(原 designer Step 1-5 并入)
  4.0 能力探测:cairosvg / UNSPLASH_KEY / brand assets
  4.1 视觉扫描 4 类机会:icon 缺失 / hero 缺失 / 装饰过简 / 布局节奏同质
  4.2 主动加视觉:iconify(首选,免费)/ Unsplash(需 KEY)/ brand assets(优先)
       三路 graceful degrade
  4.3 改 deck_plan.json + rebuild
  4.4 自检 fresh Read · 改了变好留下 · 变糟回滚

Step 5 · 写 visual_report_r{N}.md + 返回
  visual_report 含:visual_edits[] / rolled_back[] / 4 类机会处理记录 /
  audience_priority_addressed_count(第 2 轮起)
  返回 done(pptx_path + auto_md_edits + qa_rounds + visual_edits_count)
```

### 3.2 Step 4 风格统一硬规则(从原 designer 继承)

- 全 deck icon 同一 prefix(`lucide` / `phosphor` / `heroicons` / `tabler` 选一,**不混 prefix**)
- 染色限定 `BRAND_*` / `GRAY_*` 色板(helpers.py SSOT)
- 不混 flat + 写实摄影(单 deck 选一)
- **节制原则**:咨询稿是文字驱动,没合适 icon 就不加,比将就加更专业

---

## 4. mode 字段(新增入参)

| mode | 跑哪些 step | 触发场景 |
|---|---|---|
| `full`(默认) | Step 0-5 全跑 | 首跑 / author 改 content 后重派 / 任意 critic D 报告变化 |
| `visual_redo` | **跳 Step 0-3**,直接 Step 4 + rebuild + final QA | audience 反馈 `needs_visual_redo` 时(主线程派回 iloveppt) |

### 4.1 入参契约(扩展)

```yaml
working_dir: /abs/path/to/deck-工作目录
content_md_path: <working_dir>/author/deck_v{N}_content.md
output_pptx: <working_dir>/builder/deck_v{N}.pptx
theme: tech_blue
critic_d_report_path: <working_dir>/critic/critic_report_D_r{N}.md   # mode=full 时必填
mode: full | visual_redo                                              # 默认 full
prev_audience_review_path: <working_dir>/audience/audience_review_r{N-1}.md  # mode=visual_redo 时必填
prev_visual_report_path: <working_dir>/builder/visual_report_r{N-1}.md       # mode=visual_redo 时可选(避免重复改/回滚)
```

### 4.2 mode=visual_redo 流程

```
Step 0 · 跳过(假设 deck_plan.json / pptx 已存在)
Step 1 · 跳过
Step 2 · 跳过
Step 3 · 跳过
Step 4 · 跑(主线程要传 prev_audience_review_path,iloveppt 读 needs_visual_redo 页号 priority high)
Step 5 · 写 visual_report_r{N}.md(N = max existing + 1)
```

---

## 5. audience 反馈分流(改名 1 项)

```yaml
# 旧
needs_author_rewrite: [pages]
needs_designer_revision: [pages]
needs_theme_fix: [pages]

# 新
needs_author_rewrite: [pages]
needs_visual_redo: [pages]                # 改名
needs_theme_fix: [pages]
```

**主线程处理**:

- `needs_author_rewrite` → 派 author 改 content → critic Stage D 重评 → iloveppt mode=full(走完整)
- `needs_visual_redo` → 派 iloveppt mode=visual_redo(只重做视觉,跳过 build)
- `needs_theme_fix` → 主线程改 themes/tech_blue.py → iloveppt mode=full 重 build

---

## 6. 工作目录布局变化

```diff
 builder/                               (iloveppt 自己产物全归这里)
 ├── deck_plan.json
 ├── deck_v{N}.pptx
 ├── deck_v{N}_render/
 ├── deck_v{N}_content.postbuild.md
+├── visual_report_r1.md               (原 designer/designer_report_r{N}.md,改名)
+├── visual_report_r2.md
+├── icons/                             (原 designer/icons/)
+└── hero/                              (原 designer/hero/)

-designer/                              (整个目录删)
-├── designer_report_r{N}.md
-├── icons/
-└── hero/
```

---

## 7. 改动清单

| 类型 | 文件 | 改动 |
|---|---|---|
| **删除** | `.claude/agents/iloveppt-designer.md` | 整个文件删 |
| **改 agent** | `.claude/agents/iloveppt.md` | 加 Step 4(整合 designer 流程)+ 加 mode 入参 + 加 prev_* 入参 + Step 5 改名 visual_report |
| | `.claude/agents/iloveppt-audience.md` | `needs_designer_revision` → `needs_visual_redo` |
| **改协议** | `.claude/pipeline-protocol.md` | §8.5 designer 章节并入 §8 / 概览 6→5 agent / agent 表 designer 行删 / handoff 表 / §0.5 版本化表 designer 行改 visual_report / §9 builder→audience handoff 描述简化(不再有"先派 designer 才派 audience") |
| **改文档** | `docs/agent-internals.zh.md` | "6 agent + 1 旁路" → "5 agent + 1 旁路" 全文替换 / §2.4 + §2.5 合并 / §3 协作机制 / §4 决策 4.4 视觉 QA 三方分工改为"机械 + 主动 + 认知,但前两者归 iloveppt"/ §5.3 工作目录布局 / mermaid 总图 |
| | `docs/MANUAL.zh.md` | 工作目录布局图 / 6 阶段说明改 5 阶段(designer 段并入 build)/ "你会看到什么" 章节 |
| | `README.md` | mermaid 流水线图(8 节点→7 节点,去 designer 节点)/ slogan / why iLovePPT 段(若提到) |
| **不动** | `build.py` / `extract_template.py` / `tests/` / 其他 agent | 机械工具不感知 agent 拆分;其他 agent 不涉及 |
| **新增** | 本 spec | `docs/superpowers/specs/2026-05-25-builder-designer-merge-design.md` |

---

## 8. 执行步骤

1. **删 `iloveppt-designer.md`**
2. **改 `iloveppt.md`**(并入 Step 4 + mode + 入参 + visual_report 命名)
3. **改 `iloveppt-audience.md`**(needs_designer_revision → needs_visual_redo)
4. **改 `pipeline-protocol.md`**(§8.5 合入 §8 + 全文 agent 数 / handoff / 版本化表)
5. **改 `agent-internals.zh.md`**(7→6 agent 全文 + §2.4+2.5 合并 + mermaid + §5)
6. **改 `MANUAL.zh.md`**(工作目录布局 + 6 阶段说明)
7. **改 `README.md`**(mermaid 流水线 7→6 节点)
8. **跑 pytest** 确认 72 测试不破
9. **commit + push**

---

## 9. 验收标准

- [ ] `.claude/agents/iloveppt-designer.md` 已删除(`ls .claude/agents/` 验证)
- [ ] `iloveppt.md` 含 Step 0-5(Step 4 是主动加视觉)+ mode 入参
- [ ] `audience.md` 全文无 `needs_designer_revision`,有 `needs_visual_redo`
- [ ] `pipeline-protocol.md` 概览图 / agent 表 / handoff 全部 5 agent + 1 旁路
- [ ] `pipeline-protocol.md` §0.5 版本化表 `designer/designer_report_r{N}.md` → `builder/visual_report_r{N}.md`
- [ ] `agent-internals.zh.md` 全文无 "6 agent + 1 旁路",改为 "5 agent + 1 旁路"
- [ ] `agent-internals.zh.md` §2 子节数从 7 → 6(brainstorm/author/critic/iloveppt/audience/extractor)
- [ ] `MANUAL.zh.md` 工作目录布局图无 `designer/` 块,builder/ 含 visual_report_r{N}.md / icons/ / hero/
- [ ] `README.md` mermaid 流水线图无 designer 节点(节点数 7→6)
- [ ] grep `iloveppt-designer` 全仓返 0(除 archive / specs)
- [ ] grep `designer_report` 全仓返 0(除 archive / specs)
- [ ] grep `needs_designer_revision` 全仓返 0(除 archive / specs)
- [ ] 72 pytest 全过

---

## 10. 风险与缓解

| 风险 | 缓解 |
|---|---|
| iloveppt 文件变胖(~380 + ~360 → ~700 行) | 内部清晰分 Step 0-5,Step 4 子节 4.0-4.4 |
| mode=visual_redo 跳哪些 step 不明确,LLM 误跑 | spec §4.2 + agent 文件 Step 0 加 mode 分流条件判断 |
| audience needs_designer_revision 残留导致主线程派错 | 验收 grep 0 残留 |
| 文档跟设计不同步(全范围工作量大) | 7 个改动文件按步骤来 + 最后 grep 全仓验收 |
| 现有 visual_report 命名跟"agent 独立目录"原则有歧义(visual 不是 agent 名) | 合理:agent 是 iloveppt,产物 visual_report 表示"视觉报告"性质,跟 deck_plan.json / .pptx 同级在 builder/ |

---

## 11. 不在本次范围

- 不动 build.py(机械工具,从 deck_plan.json output 字段读路径,不感知 agent)
- 不动 extract_template.py(extractor 旁路)
- 不实现"自动 visual_redo"(audience < 9 + 视觉问题 → 手动 cherry-pick 后才派)
- 不动 critic / brainstorm / author / audience 内部流程(只动 audience 反馈分流名)
- 不动 _assets/ 用户共享资产(brand/ 等)
