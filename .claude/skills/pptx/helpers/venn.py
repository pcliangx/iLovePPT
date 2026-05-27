"""venn layout plugin — 2 或 3 圆 Venn 图(交叠 + 标签)。

新建实现(themes 无现成参考)。N=2-3 推荐;N>3 视觉过载,建议改 matrix 或 cards。

sets: list of {label, body?},顺序对应:
- N=2:左右两圆,中心 = 共同
- N=3:三角排布,中心 = 三方共同
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
    GRAY_700,
    WHITE,
    fix_textbox_margins,
    no_line,
    set_font,
)
from ._base import register_layout
from ._internals import add_title, blank_slide, resolve_brand, text_in_box
from layout import Box, content_region


@register_layout("venn")
def make_venn(
    prs: _Pres,
    title: str,
    sets: list[dict[str, Any]],
    *,
    theme: ModuleType | None = None,
    intersection_label: str = "",
) -> Slide:
    """Venn 图。

    N=2: 左右两圆水平排,交叠区中央放 intersection_label(如有)。
    N=3: 三角排布(顶 + 左下 + 右下),三圆中心共同区放 intersection_label。
    """
    T = resolve_brand(theme)
    n = len(sets)
    if n not in (2, 3):
        raise ValueError(f"venn 仅支持 2 或 3 个 set,得到 {n}")
    s = blank_slide(prs)
    add_title(s, title, theme=theme)
    region = content_region()

    # 半透明色梯度(用 muted_blue / accent 简化非真透明)
    fills = [T["PRIMARY"], T["ACCENT"], T["PRIMARY_DEEP"]]
    circle_d = Inches(3.6) if n == 2 else Inches(3.2)
    overlap = Inches(1.0) if n == 2 else Inches(0.9)

    cx_center = region.x + Emu(region.w // 2)
    cy_center = region.y + Emu(region.h // 2)

    positions: list[tuple[int, int]] = []
    if n == 2:
        # 水平排:两圆中心距 = circle_d - overlap
        gap = circle_d - overlap
        left_cx = cx_center - Emu(gap // 2)
        right_cx = cx_center + Emu(gap // 2)
        positions = [(left_cx, cy_center), (right_cx, cy_center)]
    else:
        # 三角排:顶 + 左下 + 右下
        offset = Emu(int((circle_d - overlap) // 2))
        # vertical offset for 60° triangle ~= offset * sqrt(3)
        vert_offset = Emu(int(offset * 1.732 / 2))
        positions = [
            (cx_center, cy_center - vert_offset),
            (cx_center - offset, cy_center + vert_offset),
            (cx_center + offset, cy_center + vert_offset),
        ]

    for i, ((cx, cy), set_def) in enumerate(zip(positions, sets)):
        x = cx - Emu(circle_d // 2)
        y = cy - Emu(circle_d // 2)
        circle = s.shapes.add_shape(MSO_SHAPE.OVAL, x, y, circle_d, circle_d)
        circle.fill.solid()
        circle.fill.fore_color.rgb = fills[i % len(fills)]
        # 50% transparency 透明度 — python-pptx 无内置,用 lxml 写 alpha
        from lxml import etree
        from pptx.oxml.ns import qn
        spPr = circle.fill._xPr.find(qn("a:solidFill"))
        if spPr is not None:
            for child in spPr:
                if "srgbClr" in child.tag:
                    alpha = etree.SubElement(child, qn("a:alpha"))
                    alpha.set("val", "50000")  # 50%
        no_line(circle)

        # label 放在圆外缘(避免被相邻圆遮挡)
        label_w = Inches(2.4)
        label_h = Inches(0.55)
        if n == 2:
            # 水平排:label 在各自圆外侧(左圆 label 在左,右圆 label 在右)
            if i == 0:
                label_x = x - Emu(int(Inches(0.5)))
            else:
                label_x = x + circle_d - Emu(int(label_w - Inches(0.5)))
            label_y = y - Emu(int(Inches(0.6)))
        else:
            # 三角排:顶圆 label 在上,左下 label 在左,右下 label 在右
            if i == 0:
                label_x = cx - Emu(label_w // 2)
                label_y = y - Emu(int(Inches(0.5)))
            elif i == 1:
                label_x = x - Emu(int(Inches(0.4)))
                label_y = y + circle_d - Emu(int(Inches(0.2)))
            else:
                label_x = x + circle_d - Emu(int(label_w - Inches(0.4)))
                label_y = y + circle_d - Emu(int(Inches(0.2)))

        text_in_box(
            s,
            Box(Emu(int(label_x)), Emu(int(label_y)), label_w, label_h),
            set_def.get("label", ""),
            theme=theme, size=16, bold=True, color=T["PRIMARY_DEEP"],
            align=PP_ALIGN.CENTER,
        )

    # 交集 label(中心区)
    if intersection_label:
        text_in_box(
            s,
            Box(cx_center - Emu(int(Inches(1.0))),
                cy_center - Emu(int(Inches(0.25))),
                Inches(2.0), Inches(0.5)),
            intersection_label,
            theme=theme, size=13, bold=True, color=WHITE,
            align=PP_ALIGN.CENTER,
        )
    return s
