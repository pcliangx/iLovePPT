"""radial layout plugin — central node + N spokes(圆形围绕中心,可选连线)。

实现移植自 themes/template_golden.py:make_radial(SSOT)。

center: {title, body?}。spokes: list of {title, body}(N=3-6 推荐)。
"""
from __future__ import annotations

import math
from types import ModuleType

from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Emu, Inches

from . import (
    GRAY_300,
    GRAY_700,
    WHITE,
    connector,
    fix_textbox_margins,
    no_line,
    set_font,
)
from ._base import register_layout
from ._internals import add_title, blank_slide, resolve_brand, text_in_box
from layout import Box, content_region


@register_layout("radial")
def make_radial(
    prs: _Pres,
    title: str,
    center: dict[str, str],
    spokes: list[dict[str, str]],
    *,
    theme: ModuleType | None = None,
) -> Slide:
    T = resolve_brand(theme)
    s = blank_slide(prs)
    add_title(s, title, theme=theme)
    region = content_region()
    n = len(spokes)

    cx = region.x + Emu(region.w // 2)
    cy = region.y + Emu(int(region.h * 0.55))
    center_d = Inches(1.4)
    spoke_d = Inches(0.9)
    radius = Inches(2.4) if n <= 4 else Inches(2.2)
    spoke_text_w = Inches(1.7)
    spoke_text_h = Inches(0.7)

    # 中心圆
    cc_x = cx - Emu(center_d // 2)
    cc_y = cy - Emu(center_d // 2)
    cc = s.shapes.add_shape(MSO_SHAPE.OVAL, cc_x, cc_y, center_d, center_d)
    cc.fill.solid()
    cc.fill.fore_color.rgb = T["PRIMARY_DEEP"]
    no_line(cc)
    cc_tb = s.shapes.add_textbox(cc_x, cc_y, center_d, center_d)
    fix_textbox_margins(cc_tb.text_frame)
    cc_tb.text_frame.vertical_anchor = 3
    cc_tb.text_frame.word_wrap = True
    pc = cc_tb.text_frame.paragraphs[0]
    pc.alignment = PP_ALIGN.CENTER
    rc = pc.add_run()
    rc.text = center.get("title", "")
    set_font(rc, name=T["FONT_HEADER"], size=14, bold=True, color=WHITE)

    # N spokes
    for i, spoke in enumerate(spokes):
        angle_deg = -90 + i * (360 / n)
        angle_rad = math.radians(angle_deg)
        sx = cx + Emu(int(radius * math.cos(angle_rad)))
        sy = cy + Emu(int(radius * math.sin(angle_rad)))
        sc_x = sx - Emu(spoke_d // 2)
        sc_y = sy - Emu(spoke_d // 2)

        # connector
        center_edge_x = cx + Emu(int((center_d // 2) * math.cos(angle_rad)))
        center_edge_y = cy + Emu(int((center_d // 2) * math.sin(angle_rad)))
        spoke_edge_x = sx - Emu(int((spoke_d // 2) * math.cos(angle_rad)))
        spoke_edge_y = sy - Emu(int((spoke_d // 2) * math.sin(angle_rad)))
        connector(s, center_edge_x, center_edge_y,
                  spoke_edge_x, spoke_edge_y, color=GRAY_300, weight_pt=1.5)

        # spoke 圆
        sc = s.shapes.add_shape(MSO_SHAPE.OVAL, sc_x, sc_y, spoke_d, spoke_d)
        sc.fill.solid(); sc.fill.fore_color.rgb = T["PRIMARY"]
        no_line(sc)
        sn_tb = s.shapes.add_textbox(sc_x, sc_y, spoke_d, spoke_d)
        fix_textbox_margins(sn_tb.text_frame)
        sn_tb.text_frame.vertical_anchor = 3
        psn = sn_tb.text_frame.paragraphs[0]
        psn.alignment = PP_ALIGN.CENTER
        rsn = psn.add_run()
        rsn.text = str(i + 1)
        set_font(rsn, name=T["FONT_NUM"], size=18, bold=True, color=WHITE)

        # spoke text 位置(top spoke 特例:text 放 spoke 下方避开 deck title)
        is_top = -110 <= angle_deg <= -70
        if is_top:
            text_cx = sx
            text_cy = sy + Emu(int(Inches(0.9)))
        else:
            text_offset = Inches(1.55)
            text_cx = sx + Emu(int(text_offset * math.cos(angle_rad)))
            text_cy = sy + Emu(int(text_offset * math.sin(angle_rad)))

        text_x = text_cx - Emu(spoke_text_w // 2)
        text_y = text_cy - Emu(spoke_text_h // 2)
        text_x = max(Emu(int(region.x)),
                     min(text_x, Emu(int(region.x + region.w - spoke_text_w))))
        text_y = max(Emu(int(region.y)),
                     min(text_y, Emu(int(region.y + region.h - spoke_text_h))))

        title_box = Box(text_x, text_y, spoke_text_w, Inches(0.33))
        text_in_box(s, title_box, spoke.get("title", ""), theme=theme,
                    size=13, bold=True, color=T["PRIMARY_DEEP"],
                    align=PP_ALIGN.CENTER, valign="middle")
        body_box = Box(text_x, text_y + Inches(0.35), spoke_text_w,
                       Emu(spoke_text_h - Inches(0.35)))
        text_in_box(s, body_box, spoke.get("body", ""), theme=theme,
                    size=10, color=GRAY_700, align=PP_ALIGN.CENTER,
                    valign="top")
    return s
