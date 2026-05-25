# pptx skill — 从零创建（python-pptx 全定制路径）

> 适用于：没有现成模板、跨平台中文、23+ 页量级、程序化重生成场景。

---

## 何时走本路径

选择 python-pptx 全定制而非模板混合，当满足以下任意条件：

| 条件 | 说明 |
|---|---|
| **无模板** | 仓库里没有可用的 .pptx 模板文件 |
| **跨平台中文** | 目标受众在 Windows / macOS / Linux 均需正确显示汉字 |
| **23+ 页量级** | 页数多到手动维护不现实，需要代码驱动 |
| **程序化重生成** | 数据会更新，PPT 必须从源码一键重跑 |
| **视觉完全自定义** | 没有设计师模板投入，排版逻辑全在代码里 |

不适合走本路径的场景：
- 已有设计精良的 .pptx 模板 → 走 [editing.md](editing.md)（保模板视觉投入）
- 一次性单页修改 → 直接用 python-pptx 局部改，不需要 helpers.py 全套
- 需要复杂动画 / 视频嵌入 → python-pptx 弱项，考虑 Keynote / Figma

---

## 工具链（macOS 实测表）

| 用途 | 工具 | 安装 | 备注 |
|---|---|---|---|
| PPT 生成 | `python-pptx ≥ 1.0` | `pip3 install python-pptx lxml` | lxml 通常已装，但建议显式指定 |
| XML 微调（EA 字体 / 表格属性）| `lxml` | 同上 | `set_font` / `_fix_ph_font` 依赖 |
| 渲染验证 | `soffice`（LibreOffice） | `brew install --cask libreoffice` | 最接近 Windows PowerPoint 的免费渲染 |
| PDF → PNG | `pdftoppm`（poppler） | `brew install poppler` | 视觉 QA 必需 |
| 缩略图网格 | `Pillow` | `pip3 install Pillow` | `scripts/thumbnail.py` 依赖 |
| 文字提取验证 | `markitdown` | `pip3 install "markitdown[pptx]"` | content QA 用 |

**依赖一键检查**：

```bash
bash scripts/check_deps.sh
```

输出 ✅/❌/⚠️ 列出各工具安装状态，缺失的给出安装命令。

⚠️ **不要装 PrinceXML**（商业授权 + 免费版水印）；不要走 `pandoc --pdf-engine=prince` 这条路。pandoc 生成的 pptx 结构非标准，与 python-pptx 混用会引起 XML 损坏。

---

## ⚠️ 中文字体（最致命的坑）

这是 python-pptx 最容易踩、影响最大的坑，必须在写第一行代码前理解清楚。

### 问题根因

`python-pptx` 默认的 `font.name = "某字体"` **只写 `<a:latin>` 节点**。中文字符（Unicode 中日韩区段）在渲染时走的是 `<a:ea>`（East Asian）节点，不是 `<a:latin>`。如果 `<a:ea>` 没有显式设置，渲染引擎会 fallback 到系统默认东亚字体——在不同平台结果不同：

| 平台 | 未设 `<a:ea>` 时 fallback |
|---|---|
| Windows | 通常 SimSun（宋体）或微软雅黑（取决于系统语言） |
| macOS | PingFang SC（苹方） |
| LibreOffice | 取决于 /etc/fonts 配置，通常 Noto Sans CJK |

结果：同一份 .pptx 在三个平台上中文字体不一致，且可能回退到又细又小的宋体，整体视觉崩溃。

### 解决方案

必须用 lxml 显式写 `<a:ea>` + `<a:cs>` 节点，指定字体名称。

```python
from pptx.oxml.ns import qn
from lxml import etree

def set_font(run, *, name="Microsoft YaHei", size=14, bold=False, italic=False, color=...):
    run.font.name = name          # 写 <a:latin>（英文 / 数字走这里）
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):  # 中文 / 复杂脚本走这两个节点
        elem = rPr.find(qn(tag))
        if elem is None:
            elem = etree.SubElement(rPr, qn(tag))
        elem.set("typeface", name)
```

这个函数已在 `helpers.py` 实现为 `set_font(run, ...)` — 直接 `import helpers as H` 调用，不要重新实现。

### 默认字体：Microsoft YaHei

`helpers.py` 的 `FONT_CN = "Microsoft YaHei"`（微软雅黑）。选它的理由：

- **Windows 原生**：Office 安装时随附，是 Windows 中文 PPT 事实标准
- **可嵌入**：不受 PingFang SC 的 macOS 专有字体授权限制
- **跨平台可装**：macOS / Linux 上均可手动安装 .ttf 文件

fallback 链（`helpers.py` `FONT_FALLBACK_CHAIN`）：
```
Microsoft YaHei → PingFang SC → Source Han Sans CN → Heiti SC
```

PingFang SC 仅出现在 fallback 链中，不作为默认。

### macOS 渲染验证前必须装雅黑

macOS 系统没有内置微软雅黑。如果不装，LibreOffice 渲染时会 fallback 到 PingFang SC，导致你在 macOS 上的视觉验证与 Windows PowerPoint 实际显示不一致。

安装方法：
1. 找到微软雅黑 .ttf 文件（`msyh.ttf`、`msyhbd.ttf`）——通常可以从 Windows 虚机的 `C:\Windows\Fonts\` 复制
2. 放到 `~/Library/Fonts/` 目录
3. 重启 LibreOffice（`soffice --headless --convert-to pdf` 重跑即可）

验证安装成功：
```bash
fc-list | grep -i "yahei"  # 应看到 Microsoft YaHei
```

---

## Placeholder vs Shape 概念区分

这是最关键的认知，影响字体修复、位置控制和内容填充。

| 项 | Placeholder | Shape（自加） |
|---|---|---|
| **来源** | layout / master 中预定义的"位置 + 类型" | 你 `slide.shapes.add_*` 手动加的 |
| **字体继承** | 继承 master 默认字体（可能是系统默认） | 你 `set_font(run, ...)` 直接控制 |
| **位置** | 模板定死（一般不建议改坐标） | 你自己写 `Inches(x)` 定义 |
| **典型用途** | 封面主标题、章节标题（用模板已设计好的位置） | 内容区卡片、图表、装饰元素 |
| **字体修复函数** | `_fix_ph_font(ph, ...)` ⚠️ | `set_font(run, ...)` |

**致命误区**：在 placeholder 上调用 `set_font(run, ...)` 想改字体——**改不动**。原因是 placeholder 的中文字体 `<a:ea>` 节点在 layout / master XML 那一层，slide 级别的 run 级 set_font 只改了 `<a:latin>`，东亚字体仍然继承 master。

全定制路径下，推荐做法是**避免使用 placeholder**，直接 `add_textbox` 加 shape，这样 `set_font` 完全有效，不受 master 影响。如果一定要用 placeholder（例如某些模板依赖它），用 `_fix_ph_font(ph, ...)` 而非 `set_font`。

---

## 7 致丑反模式

这 7 个模式是 python-pptx 新手最容易踩的视觉陷阱，在动笔前逐条对照：

| # | 反模式 | 为什么丑 | 正确做法 |
|:-:|---|---|---|
| 1 | 顶部厚色带（≥0.5"）每页重复 | 压死页面空间，视觉疲劳 | 6pt 极细横线 + 右上角 120-150pt 装饰大数字 |
| 2 | 每页同一个通用 header layout | 章节同质化，无层次感 | 章节扉页与内容页用不同 layout / 模板 |
| 3 | 表格全网格（Excel 风）+ 默认 banding | 老旧感强，信息密度低 | 表头深色底 + 0 内边框 + 手动斑马纹 |
| 4 | 一页 5+ 种饱和色（绿/蓝/红/橙/紫） | 眼花缭乱，权重失序 | 1 主色 + 1 强调色 + 灰阶 + 白 |
| 5 | 全屏文字墙（一页 >100 字） | 观众不会读完 | 卡片化：每个信息单元独立矩形 |
| 6 | 标题用艺术字 / 阴影 / 3D / 渐变铺底 | 过时感，形式干扰内容 | 简洁字体 + 1pt 横线分隔 |
| 7 | emoji 滥用（🚀 ✅ 🎉 等活泼感） | 制度 / 商务场合不严肃 | 仅 ⚠ ⛔ 🔒 类警示性图标 |

---

## 12 关键技巧（按重要性排序）

以下每条都引用 `helpers.py` 对应函数，不重写函数代码。

### 1. 中文字体跨平台 — `set_font` / `_fix_ph_font`

见上方"中文字体"章节。`helpers.py:set_font(run, ...)` 处理自加 textbox；`helpers.py:_fix_ph_font(ph, ...)` 处理 placeholder。两者不可互换。

### 2. textbox margin 归零 — `fix_textbox_margins`

```python
import helpers as H
box = slide.shapes.add_textbox(x, y, w, h)
H.fix_textbox_margins(box.text_frame)
```

python-pptx 默认 textbox 有约 90000 EMU（约 0.1"）的内边距。不归零会导致：
- 文字神秘偏右 / 偏下，和相邻元素对不齐
- 卡片内文字与卡片边缘间距不一致
- 精确坐标计算全部偏差

`helpers.py:fix_textbox_margins(tf)` 把 margin_left / right / top / bottom 全设为 `Emu(0)`。

### 3. 大字号装饰数字防换行 — `page_decoration`

180pt 大数字如果 `word_wrap=True`，"01" 会被拆成两行（"0\n1"），因为字符宽度超出 textbox 宽度就换行。

`helpers.py:page_decoration(slide, num, tint_color)` 已正确设置 `word_wrap=False` + textbox 宽度 4.4"（容纳 2-3 位数字）。

调用示例：
```python
H.page_decoration(slide, "01", H.BRAND_TINT)
```

textbox 宽度必须 ≥ `字符数 × 0.6 × 字号pt / 72 inches`，否则即使设了 `word_wrap=False` 也可能截断。

### 4. 表格行高 + 关 banding — `table_modern`

`helpers.py:table_modern(slide, x, y, w, h, headers, rows, ...)` 做三件事：
1. 显式设置每行高度（否则 LibreOffice 渲染行高失控）
2. 关闭 `firstRow` / `bandRow`（防止 python-pptx 默认 banding 出现奇怪横纹）
3. 手动给偶数行填 `GRAY_50` 实现自定义斑马纹

不要用 `slide.shapes.add_table()` 原始接口直接操作，很容易遗漏 banding 关闭步骤。

### 5. shape 真无填充/无边框 — `no_fill` / `no_line`

```python
# 错误：fill=None / line=None 不是"无"，是"继承默认"（可能有边框）
shape.fill = None  # 不等于透明

# 正确：
H.no_fill(shape)   # → shape.fill.background()（真透明）
H.no_line(shape)   # → shape.line.fill.background()（真无边框）
```

`helpers.py:no_fill(shape)` 和 `no_line(shape)` 封装了这两个调用。装饰性矩形、色条等不需要边框的元素都要调 `no_line`。

### 6. 卡片化 — `card`

`helpers.py:card(slide, x, y, w, h, *, fill, border, accent)` 创建圆角矩形 + 可选左侧 accent 色条：
- 圆角调整值 0.05（小圆角，不是 python-pptx 默认的大圆角）
- `accent` 参数传 `RGBColor` 则在卡片左边加 2.83pt 宽的细色条（视觉锚点）
- 返回 shape 对象，之后可在 shape 上 overlay textbox

典型用法：
```python
c = H.card(slide, Inches(0.55), Inches(1.8), Inches(5.5), Inches(1.2),
           fill=H.GRAY_50, border=H.GRAY_300, accent=H.BRAND_PRIMARY)
```

### 7. 现代 bullet `▎` — `bullets`

`helpers.py:bullets(slide, x, y, w, h, items, *, size, accent_color, body_color)` 生成带 `▎` 前缀的 bullet 列表。

`▎` 比 `•` `‣` 更现代，在制度 / 咨询 PPT 中常见。行高固定 1.45（中文正文最佳行距）。

调用示例：
```python
H.bullets(slide, Inches(0.55), Inches(2.0), Inches(6.0), Inches(3.0),
          ["要点一", "要点二", "要点三"],
          size=13, accent_color=H.BRAND_PRIMARY, body_color=H.GRAY_700)
```

### 8. 字号层级（16:9 = 13.333 × 7.5 in）

| 用途 | 字号 | 加粗 |
|---|---|---|
| 封面主标题 | 44-54pt | bold |
| 章节扉页大标题 | 36-40pt | bold |
| 内容页 H2 | 20-28pt | bold |
| 内容页 H3 / 小节 | 14-18pt | bold |
| 正文 bullet | 11.5-14pt | normal |
| 表格 body | 10.5-12pt | normal |
| 页脚 / caption | 8.5-10pt | normal |
| 装饰大数字 | 120-150pt | bold（淡色，`BRAND_TINT`）|

行高：中文正文 `line_spacing=1.45`，标题 `line_spacing=1.0`。

### 9. 留白边界（标准 layout）

`helpers.py` 顶部定义的布局常量（不要硬编码数字，直接引用这些常量）：

```python
SLIDE_W = Inches(13.333)   # 16:9 宽
SLIDE_H = Inches(7.5)      # 16:9 高
LEFT_MARGIN  = Inches(0.55)
RIGHT_MARGIN = Inches(0.55)
HEADER_BOTTOM = Inches(1.4)   # 标题区结束 → 内容区开始
FOOTER_TOP    = Inches(7.0)   # 内容区结束 → 页脚开始

content_w = 12.23"  # SLIDE_W - LEFT_MARGIN - RIGHT_MARGIN
content_h = 5.60"   # FOOTER_TOP - HEADER_BOTTOM
```

内容元素的 x 从 `LEFT_MARGIN` 开始，y 从 `HEADER_BOTTOM` 开始，宽度不超 `content_w`，高度不超 `content_h`。

### 10. 双视图嵌入图 + 卡片

竖长流程图 / 架构图适合"左图右文"布局（与 [[diagram]] 输出搭配）：
- **左 4-5"**：用 `embed_picture` 嵌入图（`height=Inches(5.0)` 等比缩放）
- **右 8"**：序号小字 + 主标题 28pt + 4 个左 accent 卡片说明

```python
H.embed_picture(slide, "diagram.png", Inches(0.55), Inches(1.9), height=Inches(5.0))
for i, (k, v) in enumerate(points):
    y = Inches(2.0 + i * 0.8)
    H.card(slide, Inches(4.8), y, Inches(8.0), Inches(0.65),
           fill=H.GRAY_50, border=H.GRAY_300, accent=H.BRAND_PRIMARY)
```

### 11. 阶段流程页万能 layout

左 1.7" 大色块 + 80pt 巨大数字（视觉锚点）+ 右 10" 信息区：

```python
H.section_header(s, "阶段名称", 1, H.BRAND_PRIMARY)
# 右侧信息区用 card + bullets 填充
```

`helpers.py:section_header(slide, title, num, color, ...)` 封装了整个左色块 + 数字 + 标题逻辑。数字字号 80pt，让观众一眼记住"这是阶段 N"。也可以在右侧信息区叠加 `card` + `bullets` 加更多内容。

### 12. 单一品牌色覆盖（≤ 9 色变量）

`helpers.py` 顶部定义了抽象 `BRAND_*` 变量，全 deck 只改这里，联动生效：

```python
BRAND_PRIMARY = RGBColor(0x1E, 0x6F, 0xE0)  # 主色
BRAND_DARK    = RGBColor(0x0B, 0x2A, 0x4A)  # 深色（大色块）
BRAND_TINT    = RGBColor(0xE6, 0xF0, 0xFC)  # 浅底（装饰数字）
ACCENT        = RGBColor(0x00, 0xD1, 0xC1)  # 强调色（少量点睛）
```

默认 9 个色变量足够覆盖 90% 场景（4 BRAND + 5 灰阶 + WHITE）。极端情况不要超过 12 个。

切换色板：把 `BRAND_*` 替换成 `design-system.md` 里的 10 套色板之一。

---

## 迭代验证 5 步循环

**最致命的错误**：只用 python-pptx 读回文件验证"没报错"，不看实际渲染效果。

文字溢出 / 表格截断 / 文字遮挡 / 行高失控 / 中文字体 fallback —— 这些只能通过 LibreOffice 渲染 PDF + 看 PNG 才能发现。

### 标准 5 步 cycle

```bash
# Step 1: 生成
python3 build.py

# Step 2: 转 PDF（LibreOffice 真实渲染）
mkdir -p /tmp/preview && rm -f /tmp/preview/*.pdf /tmp/preview/p*.jpg
soffice --headless --convert-to pdf /path/to/output.pptx --outdir /tmp/preview/

# Step 3: 转 PNG（每页一张）
pdftoppm -jpeg -r 100 /tmp/preview/output.pdf /tmp/preview/p
# 产物: /tmp/preview/p-1.jpg, /tmp/preview/p-2.jpg ...

# Step 4: 用 Read tool 看关键页
# 封面页 / 第一张内容页 / 表格页 / 图文嵌入页

# Step 5: 发现问题 → 修 build.py → 回 Step 1
```

### 每页 3 步检查

每次看 PNG 时，按顺序检查：
1. **文字截断 / 溢出 / 遮挡**：文字是否被 shape 边框截断？textbox 是否溢出 slide 边界？
2. **中文字体 fallback**：中文是否是微软雅黑？还是变成宋体 / 黑体 SC？
3. **表格 / 列宽**：表格行高是否均匀？斑马纹是否生效？列宽是否合理？

第一轮渲染几乎必有问题，这是正常的。目标是经过 2-3 轮 cycle 后达到零视觉问题。

---

## Anti-prompt（不要让 Claude 做的事）

把这段加入 prompt 避免走弯路：

```
- 不要装 PrinceXML / pandoc-with-prince
- 不要用 python-pptx 默认 font.name 设中文字体 — 必须 lxml 写 <a:ea>
- 不要每页用同一个 header layout — 章节扉页要有独立 layout
- 不要堆 5 种以上饱和色 — 主色 + 1 强调色 + 灰阶
- 不要只用 python-pptx 读回验证 — 必须 LibreOffice 转 PDF + 看 PNG
- 不要 commit 渲染产物（.pdf / .jpg / .pyc）— 写入 .gitignore
- 不要自己重写 set_font / _fix_ph_font — 直接 import helpers as H 调用
- 不要跳过 fix_textbox_margins — 否则对齐会神秘偏移
```

---

## 完整文件结构参考

全定制路径的典型项目结构：

```
my-deck/
├── build.py              # 主入口，python3 build.py 一键生成
├── helpers.py            # 从 iLovePPT .claude/skills/pptx/ 复制 or symlink
├── scripts/
│   ├── check_deps.sh     # 依赖检查
│   ├── thumbnail.py      # 缩略图网格
│   └── office/
│       └── unpack.py     # XML 解包
├── assets/
│   └── diagrams/         # [[diagram]] 输出的 PNG
└── output/
    └── deck.pptx         # 生成产物（gitignore）
```

`build.py` 的最小骨架：

```python
from pptx import Presentation
from pptx.util import Inches, Pt
import helpers as H

prs = Presentation()
prs.slide_width  = H.SLIDE_W
prs.slide_height = H.SLIDE_H

blank_layout = prs.slide_layouts[6]  # 全空白 layout

# --- 封面页 ---
s = prs.slides.add_slide(blank_layout)
H.page_decoration(s, "00", H.BRAND_TINT)
# ... 封面内容

# --- 内容页循环 ---
for section in data:
    s = prs.slides.add_slide(blank_layout)
    # ... 内容填充

prs.save("output/deck.pptx")
print(f"生成完毕：{len(prs.slides)} 页")
```
