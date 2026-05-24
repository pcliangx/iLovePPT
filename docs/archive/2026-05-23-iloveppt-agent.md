# iLovePPT Agent 重构 Implementation Plan

> 📜 **实施史档**(2026-05-23) · 本文记录"把 iLovePPT 从 skill 库改造成 Claude Code agent"的逐步实施 plan,已完成。
> 现状协议见 [`.claude/pipeline-protocol.md`](../../../.claude/pipeline-protocol.md)。
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 iLovePPT 从 skill 库改造成 Claude Code 项目内 agent —— 新增一个 `.claude/agents/iloveppt.md` 作为 orchestrator,把现有 3 个 skill 降级为 agent 的参考库,引入大纲 checkpoint。

**Architecture:** 最小改动叠加一层。agent 在独立上下文跑两阶段(Phase 1 出大纲并停下等批准 → Phase 2 拓写/构建/QA/交付)。build.py / themes / helpers / layout / content-writing.md / visual-qa.md / diagram-planning.md / template-extract.md / evals / 测试**一律不动**;只新增 agent 定义 + 4 份入口文档轻改。

**Tech Stack:** Markdown(agent 定义本身就是 markdown + YAML frontmatter);用 Bash/git 做提交、grep/cat 验证;`python3 -m pytest tests/` 跑现有测试确认未回归(应保持 42 PASS)。

**Spec:** `docs/superpowers/specs/2026-05-23-iloveppt-agent-design.md`

**工作目录:** `/Users/pc2026/Documents/DevTools/KillPPTs/`

---

## File Structure

```
.claude/agents/iloveppt.md              ★ 新增 —— agent 定义(frontmatter + system prompt)
skills/pptx-deck/SKILL.md               改写入口段:agent 主、skill-mode 备
skills/pptx-deck/workflow.md            加一节「在 agent 模式下的运行差异(Phase 1/2 + checkpoint)」
README.md                                主入口改为 @agent-iloveppt
USAGE.zh.md                              主入口改为 agent;skill-mode 列备用
CLAUDE.md                                架构段加一节描述 agent 层
```

代码:`build.py / helpers.py / layout.py / themes/ / evals/ / tests/` —— **一行不动**。

---

# Task 1:Author `.claude/agents/iloveppt.md`

**Files:**
- Create: `.claude/agents/iloveppt.md`

- [ ] **Step 1: 确认目录存在**

```bash
cd /Users/pc2026/Documents/DevTools/KillPPTs
mkdir -p .claude/agents
ls -la .claude/agents
```

期望: 目录存在(空或已有别的 agent)。

- [ ] **Step 2: 写 `.claude/agents/iloveppt.md`**

完整内容如下,**逐字逐句照写**(YAML frontmatter + Markdown 正文):

```markdown
---
name: iloveppt
description: 端到端 PPT 生成 agent。用户给主题/要点/brief.yaml/参考 .pptx 模板,自主完成大纲规划(出大纲后停下等批准)、配图生成、逐页拓写、build、视觉自检、交付 .pptx + review-needed 清单。Use proactively when the user wants a deck/presentation/PPT generated from a topic or brief —— 做 PPT / 帮我写 PPT / 路演 deck / 汇报 / 提案 / brief.yaml / .pptx 模板。
tools: Bash, Read, Write, Edit, Glob, Grep, Skill
model: opus
color: blue
---

你是 **iLovePPT** —— 一个端到端 PPT 生成 agent。你跑在 Claude Code 里、独立上下文,把"主题/要点/brief"变成完整 `.pptx` + 视觉自检过的渲染图。

## 仓库地基

iLovePPT 仓库布局(可能在主线程项目目录,或链接到 `.claude/skills/` 下):

- `skills/pptx-deck/build.py` —— 纯机械构建器,读 `deck_plan.json` 出 `.pptx + PNG`
- `skills/pptx-deck/themes/tech_blue.py` —— 默认主题(11 个 `make_*` layout)
- `skills/pptx-deck/workflow.md` —— 完整工作流 SSOT(开工前先读)
- `skills/pptx-deck/content-writing.md` —— 11 layout 文案规则 + 「deck 级论证结构」(**核心要求:麦肯锡金字塔原理 5 件套** + action title + Pyramid 自检表)
- `skills/pptx-deck/diagram-planning.md` —— 图层规划(哪节配图 + 4 类图决策表;结构性图形优先 draw.io)
- `skills/pptx-deck/visual-qa.md` —— 单页 12 项视觉 checklist
- `skills/pptx-deck/template-extract.md` —— 从用户 .pptx 提主色 + 字体
- `evals/rubric.md` —— PPTEval 三维(Content / Design / Coherence)
- `[[diagram]]` skill —— draw.io / Mermaid / matplotlib / pptx-native 出图
- `[[pptx]]` skill —— 底层 .pptx 读写(helpers / layout)

## 运行模式识别

派发入参里**含已批准 outline 结构** → 跑 **Phase 2(构建)**。
**否则** → 跑 **Phase 1(大纲)**,结束时返回大纲,等用户批准。

---

## Phase 1 —— 大纲(出完即终止)

1. **收 brief**:从派发入参提取 `title / outline 意图 / 受众 / 时长 / 输出路径 / 主题选择(tech_blue 或 .pptx 模板路径)`。缺字段在最终返回的 `missing_fields` 中列出,**不要凭空编**。
2. **按需读文档**(用 `Read`):
   - `skills/pptx-deck/workflow.md` —— 全流程概貌
   - `skills/pptx-deck/content-writing.md` —— 「deck 级论证结构」+「11 layout 文案规则」
   - `skills/pptx-deck/diagram-planning.md` —— 4 类图决策表
3. **按金字塔原理设计论证结构(核心要求,5 件套缺一不可)**:
   完整规则见 `content-writing.md` 「deck 级论证结构」。执行要点:
   - **① 单一顶端论点**:整 deck 只服务于一个核心推荐句(完整动宾 + 具体边界),不是议题陈述。落到 `top_recommendation` 字段
   - **② SCQA 开场**:Situation / Complication / Question / Answer 四要素全填,A == 顶端论点。落到 `scqa` 字段
   - **③ 答案在前(BLUF)**:cover.subtitle 或第 1 内容页明示顶端论点;每个 section_divider 标题是结论句
   - **④ 横向 MECE 支撑**:3-5 个章节,两两不重叠,加起来完整支撑顶端论点。自检后落到 `mece_check_passed` 字段
   - **⑤ 纵向疑问/回答链**:章节标题 + 页面 action title 串起来应能独立讲出顶端论点的完整论据链(即 ghost deck test)
   - 跑完 `content-writing.md` 的 **Pyramid 自检表 7 项**,任一不过 → 在 `missing_fields` 列出该项,不交付 Phase 1
   - **例外**:用户在 brief 中显式声明 `structure_mode: data_report | tutorial | catalog`,可设 `bypass_pyramid: true` 跳过自检 1-6 项(action title 仍要求)
4. **图层规划**:逐节按 `diagram-planning.md` 决策表判断是否配图,记 `diagram_plan`。**结构性图形(arch / flow / matrix / decision tree / relation)优先 draw.io**;数据图用 matplotlib;Mermaid 仅备选。
5. **页数预估**:按 `content-writing.md` 时长公式 `total ≈ duration_min × 1.5`(含 cover / toc / divider × N / summary / closing)。
6. **返回 Phase 1 输出**(YAML 结构,严格按下面字段):

```yaml
phase: 1
theme: tech_blue                      # 或 .pptx 模板的绝对路径
output: /abs/path/to/deck.pptx
audience: executive | technical | general | sales
target_page_count: 12

# === 金字塔原理 5 件套(核心要求,bypass_pyramid=false 时全部必填) ===
top_recommendation: "完整推荐句:动宾结构 + 具体边界"
scqa:
  situation: "听众认同的客观背景"
  complication: "打破现状的冲突 / 变化 / 风险"
  question: "由 C 产生的关键问题(可隐含)"
  answer: "= top_recommendation"
mece_check_passed: true               # 章节横向 MECE 自检:3-5 节,两两不重叠
pyramid_check_passed: true            # Pyramid 自检表 7 项全过
bypass_pyramid: false                 # 仅 structure_mode in {data_report, tutorial, catalog} 可设 true
# === 金字塔字段结束 ===

sections:
  - title: "节标题(≤ 12 字)"
    action_title: "完整结论句(对顶端论点的'为什么/怎么做/是什么'回答)"
    intent: "这节要让读者明白什么"
    layout: cards | compare | bullet_list | single_focus | table | pic_text | summary
    needs_diagram: true | false
diagram_plan:
  - section_idx: 2
    diagram_type: arch_diagram | flow | chart | simple_relation
    tool: drawio | mermaid | matplotlib | pptx-native
    intent: "这张图要表达什么"
ghost_deck_test_passed: true          # 即 Pyramid 自检第 6 项;保留独立字段供旧消费方使用
missing_fields: []                    # 若 brief 缺字段 或 Pyramid 自检某项不过,列在这里;非空则不交付 Phase 1
```

返回完即**终止 Phase 1**。**不要继续生成图或写 deck_plan.json** —— 那是 Phase 2 的事。

---

## Phase 2 —— 构建(从已批准 outline 起,一路跑到交付)

派发入参带 Phase 1 输出的批准版(用户可能改过)。

1. **生成图**:对 `diagram_plan` 里每张图:
   - 结构性图形(arch / flow / relation) → **优先 draw.io**(参 `[[diagram]] drawio.md`;用 `Bash` 跑 draw.io CLI 出 PNG,`--width 3200`)
   - 数据图(chart) → matplotlib(参 `[[diagram]] matplotlib.md`)
   - 落 PNG 到 `<output 所在目录>/_assets/` 下,记下绝对路径
2. **写 `deck_plan.json`**:按已批准 outline 逐页拓写,严格遵守 `content-writing.md` 字数/句式约束:
   - 每节 1-3 个内容页;按节奏感规则(相邻页不重 layout)穿插
   - 每页 `title` 用 **action title**(标题即结论)
   - 配图节用 `pic_text`,`image_path` 指步骤 1 的 PNG
   - 加 cover / toc / section_divider × N / summary / closing
   - 写到 `<output 同目录>/deck_plan.json`
3. **构建**:`python3 <仓库>/skills/pptx-deck/build.py <deck_plan.json>`。等待完成,记下 `.pptx` 路径 + `*_render/` 渲染目录。
4. **视觉 QA 循环(至多 3 轮)**:
   - 读 `evals/rubric.md` Design 维(D1-D14)+ `visual-qa.md` 12 项
   - 对每页 `*_render/page-*.jpg` 用 `Read` 看图,按 Design 维打分,记 fail 项 + 页号
   - 有 fail → 改 `deck_plan.json`(改字数 / 改 layout / 调字段)→ 重跑 build.py → 重看
   - **3 轮后仍有 fail 的页加入 `review_needed`**
5. **返回 Phase 2 输出**:

```yaml
phase: 2
pptx_path: /abs/path/to/deck.pptx
qa_rounds: 1 | 2 | 3
review_needed:
  - page: 5
    issues: ["D10 内容下半空白"]
    suggestion: "缩短卡片正文 或 改用 bullet_list"
design_score: "M/N (M 项通过 / N 总检查)"
```

---

## 关键约束

- **绝不内嵌 LLM API 调用**:`build.py` 是纯机械,**你**是智能侧。brief 解析 / 文案拓写 / 视觉 QA 判断都在你这里,build.py 只渲染。
- **绝不跳过视觉 QA**:Phase 2 第 4 步必须真读渲染图打分,不能"应该差不多"。
- **3 轮 QA 上限**:不要无限循环。3 轮后仍 fail 的页进 `review_needed`,交人审。
- **不能再派 subagent**:你是 subagent,不可嵌套派发。要工具直接用(Bash 跑脚本、Skill 调 [[diagram]] / [[pptx]])。
- **绝不复制用户模板内容**:`.pptx` 模板只 `_extract_theme_from_pptx` 抽主色 + 字体(参 `template-extract.md`),不挪页面。
- **draw.io 优先**:流程 / 架构 / 矩阵 / 决策树 / 关系 → draw.io;Mermaid 仅备选;数据 → matplotlib。
- **中文字体默认 Microsoft YaHei**:macOS 渲染需装雅黑(参 `pptx/SKILL.md`)。
- **action title**:每页 `title` 是完整结论句。反例"市场背景";对例"SaaS 市场三年翻倍,渗透率仍不足 15%"。
- **金字塔原理是核心要求**:Phase 1 不交付未通过 Pyramid 自检表 7 项的 outline。`top_recommendation` / `scqa` / `mece_check_passed` / `pyramid_check_passed` 任一缺失或不过 → 在 `missing_fields` 列出,要求用户补 brief 或重排 outline。仅 `bypass_pyramid=true`(由用户 brief 显式声明 `structure_mode`) 可豁免。

## anti-prompt

- 不要在 Phase 1 就开始出图 / 写 deck_plan.json —— 那是 Phase 2 的活
- 不要在 Phase 2 跳过 Pyramid 自检之前直接开拓 —— 但若 outline 是用户批过的,默认它过了
- 不要把 `review_needed` 留空就交付 —— 除非真的零 fail
- 不要把"完整结论句"写成口号("我们一定行") —— 结论要具体陈述/数字
- 不要为单条 brief 派生上百页 —— 守住 `target_page_count`(合理边界 ≤ 50)
```

注意:正文中的 ``` 包裹了 YAML 输出结构示例。用 `Write` 工具一次性写入即可。

- [ ] **Step 3: 验证 YAML frontmatter 解析**

```bash
cd /Users/pc2026/Documents/DevTools/KillPPTs
python3 -c "
import yaml, pathlib
text = pathlib.Path('.claude/agents/iloveppt.md').read_text(encoding='utf-8')
assert text.startswith('---'), 'must start with ---'
fm_end = text.find('\n---\n', 4)
assert fm_end > 0, 'no closing ---'
fm = yaml.safe_load(text[4:fm_end])
for k in ['name', 'description', 'tools', 'model']:
    assert k in fm, f'missing field: {k}'
print('frontmatter OK:', fm['name'], fm['model'])
"
```

期望: `frontmatter OK: iloveppt opus`。失败则修文件头。

- [ ] **Step 4: 验证正文覆盖了关键概念**

```bash
cd /Users/pc2026/Documents/DevTools/KillPPTs
for term in "Phase 1" "Phase 2" "checkpoint\|批准\|批准版" "金字塔原理\|Pyramid 自检" "ghost deck test" "draw.io 优先\|优先 draw.io" "review_needed" "3 轮" "action title" "top_recommendation" "scqa"; do
  if grep -qE "$term" .claude/agents/iloveppt.md; then
    echo "OK: $term"
  else
    echo "MISSING: $term"
  fi
done
```

期望: 每项都 OK。任何 MISSING 都说明 system prompt 漏了关键概念,需补。

- [ ] **Step 5: 确认现有测试仍 42 PASS**

```bash
python3 -m pytest tests/ -q
```

期望: `42 passed`(本任务零代码改动,只是确认未误伤)。

- [ ] **Step 6: Commit**

```bash
git add .claude/agents/iloveppt.md
git commit -m "feat(agent): add iloveppt orchestrator agent definition"
```

---

# Task 2:Reframe `pptx-deck/SKILL.md` + `workflow.md`

**Files:**
- Modify: `skills/pptx-deck/SKILL.md`
- Modify: `skills/pptx-deck/workflow.md`

- [ ] **Step 1: 读现有 SKILL.md 与 workflow.md**

```bash
cd /Users/pc2026/Documents/DevTools/KillPPTs
head -10 skills/pptx-deck/SKILL.md
head -10 skills/pptx-deck/workflow.md
```

了解当前 frontmatter description 与开篇段落。

- [ ] **Step 2: 改写 `skills/pptx-deck/SKILL.md` frontmatter 与开篇**

用 `Edit` 工具改 frontmatter 的 `description` 字段——把"做 PPT / 帮我写 PPT..."这些触发词搬走,改成"agent 知识库"的定位。把当前的 description 内容(端到端 PPT 生成器 + 触发关键词)替换为下面这条:

```
description: pptx-deck 知识库 —— 11 个 layout 的主题(tech_blue)、build.py 机械构建器、文案/图层/视觉 QA/模板提取的参考文档。**主入口是 [[iloveppt]] agent**(@agent-iloveppt 派发,带大纲 checkpoint 自动跑完全程);本 SKILL.md 仅作 skill-mode 后备入口供主线程 Claude 直接读用。触发由 agent 的 description 接管;本 skill 不再做自动委派。
```

然后在 SKILL.md 文件开头(`# pptx-deck — 端到端 PPT 生成器` 标题之后的第一段)前插入一段提示:

```
> **主入口:`@agent-iloveppt`**(独立上下文跑两阶段:Phase 1 出大纲等批准 → Phase 2 拓写/构建/QA/交付)。本 skill 仍可被主线程 Claude 直接读用作 skill-mode 后备入口;触发关键词已搬到 agent 的 description。
> agent 设计见 [iLovePPT Agent 设计](../../docs/superpowers/specs/2026-05-23-iloveppt-agent-design.md)。
```

保持文件其他段落不动(layout 表、共识 token、子文档导航、内置主题、anti-prompt、checklist 都仍有效)。

- [ ] **Step 3: 改写 `skills/pptx-deck/workflow.md` 加 agent 模式段**

用 `Edit` 工具在 workflow.md 现有"## 流程(Claude 逐步执行)"小节**之后**(在"## build.py 的能力边界"小节**之前**)插入新一节:

```markdown
## agent 模式下的运行差异

当通过 `@agent-iloveppt` 派发时,上述 7 步分到两次 agent 派发里:

- **Phase 1**(第 1 次派发) = 步骤 1 + 2 + 3(部分):读 brief → 图层规划 → **按金字塔原理 5 件套设计大纲 + 跑 Pyramid 自检 7 项**。**出完大纲即终止,等用户批准。**
- **Phase 2**(第 2 次派发,入参带已批准 outline) = 步骤 3(余) + 4 + 5 + 6 + 7:生成图 → 写 deck_plan.json → build.py → 视觉 QA 循环(≤ 3 轮)→ 交付。

主线程 Claude 模式(直接读本 SKILL.md 跑)= 一气跑完 7 步,中间不强制 checkpoint。

两种模式的 build.py 调用、deck_plan.json 接缝、视觉 QA 标准完全一致 —— 只是 orchestration 主体不同(agent 实例 vs 主线程 Claude)。

agent 详细设计见 [iLovePPT Agent 设计](../../docs/superpowers/specs/2026-05-23-iloveppt-agent-design.md)。
```

- [ ] **Step 4: 验证两份文档关键字都在**

```bash
cd /Users/pc2026/Documents/DevTools/KillPPTs
grep -n "agent-iloveppt\|iloveppt agent\|\[\[iloveppt\]\]" skills/pptx-deck/SKILL.md
grep -n "agent 模式\|Phase 1\|Phase 2\|checkpoint\|批准" skills/pptx-deck/workflow.md
```

期望: 每个 grep 都有命中(SKILL.md 至少 2 条;workflow.md 至少 5 条覆盖 Phase/checkpoint)。

- [ ] **Step 5: 现有测试仍 42 PASS**

```bash
python3 -m pytest tests/ -q
```

期望: `42 passed`。

- [ ] **Step 6: Commit**

```bash
git add skills/pptx-deck/SKILL.md skills/pptx-deck/workflow.md
git commit -m "docs(pptx-deck): point primary entry to iloveppt agent; add agent-mode workflow section"
```

---

# Task 3:Update `README.md` + `USAGE.zh.md` + `CLAUDE.md`

**Files:**
- Modify: `README.md`
- Modify: `USAGE.zh.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: 读现有 README.md 的"快速开始"段**

```bash
cd /Users/pc2026/Documents/DevTools/KillPPTs
sed -n '1,80p' README.md
```

找到目前"快速开始 / 用法 / 入口"的位置。

- [ ] **Step 2: README.md 主入口改为 agent**

用 `Edit` 工具,在 README 的"快速开始"或"用法"段(具体位置取决于现有结构)**最前**插入下面段落,作为推荐主入口:

```markdown
## 用法 —— 通过 agent(主推)

iLovePPT 是一个 Claude Code agent。装好后(把 `.claude/agents/iloveppt.md` 放到目标项目的 `.claude/agents/`,或在本仓库内直接用),在 Claude Code 里:

```
@agent-iloveppt 帮我做一份关于 X 的 PPT,受众 Y,时长 Z 分钟
```

agent 会两阶段跑:

1. **Phase 1 — 大纲**:返回 sections + 图层计划 + 页数预估,等你批准
2. **Phase 2 — 构建**:你批准后,自动跑配图 → 拓写 → build → 视觉 QA(≤ 3 轮)→ 交付 `.pptx`

详见 [USAGE.zh.md](USAGE.zh.md) 与 [agent 设计](docs/superpowers/specs/2026-05-23-iloveppt-agent-design.md)。

## 用法 —— skill-mode(备用)

若不通过 agent,主线程 Claude 也能直接读 `skills/pptx-deck/SKILL.md` 跑 7 步流程。skill-mode 没有强制 checkpoint。
```

保留 README 其他段落(架构图、依赖、测试、贡献等)不动。

- [ ] **Step 3: USAGE.zh.md 顶部增"通过 agent 使用"段**

用 `Edit` 工具,在 `USAGE.zh.md` 当前 `# iLovePPT 使用说明` 标题与第一段之间(或紧接现有"一、这是什么"小节之后)插入:

```markdown
## 通过 agent 使用(主推)

iLovePPT 作为 Claude Code agent 部署:

```
@agent-iloveppt 做一份 <主题> 的 PPT,受众 <executive|technical|general|sales>,时长 <N> 分钟
```

agent 两阶段:

- **Phase 1**:解析 brief → **按金字塔原理 5 件套设计大纲**(单一顶端论点 / SCQA / 答案在前 / MECE / 纵向疑问链)→ Pyramid 自检 7 项 → 规划图层 → 返回 outline 结构供你批准
- **Phase 2**(批准后):生成配图 → 写 deck_plan.json → 跑 build.py → 视觉自检(≤ 3 轮)→ 返回 `.pptx` 路径 + review-needed 清单

把 agent 共享给别的项目:把本仓库的 `.claude/agents/iloveppt.md` 拷或软链到目标项目的 `.claude/agents/iloveppt.md`(同时需要 `skills/` 也可访问 —— 与现在的 skill 链接方式一致)。

详细设计:[docs/superpowers/specs/2026-05-23-iloveppt-agent-design.md](docs/superpowers/specs/2026-05-23-iloveppt-agent-design.md)。

---
```

保留 USAGE.zh.md 其他段落不动(它们仍解释 skill-mode 的细节,作为 agent 内部知识的延伸)。

- [ ] **Step 4: CLAUDE.md 架构段加 agent 层**

用 `Edit` 工具,在 `CLAUDE.md` 的 `## Architecture` 段下、`### Three-skill layering` 小节**之前**插入新小节:

```markdown
### Agent 层

`.claude/agents/iloveppt.md` 是项目的主入口。它是一个 Claude Code subagent —— 独立上下文 orchestrator,把以下三件事串起来:(1) 读 brief / 设计大纲 / 规划图层(Phase 1,终于大纲 checkpoint 等用户批准);(2) 批准后,生成图 / 拓写 / 跑 build.py / 视觉 QA 循环 / 交付(Phase 2)。

skill 层(`pptx-deck` / `pptx` / `diagram`)继续作为 agent 的工具与知识库存在,也可被主线程 Claude 直接用作 skill-mode 后备入口。

agent 设计见 `docs/superpowers/specs/2026-05-23-iloveppt-agent-design.md`。
```

- [ ] **Step 5: 验证 3 份文档都更新到了**

```bash
cd /Users/pc2026/Documents/DevTools/KillPPTs
grep -n "@agent-iloveppt\|iloveppt agent\|Agent 层" README.md USAGE.zh.md CLAUDE.md
```

期望: README + USAGE + CLAUDE 三份都至少 1 条命中。

- [ ] **Step 6: 现有测试仍 42 PASS**

```bash
python3 -m pytest tests/ -q
```

期望: `42 passed`。

- [ ] **Step 7: Commit**

```bash
git add README.md USAGE.zh.md CLAUDE.md
git commit -m "docs: update README/USAGE/CLAUDE to point at iloveppt agent as primary entry"
```

---

# Task 4:Final consistency + 手动 e2e smoke 准备

**Files:**
- 可能 Modify(若上面 grep 抓到死链): 任何 `skills/**.md`、`docs/**.md`、`README.md`、`USAGE.zh.md`、`CLAUDE.md`

- [ ] **Step 1: 死链/不一致扫描**

```bash
cd /Users/pc2026/Documents/DevTools/KillPPTs
# 应该出现 agent 引用的地方:
grep -rn "@agent-iloveppt\|iloveppt agent\|\[\[iloveppt\]\]\|iloveppt orchestrator" \
  README.md USAGE.zh.md CLAUDE.md skills/pptx-deck/SKILL.md skills/pptx-deck/workflow.md
echo "---"
# 任何指向 .claude/agents/iloveppt.md 的引用都应能解析:
grep -rn "\.claude/agents/iloveppt" \
  README.md USAGE.zh.md CLAUDE.md skills/ docs/superpowers/specs/2026-05-23-iloveppt-agent-design.md
echo "---"
# spec 文件存在:
ls -la docs/superpowers/specs/2026-05-23-iloveppt-agent-design.md
ls -la .claude/agents/iloveppt.md
```

期望: 第一组每行都有命中(确认主入口指向已落地);第二组路径正确;两个文件都存在。任何 dead link 都用 `Edit` 修。

- [ ] **Step 2: agent 文件全文 sanity 检查**

```bash
cd /Users/pc2026/Documents/DevTools/KillPPTs
wc -l .claude/agents/iloveppt.md
grep -cE "^## " .claude/agents/iloveppt.md
```

期望: 行数大于 80(完整 prompt);至少 5 个 `## ` 主小节(仓库地基 / 运行模式识别 / Phase 1 / Phase 2 / 关键约束 / anti-prompt)。

- [ ] **Step 3: 写一份「手动 e2e smoke 步骤」临时文件供用户验收**

用 `Write` 工具创建 `/tmp/iloveppt_agent_smoke.md`(不入仓库;仅给用户参考):

```markdown
# iLovePPT agent 手动 smoke 测试

1. 在 Claude Code 里(项目根目录或链接到 `.claude/agents/iloveppt.md` 的目标项目),输入:

   ```
   @agent-iloveppt 帮我做一份介绍 iLovePPT 项目的 5-8 页 PPT,受众:开发者,时长 10 分钟,输出 /tmp/iloveppt_intro.pptx
   ```

2. **Phase 1 期望**:agent 返回 YAML(或 markdown)结构,含 `phase: 1` / `top_recommendation` / `scqa` / `mece_check_passed` / `pyramid_check_passed` / `sections[]` / `diagram_plan[]` / `target_page_count` / `ghost_deck_test_passed`。**没有 .pptx 产出**;`pyramid_check_passed: false` 或 `missing_fields` 非空 → agent 反问而非交付。

3. 看一眼 outline 合理就回:
   ```
   批准,按此 outline 跑 Phase 2
   ```
   (主线程 Claude 会把已批准 outline 作为 Phase 2 的入参)

4. **Phase 2 期望**:agent 跑配图 → 写 deck_plan.json → 跑 build.py → 视觉 QA 循环。最终返回 `phase: 2 / pptx_path: /tmp/iloveppt_intro.pptx / qa_rounds: N / review_needed: [...] / design_score: M/N`。

5. 验收:
   - `/tmp/iloveppt_intro.pptx` 存在且能打开
   - 渲染目录 `/tmp/iloveppt_intro_render/page-*.jpg` 存在
   - review_needed 清单合理(或空)
   - 视觉抽检 cover / 中间一页 cards / closing 都无离谱问题
```

(这只是一份本地 smoke 说明,不 commit;运行手动 smoke 是用户的事。)

- [ ] **Step 4: 跑一次全套测试 + eval(确认零回归)**

```bash
cd /Users/pc2026/Documents/DevTools/KillPPTs
python3 -m pytest tests/ -q
bash evals/run_eval.sh 2>&1 | tail -10
```

期望: 测试 `42 passed`;eval 8 个 plan 全部 `已生成`。

- [ ] **Step 5: 最终 git status 看清**

```bash
cd /Users/pc2026/Documents/DevTools/KillPPTs
git log --oneline | head -8
git status --short
```

期望: 最近 3 个 commit 是 Task 1 / 2 / 3 的;`git status` 工作树干净(或仅有 Task 4 修出的细微 doc 改动需要 commit)。

- [ ] **Step 6: 若 Step 1 修了任何死链,commit**

```bash
git status --short
# 若有改动:
git add -A
git status --short
git commit -m "docs: final consistency pass for iloveppt agent restructure"
# 若无改动,跳过此 commit。
```

---

## 完成标准

- [ ] `.claude/agents/iloveppt.md` 存在,YAML frontmatter 合法,正文覆盖 Phase 1 / Phase 2 / checkpoint / **金字塔原理 5 件套 + Pyramid 自检 7 项** / ghost deck test / draw.io 优先 / review_needed / 3 轮上限
- [ ] `skills/pptx-deck/SKILL.md` 顶部明确指向 `@agent-iloveppt` 为主入口,skill-mode 为后备
- [ ] `skills/pptx-deck/workflow.md` 含"agent 模式下的运行差异"段
- [ ] `README.md` / `USAGE.zh.md` / `CLAUDE.md` 主入口都改为 agent
- [ ] 4 个 commit 在主分支
- [ ] `python3 -m pytest tests/` 仍 42 PASS(零代码回归)
- [ ] `bash evals/run_eval.sh` 8 个 plan 全部 build 成功(零 build 回归)
- [ ] `/tmp/iloveppt_agent_smoke.md` 已准备,用户可按它做手动 e2e

---

## 与现有计划的关系

本计划只引入 agent 层,不修代码、不动布局 / 主题 / 几何 / 评测体系 / 现有文档主体。它是 v2 之上的薄薄一层:`docs/superpowers/specs/2026-05-22-iloveppt-v2-design.md`(v2 机械/智能分离架构)+ `docs/superpowers/specs/2026-05-23-iloveppt-agent-design.md`(本次 agent 包装)。

#3(内容自适应布局)留待后续单独 brainstorm。
