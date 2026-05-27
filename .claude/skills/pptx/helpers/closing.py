"""closing layout plugin — 封底页(简单"谢谢" 或 结构化 Next Steps)。

实现移植自 themes/tech_blue.py:make_closing(SSOT)。

- 简单模式(next_steps=None):大字"谢谢" + 可选 subtitle 联系方式。
- 结构化模式(next_steps=[{action, owner?, due?}, ...]):
  标题"Next Steps" + 编号 action 列表 + 底部 subtitle。
"""
from __future__ import annotations

from types import ModuleType

from pptx.enum.text import PP_ALIGN
from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Emu, Inches

from . import (
    SLIDE_H,
    SLIDE_W,
    WHITE,
    fix_textbox_margins,
    rect,
    set_font,
)
from ._base import register_layout
from ._internals import blank_slide, resolve_brand, text_in_box
from layout import Box, full_region, stack


@register_layout("closing")
def make_closing(
    prs: _Pres,
    *,
    theme: ModuleType | None = None,
    subtitle: str = "",
    next_steps: list[dict[str, str]] | None = None,
) -> Slide:
    T = resolve_brand(theme)
    s = blank_slide(prs)
    rect(s, 0, 0, SLIDE_W, SLIDE_H, T["PRIMARY_DEEP"])

    if next_steps:
        # 结构化 closing
        title_box = Box(x=Inches(0.55), y=Inches(0.7),
                        w=Emu(SLIDE_W - Inches(1.1)), h=Inches(0.8))
        text_in_box(s, title_box, "Next Steps", theme=theme, size=36,
                    bold=True, color=WHITE)

        list_y = Inches(2.0)
        line_h = Inches(0.7)
        for i, step in enumerate(next_steps):
            row_y = Emu(list_y + i * line_h)
            num_box = s.shapes.add_textbox(Inches(0.55), row_y,
                                           Inches(0.6), line_h)
            fix_textbox_margins(num_box.text_frame)
            p = num_box.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            r = p.add_run()
            r.text = f"{i + 1}."
            set_font(r, name=T["FONT_NUM"], size=22, bold=True,
                     color=T["ACCENT"])
            action = step.get("action", "")
            owner = step.get("owner", "")
            due = step.get("due", "")
            tail = " · ".join([v for v in (owner, due) if v])
            text = f"{action}    [{tail}]" if tail else action
            text_box = s.shapes.add_textbox(Inches(1.2), row_y,
                                            Emu(SLIDE_W - Inches(1.75)),
                                            line_h)
            fix_textbox_margins(text_box.text_frame)
            p2 = text_box.text_frame.paragraphs[0]
            p2.alignment = PP_ALIGN.LEFT
            r2 = p2.add_run()
            r2.text = text
            set_font(r2, name=T["FONT_BODY"], size=18, color=WHITE)

        if subtitle:
            sub_box = s.shapes.add_textbox(
                Inches(0.55), Inches(SLIDE_H.inches - 0.7),
                Emu(SLIDE_W - Inches(1.1)), Inches(0.4))
            fix_textbox_margins(sub_box.text_frame)
            p3 = sub_box.text_frame.paragraphs[0]
            p3.alignment = PP_ALIGN.LEFT
            r3 = p3.add_run()
            r3.text = subtitle
            set_font(r3, name=T["FONT_BODY"], size=14,
                     color=T["PRIMARY_TINT"])
    else:
        # 简单模式:谢谢 + subtitle
        region = full_region()
        blocks = stack(region, [Inches(1.5), Inches(0.6)], gap=Inches(0.3),
                       align="middle")
        text_in_box(s, blocks[0], "谢谢", theme=theme, size=72, bold=True,
                    color=WHITE, align=PP_ALIGN.CENTER)
        text_in_box(s, blocks[1], subtitle, theme=theme, size=18,
                    color=T["PRIMARY_TINT"], font=T["FONT_BODY"],
                    align=PP_ALIGN.CENTER)

    return s
