"""timeline layout plugin — 水平时间轴 N 个里程碑节点 + 连线。

参考 themes/template_training.py:make_timeline_band_3 思路,做更通用的 N 节点
水平 timeline:每个节点 = 上方 label(title)+ 节点圆(numbered)+ 下方 desc。
N=3-7 推荐。
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
from layout import Box, columns, content_region, stack


@register_layout("timeline")
def make_timeline(
    prs: _Pres,
    title: str,
    milestones: list[dict[str, Any]],
    *,
    theme: ModuleType | None = None,
) -> Slide:
    """N 个 milestones,每个 {title, desc, date?}。

    布局:垂直三层 — 上 label(title + 可选 date)+ 中 节点圆 + 下 desc。
    节点圆之间用水平线连。
    """
    T = resolve_brand(theme)
    s = blank_slide(prs)
    add_title(s, title, theme=theme)
    region = content_region()
    n = len(milestones)

    # 三层分布
    band_h = Inches(0.06)  # 中间细线
    circle_d = Inches(0.7)
    top_block_h = Inches(1.2)
    bot_block_h = Inches(2.0)
    blocks = stack(
        region,
        [top_block_h, circle_d, bot_block_h],
        gap=Inches(0.2),
        align="middle",
    )
    top_band, mid_band, bot_band = blocks

    # 中带子的横线(从首节点到末节点)
    cols_top = columns(top_band, n, gap=Inches(0.1))
    cols_bot = columns(bot_band, n, gap=Inches(0.1))
    cols_mid = columns(mid_band, n, gap=Inches(0.1))

    # 节点之间的连线(水平)
    first_cx = cols_mid[0].x + Emu(cols_mid[0].w // 2)
    last_cx = cols_mid[-1].x + Emu(cols_mid[-1].w // 2)
    line_y = mid_band.y + Emu((mid_band.h - band_h) // 2)
    line_w = Emu(last_cx - first_cx)
    rect(s, first_cx, line_y, line_w, band_h, T["PRIMARY_TINT"])

    for i, (tcol, mcol, bcol, ms) in enumerate(
        zip(cols_top, cols_mid, cols_bot, milestones)
    ):
        # 上方 label(title + date)
        title_text = ms.get("title", "")
        date_text = ms.get("date", "")
        upper_text = (
            f"{date_text}\n{title_text}" if date_text else title_text
        )
        text_in_box(s, tcol, upper_text, theme=theme, size=14, bold=True,
                    color=T["PRIMARY_DEEP"], align=PP_ALIGN.CENTER,
                    valign="bottom")

        # 中间节点圆(numbered)
        cx = mcol.x + Emu((mcol.w - circle_d) // 2)
        cy = mcol.y + Emu((mcol.h - circle_d) // 2)
        circle = s.shapes.add_shape(MSO_SHAPE.OVAL, cx, cy, circle_d,
                                    circle_d)
        circle.fill.solid(); circle.fill.fore_color.rgb = T["PRIMARY"]
        no_line(circle)
        n_tb = s.shapes.add_textbox(cx, cy, circle_d, circle_d)
        fix_textbox_margins(n_tb.text_frame)
        n_tb.text_frame.vertical_anchor = 3
        pn = n_tb.text_frame.paragraphs[0]
        pn.alignment = PP_ALIGN.CENTER
        rn = pn.add_run(); rn.text = str(i + 1)
        set_font(rn, name=T["FONT_NUM"], size=16, bold=True, color=WHITE)

        # 下方 desc
        text_in_box(s, bcol, ms.get("desc", ""), theme=theme, size=12,
                    color=GRAY_700, align=PP_ALIGN.CENTER, valign="top")
    return s
