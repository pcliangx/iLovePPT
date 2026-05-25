# pptx skill — 设计系统（配色 / 字体 / 12 helper）

> helpers.py 的设计决策说明。切换色板、理解字号体系、查阅 12 个 helper 的签名和适用场景。

---

## 10 现成色板

> **SSOT（单一事实来源）**：色值的唯一权威定义在 `helpers.py` 顶部的 `BRAND_*` 常量。
> 下表是**参考目录**——10 套可选配色的备查清单,不是独立定义。`tech_blue.py` 等主题
> 模块**别名引用** `helpers.py`（`PRIMARY = H.BRAND_PRIMARY`）,不重新定义色值。
> 改色板 = 改 `helpers.py` 一处,全 deck（含 tech_blue 主题）联动。

全定制路径只需修改 `helpers.py` 顶部的 `BRAND_*` 常量，全 deck 联动。以下 10 套色板直接可用。

| 主题 | BRAND_PRIMARY | BRAND_DARK | BRAND_TINT | ACCENT |
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

### 切换色板

编辑 `helpers.py` 顶部的 4 个 `BRAND_*` 常量：

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

修改后无需改其他代码，所有调用 `H.BRAND_PRIMARY` / `H.BRAND_DARK` / `H.BRAND_TINT` / `H.ACCENT` 的 helper 自动生效。

### 色彩设计原则

- **主导原则**：`BRAND_PRIMARY` 占视觉重量 60-70%，`ACCENT` 仅用于点睛（< 10%）
- **不超过 9 个颜色变量**（4 个 BRAND + 5 个灰阶）——超出后 PPT 颜色体系失控
- 深浅对比：`BRAND_DARK` 用于大色块 / 表头；`BRAND_TINT` 用于背景底色 / 装饰数字
- 灰阶（GRAY_900 → GRAY_50）用于文字层级和表格斑马纹，不消耗品牌色预算

---

## 字体配对

### 默认配置（helpers.py）

| 角色 | 字体 | 说明 |
|---|---|---|
| 中文标题 / 正文（`FONT_CN`） | **Microsoft YaHei** | Windows 原生，办公标配 |
| 英文 / 数字装饰（`FONT_EN` / `FONT_NUM`） | Helvetica Neue | 与雅黑视觉重量匹配 |
| Fallback 链 | YaHei → PingFang SC → Source Han Sans CN → Heiti SC | 按优先级，macOS 无雅黑时走 PingFang |

**PingFang SC 仅作为 fallback**，不作为默认字体。macOS 渲染验证时若雅黑未安装，LibreOffice 会 fallback 到 PingFang SC，视觉结果与 Windows PowerPoint 不一致。

### macOS 安装微软雅黑

1. 从 Windows 虚机复制 `msyh.ttf`（常规）和 `msyhbd.ttf`（加粗）
2. 放到 `~/Library/Fonts/`
3. 重启 LibreOffice

验证安装：`fc-list | grep -i "yahei"`（应输出字体路径）

### 字体来源说明

为什么不用 PingFang SC 作默认：
- PingFang SC 是 macOS 专有，在 Windows PowerPoint 上不显示（fallback 到宋体）
- Microsoft YaHei 可在 macOS / Linux 上手动安装，跨平台部署更简单
- 商务 / 制度文件的目标受众主要在 Windows 环境

---

## 字号体系（16:9 = 13.333 × 7.5 in）

| 用途 | 字号范围 | 加粗 | 典型颜色 |
|---|---|---|---|
| 封面主标题 | 44-54pt | bold | `BRAND_DARK` |
| 章节扉页大标题 | 36-40pt | bold | `BRAND_PRIMARY` |
| 内容页 H2（页标题） | 20-28pt | bold | `BRAND_DARK` |
| 内容页 H3 / 小节 | 14-18pt | bold | `GRAY_900` |
| 正文 bullet | 11.5-14pt | normal | `GRAY_700` |
| 表格 body | 10.5-12pt | normal | `GRAY_900` |
| 页脚 / caption | 8.5-10pt | normal | `GRAY_500` |
| 装饰大数字 | 120-150pt | bold | `BRAND_TINT`（淡色）|

行高规范：
- 中文正文：`line_spacing=1.45`（低于 1.4 中文行间距太紧）
- 标题：`line_spacing=1.0`
- 装饰数字：`line_spacing=1.0`

---

## 留白 layout 常量

```python
SLIDE_W = Inches(13.333)   # 16:9 宽度
SLIDE_H = Inches(7.5)      # 16:9 高度
LEFT_MARGIN   = Inches(0.55)
RIGHT_MARGIN  = Inches(0.55)
HEADER_BOTTOM = Inches(1.4)   # 标题区结束 → 内容区开始
FOOTER_TOP    = Inches(7.0)   # 内容区结束 → 页脚开始

# 可用内容区
content_w = 12.23"   # SLIDE_W - LEFT_MARGIN - RIGHT_MARGIN
content_h = 5.60"    # FOOTER_TOP - HEADER_BOTTOM
```

内容元素坐标：`x ≥ LEFT_MARGIN`，`y ≥ HEADER_BOTTOM`，宽度 ≤ `content_w`，不超出 `FOOTER_TOP`。

---

## 12 helper 详解

每个 helper 均在 `helpers.py` 实现。以下列出签名 + 一句话用途 + 典型用例 + 何时不该用。

---

### 1. `set_font(run, *, name, size, bold, italic, color)`

**用途**：设置 textbox run 的字体，包含 lxml 写 `<a:ea>` + `<a:cs>`，确保中文跨平台不 fallback。

**默认值**：`name=FONT_CN`（Microsoft YaHei）、`size=14`、`bold=False`、`italic=False`、`color=GRAY_900`

**典型用例**：
```python
box = slide.shapes.add_textbox(x, y, w, h)
r = box.text_frame.paragraphs[0].add_run()
r.text = "中文文字"
H.set_font(r, size=16, bold=True, color=H.BRAND_DARK)
```

**何时不该用**：placeholder 字体不能用 `set_font` 改，必须用 `_fix_ph_font`。

---

### 2. `_fix_ph_font(ph, *, name, size_pt, bold, color)`

**用途**：修复 placeholder 字体。`set_font` 只能改 run 级 `<a:latin>`，placeholder 的中文字体继承自 master 的 `<a:ea>`，必须用本函数覆盖。

**默认值**：`name=FONT_CN`、`size_pt=14`、`bold=False`、`color=GRAY_900`

**典型用例**：
```python
for ph in slide.placeholders:
    if ph.placeholder_format.idx == 0:  # title
        ph.text = "主标题"
        H._fix_ph_font(ph, size_pt=38, bold=True, color=H.BRAND_DARK)
```

**何时不该用**：自己 `add_textbox` 加的 shape 用 `set_font`，不用 `_fix_ph_font`（placeholder 专用）。

---

### 3. `clear_template_slides(prs)`

**用途**：清空模板自带的样例 slide，保留 layout / master / theme。同时清理孤儿 rels，防止保存后打开报错。

**典型用例**：
```python
prs = Presentation("template.pptx")
H.clear_template_slides(prs)
# 现在 len(prs.slides) == 0，但所有 layout 仍然可用
```

**何时不该用**：全定制路径（`Presentation()` 无参数创建空 prs）不需要调用，因为本来就没有样例 slide。

---

### 4. `fix_textbox_margins(tf)`

**用途**：把 text_frame 的 margin_left / right / top / bottom 全归零（默认有约 90000 EMU 内边距）。

**典型用例**：
```python
box = slide.shapes.add_textbox(x, y, w, h)
tf = box.text_frame
H.fix_textbox_margins(tf)
```

**何时不该用**：如果你想要内边距（如卡片内文字要和卡片边缘有间距），就不要调这个，改为在坐标上偏移。

---

### 5. `no_fill(shape)`

**用途**：设置 shape 为真透明（`shape.fill.background()`）。`shape.fill = None` 不等于透明。

**典型用例**：
```python
overlay = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
H.no_fill(overlay)   # 让矩形透明，只当占位用
```

**何时不该用**：需要有填充色的 shape 不要调（显然）。

---

### 6. `no_line(shape)`

**用途**：设置 shape 边框为真无边框（`shape.line.fill.background()`）。

**典型用例**：
```python
bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
bar.fill.solid(); bar.fill.fore_color.rgb = H.BRAND_PRIMARY
H.no_line(bar)   # 色条不要边框
```

**何时不该用**：需要边框的 shape（如卡片边框）不要调。

---

### 7. `rect(slide, x, y, w, h, color)`

**用途**：创建无边框纯色矩形，返回 shape 对象。是 `add_shape + fill + no_line` 的快捷组合。

**典型用例**：
```python
# 章节扉页左色块
H.rect(slide, H.LEFT_MARGIN, H.HEADER_BOTTOM, Inches(1.7), Inches(2.5), H.BRAND_PRIMARY)

# 页脚分隔线（极细横线）
H.rect(slide, H.LEFT_MARGIN, H.FOOTER_TOP - Inches(0.02), Inches(12.23), Inches(0.008), H.GRAY_300)
```

**何时不该用**：需要圆角的用 `card`；需要 accent 色条的用 `card`（accent 参数）。

---

### 8. `card(slide, x, y, w, h, *, fill, border, accent)`

**用途**：创建圆角矩形卡片，可选左侧 accent 色条。圆角值 0.05（比 python-pptx 默认值小，更精致）。

**签名**：
```python
card(slide, x, y, w, h, *, fill=WHITE, border=GRAY_300, accent=None)
```

**典型用例**：
```python
# 内容卡片（带左色条）
H.card(slide, Inches(0.55), Inches(1.8), Inches(5.5), Inches(1.2),
       fill=H.GRAY_50, border=H.GRAY_300, accent=H.BRAND_PRIMARY)

# 纯白卡片（无色条）
H.card(slide, Inches(6.5), Inches(1.8), Inches(6.0), Inches(1.2),
       fill=H.WHITE, border=H.GRAY_300)
```

**何时不该用**：纯色矩形（无圆角、无边框）用 `rect` 更简单；需要在 shape 上直接填文字的场景要 overlay 一个 textbox，`card` 本身不含文字。

---

### 9. `bullets(slide, x, y, w, h, items, *, size, accent_color, body_color)`

**用途**：生成带 `▎` 前缀的现代 bullet 列表。行高固定 1.45，中文正文最佳行距。

**签名**：
```python
bullets(slide, x, y, w, h, items, *,
        size=14, accent_color=BRAND_PRIMARY, body_color=GRAY_900)
```

**典型用例**：
```python
H.bullets(slide, H.LEFT_MARGIN, H.HEADER_BOTTOM + Inches(0.3),
          Inches(12.23), Inches(4.0),
          ["核心要点一", "核心要点二", "核心要点三（较长文字会自动换行）"],
          size=13, accent_color=H.BRAND_PRIMARY, body_color=H.GRAY_700)
```

**何时不该用**：需要多级缩进 bullet、需要自定义每条颜色或图标时，手动构建 text_frame 更灵活。

---

### 10. `table_modern(slide, x, y, w, h, headers, rows, *, ...)`

**用途**：创建关闭 banding 的现代表格（表头深色底 + 自定义斑马纹），显式设置行高防 LibreOffice 失控。

**签名**：
```python
table_modern(slide, x, y, w, h, headers, rows, *,
             header_fill=BRAND_DARK, header_color=WHITE,
             body_color=GRAY_900, zebra=GRAY_50, font_size=11,
             row_height=Inches(0.5))
```

**典型用例**：
```python
H.table_modern(slide,
               H.LEFT_MARGIN, H.HEADER_BOTTOM + Inches(0.2),
               Inches(12.23), Inches(5.0),
               headers=["功能", "状态", "负责人", "截止日期"],
               rows=[
                   ["功能 A", "已完成", "张三", "2026-05"],
                   ["功能 B", "进行中", "李四", "2026-06"],
               ],
               font_size=12)
```

**何时不该用**：合并单元格 / 复杂表格样式需要直接操作 `tbl.cell(r, c)` XML，`table_modern` 不支持合并单元格。

---

### 11. `page_decoration(slide, num, tint_color, *, x, y, w, h, size)`

**用途**：在 slide 右上角添加淡色装饰大数字（右对齐，`word_wrap=False`）。

**默认位置**：`x=Inches(8.8), y=Inches(0.25), w=Inches(4.4), h=Inches(2.0)`，字号 140pt。

**典型用例**：
```python
# 每页加装饰数字
H.page_decoration(slide, "01", H.BRAND_TINT)
H.page_decoration(slide, "02", H.BRAND_TINT)
```

**何时不该用**：章节扉页已有大数字（通过 `section_header`），不要再加 `page_decoration`，避免两个大数字叠加。装饰数字颜色通常用 `BRAND_TINT`（淡色），不要用主色（过于抢眼）。

---

### 12. `section_header(slide, title, num, color, *, 坐标参数...)`

**用途**：章节扉页标准 layout——左侧大色块 + 80pt 白色数字 + 右侧大标题文字。

**签名**：
```python
section_header(slide, title, num, color, *,
               block_x=LEFT_MARGIN, block_y=Inches(1.9),
               block_w=Inches(1.7), block_h=Inches(2.0),
               title_x=Inches(2.55), title_y=Inches(2.3),
               title_w=Inches(10), title_h=Inches(1.2),
               num_size=80, title_size=36)
```

**典型用例**：
```python
s = prs.slides.add_slide(blank_layout)
H.section_header(s, "第一章：背景", 1, H.BRAND_PRIMARY)
H.page_decoration(s, "01", H.BRAND_TINT)
```

**何时不该用**：内容页不要用 `section_header`，它是章节扉页专用。内容页用 title placeholder 或普通 textbox 加标题。

---

### 附：`embed_picture(slide, path, x, y, *, height, width)`

**用途**：等比缩放嵌入图片（传 height 或 width 之一，不变形）。与 [[diagram]] 输出搭配使用。

**典型用例**：
```python
# 按高度等比缩放（左图右文 layout 常用）
H.embed_picture(slide, "assets/diagrams/flow.png",
                H.LEFT_MARGIN, H.HEADER_BOTTOM + Inches(0.2),
                height=Inches(5.0))

# 按宽度等比缩放（全宽图常用）
H.embed_picture(slide, "assets/diagrams/arch.png",
                H.LEFT_MARGIN, H.HEADER_BOTTOM + Inches(0.3),
                width=Inches(12.23))
```

**何时不该用**：同时传 `height` 和 `width` 会拉伸变形（`helpers.py` 实现中 `height` 优先，`width` 被忽略）。不要直接用 `slide.shapes.add_picture(path, x, y, w, h)` 指定全部四个参数，那会强制拉伸。

---

## Helper 速查表

| helper | 输入 | 返回 | 核心作用 |
|---|---|---|---|
| `set_font` | run + 字体参数 | — | run 字体（含 EA/CS 节点） |
| `_fix_ph_font` | placeholder + 字体参数 | — | placeholder 字体 |
| `clear_template_slides` | prs | — | 清空样例 slide |
| `fix_textbox_margins` | text_frame | — | margin 归零 |
| `no_fill` | shape | — | 真透明填充 |
| `no_line` | shape | — | 真无边框 |
| `rect` | slide + 坐标 + color | shape | 纯色矩形 |
| `card` | slide + 坐标 + 样式参数 | shape | 圆角卡片 |
| `bullets` | slide + 坐标 + items | box | ▎ bullet 列表 |
| `table_modern` | slide + 坐标 + data | tbl_shape | 现代表格 |
| `page_decoration` | slide + num + color | box | 右上装饰大数字 |
| `section_header` | slide + title + num + color | (box, box2) | 章节扉页 |
| `embed_picture` | slide + path + 坐标 | shape | 等比嵌入图片 |
