# pptx skill — 基于模板编辑（模板混合路径）

> 适用于：仓库已有 .pptx 模板，需保留视觉设计投入 + 程序化生成内容。

---

## 何时走本路径

| 条件 | 说明 |
|---|---|
| 仓库已有 .pptx 模板 | 设计师投入了视觉设计，不想重来 |
| 需要版本化重生成 | 内容更新时要能一键重跑，不是手动改 |
| 模板视觉已经过审 | 只需把新内容填进去 |
| 涉及 ≥ 5 张 slide | 少于 5 张可以直接手动改 |

不适合走本路径：
- 没有现成模板 → 走 [creating.md](creating.md)（全定制）
- 一次性改 1-2 张文字 → 直接用 python-pptx 局部改，不需要本流程
- 模板视觉需要大改 → 回到 creating.md 或重新设计

---

## Step 1 — 模板分析三件套（先看再动）

**不要在没有分析模板的情况下直接写代码。** 模板可能有不可见的 iSlide 工具页、不能渲染的特殊 slide、名称误导的 layout。先分析清楚，再动手。

> 💡 如果该模板是 [[pptx-deck]] 生成的（或要用 [[pptx-deck]] 提取风格再生成），可以跳过手动 dump：
> [[pptx-deck]]/template-extract.md 流程会自动输出 layout 映射与 design token JSON。
> 本节流程适用于无 extract 上下文、手动分析的场景。

```bash
# 1. 复制模板到临时目录（不要直接操作原文件）
mkdir -p /tmp/template-analysis
cp path/to/template.pptx /tmp/template-analysis/

# 2. 缩略图网格（直观看每张 slide 的视觉概览）
python3 scripts/thumbnail.py /tmp/template-analysis/template.pptx --cols 4
# 产物：thumbnails-1.jpg, thumbnails-2.jpg ... 用 Read tool 查看

# 3. unpack 看 XML 结构（theme / master / layout / slide）
python3 scripts/office/unpack.py /tmp/template-analysis/template.pptx /tmp/template-analysis/unpacked/
# 产物：unpacked/ppt/{theme,slideMasters,slideLayouts,slides}/*.xml
```

### dump 脚本：找 layout → placeholder 映射

```python
from pptx import Presentation

prs = Presentation("/tmp/template-analysis/template.pptx")

print("=== layouts ===")
for i, layout in enumerate(prs.slide_layouts):
    print(f"layout[{i}] '{layout.name}' — {len(layout.placeholders)} ph")
    for ph in layout.placeholders:
        idx = ph.placeholder_format.idx
        ptype = ph.placeholder_format.type
        print(f"  ph[{idx}] type={ptype} name='{ph.name}'")

print("\n=== slides → layouts ===")
for i, slide in enumerate(prs.slides, 1):
    print(f"slide{i} → '{slide.slide_layout.name}'")
```

**分析 dump 结果的要点**：
- 哪些 layout 被 slide 实际引用了？被用过的是核心 layout，没被用的通常不可靠
- 多数模板实测只有 3-5 个 layout 真正可用，不要假设全部可用
- layout 名称有时具有误导性（如"标题幻灯片"实际上可能是空白）

---

## Step 2 — Placeholder vs Shape 概念区分

（本节与 creating.md 一致，因为本文档需要独立可读。）

| 项 | Placeholder | Shape（自加） |
|---|---|---|
| **来源** | layout / master 预定义的"位置 + 类型" | 你 `slide.shapes.add_*` 手动加的 |
| **字体继承** | 继承 master 默认字体（可能是系统默认） | 你 `set_font(run, ...)` 直接控制 |
| **位置** | 模板定死（一般不建议改坐标） | 你自己写 `Inches(x)` 定义 |
| **典型用途** | 封面主标题 / 章节标题（模板已设计好） | 内容区卡片 / 图表 / 装饰元素 |
| **字体修复函数** | `_fix_ph_font(ph, ...)` ⚠️ | `set_font(run, ...)` |

**最重要的误区**：在 placeholder 上调 `set_font(run, ...)` 想改字体——**改不动**。

Placeholder 的中文字体 `<a:ea>` 节点在 layout / master XML 层，slide 级别的 run 级 `set_font` 只能改 `<a:latin>`，东亚字体仍然继承 master，中文还是会 fallback 到 master 定义的字体（可能是宋体或系统默认）。

**正确做法**：placeholder 用 `helpers.py:_fix_ph_font(ph, ...)` 修字体。

---

## Step 3 — 加载模板 + clear_template_slides

模板自带的样例 slide 必须先清空（保留 layout / master / theme）：

```python
from pptx import Presentation
import helpers as H  # helpers.py 路径需在 sys.path 内

prs = Presentation("path/to/template.pptx")
H.clear_template_slides(prs)
# 现在 prs 是个空壳，但所有 layout / master / theme 都保留
# len(prs.slides) == 0
```

`helpers.py:clear_template_slides(prs)` 做两件事：
1. 从 `_sldIdLst` 移除所有 slide 引用
2. 清理 rels 防孤儿引用（某些模板如果只移除 slide ID 不清 rels，保存后再打开会报错）

**不要跳过这一步**。模板样例 slide 会出现在输出里，污染最终产物，并且某些样例 slide（如第三方工具的使用说明页）LibreOffice 无法渲染，导致页数对不上。

---

## Step 4 — 选 layout + 填 placeholder + 修字体

根据 Step 1 的 dump 结果，选择合适的 layout 新建 slide：

```python
# 用封面 layout（假设 dump 显示 layout[0] 是封面）
s = prs.slides.add_slide(prs.slide_layouts[0])

for ph in s.placeholders:
    idx = ph.placeholder_format.idx
    if idx == 0:      # title placeholder
        ph.text = "主标题文字"
        H._fix_ph_font(ph, name="Microsoft YaHei", size_pt=40, bold=True,
                       color=H.BRAND_DARK)
    elif idx == 1:    # subtitle placeholder
        ph.text = "副标题 / 日期 / 部门"
        H._fix_ph_font(ph, name="Microsoft YaHei", size_pt=18,
                       color=H.GRAY_700)
```

**注意**：
- `_fix_ph_font` 只修改已有 run 的字体，如果 placeholder 的 text_frame 是空的（刚 `ph.text = "..."` 赋值后 runs 可能为空），先赋文本再修字体
- `ph.text = "..."` 会清空 text_frame 原有内容，适合简单单段文字；复杂多行内容需要操作 `ph.text_frame.paragraphs`

---

## Step 5 — 内容页：空白 layout + add_shape

多数内容页应使用"仅标题 / 空白"类 layout（只含 title + footer，内容区空白），然后用 `helpers.py` 的 shape 函数自由填充：

```python
# 找到空白内容 layout（通常是 layout 名含"空白"/"Blank"/"Title Only"的）
content_layout = prs.slide_layouts[5]   # 按 dump 结果调整 index

s = prs.slides.add_slide(content_layout)

# 填标题 placeholder
for ph in s.placeholders:
    if ph.placeholder_format.idx == 0:
        ph.text = "内容页标题"
        H._fix_ph_font(ph, size_pt=28, bold=True, color=H.BRAND_DARK)

# 在内容区 (HEADER_BOTTOM ~ FOOTER_TOP) 自由加 shape
# 卡片示例
H.card(s, H.LEFT_MARGIN, H.HEADER_BOTTOM + Inches(0.2),
       Inches(5.5), Inches(1.2),
       fill=H.GRAY_50, border=H.GRAY_300, accent=H.BRAND_PRIMARY)

# bullet 列表示例
H.bullets(s, H.LEFT_MARGIN, H.HEADER_BOTTOM + Inches(1.6),
          Inches(12.23), Inches(3.5),
          ["要点 A", "要点 B", "要点 C"],
          size=13, accent_color=H.BRAND_PRIMARY, body_color=H.GRAY_700)

# 表格示例
H.table_modern(s, H.LEFT_MARGIN, H.HEADER_BOTTOM + Inches(0.2),
               Inches(12.23), Inches(5.0),
               headers=["列一", "列二", "列三"],
               rows=[["内容", "内容", "内容"]])
```

---

## Step 6 — LibreOffice 不渲染部分 slide 的兜底

某些第三方模板含"工具说明页"（例如教用户如何使用模板软件的插件页面）。LibreOffice 不识别这类特殊 slide——渲染时 PDF 页数 < 模板 XML 中的 slide 数。

**判断方法**：
```bash
# 渲染后数 PNG 数量
ls /tmp/preview/slide-*.jpg | wc -l

# 对比 python 里的 slide 数
python3 -c "from pptx import Presentation; prs=Presentation('output.pptx'); print(len(prs.slides))"
```

如果两个数字不一致：
1. **先确认是否真的是"工具页"问题**，不要立刻怀疑代码 bug
2. 如果你已经在 Step 3 调用了 `clear_template_slides(prs)`，这些工具页已被清除，不会出现在输出里
3. 如果问题仍然存在，用 unpack.py 查看各 slide XML，找异常的 slide（通常含第三方工具专有的 XML 命名空间）

**最佳实践**：只要走模板路径，始终在 Step 3 调用 `clear_template_slides`，让模板只贡献 layout / master / theme，不带入样例内容。

---

## Step 7 — 渲染验证 5 步循环

与 creating.md 完全相同的 cycle（模板路径和全定制路径都需要）：

```bash
# Step 1: 生成
python3 build.py

# Step 2: LibreOffice 渲染
mkdir -p /tmp/preview
soffice --headless --convert-to pdf output.pptx --outdir /tmp/preview/

# Step 3: PDF → PNG
pdftoppm -jpeg -r 150 /tmp/preview/output.pdf /tmp/preview/slide

# Step 4: 检查关键页（用 Read tool 看图）
# 封面 / 第一张内容页 / 含表格页 / 含图片页

# Step 5: 发现问题 → 改 build.py → 回 Step 1
```

**每页 3 步检查**：
1. 文字截断 / 溢出 / 遮挡？
2. 中文字体是否为 Microsoft YaHei（不是宋体 / 黑体 / 系统 fallback）？
3. 表格行高 / 列宽是否合理，斑马纹是否生效？

**模板路径专项检查**：
- `len(prs.slides)` 是否等于 PNG 数量？
- Placeholder 字体是否已通过 `_fix_ph_font` 修正（不是继承了 master 的宋体）？

---

## 完整 build.py 骨架（模板路径）

```python
"""基于模板生成 deck — 模板混合路径骨架。"""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
import helpers as H

TEMPLATE = Path("assets/template.pptx")
OUTPUT   = Path("output/deck.pptx")
OUTPUT.parent.mkdir(exist_ok=True)

# 1. 加载 + 清空样例 slide
prs = Presentation(TEMPLATE)
H.clear_template_slides(prs)

# 2. 找可用 layout（按 Step 1 dump 结果填 index）
LAYOUT_COVER   = prs.slide_layouts[0]
LAYOUT_SECTION = prs.slide_layouts[2]
LAYOUT_CONTENT = prs.slide_layouts[5]

# 3. 封面
s = prs.slides.add_slide(LAYOUT_COVER)
for ph in s.placeholders:
    if ph.placeholder_format.idx == 0:
        ph.text = "文档标题"
        H._fix_ph_font(ph, size_pt=40, bold=True, color=H.BRAND_DARK)
    elif ph.placeholder_format.idx == 1:
        ph.text = "副标题 · 2026-05"
        H._fix_ph_font(ph, size_pt=18, color=H.GRAY_700)
H.page_decoration(s, "00", H.BRAND_TINT)

# 4. 内容页（示例）
s = prs.slides.add_slide(LAYOUT_CONTENT)
for ph in s.placeholders:
    if ph.placeholder_format.idx == 0:
        ph.text = "第一页标题"
        H._fix_ph_font(ph, size_pt=28, bold=True, color=H.BRAND_DARK)
H.bullets(s, H.LEFT_MARGIN, H.HEADER_BOTTOM + Inches(0.3),
          Inches(12.23), Inches(4.5),
          ["要点一", "要点二", "要点三"])
H.page_decoration(s, "01", H.BRAND_TINT)

# 5. 保存
prs.save(OUTPUT)
print(f"生成完毕: {OUTPUT} ({len(prs.slides)} 页)")
```

---

## 常见问题排查

| 现象 | 可能原因 | 解决 |
|---|---|---|
| PDF 页数 < `len(prs.slides)` | 模板含工具说明页 | 确认已调 `clear_template_slides`；检查 unpack XML |
| 中文字体仍然是宋体 | Placeholder 没用 `_fix_ph_font` | 改用 `H._fix_ph_font(ph, ...)` |
| 文字位置偏移 | Textbox margin 未归零 | 在 `add_textbox` 后调 `H.fix_textbox_margins(tf)` |
| 保存后打开报错 | 模板 rels 孤儿引用 | 确认 `clear_template_slides` 版本是最新的（含 drop_rel 步骤） |
| 装饰数字被截断 | `word_wrap=True` 或 textbox 太窄 | 用 `H.page_decoration`（已正确设置 `word_wrap=False`）|
