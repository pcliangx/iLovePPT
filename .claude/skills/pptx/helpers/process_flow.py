"""process_flow layout plugin — N 步 vertical 流程(numbered circle + step_title + step_desc + arrows)。

实现移植自 themes/template_golden.py:make_process_flow(SSOT)。

steps: list of {title, desc}。N=3-7 推荐;N>7 拆页。
"""
from __future__ import annotations

from types import ModuleType
from typing import Any

from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Emu, Inches

from . import (
    GRAY_300,
    GRAY_700,
    WHITE,
    fix_textbox_margins,
    no_line,
    rect,
    set_font,
)
from ._base import register_layout
from ._internals import add_title, blank_slide, resolve_brand, text_in_box
from layout import Box, content_region, stack


@register_layout("process_flow")
def make_process_flow(
    prs: _Pres,
    title: str,
    steps: list[dict[str, Any]],
    *,
    theme: ModuleType | None = None,
) -> Slide:
    T = resolve_brand(theme)
    s = blank_slide(prs)
    add_title(s, title, theme=theme)
    region = content_region()
    n = len(steps)
    gap = Inches(0.18)
    row_h = Emu((region.h - gap * (n - 1)) // n)
    rboxes = stack(region, [row_h] * n, gap=gap, align="top")

    circle_d = Inches(0.7)
    desc_left_offset = Inches(1.0)

    for i, (row, step) in enumerate(zip(rboxes, steps)):
        circle_y = row.y + Emu((row.h - circle_d) // 2)
        circle = s.shapes.add_shape(MSO_SHAPE.OVAL,
                                    row.x, circle_y, circle_d, circle_d)
        circle.fill.solid()
        circle.fill.fore_color.rgb = T["PRIMARY"]
        no_line(circle)
        n_tb = s.shapes.add_textbox(row.x, circle_y, circle_d, circle_d)
        fix_textbox_margins(n_tb.text_frame)
        n_tb.text_frame.vertical_anchor = 3
        pn = n_tb.text_frame.paragraphs[0]
        pn.alignment = PP_ALIGN.CENTER
        rn = pn.add_run()
        rn.text = str(i + 1)
        set_font(rn, name=T["FONT_NUM"], size=20, bold=True, color=WHITE)

        # connector(垂直短线,最后一步不画)
        if i < n - 1:
            conn_x = row.x + Emu(circle_d // 2) - Emu(Inches(0.015))
            conn_y = circle_y + circle_d
            conn_h = row.h - circle_d + gap
            conn = rect(s, conn_x, conn_y, Inches(0.03), conn_h, GRAY_300)
            no_line(conn)

        text_x = row.x + desc_left_offset
        text_w = row.w - desc_left_offset
        title_box = Box(text_x, row.y, text_w, Inches(0.4))
        text_in_box(s, title_box, step.get("title", ""), theme=theme,
                    size=18, bold=True, color=T["PRIMARY_DEEP"],
                    valign="middle")
        desc_box = Box(text_x, row.y + Inches(0.4), text_w,
                       Emu(row.h - Inches(0.4)))
        text_in_box(s, desc_box, step.get("desc", ""), theme=theme, size=13,
                    color=GRAY_700, valign="top")
    return s
