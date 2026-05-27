"""single_focus layout plugin — Hero 大数字 / 大字页。

实现移植自 themes/tech_blue.py:make_single_focus(SSOT)。

big_number 槽 1.95 in + valign middle:120pt 字 ascent ~1.67 in,
旧版 1.6 in + top-anchor 会让字下沉到 big_text 槽。
"""
from __future__ import annotations

from types import ModuleType

from pptx.enum.text import PP_ALIGN
from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Inches

from . import GRAY_700
from ._base import register_layout
from ._internals import blank_slide, resolve_brand, text_in_box
from layout import content_region, stack


@register_layout("single_focus")
def make_single_focus(
    prs: _Pres,
    *,
    theme: ModuleType | None = None,
    big_text: str = "",
    big_number: str = "",
    explanation: str = "",
) -> Slide:
    T = resolve_brand(theme)
    s = blank_slide(prs)
    region = content_region()
    blocks = stack(region, [Inches(1.95), Inches(0.9), Inches(0.6)],
                   gap=Inches(0.25), align="middle")
    text_in_box(s, blocks[0], big_number, theme=theme, size=120, bold=True,
                color=T["PRIMARY"], font=T["FONT_NUM"],
                align=PP_ALIGN.CENTER, valign="middle")
    text_in_box(s, blocks[1], big_text, theme=theme, size=36, bold=True,
                color=T["PRIMARY_DEEP"], align=PP_ALIGN.CENTER, valign="middle")
    text_in_box(s, blocks[2], explanation, theme=theme, size=18,
                color=GRAY_700, align=PP_ALIGN.CENTER, valign="top")
    return s
