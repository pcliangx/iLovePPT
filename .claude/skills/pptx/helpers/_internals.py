"""Layout plugin 共享内部 helper(theme-agnostic 标准实现)。

提取自 themes/tech_blue.py 的私有 helper(`_blank_slide` / `_add_title` / `_text`),
让 layout plugin 不依赖具体 theme module 也能跑。

设计原则:
- 接受 theme module 可选(`theme=None` 走 helpers 默认 token)
- 不重新定义任何色彩 / 字体 token,直接用 helpers/__init__.py 已定义的 BRAND_*/FONT_*
- 保留 theme override 路径:plugin 拿到 theme 后,优先用 theme.PRIMARY / theme.FONT_HEADER 等
"""
from __future__ import annotations

import re
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
    FONT_LATIN,
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


# ============================================================================
# 中英文混排(mixed_lang_text)— P3-10
# ============================================================================
#
# 痛点:
# - 默认 set_font 把整 run 字体设为 FONT_CN(YaHei),英文片段被中文字体撑宽 /
#   字重不齐。或者整 run 设 FONT_EN,中文片段在 Windows fallback 成宋体。
# - lxml <a:ea> + <a:latin> 写在同一 run 上理论上能让 PowerPoint 按字符类型选,
#   但跨平台(LibreOffice / WPS)实现不一致 — 最稳的做法是按语言切 run。
#
# 方案:
# - tokenize_mixed:输入 str → 按 char 切 [{text, lang}] runs(zh/en/num)
# - mixed_lang_text:输入 paragraph + runs → clear + 每 run 独立 set_font
# - 中文 run:set_font(name=FONT_CN) — ea/cs/latin 全 YaHei
# - 英文 run:set_font(name=FONT_LATIN=Arial) — latin Arial,ea 仍 YaHei
#   (混排里中文 EA 不动,保证如有遗漏的中文 char 也走 YaHei)
# - 数字 run:set_font(name=FONT_NUM)

# CJK Unified Ideographs:U+4E00-U+9FFF;CJK 标点 / 全角符号也算 zh
_CJK_RE = re.compile(r"[一-鿿　-〿＀-￯]")
# 纯 ASCII alpha
_ASCII_ALPHA_RE = re.compile(r"[A-Za-z]")
# 数字 / 标点 / 空白
_NUM_PUNCT_RE = re.compile(r"^[\d\s%\.,;:!?'\"\-+*/=()\[\]{}<>@#$&_]+$")


def _detect_lang(text: str) -> str:
    """启发式判断段语言:zh / en / num。

    规则:
    - 含 CJK char → "zh"(中文 fallback 保守,混排里只要有一个中文就当中文段)
    - 全 ASCII alpha(可带空格 / 标点)→ "en"
    - 全数字 / 标点 / 空白 → "num"
    - 其他 → "zh"(保守 fallback)
    """
    if not text:
        return "zh"
    if _CJK_RE.search(text):
        return "zh"
    # 全数字 + 标点 + 空白 → num
    if _NUM_PUNCT_RE.match(text):
        return "num"
    # 含 alpha → en(可能混了数字 / 标点,但有 alpha 就当 en)
    if _ASCII_ALPHA_RE.search(text):
        return "en"
    # 兜底 zh
    return "zh"


def tokenize_mixed(text: str) -> list[dict]:
    """按 char 类型切分混排字符串 → [{text, lang}] runs。

    规则:
    - 相邻同类 char 合并成一个 run
    - 数字 / 标点 / 空白默认归到相邻 run(优先英 → 中 → 兜底 num):
      `"100%"` 自成 num run · `"是 100% 开源"` → zh + num + zh 三段
      (空白属于"过渡"会被并入前一 run)
    - 中文标点(逗号句号等)归 zh
    - char 类别:zh(CJK)/ en(ASCII alpha)/ num(数字 + ASCII 标点 + 空白)

    例:
        "iLovePPT 是 100% 开源工具" →
          [{text: "iLovePPT", lang: "en"},
           {text: " ", lang: "en"},          # 空白并入前 en run(简化:见下面 merge)
           {text: "是 ", lang: "zh"},
           {text: "100%", lang: "num"},
           {text: " 开源工具", lang: "zh"}]
    """
    if not text:
        return []

    # Step 1:按 char 标语言类(粗粒度,空白单独标 "ws")
    def _char_lang(ch: str) -> str:
        if _CJK_RE.match(ch):
            return "zh"
        if _ASCII_ALPHA_RE.match(ch):
            return "en"
        if ch.isspace():
            return "ws"
        if ch.isdigit():
            return "num"
        # ASCII 标点 / 符号:归 "punct"(后续合并到相邻 run)
        if ord(ch) < 128:
            return "punct"
        # 兜底:非 ASCII 非 CJK → zh(全角符号等)
        return "zh"

    raw = [(ch, _char_lang(ch)) for ch in text]

    # Step 2:合并 ws/punct 到相邻 run(优先靠 num,其次 en,其次 zh)
    # 策略:扫一遍,把每个 ws/punct 标成 prev/next 的语言(若 prev/next 是 zh/en/num)
    # 边界 case:开头或结尾的 ws/punct → 用 next/prev 即可
    n = len(raw)
    resolved: list[tuple[str, str]] = []  # (char, final_lang)
    for i, (ch, lang) in enumerate(raw):
        if lang in ("zh", "en", "num"):
            resolved.append((ch, lang))
            continue
        # ws/punct:找前后非 ws/punct lang
        prev_lang = None
        for j in range(i - 1, -1, -1):
            if raw[j][1] in ("zh", "en", "num"):
                prev_lang = raw[j][1]
                break
        next_lang = None
        for j in range(i + 1, n):
            if raw[j][1] in ("zh", "en", "num"):
                next_lang = raw[j][1]
                break
        # 数字(ASCII 标点 / 空白)归并优先级:
        # - 数字相关上下文(num)优先:`100%` / `1, 000`
        # - 否则继承 prev(保持上下文连续)
        # - 都没有 → 默认 zh(整段没字母没汉字,纯标点 / 空白:当 zh 处理)
        if prev_lang == "num" and next_lang == "num":
            final = "num"
        elif prev_lang is not None:
            final = prev_lang
        elif next_lang is not None:
            final = next_lang
        else:
            final = "zh"
        resolved.append((ch, final))

    # Step 3:相邻同 lang char 合并成 run
    out: list[dict] = []
    cur_lang = resolved[0][1]
    cur_text = resolved[0][0]
    for ch, lang in resolved[1:]:
        if lang == cur_lang:
            cur_text += ch
        else:
            out.append({"text": cur_text, "lang": cur_lang})
            cur_lang = lang
            cur_text = ch
    out.append({"text": cur_text, "lang": cur_lang})
    return out


def mixed_lang_text(
    p: Any,
    runs: list[dict],
    *,
    default_font_size: int = 18,
    bold: bool = False,
    color: RGBColor | None = None,
) -> None:
    """中英文分段写 paragraph · 每段独立设字体确保 fallback 一致。

    runs schema:
        [{"text": "中文片段", "lang": "zh"},
         {"text": "English",   "lang": "en"},
         {"text": "iLovePPT",  "lang": "auto"}]   # auto = detect by char

    每个 run 写完后:
    - lang="zh" → set_font(name=FONT_CN)        # ea+cs+latin 全 YaHei
    - lang="en" → set_font(name=FONT_LATIN)     # latin Arial · ea 仍 YaHei
    - lang="num" → set_font(name=FONT_NUM)
    - lang="auto" → 调 _detect_lang(text) 后按以上分支

    用例:
        from helpers._internals import mixed_lang_text, tokenize_mixed
        runs = tokenize_mixed("iLovePPT 是 100% 开源")
        mixed_lang_text(paragraph, runs, default_font_size=20, bold=True,
                        color=BRAND_DARK)
    """
    if color is None:
        color = GRAY_900
    p.clear()
    for seg in runs:
        text = seg.get("text", "")
        lang = seg.get("lang", "auto")
        if lang == "auto":
            lang = _detect_lang(text)
        run = p.add_run()
        run.text = text
        if lang == "zh":
            set_font(run, name=FONT_CN, size=default_font_size, bold=bold,
                     color=color)
        elif lang == "en":
            set_font(run, name=FONT_LATIN, size=default_font_size, bold=bold,
                     color=color)
        elif lang == "num":
            set_font(run, name=FONT_NUM, size=default_font_size, bold=bold,
                     color=color)
        else:
            raise ValueError(
                f"unknown lang: {lang!r}(允许:zh / en / num / auto)"
            )
