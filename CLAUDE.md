# CLAUDE.md

本文件为 Claude Code(claude.ai/code)在本仓库工作时提供指引。

**这是导航文件** —— 高层架构 + 不变量在此;具体的协议 / handoff / gate 规则在链接到的 spec 里。

## 仓库是什么

iLovePPT 是一个 **agent team 帮你写 PPT 的开源工具**。clone 本仓库后,在仓库根目录跟 Claude Code 说"做 PPT",**5 个 agent + 1 旁路**(brainstorm → author → critic → iloveppt-builder → audience + extractor)接力把你的想法变成完整 `.pptx`。

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
| `iloveppt-brainstorm` | Stage A-B:多轮对话收 brief + 素材,出 brief.md 让用户确认 | TeamCreate(team) | opus |
| `iloveppt-author` | Stage C-D:出 outline.md(章节骨架)+ 拓写 content.md(全文)— 两次独立 Task | Task | opus |
| `iloveppt-critic` | **partner 评审员**:14 项 checklist 底线 + 5 维度判断性评审(论据强度 / 节奏 / 措辞 / 平衡 / **pattern 适配性**),Stage C/D 各跑一次 | Task | opus |
| `iloveppt-builder` | Stage E:**机械构建 .pptx + 机械视觉 QA(Step 0-3)+ 主动加视觉(Step 4)**,iconify / Unsplash / brand / **RAG patterns** 四路降级 | Task | opus |
| `iloveppt-audience` | 模拟目标受众读 deck 评分(9 分硬阈值);反馈三类分流(needs_author_rewrite / needs_visual_redo / needs_theme_fix) | Task | opus |
| `iloveppt-template-extractor` | 旁路:用户给 .pptx 模板时 ingest 到 `library/pptx-templates/items/<name>/`(复制 _source + render_pages.py 渲染每页 + 起草双层 yaml + Step 3.3 self-check 拦 enum/字段/YAML 语法),`user_review_drafts` gate → 用户审 → 主线程 embed | Task | opus |

**深读**:派发 / handoff / gate / 退出条件 — [`.claude/pipeline-protocol.md`](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md)(AI 运行时活协议);系统怎么跑 — [`docs/agent-internals.zh.md`](${CLAUDE_PROJECT_DIR}/docs/agent-internals.zh.md)。

### Library / 知识库(RAG)

[`library/`](${CLAUDE_PROJECT_DIR}/library/) —— 双知识库 + 单 DB + 顶层 router:

| kb | 单位 | 调用场景 |
|---|---|---|
| `library/visual-patterns/` | 跨模板视觉模式(timeline / pdca / funnel / ...) | author 拓写 / iloveppt-builder Step 4 加视觉 |
| `library/pptx-templates/` | 用户预置 .pptx 模板 + 拆出的每页 | brainstorm 列模板 / author 选页 / iloveppt-builder 渲染参考 |

**唯一检索入口** `library/search.sh`(`--preferred-template` 优先 + visual-patterns fallback;hosted multimodal embedding 阿里云 tongyi-embedding-vision-plus dim 1152):

```bash
library/search.sh --kb pptx-templates --type template --query "<主题>" --top-k 5  # 列模板
library/search.sh --query "<本页意图>" --preferred-template <brief.theme> --type page  # author 选页
```

`items/<id>/{meta.yaml, preview.png}` 入 git;`_rag/{db.sqlite, .venv, .env}` / `*/_source/*.pptx` 不入。

### 主线程派发规则

"做 PPT" 意图 → 先 `TeamCreate(brainstorm)` 跑 Phase A;`dispatch_author` 后关 team,转 `Task` 依次调 author/critic/iloveppt-builder/audience(**不要**自己写 brief / content / 跑视觉 QA)。改仓库代码(helpers.py / themes / build.py / tests / agent prompts / 协议)时 → 主线程直接干。完整派发表:[pipeline protocol §1](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md#1-主线程派发表)。

**Pattern 注释 + cherry-pick**:
- **前缀强制**:author 写 content.md 的 pattern 注释必须带 kb 前缀 — `<!-- pattern: vp:<id> -->`(visual-patterns)或 `<!-- pattern: tpl:<theme>__<NN-slug> -->`(pptx-templates)。iloveppt-builder Step 2 按前缀路由查对应 kb,**无前缀 hard_stop**
- **cherry-pick gate**:critic / iloveppt-builder / audience return 含 `suggested_alternative_pattern(s)` → 主线程展示用户决定,不自决;用户答"改" → Task author rework(`user_response.accept_alternative_pattern: {page, suggest}`);audience 阶段触发改 → rework 后必须重派 critic D + audience

完整规则见 [pipeline protocol](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md)。

### 三 skill 分层

```
pptx-deck  ── 编排者:brief.md → outline.md → content.md → deck_plan.json → 完整 .pptx
   ├── 调用 → pptx      (helpers.py / office 脚本 / render 流水线)
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

### SSOT 标准 —— helpers.py 是唯一真实源

`${CLAUDE_PROJECT_DIR}/.claude/skills/pptx/helpers.py` 是权威源,下游只能引用或扩展,**不允许重定义**:

1. **底层 pptx 原语** —— 字体/形状/表格(`set_font` / `_fix_ph_font` / `card` / `bullets` / `table_modern` / `section_header`)。Theme 在此基础上写 `make_*` layout 函数,绝不复制字体/形状逻辑
2. **设计 token** —— `FONT_CN` / `FONT_NUM` / `BRAND_PRIMARY` / `BRAND_DARK` / `BRAND_TINT` / `ACCENT` / 灰阶 / `SLIDE_W` / `SLIDE_H`。`tech_blue.py` 用 alias(`PRIMARY = H.BRAND_PRIMARY`),不重定义;`build.py` 用 `H.SLIDE_W/H` 不写死 `Inches(...)`

`${CLAUDE_PROJECT_DIR}/.claude/skills/pptx/layout.py` 提供**几何原语**(`Box` / `content_region` / `columns` / `rows` / `stack` / `split` / `inset`),主题无关,跟 `helpers.py` 并列。

改色 / 改字体 = **只**改 `helpers.py` 一处。markdown 文档里的 hex 是标注过的拷贝(`design-system.md` / `diagram/*.md`),色板变了要手动同步。规则禁的是重述**同一个**值,不是禁止新 theme(如未来的 `party_red.py`)定义自己色板。

### Skill 文档就是产品

`SKILL.md` + 子 `.md` 是 Claude 运行时读的内容,**改它们就是改产品行为**;文档间用 `[[skill-name]]` 交叉引用。`${CLAUDE_PROJECT_DIR}/.claude/skills/pptx/scripts/office/` 从 Anthropic pptx skill **逐字 vendor,不要改**。

## 核心原则 —— 一图胜千文

表达**结构 / 流程 / 关系 / 数据对比**的内容应该变成**图**,不是一堵 bullet 文字墙。生成或审 deck 时,**主动用** `diagram` skill;**拿不准的时候,画**。落地在 [`diagram-planning.md`](${CLAUDE_PROJECT_DIR}/.claude/skills/pptx-deck/diagram-planning.md);默认 draw.io(精确配色 / 可控布局),Mermaid 作 sketch fallback,matplotlib 处理数据图。工具选择表见 [`diagram/SKILL.md`](${CLAUDE_PROJECT_DIR}/.claude/skills/diagram/SKILL.md)。

## 关键不变量

- **中文字体必须通过 lxml 写 `<a:ea>` + `<a:cs>`**(`helpers.py:set_font`)。python-pptx 的默认 `font.name` 只写 `<a:latin>`,中文文字跨平台会 fallback 成丑字体。**这是 #1 的产物破损源**
- **默认字体是 Microsoft YaHei**(项目的有意决定)。`PingFang SC` / `Heiti SC` 只在 fallback 链;macOS 需装 Microsoft YaHei 让 LibreOffice 渲染跟 Windows PowerPoint 一致
- **占位符字体用 `_fix_ph_font`,不是 `set_font`**。占位符从 slide master 继承 `<a:ea>`,run 级别 `set_font` 够不到
- **测试验证的是结构,不是视觉**。检查 shape 数量和字体属性 —— layout 可能渲染破了但测试照样通过;改完 layout / helper **必须**渲染 PNG 人审
- **`library/search.sh` 是唯一 RAG 入口**,所有 agent 检索两 kb 必须经它,不许直接读 `_rag/db.sqlite`
- **extractor 写 `.draft` 不直接入库**,`library/pptx-templates/items/<name>/{meta.yaml.draft, pages/*/meta.yaml.draft}` 必须经 `user_review_drafts` gate,用户审过主线程才跑 embed
- **extractor layout_type 17 enum + other 兜底**:`cover / toc / section_divider / summary / closing / quote / single_focus / cards / bullet_list / data / timeline / pyramid / venn / radial / process_flow / quadrant / comparison` + 兜底 `other`(必填 `needs_manual_review: true` + `layout_hint`);违反 Step 3.3 self-check `SCHEMA_VALIDATION_FAILED` hard_stop。enum 权威表见 [`library/pptx-templates/ingest_workflow.md`](${CLAUDE_PROJECT_DIR}/library/pptx-templates/ingest_workflow.md)
- **extractor Step 2.5 是 advisory 不是 hard_stop**:`unzip <p:sldId>` 数(declared) vs `ls *.png` 数(rendered)如实记 `extraction.{declared_pages, rendered_pages, discrepancy, discrepancy_resolution: pending}`,**严禁** agent 用"hidden/master slides"自圆其说;唯一 hard_stop 是 `rendered == 0`
- **Pyramid 收口 critic**:critic Section A 7 项是 Pyramid 唯一判定点,author 不自检 / iloveppt-builder 不重跑
- **author/content.md 全程不可变**:iloveppt-builder Step 3 字数 / 视觉修复改 `deck_plan.json`,**不写 `.postbuild.md` 副本**;改写过头 → `review_needed_pages.needs_author_rewrite` 升 author
- **`<!-- layout: X -->` 强制 explicit**:每个 `## N.` 内容页必须紧跟 layout 注释;iloveppt-builder strict 1:1 解析,缺则 `hard_stop: missing_layout_directive`,不做结构推断

## 约定

- **`${CLAUDE_PROJECT_DIR}/...`** 是 [Claude Code 标准环境变量](https://code.claude.com/docs/en/hooks.md),指 iLovePPT 仓库根(也是 cwd)
- **Commit**:conventional commits + scope:`feat(pptx-deck):` / `fix(pptx):` / `docs(diagram):` / `refactor:` / `test(pptx):` / `chore:`
- **测试 import**:`pyproject.toml` 的 `pythonpath` 已配 `.claude/skills/pptx` + `.claude/skills/pptx-deck`,直接 import `helpers` / `layout` / `themes.tech_blue` / `build`,无需 `sys.path` hack(非 test 模块保留幂等 `sys.path.insert` 方便直接跑)
- **协议权威**:agent 派发 / handoff 行为以 `.claude/pipeline-protocol.md` 为准
