"""data layout plugin — 数据展示(默认 modern 表格;接受 chart_path 时切到图表 + 标题)。

实现思路:tech_blue 用 make_table(纯表)+ make_pic_text(图表用图片承载),
这里融合成 data layout:
- 传 `chart_path` → 图表大图为主,右侧可选 highlights bullets
- 否则按 headers + rows 走 make_table 路径
"""
from __future__ import annotations

from types import ModuleType

from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Inches

from . import (
    GRAY_300,
    GRAY_700,
    WHITE,
    bullets as draw_bullets,
    embed_picture,
    is_handout,
    table_modern,
)
from ._base import register_layout
from ._internals import add_title, blank_slide, resolve_brand, text_in_box
from layout import Box, content_region, rows, split


@register_layout("data")
def make_data(
    prs: _Pres,
    title: str,
    *,
    theme: ModuleType | None = None,
    headers: list[str] | None = None,
    table_rows: list[list[str]] | None = None,
    chart_path: str | None = None,
    highlights: list[str] | None = None,
) -> Slide:
    """数据 slide。两种主形态:

    - 表格模式:`headers` + `table_rows` → 全宽 modern 表格(zebra + 主色 header)
    - 图表模式:`chart_path` → 大图为主,可选 `highlights` 在右侧显要点
    """
    T = resolve_brand(theme)
    s = blank_slide(prs)
    add_title(s, title, theme=theme)
    region = content_region()

    if chart_path:
        # 图表 + 可选 highlights
        if highlights:
            left, right = split(region, 0.65)
            embed_picture(s, chart_path, left.x, left.y, box_w=left.w,
                          box_h=left.h)
            draw_bullets(s, right.x, right.y, right.w, right.h,
                         items=highlights, size=14,
                         accent_color=T["PRIMARY"], body_color=GRAY_700)
        else:
            embed_picture(s, chart_path, region.x, region.y,
                          box_w=region.w, box_h=region.h)
        return s

    # 表格模式(默认)
    if not headers or table_rows is None:
        raise ValueError("data layout 需要 chart_path 或 (headers + table_rows)")
    table_modern(s, region.x, region.y, region.w, region.h,
                 headers=headers, rows=table_rows,
                 header_fill=T["PRIMARY_DEEP"], header_color=WHITE,
                 zebra=T["PRIMARY_TINT"], font_size=14)
    return s
