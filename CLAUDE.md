# CLAUDE.md

本文件为 Claude Code(claude.ai/code)在本仓库工作时提供指引。

**这是导航文件** —— 高层架构 + 不变量在此;具体的协议 / handoff / gate 规则在链接到的 spec 里。

## 仓库是什么

iLovePPT 是一个 **agent team 帮你写 PPT 的开源工具**。clone 本仓库后,在仓库根目录跟 Claude Code 说"做 PPT",**5 个 agent + 1 旁路**(brainstorm → author → critic[cd 合审] → iloveppt-builder → audience + extractor)接力把你的想法变成完整 `.pptx`。P2-3 后 pipeline 7 步:brainstorm(自带 brief self-audit)→ author Stage C → author Stage D → critic stage=cd → builder → audience(自带 Step 0 spot-check)→ 用户 OK。

仓库本身就是产品:

- `.claude/agents/` —— 6 个 agent 定义(5 主流水线 + 1 旁路 extractor),Claude Code 启动时自动加载
- `.claude/skills/` —— 3 个 skill 实现(`pptx-deck` / `pptx` / `diagram`),Claude Code 自动加载,可直接 `Skill(skill="pptx-deck")` 调用
- `.claude/pipeline-protocol.md` —— agent 之间的派发 / handoff / gate 协议
- `.claude/settings.json` —— 框架配置(hooks / permissions / env)

> 安装 / 跑测试 / 烟测 / 单命令一览:见 [README.md § Development](README.md#development)。本文专注架构 + 不变量。

## 架构

### Agent 流水线(Hybrid:1 team + 5 subagent + 1 旁路 extractor + 2 Haiku helper)

`${CLAUDE_PROJECT_DIR}/.claude/agents/` 是项目的运行时流水线,**Hybrid 架构**:

- **Phase A (team 模式)**:brainstorm 用 `TeamCreate` 持续窗口,多轮 SendMessage 跟用户聊收 brief。
- **Phase B (subagent 模式)**:author / critic / iloveppt-builder / audience / template-extractor 用 `Task` 工具调用,每次跑完 return yaml(主线程 parse 决定下一步)。
- **Helper agents (P3-7)**:`iloveppt-self-check` / `iloveppt-yaml-fixer` 用 Haiku 跑结构性活,主流水线不直接派,主线程在工程错误恢复路径上 dispatch(详见下方 § Haiku helper agents)。

**模型(主流水线)**:6 个主流水线 agent 全用 **opus**(team 跨阶段一致性 + 整条流水线的深度判断 / 多职责 / 多轮对话 / 视觉认知都需要高质量推理)。

| agent | 角色 | 调用方式 | model |
|---|---|---|---|
| `iloveppt-brainstorm` | Stage A-B:多轮对话收 brief + 素材 + **Step 3.6 brief self-audit 5 项**(P2-3.1 后 critic Stage B 已并入),出 brief.md 让用户确认 | TeamCreate(team) | opus |
| `iloveppt-author` | Stage C-D:出 outline.md(章节骨架)→ 自走 Stage D 拓写 content.md(P2-3.2 后无中间 critic gate)— 两次独立 Task | Task | opus |
| `iloveppt-critic` | **partner 评审员**:stage=cd 单次合审 **21 项量化** rubric(P2-1 · `critic-rubric.yaml` SSOT · 每项 `{passed, evidence, severity 0-3, suggestion}` · verdict 自动算 · LLM 不主观判)+ 5 维度判断性评审(论据强度 / 节奏 / 措辞 / 平衡 / **pattern 适配性**),P2-3.2 后取代原 Stage C/D 双 gate | Task | opus |
| `iloveppt-builder` | Stage E:**机械构建 .pptx + 机械视觉 QA(Step 0-3)+ 主动加视觉(Step 4)**,iconify / Unsplash / brand / **RAG patterns** 四路降级;**Step 0.5 SSOT verify**(P2-5 · `deck_plan.json` sha256 对 `content.md` derived 结果)+ **Step 4.3.5 视觉一致性反查**(P2-7 · 把渲染 PNG 喂 `search.sh --query-image` 看是否漂出 brief.theme) | Task | opus |
| `iloveppt-audience` | **Step 0.0 spot-check**(P2-3.3 后并入,placeholder grep / chart source / 5+ PNG 破损 detect / red_line grep)+ 模拟目标受众读 deck 评分(**每页 12 项量化** · 0-3 分 + evidence · `page_score` weighted by persona;**multi-persona strict-eval** · brief.audience 是 list[persona] → 每 persona 各打一遍 · 取**最低分** · P2-2/13);反馈三类分流(needs_author_rewrite / needs_visual_redo / needs_theme_fix);**P3-5 评分完 append `library/_rag/feedback.jsonl` 反馈给 RAG** | Task | opus |
| `iloveppt-template-extractor` | 旁路:用户给 .pptx 模板时 ingest 到 `library/pptx-templates/items/<name>/`(复制 _source + render_pages.py 渲染每页 + 起草双层 yaml + Step 3.3 self-check 拦 enum/字段/YAML 语法),`user_review_drafts` gate → 用户审 → 主线程 embed | Task | opus |
| `iloveppt-self-check` | **P3-7 Haiku helper · 主流水线不直接派**;主线程在工程错误恢复路径上 dispatch:跑 `self_check.py` / `red_line_check.py` 等纯结构性校验脚本 + 解析输出 + 归一化 yaml | Task helper | **haiku-4-5** |
| `iloveppt-yaml-fixer` | **P3-7 Haiku helper · 主流水线不直接派**;修复 LLM 写错的 YAML(int 误识 str / colon 误识 dict / quote 不闭合等字面问题),**不动语义** | Task helper | **haiku-4-5** |

**深读**:派发 / handoff / gate / 退出条件 — [`.claude/pipeline-protocol.md`](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md)(AI 运行时活协议);系统怎么跑 — [`docs/agent-internals.zh.md`](${CLAUDE_PROJECT_DIR}/docs/agent-internals.zh.md)。

### Haiku helper agents(P3-7)

`iloveppt-self-check` + `iloveppt-yaml-fixer` 是**辅助 agent**,主流水线 6 agent 链路**不直接派**它们。主线程在以下**工程错误恢复**场景 dispatch:

1. **agent return yaml malformed**(`yaml.safe_load` 异常) → `Task(iloveppt-yaml-fixer, args={yaml_path, failure_report})` → 修完 → 主线程重 parse,失败 → 整 Task 重派原 agent
2. **批量 self-check**(extractor 一次入 N 个模板,主线程要并行校验) → `Task(iloveppt-self-check, args={check_type, targets})` × N 并行,聚合 fail 项
3. **CI / pre-commit 校验**(未来) → 同上,Haiku 跑批量校验比 Opus 单价 19x 便宜

**为什么 Haiku 够用**:这两个 agent 任务范围窄、规则化、输出 schema 严格 — 不需要创造性推理;但仍要 fail-loud,Haiku 4.5 跟得上 prompt 严格度。**主流水线 6 agent 仍全 Opus**(创造性 / 多轮对话 / 视觉认知 / 判断性评审是 Opus 不可替代的)。完整 dispatch 路径见 [pipeline protocol §3.7](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md#37-haiku-helper-错误恢复路径)。

### Library / 知识库(RAG)

[`library/`](${CLAUDE_PROJECT_DIR}/library/) —— 双知识库 + 单 DB + 顶层 router:

| kb | 单位 | 调用场景 |
|---|---|---|
| `library/visual-patterns/` | 跨模板视觉模式(timeline / pdca / funnel / ...) | author 拓写 / iloveppt-builder Step 4 加视觉 |
| `library/pptx-templates/` | 用户预置 .pptx 模板 + 拆出的每页 | brainstorm 列模板 / author 选页 / iloveppt-builder 渲染参考 |

**唯一检索入口** `library/search.sh`(`--preferred-template` 优先 + visual-patterns fallback;hosted multimodal embedding 阿里云 tongyi-embedding-vision-plus dim 1152;text + image 双 embedding 入库):

```bash
# A. 语义查模板(默认 text · brainstorm 列模板)
library/search.sh --kb pptx-templates --type template --query "<brief 主题>" --top-k 5

# B. 视觉风格查模板(hybrid · text+image 加权融合)
library/search.sh --kb pptx-templates --type template --query "<视觉描述>" --mode hybrid --top-k 5

# C. 图查相似页(image · 用 PNG 反查 · author/builder/audience 视觉互参)
library/search.sh --kb pptx-templates --type page --query-image <PNG> --mode image --top-k 5

# D. 限定模板内选页(author 拓写)
library/search.sh --query "<本页意图>" --preferred-template <name> --type page --top-k 5
```

短 query 自动撞库扩展(`财务` → `+财报+营收+CFO ...`),`--no-expand` 关。完整用法:`library/search.sh --help`。

`items/<id>/{meta.yaml, preview.png}` 入 git;`_rag/{db.sqlite, .venv, .env}` / `*/_source/*.pptx` 不入。

**Hybrid 权重 default** = `(0.8, 0.2)`(text/image)· P2-9 ablation 在 7 query × 4 权重组合(`(1,0)/(0.8,0.2)/(0.6,0.4)/(0.4,0.6)`)选出最佳;改 default **必须**先跑 `library/_rag/scripts/ablation_hybrid_weights.py` 拿数据。

### 受控词典层(P1 · `library/vocabularies/`)

受控词典 SSOT 5 个,LLM 必须**从枚举里选**,不允许自由发明 — extractor / author / critic / audience 都强约束。**新词**走 PR → review 后入 yaml,不走 inline 创造:

| yaml | 用途 | 规模 |
|---|---|---|
| `layout_variants.yaml` | layout 子类型(cards-3-icon / timeline-h-N / quadrant-swot 等),extractor 强制选 enum,212 页全 backfill | **139 enum** |
| `slot_ids.yaml` | 通用槽位词汇,extractor 强制选 enum,self_check #12 校验 | **1115 enum** |
| `categories.yaml` | 模板大类(`enterprise-finance` / `enterprise-product` / ...),retrofit 7 模板 | **12 enum** |
| `audience_personas.yaml` | persona schema(`{name, role, concerns, decision_criteria}`),brief.audience / audience 引用 | **7 persona** |
| `keywords_bank.yaml` | 按 category 分桶,LLM 从桶选,`EXPANSION_HINTS` derived view 自动生成 | **13 桶 / 327 词** |

### Deck skeletons(P3-8 · `library/deck-skeletons/`)

预置 6 个常见 deck 骨架(outline.md 模板 + 默认 SCQA + 推荐 layout 序列),`scripts/new_deck.py --skeleton <id>` scaffold 新 deck 自动 copy:

- `quarterly_finance_report` · `annual_strategy_review` · `product_launch` · `team_okr_kickoff` · `project_postmortem` · `customer_pitch`

skeleton 给 brainstorm Phase A **节省 30-50% 来回**(默认骨架够用 → 用户改填具体即可)。

### 主线程派发规则

"做 PPT" 意图 → 先 `TeamCreate(brainstorm)` 跑 Phase A;`dispatch_author` 后关 team,转 `Task` 依次调 author/critic/iloveppt-builder/audience(**不要**自己写 brief / content / 跑视觉 QA)。改仓库代码(helpers/ / themes / build.py / tests / agent prompts / 协议)时 → 主线程直接干。完整派发表:[pipeline protocol §1](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md#1-主线程派发表)。

**Pattern 注释 + cherry-pick**:
- **前缀强制**:author 写 content.md 的 pattern 注释必须带 kb 前缀 — `<!-- pattern: vp:<id> -->`(visual-patterns)或 `<!-- pattern: tpl:<theme>__<NN-slug> -->`(pptx-templates)。iloveppt-builder Step 2 按前缀路由查对应 kb,**无前缀 hard_stop**
- **cherry-pick gate**:critic / iloveppt-builder / audience return 含 `suggested_alternative_pattern(s)` → 主线程展示用户决定,不自决;用户答"改" → Task author rework(`user_response.accept_alternative_pattern: {page, suggest}`);audience 阶段触发改 → rework 后必须重派 critic D + audience

完整规则见 [pipeline protocol](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md)。

### 三 skill 分层

```
pptx-deck  ── 编排者:brief.md → outline.md → content.md → deck_plan.json → 完整 .pptx
   ├── 调用 → pptx      (helpers/ / layout / office 脚本 / render 流水线)
   └── 调用 → diagram   (draw.io / mermaid / matplotlib → PNG)
pptx       ── 底层 .pptx 读写;也可独立使用
diagram    ── 图表生成;也可独立使用
```

### build.py 是纯机械构建器(P3-3 后拆 builder/)

`build.py` 输入 `deck_plan.json` 输出 `.pptx` + PNG,**不含占位函数、不调 LLM**。接缝是 `deck_plan.json`:`{theme, output, slides: [{layout, ...fields}]}` — Claude 产出,`build.py` 消费。

**P3-3 拆分**:`build.py`(149 行)是**薄入口** · 业务逻辑落 `${CLAUDE_PROJECT_DIR}/.claude/skills/pptx-deck/builder/`:

- `builder/base.py` —— plan/theme load · `build_deck` orchestrator · render · `ThemeSpec` / `parse_theme`
- `builder/tier1.py` —— 跨模板 deep-copy slide(`placeholder_map.yaml` 索引 · shape-removal 删空槽 · P3-9 多模板组合支持)
- `builder/tier2.py` —— Python theme-specific `make_<layout>` 调度
- `builder/tier3.py` —— LayoutRegistry plugin fallback

智能步骤是 Claude 按文档化流程执行,**不是 Python 函数**:
- **内容拓写**(brief → per-page deck_plan.json) → 记录在 `content-writing.md`
- **视觉 QA**(读 PNG → 对照 17 项 checklist → 改 deck_plan → 重跑) → 记录在 `visual-qa.md`

提升生成**质量**改 prompt 文档(`content-writing.md` / `visual-qa.md`),**不要**改 `build.py` / `builder/`。

### SSOT 标准 —— helpers/ 是底层原语 · theme yaml 是 token · layout plugin 是渲染单元

**三层 SSOT**(P3-2 后):

1. **底层原语 SSOT** —— [`${CLAUDE_PROJECT_DIR}/.claude/skills/pptx/helpers/__init__.py`](${CLAUDE_PROJECT_DIR}/.claude/skills/pptx/helpers/__init__.py) 是权威源,下游只能引用或扩展,**不允许重定义**:
   - **底层 pptx 原语** —— 字体/形状/表格(`set_font` / `_fix_ph_font` / `card` / `bullets` / `table_modern` / `section_header` / `icon` / `connector` / `progress_bar` 等)
   - **底层 default token** —— `FONT_CN` / `FONT_NUM` / `BRAND_PRIMARY` / `BRAND_DARK` / `BRAND_TINT` / `ACCENT` / 灰阶 / `SLIDE_W` / `SLIDE_H`。任何 theme 没声明的 token 自动从这里继承
   - **`import helpers as H`** 入口不变(`helpers.py` → `helpers/__init__.py`,Python package 优先);所有 `H.set_font(...)` / `H.BRAND_PRIMARY` 保持向后兼容

2. **Theme token SSOT** —— [`${CLAUDE_PROJECT_DIR}/.claude/skills/pptx-deck/themes/<name>.yaml`](${CLAUDE_PROJECT_DIR}/.claude/skills/pptx-deck/themes/):每个 theme 的 design token 在此 **yaml** 声明(P3-1)。Python `.py` 文件仍提供 theme-specific `make_<layout>` 渲染函数,但 `colors` / `fonts` 不再硬编码:
   - `themes/_base.py:load_theme('tech_blue')` → 加载 yaml + 解析 ThemeConfig
   - `themes/_base.py:apply_theme(module, cfg)` → 把 yaml token 推到 module 常量(`PRIMARY = brand_primary` / `FONT_HEADER = ea` 等)
   - `themes/_base.py:get_layout_func(cfg, mod, layout_type)` → 按 yaml `layouts:` mapping 返回 `make_<layout>` 引用
   - 文档化 schema:[`themes/_schema.yaml`](${CLAUDE_PROJECT_DIR}/.claude/skills/pptx-deck/themes/_schema.yaml)
   - 老代码 `from themes._legacy.tech_blue import BRAND_PRIMARY` 仍可工作(compat shim re-export helpers + tech_blue.py)

3. **Layout plugin SSOT(P3-2)** —— [`${CLAUDE_PROJECT_DIR}/.claude/skills/pptx/helpers/<layout>.py`](${CLAUDE_PROJECT_DIR}/.claude/skills/pptx/helpers/) · 17 个 layout 类型的**theme-agnostic 标准实现**,通过 `@register_layout("<type>")` decorator 自动注册到全局 `LayoutRegistry`:
   - `from helpers import LayoutRegistry; fn = LayoutRegistry.get("cover")` → 取标准实现(`fn(prs, theme=mod, **fields)`)
   - 加新 layout = 写 `helpers/<name>.py` + `@register_layout("<name>")` 即可,**不改 helpers/__init__.py / build.py / themes/**
   - `helpers/__init__.py` 用 `pkgutil.iter_modules` 自动 import 所有非下划线开头模块,触发 decorator 副作用注册
   - **优先级**:`get_layout_func()` 先查 theme module(theme-specific override)→ 没有时 fall back 到 `LayoutRegistry.get()`(plugin 标准实现)
   - 添加新 layout 完整流程:[`docs/adding-new-layout.md`](${CLAUDE_PROJECT_DIR}/docs/adding-new-layout.md)

`${CLAUDE_PROJECT_DIR}/.claude/skills/pptx/layout.py` 提供**几何原语**(`Box` / `content_region` / `columns` / `rows` / `stack` / `split` / `inset`),主题无关,跟 `helpers/` 并列。

**改色 / 改字体规则**:
- 改单个 theme 的色板 / 字体 → 改对应 `themes/<name>.yaml`(P3-1 后的主流路径)· 完整步骤见 [`docs/writing-custom-themes.md`](${CLAUDE_PROJECT_DIR}/docs/writing-custom-themes.md)
- 改 helpers default token(影响 fallback / 没 yaml 的代码路径)→ 改 `helpers/__init__.py` 顶部常量
- 加新 layout type → 新建 `helpers/<name>.py` + `@register_layout("<name>")`(不动 helpers/__init__.py / build.py / themes/)· 完整流程见 [`docs/adding-new-layout.md`](${CLAUDE_PROJECT_DIR}/docs/adding-new-layout.md)
- markdown 文档里的 hex 是标注过的拷贝(`design-system.md` / `diagram/*.md`),色板变了要手动同步
- 规则禁的是重述**同一个**值,不是禁止新 theme(如未来的 `party_red.yaml`)定义自己色板

### Skill 文档就是产品

`SKILL.md` + 子 `.md` 是 Claude 运行时读的内容,**改它们就是改产品行为**;文档间用 `[[skill-name]]` 交叉引用。`${CLAUDE_PROJECT_DIR}/.claude/skills/pptx/scripts/office/` 从 Anthropic pptx skill **逐字 vendor,不要改**。

## 核心原则 —— 一图胜千文

表达**结构 / 流程 / 关系 / 数据对比**的内容应该变成**图**,不是一堵 bullet 文字墙。生成或审 deck 时,**主动用** `diagram` skill;**拿不准的时候,画**。落地在 [`diagram-planning.md`](${CLAUDE_PROJECT_DIR}/.claude/skills/pptx-deck/diagram-planning.md);默认 draw.io(精确配色 / 可控布局),Mermaid 作 sketch fallback,matplotlib 处理数据图。工具选择表见 [`diagram/SKILL.md`](${CLAUDE_PROJECT_DIR}/.claude/skills/diagram/SKILL.md)。

## 关键不变量

- **中文字体必须通过 lxml 写 `<a:ea>` + `<a:cs>`**(`helpers/__init__.py:set_font`)。python-pptx 的默认 `font.name` 只写 `<a:latin>`,中文文字跨平台会 fallback 成丑字体。**这是 #1 的产物破损源**
- **默认字体是 Microsoft YaHei**(项目的有意决定)。`PingFang SC` / `Heiti SC` 只在 fallback 链;macOS 需装 Microsoft YaHei 让 LibreOffice 渲染跟 Windows PowerPoint 一致
- **占位符字体用 `_fix_ph_font`,不是 `set_font`**。占位符从 slide master 继承 `<a:ea>`,run 级别 `set_font` 够不到
- **测试验证的是结构,不是视觉**。检查 shape 数量和字体属性 —— layout 可能渲染破了但测试照样通过;改完 layout / helper **必须**渲染 PNG 人审
- **`library/search.sh` 是唯一 RAG 入口**,所有 agent 检索两 kb 必须经它,不许直接读 `_rag/db.sqlite`
- **extractor 写 `.draft` 不直接入库**,`library/pptx-templates/items/<name>/{meta.yaml.draft, pages/*/meta.yaml.draft}` 必须经 `user_review_drafts` gate,用户审过主线程才跑 embed
- **extractor layout_type 17 enum + other 兜底**:`cover / toc / section_divider / summary / closing / quote / single_focus / cards / bullet_list / data / timeline / pyramid / venn / radial / process_flow / quadrant / comparison` + 兜底 `other`(必填 `needs_manual_review: true` + `layout_hint`);违反 Step 3.3 self-check `SCHEMA_VALIDATION_FAILED` hard_stop。enum 权威表见 [`library/pptx-templates/ingest_workflow.md`](${CLAUDE_PROJECT_DIR}/library/pptx-templates/ingest_workflow.md)
- **extractor Step 2.5 是 advisory 不是 hard_stop**:`unzip <p:sldId>` 数(declared) vs `ls *.png` 数(rendered)如实记 `extraction.{declared_pages, rendered_pages, discrepancy, discrepancy_resolution: pending}`,**严禁** agent 用"hidden/master slides"自圆其说;唯一 hard_stop 是 `rendered == 0`
- **Pyramid 收口 critic**:critic stage=cd Section A 7 项是 Pyramid 唯一判定点,author 不自检 / iloveppt-builder 不重跑
- **author/content.md 全程不可变**:iloveppt-builder Step 3 字数 / 视觉修复改 `deck_plan.json`,**不写 `.postbuild.md` 副本**;改写过头 → `review_needed_pages.needs_author_rewrite` 升 author
- **`<!-- layout: X -->` 强制 explicit**:每个 `## N.` 内容页必须紧跟 layout 注释;iloveppt-builder strict 1:1 解析,缺则 `hard_stop: missing_layout_directive`,不做结构推断
- **subagent 默认并行(≤5 实例)**:任何时候面对 ≥ 2 个**独立** subagent 工作(无 shared state / 无 sequential 依赖)→ **1 条消息里多 Agent tool call 并行起,最多 5 实例**;不要顺序串。可并行示例:多 Explore 扫不同模板范围 / author 改 content 跟 builder 改 deck_plan 不冲突 / 多 layout placeholder_map 各写各的。不可并行:hard gate(critic / audience)在 critical path 上;改同一文件的两 agent。反模式 ✗:用户提示"加大并行度"才并行(应该默认)。规则定义见 [pipeline protocol §0](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md#0-并行优先适用于所有派发场景)
- **改前备份 + 统一命名(过程文档 + 结果 .pptx 强制)**:每次改动 SSOT 必须新增版本,上版本备份,**不允许直接覆盖**(防 outline v1 被覆盖丢失再发生)。
  - **统一命名 schema**:`deck_v{N}_{kind}[.r{R}].{ext}`,kind 字典 `brief / outline / content / state / plan / critic_cd / visual_qa / audience` 不允许新增同义词(P2-3.2 后 critic_C / critic_D 合并为 critic_cd)
  - **两层版本**:Major iteration(章节增删 / SCQA 变 / >3 页连锁 → `deck_v{N+1}_*` 新文件平行)+ Minor revision(小改前 cp 到 `archive/<basename>.r{R}.<ext>`)
  - **反模式 ✗**:`deck_plan.json`(应 `deck_v1_plan.json`)/ `critic_report_C_r1.md`(应 `deck_v1_critic_cd.r1.md`;P2-3.2 合并后无 C/D 区分)/ `audience_report_tier1_r4.md`(应 `deck_v1_audience.r1.md`,sprint 信息进 state 不进文件名)/ `deck_v1_r2_backup.pptx`(应 `archive/deck_v1.r2.pptx`)
  - **Escape hatch**:typo / < 5 行 trivial bug,edit_history 标 `no_backup: true`
  - 完整 schema 表 + 目录树见 [pipeline protocol §0a](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md#0a-版本管理统一命名--改前备份)
- **brief.theme 支持 4 schema**(P3-9 跨模板组合):`str` / `list[str]` / `dict{primary, secondary[]}` / `dict{per_page{<n>: theme}}`。builder 用 `parse_theme()` → `ThemeSpec`,跨模板 deep-copy 时**字体 / 色板保 primary**,不混搭(避免一页里两套色)。`ThemeSpec.resolve_for_page(n)` 是唯一查询入口
- **brief.audience 是 list[persona]**(P2-13):audience agent 跑 **multi-persona strict-eval** — 每 persona 各打一遍,`page_score = min(per_persona_scores)`(取最低分,不平均),deck_score 同。persona 来自 `library/vocabularies/audience_personas.yaml` 的 7 enum,不允许自由填
- **critic verdict 自动算**(P2-1):每项 `severity` 是数字 0-3(blocking / major / minor / ok),LLM **不主观判** verdict,公式 `if any(severity==3): needs_revision; elif sum(severity>=2) > N: pass_with_notes; else: pass`。rubric 在 [`.claude/agents/critic-rubric.yaml`](${CLAUDE_PROJECT_DIR}/.claude/agents/critic-rubric.yaml) 是 SSOT,21 项 schema 改这里
- **audience 每页 12 项打分**(P2-2):每项 0-3 + evidence,`page_score = weighted_sum(per_item)` × persona weighting,deck_score = `min` over pages × persona。同 deck 跑 3 次方差应 < 0.5(quantization 治不稳定)
- **state.json 加 chapter_hashes**(P2-4 hot-reload):rework 时只重算 `chapter_hashes` 变化的章节,unchanged carry over previous verdict(critic / audience 不重跑)。helper 脚本 `library/_rag/scripts/compute_chapter_hashes.py`
- **deck_plan.json 是 derived artifact**(P2-5):`content.md` 是单源,`scripts/derive_plan.py` auto-derive deck_plan,builder **Step 0.5 verify** sha256 — derived 跟磁盘上的 deck_plan 不符 → `hard_stop: DERIVATION_MISMATCH`,逼用户改 content.md 不改 deck_plan
- **placeholder_map.shape_id 是主索引**(P0-7):`shape_id` 是 stable 主键,`tree_path` 是 fallback;源 .pptx 形状顺序变 → tree_path 失效但 shape_id 仍稳。self_check #11 对账 `placeholder_map[*].shape_id ⊆ source_pptx.shape_ids`,失配 → `SHA_DRIFT`
- **source_pptx_version + sha self_check**(P3-15):模板 ingest 时记 `source_pptx_version` + `source_pptx_sha256`,后续 .pptx 文件 sha 变 → `library/_rag/scripts/check_template_drift.py` 立即报 `SOURCE_PPTX_SHA_DRIFT`,逼用户重 ingest(避免 placeholder_map 跟源不一致悄悄渲染破)
- **DB 用 SQLite WAL mode**(P3-6):`PRAGMA journal_mode=WAL` + `busy_timeout=10s` + `synchronous=NORMAL` — `parallel_embed.sh` 让 text + image 两进程同时写 db.sqlite,WAL 才能多 reader / 单 writer 并发。运行时生成 `db.sqlite-wal` / `db.sqlite-shm` 辅助文件(不入 git)
- **第三方 SaaS 工具品牌引用 0**:全 repo 不允许出现已下架 SaaS 工具品牌名(早期 PoC 残留 · 已 cleanup 90 文件) · PR 引入 → CI 拦
- **subagent 不直接派 Haiku helper**(P3-7):`iloveppt-self-check` / `iloveppt-yaml-fixer` 只能**主线程 dispatch** · 任何 subagent(brainstorm / author / critic / builder / audience / extractor)起 helper = 反模式(subagent 起 subagent 在 Claude Code 里不工作)。主流水线 6 agent 内部要 self_check / yaml fix → 自己跑 Python 脚本,出问题在 return yaml 上报主线程,主线程再 dispatch helper
- **图片资产 reproducibility 强制**:**任何**引入到 deck 的图片(生成 / 下载 / 引用 / 提取)都必须能 traceback 到 reproducible 源 —— 只有 PNG 等于让用户重画。配对规则按引入方式区分:
  - **生成类**(author Stage D matplotlib / draw.io / mermaid):`.py` / `.drawio` / `.mmd` 源文件跟 PNG 同目录、同名前缀 — `author/charts/X.{py,drawio,mmd}` + `author/charts/X.png`
  - **下载类**(builder Step 4 iconify / Unsplash):落 `<name>.source.yaml` 记 URL / query / icon_name / photo_id / 颜色等参数,跟 PNG 同目录;iconify SVG 原文件也保留
  - **引用类**(builder Step 4 RAG fallback / brand_assets):source.yaml 记 library item path / RAG query / 用户原 path
  - **提取类**(extractor render_pages.py):preview.png 源 = `_source/<name>.pptx`(已保留)
  - **渲染类**(builder final 51 张 page-NN.jpg):源 = `deck_v1.pptx`(已保留)
  - return yaml 强制配对字段:author `charts_generated[{png, source, tool}]`、builder `visual_edits[{asset, source, tool}]`,缺 source 视为 bug。规则定义见 [`.claude/agents/iloveppt-author.md` Stage D](${CLAUDE_PROJECT_DIR}/.claude/agents/iloveppt-author.md) + [`.claude/agents/iloveppt-builder.md` Step 4](${CLAUDE_PROJECT_DIR}/.claude/agents/iloveppt-builder.md) + [`.claude/skills/diagram/SKILL.md` §源文件归档](${CLAUDE_PROJECT_DIR}/.claude/skills/diagram/SKILL.md)

## 工程脚本

按目录分:`library/_rag/`(RAG / 模板治理)+ `scripts/`(deck 级 / 仓库级)。详细 usage 见各脚本 `--help` 或同目录 README。

### `library/_rag/`(RAG / 模板治理)

| 脚本 | 用途 | sprint |
|---|---|---|
| `bench.py` | 7 query golden bench · sprint 完成跑 `--label <name>` 拿数据 | P0-3 |
| `scripts/parallel_embed.sh` | text+image 两进程并行 embed · ingest 10min → 2min | P1-7 |
| `scripts/track_cost.py` | per-deck token cost 聚合 · 写 `state.json.tokens_by_agent[]` | P1-8 |
| `scripts/rotate_api_key.py` | API key 轮换 · 安全 manager | P3-18 |
| `scripts/redact.py` | query log 脱敏 · 邮箱 / 手机号 / 钱数 redact | P3-21 |
| `scripts/detect_watermark.py` | 模板入库 detect 第三方水印 + 版权 LOGO | P3-22 |
| `scripts/check_template_drift.py` | 模板 sha drift sweep · `SOURCE_PPTX_SHA_DRIFT` 拦 | P3-15 |
| `scripts/feedback_stats.py` | RAG 反馈月度 review · score < 7 pattern 降权 | P3-5 |
| `scripts/query_cache.py` | iconify / Unsplash query fuzzy match 缓存 | P2-10 |
| `scripts/compute_chapter_hashes.py` | hot-reload helper · 给 rework 决定哪些章节重算 | P2-4 |
| `scripts/ablation_hybrid_weights.py` | hybrid 权重 ablation · 改 default 前必跑 | P2-9 |
| `scripts/red_line_check.py` | red_line_words fuzzy + 拼音 fallback | P1-10 |

### `scripts/`(deck 级 / 仓库级)

| 脚本 | 用途 | sprint |
|---|---|---|
| `derive_plan.py` | `content.md` → `deck_plan.json` auto-derive · builder Step 0.5 verify | P2-5 |
| `dashboard.py` | 跨 deck 聚合 · token / rework / audience / layout failure rate | P2-11/12 |
| `new_deck.py` | `--skeleton <id>` scaffold 新 deck(6 deck-skeleton) | P3-8 |
| `clip_chapter.py` | 跨 deck 章节复制 · 拷贝 content + deck_plan slice | P3-14 |
| `deck_diff.py` | 跨 deck 语义 diff(4 类:章节增删 / SCQA / pattern / visual) | P3-13 |
| `gitignore_lint.py` | 多 .gitignore 一致性自动校(5 类检查) | P3-20 |
| `install-hooks.sh` | 启用 pre-commit · 扫敏感数据 / `_assets/raw` 强警告 | P3-19 |

## 约定

- **`${CLAUDE_PROJECT_DIR}/...`** 是 [Claude Code 标准环境变量](https://code.claude.com/docs/en/hooks.md),指 iLovePPT 仓库根(也是 cwd)
- **Commit**:conventional commits + scope:`feat(pptx-deck):` / `fix(pptx):` / `docs(diagram):` / `refactor:` / `test(pptx):` / `chore:`
- **测试 import**:`pyproject.toml` 的 `pythonpath` 已配 `.claude/skills/pptx` + `.claude/skills/pptx-deck`,直接 import `helpers` / `layout` / `themes.tech_blue` / `build`,无需 `sys.path` hack(非 test 模块保留幂等 `sys.path.insert` 方便直接跑)
- **协议权威**:agent 派发 / handoff 行为以 `.claude/pipeline-protocol.md` 为准
