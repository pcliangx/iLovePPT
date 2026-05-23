# tests/pptx/test_helpers.py
"""helpers.py light test：验证 shape 数、字体名、color、文字内容。
真正的"长得对不对"由 examples/minimal_deck.py 视觉 smoke test 验证。"""
from pptx import Presentation
from pptx.util import Inches, Pt
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
    from pptx.oxml.ns import qn
    rPr = run._r.find(qn("a:rPr"))
    ea = rPr.find(qn("a:ea"))
    cs = rPr.find(qn("a:cs"))
    assert ea is not None, "set_font 必须写 <a:ea>"
    assert ea.get("typeface") == "Microsoft YaHei"
    assert cs is not None, "set_font 必须写 <a:cs>"
    assert cs.get("typeface") == "Microsoft YaHei"


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


def test_footer_writes_divider_and_page_number():
    prs = _new_prs()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    n_before = len(slide.shapes)
    H.footer(slide, 3, 12)
    # divider rect + page-num textbox = 2 个新 shape
    assert len(slide.shapes) == n_before + 2
    # rect autoshape 也有 text_frame(只是空的);筛选真有文字的
    text_shapes = [
        sh for sh in slide.shapes if sh.has_text_frame and sh.text_frame.text
    ]
    assert len(text_shapes) == 1
    text = text_shapes[0].text_frame.text
    assert "3" in text and "12" in text and "/" in text
    # 字号 9pt / GRAY_500
    run = text_shapes[0].text_frame.paragraphs[0].runs[0]
    assert run.font.size == Pt(9)
    assert run.font.color.rgb == H.GRAY_500


def test_footer_with_left_text_adds_third_shape():
    prs = _new_prs()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    n_before = len(slide.shapes)
    H.footer(slide, 1, 10, left_text="iLovePPT · 2026-05-23")
    # divider + page-num textbox + left textbox = 3 个新 shape
    assert len(slide.shapes) == n_before + 3
    texts = " ".join(
        sh.text_frame.text for sh in slide.shapes if sh.has_text_frame
    )
    assert "iLovePPT" in texts
    assert "1 / 10" in texts


def test_footer_no_divider_omits_rect():
    prs = _new_prs()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    n_before = len(slide.shapes)
    H.footer(slide, 1, 10, divider=False)
    # 只有页码 textbox,无 divider rect
    assert len(slide.shapes) == n_before + 1


def test_footer_chinese_left_text_writes_ea_typeface():
    """左侧中文文字必须走 set_font 的 EA 字段写入(防 fallback)。"""
    prs = _new_prs()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    H.footer(slide, 1, 5, left_text="技术部 · 演示稿")
    from pptx.oxml.ns import qn
    text_shapes = [sh for sh in slide.shapes if sh.has_text_frame]
    cn_shape = next(s for s in text_shapes if "技术" in s.text_frame.text)
    run = cn_shape.text_frame.paragraphs[0].runs[0]
    rPr = run._r.find(qn("a:rPr"))
    ea = rPr.find(qn("a:ea"))
    assert ea is not None and ea.get("typeface") == H.FONT_CN


def test_footer_meta_composes_left_text_when_no_explicit():
    """classification / project / version 应自动用 ' · ' 拼成 left_text。"""
    prs = _new_prs()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    H.footer(slide, 1, 5,
             classification="INTERNAL",
             project="Project Atlas",
             version="v1.0")
    text_shapes = [sh for sh in slide.shapes
                   if sh.has_text_frame and sh.text_frame.text]
    # 应有 2 个文本(page num + 拼接后的 left)
    assert len(text_shapes) == 2
    texts = " | ".join(sh.text_frame.text for sh in text_shapes)
    assert "INTERNAL · Project Atlas · v1.0" in texts


def test_footer_explicit_left_text_overrides_meta():
    """显式 left_text 优先于 classification / project / version。"""
    prs = _new_prs()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    H.footer(slide, 1, 5,
             left_text="自定义页脚",
             classification="SHOULD-IGNORE",
             project="SHOULD-IGNORE")
    text_shapes = [sh for sh in slide.shapes
                   if sh.has_text_frame and sh.text_frame.text]
    texts = " | ".join(sh.text_frame.text for sh in text_shapes)
    assert "自定义页脚" in texts
    assert "SHOULD-IGNORE" not in texts


def test_source_citation_renders_with_prefix():
    """source_citation 自动加 'Source: ' 前缀(除非已有)。"""
    prs = _new_prs()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    H.source_citation(slide, "公司财报 2025 Q4")
    text_shapes = [sh for sh in slide.shapes
                   if sh.has_text_frame and sh.text_frame.text]
    assert len(text_shapes) == 1
    assert text_shapes[0].text_frame.text == "Source: 公司财报 2025 Q4"


def test_source_citation_skips_prefix_if_already_present():
    prs = _new_prs()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    H.source_citation(slide, "来源:IDC 2024 报告")
    text_shapes = [sh for sh in slide.shapes
                   if sh.has_text_frame and sh.text_frame.text]
    assert text_shapes[0].text_frame.text == "来源:IDC 2024 报告"


def test_source_citation_empty_does_nothing():
    prs = _new_prs()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    n_before = len(slide.shapes)
    H.source_citation(slide, "")
    H.source_citation(slide, None)
    assert len(slide.shapes) == n_before


def test_aaa_brand_primary_contrast_against_white():
    """BRAND_PRIMARY 在白底对比度应 >= 7:1(AAA 标准)。"""
    # WCAG luminance 公式
    def lum(c):
        def chan(v):
            v = v / 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * chan(c[0]) + 0.7152 * chan(c[1]) + 0.0722 * chan(c[2])

    bp = H.BRAND_PRIMARY
    contrast = (1 + 0.05) / (lum(bp) + 0.05)
    assert contrast >= 7.0, f"BRAND_PRIMARY 对比度 {contrast:.2f} 不过 AAA"


def test_clear_template_slides_removes_all_slides():
    prs = _new_prs()
    # 加 3 张 slide
    for _ in range(3):
        prs.slides.add_slide(prs.slide_layouts[6])
    assert len(prs.slides) == 3
    H.clear_template_slides(prs)
    assert len(prs.slides) == 0
    # 验证清空后仍可继续 add_slide 并保存
    prs.slides.add_slide(prs.slide_layouts[6])
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
        prs.save(f.name)
        assert os.path.getsize(f.name) > 0
        os.unlink(f.name)
