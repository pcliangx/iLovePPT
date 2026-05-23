"""iLovePPT pptx skill — 核心 helper 集合。

被 pptx-deck/themes/*.py 调用作为 layout 底层；也可单独 import 用于
"从零创建 PPT"或"模板局部改"场景。

设计原则：
- 单一品牌色 + 灰阶（10 色变量）
- 中文字体 lxml 写 <a:ea>（跨平台不 fallback）
- textbox margin 归零 + word_wrap 显式
- 表格关 firstRow/bandRow + 手动斑马纹
"""

from pathlib import Path
from typing import Any

from lxml import etree
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.presentation import Presentation
from pptx.shapes.autoshape import Shape
from pptx.shapes.base import BaseShape
from pptx.slide import Slide
from pptx.text.text import _Run, TextFrame
from pptx.util import Emu, Inches, Length, Pt


# ============================================================================
# 1. 设计 token
# ============================================================================

# 字体:default 仍是 Microsoft YaHei（Windows / Office 装机即用,跨平台兜底）。
# 设计感更强的中文字体首选 Source Han Sans CN(思源黑体,Adobe+Google,开源免费),
# 但需要用户自行安装,不能假设到处都有。FONT_CN_DESIGN 提供给愿意分发字体的场景。
# macOS 渲染前装雅黑;否则 LibreOffice fallback 到 PingFang SC,渲染图字形对不上。
FONT_CN        = "Microsoft YaHei"        # 系统兼容默认(broad compatibility)
FONT_CN_DESIGN = "Source Han Sans CN"     # 设计感更强,需用户安装思源黑体
FONT_EN  = "Helvetica Neue"
FONT_NUM = "Helvetica Neue"

# fallback 链:渲染端如缺当前字体,按此顺序查找替代
FONT_FALLBACK_CHAIN = (
    "Source Han Sans CN",   # 思源黑体优先(若有)
    "Microsoft YaHei",
    "PingFang SC",
    "Heiti SC",
)

# 品牌色板(default 科技蓝;其他色板见 design-system.md)。
# AAA 优先:正文 + 正色对比 ≥ 7:1(WebAIM 投影场景建议)。
# BRAND_PRIMARY 选 #0A52BF —— 在白底对比度 7.00:1(刚过 AAA)。
# 历史值 #1E6FE0 在白底仅 4.62:1(刚过 AA),已废弃 —— 投影场景会糊。
BRAND_PRIMARY = RGBColor(0x0A, 0x52, 0xBF)  # 科技蓝(AAA 7:1)
BRAND_DARK    = RGBColor(0x0B, 0x2A, 0x4A)  # 深海蓝(白底 14:1)
BRAND_TINT    = RGBColor(0xE6, 0xF0, 0xFC)  # 浅蓝底(填充用,不承载文字)
ACCENT        = RGBColor(0x00, 0x7A, 0x6D)  # 深青(白底 5.2:1,AA pass) — 旧 #00D1C1 在白底仅 1.7:1 不能承载文字

# 灰阶(常用 3 个,其余兼容历史代码 — 见 design-system.md 用法指引):
GRAY_700 = RGBColor(0x4A, 0x4A, 0x4A)  # ★ 主要正文色(白底 9.7:1,AAA)
GRAY_300 = RGBColor(0xD9, 0xD9, 0xD9)  # ★ 分隔线 / border
GRAY_500 = RGBColor(0x6F, 0x6F, 0x6F)  # ★ 页脚 / meta 文字(原 #8C8C8C 在白底 3.5:1 不过 AA — 改 #6F6F6F = 5.7:1)
GRAY_900 = RGBColor(0x1A, 0x1A, 0x1A)  # 极少用,标题已有 BRAND_DARK
GRAY_50  = RGBColor(0xFA, 0xFA, 0xFA)  # 极少用,大色块底
WHITE    = RGBColor(0xFF, 0xFF, 0xFF)
BLACK    = RGBColor(0x00, 0x00, 0x00)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
LEFT_MARGIN  = Inches(0.55)
RIGHT_MARGIN = Inches(0.55)
HEADER_BOTTOM = Inches(1.4)
FOOTER_TOP    = Inches(7.0)


# ============================================================================
# 2. 字体工具
# ============================================================================

def set_font(
    run: _Run,
    *,
    name: str = FONT_CN,
    size: int = 14,
    bold: bool = False,
    italic: bool = False,
    color: RGBColor = GRAY_900,
) -> None:
    """设置 run 字体；用 lxml 写 <a:ea>+<a:cs>,中文跨平台不 fallback。

    适用：你自己 add_textbox 加的 textbox 的 run。
    placeholder（layout 自带）请用 _fix_ph_font(ph, ...)。
    """
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        elem = rPr.find(qn(tag))
        if elem is None:
            elem = etree.SubElement(rPr, qn(tag))
        elem.set("typeface", name)


def _fix_ph_font(
    ph: Any,
    *,
    name: str = FONT_CN,
    size_pt: int = 14,
    bold: bool = False,
    color: RGBColor = GRAY_900,
) -> None:
    """修 placeholder 字体。set_font 只能改 run 级 latin,改不到 master 的 <a:ea>。"""
    for p in ph.text_frame.paragraphs:
        for run in p.runs:
            set_font(run, name=name, size=size_pt, bold=bold, color=color)


# ============================================================================
# 3. 模板生命周期
# ============================================================================

def clear_template_slides(prs: Presentation) -> None:
    """清空模板自带样例 slide,保留 layout / master / theme。"""
    sldIdLst = prs.slides._sldIdLst
    for sldId in list(sldIdLst):
        sldIdLst.remove(sldId)
    # 同时清 rels 防孤儿引用
    part = prs.part
    for rel_id in list(part.rels):
        rel = part.rels[rel_id]
        if "slide" in rel.reltype and "slideLayout" not in rel.reltype and "slideMaster" not in rel.reltype:
            part.drop_rel(rel_id)


# ============================================================================
# 4. 视觉元素 helper
# ============================================================================

def fix_textbox_margins(tf: TextFrame) -> None:
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)


def no_fill(shape: BaseShape) -> None:
    shape.fill.background()


def no_line(shape: BaseShape) -> None:
    shape.line.fill.background()


def rect(slide: Slide, x: Length, y: Length, w: Length, h: Length, color: RGBColor) -> Shape:
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    no_line(shape)
    return shape


def card(
    slide: Slide,
    x: Length,
    y: Length,
    w: Length,
    h: Length,
    *,
    fill: RGBColor = WHITE,
    border: RGBColor = GRAY_300,
    accent: RGBColor | None = None,
) -> Shape:
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = border
    shape.line.width = Pt(0.75)  # 0.75pt border keeps card light without being invisible
    shape.adjustments[0] = 0.05  # corner radius = 5% of shorter side (small rounded corner)
    if accent:
        bar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, Inches(0.04), h)  # ~2.88pt 窄左 accent 条
        bar.fill.solid()
        bar.fill.fore_color.rgb = accent
        no_line(bar)
        bar.adjustments[0] = 0.05
    return shape


def bullets(
    slide: Slide,
    x: Length,
    y: Length,
    w: Length,
    h: Length,
    items: list[str],
    *,
    size: int = 14,
    accent_color: RGBColor = BRAND_PRIMARY,
    body_color: RGBColor = GRAY_900,
) -> Shape:
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    fix_textbox_margins(tf)
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.45  # 中文正文行高 1.45 防止挤压
        r1 = p.add_run(); r1.text = "▎ "
        set_font(r1, size=size, color=accent_color, bold=True)
        r2 = p.add_run(); r2.text = item
        set_font(r2, size=size, color=body_color)
    return box


def table_modern(
    slide: Slide,
    x: Length,
    y: Length,
    w: Length,
    h: Length,
    headers: list[str],
    rows: list[list[str]],
    *,
    header_fill: RGBColor = BRAND_DARK,
    header_color: RGBColor = WHITE,
    body_color: RGBColor = GRAY_900,
    zebra: RGBColor = GRAY_50,
    font_size: int = 11,
    row_height: Length = Inches(0.5),
) -> Any:
    tbl_shape = slide.shapes.add_table(len(rows) + 1, len(headers), x, y, w, h)
    tbl = tbl_shape.table
    for row in tbl.rows:
        row.height = row_height
    tblPr = tbl._tbl.find(qn("a:tblPr"))
    if tblPr is not None:
        tblPr.set("firstRow", "0")
        tblPr.set("bandRow", "0")
    # 表头
    for j, h_text in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.fill.solid(); cell.fill.fore_color.rgb = header_fill
        tf = cell.text_frame
        tf.text = h_text
        for run in tf.paragraphs[0].runs:
            set_font(run, size=font_size, bold=True, color=header_color)
    # body
    for i, row in enumerate(rows):
        for j, txt in enumerate(row):
            cell = tbl.cell(i + 1, j)
            if i % 2 == 0:
                cell.fill.solid(); cell.fill.fore_color.rgb = zebra
            tf = cell.text_frame
            tf.text = str(txt)
            for run in tf.paragraphs[0].runs:
                set_font(run, size=font_size, color=body_color)
    return tbl_shape


def page_decoration(
    slide: Slide,
    num: int | str,
    tint_color: RGBColor,
    *,
    x: Length = Inches(8.8),
    y: Length = Inches(0.25),
    w: Length = Inches(4.4),
    h: Length = Inches(2.0),
    size: int = 140,
) -> Shape:  # 大号装饰数字典型尺寸 120-150pt
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    fix_textbox_margins(tf)
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    p.line_spacing = 1.0
    r = p.add_run()
    r.text = str(num)
    set_font(r, name=FONT_NUM, size=size, bold=True, color=tint_color)
    return box


def section_header(
    slide: Slide,
    title: str,
    num: int | str,
    color: RGBColor,
    *,
    block_x: Length = Inches(0.55),
    block_y: Length = Inches(1.9),
    block_w: Length = Inches(1.7),
    block_h: Length = Inches(2.0),
    title_x: Length = Inches(2.55),
    title_y: Length = Inches(2.3),
    title_w: Length = Inches(10),
    title_h: Length = Inches(1.2),
    num_size: int = 80,
    title_size: int = 36,
) -> tuple[Shape, Shape]:
    """章节扉页：左大色块 + 大数字 + 标题。"""
    rect(slide, block_x, block_y, block_w, block_h, color)
    box = slide.shapes.add_textbox(block_x, block_y, block_w, block_h)
    tf = box.text_frame
    fix_textbox_margins(tf)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = str(num)
    set_font(r, name=FONT_NUM, size=num_size, bold=True, color=WHITE)

    box2 = slide.shapes.add_textbox(title_x, title_y, title_w, title_h)
    tf2 = box2.text_frame
    fix_textbox_margins(tf2)
    r2 = tf2.paragraphs[0].add_run(); r2.text = title
    set_font(r2, size=title_size, bold=True, color=color)
    return box, box2


def embed_picture(
    slide: Slide,
    path: str | Path,
    x: Length,
    y: Length,
    *,
    height: Length | None = None,
    width: Length | None = None,
) -> Any:
    """嵌入图片到 slide。

    传 height 或 width 之一（若都传,width 会被忽略）。
    都不传则按原始像素尺寸嵌入。
    """
    if height is not None:
        return slide.shapes.add_picture(str(path), x, y, height=height)
    if width is not None:
        return slide.shapes.add_picture(str(path), x, y, width=width)
    return slide.shapes.add_picture(str(path), x, y)


def footer(
    slide: Slide,
    page_num: int | str,
    total: int | str,
    *,
    left_text: str | None = None,
    divider: bool = True,
    classification: str | None = None,
    project: str | None = None,
    version: str | None = None,
) -> None:
    """页脚 helper：分隔线 + 右对齐 "N / TOTAL" + 左侧元数据。

    spec: pptx-deck/visual-qa.md 页脚 / 页码完整性 + design-system.md
    页脚字号 9pt / GRAY_500 / FOOTER_TOP=Inches(7.0)。

    用于内容页:`toc / single_focus / compare / cards / bullet_list /
    table / pic_text / summary`。不用于 cover / section_divider / closing。

    左侧文字优先级:
    - `left_text` 非空 → 直接用(用户完全控制)
    - 否则按 "classification · project · version" 拼接(MBB 标准 footer 元数据)
    - 全空 → 不渲染左侧文字
    """
    if divider:
        rect(
            slide,
            LEFT_MARGIN,
            FOOTER_TOP,
            Emu(SLIDE_W - LEFT_MARGIN - RIGHT_MARGIN),
            Pt(0.5),
            GRAY_300,
        )

    text_y = Emu(FOOTER_TOP + Inches(0.1))
    text_h = Inches(0.3)
    num_w = Inches(2.0)

    # 右侧 "N / TOTAL"
    num_box = slide.shapes.add_textbox(
        Emu(SLIDE_W - RIGHT_MARGIN - num_w), text_y, num_w, text_h
    )
    num_tf = num_box.text_frame
    fix_textbox_margins(num_tf)
    num_tf.word_wrap = False
    p = num_tf.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    p.line_spacing = 1.0
    r = p.add_run()
    r.text = f"{page_num} / {total}"
    set_font(r, name=FONT_NUM, size=9, color=GRAY_500)

    # 左侧:用户 left_text 优先;否则用 classification · project · version 组合
    if left_text is None and any([classification, project, version]):
        parts = [p for p in (classification, project, version) if p]
        left_text = " · ".join(parts)

    if left_text:
        left_w = Emu(SLIDE_W - LEFT_MARGIN - RIGHT_MARGIN - num_w - Inches(0.3))
        left_box = slide.shapes.add_textbox(LEFT_MARGIN, text_y, left_w, text_h)
        left_tf = left_box.text_frame
        fix_textbox_margins(left_tf)
        left_tf.word_wrap = False
        p2 = left_tf.paragraphs[0]
        p2.alignment = PP_ALIGN.LEFT
        p2.line_spacing = 1.0
        r2 = p2.add_run()
        r2.text = left_text
        set_font(r2, name=FONT_CN, size=9, color=GRAY_500)


def source_citation(slide: Slide, text: str) -> None:
    """数据 slide 标注 "Source: ..." 引文,位于 footer 分隔线上方。

    BCG / McKinsey 硬要求:任何 chart / table / pic_text(数据 slide)
    必须标注数据来源。

    位置:y=Inches(6.7)(footer 上 0.3"),GRAY_500 9pt,左对齐。
    """
    if not text:
        return
    src_y = Emu(FOOTER_TOP - Inches(0.3))
    src_w = Emu(SLIDE_W - LEFT_MARGIN - RIGHT_MARGIN)
    box = slide.shapes.add_textbox(LEFT_MARGIN, src_y, src_w, Inches(0.25))
    tf = box.text_frame
    fix_textbox_margins(tf)
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    p.line_spacing = 1.0
    r = p.add_run()
    prefix = "" if text.startswith(("Source:", "来源:", "来源：")) else "Source: "
    r.text = f"{prefix}{text}"
    set_font(r, name=FONT_CN, size=9, color=GRAY_500, italic=True)
