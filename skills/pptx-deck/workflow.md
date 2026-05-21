# pptx-deck 主流程

## 概览

端到端流程：用户 brief（自由对话 / brief.yaml）→ 完整 .pptx + 视觉自检通过。

```
brief
  │
  ▼
parse_brief ──── 字段校验 / 补默认值
  │
  ▼
load_theme ───── 内置 tech_blue 或 template-ingest 学风格
  │
  ▼
generate_outline ─── 页数估算 + layout 选型
  │
  ▼
┌─────────────────────────────────┐
│  per-slide loop (每页)          │
│                                 │
│  generate_slide                 │
│       │                         │
│       ▼                         │
│  render_one_slide               │
│       │                         │
│       ▼                         │
│  vision_check ──── issues JSON  │
│       │                         │
│       ▼  (issues 非空 ≤ 3 次)   │
│  fix_slide ──── 重渲染 ──► loop │
│       │                         │
│       ▼  (issues 仍存在)        │
│  mark_review_needed             │
└─────────────────────────────────┘
  │
  ▼
deck_review ──── 跨页一致性检查
  │
  ▼
save → brief.output
  │
  ▼
打印 review-needed 清单 → 人工最终核审
```

---

## 6 步流程详解

### Step 1：parse_brief

#### 两条输入路径

**路 A — 自由对话**

LLM 与用户对话补齐 brief 必填字段（title / outline / theme / output）。
当用户未提供某字段时,使用以下 prompt 模板追问：

```
请提供以下信息以生成 PPT：
1. 主题（≤ 20 字）
2. 章节/大纲（建议 4-6 个）
3. 主题风格（默认 tech_blue,或给 .pptx 模板路径让 skill 学风格）
4. 输出路径
（可选）受众、时长、关键论点、目标页数、品牌色
```

**路 B — brief.yaml**

用户直接给 yaml 文件路径,代码 `parse_brief()` 解析。

```python
brief = parse_brief("examples/demo_brief.yaml")
```

#### 字段规范

必填字段（4 项）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `title` | str | PPT 主标题,≤ 30 字 |
| `outline` | list[str] | 章节大纲,建议 4-6 项 |
| `theme` | str | `tech_blue` 或 `.pptx` 文件路径 |
| `output` | str | 输出 .pptx 路径,支持 `~` |

可选字段（7 项）：

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `subtitle` | str | `""` | 封面副标题 |
| `page_count_target` | int | None（自动估算） | 目标页数 |
| `key_points` | list[str] | `[]` | 核心论点,用于 bullet_list / summary |
| `reference_pptx` | str | None | 参考 pptx，用于风格学习 |
| `audience` | str | None | 受众描述（影响措辞复杂度） |
| `duration_min` | int | None | 演讲时长（影响页数估算） |
| `brand_colors` | list[str] | None | 品牌色 hex 列表 |

完整示例见 [brief.example.yaml](brief.example.yaml)。

#### 校验逻辑

`parse_brief()` 在 `REQUIRED - set(data.keys())` 非空时抛出 `ValueError`：

```python
missing = REQUIRED - set(data.keys())
if missing:
    raise ValueError(f"brief 缺字段: {missing}")
```

---

### Step 2：load_theme

#### 内置主题路径

当 `brief["theme"] == "tech_blue"` 时直接 import：

```python
from themes import tech_blue as T
theme = T
```

`tech_blue.py` 提供 11 个 `make_*()` 函数对应所有支持的 layout。
详见 [themes/tech_blue.py](themes/tech_blue.py)。

#### 用户给 .pptx 模板

当 `brief["theme"]` 以 `.pptx` 结尾时,走 [template-ingest.md](template-ingest.md) 流程：

1. Claude 调用 `reading.md` 中的 `analyze_pptx()` 分析模板
2. 提取颜色、字体、spacing 规则
3. 生成临时 `theme_custom.py` 供本次 run 使用

`workflow.py` 骨架对此路径抛出 `NotImplementedError`,提示走 LLM 流程。

#### 兜底降级

模板太复杂（> 10 个 layout 全部用过）→ 降级为复用 master slide + theme 颜色,
自定义 layout 用 `bullet_list` 兜底,不强行还原所有原始 layout。

---

### Step 3：generate_outline

`generate_outline(brief, theme)` 根据 brief 生成 page_spec list。
骨架版返回固定结构跑通 pipeline；真实运行由 LLM 替换此函数。

#### 页数估算

当 `brief["page_count_target"]` 未指定时：

```
total = len(outline) × 1.5 + 4
# +4 = 封面 + 目录 + 总结 + 封底
```

示例：4 章节 outline → 10 页；6 章节 → 13 页。

当指定了 `duration_min` 时可进一步修正：

```
total_by_time = duration_min × 1.2   # 约每分钟 1.2 页
total = max(estimate_page_count, total_by_time)
```

#### 骨架版固定结构

```
封面 (cover)
目录 (toc)
章节扉页 × N (section_divider)
内容页 × N (bullet_list)
总结 (summary)
封底 (closing)
```

#### layout 预选规则（LLM 版）

LLM 根据每节要点数选择 layout：

| 要点数 | 推荐 layout |
|---|---|
| 1 | `single_focus` |
| 2 | `two_col_compare` |
| 3 | `three_col_cards` |
| 4–6 | `bullet_list` |
| ≥ 7 | `table` 或拆为 2 页 `bullet_list` |

#### 图表插入决策

每 4–5 页至少插入一张图（架构图 / 流程图 / 对比图）。
生成图需求 → 调 [[diagram]] skill 出 PNG → 用 `make_image_full()` 或 `make_two_col_compare()` 嵌入。

---

### Step 4：per-slide generate + vision QA 循环

#### generate_slide

`generate_slide(prs, spec, theme)` 按 spec["layout"] 动态调用 theme 的 `make_*()` 函数：

```python
def generate_slide(prs, spec, theme):
    fn = getattr(theme, f"make_{spec['layout']}")
    kwargs = {k: v for k, v in spec.items() if k != "layout"}
    return fn(prs, **kwargs)
```

#### render_one_slide

`render_one_slide(prs, idx, out_png)` 将当前 deck 导出 PDF 后用 pdftoppm 截取单页：

1. `prs.save("/tmp/killppts_render/current.pptx")`
2. `soffice --headless --convert-to pdf` → `current.pdf`
3. `pdftoppm -jpeg -r 120 -f idx -l idx` → `slide_only-NNN.jpg`
4. 重命名到 `out_png`

渲染约 3–4 秒/页。全 12 页 deck 约 8–10 秒（逐页渲染时可并发优化）。

#### vision_check

`vision_check(image_path, intent)` 检查渲染图是否符合预期。

**骨架实现**：打印路径后直接返回 `[]`（接受所有）。

**真实 Claude 实现**（见下文 Claude 会话内使用章节）：
- Claude 用 Read tool 读取 PNG
- 对照 [visual-qa.md](visual-qa.md) 检查清单出 issue JSON
- 格式：`[{"severity": "high"|"medium"|"low", "description": "...", "suggested_fix": "..."}]`

#### fix_slide

`fix_slide(slide, issues)` 根据 issue JSON 修改 slide。

**骨架实现**：打印修复数量后返回原 slide（不修）。

**真实实现**：按 `suggested_fix` 字段调用对应 theme.make_*() 或 helpers.set_text_run() 修复。

#### 主循环

完整伪代码（引用 [workflow.py](workflow.py) `run()`）：

```python
for idx, spec in enumerate(outline, 1):
    slide = generate_slide(prs, spec, theme)
    png_path = f"/tmp/killppts_render/page_{idx:02d}.png"

    try:
        render_one_slide(prs, idx, png_path)
    except subprocess.CalledProcessError:
        mark_review_needed(idx, "render_failed")
        continue

    attempts = 0
    issues = vision_check(png_path, intent=spec["layout"])
    while issues and attempts < 3:
        slide = fix_slide(slide, issues)
        render_one_slide(prs, idx, png_path)
        issues = vision_check(png_path, intent=spec["layout"])
        attempts += 1

    if issues:
        mark_review_needed(idx, "vision_unresolved", issues)
```

vision_check 详细检查项见 [visual-qa.md](visual-qa.md)。

---

### Step 5：deck_review

全 deck 渲染完成后执行跨页一致性检查。

#### 字体一致性

抽取 5 页 text run，检查 East Asian typeface 都是 `Microsoft YaHei`：

```python
for slide in prs.slides[:5]:
    for shape in slide.shapes:
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    ea = run.font._element.rPr.get("eastAsiaTheme")
                    # 或检查 run.font.name 是否为 "Microsoft YaHei"
```

#### 页脚 / 页码完整性

检查每页 footer 区域是否有页码文本框且内容正确。

#### 章节扉页与内容页配对

验证每个 `section_divider` 后都至少有 1 个内容 layout（`bullet_list` / `two_col_compare` / `table`）。
若 section 后直接是下一个 section → 标 `review_needed`（可能 outline 生成时跳过了内容页）。

#### 颜色一致性

品牌主色（`#1B3F8B`）和强调色（`#00B4D8`）不得被其他颜色大量替代。

---

### Step 6：交付

```python
out = Path(brief["output"]).expanduser()
out.parent.mkdir(parents=True, exist_ok=True)
prs.save(str(out))
```

打印输出路径和 review-needed 清单：

```
Done: /path/to/output.pptx
Warning: 2 pages need review:
  - page 3: render_failed
  - page 7: vision_unresolved
```

给用户最后人工核审建议：
- 用 PowerPoint / LibreOffice 打开检查 review-needed 页
- 重点看中文字体是否正确渲染（跨平台字体替换风险）
- 确认图表数据准确性（skill 不校验业务逻辑）

---

## workflow.py 可跑骨架

完整代码：[workflow.py](workflow.py)。

### 安装依赖

```bash
pip install python-pptx pyyaml
# 系统依赖（渲染用）：
# macOS: brew install --cask libreoffice && brew install poppler
# Ubuntu: sudo apt install libreoffice poppler-utils
```

### 运行示例

```bash
cd skills/pptx-deck
python3 workflow.py examples/demo_brief.yaml
```

输出：`examples/sample_output.pptx`（12 页）+ 渲染 PNG 到 `/tmp/killppts_render/`。

### 仅测试 parse_brief

```bash
python3 -c "
import sys; sys.path.insert(0, 'skills/pptx-deck')
from workflow import parse_brief
b = parse_brief('skills/pptx-deck/examples/demo_brief.yaml')
print('outline:', b['outline'])
print('theme:', b['theme'])
print('output:', b['output'])
"
```

---

## 在 Claude 会话内的使用

Claude 调用本 workflow 时，`vision_check` 占位返回 `[]`，真实自检由 Claude 自己用 Read 工具看图实现。

### 标准流程（半自动）

1. Claude 调 `python3 workflow.py brief.yaml` 跑完全部 `generate_slide` + `render_one_slide`
   （占位 `vision_check` 接受所有，`fix_slide` 不修）
2. Claude 用 Read tool 逐张读取 `/tmp/killppts_render/page_NN.png`
3. 对照 [visual-qa.md](visual-qa.md) 检查清单，输出 issue JSON
4. 按 issue 调用对应 `theme.make_*()` 或 `H.set_text_run()` 修复 page_spec
5. 重新跑 `render_one_slide(prs, idx, png_path)` 确认修复
6. 通过后进下一页

### 全自动模式（patch vision_check）

Claude 可以 patch `workflow.py` 的 `vision_check` 函数，改成内嵌 Read 调用：

```python
# patch 示例（Claude 在会话内临时替换）
def vision_check(image_path, intent):
    # 改为调用 Claude Read tool 读图后返回 issue JSON
    # 此处为伪代码；真实实现依赖 Claude 框架
    from claude_tools import read_image_and_check
    return read_image_and_check(image_path, intent)
```

更自动化，适合批量生成场景。

### issue JSON 格式

```json
[
  {
    "severity": "high",
    "description": "标题文字溢出右边界约 15px",
    "suggested_fix": "缩短标题至 ≤ 25 字，或将字号从 36pt 降至 28pt"
  },
  {
    "severity": "medium",
    "description": "bullet_list 第 3 项字体为 Arial，应为 Microsoft YaHei",
    "suggested_fix": "调用 H.set_text_run(run, font_name='Microsoft YaHei')"
  }
]
```

severity 处理规则：
- `high` → 必须修复，否则标 `review_needed`
- `medium` → 尝试修复，失败后可接受
- `low` → 记录但不阻塞流程

---

## 关键设计决策

### 逐页渲染（非全 deck）

单页 PDF→PNG 约 3–4s，全 deck 12 页约 8–10s（soffice 启动开销摊薄后）。
逐页渲染的优势：发现问题后可立即修复当页，不需要重跑全 deck。
代价：每页都要 `prs.save()` + 转 PDF，IO 较重。

### fix 失败 ≤ 3 次降级

避免死循环。`attempts >= 3` 且 `issues` 仍存在 → 标 `review_needed`，人工最终审。
三次限制对应：初次渲染 → 修复一 → 修复二。第三次仍失败说明是系统性问题。

### 不在 workflow.py 内嵌 LLM 调用

保持 skill 文档+脚本边界：
- `workflow.py` 是纯 Python 的可测试脚本
- LLM 调用由 Claude 框架（Claude Code）做
- `generate_outline` / `vision_check` / `fix_slide` 是 LLM 的"插槽"，骨架版给占位实现

### render 失败时不静默跳过

`subprocess.CalledProcessError` 捕获后一定标 `review_needed`，不允许静默继续。
因为后续 vision_check 依赖渲染图，渲染失败后 vision 也无法运行。

---

## 与其他 skill 的接口

| skill | 调用方向 | 用途 |
|---|---|---|
| [[pptx]] `helpers.py` | workflow → pptx | `set_text_run()` / `add_picture()` / `rgb()` 等底层操作 |
| [[pptx]] `scripts/office/` | 独立调用 | `soffice` 转 PDF 的底层命令封装 |
| [[pptx]] `reading.md` | template-ingest 内调用 | 分析用户提供的 .pptx 模板 |
| [[pptx-deck]] `template-ingest.md` | load_theme 内调用 | 用户给 .pptx 时的风格学习流程 |
| [[diagram]] | generate_outline 内调用 | 需要架构图/流程图时出 PNG |
| [[pptx-deck]] `visual-qa.md` | vision_check 参考 | 视觉检查清单和 issue JSON 格式规范 |

---

## Anti-prompt

以下是使用本 workflow 时的禁止项：

- **不要在 workflow.py 内嵌 LLM API 调用**
  workflow.py 必须是可以在没有 Claude 环境时独立运行的脚本

- **不要在 fix_slide 里"猜"修法**
  `issues` JSON 应明确提供 `suggested_fix`；fix_slide 只执行，不推断

- **不要 vision_check 失败 N 次后还硬重试**
  超过 3 次直接降级 → `review_needed`，避免死循环浪费时间

- **不要跨 deck 复用 prs 对象**
  每次 `run()` 必须起新 `Presentation()`，不允许在多次调用间复用

- **render 失败时不要静默跳过**
  一定标 `review_needed` 并 `continue`，不要假装渲染成功继续 vision_check

- **不要跳过 deck_review（Step 5）**
  单页自检通过不代表跨页一致性没问题；字体/页脚/配对必须整体检查

- **不要在 generate_outline 骨架版硬编码业务内容**
  骨架版 `generate_outline` 只用于跑通 pipeline，真实内容由 LLM 替换整个函数

---

## 常见问题

### Q: soffice 命令找不到

```bash
# macOS
brew install --cask libreoffice
# Ubuntu
sudo apt install libreoffice
```

验证：`soffice --version`

### Q: pdftoppm 命令找不到

```bash
# macOS
brew install poppler
# Ubuntu
sudo apt install poppler-utils
```

### Q: 中文字体在渲染 PNG 中显示为方块

soffice 渲染需要系统安装 Microsoft YaHei 字体：

```bash
# macOS：从 Windows VM 或合法来源拷贝字体到
cp "Microsoft YaHei.ttf" ~/Library/Fonts/
fc-cache -fv
```

或者降级使用 `PingFang SC`（macOS 内置），并在 brief 中指定 `brand_colors`。

### Q: vision_check 骨架版全部接受，如何接入真实检查？

参见上文"在 Claude 会话内的使用 — 全自动模式"章节。
真实检查由 Claude 用 Read tool 读 PNG，对照 [visual-qa.md](visual-qa.md) 出 issue JSON。

### Q: 如何只重跑单页而不跑全 deck？

```python
# 在 Python shell 或临时脚本里
import sys; sys.path.insert(0, "skills/pptx-deck")
from pptx import Presentation
from pptx.util import Inches
from workflow import parse_brief, load_theme, generate_outline, generate_slide, render_one_slide

brief = parse_brief("examples/demo_brief.yaml")
theme = load_theme(brief["theme"])
outline = generate_outline(brief, theme)

prs = Presentation()
prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)

idx = 3  # 只跑第 3 页
spec = outline[idx - 1]
generate_slide(prs, spec, theme)
render_one_slide(prs, idx, f"/tmp/killppts_render/page_{idx:02d}.png")
```
