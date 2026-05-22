# iLovePPT 详细使用手册

> 版本：v2.0 | 最后更新：2026-05-22 | 覆盖：完整 API、所有 layout、工作流内部、故障排查、二次开发

---

## 目录

1. [文档导读](#1-文档导读)
2. [项目概述](#2-项目概述)
3. [安装与环境配置](#3-安装与环境配置)
   - [3.1 依赖全清单](#31-依赖全清单)
   - [3.2 各依赖安装命令](#32-各依赖安装命令)
   - [3.3 中文字体配置](#33-中文字体配置微软雅黑)
   - [3.4 check_deps.sh 用法](#34-check_depssh-用法与输出解读)
   - [3.5 Python 版本要求](#35-python-版本要求)
4. [第一次使用——完整走一遍](#4-第一次使用完整走一遍)
   - [4.1 跑 demo_plan.json](#41-跑-demo_planjson-的完整命令)
   - [4.2 终端输出逐步解释](#42-逐步解释终端输出)
   - [4.3 产物说明](#43-产物-sample_outputpptx-在哪长什么样)
   - [4.4 如何查看产物](#44-如何把产物转成图片查看)
5. [brief.yaml 完全参考](#5-briefyaml-完全参考)
   - [5.1 双路输入说明](#51-双路输入自由对话-vs-briefyaml)
   - [5.2 字段详解](#52-每个字段详解)
   - [5.3 brief 示例](#53-一个最小-brief-示例--一个完整-brief-示例)
   - [5.4 字段校验规则](#54-字段校验规则)
6. [11 种版式（layout）详解](#6-11-种版式layout详解)
7. [工作流程详解](#7-工作流程详解)
8. [视觉自检机制](#8-视觉自检机制)
9. [主题与配色](#9-主题与配色)
   - [9.1 内置 tech_blue 详解](#91-内置-tech_blue-详解)
   - [9.2 10 套预设色板](#92-10-套预设色板完整表格)
   - [9.3 切换色板](#93-切换色板的方法)
   - [9.4 新建主题](#94-新建一套主题的完整步骤)
10. [从模板提取主色与字体（template-extract）](#10-从模板提取主色与字体template-extract)
11. [diagram skill 用法](#11-diagram-skill-用法)
    - [11.1 工具选型决策表](#111-工具选型决策表)
    - [11.2 draw.io 用法](#112-drawio-用法)
    - [11.3 Mermaid 用法](#113-mermaid-用法)
    - [11.4 matplotlib 用法](#114-matplotlib-用法)
    - [11.5 pptx-native 用法](#115-pptx-native-用法)
    - [11.6 图片嵌入 PPT](#116-出的图怎么嵌入-ppt)
12. [pptx skill 单独用法](#12-pptx-skill-单独用法)
    - [12.1 读取已有 PPT](#121-读取已有-ppt-提取内容)
    - [12.2 基于模板局部修改](#122-基于模板局部修改)
    - [12.3 helpers.py API 速查表](#123-helperspy-13-个函数-api-速查表)
13. [在 Claude Code 中集成](#13-在-claude-code-中集成)
14. [故障排查大全](#14-故障排查大全)
15. [进阶：二次开发](#15-进阶二次开发)
16. [命令速查表](#16-命令速查表)
17. [附录](#17-附录)

---

## 1. 文档导读

### 这份手册 vs USAGE.zh.md 的区别

| 文档 | 定位 | 适合 |
|---|---|---|
| `USAGE.zh.md` | 快速上手速查 | 第一次跑通、找命令、确认字段名 |
| `docs/MANUAL.zh.md`（本文） | 完整大全（700+ 行） | 深度理解机制、定制主题、二次开发、故障排查 |

两份文档并存：USAGE 是速查，MANUAL 是大全。不冲突，功能互补。

### 不同读者看哪几章

| 读者 | 推荐章节 |
|---|---|
| **只想跑起来** | 第 3 章（安装）→ 第 4 章（快速试用） |
| **想自定义 brief** | 第 5 章（brief 字段）→ 第 6 章（layout 选型） |
| **想定制配色/主题** | 第 9 章（主题与配色）→ 第 10 章（模板提取主色与字体） |
| **想生成架构图** | 第 11 章（diagram 工具链） |
| **想单独操作 PPT 文件** | 第 12 章（pptx skill 独用） |
| **想二次开发** | 第 7 章（工作流内部）→ 第 15 章（扩展指南） |
| **遇到报错** | 第 14 章（故障排查） |

---

## 2. 项目概述

### iLovePPT 是什么

iLovePPT 是一个端到端 PPT 生成 skill 库，目标是**复制人类快速生成 PPT 的能力**。你输入主题与要点（brief.yaml 或自由对话），工具自动：

- 拓写每页文案（标题/要点/对比/数据）
- 选择合适的版式（11 种 layout）
- 嵌入架构图、流程图、可视化图表
- 套用统一风格（默认科技蓝主题，10 套色板可选）
- 逐页渲染后视觉自检，问题自动修复

最终产物是一份可以直接在 PowerPoint 打开的 `.pptx` 文件。

### 3-skill 架构

```
用户输入（brief.yaml / 自由对话）
          │
          ▼
┌─────────────────────────────────────────┐
│            pptx-deck  skill              │
│  端到端生成器：主流程协调者              │
│                                          │
│  ┌──────────────┐  ┌──────────────────┐  │
│  │  pptx skill  │  │  diagram skill   │  │
│  │  底层读写    │  │  架构图/流程图   │  │
│  │  helpers.py  │  │  draw.io/mermaid  │  │
│  │  set_font    │  │  matplotlib      │  │
│  │  card/rect   │  │  pptx-native     │  │
│  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────┘
          │
          ▼
    完整 .pptx 产物
```

`pptx-deck` 是协调者，调用 `pptx` 做底层绘制，调用 `diagram` 出图，最终汇总成完整 deck。

### 与传统手工做 PPT 的区别

| 对比维度 | 传统手工 | iLovePPT |
|---|---|---|
| 文案来源 | 手写，逐页填充 | 从 brief 自动拓写 |
| 版式选择 | 手动挑模板 | 按要点数量自动选 layout |
| 配色一致性 | 手动改每个元素 | 统一色板常量，全 deck 联动 |
| 中文字体 | 容易 fallback | lxml 写 `<a:ea>` 节点，跨平台保证 |
| 视觉验证 | 目测，漏看 | 逐页渲染 PNG 自检，问题自动修复 |
| 可重现性 | 不可重现 | brief.yaml + deck_plan.json + build.py 可任意重跑 |

---

## 3. 安装与环境配置

### 3.1 依赖全清单

| 分类 | 依赖 | 作用 | 必填？ |
|---|---|---|---|
| **核心必需** | `python-pptx >= 1.0` | PPT 文件读写（OOXML 操作） | 是 |
| **核心必需** | `lxml >= 4.9` | 写 `<a:ea>` 中文字体节点 | 是 |
| **核心必需** | `pyyaml >= 6.0` | 解析 brief.yaml | 是 |
| **核心必需** | `Pillow >= 10.0` | 缩略图生成、图片处理 | 是 |
| **读取可选** | `markitdown[pptx]` | 从 .pptx 提取 Markdown 文本 | 否（仅读 PPT 时需要） |
| **渲染必需** | `soffice`（LibreOffice） | PPT → PDF 转换（视觉验证用） | 是（渲染验证必须） |
| **渲染必需** | `pdftoppm`（poppler） | PDF → PNG 截图（逐页自检用） | 是（渲染验证必须） |
| **画图可选** | `draw.io` | 多层架构图、矩阵图渲染 | 否（架构图时需要） |
| **画图可选** | `mmdc`（mermaid-cli） | 流程图、时序图渲染 | 否（流程图时需要） |
| **画图可选** | `matplotlib >= 3.7` | 柱状图、雷达图、仪表盘 | 否（数据可视化时需要） |

> ⚠️ `soffice` 和 `pdftoppm` 虽在 `pyproject.toml` 中未列为 Python 依赖（它们是系统命令），但执行渲染验证时是硬依赖。若缺失，`render_one_slide()` 会抛出 `RuntimeError`。

### 3.2 各依赖安装命令

```bash
# Python 核心依赖
pip3 install python-pptx lxml pyyaml Pillow

# 或一键装全（通过 pyproject.toml）
pip3 install -e ".[read,diagram,dev]"

# 渲染依赖（macOS）
brew install --cask libreoffice    # 提供 soffice 命令
brew install poppler               # 提供 pdftoppm 命令

# 画图依赖（按需）
brew install --cask drawio         # draw.io GUI + CLI
brew install mermaid-cli           # 或用 npm: npm install -g @mermaid-js/mermaid-cli
pip3 install matplotlib            # 数据可视化

# Linux（Ubuntu/Debian）等价命令
sudo apt install libreoffice
sudo apt install poppler-utils
```

### 3.3 中文字体配置：微软雅黑

#### 为什么默认微软雅黑

`helpers.py` 中的默认字体设置为：

```python
FONT_CN = "Microsoft YaHei"
```

选择微软雅黑而非 PingFang SC（苹方）的原因：
- 微软雅黑可在 macOS / Linux 上手动安装，跨平台部署简单
- PingFang SC 是 macOS 专有字体，在 Windows PowerPoint 上 fallback 到宋体，视觉差异极大
- 商务 / 制度文件的目标受众主要在 Windows 环境

#### macOS 如何安装微软雅黑

微软雅黑是 Windows 系统字体，macOS 不自带。安装方式：

```bash
# 方式一：从 Windows 系统（或 VM）复制字体文件
cp "/path/to/windows/fonts/msyh.ttf"   ~/Library/Fonts/
cp "/path/to/windows/fonts/msyhbd.ttf" ~/Library/Fonts/   # 加粗版

# 方式二：从 Office for Mac 提取（若已安装）
# 字体通常在 /Library/Fonts/ 或 /Users/你的用户名/Library/Fonts/

# 验证安装
fc-list | grep -i "yahei"
# 应输出类似：/Users/xxx/Library/Fonts/msyh.ttf: Microsoft YaHei:style=Regular
```

安装后需重启 LibreOffice，使其重新加载字体缓存。

#### 不装的后果

不安装微软雅黑时：
- **Python 端**（python-pptx 写文件）：字体名仍写入 XML，文件结构正确
- **LibreOffice 渲染端**（视觉验证 PNG）：LibreOffice 找不到字体，按 fallback 链选择替代字体
- **结果**：渲染 PNG 的字体与 Windows PowerPoint 打开效果不一致，视觉自检可能报字体问题

#### fallback 链

```python
FONT_FALLBACK_CHAIN = (
    "Microsoft YaHei",
    "PingFang SC",
    "Source Han Sans CN",
    "Heiti SC",
)
```

LibreOffice 渲染时按此链顺序查找可用字体，找到即用。macOS 通常回落到 PingFang SC。

### 3.4 check_deps.sh 用法与输出解读

```bash
# 从项目根目录执行
bash skills/pptx/scripts/check_deps.sh
```

脚本检测项：
1. `python-pptx` — Python 包
2. `lxml` — Python 包
3. `markitdown[pptx]` — Python 包（可选）
4. `Pillow (PIL)` — Python 包
5. `soffice` — 系统命令
6. `pdftoppm` — 系统命令
7. 微软雅黑字体（仅 macOS）

输出示例：

```
== iLovePPT pptx skill 依赖检查 ==
  ✅ python -m pptx
  ✅ python -m lxml
  ❌ python -m markitdown  → pip3 install 'markitdown[pptx]'
  ✅ python -m PIL
  ✅ soffice
  ✅ pdftoppm
  ⚠️  微软雅黑未装（LibreOffice 渲染中文会 fallback）
      手动方案：放雅黑字体到 ~/Library/Fonts/，或接受 fallback
完成。
```

- `✅` 表示已装且可用
- `❌` 表示缺失，后跟安装命令
- `⚠️` 表示不影响功能运行但建议安装

### 3.5 Python 版本要求

`pyproject.toml` 中明确：

```toml
requires-python = ">=3.10"
```

需要 Python **3.10 或更高版本**。主要原因：
- 使用了 `int | str`、`str | Path` 等 union type hint 语法（Python 3.10+）
- `match/case` 语句未使用，但类型注解风格依赖 3.10+

验证：

```bash
python3 --version  # 应输出 Python 3.10.x 或更高
```

---

## 4. 第一次使用——完整走一遍

### 4.1 跑 demo_plan.json 的完整命令

```bash
# 进入项目根目录
cd /path/to/iLovePPT

# 确认依赖已装
bash skills/pptx/scripts/check_deps.sh

# 运行 demo（从项目根目录执行）
python3 skills/pptx-deck/build.py skills/pptx-deck/examples/demo_plan.json
```

加 `--no-render` 仅生成 .pptx，跳过 PNG 渲染：

```bash
python3 skills/pptx-deck/build.py skills/pptx-deck/examples/demo_plan.json --no-render
```

### 4.2 逐步解释终端输出

build.py 正常运行时，终端输出如下（以 demo_plan.json 的 deck 为例）：

```
slide 1/12: cover       → /tmp/iloveppt_render/page_01.png
slide 2/12: toc         → /tmp/iloveppt_render/page_02.png
slide 3/12: section_divider → /tmp/iloveppt_render/page_03.png
slide 4/12: bullet_list → /tmp/iloveppt_render/page_04.png
...
slide 12/12: closing    → /tmp/iloveppt_render/page_12.png

Done: ./examples/sample_output.pptx
```

各行含义：

| 输出行 | 含义 |
|---|---|
| `slide N/M: layout` | 第 N 页（共 M 页），使用的 layout 类型 |
| `→ /tmp/.../page_NN.png` | 渲染 PNG 路径（build.py 机械输出） |
| `Done: <路径>` | 生成完成，产物路径 |
| `Warning: N pages need review:` | 有 N 页渲染失败，需人工审查 |
| `- page N: render_failed` | 第 N 页渲染失败（soffice/pdftoppm 问题） |

**视觉 QA 由 Claude 主导**：build.py 完成后，Claude 逐张 Read PNG，按 12 项 checklist 找问题，修改 deck_plan.json 后重新调用 build.py。

如果渲染工具（soffice / pdftoppm）未安装，会看到：

```
slide 1/12: cover
  warning: render failed: soffice 未安装。请: brew install --cask libreoffice; marking review-needed
```

此时 deck 仍会生成，但所有页面标记为 `review_needed`。

### 4.3 产物 sample_output.pptx 在哪、长什么样

产物路径由 demo_plan.json 的 `output` 字段决定：

```json
"output": "./examples/sample_output.pptx"
```

因此产物在：`skills/pptx-deck/examples/sample_output.pptx`

demo deck 共 **12 页**，结构如下：

| 页码 | layout | 内容 |
|---|---|---|
| 1 | `cover` | 封面：大标题 "iLovePPT 自动化 PPT 生成" + 副标 |
| 2 | `toc` | 目录：4 个章节（动机/技术方案/效果数据/落地路径） |
| 3 | `section_divider` | 章节扉页：01 动机 |
| 4 | `bullet_list` | 内容页：动机 要点列表 |
| 5 | `section_divider` | 章节扉页：02 技术方案 |
| 6 | `bullet_list` | 内容页：技术方案 要点列表 |
| 7 | `section_divider` | 章节扉页：03 效果数据 |
| 8 | `bullet_list` | 内容页：效果数据 要点列表 |
| 9 | `section_divider` | 章节扉页：04 落地路径 |
| 10 | `bullet_list` | 内容页：落地路径 要点列表 |
| 11 | `summary` | 总结：核心结论（3 条 key_points） |
| 12 | `closing` | 封底："谢谢" |

### 4.4 如何把产物转成图片查看

**方式一：用 LibreOffice 打开**（推荐）

```bash
soffice --impress skills/pptx-deck/examples/sample_output.pptx
```

**方式二：转 PDF 后逐页看**

```bash
# 转 PDF
soffice --headless --convert-to pdf \
  skills/pptx-deck/examples/sample_output.pptx \
  --outdir /tmp/

# 用系统 PDF 阅读器打开
open /tmp/sample_output.pdf   # macOS
```

**方式三：转 PNG 逐页查看**

```bash
# 转 PDF 后用 pdftoppm 批量转 PNG
soffice --headless --convert-to pdf \
  skills/pptx-deck/examples/sample_output.pptx \
  --outdir /tmp/

pdftoppm -jpeg -r 150 /tmp/sample_output.pdf /tmp/sample_slides

# 查看所有页
ls /tmp/sample_slides-*.jpg
open /tmp/sample_slides-1.jpg   # macOS 打开第 1 页
```

---

## 5. brief.yaml 完全参考

### 关于输入与构建的分工

**brief.yaml 是用户→Claude 的输入**，不是 build.py 的直接输入。build.py 的输入是 Claude 产出的 `deck_plan.json`。

流程：`brief.yaml（用户写）→ Claude 读取并规划 → deck_plan.json（Claude 写）→ build.py 渲染`

### 5.1 双路输入：自由对话 vs brief.yaml

`pptx-deck` skill 支持两种输入方式，均可触发完整 7 步生成流程：

**路 A — 自由对话**：在 Claude Code 对话框中说"帮我做一份 PPT"，Claude 会追问必填字段：

```
请提供以下信息以生成 PPT：
1. 主题（≤ 20 字）
2. 章节/大纲（建议 4-6 个）
3. 主题风格（默认 tech_blue，或给 .pptx 模板路径提取主色与字体）
4. 输出路径
（可选）受众、时长、关键论点、目标页数、品牌色
```

**路 B — brief.yaml**：直接提供 YAML 文件路径，Claude 读取后产出 `deck_plan.json`，再调用 build.py。

两种路最终都由 Claude 产出 `deck_plan.json` 交给 `build.py` 渲染。

### 5.2 每个字段详解

#### 必填字段（4 项）

| 字段名 | 类型 | 必填 | 约束 | 示例 | 说明 |
|---|---|---|---|---|---|
| `title` | `str` | 是 | ≤ 30 字 | `"AI 4A 架构评审办法 v1.0"` | PPT 主标题，显示在封面大字 |
| `outline` | `list[str]` | 是 | 建议 4-6 项 | `["背景", "方案", "数据"]` | 章节大纲，决定 section_divider 数量 |
| `theme` | `str` | 是 | 内置主题名或 .pptx 路径 | `"tech_blue"` 或 `"./template.pptx"` | 内置只有 `tech_blue`；其他路径走 template-extract |
| `output` | `str` | 是 | 支持 `~` 展开 | `"./out/deck.pptx"` | 产物 .pptx 保存路径，父目录不存在会自动创建 |

#### 可选字段（7 项）

| 字段名 | 类型 | 默认值 | 约束 | 示例 | 说明 |
|---|---|---|---|---|---|
| `subtitle` | `str` | `""` | ≤ 30 字 | `"技术 + 业务 协同评审机制"` | 封面副标题 |
| `audience` | `str` | `None` | 自由文本 | `"技术 + 业务团队，约 30 人"` | 影响 LLM 拓写的语气（executive/technical/general/sales） |
| `duration_min` | `int` | `None` | 正整数（分钟） | `15` | 影响页数估算（约 1 分钟 1.5 页） |
| `key_points` | `list[str]` | `[]` | 每条 ≤ 18 字 | `["强制嵌入研发流程", "5 阶段评审"]` | 核心论点，用于 summary/bullet_list |
| `page_count_target` | `int` | `None` | 正整数 | `20` | 目标页数；不填时自动估算：`len(outline) × 1.5 + 4` |
| `brand_color` | `str` | `None` | 6 位 hex 含 # | `"#0B2A4A"` | 覆盖 theme 默认主色（Claude 在产出 deck_plan.json 时写入 theme token） |
| `reference_pptx` | `str` | `None` | 文件路径 | `"./corporate.pptx"` | 提供参考模板提取主色与字体（走 template-extract 流程） |

### 5.3 一个最小 brief 示例 + 一个完整 brief 示例

**最小 brief**（4 个必填字段）：

```yaml
title: "我的项目汇报"
outline:
  - "背景"
  - "方案"
  - "成果"
theme: tech_blue
output: ./my_deck.pptx
```

**完整 brief**（所有字段）：

```yaml
title: "AI 4A 架构评审办法 v1.0"
subtitle: "技术 + 业务 协同评审机制"
audience: "技术 + 业务团队，约 30 人"
duration_min: 15
outline:
  - "背景与意义"
  - "评审范围"
  - "评审流程（5 阶段）"
  - "组织保障"
  - "落地节奏"
key_points:
  - "强制嵌入研发流程"
  - "5 阶段评审，每阶段 ≤ 3 天"
  - "AI 助手提前预审"
theme: tech_blue
output: ./out/deck.pptx
page_count_target: 20
brand_color: "#0B2A4A"
reference_pptx: null
```

### 5.4 字段校验规则

brief.yaml 由 Claude 读取并校验（不是 build.py 直接解析）。Claude 检查必填字段后产出 `deck_plan.json`，build.py 只消费 `deck_plan.json`。

必填字段：`title` / `outline` / `theme` / `output`（4 项），任意缺一 Claude 会追问。

可选字段若缺失，Claude 按默认值填充：`subtitle` → `""`，`key_points` → `[]`，`page_count_target` → 按章节数估算（`len(outline) × 1.5 + 4`）。

**常见问题**：若 Claude 报告 brief 字段不完整，检查 brief.yaml 是否包含上述 4 个必填字段。

---

## 6. 11 种版式（layout）详解

11 种 layout 均在 `skills/pptx-deck/themes/tech_blue.py` 中实现，文案约束来自 `content-writing.md`。在 `deck_plan.json` 的每页 `"layout"` 字段中使用下方的版式名称。

---

### 6.1 cover — 封面

**函数签名**（来自 tech_blue.py）：

```python
def make_cover(prs: _Pres, title: str, subtitle: str) -> Slide:
```

**视觉描述**：全页深海蓝背景（`PRIMARY_DEEP = #0B2A4A`），大号白色主标题居左（48pt），小号浅蓝副标题（20pt）。

**适用场景**：每个 deck 固定只有 1 张，位于第 1 页。

**文案约束**：
- `title`：≤ 20 字
- `subtitle`：≤ 30 字，不堆头衔

**deck_plan.json 示例**：

```json
{
  "layout": "cover",
  "title": "2026 年 Q2 技术战略规划",
  "subtitle": "技术平台部 · 内部汇报"
}
```

---

### 6.2 toc — 目录

**函数签名**：

```python
def make_toc(prs: _Pres, sections: list[str]) -> Slide:
```

**视觉描述**：白底，顶部 "目录" 大标题（40pt，深海蓝），下方每章节一行，左侧两位数编号（26pt 科技蓝），右侧章节文字（20pt 灰色）。

**适用场景**：紧跟封面，全 deck 只出现 1 次。

**文案约束**：`sections` 列表 ≤ 6 项，每章节 ≤ 12 字，用动宾短语或名词性结构。

**deck_plan.json 示例**：

```json
{
  "layout": "toc",
  "sections": ["背景与意义", "技术方案", "效果数据", "落地路径"]
}
```

---

### 6.3 section_divider — 章节扉页

**函数签名**：

```python
def make_section_divider(prs: _Pres, num: int | str, title: str) -> Slide:
```

**视觉描述**：白底，左侧大色块（深海蓝，1.7" × 2.0"），色块内白色大数字（80pt），右侧章节标题（36pt 深海蓝加粗）。通过调用 `helpers.section_header()` 实现。

**适用场景**：每个章节开始前插入一张，视觉上标志章节切换。

**文案约束**：`num` 为章节序号（1、2、3...），`title` ≤ 10 字，与 toc 章节名严格对应。

**deck_plan.json 示例**：

```json
{
  "layout": "section_divider",
  "num": 1,
  "title": "背景与意义"
}
```

---

### 6.4 single_focus — 单点聚焦

**函数签名**：

```python
def make_single_focus(
    prs: _Pres,
    *,
    big_text: str = "",
    big_number: str = "",
    explanation: str = "",
) -> Slide:
```

**视觉描述**：白底，正中大号数字（120pt，科技蓝，居中），数字下方大文字（32pt，深海蓝，居中），最下方小号解释文字（14pt 灰色）。

**适用场景**：展示最关键的 1 个数字或 1 个核心论点，整 deck 建议用 1-2 次。

**文案约束**：`big_text` ≤ 12 字，`big_number` 为数字（如 "80%"、"3.2h"），`explanation` 1 行解释。不得放多个要点。

**deck_plan.json 示例**：

```json
{
  "layout": "single_focus",
  "big_number": "80%",
  "big_text": "成本降低",
  "explanation": "相比传统方式，3 个月实测数据"
}
```

---

### 6.5 compare — 双栏对比

**函数签名**：

```python
def make_compare(
    prs: _Pres,
    left_title: str,
    left_body: str,
    right_title: str,
    right_body: str,
) -> Slide:
```

**视觉描述**：顶部 "对比" 标题（28pt），下方左右两个等宽卡片（各 6"）。左卡片浅蓝背景（`PRIMARY_TINT`）带蓝色左边条；右卡片白底带青绿左边条（`ACCENT`）。

**适用场景**：两个方案对比、before/after 对比、优缺点分析。

**文案约束**：左右标题各 ≤ 6 字，句式对称（长度差不超过 2×），body 正文 ≤ 80 字。

**deck_plan.json 示例**：

```json
{
  "layout": "compare",
  "left_title": "方案 A",
  "left_body": "基于微服务，部署灵活，维护成本高，需要容器编排平台。",
  "right_title": "方案 B",
  "right_body": "基于单体架构，运维简单，扩展受限，适合初期快速交付。"
}
```

---

### 6.6 cards — 三栏卡片

**函数签名**：

```python
def make_cards(
    prs: _Pres,
    cards: list[dict[str, str]],
    title: str = "三栏",
) -> Slide:
```

**视觉描述**：顶部标题（28pt），下方 3 张等宽卡片（各 3.85"），奇偶卡片交替使用蓝色/青绿左边条。每卡标题（18pt 深海蓝加粗）+ body 正文（13pt 灰色）。

**注意**：若 `cards` 超过 3 项，会打印 warning 并只显示前 3 张。

**适用场景**：3 个并列的功能、特性、优势、步骤说明。

**文案约束**：每卡 `title` ≤ 6 字，`body` ≤ 30 字，三卡 body 长度差 ≤ 30%（视觉平衡）。

**deck_plan.json 示例**：

```json
{
  "layout": "cards",
  "title": "三大核心能力",
  "cards": [
    {"title": "自动生成", "body": "从 brief 一键产出完整 PPT，无需手动排版"},
    {"title": "视觉自检", "body": "逐页渲染并检查，字体/对齐/溢出问题自动修复"},
    {"title": "模板提取", "body": "给参考 .pptx，提取主色与字体，复刻品牌风格"}
  ]
}
```

---

### 6.7 bullet_list — 要点列表

**函数签名**：

```python
def make_bullet_list(prs: _Pres, title: str, items: list[str]) -> Slide:
```

**视觉描述**：顶部标题（28pt，深海蓝加粗），下方调用 `helpers.bullets()` 生成带 `▎` 前缀的现代 bullet 列表，行高 1.45，字号 16pt。

**适用场景**：常规内容页，3-6 个要点的陈述或步骤。最常用的 layout。

**文案约束**：每项 ≤ 14 字，句式一致（全动宾或全名词性，不混用），不应放 5+ 项（超出时拆页或换 table）。

**deck_plan.json 示例**：

```json
{
  "layout": "bullet_list",
  "title": "评审流程五阶段",
  "items": [
    "需求评审：明确范围与边界",
    "方案评审：技术可行性与风险",
    "代码评审：质量门禁",
    "集成评审：端到端验证",
    "上线评审：监控与回滚"
  ]
}
```

---

### 6.8 table — 表格

**函数签名**：

```python
def make_table(
    prs: _Pres,
    title: str,
    headers: list[str],
    rows: list[list[str]],
) -> Slide:
```

**视觉描述**：顶部标题（28pt），下方调用 `helpers.table_modern()` 生成现代表格。表头深海蓝背景白字，body 行交替浅蓝斑马纹（`PRIMARY_TINT`），关闭 firstRow/bandRow 防默认 banding 干扰。

**适用场景**：多维度数据对比、清单、矩阵式对比表。

**文案约束**：列 ≤ 5，行 ≤ 7，单元格 ≤ 8 字（不能塞段落）。

**deck_plan.json 示例**：

```json
{
  "layout": "table",
  "title": "各工具能力对比",
  "headers": ["工具", "适用图类", "学习曲线", "中文字体"],
  "rows": [
    ["draw.io", "架构/矩阵", "中", "强"],
    ["Mermaid", "流程/时序", "低", "中"],
    ["matplotlib", "数据可视化", "中", "需配置"]
  ]
}
```

---

### 6.9 pic_text — 图文并排

**函数签名**：

```python
def make_pic_text(
    prs: _Pres,
    title: str,
    image_path: str,
    points: list[dict[str, str]],
) -> Slide:
```

**视觉描述**：左侧图片（等比缩放，高度 5"），右侧最多 4 张小卡片（各 5.78" × 0.95"，带蓝色左边条），每卡显示 `title`（14pt 加粗）和 `body`（11pt 灰色）。

**注意**：`points` 超过 4 项时打印 warning 并截取前 4 项。

**适用场景**：架构图/流程图配文字说明，产品截图配功能说明。

**文案约束**：每卡 `title` ≤ 8 字，`body` ≤ 20 字；图片宽度 ≥ 1600px（保证清晰度）。

**deck_plan.json 示例**：

```json
{
  "layout": "pic_text",
  "title": "系统架构说明",
  "image_path": "./diagrams/arch.png",
  "points": [
    {"title": "接入层", "body": "支持 HTTP/gRPC 双协议"},
    {"title": "服务层", "body": "微服务，独立扩缩容"},
    {"title": "存储层", "body": "分库分表，读写分离"},
    {"title": "监控层", "body": "Prometheus + Grafana"}
  ]
}
```

---

### 6.10 summary — 核心结论

**函数签名**：

```python
def make_summary(
    prs: _Pres,
    conclusions: list[str],
    title: str = "核心结论",
) -> Slide:
```

**视觉描述**：顶部标题（32pt，深海蓝加粗），下方最多 5 条结论，每条左侧科技蓝色方块内白色序号（32pt），右侧结论文字（18pt 灰色）。

**注意**：`conclusions` 超过 5 项时打印 warning 并截取前 5 项。

**适用场景**：deck 结尾前的总结页，呼应 brief.key_points。

**文案约束**：3-5 条结论，每条 ≤ 18 字，包含数字佐证，不要重复 outline 章节名。

**deck_plan.json 示例**：

```json
{
  "layout": "summary",
  "title": "核心结论",
  "conclusions": [
    "生成效率提升 5×，从 2 小时降至 25 分钟",
    "视觉自检覆盖 12 项，问题漏检率 < 5%",
    "支持 10 套色板，品牌一致性达 100%"
  ]
}
```

---

### 6.11 closing — 封底

**函数签名**：

```python
def make_closing(prs: _Pres, subtitle: str = "谢谢") -> Slide:
```

**视觉描述**：全页深海蓝背景，居中大字 "谢谢"（64pt 白色加粗），下方小字 `subtitle`（16pt 浅蓝色）。

**适用场景**：每个 deck 固定只有 1 张，位于最后一页。

**文案约束**：`subtitle` ≤ 30 字，通常放联系方式或 "Q&A"，不要再列要点。

**deck_plan.json 示例**：

```json
{
  "layout": "closing",
  "subtitle": "欢迎交流 · 技术平台部"
}
```

---

## 7. 工作流程详解

v2 的生成流程由 Claude 驱动 7 步，`build.py` 负责机械渲染。

### 7 步 Claude 工作流

| 步骤 | 执行者 | 工作内容 |
|---|---|---|
| 1. 读 brief | Claude | 读取 brief.yaml 或与用户对话，补齐必填字段 |
| 2. 图层规划 | Claude | 判断哪些章节需要架构图/流程图/数据图（见 diagram-planning.md） |
| 3. 拓写文案 | Claude | 按 11 种 layout 文案约束产出每页内容（见 content-writing.md） |
| 4. 写 deck_plan.json | Claude | 输出完整 JSON，含 theme/output/slides 数组 |
| 5. 调用 build.py | Claude | `python3 skills/pptx-deck/build.py deck_plan.json` |
| 6. 视觉 QA | Claude | 逐页 Read PNG，按 12 项 checklist 找问题，修 deck_plan.json 后 rebuild |
| 7. 交付 | Claude | 给用户 .pptx 路径 + review_needed 清单（若有） |

### deck_plan.json 结构

build.py 的唯一输入：

```json
{
  "theme": "tech_blue",
  "output": "./out/deck.pptx",
  "slides": [
    { "layout": "cover", "title": "标题", "subtitle": "副标题" },
    { "layout": "toc", "sections": ["章节 1", "章节 2"] },
    { "layout": "bullet_list", "title": "要点", "items": ["...", "..."] }
  ]
}
```

### build.py — 机械构建器

**CLI**：

```bash
python3 skills/pptx-deck/build.py deck_plan.json
python3 skills/pptx-deck/build.py deck_plan.json --no-render   # 仅 .pptx，跳过 PNG
```

**做什么**：
1. 解析 `deck_plan.json`
2. 加载 theme（`tech_blue` 或 `_extract_theme_from_pptx` 提取的临时主题）
3. 逐页调用 `theme.make_<layout>(**fields)` 生成 slide
4. 保存 `.pptx`
5. 逐页调用 `soffice + pdftoppm` 渲染 PNG（除非 `--no-render`）

build.py **不含任何 LLM 调用**。视觉 QA 由 Claude 在 build.py 完成后读图处理。

### 加载主题

```
theme in THEMES（"tech_blue"）
  → 直接返回 tech_blue 模块

theme 以 ".pptx" 结尾
  → 检查文件存在
  → 调用 _extract_theme_from_pptx(pptx_path) 提取主色与字体
  → 动态生成临时主题模块并返回

其他值
  → 抛出 ValueError("未知 theme: ...")
```

**输出**：含 11 个 `make_*()` 函数的模块对象

**必填字段**：`title` / `outline` / `theme` / `output`（Claude 校验，缺一追问）

---

### 步骤二：load_theme — 加载主题

**函数**：`load_theme(theme_id: str) -> ModuleType`

**输入**：`brief["theme"]` 字符串

**做什么**：

```
theme_id in THEMES（"tech_blue"）
  → 直接返回 tech_blue 模块

theme_id 以 ".pptx" 结尾
  → 检查文件是否存在
  → 调用 _extract_theme_from_pptx(pptx_path) 提取主色与字体
  → 动态生成临时主题模块并返回

其他值
  → 抛出 ValueError("未知 theme: ...")
```

**输出**：含 11 个 `make_*()` 函数的模块对象

**内置主题注册表**：`THEMES: dict[str, ModuleType] = {"tech_blue": T}`，新主题在此注册。

### build.py 逐页渲染流程

```python
# 每页执行：
fn = getattr(theme, f"make_{spec['layout']}")
kwargs = {k: v for k, v in spec.items() if k != "layout"}
slide = fn(prs, **kwargs)

# 渲染 PNG（soffice + pdftoppm）
render_one_slide(prs, idx, out_png)
```

速度参考：~3-4 秒/页（soffice 启动开销约 1.5 秒）。

### deck_review — 跨页一致性（Claude 驱动）

build.py 完成后，Claude 执行跨页检查（见 workflow.md）：

- **字体一致性**：抽取 5 页 run，检查 `<a:ea>` typeface 是否全为 Microsoft YaHei
- **页脚/页码完整性**：非 cover/section_divider/closing 页面应有页脚和页码
- **章节扉页配对**：每个 section_divider 后至少有 1 个内容页
- **颜色一致性**：主色（PRIMARY #1E6FE0）和强调色（ACCENT #00D1C1）不被随机色替代

修复方式：Claude 修改 deck_plan.json 对应页字段，重新调用 build.py。修 ≤ 3 次仍有问题则标记 `review_needed`，给用户人工核审。

---

## 8. 视觉自检机制

### 逐页渲染的原因

每生成一页就渲染一次 PNG，而不是全 deck 生成后再批量检查。原因：

- **发现即修复**：逐页检查时发现问题可立即修复当页，不需重跑全 deck
- **代价可控**：soffice 启动开销在整条流程中分摊，12 页 deck 约 8-10 秒
- **失败隔离**：某页渲染失败不影响其他页继续处理

代价是每页都要 `prs.save() + soffice PDF` 转换，IO 较重。

### 12 项视觉 checklist

`visual-qa.md` 定义的完整检查清单：

| # | 检查项 | 说明 |
|---|---|---|
| 1 | 元素重叠 | 文字穿过形状、卡片相互覆盖、线条压住文字 |
| 2 | 文字溢出框 | 截断、标题换行成两行但装饰按一行布局 |
| 3 | 中文字体 fallback | Arial/cursive 花体/大间距宽体（期望 Microsoft YaHei） |
| 4 | 标题与内容区距离失衡 | 间距 > 0.8" 或 < 0.3" |
| 5 | 颜色对比度不足 | 深底深字/浅底浅字（WCAG AA 需 ≥ 4.5:1） |
| 6 | layout 与意图不符 | 要点 5 个却用了 single_focus |
| 7 | 数字/图表位置偏移 | textbox margin 未归零导致内容偏右/偏下 |
| 8 | 装饰配色不一致 | 色值不在 BRAND_\*/GRAY_\* 套色板内 |
| 9 | 留白边界不达标 | 左右 < 0.55"、底部 < 0.5" |
| 10 | 表格意外 banding | 横纹穿过单元格干扰阅读 |
| 11 | emoji 误用/方块显示 | 除 ⚠ ⛔ 🔒 外均不应出现 |
| 12 | 装饰大字号换行 | 180pt 数字或 single_focus 的 big_number 变两行 |

### v2 视觉 QA：Claude 主导

build.py 生成每页 PNG 后，Claude 用 Read 工具读取渲染 PNG，参照上述 12 项 checklist 输出 issue JSON：

```json
[
  {
    "severity": "high",
    "description": "标题文字溢出右边界",
    "suggested_fix": "缩短标题至 ≤ 25 字"
  }
]
```

Claude 收到 issue 后，修改 `deck_plan.json` 中对应页的字段（缩短文案 / 调小字号 / 换 layout），重新调用 `build.py` rebuild。修 ≤ 3 次仍有问题 → 标记 `review_needed`，不再重试。

**何时降级**：`review_needed` 页面给用户人工核审。Claude 不再强行重试 3 次以上。

### review_needed 清单怎么读

运行结束时若有问题页，输出如下：

```
Warning: 2 pages need review:
  - page 3: render_failed
  - page 7: vision_unresolved
```

| reason | 含义 | 处理建议 |
|---|---|---|
| `render_failed` | soffice 或 pdftoppm 报错，未能生成 PNG | 检查工具安装；重新跑该页 |
| `vision_unresolved` | 修复 3 次仍有 high severity issue | 用 PowerPoint/LibreOffice 手动打开该页调整 |

---

## 9. 主题与配色

### 9.1 内置 tech_blue 详解

`skills/pptx-deck/themes/tech_blue.py` 定义的色板和字体：

**色板常量**：

```python
PRIMARY_DEEP = RGBColor(0x0B, 0x2A, 0x4A)   # #0B2A4A 深海蓝（封面背景/表头）
PRIMARY      = RGBColor(0x1E, 0x6F, 0xE0)   # #1E6FE0 科技蓝（主色块/目录编号）
PRIMARY_TINT = RGBColor(0xE6, 0xF0, 0xFC)   # #E6F0FC 浅蓝底（左栏卡片/斑马纹）
ACCENT       = RGBColor(0x00, 0xD1, 0xC1)   # #00D1C1 青绿点睛（右栏卡片边条）
```

灰阶沿用 `helpers.py`：`H.GRAY_900(#1A1A1A)` / `H.GRAY_700(#4A4A4A)` / `H.GRAY_500(#8C8C8C)` / `H.GRAY_300(#D9D9D9)` / `H.GRAY_50(#FAFAFA)` / `H.WHITE(#FFFFFF)`

**字体常量**：

```python
FONT_HEADER = "Microsoft YaHei"   # 标题字体
FONT_BODY   = "Microsoft YaHei"   # 正文字体
FONT_NUM    = "Helvetica Neue"    # 数字装饰字体（大号数字、编号）
```

**字号体系**：

| 用途 | 字号 | 典型位置 |
|---|---|---|
| 封面主标题 | 48pt bold | `make_cover` |
| 目录大标题 | 40pt bold | `make_toc` |
| 章节扉页标题 | 36pt bold | `make_section_divider` |
| 内容页标题 | 28pt bold | 大多数 layout |
| 总结页标题 | 32pt bold | `make_summary` |
| 封底大字 | 64pt bold | `make_closing` |
| single_focus 大数字 | 120pt bold | `make_single_focus` |
| 章节扉页数字 | 80pt bold | `section_header` |
| bullet 正文 | 16pt | `make_bullet_list` |
| 表格正文 | 12pt | `make_table` |
| pic_text 卡片标题 | 14pt bold | `make_pic_text` |

### 9.2 10 套预设色板（完整表格）

来自 `skills/pptx/design-system.md`，通过修改 `helpers.py` 的 `BRAND_*` 常量切换：

| 主题名 | BRAND_PRIMARY | BRAND_DARK | BRAND_TINT | ACCENT |
|---|---|---|---|---|
| **科技蓝**（默认） | `#1E6FE0` | `#0B2A4A` | `#E6F0FC` | `#00D1C1` |
| **商务深蓝**（Midnight Executive） | `#1E2761` | `#0A1234` | `#CADCFC` | `#FFFFFF` |
| **党政红**（严肃中式） | `#8B1F24` | `#5E0E14` | `#FBE5E7` | `#EC0A1E` |
| **极简白**（高端 pitch） | `#212121` | `#000000` | `#F5F5F5` | `#FF6B35` |
| **咨询黑**（McKinsey 风） | `#1A1A1A` | `#000000` | `#E0E0E0` | `#C99A4D` |
| **莫兰迪灰** | `#6D6D6D` | `#3D3D3D` | `#E8E4E0` | `#B85042` |
| **薄荷绿**（消费品） | `#028090` | `#00A896` | `#D6F0EE` | `#F0C808` |
| **暖橙**（活力创业） | `#F96167` | `#C73E1D` | `#FFEDDB` | `#2F3C7E` |
| **灰盐**（学术） | `#50808E` | `#2C3E50` | `#ECEFF1` | `#E8A87C` |
| **酒红**（品质零售） | `#6D2E46` | `#4A1F30` | `#ECE2D0` | `#C99A4D` |

### 9.3 切换色板的方法

编辑 `skills/pptx/helpers.py` 顶部的 4 个 `BRAND_*` 常量：

```python
# 默认：科技蓝
BRAND_PRIMARY = RGBColor(0x1E, 0x6F, 0xE0)
BRAND_DARK    = RGBColor(0x0B, 0x2A, 0x4A)
BRAND_TINT    = RGBColor(0xE6, 0xF0, 0xFC)
ACCENT        = RGBColor(0x00, 0xD1, 0xC1)

# 切换为商务深蓝：
BRAND_PRIMARY = RGBColor(0x1E, 0x27, 0x61)
BRAND_DARK    = RGBColor(0x0A, 0x12, 0x34)
BRAND_TINT    = RGBColor(0xCA, 0xDC, 0xFC)
ACCENT        = RGBColor(0xFF, 0xFF, 0xFF)
```

修改后，所有调用 `H.BRAND_PRIMARY` / `H.BRAND_DARK` 的 helper 自动生效。

注意：`tech_blue.py` 中定义了独立的 `PRIMARY`/`PRIMARY_DEEP`/`PRIMARY_TINT`/`ACCENT` 常量（与 helpers.py 分开），若要同步修改还需更新 `tech_blue.py` 顶部对应常量。

### 9.4 新建一套主题的完整步骤

**第一步**：复制 tech_blue.py：

```bash
cp skills/pptx-deck/themes/tech_blue.py \
   skills/pptx-deck/themes/warm_orange.py
```

**第二步**：修改新文件顶部颜色和字体常量：

```python
# warm_orange.py 顶部
FONT_HEADER = "Microsoft YaHei"
FONT_BODY   = "Microsoft YaHei"
FONT_NUM    = "Helvetica Neue"

PRIMARY_DEEP = RGBColor(0xC7, 0x3E, 0x1D)   # #C73E1D
PRIMARY      = RGBColor(0xF9, 0x61, 0x67)   # #F96167
PRIMARY_TINT = RGBColor(0xFF, 0xED, 0xDB)   # #FFEDDB
ACCENT       = RGBColor(0x2F, 0x3C, 0x7E)   # #2F3C7E
```

**第三步**：在 `build.py` 的 `THEMES` 字典中注册：

```python
from themes import tech_blue as T
from themes import warm_orange as W   # 新增

THEMES: dict[str, ModuleType] = {
    "tech_blue": T,
    "warm_orange": W,   # 新增
}
```

**第四步**：在 brief.yaml 中使用：

```yaml
theme: warm_orange
```

---

## 10. 从模板提取主色与字体（template-extract）

### 何时用

当你已有一份制作精良的 .pptx，想复刻其配色和字体风格时使用。

在 `brief.yaml` 中设置：

```yaml
# 方式一：通过 theme 字段直接指向 .pptx
theme: "/path/to/your/corporate_template.pptx"

# 方式二：通过 reference_pptx 字段（Claude 读取后写入 deck_plan.json 的 theme 字段）
reference_pptx: "/path/to/your/corporate_template.pptx"
```

当 `deck_plan.json` 的 `theme` 字段以 `.pptx` 结尾时，`build.py` 自动触发 `_extract_theme_from_pptx()`。完整 6 步提取流程见 [template-extract.md](template-extract.md)。

### `_extract_theme_from_pptx()` 怎么工作

```python
def _extract_theme_from_pptx(pptx_path: str) -> ModuleType:
```

工作步骤：

1. 调用 `_extract_design_tokens(pptx_path)` 提取 design token
2. 读取 `tech_blue.py` 源码作为基础模板
3. 用提取的 token 替换字体/颜色常量字符串
4. 将修改后的源码写入 `/tmp/iloveppt_ingest/ingested_<stem>.py`
5. 用 `importlib` 动态加载该文件并返回模块

**提取内容**（`_extract_design_tokens`）：

- **字体**：从 slide master 中找第一个含 `<a:ea>` typeface 的 run，提取 East Asian 字体名
- **主色**：从 `ppt/theme/theme*.xml` 的 `<a:accent1>/<a:srgbClr>` 读取 6 位 hex 值

提取成功后，打印提示：

```
  extracted theme written to /tmp/iloveppt_ingest/ingested_corporate.py
     fonts: 微软雅黑
     primary: (30, 111, 224)
```

### 提取失败的 fallback 行为

`_extract_design_tokens` 为 best-effort 实现，所有提取步骤均在 `try/except` 内：

```python
tokens: dict[str, Any] = {}
try:
    prs = _Pres2(pptx_path)
except Exception:
    return tokens   # 返回空 dict
```

若提取失败（tokens 为空 dict 或缺失字段），`_extract_theme_from_pptx` 使用 tech_blue.py 默认值：
- 字体：`Microsoft YaHei`（未替换源码中的默认值）
- 主色：`PRIMARY = RGBColor(0x1E, 0x6F, 0xE0)` 保持不变

### 局限

- 只提取主色（accent1）和中文字体（ea typeface），不提取排版间距、装饰元素等
- 字体名替换使用精确字符串匹配，依赖 tech_blue.py 的默认值字符串格式
- 复杂模板（艺术字/3D效果/OLE嵌入）无法提取，自动退回 tech_blue 默认值
- 提取的是近似效果，不是像素级还原

---

## 11. diagram skill 用法

### 11.1 工具选型决策表

| 图类型 | 首选工具 | 切换条件 |
|---|---|---|
| 简单线性流程（≤ 8 节点） | Mermaid | 节点 > 10 或要精确配色 → draw.io |
| 多层架构/嵌套 subgraph | **draw.io** | 没有替代 |
| 类比/概念图 | draw.io | — |
| 矩阵/角色边界 | **draw.io** | Mermaid 形状有限 |
| 决策树（菱形判断） | **draw.io** | Mermaid 菱形不稳 |
| 数据可视化（柱/雷达） | matplotlib | 数据 > 5 行用 mpl |
| 卡片墙/icon grid | draw.io | 多 slide 复用 → draw.io PNG |
| ≤ 5 节点 slide 内简单关系 | **pptx-native** | 节点 > 5 → 切 draw.io |

**经验法则**：deck 总图数 ≤ 10 → 全 Mermaid；> 10 张或要"视觉一致" → 全 draw.io。不混搭（视觉割裂）。

### 11.2 draw.io 用法

**安装**：

```bash
brew install --cask drawio
# 验证：
ls /Applications/draw.io.app && echo "OK"
```

**headless CLI 渲染**：

```bash
/Applications/draw.io.app/Contents/MacOS/draw.io \
  --export --format png --width 3200 \
  --output out.png in.drawio
```

关键参数：
- `--format png`：输出 PNG（不用 SVG，LibreOffice 渲染不稳定）
- `--width 3200`：**必须显式指定**，默认 800px 嵌 PPT 模糊

**mxGraph XML 最小模板**：

```xml
<mxfile host="app.diagrams.net" version="30.0.1">
  <diagram name="my-diagram" id="D1">
    <mxGraphModel dx="1600" dy="900" page="1"
                  pageWidth="1600" pageHeight="900"
                  background="#FFFFFF">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="n1" value="节点 A" vertex="1" parent="1"
                style="rounded=1;arcSize=10;fillColor=#1E6FE0;strokeColor=#0B2A4A;
                       fontColor=#FFFFFF;fontSize=20;fontFamily=Microsoft YaHei;
                       fontStyle=1;whiteSpace=wrap;">
          <mxGeometry x="100" y="200" width="240" height="80" as="geometry" />
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

**8 大致丑坑速查**：

| 坑 | 解决 |
|---|---|
| 用 Heiti SC 作默认字体 | 改为 `fontFamily=Microsoft YaHei` |
| 大背景 box 加 `sketch=1` | 改为 `sketch=0` |
| 长英文串不换行 | 加 `whiteSpace=wrap` |
| 不加 `--width 3200` | 始终加 `--width 3200` |
| `value` 里裸 `\n` 换行 | 用 `&#xa;` 代替 |
| `&` / `<` 等特殊字符未转义 | `&` → `&amp;`，`<` → `&lt;` |
| edge 用纯坐标而非 source/target | 用 `source="n1" target="n2"` |
| 节点内用 emoji | 改用 ⚠ ⛔ ✓ 等 Unicode 符号 |

### 11.3 Mermaid 用法

**安装**：

```bash
brew install mermaid-cli
# 或 npm
npm install -g @mermaid-js/mermaid-cli
which mmdc  # 验证
```

**基本渲染命令**：

```bash
mmdc -i diag.mmd -o diag.png -w 2400 -H 1800 -b white
```

参数 `-w 2400` 保证嵌入 PPT 后不糊（与 draw.io 的 `--width 3200` 同理）。

**必须配置 themeVariables** 覆盖 Mermaid 默认棕色：

```
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#1E6FE0',
  'primaryTextColor': '#FFFFFF',
  'primaryBorderColor': '#0B2A4A',
  'lineColor': '#0B2A4A',
  'secondaryColor': '#E6F0FC',
  'clusterBkg': '#E6F0FC',
  'clusterBorder': '#1E6FE0',
  'fontFamily': 'Microsoft YaHei, sans-serif',
  'fontSize': '16px'
}}}%%
```

**4 种图类型**：

| 类型 | 适合场景 | 关键字 |
|---|---|---|
| `flowchart` | 线性流程、决策分支（≤ 10 节点） | `flowchart LR` |
| `sequenceDiagram` | 系统间调用、API 交互时序 | `sequenceDiagram` |
| `classDiagram` | 数据模型、继承关系 | `classDiagram` |
| `stateDiagram-v2` | 工作流状态、任务生命周期 | `stateDiagram-v2` |

### 11.4 matplotlib 用法

**安装**：

```bash
pip3 install matplotlib
```

**中文字体配置**（每个脚本顶部必须加）：

```python
import matplotlib
matplotlib.rcParams['font.sans-serif'] = [
    'Microsoft YaHei',
    'Source Han Sans CN',
    'DejaVu Sans',
]
matplotlib.rcParams['axes.unicode_minus'] = False  # 修复负号显示为方块
```

**输出 DPI**：始终用 `dpi=200`：

```python
plt.savefig("out.png", dpi=200, bbox_inches='tight', facecolor='white')
```

**3 类常用图**：

| 图类型 | 适合场景 |
|---|---|
| 柱状图（bar chart） | 分类对比、数据排名、同比环比 |
| 雷达图（radar chart） | 多维能力评估、多方案综合对比 |
| 仪表盘（gauge）| KPI 完成率、健康度评分、单一指标展示 |

### 11.5 pptx-native 用法

使用 `python-pptx` 的 `add_shape` / `add_connector` 直接在 slide 内画图，无需外部工具。

**适用条件**：
- 节点 ≤ 5
- 在 pptx-deck 流程内，无需引入额外工具
- 需要 PPT 打开后可编辑（draw.io 输出 PNG 为位图，不可编辑）

**核心 API**：

```python
# 圆角矩形节点
shape = slide.shapes.add_shape(1, left, top, width, height)  # 1 = ROUNDED_RECTANGLE

# 直线箭头
connector = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
connector.line.color.rgb = DARK
connector.line.width = Pt(2.0)
```

节点 > 5 时切换到 draw.io（坐标管理复杂度急剧上升）。

### 11.6 出的图怎么嵌入 PPT

调用 `helpers.py` 的 `embed_picture` 函数：

```python
from pptx.util import Inches
import helpers as H

# 单图全宽（全幅占满内容区）
H.embed_picture(slide, "arch.png", Inches(0.55), Inches(1.9), height=Inches(5.0))

# 双图并列（左右各半）
H.embed_picture(slide, "left.png",  Inches(0.55), Inches(1.9), height=Inches(4.5))
H.embed_picture(slide, "right.png", Inches(7.00), Inches(1.9), height=Inches(4.5))
```

分辨率原则：
- draw.io：`--width 3200`
- mmdc：`-w 2400`
- matplotlib：`dpi=200`

保证嵌入 PPT 后清晰，不出现上采样模糊。

---

## 12. pptx skill 单独用法

除了在 pptx-deck 流程中被调用，`pptx` skill 也可以单独使用。

### 12.1 读取已有 PPT 提取内容

**方式一：markitdown 提取文本**

```bash
pip3 install "markitdown[pptx]"
```

```python
from markitdown import MarkItDown
md = MarkItDown()
result = md.convert("deck.pptx")
print(result.text_content)  # 输出 Markdown 格式的所有文字
```

**方式二：python-pptx 遍历**

```python
from pptx import Presentation

prs = Presentation("deck.pptx")
for i, slide in enumerate(prs.slides, 1):
    print(f"\n=== Slide {i} ===")
    for shape in slide.shapes:
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                text = para.text.strip()
                if text:
                    print(f"  {text}")
```

**方式三：缩略图生成**（需要 soffice + Pillow）

```bash
python3 skills/pptx/scripts/thumbnail.py deck.pptx --cols 4
# 产物：thumbnails-N.jpg（每行 4 页）
```

### 12.2 基于模板局部修改

```python
from pptx import Presentation
import sys
sys.path.insert(0, "skills/pptx")
import helpers as H

# 加载模板，清空样例 slide
prs = Presentation("template.pptx")
H.clear_template_slides(prs)

# 添加新 slide 并修改内容
blank_layout = prs.slide_layouts[6]
slide = prs.slides.add_slide(blank_layout)

# 用 helpers 添加内容
H.rect(slide, H.LEFT_MARGIN, H.Inches(0), H.SLIDE_W, H.Inches(0.12), H.BRAND_PRIMARY)
# ... 添加更多内容

prs.save("output.pptx")
```

### 12.3 helpers.py 13 个函数 API 速查表

以下签名直接来自 `skills/pptx/helpers.py` 源码：

| 函数名 | 签名 | 用途 |
|---|---|---|
| `set_font` | `set_font(run: _Run, *, name=FONT_CN, size=14, bold=False, italic=False, color=GRAY_900) -> None` | 设置 textbox run 字体（含 lxml 写 `<a:ea>/<a:cs>` 保证中文跨平台） |
| `_fix_ph_font` | `_fix_ph_font(ph: Any, *, name=FONT_CN, size_pt=14, bold=False, color=GRAY_900) -> None` | 修复 placeholder 字体（slide master 继承的 ea 字体） |
| `clear_template_slides` | `clear_template_slides(prs: Presentation) -> None` | 清空模板自带样例 slide，保留 layout/master/theme |
| `fix_textbox_margins` | `fix_textbox_margins(tf: TextFrame) -> None` | textbox 四边 margin 全归零（消除默认 ~90000 EMU 内边距） |
| `no_fill` | `no_fill(shape: BaseShape) -> None` | shape 真透明填充（`fill.background()`） |
| `no_line` | `no_line(shape: BaseShape) -> None` | shape 真无边框（`line.fill.background()`） |
| `rect` | `rect(slide: Slide, x: Length, y: Length, w: Length, h: Length, color: RGBColor) -> Shape` | 创建无边框纯色矩形 |
| `card` | `card(slide: Slide, x: Length, y: Length, w: Length, h: Length, *, fill=WHITE, border=GRAY_300, accent: RGBColor | None = None) -> Shape` | 创建圆角矩形卡片，可选左侧 accent 色条 |
| `bullets` | `bullets(slide: Slide, x: Length, y: Length, w: Length, h: Length, items: list[str], *, size=14, accent_color=BRAND_PRIMARY, body_color=GRAY_900) -> Shape` | 生成带 `▎` 前缀的现代 bullet 列表（行高 1.45） |
| `table_modern` | `table_modern(slide: Slide, x: Length, y: Length, w: Length, h: Length, headers: list[str], rows: list[list[str]], *, header_fill=BRAND_DARK, header_color=WHITE, body_color=GRAY_900, zebra=GRAY_50, font_size=11, row_height=Inches(0.5)) -> Any` | 创建关闭 banding 的现代表格，手动斑马纹 |
| `page_decoration` | `page_decoration(slide: Slide, num: int | str, tint_color: RGBColor, *, x=Inches(8.8), y=Inches(0.25), w=Inches(4.4), h=Inches(2.0), size=140) -> Shape` | 右上角淡色装饰大数字（word_wrap=False） |
| `section_header` | `section_header(slide: Slide, title: str, num: int | str, color: RGBColor, *, block_x=Inches(0.55), block_y=Inches(1.9), block_w=Inches(1.7), block_h=Inches(2.0), title_x=Inches(2.55), title_y=Inches(2.3), title_w=Inches(10), title_h=Inches(1.2), num_size=80, title_size=36) -> tuple[Shape, Shape]` | 章节扉页：左色块+数字+右标题 |
| `embed_picture` | `embed_picture(slide: Slide, path: str | Path, x: Length, y: Length, *, height: Length | None = None, width: Length | None = None) -> Any` | 等比缩放嵌入图片（传 height 或 width 之一） |

---

## 13. 在 Claude Code 中集成

### 13.1 把 skills/ 安装到目标项目

**方式一：拷贝**（适合独立部署，两套代码独立维护）

```bash
cp -R /path/to/iLovePPT/skills/pptx       /path/to/your-project/.claude/skills/pptx
cp -R /path/to/iLovePPT/skills/pptx-deck  /path/to/your-project/.claude/skills/pptx-deck
cp -R /path/to/iLovePPT/skills/diagram    /path/to/your-project/.claude/skills/diagram
```

**方式二：软链接**（适合开发期，修改 iLovePPT 自动反映到目标项目）

```bash
ln -s /path/to/iLovePPT/skills/pptx       /path/to/your-project/.claude/skills/pptx
ln -s /path/to/iLovePPT/skills/pptx-deck  /path/to/your-project/.claude/skills/pptx-deck
ln -s /path/to/iLovePPT/skills/diagram    /path/to/your-project/.claude/skills/diagram
```

安装后目录结构应为：

```
your-project/
└── .claude/
    └── skills/
        ├── pptx/
        │   ├── SKILL.md
        │   ├── helpers.py
        │   └── ...
        ├── pptx-deck/
        │   ├── SKILL.md
        │   ├── build.py
        │   └── ...
        └── diagram/
            ├── SKILL.md
            └── ...
```

### 13.2 三个 skill 的触发关键词

来自各 SKILL.md frontmatter 的 `description` 字段：

**pptx-deck**（完整 PPT 生成）：
- deck / 演示 / PPT / 幻灯片 / 提案 / 路演 / 汇报 / 提报 / 提交报告 / brief.yaml / 自动生成 PPT / 帮我写 PPT

**pptx**（底层读写）：
- 读取 .pptx / 提取文字 / 解包 .pptx / 改模板 / unpack / 演示文稿 / 幻灯片（底层操作语境）

**diagram**（图表生成）：
- 架构图 / 流程图 / 矩阵 / 决策树 / draw.io / mermaid / sequence / 可视化

### 13.3 对话示例

| 用户说 | 触发 skill | Claude 行为 |
|---|---|---|
| "帮我做一份汇报 PPT" | `pptx-deck` | 追问 title/outline/theme/output |
| "给我做个路演 deck" | `pptx-deck` | 追问必填字段，生成完整 .pptx |
| "用这个 brief.yaml 生成 PPT" | `pptx-deck` | 读取 brief，产出 deck_plan.json，调用 build.py |
| "读一下这份 PPT 里有什么内容" | `pptx` | 用 markitdown 或遍历提取文字 |
| "在模板基础上改第 3 页的标题" | `pptx` | 用 clear_template_slides + 局部修改 |
| "画一个系统架构图" | `diagram` | 用 draw.io 生成多层架构图 PNG |
| "把这个流程画成流程图" | `diagram` | 用 Mermaid 生成流程图 |
| "画个柱状图对比这 5 个方案" | `diagram` | 用 matplotlib 生成柱状图 |

---

## 14. 故障排查大全

### 中文字体显示不正确（方块字 / Arial 显示汉字）

**症状**：渲染 PNG 中汉字显示为方块，或字形明显是 Arial 字体。

**原因**：LibreOffice 找不到 Microsoft YaHei，按 fallback 链替换。

**解决**：
```bash
# macOS 安装微软雅黑
cp msyh.ttf ~/Library/Fonts/
cp msyhbd.ttf ~/Library/Fonts/
fc-cache -fv
# 重启 LibreOffice
```

---

### soffice 命令找不到

**症状**：`RuntimeError: soffice 未安装。请: brew install --cask libreoffice`

**原因**：LibreOffice 未安装，或安装路径不在 PATH 中。

**解决**：
```bash
# macOS
brew install --cask libreoffice
# 验证
soffice --version
# 若 soffice 不在 PATH，直接用绝对路径（较少见）
/Applications/LibreOffice.app/Contents/MacOS/soffice --version
```

---

### pdftoppm 命令找不到

**症状**：`RuntimeError: pdftoppm 未安装。请: brew install poppler`

**解决**：
```bash
# macOS
brew install poppler
# 验证
pdftoppm -v
```

---

### draw.io 命令找不到

**症状**：运行 diagram 脚本时报 `draw.io.app` 不存在。

**解决**：
```bash
brew install --cask drawio
ls /Applications/draw.io.app   # 验证
```

---

### 卡片重叠（元素遮挡）

**症状**：`compare` 或 `cards` 版式中卡片互相覆盖。

**原因**：deck_plan.json 中字段过长，或 layout 函数中 x 坐标计算有误。

**解决**：
1. 检查 `make_cards` 的列间距：`x = Inches(0.55 + i * 4.15)`，共 3 列，最右列 `x = Inches(8.85)`，总宽度 `0.55 + 3.85 = 12.4"`，未超出 13.333"
2. 若是自定义 layout，检查 `x + w` 不超过 `13.333" - 0.55" = 12.78"`

---

### 文字溢出（标题/bullet 被截断）

**症状**：渲染 PNG 中文字在框外被裁剪，或省略号出现。

**原因**：textbox 高度不足，或字号过大，或 `word_wrap=False` 但文字过长。

**解决**：
1. 减少 brief 的字数（按照 content-writing.md 字数约束严格执行）
2. Claude 视觉 QA 返回 `suggested_fix: "字号过大"` → Claude 修 deck_plan.json 缩减文案，rebuild
3. 手动修改 deck_plan.json 中的文字，控制在约束范围内

---

### 表格横纹（banding 干扰）

**症状**：表格中出现意外的深色/浅色交替横纹，不是代码设定的斑马纹。

**原因**：`table_modern()` 已关闭 `firstRow`/`bandRow`，若仍出现可能是 python-pptx 版本问题。

**解决**：
```python
# 手动关闭 tblPr 的 banding 属性
from pptx.oxml.ns import qn
tblPr = tbl._tbl.find(qn("a:tblPr"))
if tblPr is not None:
    tblPr.set("firstRow", "0")
    tblPr.set("bandRow", "0")
```

---

### brief 字段缺失报错

**症状**：`ValueError: brief 缺字段: {'theme'}`

**解决**：检查 brief.yaml 是否包含 4 个必填字段（title / outline / theme / output），补充缺失字段。

---

### 模板提取失败

**症状**：`RuntimeError: 无法从 /tmp/... 加载 extracted theme`

**原因**：动态生成的 theme Python 文件语法错误，或 importlib 加载失败。

**解决**：
1. 检查 `/tmp/iloveppt_ingest/ingested_<stem>.py` 文件内容，确认替换的颜色 hex 为合法值
2. 确认模板 .pptx 可被 python-pptx 正常打开：`python3 -c "from pptx import Presentation; Presentation('template.pptx')"`
3. 若仍失败，在 deck_plan.json 中改用 `"theme": "tech_blue"` 跳过提取

---

### 渲染页数不对

**症状**：soffice 转出的 PDF 页数与 `len(prs.slides)` 不一致。

**原因**：`clear_template_slides` 未完全清理孤儿 rels，导致 soffice 解析错误。

**解决**：
```python
# 确认清理完整
H.clear_template_slides(prs)
assert len(prs.slides) == 0  # 或期望的页数
```

若仍有问题，检查 `part.rels` 中是否有残留 slide 引用（helpers.py 的 `clear_template_slides` 有处理逻辑）。

---

### soffice PDF 转换失败（CalledProcessError）

**症状**：`RuntimeError: soffice PDF 转换失败: <stderr 内容>`

**常见原因与解决**：

| stderr 内容 | 原因 | 解决 |
|---|---|---|
| `Error: no export filter` | pptx 格式不兼容 | 更新 LibreOffice 版本 |
| `libGL error` | GPU 渲染问题（Linux） | 加 `--headless` 参数（已有） |
| `锁定文件存在` | 另一个 soffice 进程占用 | 关闭所有 LibreOffice 窗口 |
| `字体未找到` | 字体缺失但不影响转换 | 安装对应字体或忽略 warning |

---

## 15. 进阶：二次开发

### 15.1 加一个新 layout 函数

以在 `tech_blue.py` 中新增 `make_image_full`（全幅图页）为例：

**第一步**：在 `tech_blue.py` 中添加函数：

```python
def make_image_full(prs: _Pres, title: str, image_path: str) -> Slide:
    """全幅图页：顶部标题 + 下方全宽图片。"""
    s = _blank_slide(prs)
    _add_title(s, title, size=28)
    H.embed_picture(s, image_path, Inches(0.55), Inches(1.8), height=Inches(5.2))
    return s
```

**第二步**：在 `content-writing.md` 补充对应文案约束（保持文档与代码同步）：

```markdown
| image_full | 标题 ≤ 20 字；图片宽度 ≥ 2400px | 用截图作为图片 |
```

**第三步**：在 `content-writing.md` 的拓写指令模板中补充 deck_plan.json 格式：

```
image_full:   { layout, title, image_path }
```

**第四步**：测试新 layout：

```python
# 在 tests/pptx_deck/test_tech_blue.py 添加
def test_make_image_full():
    prs = _new_prs()
    slide = T.make_image_full(prs, "架构示意图", "tests/fixtures/arch.png")
    assert slide is not None
```

### 15.2 加一个新主题

参见第 9.4 节"新建一套主题的完整步骤"，核心是：复制 tech_blue.py → 修改常量 → 在 build.py THEMES 注册。

### 15.3 视觉 QA 扩展

v2 的 QA 由 Claude 驱动：build.py 渲染 PNG 后，Claude 读图 → 输出 issue JSON → 修改 deck_plan.json → rebuild。

若需自动化 QA（不依赖交互式 Claude），可通过外部脚本调用 Claude API：

```python
def vision_check_external(image_path: str, intent: str) -> list[dict]:
    """调用外部视觉检查脚本（返回 issue JSON）。"""
    import json, subprocess
    result = subprocess.run(
        ["python3", "scripts/vision_check_claude.py", str(image_path), intent],
        capture_output=True, text=True
    )
    if result.returncode == 0 and result.stdout.strip():
        return json.loads(result.stdout)
    return []
```

注意：build.py 本身不内嵌 LLM 调用（架构约定：build.py 是纯机械构建器）。

---

## 16. 命令速查表

| 用途 | 命令 |
|---|---|
| **装核心依赖** | `pip3 install python-pptx lxml pyyaml Pillow` |
| **装全部依赖** | `pip3 install -e ".[read,diagram,dev]"` |
| **装渲染依赖（macOS）** | `brew install --cask libreoffice && brew install poppler` |
| **装 draw.io** | `brew install --cask drawio` |
| **装 Mermaid** | `brew install mermaid-cli` |
| **依赖检查** | `bash skills/pptx/scripts/check_deps.sh` |
| **跑 demo** | `python3 skills/pptx-deck/build.py skills/pptx-deck/examples/demo_plan.json` |
| **自定义生成** | `python3 skills/pptx-deck/build.py deck_plan.json` |
| **仅生成 .pptx** | `python3 skills/pptx-deck/build.py deck_plan.json --no-render` |
| **跑测试** | `python3 -m pytest tests/ -v` |
| **回归 eval** | `bash evals/run_eval.sh` |
| **渲染查看（PPT → PDF）** | `soffice --headless --convert-to pdf deck.pptx --outdir /tmp/` |
| **渲染查看（PDF → PNG）** | `pdftoppm -jpeg -r 150 /tmp/deck.pdf /tmp/slides` |
| **查看全 PNG** | `open /tmp/slides-1.jpg` |
| **单独 smoke test** | `python3 -m pytest tests/pptx_deck/test_build.py -v` |
| **验证雅黑字体** | `fc-list \| grep -i yahei` |
| **验证 soffice** | `soffice --version` |
| **验证 pdftoppm** | `pdftoppm -v` |
| **draw.io 渲染** | `/Applications/draw.io.app/Contents/MacOS/draw.io --export --format png --width 3200 --output out.png in.drawio` |
| **mmdc 渲染** | `mmdc -i diag.mmd -o diag.png -w 2400 -b white` |

---

## 17. 附录

### 17.1 完整目录结构树

```
iLovePPT/
├── README.md                        # 项目概述（快速开始）
├── USAGE.zh.md                      # 中文快速上手速查
├── pyproject.toml                   # 依赖与配置（Python 3.10+）
├── evals/                           # 回归 eval 集
│   ├── run_eval.sh                  # eval runner
│   ├── baseline/                    # 基准产物
│   └── rubric.md                    # 评分标准
├── docs/
│   ├── MANUAL.zh.md                 # 本文件：详细使用手册
│   └── superpowers/
│       ├── specs/                   # 设计文档
│       │   └── 2026-05-21-iloveppt-skill-design.md
│       └── plans/                   # 实现计划
│           └── 2026-05-21-iloveppt-skill.md
└── skills/
    ├── pptx-deck/                   # 端到端 PPT 生成器（主入口）
    │   ├── SKILL.md                 # skill 入口描述（含触发关键词）
    │   ├── build.py                 # 机械构建器：deck_plan.json → .pptx + PNG
    │   ├── workflow.md              # 7 步 Claude 工作流文档
    │   ├── content-writing.md       # 11 layout 文案规则 + 拓写 prompt
    │   ├── visual-qa.md             # 视觉自检 12 项 checklist
    │   ├── template-extract.md      # 从 .pptx 提取主色与字体 6 步流程
    │   ├── diagram-planning.md      # 图层规划决策规则
    │   ├── brief.example.yaml       # brief 完整示例（用户→Claude 输入）
    │   ├── themes/
    │   │   └── tech_blue.py         # 内置科技蓝主题（11 个 make_* 函数）
    │   └── examples/
    │       ├── demo_plan.json       # 可直接运行的演示 deck_plan
    │       └── sample_output.pptx   # 参考成品
    ├── pptx/                        # .pptx 底层读写
    │   ├── SKILL.md                 # skill 入口描述
    │   ├── helpers.py               # 13 个核心 helper 函数
    │   ├── layout.py                # 几何图元（geometry primitives）
    │   ├── creating.md              # 从零创建 PPT 指南
    │   ├── editing.md               # 模板局部修改指南
    │   ├── reading.md               # 读取提取内容指南
    │   ├── design-system.md         # 10 套色板 + 字号体系 + helper 详解
    │   ├── examples/
    │   │   └── minimal_deck.py      # 最小 PPT 生成示例
    │   └── scripts/
    │       ├── check_deps.sh        # 依赖检查脚本
    │       ├── thumbnail.py         # 生成缩略图
    │       ├── clean.py             # 清理临时文件
    │       ├── add_slide.py         # 添加单页工具
    │       └── office/              # soffice 相关工具
    └── diagram/                     # 架构图与可视化
        ├── SKILL.md                 # skill 入口描述（8 种图选型表）
        ├── drawio.md                # draw.io 完全指南
        ├── mermaid.md               # Mermaid 工作流
        ├── matplotlib.md            # 数据可视化图表
        ├── pptx-native.md           # slide 内 add_shape 画图
        └── examples/
            ├── minimal.drawio       # 最小 draw.io 示例
            └── render.sh            # 批量渲染脚本
```

### 17.2 设计文档指引

| 文档 | 内容 | 路径 |
|---|---|---|
| 完整设计文档 | iLovePPT skill 整体设计：架构决策、11 layout 规范、10 色板、13 helper | `docs/superpowers/specs/2026-05-21-iloveppt-skill-design.md` |
| 实现计划 | 分阶段实现任务列表（Phase 1/2/3） | `docs/superpowers/plans/2026-05-21-iloveppt-skill.md` |

### 17.3 测试说明

共 3 个测试文件，总计 35 个测试函数：

| 测试文件 | 测试数 | 覆盖内容 |
|---|---|---|
| `tests/pptx/test_helpers.py` | 5 个 | set_font EA 节点、card shape 数、色板常量、clear_template_slides |
| `tests/pptx_deck/test_tech_blue.py` | 12 个 | 11 个 make_* 函数各自的 slide 生成、shape 数量、字体名 |
| `tests/pptx_deck/test_build.py` | 18 个 | deck_plan.json 校验、load_theme、build 各 layout、render 流程 |

运行方式：

```bash
# 全部测试
python3 -m pytest tests/ -v

# 单文件
python3 -m pytest tests/pptx_deck/test_build.py -v

# 单个测试
python3 -m pytest tests/pptx/test_helpers.py::test_set_font_writes_ea_typeface -v

# 回归 eval 集
bash evals/run_eval.sh
```

测试设计原则：纯 Python 单测不依赖 soffice/pdftoppm，视觉"长得对不对"由端到端 smoke test 验证（运行 `build.py examples/demo_plan.json` 后目视检查产物）。

### 17.4 项目信息

| 项目 | 信息 |
|---|---|
| **GitHub** | `https://github.com/pcliangx/iLovePPT`（参见 README.md 鸣谢部分） |
| **许可** | MIT |
| **兼容性** | macOS 主测；Linux/Windows 理论可用，字体需手动配置 |
| **PPT 兼容性** | 生成的 .pptx 兼容 PowerPoint 2016+ / Keynote / WPS / LibreOffice |
| **Python 版本** | Python 3.10+ |
| **版本** | 0.1.0 |
