"""toc layout plugin — 目录页:标题"目录" + N 行章节(编号 + 标题)。

实现移植自 themes/tech_blue.py:make_toc(SSOT)。
"""
from __future__ import annotations

from types import ModuleType

from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Emu, Inches

from . import FONT_NUM, GRAY_700, fix_textbox_margins, set_font
from ._base import register_layout
from ._internals import add_title, blank_slide, resolve_brand
from layout import Box, content_region, rows  # layout.py at sys.path top-level


@register_layout("toc")
def make_toc(
    prs: _Pres,
    sections: list[str],
    *,
    theme: ModuleType | None = None,
) -> Slide:
    T = resolve_brand(theme)
    s = blank_slide(prs)
    add_title(s, "目录", theme=theme, size=42, y=Inches(0.6),
              color=T["PRIMARY_DEEP"])
    rboxes = rows(content_region(), len(sections))
    for i, (rb, sec) in enumerate(zip(rboxes, sections)):
        # 序号 box(左侧固定宽度)
        num_box = Box(x=rb.x, y=rb.y, w=Inches(0.7), h=rb.h)
        n_tb = s.shapes.add_textbox(num_box.x, num_box.y, num_box.w, num_box.h)
        fix_textbox_margins(n_tb.text_frame)
        rn = n_tb.text_frame.paragraphs[0].add_run()
        rn.text = f"{i+1:02d}"
        set_font(rn, name=T["FONT_NUM"], size=28, bold=True,
                 color=T["PRIMARY"])
        # 标题 box(剩余宽度)
        title_x = Emu(rb.x + Inches(0.9))
        title_w = Emu(rb.w - Inches(0.9))
        t_tb = s.shapes.add_textbox(title_x, rb.y, title_w, rb.h)
        fix_textbox_margins(t_tb.text_frame)
        rt = t_tb.text_frame.paragraphs[0].add_run()
        rt.text = sec
        set_font(rt, name=T["FONT_HEADER"], size=22, color=GRAY_700)
    return s
