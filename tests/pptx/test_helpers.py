# tests/pptx/test_helpers.py
"""helpers.py light test：验证 shape 数、字体名、color、文字内容。
真正的"长得对不对"由 examples/minimal_deck.py 视觉 smoke test 验证。"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../skills/pptx"))

from pptx import Presentation
from pptx.util import Inches
import helpers as H


def _new_prs():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    return prs


def test_set_font_writes_ea_typeface():
    prs = _new_prs()
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    tb = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1))
    run = tb.text_frame.paragraphs[0].add_run()
    run.text = "中文测试"
    H.set_font(run, name="Microsoft YaHei", size=14)
    # 检查 <a:ea> 写入
    from pptx.oxml.ns import qn
    rPr = run._r.find(qn("a:rPr"))
    ea = rPr.find(qn("a:ea"))
    assert ea is not None, "set_font 必须写 <a:ea>"
    assert ea.get("typeface") == "Microsoft YaHei"


def test_card_creates_rounded_rect():
    prs = _new_prs()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    n_before = len(slide.shapes)
    H.card(slide, Inches(1), Inches(1), Inches(4), Inches(1.5),
           fill=H.WHITE, border=H.GRAY_300)
    assert len(slide.shapes) == n_before + 1


def test_card_with_accent_creates_two_shapes():
    prs = _new_prs()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    n_before = len(slide.shapes)
    H.card(slide, Inches(1), Inches(1), Inches(4), Inches(1.5),
           fill=H.WHITE, border=H.GRAY_300, accent=H.BRAND_PRIMARY)
    assert len(slide.shapes) == n_before + 2  # 圆角矩 + 左色条


def test_default_brand_palette_defined():
    # 验证 10 色变量都存在
    for c in ["BRAND_PRIMARY", "BRAND_DARK", "BRAND_TINT", "ACCENT",
              "GRAY_900", "GRAY_700", "GRAY_500", "GRAY_300", "GRAY_50", "WHITE"]:
        assert hasattr(H, c), f"missing color: {c}"
