"""summary layout plugin — 总结 N 条结论(紧凑数字方块 + 等高文字行,整体居中)。

实现移植自 themes/tech_blue.py:make_summary(SSOT)。

按内容算单元高度 + 整体垂直居中,避免 number box 过高 / 短结论文字撑不满的视觉失衡。
"""
from __future__ import annotations

from types import ModuleType

from pptx.enum.text import PP_ALIGN
from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Emu, Inches

from . import (
    GRAY_900,
    WHITE,
    fix_textbox_margins,
    is_handout,
    rect,
    set_font,
)
from ._base import register_layout
from ._internals import add_title, blank_slide, resolve_brand
from layout import content_region


@register_layout("summary")
def make_summary(
    prs: _Pres,
    conclusions: list[str],
    *,
    theme: ModuleType | None = None,
    title: str = "核心结论",
) -> Slide:
    T = resolve_brand(theme)
    s = blank_slide(prs)
    add_title(s, title, theme=theme, size=36, color=T["PRIMARY_DEEP"])
    region = content_region()
    n = len(conclusions)
    text_size = 16 if is_handout() else 22
    gap = Inches(0.25)
    safe_top = Inches(0.7)
    available_h = region.h - safe_top
    desired_unit_h = Inches(1.2) if is_handout() else Inches(0.9)
    max_unit_h = Emu((available_h - gap * (n - 1)) // n)
    unit_h = min(desired_unit_h, max_unit_h)
    total_h = unit_h * n + gap * (n - 1)
    start_y = region.y + safe_top + (available_h - total_h) // 2
    num_w = Inches(1.0)
    text_x = region.x + num_w + Inches(0.3)
    text_w = region.w - num_w - Inches(0.3)
    for i, c in enumerate(conclusions):
        y = start_y + (unit_h + gap) * i
        rect(s, region.x, y, num_w, unit_h, T["PRIMARY"])
        n_tb = s.shapes.add_textbox(region.x, y, num_w, unit_h)
        fix_textbox_margins(n_tb.text_frame)
        n_tb.text_frame.vertical_anchor = 3
        pn = n_tb.text_frame.paragraphs[0]
        pn.alignment = PP_ALIGN.CENTER
        rn = pn.add_run(); rn.text = str(i + 1)
        set_font(rn, name=T["FONT_NUM"], size=36, bold=True, color=WHITE)
        t_tb = s.shapes.add_textbox(text_x, y, text_w, unit_h)
        fix_textbox_margins(t_tb.text_frame)
        t_tb.text_frame.word_wrap = True
        t_tb.text_frame.vertical_anchor = 3
        rt = t_tb.text_frame.paragraphs[0].add_run()
        rt.text = c
        set_font(rt, name=T["FONT_HEADER"], size=text_size, color=GRAY_900)
    return s
