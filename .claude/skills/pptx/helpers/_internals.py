"""Layout plugin 共享内部 helper(theme-agnostic 标准实现)。

提取自 themes/tech_blue.py 的私有 helper(`_blank_slide` / `_add_title` / `_text`),
让 layout plugin 不依赖具体 theme module 也能跑。

设计原则:
- 接受 theme module 可选(`theme=None` 走 helpers 默认 token)
- 不重新定义任何色彩 / 字体 token,直接用 helpers/__init__.py 已定义的 BRAND_*/FONT_*
- 保留 theme override 路径:plugin 拿到 theme 后,优先用 theme.PRIMARY / theme.FONT_HEADER 等
"""
from __future__ import annotations

from types import ModuleType
from typing import Any

from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Inches, Length

# 直接从 helpers package(__init__.py)取共享原语 + token。
# helpers/<layout>.py 用 `from ._internals import ...` 拿到这里组合好的工具。
from . import (
    ACCENT,
    BRAND_DARK,
    BRAND_PRIMARY,
    BRAND_TINT,
    FONT_CN,
    FONT_NUM,
    GRAY_300,
    GRAY_500,
    GRAY_700,
    GRAY_900,
    SLIDE_W,
    WHITE,
    fix_textbox_margins,
    set_font,
)


def get_token(theme: ModuleType | None, name: str, fallback: Any) -> Any:
    """从 theme module 取 token(若存在),否则用 fallback。

    用例:
        primary = get_token(theme, "PRIMARY", BRAND_PRIMARY)
        font_header = get_token(theme, "FONT_HEADER", FONT_CN)
    """
    if theme is None:
        return fallback
    return getattr(theme, name, fallback)


def blank_slide(prs: _Pres) -> Slide:
    """添加 blank slide(跨模板 robust:按名匹配 → idx 6 → last layout)。

    python-pptx 默认 Presentation() 7 layouts(idx 6 = blank),用户加载的模板
    可能少于 7。提取自 themes/tech_blue.py:_blank_slide。
    """
    blank_names = ("Blank", "空白", "blank")
    for sl in prs.slide_layouts:
        if (sl.name or "").strip() in blank_names:
            return prs.slides.add_slide(sl)
    n = len(prs.slide_layouts)
    idx = 6 if n > 6 else n - 1
    return prs.slides.add_slide(prs.slide_layouts[idx])


def add_title(
    slide: Slide,
    text: str,
    *,
    theme: ModuleType | None = None,
    y: Length = Inches(0.6),
    size: int = 32,
    color: RGBColor | None = None,
) -> Any:
    """页面标题 — 32pt 是行业最低实践(BCG action title 36-44pt)。"""
    font = get_token(theme, "FONT_HEADER", FONT_CN)
    if color is None:
        color = get_token(theme, "PRIMARY_DEEP", BRAND_DARK)
    box = slide.shapes.add_textbox(Inches(0.55), y, Inches(12.2), Inches(0.9))
    tf = box.text_frame
    fix_textbox_margins(tf)
    r = tf.paragraphs[0].add_run()
    r.text = text
    set_font(r, name=font, size=size, bold=True, color=color)
    return box


def text_in_box(
    slide: Slide,
    box: Any,
    text: str,
    *,
    theme: ModuleType | None = None,
    size: int,
    bold: bool = False,
    color: RGBColor | None = None,
    align=PP_ALIGN.LEFT,
    font: str | None = None,
    valign: str = "top",
) -> None:
    """在一个 layout.Box 内放一段文字(textbox + margin 归零 + set_font)。

    valign: "top" | "middle" | "bottom" — textbox 内文字垂直对齐。
        默认 top 保持向后兼容;hero 大字号(big_number/big_text)用 middle 让
        字在槽内居中,避免 ascent 撑爆槽位下沉到相邻区域。
    """
    if color is None:
        color = GRAY_900
    if font is None:
        font = get_token(theme, "FONT_HEADER", FONT_CN)
    tb = slide.shapes.add_textbox(box.x, box.y, box.w, box.h)
    fix_textbox_margins(tb.text_frame)
    tb.text_frame.word_wrap = True
    if valign == "middle":
        tb.text_frame.vertical_anchor = 3  # MSO_ANCHOR.MIDDLE
    elif valign == "bottom":
        tb.text_frame.vertical_anchor = 4  # MSO_ANCHOR.BOTTOM
    p = tb.text_frame.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    set_font(r, name=font, size=size, bold=bold, color=color)


# Token resolver helper:plugin 一次性取常用 4 个 brand token
def resolve_brand(theme: ModuleType | None) -> dict:
    """一次性取 PRIMARY / PRIMARY_DEEP / PRIMARY_TINT / ACCENT。

    用例:
        T = resolve_brand(theme)
        H.rect(s, x, y, w, h, T["PRIMARY_DEEP"])
    """
    return {
        "PRIMARY":      get_token(theme, "PRIMARY",      BRAND_PRIMARY),
        "PRIMARY_DEEP": get_token(theme, "PRIMARY_DEEP", BRAND_DARK),
        "PRIMARY_TINT": get_token(theme, "PRIMARY_TINT", BRAND_TINT),
        "ACCENT":       get_token(theme, "ACCENT",       ACCENT),
        "FONT_HEADER":  get_token(theme, "FONT_HEADER",  FONT_CN),
        "FONT_BODY":    get_token(theme, "FONT_BODY",    FONT_CN),
        "FONT_NUM":     get_token(theme, "FONT_NUM",     FONT_NUM),
    }
