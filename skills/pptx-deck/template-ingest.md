# 从用户 .pptx 模板"学风格"

本文档定义当用户在 `brief.reference_pptx` 提供一个 .pptx 文件路径时，如何分析模板并生成临时 theme 模块。被 [workflow.md](workflow.md) Step 2 引用。

---

## 流程 6 步

### Step 1：拷贝到 /tmp/ 防污染

```bash
mkdir -p /tmp/template-ingest
cp "<reference_pptx 路径>" /tmp/template-ingest/user_template.pptx
```

必须先拷贝，不得直接读取用户原始文件路径（防止意外写入 / 路径依赖）。

### Step 2：缩略图整体看一眼

```bash
python3 [[pptx]]/scripts/thumbnail.py \
  /tmp/template-ingest/user_template.pptx \
  --cols 4
```

产物：`thumbnails-N.jpg`（每行 4 页）。

Claude 用 Read 工具读缩略图，识别整体风格：

| 维度 | 观察点 |
|---|---|
| 背景色调 | 深色背景 vs 浅色背景？ |
| 信息密度 | 极简（大量留白）vs 信息密集？ |
| 装饰风格 | 装饰性强（大色块 / 线条）vs 简洁线框？ |
| 主色调 | 暖色系 / 冷色系 / 中性色？ |
| 字体感 | 粗体标题 / 细体正文 / 等宽代码风？ |

### Step 3：unpack XML

```bash
python3 [[pptx]]/scripts/office/unpack.py \
  /tmp/template-ingest/user_template.pptx \
  /tmp/template-ingest/unpacked/
```

关注以下文件：

| 文件 | 作用 |
|---|---|
| `ppt/theme/theme1.xml` | 全局色板与字体定义 |
| `ppt/slideMasters/slideMaster1.xml` | master layout（背景 / 默认字体） |
| `ppt/slideLayouts/slideLayout*.xml` | 各 layout 定义（名称 / placeholder） |
| `ppt/slides/slide*.xml` | 实际 slide 内容（用于核查 layout 使用频率） |

### Step 4：提 design token

```python
# /tmp/template-ingest/extract.py
from lxml import etree
from pathlib import Path

UNPACK = Path("/tmp/template-ingest/unpacked")
NSMAP = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}

# 主色 = theme1.xml 的 <a:accent1> → <a:srgbClr val="..."/>
theme_root = etree.fromstring((UNPACK / "ppt/theme/theme1.xml").read_bytes())

# 字体 = master 的 <a:latin> + <a:ea> typeface
# <a:ea> 是 East Asian 字体，即中文字体，期望是 Microsoft YaHei
master_root = etree.fromstring(
    (UNPACK / "ppt/slideMasters/slideMaster1.xml").read_bytes()
)

# layout 命名表
for f in sorted((UNPACK / "ppt/slideLayouts").glob("*.xml")):
    root = etree.fromstring(f.read_bytes())
    name_el = root.find(".//p:cSld", NSMAP)
    # name_el.get("name") → layout 名称
```

token 输出格式（JSON）：

```json
{
  "fonts": {
    "header": "微软雅黑",
    "body": "微软雅黑"
  },
  "colors": {
    "accent1": "#1E6FE0",
    "accent2": "#0B2A4A",
    "lt1": "#FFFFFF",
    "dk1": "#000000"
  },
  "layouts": {
    "layout_0": { "name": "标题幻灯片", "placeholders": [0, 1] },
    "layout_5": { "name": "仅标题",     "placeholders": [0] }
  }
}
```

`fonts.header` / `fonts.body` 若不是常见中文字体（见降级方案），退回 `Microsoft YaHei`。

### Step 5：dump slide → layout 映射

```python
from pptx import Presentation

prs = Presentation("/tmp/template-ingest/user_template.pptx")
usage = {}
for i, slide in enumerate(prs.slides, 1):
    name = slide.slide_layout.name
    usage[name] = usage.get(name, 0) + 1
    print(f"slide{i:02d} → '{name}'")

# 用得多的 = 核心 layout；从未用过的 = 备用，不映射
core_layouts = [k for k, v in usage.items() if v >= 2]
```

### Step 6：生成 /tmp/ingested_theme.py

基于 `themes/tech_blue.py` 的结构，将 BRAND_* / FONT_* 常量替换为 Step 4 提取的 token：

```python
# /tmp/ingested_theme.py（自动生成，勿手动编辑）
from pptx.dml.color import RGBColor
import sys, os

sys.path.insert(0, "<KillPPTs>/skills/pptx")
import helpers as H

# --- token 填入区 ---
FONT_HEADER = "{token.fonts.header}"   # e.g. "微软雅黑"
FONT_BODY   = "{token.fonts.body}"     # e.g. "微软雅黑"
FONT_NUM    = "Helvetica Neue"         # 数字装饰字体，固定不提取

def _hex(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

PRIMARY      = RGBColor(*_hex("{token.colors.accent1}"))
PRIMARY_DEEP = RGBColor(*_hex("{token.colors.accent2}"))
LIGHT_BG     = RGBColor(*_hex("{token.colors.lt1}"))
DARK_TEXT    = RGBColor(*_hex("{token.colors.dk1}"))

# --- 11 layout 函数（签名与 tech_blue.py 一致，只换色 / 字体常量）---
def make_cover(prs, title, subtitle): ...
def make_toc(prs, sections): ...
# ... 其余 9 个 layout 函数
```

[workflow.py](workflow.py) 中的 `load_theme()` 检测到 `theme_id` 是 `.pptx` 路径时，动态生成本文件并 `import`。

---

## 与 workflow.py 的接口

```python
# workflow.py（节选）
THEMES = {"tech_blue": tech_blue}

def load_theme(theme_id):
    if theme_id in THEMES:
        return THEMES[theme_id]
    if str(theme_id).endswith(".pptx"):
        return _ingest_template(theme_id)
    raise ValueError(f"未知 theme: {theme_id}")


def _ingest_template(pptx_path: str):
    # Step 1：复制到 /tmp/
    # Step 2：运行 thumbnail.py，Claude Read 看风格
    # Step 3：运行 unpack.py
    # Step 4：提取 token → JSON
    # Step 5：dump layout 映射
    # Step 6：写出 /tmp/ingested_theme.py → importlib.import_module
    ...
```

骨架版（[workflow.py](workflow.py)）中 `_ingest_template` 暂抛 `NotImplementedError`，留待实际调用时 Claude 按本文档手动执行各步骤。

---

## 降级方案

模板过于复杂时降级处理：

| 复杂度信号 | 降级策略 |
|---|---|
| > 10 个 layout 都被用过 | 只复用 master 背景色 + theme 色板；layout 函数沿用 tech_blue |
| 含艺术字 / 3D 效果 / 动画 | 警告 + 完全退回 tech_blue，不学风格 |
| 含外部数据连接（OLE embed） | 警告 + 退回 tech_blue |
| 字体非中文常见字体（花体 / 手写体） | `fonts.*` 退回 `Microsoft YaHei`；色板仍提取 |
| `<a:ea>` typeface 为空 / 缺失 | 退回 `Microsoft YaHei`，并在输出中提示用户检查字体 |

常见中文字体白名单（不退回）：`Microsoft YaHei` / `微软雅黑` / `PingFang SC` / `Noto Sans SC` / `思源黑体`。

---

## 何时不走 template-ingest

- 用户没有提供 `reference_pptx` → 使用内置 `tech_blue` theme 即可
- 用户只想读取现有 .pptx 内容 → 走 [[pptx]] `reading.md`，不走 ingest
- 用户给的 .pptx 文件损坏 / python-pptx 无法打开 → 提示修复或换模板，不强行 ingest

---

## Anti-prompt

- 不要假设所有用户模板都用 PingFang SC — 必须检查 `<a:ea>` typeface 属性
- 不要把 tech_blue 色板硬塞进用户模板 — 必须从 theme1.xml 提取真实 accent 色
- 不要复制粘贴用户 .pptx 的内容文本（侵权风险）— 只学色板 / 字体 / layout 命名
- 不要让 ingested_theme.py 依赖原始 .pptx 路径运行时存在 — 输出独立可用的模块
- 不要直接读取用户原始文件路径 — 必须先 `cp` 到 `/tmp/template-ingest/`
- 不要在 Step 2 跳过缩略图观察 — 整体风格判断影响后续 token 优先级
- 不要在字体退回时静默处理 — 必须在输出中说明"字体已退回 Microsoft YaHei，原因：xxx"
