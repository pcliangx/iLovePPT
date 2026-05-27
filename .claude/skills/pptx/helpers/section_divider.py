"""section_divider layout plugin — 章节扉页:巨型背景数字 + 章节小标 + 标题。

实现移植自 themes/tech_blue.py:make_section_divider(SSOT)。
"""
from __future__ import annotations

from types import ModuleType

from pptx.enum.text import PP_ALIGN
from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Inches

from . import GRAY_100, fix_textbox_margins, rect, set_font
from ._base import register_layout
from ._internals import add_title, blank_slide, resolve_brand, text_in_box
from layout import Box


@register_layout("section_divider")
def make_section_divider(
    prs: _Pres,
    num: int | str,
    title: str,
    *,
    theme: ModuleType | None = None,
) -> Slide:
    """章节分隔页。

    视觉层次:
    1. 背景层:巨型 "01" 占 60% 屏幕高,极浅灰(GRAY_100),营造大气版式感
    2. 前景:左上小字 "CHAPTER 01" + 主标题在背景数字下方
    """
    T = resolve_brand(theme)
    s = blank_slide(prs)
    # 背景巨型数字水印(右半屏,极浅灰)
    bg_num = f"{int(num):02d}" if isinstance(num, int) or str(num).isdigit() else str(num)
    bg_tb = s.shapes.add_textbox(Inches(4.0), Inches(0.3), Inches(9.0), Inches(7.0))
    fix_textbox_margins(bg_tb.text_frame)
    bg_p = bg_tb.text_frame.paragraphs[0]
    bg_p.alignment = PP_ALIGN.RIGHT
    bg_r = bg_p.add_run(); bg_r.text = bg_num
    set_font(bg_r, name=T["FONT_NUM"], size=400, bold=True, color=GRAY_100)

    # 左侧 vertical accent bar(细蓝竖条)
    rect(s, Inches(0.55), Inches(2.3), Inches(0.08), Inches(2.9), T["PRIMARY"])

    # 前景:左上 "CHAPTER NN" 小字
    chap_box = Box(Inches(0.85), Inches(2.4), Inches(6.0), Inches(0.5))
    text_in_box(s, chap_box, f"CHAPTER {bg_num}", theme=theme, size=14,
                bold=True, color=T["PRIMARY"], font=T["FONT_NUM"])

    # 前景:大章节标题(覆盖背景数字上层)
    title_box = Box(Inches(0.85), Inches(3.0), Inches(11.0), Inches(2.0))
    text_in_box(s, title_box, title, theme=theme, size=52, bold=True,
                color=T["PRIMARY_DEEP"])
    return s
