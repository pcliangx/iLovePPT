"""tests/pptx/test_mixed_lang_text.py — P3-10 中英文混排标准化测试。

测点:
- tokenize_mixed 切分正确(zh / en / num runs)
- _detect_lang 启发式正确
- mixed_lang_text 写到 paragraph 后:
  * runs 数量对
  * 每 run 字体属性对(lxml <a:ea> / <a:latin> / <a:cs>)
  * 中英混排:<a:ea> 全段 YaHei · <a:latin> 英文段 Arial / 中文段 YaHei
"""
from __future__ import annotations

import pytest
from pptx import Presentation
from pptx.oxml.ns import qn
from pptx.util import Inches

import helpers as H
from helpers._internals import _detect_lang, mixed_lang_text, tokenize_mixed


def _new_prs():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    return prs


def _new_paragraph():
    """加一个空 textbox 拿到一个干净 paragraph(已含 1 空 run 给 p.clear() 清)。"""
    prs = _new_prs()
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    tb = sl.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(1))
    return tb.text_frame.paragraphs[0]


def _ea(run):
    rPr = run._r.find(qn("a:rPr"))
    if rPr is None:
        return None
    el = rPr.find(qn("a:ea"))
    return el.get("typeface") if el is not None else None


def _latin(run):
    rPr = run._r.find(qn("a:rPr"))
    if rPr is None:
        return None
    el = rPr.find(qn("a:latin"))
    return el.get("typeface") if el is not None else None


def _cs(run):
    rPr = run._r.find(qn("a:rPr"))
    if rPr is None:
        return None
    el = rPr.find(qn("a:cs"))
    return el.get("typeface") if el is not None else None


# ============================================================================
# _detect_lang
# ============================================================================


def test_detect_lang_pure_ascii_is_en():
    assert _detect_lang("Hello World") == "en"
    assert _detect_lang("iLovePPT") == "en"


def test_detect_lang_pure_chinese_is_zh():
    assert _detect_lang("你好世界") == "zh"
    assert _detect_lang("开源工具") == "zh"


def test_detect_lang_pure_digits_or_punct_is_num():
    assert _detect_lang("100") == "num"
    assert _detect_lang("100%") == "num"
    assert _detect_lang("1, 000") == "num"


def test_detect_lang_mixed_with_cjk_is_zh_conservative():
    # 含中文 → 保守归 zh(整段中文字体)
    assert _detect_lang("50% 开源") == "zh"
    assert _detect_lang("iLovePPT 是工具") == "zh"


def test_detect_lang_empty_defaults_zh():
    """空串保守 fallback zh,不抛 ValueError。"""
    assert _detect_lang("") == "zh"


# ============================================================================
# tokenize_mixed — 切分
# ============================================================================


def test_tokenize_pure_en():
    result = tokenize_mixed("Hello")
    assert result == [{"text": "Hello", "lang": "en"}]


def test_tokenize_pure_zh():
    result = tokenize_mixed("你好世界")
    assert result == [{"text": "你好世界", "lang": "zh"}]


def test_tokenize_pure_num():
    result = tokenize_mixed("100%")
    assert result == [{"text": "100%", "lang": "num"}]


def test_tokenize_en_then_zh():
    result = tokenize_mixed("Hello 世界")
    langs = [r["lang"] for r in result]
    texts = [r["text"] for r in result]
    # 中间空格归到前 en run(prev_lang 优先)
    assert "en" in langs
    assert "zh" in langs
    # 全段拼回原字符串
    assert "".join(texts) == "Hello 世界"


def test_tokenize_zh_en_num_mix():
    """`iLovePPT 是 100% 开源工具` → en + zh + num + zh"""
    result = tokenize_mixed("iLovePPT 是 100% 开源工具")
    langs = [r["lang"] for r in result]
    texts = [r["text"] for r in result]
    assert langs == ["en", "zh", "num", "zh"]
    assert "".join(texts) == "iLovePPT 是 100% 开源工具"
    # iLovePPT 在 en run · 中文在 zh run · 100% 在 num run
    assert any("iLovePPT" in r["text"] and r["lang"] == "en" for r in result)
    assert any("100%" in r["text"] and r["lang"] == "num" for r in result)
    assert any("开源工具" in r["text"] and r["lang"] == "zh" for r in result)


def test_tokenize_empty_string():
    assert tokenize_mixed("") == []


def test_tokenize_preserves_full_text():
    """tokenize 必须无损 — 所有 run.text 拼起来 == 输入。"""
    cases = [
        "纯中文",
        "Pure English",
        "100 个用户",
        "AI/ML 是 2025 年热点",
        "iLovePPT v0.8.0 即将发布",
        "GDP 增长 8.5%",
    ]
    for s in cases:
        runs = tokenize_mixed(s)
        assert "".join(r["text"] for r in runs) == s, f"failed: {s!r}"


# ============================================================================
# mixed_lang_text — paragraph 写入
# ============================================================================


def test_mixed_lang_text_run_count():
    """3 个 runs 输入应产生 3 个 paragraph.runs。"""
    p = _new_paragraph()
    mixed_lang_text(p, [
        {"text": "你好", "lang": "zh"},
        {"text": "World", "lang": "en"},
        {"text": "100", "lang": "num"},
    ])
    assert len(p.runs) == 3
    assert p.runs[0].text == "你好"
    assert p.runs[1].text == "World"
    assert p.runs[2].text == "100"


def test_mixed_lang_text_clears_existing():
    """p.clear() 先清,再加新 runs(不累加)。"""
    p = _new_paragraph()
    # 先加旧 run
    old = p.add_run()
    old.text = "旧内容"
    assert len(p.runs) >= 1
    mixed_lang_text(p, [{"text": "新", "lang": "zh"}])
    assert len(p.runs) == 1
    assert p.runs[0].text == "新"


def test_mixed_lang_text_zh_run_uses_font_cn():
    """zh run · ea / cs / latin 全 YaHei(set_font 走标准 EA 写入)。"""
    p = _new_paragraph()
    mixed_lang_text(p, [{"text": "中文", "lang": "zh"}])
    r = p.runs[0]
    assert _ea(r) == H.FONT_CN
    assert _cs(r) == H.FONT_CN
    # set_font 也 set font.name = FONT_CN(latin 字段)
    assert r.font.name == H.FONT_CN


def test_mixed_lang_text_en_run_uses_font_latin():
    """en run · latin = Arial · ea 仍 YaHei(混排里防漏掉的中文 char)。"""
    p = _new_paragraph()
    mixed_lang_text(p, [{"text": "English", "lang": "en"}])
    r = p.runs[0]
    # latin / cs 走 set_font 的 name=FONT_LATIN
    assert _ea(r) == H.FONT_LATIN  # set_font 把 name 写到 ea / cs / latin 三处
    assert _cs(r) == H.FONT_LATIN
    assert r.font.name == H.FONT_LATIN
    # 默认 FONT_LATIN = "Arial"
    assert H.FONT_LATIN == "Arial"


def test_mixed_lang_text_num_run_uses_font_num():
    p = _new_paragraph()
    mixed_lang_text(p, [{"text": "100%", "lang": "num"}])
    r = p.runs[0]
    assert r.font.name == H.FONT_NUM


def test_mixed_lang_text_auto_detects():
    """lang='auto' → 调 _detect_lang 决定 — zh detect 后走 FONT_CN。"""
    p = _new_paragraph()
    mixed_lang_text(p, [{"text": "你好", "lang": "auto"}])
    r = p.runs[0]
    assert r.font.name == H.FONT_CN  # detect 为 zh


def test_mixed_lang_text_unknown_lang_raises():
    p = _new_paragraph()
    with pytest.raises(ValueError, match="unknown lang"):
        mixed_lang_text(p, [{"text": "x", "lang": "fr"}])


def test_mixed_lang_text_zh_en_mix_independent_fonts():
    """zh + en 混排 · 每 run 独立字体 · 验证完整 lxml 字段。"""
    p = _new_paragraph()
    mixed_lang_text(p, [
        {"text": "iLovePPT ", "lang": "en"},
        {"text": "是开源工具", "lang": "zh"},
    ])
    assert len(p.runs) == 2
    en_run, zh_run = p.runs[0], p.runs[1]
    # 英文 run:Arial 全段
    assert _ea(en_run) == H.FONT_LATIN
    assert _cs(en_run) == H.FONT_LATIN
    assert en_run.font.name == H.FONT_LATIN
    # 中文 run:YaHei 全段
    assert _ea(zh_run) == H.FONT_CN
    assert _cs(zh_run) == H.FONT_CN
    assert zh_run.font.name == H.FONT_CN


def test_mixed_lang_text_default_size_18():
    """默认 default_font_size=18(layout body 常用)。"""
    from pptx.util import Pt
    p = _new_paragraph()
    mixed_lang_text(p, [{"text": "test", "lang": "en"}])
    assert p.runs[0].font.size == Pt(18)


def test_mixed_lang_text_custom_size():
    from pptx.util import Pt
    p = _new_paragraph()
    mixed_lang_text(p, [{"text": "test", "lang": "en"}], default_font_size=24)
    assert p.runs[0].font.size == Pt(24)


def test_mixed_lang_text_bold_and_color():
    """bold / color 参数生效。"""
    p = _new_paragraph()
    mixed_lang_text(
        p,
        [{"text": "强调", "lang": "zh"}],
        default_font_size=20,
        bold=True,
        color=H.BRAND_DARK,
    )
    r = p.runs[0]
    assert r.font.bold is True
    assert r.font.color.rgb == H.BRAND_DARK


def test_mixed_lang_text_with_tokenize_pipeline():
    """tokenize_mixed → mixed_lang_text 闭环:从 str 一步出多 run。"""
    p = _new_paragraph()
    runs = tokenize_mixed("iLovePPT 是 100% 开源")
    mixed_lang_text(p, runs)
    # 至少 3 runs(en + zh + num + zh)
    assert len(p.runs) >= 3
    # 每个 run 字体走对应语言
    for run in p.runs:
        # ea / cs 字段必须存在(避免回到 fallback)
        assert _ea(run) is not None
        assert _cs(run) is not None


# ============================================================================
# 跟 set_font 互不冲突 — 不破回原有 EA 不变量
# ============================================================================


def test_mixed_lang_text_ea_field_written_via_lxml():
    """核心不变量:中文 run 必须通过 lxml 写 <a:ea> · 跨平台不 fallback。"""
    p = _new_paragraph()
    mixed_lang_text(p, [{"text": "中文测试", "lang": "zh"}])
    r = p.runs[0]
    rPr = r._r.find(qn("a:rPr"))
    assert rPr is not None
    ea = rPr.find(qn("a:ea"))
    assert ea is not None, "mixed_lang_text 中文 run 必须写 <a:ea>"
    assert ea.get("typeface") == H.FONT_CN
