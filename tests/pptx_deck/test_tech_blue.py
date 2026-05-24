# tests/pptx_deck/test_tech_blue.py
"""tech_blue 主题 13 layout light test：验证每个 layout 创建后 prs.slides 增加 1。"""
from pptx import Presentation
from pptx.util import Inches
from themes import tech_blue as T


def _new():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    return prs


def test_make_cover():
    prs = _new()
    T.make_cover(prs, "主标题", "副标题")
    assert len(prs.slides) == 1

def test_make_toc():
    prs = _new()
    T.make_toc(prs, sections=["背景", "范围", "流程", "保障", "节奏"])
    assert len(prs.slides) == 1

def test_make_section_divider():
    prs = _new()
    T.make_section_divider(prs, 1, "第一章")
    assert len(prs.slides) == 1

def test_make_single_focus():
    prs = _new()
    T.make_single_focus(prs, big_text="一句话", big_number="80%", explanation="解释")
    assert len(prs.slides) == 1

def test_make_compare_two_items():
    prs = _new()
    T.make_compare(prs, "对比", items=[
        {"title": "现状", "body": "手工"},
        {"title": "目标", "body": "自动"}])
    assert len(prs.slides) == 1

def test_make_compare_three_items():
    prs = _new()
    T.make_compare(prs, "三方对比", items=[
        {"title": "A", "body": "x"}, {"title": "B", "body": "y"},
        {"title": "C", "body": "z"}])
    assert len(prs.slides) == 1

def test_make_compare_with_recommended_adds_badge():
    """recommended=True 主推列 = 多 1 个 OVAL 徽章 + 1 个徽章文字 = 2 shapes vs 普通列。"""
    prs = _new()
    T.make_compare(prs, "高亮", items=[
        {"title": "普通", "body": "x"},
        {"title": "主推", "body": "y", "recommended": True}])
    assert len(prs.slides) == 1
    # 每列基础 4 shapes(header rect + header textbox + body rect + body textbox)
    # 主推列多 1 OVAL + 1 textbox(徽章)→ title 1 + 2*4 + 2 = 11
    assert len(prs.slides[0].shapes) == 11

def test_make_compare_pk():
    prs = _new()
    T.make_compare_pk(prs, "对决",
                      left={"title": "旧", "body": "旧方案 body"},
                      right={"title": "新", "body": "新方案 body"})
    assert len(prs.slides) == 1
    # title + 2 sides × (bg + bar + title + body) + VS circle + VS text = 1+8+2 = 11
    assert len(prs.slides[0].shapes) == 11

def test_make_matrix_2x2():
    prs = _new()
    T.make_matrix_2x2(prs, "矩阵",
        x_axis={"low": "x 低", "high": "x 高"},
        y_axis={"low": "y 低", "high": "y 高"},
        quadrants=[
            {"pos": "tl", "title": "tl", "body": "tl body"},
            {"pos": "tr", "title": "主推", "body": "tr body", "highlight": True},
            {"pos": "bl", "title": "bl", "body": "bl body"},
            {"pos": "br", "title": "br", "body": "br body"}])
    assert len(prs.slides) == 1
    # title + 4 象限 × (rect + title textbox + body textbox) + 4 axis labels = 1+12+4 = 17
    assert len(prs.slides[0].shapes) == 17

def test_make_matrix_2x2_invalid_pos_raises():
    prs = _new()
    import pytest
    with pytest.raises(ValueError, match="quadrant.pos"):
        T.make_matrix_2x2(prs, "x",
            x_axis={"low": "a", "high": "b"},
            y_axis={"low": "c", "high": "d"},
            quadrants=[{"pos": "xx", "title": "t", "body": "b"}])

def test_make_cards_two():
    prs = _new()
    T.make_cards(prs, "两栏", cards=[
        {"title": "卡1", "body": "正文1"}, {"title": "卡2", "body": "正文2"}])
    assert len(prs.slides) == 1

def test_make_cards_four():
    prs = _new()
    T.make_cards(prs, "四栏", cards=[
        {"title": f"卡{i}", "body": f"正文{i}"} for i in range(1, 5)])
    assert len(prs.slides) == 1

def test_make_bullet_list():
    prs = _new()
    T.make_bullet_list(prs, "标题", items=["要点1", "要点2", "要点3", "要点4", "要点5"])
    assert len(prs.slides) == 1
    assert len(prs.slides[0].shapes) == 2  # title textbox + bullets textbox

def test_make_table():
    prs = _new()
    T.make_table(prs, "表格标题",
                 headers=["A", "B", "C"],
                 rows=[["1", "2", "3"], ["4", "5", "6"]])
    assert len(prs.slides) == 1
    assert len(prs.slides[0].shapes) == 2  # title textbox + table

def test_make_pic_text(tmp_path):
    from PIL import Image
    img_path = tmp_path / "blank.png"
    Image.new("RGB", (10, 10), "white").save(str(img_path))
    prs = _new()
    T.make_pic_text(prs, "标题", str(img_path),
                    points=[{"title": "点1", "body": "正文1"},
                            {"title": "点2", "body": "正文2"}])
    assert len(prs.slides) == 1

def test_make_summary():
    prs = _new()
    T.make_summary(prs, conclusions=["结论 1", "结论 2", "结论 3"])
    assert len(prs.slides) == 1

def test_make_closing():
    prs = _new()
    T.make_closing(prs, subtitle="联系邮箱：x@y.com")
    assert len(prs.slides) == 1

def test_font_default_is_microsoft_yahei():
    assert T.FONT_HEADER == "Microsoft YaHei"
    assert T.FONT_BODY == "Microsoft YaHei"


# ----- 2026-05-23 新增字段测试 -----

def test_make_cover_with_metadata():
    """cover 接受 prepared_by / date / version / project_code / classification。"""
    prs = _new()
    T.make_cover(prs, "T", "S",
                 prepared_by="技术部",
                 date="2026-05-23",
                 version="v1.0",
                 project_code="ATLAS-01",
                 classification="INTERNAL")
    slide = prs.slides[0]
    texts = [sh.text_frame.text for sh in slide.shapes
             if sh.has_text_frame and sh.text_frame.text]
    joined = " | ".join(texts)
    assert "INTERNAL" in joined
    assert "技术部" in joined
    assert "2026-05-23" in joined
    assert "v1.0" in joined
    assert "ATLAS-01" in joined


def test_make_cover_no_metadata_still_works():
    """cover 不传任何 meta 字段时,保持原有 title + subtitle 渲染。"""
    prs = _new()
    T.make_cover(prs, "T", "S")
    slide = prs.slides[0]
    texts = [sh.text_frame.text for sh in slide.shapes
             if sh.has_text_frame and sh.text_frame.text]
    joined = " | ".join(texts)
    assert "T" in joined and "S" in joined


def test_make_closing_with_next_steps():
    """next_steps 模式:渲染 'Next Steps' 标题 + 编号 action 列表。"""
    prs = _new()
    T.make_closing(prs, subtitle="问答 / 联系",
                   next_steps=[
                       {"action": "完成 Phase 1 试点", "owner": "Alice",
                        "due": "2026-06-15"},
                       {"action": "评估扩展到 Phase 2", "owner": "Bob",
                        "due": "2026-07-01"}])
    slide = prs.slides[0]
    texts = " | ".join(sh.text_frame.text for sh in slide.shapes
                       if sh.has_text_frame and sh.text_frame.text)
    assert "Next Steps" in texts
    assert "完成 Phase 1 试点" in texts
    assert "Alice" in texts and "2026-06-15" in texts
    assert "评估扩展到 Phase 2" in texts


def test_make_closing_without_next_steps_uses_simple_mode():
    """无 next_steps 时退回原版'谢谢'封底。"""
    prs = _new()
    T.make_closing(prs, subtitle="github.com/xxx")
    slide = prs.slides[0]
    texts = " | ".join(sh.text_frame.text for sh in slide.shapes
                       if sh.has_text_frame and sh.text_frame.text)
    assert "谢谢" in texts
    assert "Next Steps" not in texts
