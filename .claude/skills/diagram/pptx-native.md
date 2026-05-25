# pptx-native.md — slide 内 add_shape 直接画图

> 适用场景：节点 ≤ 5 的简单关系图，在 [[pptx-deck]] 流程内，且需要 PPT 打开后可编辑。
> 节点 > 5 → 切 draw.io（见 [[diagram]] SKILL.md）。

---

## 1. 何时用 slide 内 add_shape

| 条件 | 说明 |
|---|---|
| 节点 ≤ 5 | 精确坐标管理在此规模内可控 |
| 已在 [[pptx-deck]] 流程内 | 无需引入额外工具，python-pptx 直接调用 |
| 需 PPT 打开后可编辑 | draw.io 输出 PNG 为位图，不可在 PPT 内调整 |
| 图形简单（矩形 + 箭头） | 不需要 draw.io 的精确 XML 控制 |

---

## 2. 限制

| 限制 | 阈值 | 解决方案 |
|---|---|---|
| 节点 > 5 | 坐标管理繁琐，易出错 | 切 draw.io |
| 嵌套层次（subgraph） | python-pptx 无容器概念 | 切 draw.io subgraph |
| 跨多 slide 复用同款图 | 代码重复，维护难 | 切 draw.io PNG 批量生成 |
| 精确曲线 / 复杂路径 | python-pptx 连接线只支持直线 | 切 draw.io |

---

## 3. 与 [[pptx]] helpers.py 联动

python-pptx add_shape 系列函数在 [[pptx]] helpers.py 中有封装。主要用法：

| 用途 | helpers.py 函数 | 备注 |
|---|---|---|
| 节点（卡片） | `H.card(slide, ...)` | 圆角矩形，带标题 + 正文 |
| 纯背景矩形 | `H.rect(slide, ...)` | 无文字的色块 |
| 文字框 | `add_textbox` + `H.set_font(tf, ...)` | 浮动文本，无边框 |
| 箭头连接线 | `slide.shapes.add_connector(...)` | python-pptx 原生 API |

---

## 4. 示例：3 节点横排流程图

以下是完整的 3 节点横排流程，含 2 条箭头，字体 Microsoft YaHei：

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN

# 色板（Tech Blue，与 [[pptx]] design-system.md 一致）
PRIMARY   = RGBColor(0x1E, 0x6F, 0xE0)  # #1E6FE0
DARK      = RGBColor(0x0B, 0x2A, 0x4A)  # #0B2A4A
TINT      = RGBColor(0xE6, 0xF0, 0xFC)  # #E6F0FC
ACCENT    = RGBColor(0x00, 0xD1, 0xC1)  # #00D1C1
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
FONT_CN   = 'Microsoft YaHei'


def add_node(slide, label: str, left: Emu, top: Emu,
             width: Emu, height: Emu,
             fill_color=None, text_color=None):
    """添加圆角矩形节点"""
    if fill_color is None:
        fill_color = PRIMARY
    if text_color is None:
        text_color = WHITE

    from pptx.util import Pt
    from pptx.oxml.ns import qn
    import lxml.etree as etree

    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.ROUNDED_RECTANGLE
        left, top, width, height
    )

    # 设置圆角（调整 adj 值）
    sp = shape.element
    prstGeom = sp.find(qn('a:prstGeom'))
    if prstGeom is not None:
        avLst = prstGeom.find(qn('a:avLst'))
        if avLst is None:
            avLst = etree.SubElement(prstGeom, qn('a:avLst'))
        # 清除旧值并设置 adj
        for gd in avLst.findall(qn('a:gd')):
            avLst.remove(gd)
        gd = etree.SubElement(avLst, qn('a:gd'))
        gd.set('name', 'adj')
        gd.set('fmla', 'val 30000')  # ~30% 圆角

    # 填充色
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color

    # 边框
    shape.line.color.rgb = DARK
    shape.line.width = Pt(1.5)

    # 文字
    tf = shape.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = label
    run.font.name = FONT_CN
    run.font.size = Pt(18)
    run.font.bold = True
    run.font.color.rgb = text_color

    return shape


def add_arrow(slide, x1: Emu, y1: Emu, x2: Emu, y2: Emu):
    """添加直线箭头连接线"""
    connector = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        x1, y1, x2, y2
    )
    connector.line.color.rgb = DARK
    connector.line.width = Pt(2.0)
    return connector


def build_three_node_flow(prs: Presentation, slide_idx: int = 0):
    """在指定 slide 上画 3 节点横排流程"""
    slide = prs.slides[slide_idx]

    # 节点尺寸与间距
    node_w = Inches(2.2)
    node_h = Inches(0.9)
    node_top = Inches(3.0)

    # 3 个节点的左边距
    lefts = [Inches(1.0), Inches(4.4), Inches(7.8)]
    labels = ['需求分析', '方案设计', '交付评审']
    fills  = [PRIMARY, PRIMARY, ACCENT]
    texts  = [WHITE, WHITE, DARK]

    shapes = []
    for left, label, fill, text in zip(lefts, labels, fills, texts):
        s = add_node(slide, label, left, node_top, node_w, node_h,
                     fill_color=fill, text_color=text)
        shapes.append(s)

    # 箭头：节点 1 右边 → 节点 2 左边
    arrow_y = node_top + node_h / 2
    for i in range(len(shapes) - 1):
        x_start = lefts[i] + node_w
        x_end   = lefts[i + 1]
        add_arrow(slide, x_start, arrow_y, x_end, arrow_y)

    return slide


# 使用示例
if __name__ == '__main__':
    from pptx.util import Inches

    prs = Presentation()
    prs.slide_width  = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]  # 全空白 layout
    prs.slides.add_slide(blank_layout)

    build_three_node_flow(prs, slide_idx=0)
    prs.save('three_node_flow.pptx')
    print("saved: three_node_flow.pptx")
```

---

## 5. 何时切到 draw.io

| 触发条件 | 原因 |
|---|---|
| 节点 > 5 | 手工 Emu 坐标计算量大，易出偏差 |
| 需要 subgraph / 嵌套 | python-pptx 无容器概念 |
| 跨多个 slide 复用同款图 | draw.io PNG 批量生成更一致 |
| 需要精确曲线 / 回路箭头 | python-pptx 连接线只支持直线 |
| 视觉一致性要求（多图） | draw.io sed 批量替换配色更可靠 |
