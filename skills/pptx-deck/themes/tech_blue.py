"""iLovePPT pptx-deck — 内置科技蓝主题。

调用 [[pptx]]/helpers.py 作为底层。11 个 layout 函数对应 spec §3.4。
默认字体 Microsoft YaHei（用户决策）。
"""
import sys, warnings
from pathlib import Path
from typing import Any

# Fallback for direct import outside pytest (pytest uses pyproject.toml pythonpath)
_helpers_path = str(Path(__file__).parent.parent.parent / "pptx")
if _helpers_path not in sys.path:
    sys.path.insert(0, _helpers_path)

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Emu, Inches, Length, Pt

import helpers as H


# ===== 字体 / 色板 — SSOT：helpers.py =====
# tech_blue 不重新定义字体或色值,只对 helpers.py 的常量做语义别名。
# 改主题色 / 字体 → 改 helpers.py 顶部的 FONT_* / BRAND_* 常量,全 deck 联动。
FONT_HEADER = H.FONT_CN   # 默认 Microsoft YaHei
FONT_BODY   = H.FONT_CN
FONT_NUM    = H.FONT_NUM  # 默认 Helvetica Neue

PRIMARY_DEEP = H.BRAND_DARK     # #0B2A4A 深海蓝
PRIMARY      = H.BRAND_PRIMARY  # #1E6FE0 科技蓝
PRIMARY_TINT = H.BRAND_TINT     # #E6F0FC 浅蓝底
ACCENT       = H.ACCENT         # #00D1C1 青绿点睛
# 灰阶直接用 helpers.py: H.GRAY_900 / H.GRAY_700 / H.GRAY_500 / H.GRAY_300 / H.GRAY_50 / H.WHITE


def _blank_slide(prs: _Pres) -> Slide:
    return prs.slides.add_slide(prs.slide_layouts[6])


def _add_title(
    slide: Slide,
    text: str,
    *,
    y: Length = Inches(0.6),
    size: int = 28,
    color: RGBColor = PRIMARY_DEEP,
) -> Any:
    box = slide.shapes.add_textbox(Inches(0.55), y, Inches(12.2), Inches(0.8))
    tf = box.text_frame
    H.fix_textbox_margins(tf)
    r = tf.paragraphs[0].add_run()
    r.text = text
    H.set_font(r, name=FONT_HEADER, size=size, bold=True, color=color)
    return box


def make_cover(prs: _Pres, title: str, subtitle: str) -> Slide:
    s = _blank_slide(prs)
    H.rect(s, 0, 0, H.SLIDE_W, H.SLIDE_H, PRIMARY_DEEP)
    # 大主标题
    box = s.shapes.add_textbox(Inches(0.55), Inches(2.8), Inches(12), Inches(1.8))
    H.fix_textbox_margins(box.text_frame)
    r = box.text_frame.paragraphs[0].add_run()
    r.text = title
    H.set_font(r, name=FONT_HEADER, size=48, bold=True, color=H.WHITE)
    # 副标
    box2 = s.shapes.add_textbox(Inches(0.55), Inches(4.6), Inches(12), Inches(0.8))
    H.fix_textbox_margins(box2.text_frame)
    r2 = box2.text_frame.paragraphs[0].add_run()
    r2.text = subtitle
    H.set_font(r2, name=FONT_HEADER, size=20, color=PRIMARY_TINT)
    return s


def make_toc(prs: _Pres, sections: list[str]) -> Slide:
    """目录页：标题"目录" + N 行章节,每行编号 + 标题。"""
    s = _blank_slide(prs)
    _add_title(s, "目录", size=40, y=Inches(0.6), color=PRIMARY_DEEP)
    for i, sec in enumerate(sections):
        y = Inches(1.8 + i * 0.7)
        n_box = s.shapes.add_textbox(Inches(1.5), y, Inches(0.7), Inches(0.6))
        H.fix_textbox_margins(n_box.text_frame)
        r = n_box.text_frame.paragraphs[0].add_run()
        r.text = f"{i+1:02d}"
        H.set_font(r, name=FONT_NUM, size=26, bold=True, color=PRIMARY)
        t_box = s.shapes.add_textbox(Inches(2.4), y, Inches(10), Inches(0.6))
        H.fix_textbox_margins(t_box.text_frame)
        r2 = t_box.text_frame.paragraphs[0].add_run()
        r2.text = sec
        H.set_font(r2, name=FONT_HEADER, size=20, color=H.GRAY_900)
    return s


def make_section_divider(prs: _Pres, num: int | str, title: str) -> Slide:
    s = _blank_slide(prs)
    H.section_header(s, title, num, PRIMARY_DEEP)
    return s


def make_single_focus(
    prs: _Pres,
    *,
    big_text: str = "",
    big_number: str = "",
    explanation: str = "",
) -> Slide:
    s = _blank_slide(prs)
    # 大数字
    box = s.shapes.add_textbox(Inches(0.55), Inches(2.0), Inches(12), Inches(2.5))
    H.fix_textbox_margins(box.text_frame)
    p = box.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = big_number
    H.set_font(r, name=FONT_NUM, size=120, bold=True, color=PRIMARY)
    # 大文字
    box2 = s.shapes.add_textbox(Inches(0.55), Inches(4.5), Inches(12), Inches(1.0))
    H.fix_textbox_margins(box2.text_frame)
    p2 = box2.text_frame.paragraphs[0]
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    r2.text = big_text
    H.set_font(r2, name=FONT_HEADER, size=32, bold=True, color=PRIMARY_DEEP)
    # 解释
    box3 = s.shapes.add_textbox(Inches(0.55), Inches(5.6), Inches(12), Inches(0.6))
    H.fix_textbox_margins(box3.text_frame)
    p3 = box3.text_frame.paragraphs[0]
    p3.alignment = PP_ALIGN.CENTER
    r3 = p3.add_run()
    r3.text = explanation
    H.set_font(r3, name=FONT_HEADER, size=14, color=H.GRAY_500)
    return s


def make_two_col_compare(
    prs: _Pres,
    left_title: str,
    left_body: str,
    right_title: str,
    right_body: str,
) -> Slide:
    s = _blank_slide(prs)
    _add_title(s, "对比", size=28)
    # 左
    H.card(s, Inches(0.55), Inches(1.8), Inches(6.0), Inches(5.2),
           fill=PRIMARY_TINT, border=H.GRAY_300, accent=PRIMARY)
    lt = s.shapes.add_textbox(Inches(0.85), Inches(2.0), Inches(5.4), Inches(0.6))
    H.fix_textbox_margins(lt.text_frame)
    r = lt.text_frame.paragraphs[0].add_run()
    r.text = left_title
    H.set_font(r, name=FONT_HEADER, size=20, bold=True, color=PRIMARY_DEEP)
    lb = s.shapes.add_textbox(Inches(0.85), Inches(2.8), Inches(5.4), Inches(4.0))
    H.fix_textbox_margins(lb.text_frame)
    r2 = lb.text_frame.paragraphs[0].add_run()
    r2.text = left_body
    H.set_font(r2, name=FONT_BODY, size=14, color=H.GRAY_900)
    # 右
    H.card(s, Inches(6.78), Inches(1.8), Inches(6.0), Inches(5.2),
           fill=H.WHITE, border=H.GRAY_300, accent=ACCENT)
    rt = s.shapes.add_textbox(Inches(7.08), Inches(2.0), Inches(5.4), Inches(0.6))
    H.fix_textbox_margins(rt.text_frame)
    r3 = rt.text_frame.paragraphs[0].add_run()
    r3.text = right_title
    H.set_font(r3, name=FONT_HEADER, size=20, bold=True, color=PRIMARY_DEEP)
    rb = s.shapes.add_textbox(Inches(7.08), Inches(2.8), Inches(5.4), Inches(4.0))
    H.fix_textbox_margins(rb.text_frame)
    r4 = rb.text_frame.paragraphs[0].add_run()
    r4.text = right_body
    H.set_font(r4, name=FONT_BODY, size=14, color=H.GRAY_900)
    return s


def make_three_col_cards(
    prs: _Pres,
    cards: list[dict[str, str]],
    title: str = "三栏",
) -> Slide:
    if len(cards) > 3:
        warnings.warn(f"make_three_col_cards 收到 {len(cards)} 张卡片,只显前 3 张", stacklevel=2)
    s = _blank_slide(prs)
    _add_title(s, title, size=28)
    for i, c in enumerate(cards[:3]):
        x = Inches(0.55 + i * 4.15)  # card_w=3.85 + gap=0.30 = 4.15 列间距
        H.card(s, x, Inches(1.8), Inches(3.85), Inches(5.0),
               fill=H.WHITE, border=H.GRAY_300, accent=PRIMARY if i % 2 == 0 else ACCENT)
        t = s.shapes.add_textbox(x + Inches(0.3), Inches(2.0), Inches(3.4), Inches(0.6))
        H.fix_textbox_margins(t.text_frame)
        r = t.text_frame.paragraphs[0].add_run()
        r.text = c["title"]
        H.set_font(r, name=FONT_HEADER, size=18, bold=True, color=PRIMARY_DEEP)
        b = s.shapes.add_textbox(x + Inches(0.3), Inches(2.8), Inches(3.4), Inches(3.8))
        H.fix_textbox_margins(b.text_frame)
        r2 = b.text_frame.paragraphs[0].add_run()
        r2.text = c["body"]
        H.set_font(r2, name=FONT_BODY, size=13, color=H.GRAY_900)
    return s


def make_bullet_list(prs: _Pres, title: str, items: list[str]) -> Slide:
    s = _blank_slide(prs)
    _add_title(s, title, size=28)
    H.bullets(s, Inches(0.55), Inches(1.8), Inches(12.2), Inches(5.2),
              items=items, size=16, accent_color=PRIMARY, body_color=H.GRAY_900)
    return s


def make_table(
    prs: _Pres,
    title: str,
    headers: list[str],
    rows: list[list[str]],
) -> Slide:
    s = _blank_slide(prs)
    _add_title(s, title, size=28)
    H.table_modern(s, Inches(0.55), Inches(1.8), Inches(12.2), Inches(4.0),
                   headers=headers, rows=rows,
                   header_fill=PRIMARY_DEEP, header_color=H.WHITE,
                   zebra=PRIMARY_TINT, font_size=12)
    return s


def make_pic_text(
    prs: _Pres,
    title: str,
    image_path: str,
    points: list[dict[str, str]],
) -> Slide:
    if len(points) > 4:
        warnings.warn(f"make_pic_text 收到 {len(points)} 个要点,只显前 4 项", stacklevel=2)
    s = _blank_slide(prs)
    _add_title(s, title, size=28)
    H.embed_picture(s, image_path, Inches(0.55), Inches(1.9), height=Inches(5.0))
    # 右 4 卡片（截取前 4 项）
    for i, p in enumerate(points[:4]):
        y = Inches(2.0 + i * 1.15)
        H.card(s, Inches(7.0), y, Inches(5.78), Inches(0.95),
               fill=H.WHITE, border=H.GRAY_300, accent=PRIMARY)
        t = s.shapes.add_textbox(Inches(7.3), y + Inches(0.1), Inches(5.4), Inches(0.4))
        H.fix_textbox_margins(t.text_frame)
        r = t.text_frame.paragraphs[0].add_run()
        r.text = p["title"]
        H.set_font(r, name=FONT_HEADER, size=14, bold=True, color=PRIMARY_DEEP)
        b = s.shapes.add_textbox(Inches(7.3), y + Inches(0.45), Inches(5.4), Inches(0.45))
        H.fix_textbox_margins(b.text_frame)
        r2 = b.text_frame.paragraphs[0].add_run()
        r2.text = p["body"]
        H.set_font(r2, name=FONT_BODY, size=11, color=H.GRAY_700)
    return s


def make_summary(
    prs: _Pres,
    conclusions: list[str],
    title: str = "核心结论",
) -> Slide:
    if len(conclusions) > 5:
        warnings.warn(f"make_summary 收到 {len(conclusions)} 条结论,只显前 5 条", stacklevel=2)
    s = _blank_slide(prs)
    _add_title(s, title, size=32, color=PRIMARY_DEEP)
    for i, c in enumerate(conclusions[:5]):
        y = Inches(1.9 + i * 1.0)
        # 序号大色块
        H.rect(s, Inches(0.55), y, Inches(0.9), Inches(0.85), PRIMARY)
        n_box = s.shapes.add_textbox(Inches(0.55), y, Inches(0.9), Inches(0.85))
        H.fix_textbox_margins(n_box.text_frame)
        p = n_box.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = str(i + 1)
        H.set_font(r, name=FONT_NUM, size=32, bold=True, color=H.WHITE)
        # 结论文字
        t = s.shapes.add_textbox(Inches(1.7), y + Inches(0.18), Inches(11), Inches(0.6))
        H.fix_textbox_margins(t.text_frame)
        r2 = t.text_frame.paragraphs[0].add_run()
        r2.text = c
        H.set_font(r2, name=FONT_HEADER, size=18, color=H.GRAY_900)
    return s


def make_closing(prs: _Pres, subtitle: str = "谢谢") -> Slide:
    """封底页:大字 '谢谢' + 小字 subtitle (默认也是 '谢谢',可改为联系方式等)."""
    s = _blank_slide(prs)
    H.rect(s, 0, 0, H.SLIDE_W, H.SLIDE_H, PRIMARY_DEEP)
    box = s.shapes.add_textbox(Inches(0.55), Inches(3.0), Inches(12), Inches(1.5))
    H.fix_textbox_margins(box.text_frame)
    p = box.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = "谢谢"
    H.set_font(r, name=FONT_HEADER, size=64, bold=True, color=H.WHITE)
    box2 = s.shapes.add_textbox(Inches(0.55), Inches(4.6), Inches(12), Inches(0.6))
    H.fix_textbox_margins(box2.text_frame)
    p2 = box2.text_frame.paragraphs[0]
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    r2.text = subtitle
    H.set_font(r2, name=FONT_BODY, size=16, color=PRIMARY_TINT)
    return s
