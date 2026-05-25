# pptx skill — 读取 / 提取内容

> 适用于：读取现有 .pptx 文件、提取文字内容、分析模板结构。

---

## 何时用本文档

| 场景 | 工具 |
|---|---|
| 提取文字给 LLM 处理 / 总结 | markitdown（本页 Step 1） |
| 直观看每页视觉内容 | thumbnail.py（本页 Step 2） |
| 分析 XML 结构 / 主题 / 字体 | unpack.py（本页 Step 3） |
| 查看 layout 和 placeholder 映射 | dump 脚本（本页 Step 4） |
| 发现问题后要局部改 | → [editing.md](editing.md) |
| 提取模板主色与字体后从零生成 | → [[pptx-deck]] template-extract |

---

## Step 1 — 文字提取（markitdown）

```bash
python3 -m markitdown deck.pptx
```

**输出格式**：Markdown，每张 slide 的文字内容按顺序列出，适合：
- LLM 总结 / 摘要
- 内容审查（检查措辞 / 错别字）
- 批量提取多个 .pptx 的文本

```bash
# 提取到文件
python3 -m markitdown deck.pptx > /tmp/deck-content.md

# 配合 grep 检查残留占位符
python3 -m markitdown deck.pptx | grep -iE "xxxx|lorem|ipsum|placeholder|TODO"
```

**markitdown 的局限**：
- 只提取文字，不含图片 / 图表 / 颜色 / 布局信息
- 表格文字会提取但不保留列结构（输出为平铺文字）
- speaker notes 也会被提取（有时候不想要这部分）
- 无法判断文字所在 slide 的视觉布局，只知道顺序

安装：`pip3 install "markitdown[pptx]"`

---

## Step 2 — 视觉概览（thumbnail 缩略图网格）

```bash
python3 scripts/thumbnail.py deck.pptx --cols 4
# 产物：thumbnails-1.jpg, thumbnails-2.jpg ...（每张图最多 cols^2 页）
```

**用途**：
- 快速看全部 slide 的视觉布局（LibreOffice 渲染 → 缩略图 → 网格排列）
- 分析不熟悉模板的 slide 类型和内容分布
- 发现明显视觉问题（元素溢出 / 空白页 / 字体异常）

**前置依赖**：
- LibreOffice（`soffice`）— `brew install --cask libreoffice`
- Pillow — `pip3 install Pillow`
- pdftoppm（poppler）— `brew install poppler`

完整渲染（不缩略图，直接每页一张 JPEG）：
```bash
mkdir -p /tmp/preview
soffice --headless --convert-to pdf deck.pptx --outdir /tmp/preview/
pdftoppm -jpeg -r 150 /tmp/preview/deck.pdf /tmp/preview/slide
# 产物: slide-1.jpg, slide-2.jpg ...
```

---

## Step 3 — 原始 XML 结构（unpack）

```bash
python3 scripts/office/unpack.py deck.pptx /tmp/unpacked/
```

**产物目录结构**：
```
/tmp/unpacked/
└── ppt/
    ├── theme/
    │   └── theme1.xml          # 颜色方案 / 字体方案 / 效果
    ├── slideMasters/
    │   └── slideMaster1.xml    # master slide（全局字体 / 背景 / placeholder 默认值）
    ├── slideLayouts/
    │   ├── slideLayout1.xml    # layout 1 的 XML
    │   ├── slideLayout2.xml    # layout 2 ...
    │   └── ...
    └── slides/
        ├── slide1.xml          # 各 slide 内容
        ├── slide2.xml
        └── ...
```

**典型用途**：
- 查看 `theme1.xml` 里的 `<a:dk1>` / `<a:lt1>` / `<a:accent1>` 颜色定义
- 查看 `slideMaster1.xml` 里的 `<a:ea typeface="...">` — 这是 placeholder 中文字体的根源
- 分析 `slideLayout*.xml` 里的 placeholder 位置（`<a:off x="..." y="...">` / `<a:ext cx="..." cy="...">`）
- 找到特殊工具页（通常 XML 里有第三方命名空间如 `xmlns:p14="..."`）

重新打包（修改 XML 后）：
```bash
python3 scripts/office/pack.py /tmp/unpacked/ output-modified.pptx
```

---

## Step 4 — 语义结构提取（slide → layout 映射）

用 python-pptx 直接读取语义层面的结构：

```python
from pptx import Presentation

prs = Presentation("deck.pptx")

print(f"总页数: {len(prs.slides)}")
print(f"可用 layout 数: {len(prs.slide_layouts)}")
print()

# Layout 清单
print("=== Layout 清单 ===")
for i, layout in enumerate(prs.slide_layouts):
    print(f"[{i}] '{layout.name}' — {len(layout.placeholders)} 个 placeholder")
    for ph in layout.placeholders:
        idx = ph.placeholder_format.idx
        ptype = ph.placeholder_format.type
        w = ph.width / 914400   # EMU → inches
        h = ph.height / 914400
        x = ph.left / 914400
        y = ph.top / 914400
        print(f"     ph[{idx}] type={ptype} @ ({x:.2f}\", {y:.2f}\") {w:.2f}\"×{h:.2f}\"")

print()
# Slide → Layout 映射
print("=== Slide → Layout 映射 ===")
for i, slide in enumerate(prs.slides, 1):
    layout_name = slide.slide_layout.name
    # 计数 shapes
    n_shapes = len(slide.shapes)
    print(f"slide {i:02d} → '{layout_name}' ({n_shapes} shapes)")

print()
# 文字内容速览
print("=== 各页标题速览 ===")
for i, slide in enumerate(prs.slides, 1):
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == 0:  # title
            print(f"slide {i:02d}: {ph.text[:60]}")
```

---

## Step 5 — 配合其他 skill

| 目标 | 跳转 |
|---|---|
| 局部改文字 / 换内容 | [editing.md](editing.md) — 加载模板 + clear + 重新填充 |
| 提取模板主色与字体 + 用于生成新 deck | [[pptx-deck]] `template-extract.md` — 主色与字体提取流程 |
| 读取完后要嵌入图表 | [creating.md](creating.md) — `embed_picture` / `card` 用法 |
| 提取后需要 LLM 总结或改写 | 把 markitdown 输出直接传给 Claude prompt |

---

## 常用场景速查

**场景 A：审查别人发来的 .pptx，确认内容**
```bash
python3 -m markitdown input.pptx | head -200
python3 scripts/thumbnail.py input.pptx --cols 3
```

**场景 B：复用现有 .pptx 模板做新内容**
```bash
# 1. 先分析
python3 scripts/thumbnail.py template.pptx --cols 4
python3 scripts/office/unpack.py template.pptx /tmp/unpacked/
# 2. dump layout 映射（用上方 Step 4 脚本）
# 3. 确认可用 layout 后 → 跳转 editing.md
```

**场景 C：验证生成的 .pptx 内容是否完整**
```bash
python3 -m markitdown output.pptx | grep -iE "xxxx|TODO|占位|placeholder"
# 如果无输出 → 没有残留占位符
```

**场景 D：检查 .pptx 页数**
```python
from pptx import Presentation
prs = Presentation("output.pptx")
print(f"总页数: {len(prs.slides)}")
```
