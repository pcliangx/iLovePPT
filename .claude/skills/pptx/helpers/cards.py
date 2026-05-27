"""cards layout plugin — N 张并列卡片(2/3/4/6/8 张),自动 2 行布局。

实现移植自 themes/tech_blue.py:make_cards(SSOT)。

每张卡片可选 `icon` 字段:unicode 字符或 ICONS key。
N > 5:自动 2 行布局(N=6→2×3 / N=7-8→2×4 / N=9-10→2×5),避免单行 6+ 列
导致 18pt 中英文混排标题撑爆。
"""
from __future__ import annotations

from types import ModuleType
from typing import Any

from pptx.enum.text import PP_ALIGN
from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Emu, Inches

from . import (
    GRAY_300,
    GRAY_700,
    ICONS,
    WHITE,
    card as draw_card,
    icon as draw_icon,
    is_handout,
)
from ._base import register_layout
from ._internals import add_title, blank_slide, resolve_brand, text_in_box
from layout import Box, columns, content_region, inset, stack


@register_layout("cards")
def make_cards(
    prs: _Pres,
    title: str,
    cards: list[dict[str, Any]],
    *,
    theme: ModuleType | None = None,
) -> Slide:
    T = resolve_brand(theme)
    s = blank_slide(prs)
    add_title(s, title, theme=theme)
    region = content_region()
    n = len(cards)
    if n > 5:
        cols_per_row = (n + 1) // 2  # ceil(n/2)
        row_gap = Inches(0.3)
        card_h = Emu((region.h - row_gap) // 2)
        body_box_h = Inches(1.7) if is_handout() else Inches(1.1)
        row_boxes = stack(region, [card_h, card_h], gap=row_gap,
                          align="middle")
        col_boxes: list[Box] = []
        for row_idx, row_box in enumerate(row_boxes):
            row_cols = columns(row_box, cols_per_row)
            start = row_idx * cols_per_row
            end = min(start + cols_per_row, n)
            col_boxes.extend(row_cols[: end - start])
        cols = col_boxes
    else:
        cols_per_row = n
        card_h = Inches(4.6) if is_handout() else Inches(3.4)
        body_box_h = Inches(3.6) if is_handout() else Inches(2.2)
        row = stack(region, [card_h], align="middle")[0]
        cols = columns(row, n)
    body_size = 12 if is_handout() else 16
    for col, c in zip(cols, cards):
        draw_card(s, col.x, col.y, col.w, col.h, fill=WHITE,
                  border=GRAY_300, accent=T["PRIMARY"])

        # icon(可选)
        icon_char = c.get("icon")
        if icon_char:
            icon_str = ICONS.get(icon_char, icon_char)
            many_cols = cols_per_row >= 4
            if many_cols:
                icon_x = col.x + (col.w - Inches(0.55)) // 2
                draw_icon(s, icon_x, col.y + Inches(0.3), 22, icon_str,
                          color=WHITE, bg=T["PRIMARY"], box_size=Inches(0.55))
                title_box = Box(col.x + Inches(0.2), col.y + Inches(1.0),
                                col.w - Inches(0.4), Inches(0.55))
                text_in_box(s, title_box, c["title"], theme=theme, size=18,
                            bold=True, color=T["PRIMARY_DEEP"],
                            align=PP_ALIGN.CENTER)
                body_y = col.y + Inches(1.7)
                body_box = Box(col.x + Inches(0.25), body_y,
                               col.w - Inches(0.5), body_box_h - Inches(0.7))
                text_in_box(s, body_box, c["body"], theme=theme,
                            size=body_size, color=GRAY_700)
            else:
                draw_icon(s, col.x + Inches(0.3), col.y + Inches(0.3), 22,
                          icon_str, color=WHITE, bg=T["PRIMARY"],
                          box_size=Inches(0.55))
                title_x = col.x + Inches(1.0)
                title_w = col.w - Inches(1.3)
                title_box = Box(title_x, col.y + Inches(0.35), title_w,
                                Inches(0.55))
                text_in_box(s, title_box, c["title"], theme=theme, size=20,
                            bold=True, color=T["PRIMARY_DEEP"])
                body_y = col.y + Inches(1.0)
                body_box = Box(col.x + Inches(0.3), body_y,
                               col.w - Inches(0.5), body_box_h)
                text_in_box(s, body_box, c["body"], theme=theme,
                            size=body_size, color=GRAY_700)
        else:
            inner = inset(col, Inches(0.3), Inches(0.25))
            parts = stack(inner, [Inches(0.6), body_box_h], gap=Inches(0.15),
                          align="top")
            text_in_box(s, parts[0], c["title"], theme=theme, size=20,
                        bold=True, color=T["PRIMARY_DEEP"])
            text_in_box(s, parts[1], c["body"], theme=theme, size=body_size,
                        color=GRAY_700)
    return s
