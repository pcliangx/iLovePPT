# iLovePPT v2 设计文档 —— 诚实 skill 重构

> 📜 **设计史档**(2026-05-22) · 本文记录从骑墙形态到诚实 skill 的重构 rationale,建立"机械 = build.py / 智能 = Claude 照文档跑"的接缝。
> 现状协议见 [`.claude/pipeline-protocol.md`](../../../.claude/pipeline-protocol.md)。

**日期**:2026-05-22
**动因**:把"机械"与"智能"用清晰的文件接缝隔开 —— 机械部分 = `build.py`(`deck_plan.json → .pptx`),智能部分 = Claude 照文档流程做,二者通过 `deck_plan.json` 解耦。

---

## 1. 目标与核心思想

v1 回顾确认的根本问题:`workflow.py` 既像应用又像 skill,独立跑产出平庸 deck(每页 bullet_list、零图、无视觉自检),与"端到端生成器"的宣传不符。

v2 的核心:**用一个文件接缝（`deck_plan.json`）把机械与智能彻底隔开**。

- **机械** = `build.py`:`deck_plan.json → .pptx + PNG`。纯代码,可确定性测试。
- **智能** = Claude 照文档化流程做:读 brief → 图层规划 → 拓写每页 → 产出 `deck_plan.json`；看 PNG → 视觉自检 → 改 `deck_plan.json` → 重跑。

v2 不再假装有"自动智能"。占位骨架删除,其"智能版"以文档化流程存在。

本 v2 含 4 部分:**A** build.py 重构、**B** layout.py + tech_blue 重写、**C** evals/ 集、**D** 诚实命名/文档。

## 2. 管线与接缝

```
用户 → brief.yaml
  │  ❶ Claude（智能,照文档执行）：
  │     读 brief → 校验 → 图层规划（需图则先调 diagram skill 出 PNG）
  │     → 逐页拓写 → 产出 deck_plan.json
  ▼
deck_plan.json   ← 机械/智能接缝
  │  ❷ build.py（机械）：
  │     load_theme → 逐 slide 调 make_* → 存 .pptx → 渲染 PNG
  ▼
.pptx + 每页 PNG
  │  ❸ Claude（智能）：看 PNG → 视觉自检 → 改 deck_plan.json → 回 ❷
```

`deck_plan.json` 让二者各自独立验证:build.py 用固定 plan 做确定性回归(eval 集的基础);Claude 拓写质量由 rubric 评。

## 3. Part A —— `build.py`（机械构建器）

### 3.1 `deck_plan.json` schema

```json
{
  "theme": "tech_blue",
  "output": "./out/deck.pptx",
  "slides": [
    {"layout": "cover", "title": "...", "subtitle": "..."},
    {"layout": "cards", "title": "三大能力",
     "cards": [{"title": "", "body": ""}, ...]},
    {"layout": "pic_text", "title": "架构",
     "image_path": "/tmp/arch.png", "points": [{"title": "", "body": ""}, ...]}
  ]
}
```

- 必填:`theme`、`output`、`slides`；每个 slide 必有 `layout`。
- **图在 plan 落地前已生成**:图层规划是 Claude 流程——需图时 Claude 先调 diagram skill 出 PNG,把 `image_path` 写进 spec。build.py 看到的 `pic_text` spec 里 `image_path` 已是现成 PNG 路径。build.py 完全不碰图层逻辑。

### 3.2 build.py 函数

| 函数 | 职责 |
|---|---|
| `load_plan(path)` | 读 + 校验 `deck_plan.json`（必填字段、每 slide 有 layout）;缺失抛带定位的 `ValueError` |
| `load_theme(theme_id)` | `"tech_blue"` → 内置主题模块；`.pptx` 路径 → `_extract_theme_from_pptx`（见 §6）|
| `build_deck(plan)` | 建 `Presentation`、设尺寸 `H.SLIDE_W/H`、逐 slide `getattr(theme, f"make_{layout}")(prs, **fields)`、存 `plan["output"]` |
| `render(pptx, out_dir)` | soffice → PDF → pdftoppm → 逐页 PNG（保留 v1 的 soffice/pdftoppm 缺失分辨逻辑）|

**逐 slide 友好报错**:某 spec 字段不匹配 layout 签名 → `make_*` 抛 `TypeError` → `build_deck` 捕获,报"第 N 页 layout=X：<原始错误>",不暴露裸 traceback。

`output` 相对路径按 `deck_plan.json` 文件所在目录解析（沿用 v1 已修的相对路径逻辑）。

### 3.3 CLI

```bash
python3 build.py deck_plan.json             # 构建 + 渲染（默认）
python3 build.py deck_plan.json --no-render  # 只出 .pptx（终稿）
```

### 3.4 删除项

`workflow.py` 改名 `build.py`。删除:`generate_outline` 骨架、`vision_check` 桩、`fix_slide` 桩（含 `_fix_*` 辅助）、`plan_diagrams` 关键词桩（含 `_DIAGRAM_SIGNALS`）、`run()` 编排、`generate_slide`（并入 `build_deck`）、`estimate_page_count`、`parse_brief`、`_NON_RENDER_KEYS` 与 `visual_element` 处理、`REQUIRED` 常量。

它们的"智能版"以文档化流程存在于 `workflow.md` / `diagram-planning.md` / `visual-qa.md` / `content-writing.md`（这些文档改写为"Claude 执行清单",见 §6）。

## 4. Part B —— 可组合 layout

### 4.1 新模块 `skills/pptx/layout.py`

纯几何原语,主题无关。位于 `helpers.py`（pptx 操作）之上、`tech_blue.py`（主题）之下。

核心数据类型 `Box`：`(x, y, w, h)`,EMU 单位（`pptx.util.Emu`/`Inches`）。

| 原语 | 签名 | 作用 |
|---|---|---|
| `content_region()` | `() -> Box` | header 与 footer 之间的内容区（用 `helpers` 的 `HEADER_BOTTOM`/`FOOTER_TOP`/边距常量算出）|
| `columns(box, n, gap)` | `(Box, int, Length) -> list[Box]` | 横切 n 等宽列 |
| `rows(box, n, gap)` | `(Box, int, Length) -> list[Box]` | 纵切 n 等高行 |
| `stack(box, heights, gap, align)` | `(Box, list[Length], Length, str) -> list[Box]` | 按块高纵向排布,整组在 box 内 `top`/`middle`/`bottom` 对齐 |
| `split(box, ratio, gap)` | `(Box, float, Length) -> tuple[Box, Box]` | 按比例横切 2 块 |
| `inset(box, dx, dy)` | `(Box, Length, Length) -> Box` | 四周内缩 |

`gap` 参数有合理默认值。`Box` 提供 `.x/.y/.w/.h` 访问。

### 4.2 make_* 重写

`columns`/`rows` 让"固定数量"消失,两个 layout 合并:

| v1 layout | v2 layout | 变化 |
|---|---|---|
| `two_col_compare` | `compare` | N 列（2 或 3）,`columns(content, len(items))`；入参改为 `items: list[{title, body}]` |
| `three_col_cards` | `cards` | N 张卡（2/3/4）,`columns(content, len(cards))` |
| `bullet_list` | `bullet_list` | `stack(..., align="middle")` 把 bullet 块整体纵向居中 |
| `summary` | `summary` | `rows(content, len(conclusions))` 按结论数均布 |
| `toc` | `toc` | `rows(content, len(sections))` 均布 |
| `pic_text` | `pic_text` | `split(content, 0.42)` 分图文；右侧 `rows()` 撑 N 个 point（不再固定 4）|
| `cover` | `cover` | 全屏背景,内部改用 `Box`,逻辑不变 |
| `section_divider` | `section_divider` | 同上 |
| `single_focus` | `single_focus` | `stack(..., align="middle")` 居中数字+文字+解释 |
| `table` | `table` | 表格定位到 `content_region()` |
| `closing` | `closing` | 全屏背景,逻辑不变 |

净结果:**11 个语义 layout**——`compare`、`cards` 由 v1 的 `two_col_compare`、`three_col_cards` 改名并泛化为 N 列,其余 9 个沿用名字。数量不变,但每个对内容数量灵活。`make_*` 变成 `helpers` + `layout` 的薄组合层。

留白修法:list 类（`bullet_list`/`single_focus`）用 `stack` 中对齐;`summary`/`toc` 用 `rows` 均布。短内容不再顶端挤、底部空。

### 4.3 破坏性变更

- `two_col_compare` / `three_col_cards` layout 名退役 → `compare` / `cards`。
- `compare` 入参从 `left_title/left_body/right_title/right_body` 改为 `items: list[{title, body}]`。
- `content-writing.md`、`pptx-deck/SKILL.md` 的 layout 清单与 JSON schema 同步更新。
- v2 干净切换,不留兼容别名。

### 4.4 模块结构

```
skills/pptx/helpers.py    pptx 原语 + 设计 token（SSOT,不变）
skills/pptx/layout.py     ★新增:几何原语
skills/pptx-deck/themes/tech_blue.py   make_* = helpers + layout 的薄组合
```

`tech_blue.py` 顶部 import `helpers as H` 与 `layout as L`。

## 5. Part C —— Eval 集

### 5.1 目录

```
evals/
├── plans/*.json      8 个固定参考 deck_plan
├── rubric.md         评分标准
├── run_eval.sh       runner
├── baseline/         基准 scorecard
└── README.md         运行说明
```

### 5.2 固定 deck_plan 覆盖场景

`evals/plans/` 下 8 个 `deck_plan.json`,各覆盖一个场景:

1. 短 deck（6-8 页）
2. 长 deck（20+ 页）
3. `cards` 含 2 / 3 / 4 列
4. `compare` 含 2 / 3 列
5. `pic_text` 带预生成图
6. `table` 密集
7. 中文密集（验证字体不 fallback）
8. `.pptx` 模板提取主题（验证 `_extract_theme_from_pptx`）

**用固定 plan 而非 brief**:eval 目的是检出"layout/build 代码回归"。固定 plan → 确定性,隔离 Claude 拓写的不确定性。

### 5.3 rubric.md 评分标准

评分维度:

- **视觉**（取自 `visual-qa.md` 12 项）:元素重叠 / 文字溢出 / 字体 fallback / 标题间距 / 对比度 / margin 偏移 / 配色一致 / 留白边界 / 表格 banding / emoji / 装饰大字换行 / layout 符意图
- **留白与对齐**:内容区有无大片异常空白；列/行是否对齐网格
- **结构**:页序节奏；图密度

每项 pass/fail 或 1-5 分。

### 5.4 runner

`run_eval.sh`：逐个 `evals/plans/*.json` 跑 `build.py` → 渲染 → 收集 PNG → 生成一份 markdown scorecard 模板（每页一节,留空待填）。

runner 是机械代码。**评分由 Claude 看图按 rubric 打**——PPT 质量本质是视觉的。

### 5.5 回归对比

`evals/baseline/` 存一次已知良好运行的 scorecard。改完代码重跑 eval,新 scorecard 对比 baseline——分数掉了即回归。

## 6. Part D —— 诚实命名 / 文档

| 项 | v1 | v2 |
|---|---|---|
| 函数 | `_ingest_template` | `_extract_theme_from_pptx` |
| 文档 | `template-ingest.md`（"学风格"）| `template-extract.md`（"提取主色与字体"）|
| `workflow.py` | Python 应用骨架 | 改名 `build.py`,纯机械（§3）|
| `workflow.md` | 描述 Python `run()` 的 7 步 | 改写为 **Claude 执行流程**:brief→deck_plan→build→QA 回环 |
| README | 暗示"自动配图" | 明确:`build.py` 只做机械构建;配图/拓写/视觉自检由 Claude 驱动。附 §2 管线图 |
| `USAGE.zh.md` / `MANUAL.zh.md` | 描述旧 workflow.py | 更新到 v2 词汇（build.py / deck_plan.json / `compare`/`cards`）。**不做全面文档合并**,只保证不写错 |
| `[[skill-name]]` | 看着像链接 | 各 SKILL.md（或 CLAUDE.md）加一行说明:这是文档交叉引用约定,非自动解析机制 |

`diagram-planning.md` / `visual-qa.md` / `content-writing.md` 改写:删去"骨架函数"措辞,改为"Claude 执行清单";对接 `deck_plan.json`。

`CLAUDE.md` 更新:架构段落改述 build.py / deck_plan.json 接缝；SSOT 段落加 `layout.py`。

## 7. 错误处理

| 故障 | 兜底 |
|---|---|
| `deck_plan.json` 缺必填字段 | `load_plan` 抛带字段名的 `ValueError` |
| slide 缺 layout 字段 | `load_plan` 报第几页 |
| spec 字段与 layout 签名不匹配 | `build_deck` 捕获 `TypeError`,报"第 N 页 layout=X" |
| 未知 layout（theme 无 `make_X`）| `build_deck` 抛 `AttributeError` 转友好信息 |
| `image_path` 指向不存在的文件 | `make_pic_text` / `embed_picture` 抛带路径的错误 |
| soffice / pdftoppm 缺失 | `render` 分辨并提示安装命令（沿用 v1）|
| `.pptx` 模板提取失败 | `_extract_theme_from_pptx` best-effort,提不到的字段回退 tech_blue 默认 |

## 8. 测试策略

| 层 | v2 做法 |
|---|---|
| **几何原语**（`layout.py`）| **真单测**——`columns(box,3)` 返回 3 个 box,断言 x/w/y/h。纯函数,确定性。这是项目首次有不靠"数 shape"的测试 |
| **build.py** | 单测 `load_plan` 校验路径、`build_deck` dispatch、错误分辨 |
| **theme make_***| 轻量结构测（slide 数、关键 shape 存在）,沿用 v1 思路——视觉正确性交给 eval |
| **eval 集** | 视觉/布局回归——固定 plan 跑 build,Claude 按 rubric 评分,对比 baseline |
| **端到端 smoke** | 一个 `deck_plan.json` 跑 `build.py` 出 .pptx + 渲染抽检 |

## 9. 显式不做（YAGNI）

- ❌ 不内嵌 LLM 调用（智能由 Claude 框架做,不进 build.py）
- ❌ 不做 region/grid 完整系统（中度即可,`columns`/`rows`/`stack`/`split` 够用）
- ❌ 不做全面文档合并（USAGE/MANUAL 重叠是已知债,本次只更新不写错）
- ❌ 不做 brief→deck_plan 的自动化（那是 Claude 流程,不是代码）
- ❌ 不保留 `two_col_compare`/`three_col_cards` 兼容别名
- ❌ eval 不跑 brief→plan 全链路（非确定性;固定 plan 即可）

## 10. 实施阶段

1. **Phase A+B**（耦合,一起做）:`layout.py` 几何原语 + 单测 → `tech_blue.py` make_* 重写 → `build.py`（由 workflow.py 改造）+ 单测 → 端到端 smoke
2. **Phase C**:`evals/` 目录 + 固定 plan + rubric + runner + baseline
3. **Phase D**:命名重构（`_extract_theme_from_pptx`、`template-extract.md`）+ 文档改写（workflow.md / README / SKILL.md / CLAUDE.md / USAGE / MANUAL / diagram-planning / visual-qa / content-writing）

## 11. 从 v1 的迁移变化清单

| 维度 | v1 | v2 |
|---|---|---|
| 形态 | skill / app 骑墙 | 纯 skill:机械=build.py,智能=Claude 流程 |
| 入口 | `workflow.py run(brief)` 假端到端 | `build.py deck_plan.json` 诚实机械 |
| 接缝 | 无（占位函数串起来）| `deck_plan.json` |
| layout | 11 个写死坐标函数 | 11 个,基于 `layout.py` 几何原语,数量灵活（`compare`/`cards` 泛化为 N 列）|
| 留白问题 | 内容页顶端挤、底部空 | `stack` 中对齐 / `rows` 均布 |
| 测试 | 全是"数 shape" | 几何原语真单测 + eval 视觉回归 |
| 质量评估 | 无 | `evals/` 集 + rubric + baseline |
| 命名 | `_ingest_template`("学风格") | `_extract_theme_from_pptx`("提取主色字体") |
| 文档 | 描述假应用 | 描述 Claude 流程 + 诚实标注机械边界 |
