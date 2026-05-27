"""cover layout plugin — 封面页:深蓝底 + 主副标 + 可选咨询稿元数据。

实现移植自 themes/tech_blue.py:make_cover(SSOT)。theme 参数可选,不传时
用 helpers default brand token(BRAND_DARK / BRAND_PRIMARY / etc)。

元数据布局:
- 右上角:classification 徽标(若有,如 "CONFIDENTIAL" / "INTERNAL")
- 左下角:prepared_by · date · version · project_code(任一非空即渲染)
"""
from __future__ import annotations

from types import ModuleType

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Emu, Inches

from . import SLIDE_H, SLIDE_W, WHITE, fix_textbox_margins, no_line, rect, set_font
from ._base import register_layout
from ._internals import (
    add_title as _add_title,  # noqa: F401  (kept for symmetry / future use)
    blank_slide,
    resolve_brand,
    text_in_box,
)
from layout import Box, full_region, stack  # layout.py at sys.path top-level


@register_layout("cover")
def make_cover(
    prs: _Pres,
    title: str,
    subtitle: str,
    *,
    theme: ModuleType | None = None,
    prepared_by: str = "",
    date: str = "",
    version: str = "",
    project_code: str = "",
    classification: str = "",
) -> Slide:
    T = resolve_brand(theme)
    s = blank_slide(prs)
    rect(s, 0, 0, SLIDE_W, SLIDE_H, T["PRIMARY_DEEP"])

    # Hero 几何装饰(右上角同心圆 + 左下细线网格)
    for i, radius_in in enumerate([3.8, 2.6, 1.5]):
        diam = Inches(radius_in * 2)
        cx = SLIDE_W - Inches(radius_in - 0.3)
        cy = -Inches(radius_in - 0.5)
        circle = s.shapes.add_shape(MSO_SHAPE.OVAL, cx, cy, diam, diam)
        circle.fill.solid()
        base = T["PRIMARY_DEEP"]
        fill_color = RGBColor(
            min(255, base[0] + (i + 1) * 18),
            min(255, base[1] + (i + 1) * 18),
            min(255, base[2] + (i + 1) * 18),
        )
        circle.fill.fore_color.rgb = fill_color
        no_line(circle)

    grid_y = Inches(6.4)
    for i in range(6):
        rect(s, Inches(0.55 + i * 0.18), grid_y, Inches(0.12),
             Inches(0.015), T["PRIMARY_TINT"])

    # 主副标(左对齐,中央偏左)
    title_box = Box(Inches(0.8), Inches(2.5), Inches(11.0), Inches(1.6))
    text_in_box(s, title_box, title, theme=theme, size=54, bold=True, color=WHITE)
    # 分隔线
    rect(s, Inches(0.8), Inches(4.3), Inches(0.6), Inches(0.04), T["ACCENT"])
    sub_box = Box(Inches(0.8), Inches(4.5), Inches(11.0), Inches(0.8))
    text_in_box(s, sub_box, subtitle, theme=theme, size=22,
                color=T["PRIMARY_TINT"])

    # 右上 classification 徽标
    if classification:
        cls_w = Inches(2.5)
        cls_box = s.shapes.add_textbox(
            Inches(SLIDE_W.inches - 0.55 - 2.5), Inches(0.3), cls_w, Inches(0.35))
        fix_textbox_margins(cls_box.text_frame)
        cls_box.text_frame.word_wrap = False
        p = cls_box.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.RIGHT
        r = p.add_run()
        r.text = classification.upper()
        set_font(r, name=T["FONT_HEADER"], size=10, bold=True,
                 color=T["PRIMARY_TINT"])

    # 左下元数据
    meta_parts = [v for v in (prepared_by, date, version, project_code) if v]
    if meta_parts:
        meta_w = Inches(SLIDE_W.inches - 1.1)
        meta_box = s.shapes.add_textbox(
            Inches(0.55), Inches(SLIDE_H.inches - 0.5), meta_w, Inches(0.3))
        fix_textbox_margins(meta_box.text_frame)
        meta_box.text_frame.word_wrap = False
        p = meta_box.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        r = p.add_run()
        r.text = " · ".join(meta_parts)
        set_font(r, name=T["FONT_BODY"], size=11, color=T["PRIMARY_TINT"])

    return s
