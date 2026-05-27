"""quote layout plugin — 大字引用 + 引用源(attribution)。

新建实现:用于"客户证言""高管金句"等单引用页。

布局:
- 左侧巨型引号 " 装饰
- 中央大字引文(36pt italic)
- 引文下方分隔线 + attribution(— 姓名 / 职位 / 公司)
"""
from __future__ import annotations

from types import ModuleType

from pptx.enum.text import PP_ALIGN
from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Inches

from . import GRAY_700, fix_textbox_margins, rect, set_font
from ._base import register_layout
from ._internals import blank_slide, resolve_brand, text_in_box
from layout import Box, content_region, stack


@register_layout("quote")
def make_quote(
    prs: _Pres,
    quote: str,
    *,
    theme: ModuleType | None = None,
    attribution: str = "",
    role: str = "",
) -> Slide:
    """单页大字引用。

    quote: 引文正文(建议 ≤ 80 字,过长改 bullet_list)
    attribution: 姓名(必填,引用必须有源)
    role: 职位 / 公司(可选,显示在姓名下方)
    """
    T = resolve_brand(theme)
    s = blank_slide(prs)
    region = content_region()

    # 左上巨型引号装饰
    quote_box = Box(Inches(0.6), Inches(1.0), Inches(2.0), Inches(2.5))
    text_in_box(
        s, quote_box, "“",  # 中点向左 left double quote
        theme=theme, size=200, bold=True, color=T["PRIMARY_TINT"],
        font=T["FONT_NUM"],
    )

    # 引文主体(垂直居中)
    blocks = stack(region, [Inches(3.0), Inches(0.08), Inches(0.8)],
                   gap=Inches(0.3), align="middle")
    quote_main, divider_slot, attr_slot = blocks

    text_in_box(s, quote_main, quote, theme=theme, size=32, bold=False,
                color=T["PRIMARY_DEEP"], align=PP_ALIGN.CENTER,
                valign="middle")

    # 分隔细线(居中,80% 宽)
    div_w = Inches(2.0)
    div_x = divider_slot.x + (divider_slot.w - div_w) // 2
    rect(s, div_x, divider_slot.y, div_w, Inches(0.04), T["ACCENT"])

    # attribution + role
    attr_text = f"— {attribution}" if attribution else ""
    if role:
        attr_text = f"{attr_text}\n{role}" if attr_text else role
    if attr_text:
        text_in_box(s, attr_slot, attr_text, theme=theme, size=16,
                    bold=False, color=GRAY_700, align=PP_ALIGN.CENTER,
                    valign="top")
    return s
