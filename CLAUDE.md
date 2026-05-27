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

### Agent 流水线(Hybrid:1 team + 5 subagent · 含旁路 extractor)

`${CLAUDE_PROJECT_DIR}/.claude/agents/` 是项目的运行时流水线,**Hybrid 架构**:

- **Phase A (team 模式)**:brainstorm 用 `TeamCreate` 持续窗口,多轮 SendMessage 跟用户聊收 brief。
- **Phase B (subagent 模式)**:author / critic / iloveppt-builder / audience / template-extractor 用 `Task` 工具调用,每次跑完 return yaml(主线程 parse 决定下一步)。

**模型**:6 个 agent 全用 **opus**(team 跨阶段一致性 + 整条流水线的深度判断 / 多职责 / 多轮对话 / 视觉认知都需要高质量推理)。

| agent | 角色 | 调用方式 | model |
|---|---|---|---|
| `iloveppt-brainstorm` | Stage A-B:多轮对话收 brief + 素材 + **Step 3.6 brief self-audit 5 项**(P2-3.1 后 critic Stage B 已并入),出 brief.md 让用户确认 | TeamCreate(team) | opus |
| `iloveppt-author` | Stage C-D:出 outline.md(章节骨架)→ 自走 Stage D 拓写 content.md(P2-3.2 后无中间 critic gate)— 两次独立 Task | Task | opus |
| `iloveppt-critic` | **partner 评审员**:stage=cd 单次合审 14 项 checklist 底线 + 5 维度判断性评审(论据强度 / 节奏 / 措辞 / 平衡 / **pattern 适配性**),P2-3.2 后取代原 Stage C/D 双 gate | Task | opus |
| `iloveppt-builder` | Stage E:**机械构建 .pptx + 机械视觉 QA(Step 0-3)+ 主动加视觉(Step 4)**,iconify / Unsplash / brand / **RAG patterns** 四路降级 | Task | opus |
| `iloveppt-audience` | **Step 0.0 spot-check**(P2-3.3 后并入,placeholder grep / chart source / 5+ PNG 破损 detect / red_line grep)+ 模拟目标受众读 deck 评分(9 分硬阈值);反馈三类分流(needs_author_rewrite / needs_visual_redo / needs_theme_fix) | Task | opus |
| `iloveppt-template-extractor` | 旁路:用户给 .pptx 模板时 ingest 到 `library/pptx-templates/items/<name>/`(复制 _source + render_pages.py 渲染每页 + 起草双层 yaml + Step 3.3 self-check 拦 enum/字段/YAML 语法),`user_review_drafts` gate → 用户审 → 主线程 embed | Task | opus |

**深读**:派发 / handoff / gate / 退出条件 — [`.claude/pipeline-protocol.md`](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md)(AI 运行时活协议);系统怎么跑 — [`docs/agent-internals.zh.md`](${CLAUDE_PROJECT_DIR}/docs/agent-internals.zh.md)。

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

### build.py 是纯机械构建器

`build.py` 输入 `deck_plan.json` 输出 `.pptx` + PNG,**不含占位函数、不调 LLM**。接缝是 `deck_plan.json`:`{theme, output, slides: [{layout, ...fields}]}` — Claude 产出,`build.py` 消费。

智能步骤是 Claude 按文档化流程执行,**不是 Python 函数**:
- **内容拓写**(brief → per-page deck_plan.json) → 记录在 `content-writing.md`
- **视觉 QA**(读 PNG → 对照 17 项 checklist → 改 deck_plan → 重跑) → 记录在 `visual-qa.md`

提升生成**质量**改 prompt 文档(`content-writing.md` / `visual-qa.md`),**不要**改 `build.py`。

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
- 改单个 theme 的色板 / 字体 → 改对应 `themes/<name>.yaml`(P3-1 后的主流路径)
- 改 helpers default token(影响 fallback / 没 yaml 的代码路径)→ 改 `helpers/__init__.py` 顶部常量
- 加新 layout type → 新建 `helpers/<name>.py` + `@register_layout("<name>")`(不动 helpers/__init__.py / build.py / themes/)
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
- **图片资产 reproducibility 强制**:**任何**引入到 deck 的图片(生成 / 下载 / 引用 / 提取)都必须能 traceback 到 reproducible 源 —— 只有 PNG 等于让用户重画。配对规则按引入方式区分:
  - **生成类**(author Stage D matplotlib / draw.io / mermaid):`.py` / `.drawio` / `.mmd` 源文件跟 PNG 同目录、同名前缀 — `author/charts/X.{py,drawio,mmd}` + `author/charts/X.png`
  - **下载类**(builder Step 4 iconify / Unsplash):落 `<name>.source.yaml` 记 URL / query / icon_name / photo_id / 颜色等参数,跟 PNG 同目录;iconify SVG 原文件也保留
  - **引用类**(builder Step 4 RAG fallback / brand_assets):source.yaml 记 library item path / RAG query / 用户原 path
  - **提取类**(extractor render_pages.py):preview.png 源 = `_source/<name>.pptx`(已保留)
  - **渲染类**(builder final 51 张 page-NN.jpg):源 = `deck_v1.pptx`(已保留)
  - return yaml 强制配对字段:author `charts_generated[{png, source, tool}]`、builder `visual_edits[{asset, source, tool}]`,缺 source 视为 bug。规则定义见 [`.claude/agents/iloveppt-author.md` Stage D](${CLAUDE_PROJECT_DIR}/.claude/agents/iloveppt-author.md) + [`.claude/agents/iloveppt-builder.md` Step 4](${CLAUDE_PROJECT_DIR}/.claude/agents/iloveppt-builder.md) + [`.claude/skills/diagram/SKILL.md` §源文件归档](${CLAUDE_PROJECT_DIR}/.claude/skills/diagram/SKILL.md)

## 约定

- **`${CLAUDE_PROJECT_DIR}/...`** 是 [Claude Code 标准环境变量](https://code.claude.com/docs/en/hooks.md),指 iLovePPT 仓库根(也是 cwd)
- **Commit**:conventional commits + scope:`feat(pptx-deck):` / `fix(pptx):` / `docs(diagram):` / `refactor:` / `test(pptx):` / `chore:`
- **测试 import**:`pyproject.toml` 的 `pythonpath` 已配 `.claude/skills/pptx` + `.claude/skills/pptx-deck`,直接 import `helpers` / `layout` / `themes.tech_blue` / `build`,无需 `sys.path` hack(非 test 模块保留幂等 `sys.path.insert` 方便直接跑)
- **协议权威**:agent 派发 / handoff 行为以 `.claude/pipeline-protocol.md` 为准
