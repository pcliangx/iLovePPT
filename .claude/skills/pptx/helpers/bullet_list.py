"""bullet_list layout plugin — 要点列表(handout mode 字号降 + 行距加大)。

实现移植自 themes/tech_blue.py:make_bullet_list(SSOT)。

items 接受两种形式:
- str(向后兼容):前缀是默认 "▎" 蓝色 accent 条
- dict {text, icon}:前缀是指定的 icon
混用 OK,逐项判断。
"""
from __future__ import annotations

from types import ModuleType
from typing import Any

from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Emu, Inches, Pt

from . import GRAY_700, ICONS, bullets as draw_bullets, icon as draw_icon, is_handout
from ._base import register_layout
from ._internals import add_title, blank_slide, resolve_brand, text_in_box
from layout import Box, content_region, stack


@register_layout("bullet_list")
def make_bullet_list(
    prs: _Pres,
    title: str,
    items: list[Any],
    *,
    theme: ModuleType | None = None,
) -> Slide:
    T = resolve_brand(theme)
    s = blank_slide(prs)
    add_title(s, title, theme=theme)
    region = content_region()
    bullet_size = 14 if is_handout() else 18
    line_factor = 1.6 if is_handout() else 1.45

    # 条数少(≤ 6)→ 拉大字号并按内容区均分
    if len(items) <= 6:
        bullet_size = max(bullet_size, 22 if is_handout() else 26)
        line_factor = 1.8

    # 全 str 走原 draw_bullets(紧凑);否则 mixed/icon 模式
    if all(isinstance(it, str) for it in items):
        line_h = Emu(int(Pt(bullet_size) * line_factor))
        block = stack(region, [Emu(line_h * len(items))], align="middle")[0]
        draw_bullets(s, block.x, block.y, block.w, block.h, items=items,
                     size=bullet_size, accent_color=T["PRIMARY"],
                     body_color=GRAY_700)
        return s

    # mixed/icon mode:每行 = 左 icon + 右 text
    line_h_emu = Pt(bullet_size * line_factor * 1.5)
    total_h = line_h_emu * len(items)
    block = stack(region, [Emu(int(total_h))], align="middle")[0]
    icon_w = Inches(0.45)
    for i, it in enumerate(items):
        y = block.y + Emu(int(line_h_emu * i))
        if isinstance(it, dict):
            text = it.get("text", "")
            icon_char = it.get("icon", "▎")
        else:
            text = str(it); icon_char = "▎"
        icon_str = ICONS.get(icon_char, icon_char)
        draw_icon(s, block.x, y, bullet_size, icon_str, color=T["PRIMARY"],
                  box_size=icon_w)
        text_box = Box(block.x + icon_w + Inches(0.1), y,
                       block.w - icon_w - Inches(0.1),
                       Emu(int(line_h_emu)))
        text_in_box(s, text_box, text, theme=theme, size=bullet_size,
                    color=GRAY_700)
    return s
