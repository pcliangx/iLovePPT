"""Layout plugin auto-discover + registry 单元测试(P3-2)。

测点:
- LayoutRegistry 注册全部 17 个 plugin
- register_layout decorator 正常工作 + 失败 fail-loud
- 每个 plugin 能成功渲染最小输入(返回 Slide,prs.slides 增 1)
"""
from __future__ import annotations

import pytest
from pptx import Presentation
from pptx.util import Inches

import helpers as H


def _new_prs():
    p = Presentation()
    p.slide_width = Inches(13.333)
    p.slide_height = Inches(7.5)
    return p


# ===== Registry 行为 =====


def test_registry_singleton():
    """LayoutRegistry 是 class-level singleton(多次取同一份)。"""
    from helpers._base import LayoutRegistry as L1
    from helpers._base import LayoutRegistry as L2
    assert L1 is L2
    assert L1._layouts is L2._layouts


def test_registry_get_unknown_lists_known():
    """get(unknown) 抛 KeyError + 列已知 layouts。"""
    with pytest.raises(KeyError, match="No layout plugin for 'nonexistent'"):
        H.LayoutRegistry.get("nonexistent")


def test_registry_has():
    assert H.LayoutRegistry.has("cover")
    assert not H.LayoutRegistry.has("nonexistent_layout_xyz")


def test_register_layout_decorator():
    """register_layout decorator 注册到 _layouts dict。"""
    @H.register_layout("__test_temp_layout__")
    def fn(prs):
        return None
    assert H.LayoutRegistry.has("__test_temp_layout__")
    assert H.LayoutRegistry.get("__test_temp_layout__") is fn
    # cleanup
    H.LayoutRegistry._layouts.pop("__test_temp_layout__", None)


# ===== 17 个 layout 已注册 =====


EXPECTED_LAYOUTS = {
    "cover", "toc", "section_divider", "single_focus", "cards", "bullet_list",
    "data", "process_flow", "timeline", "pyramid", "radial", "venn", "quadrant",
    "comparison", "closing", "summary", "quote",
}


def test_all_17_layouts_registered():
    """17 个 plugin auto-discover 完整。"""
    discovered = set(H.LayoutRegistry.all_layouts())
    missing = EXPECTED_LAYOUTS - discovered
    assert not missing, f"未注册 layout: {missing}"


# ===== 每个 plugin 能渲染 =====


def test_cover_renders():
    fn = H.LayoutRegistry.get("cover")
    prs = _new_prs()
    fn(prs, "主标题", "副标题")
    assert len(prs.slides) == 1


def test_toc_renders():
    fn = H.LayoutRegistry.get("toc")
    prs = _new_prs()
    fn(prs, sections=["第一", "第二", "第三"])
    assert len(prs.slides) == 1


def test_section_divider_renders():
    fn = H.LayoutRegistry.get("section_divider")
    prs = _new_prs()
    fn(prs, 1, "第一章")
    assert len(prs.slides) == 1


def test_single_focus_renders():
    fn = H.LayoutRegistry.get("single_focus")
    prs = _new_prs()
    fn(prs, big_text="大字", big_number="80%", explanation="说明")
    assert len(prs.slides) == 1


def test_cards_renders():
    fn = H.LayoutRegistry.get("cards")
    prs = _new_prs()
    fn(prs, "卡片", cards=[
        {"title": "t1", "body": "b1"},
        {"title": "t2", "body": "b2"},
    ])
    assert len(prs.slides) == 1


def test_bullet_list_renders():
    fn = H.LayoutRegistry.get("bullet_list")
    prs = _new_prs()
    fn(prs, "要点", items=["要点 1", "要点 2", "要点 3"])
    assert len(prs.slides) == 1


def test_data_table_renders():
    fn = H.LayoutRegistry.get("data")
    prs = _new_prs()
    fn(prs, "数据", headers=["A", "B"], table_rows=[["1", "2"], ["3", "4"]])
    assert len(prs.slides) == 1


def test_data_requires_chart_or_table():
    fn = H.LayoutRegistry.get("data")
    prs = _new_prs()
    with pytest.raises(ValueError, match="chart_path 或"):
        fn(prs, "数据")  # 啥都不传


def test_process_flow_renders():
    fn = H.LayoutRegistry.get("process_flow")
    prs = _new_prs()
    fn(prs, "流程", steps=[
        {"title": "步骤 1", "desc": "做 A"},
        {"title": "步骤 2", "desc": "做 B"},
    ])
    assert len(prs.slides) == 1


def test_timeline_renders():
    fn = H.LayoutRegistry.get("timeline")
    prs = _new_prs()
    fn(prs, "时间线", milestones=[
        {"title": "M1", "desc": "d1", "date": "2026 Q1"},
        {"title": "M2", "desc": "d2", "date": "2026 Q2"},
        {"title": "M3", "desc": "d3", "date": "2026 Q3"},
    ])
    assert len(prs.slides) == 1


def test_pyramid_renders():
    fn = H.LayoutRegistry.get("pyramid")
    prs = _new_prs()
    fn(prs, "金字塔", tiers=["顶", "中", "底"])
    assert len(prs.slides) == 1


def test_radial_renders():
    fn = H.LayoutRegistry.get("radial")
    prs = _new_prs()
    fn(prs, "辐射", center={"title": "中心"}, spokes=[
        {"title": "1", "body": "b"},
        {"title": "2", "body": "b"},
        {"title": "3", "body": "b"},
        {"title": "4", "body": "b"},
    ])
    assert len(prs.slides) == 1


def test_venn_renders_2set():
    fn = H.LayoutRegistry.get("venn")
    prs = _new_prs()
    fn(prs, "Venn 2 圆", sets=[{"label": "A"}, {"label": "B"}],
       intersection_label="共同")
    assert len(prs.slides) == 1


def test_venn_renders_3set():
    fn = H.LayoutRegistry.get("venn")
    prs = _new_prs()
    fn(prs, "Venn 3 圆", sets=[{"label": "A"}, {"label": "B"}, {"label": "C"}])
    assert len(prs.slides) == 1


def test_venn_4set_raises():
    fn = H.LayoutRegistry.get("venn")
    prs = _new_prs()
    with pytest.raises(ValueError, match="venn 仅支持"):
        fn(prs, "X", sets=[{"label": s} for s in "ABCD"])


def test_quadrant_renders():
    fn = H.LayoutRegistry.get("quadrant")
    prs = _new_prs()
    fn(prs, "象限",
       x_axis={"low": "x低", "high": "x高"},
       y_axis={"low": "y低", "high": "y高"},
       quadrants=[{"pos": p, "title": "q", "body": "b"}
                  for p in ("tl", "tr", "bl", "br")])
    assert len(prs.slides) == 1


def test_comparison_renders():
    fn = H.LayoutRegistry.get("comparison")
    prs = _new_prs()
    fn(prs, "对比", items=[
        {"title": "A", "body": "b1"},
        {"title": "B", "body": "b2", "recommended": True},
    ])
    assert len(prs.slides) == 1


def test_summary_renders():
    fn = H.LayoutRegistry.get("summary")
    prs = _new_prs()
    fn(prs, conclusions=["结论 1", "结论 2", "结论 3"])
    assert len(prs.slides) == 1


def test_closing_simple_renders():
    fn = H.LayoutRegistry.get("closing")
    prs = _new_prs()
    fn(prs, subtitle="thanks")
    assert len(prs.slides) == 1


def test_closing_next_steps_renders():
    fn = H.LayoutRegistry.get("closing")
    prs = _new_prs()
    fn(prs, next_steps=[
        {"action": "做 A", "owner": "Alice", "due": "2026-06"},
        {"action": "做 B", "owner": "Bob"},
    ])
    assert len(prs.slides) == 1


def test_quote_renders():
    fn = H.LayoutRegistry.get("quote")
    prs = _new_prs()
    fn(prs, "这是一段证言", attribution="张三", role="CEO")
    assert len(prs.slides) == 1


# ===== theme override 路径 =====


def test_plugin_accepts_optional_theme():
    """所有 plugin 必须支持 theme=None(无 theme 时用 helpers default token)。"""
    fn = H.LayoutRegistry.get("cover")
    prs = _new_prs()
    fn(prs, "标题", "副标")  # 无 theme
    assert len(prs.slides) == 1


def test_plugin_uses_theme_tokens_when_provided():
    """传 theme module 时,plugin 用 theme.PRIMARY 等 token override default。"""
    from pptx.dml.color import RGBColor
    import types
    fake_theme = types.SimpleNamespace(
        PRIMARY=RGBColor(0xFF, 0x00, 0x00),
        PRIMARY_DEEP=RGBColor(0x88, 0x00, 0x00),
        PRIMARY_TINT=RGBColor(0xFF, 0xCC, 0xCC),
        ACCENT=RGBColor(0x00, 0xFF, 0x00),
        FONT_HEADER="Test Font",
        FONT_BODY="Test Font",
        FONT_NUM="Test Font",
    )
    fn = H.LayoutRegistry.get("cover")
    prs = _new_prs()
    fn(prs, "T", "S", theme=fake_theme)
    # 检查 background rect 用了 fake theme 的 PRIMARY_DEEP(#880000)
    slide = prs.slides[0]
    bg_shapes = [
        sh for sh in slide.shapes
        if hasattr(sh, "fill") and getattr(sh, "shape_type", None) is not None
    ]
    # 至少应有 1 个 shape 填了 fake_theme.PRIMARY_DEEP
    fake_deep_hex = "880000"
    found = False
    for sh in bg_shapes:
        try:
            if sh.fill.fore_color.rgb is not None and \
               str(sh.fill.fore_color.rgb).upper() == fake_deep_hex.upper():
                found = True; break
        except Exception:
            continue
    assert found, "应有 shape 使用 fake_theme.PRIMARY_DEEP (#880000),实际未找到"
