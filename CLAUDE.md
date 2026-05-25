# CLAUDE.md

本文件为 Claude Code(claude.ai/code)在本仓库工作时提供指引。

**这是导航文件** —— 高层架构 + 不变量在此;具体的协议 / handoff / gate 规则在链接到的 spec 里。

## 仓库是什么

iLovePPT 是一个 **agent team 帮你写 PPT 的开源工具**。clone 本仓库后,在仓库根目录跟 Claude Code 说"做 PPT",**5 个 agent + 1 旁路**(brainstorm → author → critic → iloveppt → audience + extractor)接力把你的想法变成完整 `.pptx`。

仓库本身就是产品:

- `.claude/agents/` —— 5 个 agent 定义,Claude Code 启动时自动加载
- `.claude/skills/` —— 3 个 skill 实现(`pptx-deck` / `pptx` / `diagram`),Claude Code 自动加载,可直接 `Skill(skill="pptx-deck")` 调用
- `.claude/pipeline-protocol.md` —— agent 之间的派发 / handoff / gate 协议
- `.claude/settings.json` —— 框架配置(hooks / permissions / env)

## Quick Start

```bash
# 1. clone + 装依赖
git clone <repo-url> iLovePPT
cd iLovePPT
pip install -e ".[diagram,dev]"

# 2. 检查外部依赖(python-pptx / soffice / pdftoppm / 中文字体)
bash .claude/skills/pptx/scripts/check_deps.sh

# 3. 跑测试确认环境 OK
python3 -m pytest tests/ -q             # 应 72 passed

# 4. 在仓库根目录打开 Claude Code,跟主线程说:
#    "做个 15 分钟的 deck,给 CTO 看 AI 4A 评审办法的提案"
# 主线程会按 pipeline-protocol 派 agent team,产出在 decks/<slug>/builder/deck_v1.pptx
```

也可以**绕过 agent team 手动跑**(已有 `deck_plan.json` 的场景):

```bash
python3 .claude/skills/pptx-deck/build.py path/to/deck_plan.json
```

## 常用命令

```bash
# 跑全部测试(72 个;pythonpath 由 pyproject.toml 自动配)
python3 -m pytest tests/ -v

# 跑单个测试
python3 -m pytest tests/pptx/test_helpers.py::test_set_font_writes_ea_typeface -v

# 检查外部依赖(python-pptx / soffice / pdftoppm / 字体)
bash .claude/skills/pptx/scripts/check_deps.sh

# 端到端:从 deck_plan.json 构建 deck
python3 .claude/skills/pptx-deck/build.py deck_plan.json
# 可选:跳过 PNG 渲染
python3 .claude/skills/pptx-deck/build.py deck_plan.json --no-render

# 烟测(跑 helper + render 流水线)
python3 .claude/skills/pptx/examples/minimal_deck.py     # → /tmp/iloveppt_minimal.pptx
bash .claude/skills/diagram/examples/render.sh           # → .claude/skills/diagram/examples/minimal.png

# 渲染 .pptx 做视觉验证
soffice --headless --convert-to pdf <file>.pptx --outdir /tmp/
pdftoppm -jpeg -r 120 /tmp/<file>.pdf /tmp/slide
```

无 build 步骤、无 linter 配置。

## 架构

### Agent 流水线(Hybrid:1 team + 5 subagent + 1 旁路 subagent)

`${CLAUDE_PROJECT_DIR}/.claude/agents/` 是项目的运行时流水线,**Hybrid 架构**:

- **Phase A (team 模式)**:brainstorm 用 `TeamCreate` 持续窗口,多轮 SendMessage 跟用户聊收 brief。
- **Phase B (subagent 模式)**:author / critic / iloveppt / audience / template-extractor 用 `Task` 工具调用,每次跑完 return yaml(主线程 parse 决定下一步)。

**模型分层**:critic / iloveppt 用 opus(深度推理 / 多职责),author / brainstorm / audience 用 sonnet,template-extractor 用 haiku。

| agent | 角色 | 调用方式 | model |
|---|---|---|---|
| `iloveppt-brainstorm` | Stage A-B:多轮对话收 brief + 素材,出 brief.md 让用户确认 | TeamCreate(team) | sonnet |
| `iloveppt-author` | Stage C-D:出 outline.md(章节骨架)+ 拓写 content.md(全文)— 两次独立 Task | Task | sonnet |
| `iloveppt-critic` | **partner 评审员**:14 项 checklist 底线 + 4 维度判断性评审(论据强度 / 节奏 / 措辞 / 平衡),Stage C/D 各跑一次 | Task | opus |
| `iloveppt` | Stage E:**机械构建 .pptx + 机械视觉 QA(Step 0-3)+ 主动加视觉(Step 4)**,iconify / Unsplash / brand 三路降级 | Task | opus |
| `iloveppt-audience` | 模拟目标受众读 deck 评分(9 分硬阈值);反馈三类分流(needs_author_rewrite / needs_visual_redo / needs_theme_fix) | Task | sonnet |
| `iloveppt-template-extractor` | 旁路:用户给 .pptx 模板时摄入 4 级 token | Task | haiku |

阶段切换信号:brainstorm SendMessage 返回 `next_action: dispatch_author` → 主线程**立即关闭 brainstorm team** → `Task(iloveppt-author, stage=C)` 进入 Phase B。

👉 **运行时流水线协议(派发顺序 / handoff / gate / 退出条件)** —— AI 运行时活协议:[`${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md`](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md)

👉 **agent 工作原理(给人看,系统怎么跑)**:[`${CLAUDE_PROJECT_DIR}/docs/agent-internals.zh.md`](${CLAUDE_PROJECT_DIR}/docs/agent-internals.zh.md)

👉 **Visual Patterns 知识库**:[`${CLAUDE_PROJECT_DIR}/library/visual-patterns/README.md`](${CLAUDE_PROJECT_DIR}/library/visual-patterns/README.md) —— hosted multimodal RAG(阿里云 tongyi-embedding-vision-plus,dim 1152,文本+图像同 API)+ INDEX.md 双路检索 + 3 search mode(text/image/hybrid)。agent 拓写 / 加视觉时可查 library 找最匹配 pattern

### 主线程派发规则(一句话总结)

用户表达"做 PPT"意图时 → 主线程**必须**先 `TeamCreate(brainstorm)` 跑 Phase A(收 brief);brainstorm `dispatch_author` 后**关闭 team**,转 `Task` 依次调 author/critic/iloveppt/audience 跑 Phase B(**不要**自己写 brief / 写 content / 跑视觉 QA)。改仓库代码(helpers.py / themes / build.py / tests / agent prompts / 协议文档)时 → 主线程直接干(跨文件一致性)。

完整派发表 + 理由:见 [pipeline protocol §1](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md#1-主线程派发表)。

**Pattern cherry-pick gate**(2026-05-25 新增):任何 critic / iloveppt / audience subagent return yaml 含 `suggested_alternative_pattern(s)` 字段 → 主线程**必须**展示给用户决定,不允许自决。用户答"改" → Task author rework(user_response 含 `accept_alternative_pattern: {page, suggest}`);用户答"不改" → 继续派下一棒。若 audience 阶段触发改 → author rework 后必须重派 critic D + audience。完整流程见 [pipeline protocol §3.3](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md#33-gate-规则)。

### 三 skill 分层

```
pptx-deck  ── 编排者:brief.md → outline.md → content.md → deck_plan.json → 完整 .pptx
   ├── 调用 → pptx      (helpers.py / office 脚本 / render 流水线)
   └── 调用 → diagram   (draw.io / mermaid / matplotlib → PNG)
pptx       ── 底层 .pptx 读写;也可独立使用
diagram    ── 图表生成;也可独立使用
```

### build.py 是纯机械构建器,智能步骤由 Claude 按文档化流程执行

最重要的事:`build.py` 是**诚实的机械构建器** —— 输入 `deck_plan.json`,输出 `.pptx` + PNG。**不含任何占位函数、不调任何 LLM**。

- **接缝是 `deck_plan.json`**:`{theme, output, slides: [{layout, ...fields}]}`。Claude 产出它;`build.py` 消费它。
- **内容拓写**(brief → 完整 per-page `deck_plan.json`)是 Claude 执行的过程,记录在 `content-writing.md`,**不是 Python 函数**。
- **视觉 QA**(读渲染 PNG → 对照 17 项 checklist 打分 → 改 `deck_plan.json` → 重跑 `build.py`)是 Claude 执行的过程,记录在 `visual-qa.md`,**不是 Python 函数**。

提升生成**质量**时,改 prompt 文档(`content-writing.md` / `visual-qa.md`),**不要**改 `build.py`。

### SSOT 标准 —— helpers.py 是唯一真实源

`${CLAUDE_PROJECT_DIR}/.claude/skills/pptx/helpers.py` 是两件事的权威定义,下游只能引用或扩展,**不允许重新定义**:

1. **底层 pptx 操作** —— 所有字体/形状/表格原语(`set_font` / `_fix_ph_font` / `card` / `bullets` / `table_modern` / `section_header` 等)。Theme 模块在此基础上写 `make_*` layout 函数,**绝不**在 theme 里复制字体/形状逻辑。
2. **设计 token** —— 字体(`FONT_CN` / `FONT_NUM`)、品牌色(`BRAND_PRIMARY` / `BRAND_DARK` / `BRAND_TINT` / `ACCENT`)、灰阶、slide 尺寸(`SLIDE_W` / `SLIDE_H`)。`tech_blue.py` **不**重新定义这些 —— 而是 alias(`PRIMARY = H.BRAND_PRIMARY`、`FONT_HEADER = H.FONT_CN`)。`build.py` 用 `H.SLIDE_W/H`,不写死 `Inches(...)`。

`${CLAUDE_PROJECT_DIR}/.claude/skills/pptx/layout.py` 提供**几何原语**(`Box` / `content_region` / `full_region` / `columns` / `rows` / `stack` / `split` / `inset`),主题无关,跟 `helpers.py` 并列。Theme 的 `make_*` 函数用这些算元素位置,不重复几何数学。

改动的连带后果:
- 改色或改字体 = **只**改 `helpers.py` 一处,会传到 theme 和所有 helper 默认值。
- markdown 文档不能 import,所以 `design-system.md` / `diagram/*.md` 里的 hex 值是**标注过的拷贝**,引用 `helpers.py` 为权威,色板变了要手动同步。
- 真正不同的 theme(例如未来的 `party_red.py`)可以定义自己的色板 —— 那是新的 SSOT 范围,**不是**重复。规则禁的是重述**同一个**值,不是禁止不同 theme。

### Skill 文档就是产品

`SKILL.md` + 子 `.md` 文件**不是**辅助文档 —— 它们是 Claude 在运行时读的内容,决定怎么生成 deck。改它们就是改产品行为。文档之间用 `[[skill-name]]` 语法交叉引用。

`${CLAUDE_PROJECT_DIR}/.claude/skills/pptx/scripts/office/` 从 Anthropic 的 pptx skill **逐字 vendor 过来,不要改动**。

## 核心原则 —— 一图胜千文

表达**结构、流程、关系、数据对比**的内容应该变成**图**,**不是**一堵 bullet 文字墙。生成或审 deck 时,**主动用** AI 画图能力(`diagram` skill)处理这类内容;**拿不准的时候,画**。这条原则在工作流 Step 3(Claude 执行的图层规划步骤)落地,文档在 `${CLAUDE_PROJECT_DIR}/.claude/skills/pptx-deck/diagram-planning.md`。任何改动生成行为都应保留这个"偏视觉"的倾向。

结构化图(流程图、架构、矩阵、决策树、关系图)默认走 **draw.io** —— 颜色精确、布局可控、跨图视觉一致。Mermaid 只是快速 sketch 的 fallback;matplotlib 处理数据图。工具选择表见 `${CLAUDE_PROJECT_DIR}/.claude/skills/diagram/SKILL.md`。

## 关键不变量

- **中文字体必须通过 lxml 写 `<a:ea>` + `<a:cs>`**(`helpers.py:set_font`)。python-pptx 的默认 `font.name` 只写 `<a:latin>`,中文文字跨平台会 fallback 成丑字体。**这是 #1 的产物破损源**。
- **默认字体是 Microsoft YaHei**(项目的有意决定)。`PingFang SC` / `Heiti SC` 只在 fallback 链里出现,**绝不**作为默认。macOS 上需要装 Microsoft YaHei 才能让 LibreOffice 渲染跟 Windows PowerPoint 一致。
- **占位符字体要用 `_fix_ph_font`,不是 `set_font`**。占位符从 slide master 继承 `<a:ea>`,run 级别的 `set_font` 够不到那一层。
- **测试验证的是结构,不是视觉**。检查的是 shape 数量和字体属性 —— layout 可能渲染破了但测试照样通过。改完 layout / helper 之后,**必须**渲染 PNG 人审。

## 约定

- **路径表示**:文档里的 `${CLAUDE_PROJECT_DIR}/...` 是 [Claude Code 标准环境变量](https://code.claude.com/docs/en/hooks.md),指 **iLovePPT 仓库根**(也是你的 cwd —— agent team 在仓库内跑,无双场景之分)。文档当字面用即可。
- Commit message 用 conventional commits + scope:`feat(pptx-deck):` / `fix(pptx):` / `docs(diagram):` / `refactor:` / `test(pptx):` / `chore:`。
- `pyproject.toml` 设了 `pythonpath = [".claude/skills/pptx", ".claude/skills/pptx-deck"]`,测试直接 import `helpers` / `layout` / `themes.tech_blue` / `build`,**无需** `sys.path` hack。非 test 模块保留幂等的 `sys.path.insert`,方便脚本直接跑。
- 流水线协议(`.claude/pipeline-protocol.md`)是 agent 派发 / handoff 行为的权威。
