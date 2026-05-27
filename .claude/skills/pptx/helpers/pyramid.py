"""pyramid layout plugin — N-tier 金字塔(顶窄底宽,色梯度,可选侧栏)。

实现移植自 themes/template_golden.py:make_pyramid(SSOT)。

tiers 从顶到底(顶=最 high-level,底=最 detailed)。
side_left / side_right(可选 1-2 项):各侧 stack 显 {title, body}。
"""
from __future__ import annotations

from types import ModuleType

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Emu, Inches

from . import (
    GRAY_700,
    WHITE,
    fix_textbox_margins,
    is_handout,
    no_line,
    set_font,
)
from ._base import register_layout
from ._internals import add_title, blank_slide, resolve_brand, text_in_box
from layout import Box, content_region


def _lerp_color(c1: RGBColor, c2: RGBColor, t: float) -> RGBColor:
    """线性插值 c1 → c2,t in [0, 1]。"""
    r = int(c1[0] + (c2[0] - c1[0]) * t)
    g = int(c1[1] + (c2[1] - c1[1]) * t)
    b = int(c1[2] + (c2[2] - c1[2]) * t)
    return RGBColor(r, g, b)


def _render_side_column(
    slide: Slide, x: int, y: int, w: int, h: int,
    items: list[dict[str, str]],
    theme: ModuleType | None,
    T: dict,
) -> None:
    """侧栏:N 个 {title, body} 项,纵向 stack。"""
    n = len(items)
    gap = Inches(0.25)
    item_h = Emu((h - gap * (n - 1)) // n)
    for i, item in enumerate(items):
        item_y = y + (item_h + gap) * i
        title_box = Box(Emu(int(x)), Emu(int(item_y)), Emu(int(w)),
                        Inches(0.4))
        text_in_box(slide, title_box, item.get("title", ""), theme=theme,
                    size=14, bold=True, color=T["PRIMARY_DEEP"], valign="top")
        body_box = Box(Emu(int(x)), Emu(int(item_y + Inches(0.4))),
                       Emu(int(w)), Emu(int(item_h - Inches(0.4))))
        text_in_box(slide, body_box, item.get("body", ""), theme=theme,
                    size=12, color=GRAY_700, valign="top")


@register_layout("pyramid")
def make_pyramid(
    prs: _Pres,
    title: str,
    tiers: list[str],
    *,
    theme: ModuleType | None = None,
    side_left: list[dict[str, str]] | None = None,
    side_right: list[dict[str, str]] | None = None,
) -> Slide:
    T = resolve_brand(theme)
    s = blank_slide(prs)
    add_title(s, title, theme=theme)
    region = content_region()
    n = len(tiers)

    has_side = bool(side_left or side_right)
    pyramid_w_ratio = 0.42 if has_side else 0.6
    pyramid_w = Emu(int(region.w * pyramid_w_ratio))
    pyramid_x = region.x + Emu((region.w - pyramid_w) // 2)
    safe_top = Inches(0.4)
    pyramid_total_h = region.h - safe_top
    tier_gap = Inches(0.06)
    tier_h = Emu((pyramid_total_h - tier_gap * (n - 1)) // n)

    primary_tint = T["PRIMARY_TINT"]
    primary = T["PRIMARY"]

    for i, tier_text in enumerate(tiers):
        width_ratio = (i + 1) / n
        this_w = Emu(int(pyramid_w * width_ratio))
        this_x = pyramid_x + Emu((pyramid_w - this_w) // 2)
        this_y = region.y + safe_top + (tier_h + tier_gap) * i
        color = _lerp_color(primary_tint, primary, (i + 0.5) / n)
        bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, this_x, this_y,
                                 this_w, tier_h)
        bar.fill.solid()
        bar.fill.fore_color.rgb = color
        no_line(bar)
        text_color = WHITE if i >= n // 2 else T["PRIMARY_DEEP"]
        text_size = 16 if is_handout() else 18
        t_tb = s.shapes.add_textbox(this_x, this_y, this_w, tier_h)
        fix_textbox_margins(t_tb.text_frame)
        t_tb.text_frame.vertical_anchor = 3
        pt = t_tb.text_frame.paragraphs[0]
        pt.alignment = PP_ALIGN.CENTER
        rt = pt.add_run()
        rt.text = tier_text
        set_font(rt, name=T["FONT_HEADER"], size=text_size, bold=True,
                 color=text_color)

    # 侧栏
    if has_side:
        side_w = Emu((region.w - pyramid_w) // 2 - Inches(0.2))
        side_y = region.y + safe_top
        side_h = pyramid_total_h
        if side_left:
            _render_side_column(s, region.x, side_y, side_w, side_h,
                                side_left, theme, T)
        if side_right:
            right_x = region.x + region.w - side_w
            _render_side_column(s, right_x, side_y, side_w, side_h,
                                side_right, theme, T)
    return s
