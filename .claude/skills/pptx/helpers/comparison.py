"""comparison layout plugin — N 列对比表(header bar 风,跟 cards 视觉拉开)。

实现移植自 themes/tech_blue.py:make_compare(SSOT,改名 comparison 与 enum 对齐)。

每列 = 顶部彩色 header(主推 PRIMARY 实色+白字,其他 GRAY_300+深字)+ 下方 body 区
(主推 PRIMARY_TINT 浅填充,其他 WHITE)。item.recommended=True 标主推列。
"""
from __future__ import annotations

from types import ModuleType
from typing import Any

from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Inches, Pt

from . import (
    GRAY_300,
    GRAY_700,
    WHITE,
    fix_textbox_margins,
    is_handout,
    no_line,
    rect,
    set_font,
)
from ._base import register_layout
from ._internals import add_title, blank_slide, resolve_brand, text_in_box
from layout import Box, columns, content_region, stack


@register_layout("comparison")
def make_comparison(
    prs: _Pres,
    title: str,
    items: list[dict[str, Any]],
    *,
    theme: ModuleType | None = None,
) -> Slide:
    T = resolve_brand(theme)
    s = blank_slide(prs)
    add_title(s, title, theme=theme)
    region = content_region()
    block_h = Inches(4.6) if is_handout() else Inches(3.5)
    row = stack(region, [block_h], align="middle")[0]
    cols = columns(row, len(items), gap=Inches(0.15))
    header_h = Inches(0.7)
    body_size = 14 if is_handout() else 16
    for col, item in zip(cols, items):
        is_recommended = bool(item.get("recommended", False))
        header_fill = T["PRIMARY"] if is_recommended else GRAY_300
        header_color = WHITE if is_recommended else T["PRIMARY_DEEP"]
        body_fill = T["PRIMARY_TINT"] if is_recommended else WHITE
        body_color = T["PRIMARY_DEEP"] if is_recommended else GRAY_700

        # header
        rect(s, col.x, col.y, col.w, header_h, header_fill)
        h_tb = s.shapes.add_textbox(col.x, col.y, col.w, header_h)
        fix_textbox_margins(h_tb.text_frame)
        h_tb.text_frame.word_wrap = True
        hp = h_tb.text_frame.paragraphs[0]
        hp.alignment = PP_ALIGN.CENTER
        hr = hp.add_run(); hr.text = item["title"]
        set_font(hr, name=T["FONT_HEADER"], size=18, bold=True,
                 color=header_color)

        # body
        body_y = col.y + header_h
        body_h = block_h - header_h
        body_shape = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, col.x, body_y,
                                        col.w, body_h)
        body_shape.fill.solid(); body_shape.fill.fore_color.rgb = body_fill
        body_shape.line.color.rgb = GRAY_300
        body_shape.line.width = Pt(0.75)

        # 主推 ✓ 标
        if is_recommended:
            badge_w = Inches(0.55)
            badge_x = col.x + col.w - badge_w - Inches(0.1)
            badge_y = col.y + header_h + Inches(0.1)
            badge = s.shapes.add_shape(MSO_SHAPE.OVAL, badge_x, badge_y,
                                       badge_w, badge_w)
            badge.fill.solid(); badge.fill.fore_color.rgb = T["ACCENT"]
            no_line(badge)
            b_tb = s.shapes.add_textbox(badge_x, badge_y, badge_w, badge_w)
            fix_textbox_margins(b_tb.text_frame)
            bp = b_tb.text_frame.paragraphs[0]
            bp.alignment = PP_ALIGN.CENTER
            br = bp.add_run(); br.text = "✓"
            set_font(br, name=T["FONT_HEADER"], size=18, bold=True,
                     color=WHITE)

        body_box = Box(col.x + Inches(0.25), body_y + Inches(0.25),
                       col.w - Inches(0.5), body_h - Inches(0.5))
        text_in_box(s, body_box, item["body"], theme=theme, size=body_size,
                    color=body_color)
    return s
