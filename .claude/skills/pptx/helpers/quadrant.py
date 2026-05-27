"""quadrant layout plugin — BCG 2×2 经典矩阵(横纵轴 + 4 象限,可高亮主推象限)。

实现移植自 themes/tech_blue.py:make_matrix_2x2(SSOT,改名 quadrant 与 enum 对齐)。

x_axis / y_axis = {low: "...", high: "..."}
quadrants = [{pos: "tl"|"tr"|"bl"|"br", title, body, highlight?}] × 4
"""
from __future__ import annotations

from types import ModuleType
from typing import Any

from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Inches, Pt

from . import (
    GRAY_300,
    GRAY_700,
    GRAY_900,
    WHITE,
    is_handout,
)
from ._base import register_layout
from ._internals import add_title, blank_slide, resolve_brand, text_in_box
from layout import Box


@register_layout("quadrant")
def make_quadrant(
    prs: _Pres,
    title: str,
    x_axis: dict[str, str],
    y_axis: dict[str, str],
    quadrants: list[dict[str, Any]],
    *,
    theme: ModuleType | None = None,
) -> Slide:
    T = resolve_brand(theme)
    s = blank_slide(prs)
    add_title(s, title, theme=theme)

    matrix_x = Inches(2.4)
    matrix_y = Inches(1.7)
    matrix_w = Inches(10.0)
    matrix_h = Inches(4.7)
    cell_w = matrix_w // 2
    cell_h = matrix_h // 2

    body_size = 14 if is_handout() else 12

    positions = {
        "tl": (matrix_x, matrix_y),
        "tr": (matrix_x + cell_w, matrix_y),
        "bl": (matrix_x, matrix_y + cell_h),
        "br": (matrix_x + cell_w, matrix_y + cell_h),
    }
    for q in quadrants:
        pos = q.get("pos")
        if pos not in positions:
            raise ValueError(f"quadrant.pos 必须是 tl/tr/bl/br,得到 {pos!r}")
        qx, qy = positions[pos]
        highlight = bool(q.get("highlight", False))
        fill = T["PRIMARY_TINT"] if highlight else WHITE
        rect = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, qx, qy, cell_w, cell_h)
        rect.fill.solid(); rect.fill.fore_color.rgb = fill
        rect.line.color.rgb = T["PRIMARY"] if highlight else GRAY_300
        rect.line.width = Pt(1.5) if highlight else Pt(0.75)
        title_box = Box(qx + Inches(0.25), qy + Inches(0.2),
                        cell_w - Inches(0.5), Inches(0.5))
        text_in_box(s, title_box, q["title"], theme=theme, size=18,
                    bold=True,
                    color=T["PRIMARY_DEEP"] if highlight else GRAY_900)
        body_box = Box(qx + Inches(0.25), qy + Inches(0.85),
                       cell_w - Inches(0.5), cell_h - Inches(1.0))
        text_in_box(s, body_box, q.get("body", ""), theme=theme,
                    size=body_size,
                    color=T["PRIMARY_DEEP"] if highlight else GRAY_700)

    # 横轴标签
    axis_y = matrix_y + matrix_h + Inches(0.1)
    x_low = Box(matrix_x, axis_y, cell_w, Inches(0.35))
    x_high = Box(matrix_x + cell_w, axis_y, cell_w, Inches(0.35))
    text_in_box(s, x_low, x_axis.get("low", ""), theme=theme, size=12,
                bold=True, color=GRAY_700, align=PP_ALIGN.CENTER)
    text_in_box(s, x_high, x_axis.get("high", ""), theme=theme, size=12,
                bold=True, color=GRAY_700, align=PP_ALIGN.CENTER)

    # 纵轴标签
    y_axis_x = Inches(0.55)
    y_axis_w = matrix_x - y_axis_x - Inches(0.15)
    y_high = Box(y_axis_x, matrix_y, y_axis_w, Inches(0.4))
    y_low = Box(y_axis_x, matrix_y + matrix_h - Inches(0.4), y_axis_w,
                Inches(0.4))
    text_in_box(s, y_high, "↑ " + y_axis.get("high", ""), theme=theme,
                size=12, bold=True, color=GRAY_700)
    text_in_box(s, y_low, "↓ " + y_axis.get("low", ""), theme=theme,
                size=12, bold=True, color=GRAY_700)
    return s
