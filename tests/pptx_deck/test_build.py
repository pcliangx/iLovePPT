"""build.py 单元测试。"""
import json
from pathlib import Path

import pytest

from pptx import Presentation as _Pres

from build import (
    FOOTERED_LAYOUTS,
    _extract_design_tokens,
    build_deck,
    load_plan,
    load_theme,
)
from themes import tech_blue


def _write_plan(tmp_path, data):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def test_load_plan_valid(tmp_path):
    p = _write_plan(tmp_path, {
        "theme": "tech_blue", "output": "./out.pptx",
        "slides": [{"layout": "cover", "title": "T", "subtitle": "S"}]})
    plan = load_plan(p)
    assert plan["theme"] == "tech_blue"
    assert plan["_plan_dir"] == str(tmp_path.resolve())


def test_load_plan_missing_field_raises(tmp_path):
    p = _write_plan(tmp_path, {"theme": "tech_blue", "slides": []})
    with pytest.raises(ValueError) as e:
        load_plan(p)
    assert "output" in str(e.value)


def test_load_plan_slide_missing_layout_raises(tmp_path):
    p = _write_plan(tmp_path, {
        "theme": "tech_blue", "output": "./o.pptx",
        "slides": [{"title": "无 layout"}]})
    with pytest.raises(ValueError) as e:
        load_plan(p)
    assert "第 1 页" in str(e.value)


def test_load_theme_tech_blue():
    assert load_theme("tech_blue") is tech_blue


def test_load_theme_unknown_raises():
    with pytest.raises(ValueError):
        load_theme("nope")


def test_load_theme_pptx_missing_raises():
    with pytest.raises(FileNotFoundError):
        load_theme("/tmp/does_not_exist_xyz.pptx")


def test_build_deck_produces_pptx(tmp_path):
    p = _write_plan(tmp_path, {
        "theme": "tech_blue", "output": "./deck.pptx",
        "slides": [
            {"layout": "cover", "title": "标题", "subtitle": "副标题"},
            {"layout": "bullet_list", "title": "要点", "items": ["a", "b"]}]})
    plan = load_plan(p)
    out = build_deck(plan)
    assert out.exists()
    assert out.stat().st_size > 0
    assert out.parent == tmp_path.resolve()


def test_build_deck_unknown_layout_raises(tmp_path):
    p = _write_plan(tmp_path, {
        "theme": "tech_blue", "output": "./d.pptx",
        "slides": [{"layout": "nonexistent_xyz"}]})
    plan = load_plan(p)
    with pytest.raises(ValueError) as e:
        build_deck(plan)
    assert "未知 layout" in str(e.value)


def test_build_deck_bad_field_raises_with_page_number(tmp_path):
    p = _write_plan(tmp_path, {
        "theme": "tech_blue", "output": "./d.pptx",
        "slides": [{"layout": "cover", "wrong_field": "x"}]})
    plan = load_plan(p)
    with pytest.raises(ValueError) as e:
        build_deck(plan)
    assert "第 1 页" in str(e.value)


# ----- footer / 页码集成测试 -----

def _build_and_open(tmp_path, slides_def):
    """构建一个 mini deck,返回打开后的 Presentation 对象供 inspect。"""
    p = _write_plan(tmp_path, {
        "theme": "tech_blue", "output": "./d.pptx", "slides": slides_def})
    plan = load_plan(p)
    out = build_deck(plan)
    return _Pres(str(out))


def test_footer_added_only_to_footered_layouts(tmp_path):
    """cover / section_divider / closing 不带页脚;其他 8 种 layout 带。"""
    prs = _build_and_open(tmp_path, [
        {"layout": "cover", "title": "T", "subtitle": "S"},
        {"layout": "section_divider", "num": 1, "title": "第一章"},
        {"layout": "bullet_list", "title": "要点", "items": ["a", "b"]},
        {"layout": "closing", "subtitle": ""},
    ])
    # 找带 "/" 的 textbox(页码标记)
    def has_page_num(slide):
        for sh in slide.shapes:
            if sh.has_text_frame and "/" in sh.text_frame.text:
                # 排除大段含"/"的正文:页码一定是 "N / M" 整段
                t = sh.text_frame.text.strip()
                if len(t) <= 10 and t.replace(" ", "").replace("/", "").isdigit():
                    return True
        return False
    assert not has_page_num(prs.slides[0]), "cover 不应有页码"
    assert not has_page_num(prs.slides[1]), "section_divider 不应有页码"
    assert has_page_num(prs.slides[2]), "bullet_list 应有页码"
    assert not has_page_num(prs.slides[3]), "closing 不应有页码"


def test_footer_page_num_uses_content_page_index_not_absolute(tmp_path):
    """N / TOTAL 的 N 是 content page 序号(跳过 cover/divider/closing),
    TOTAL 是 content page 总数。"""
    prs = _build_and_open(tmp_path, [
        {"layout": "cover", "title": "T", "subtitle": "S"},
        {"layout": "section_divider", "num": 1, "title": "一"},
        {"layout": "cards", "title": "A",
         "cards": [{"title": "x", "body": "y"}]},
        {"layout": "section_divider", "num": 2, "title": "二"},
        {"layout": "cards", "title": "B",
         "cards": [{"title": "x", "body": "y"}]},
        {"layout": "closing", "subtitle": ""},
    ])
    # 2 个 content page(cards × 2)
    page_nums = []
    for slide in prs.slides:
        for sh in slide.shapes:
            if sh.has_text_frame:
                t = sh.text_frame.text.strip()
                if "/" in t and len(t) <= 10:
                    page_nums.append(t)
    assert page_nums == ["1 / 2", "2 / 2"]


def test_footered_layouts_constant_matches_spec():
    """常量必须覆盖规范要求的 8 种 layout(除 cover/section_divider/closing)。"""
    assert FOOTERED_LAYOUTS == frozenset({
        "toc", "single_focus", "compare", "cards",
        "bullet_list", "table", "pic_text", "summary",
    })


def test_source_field_renders_citation(tmp_path):
    """deck_plan slide 含 'source' 字段时,build.py 自动加 Source: 引文。"""
    prs = _build_and_open(tmp_path, [
        {"layout": "table", "title": "数据", "headers": ["A", "B"],
         "rows": [["1", "2"]],
         "source": "公司财报 2025 Q4"},
    ])
    texts = " | ".join(
        sh.text_frame.text for sh in prs.slides[0].shapes
        if sh.has_text_frame and sh.text_frame.text
    )
    assert "Source: 公司财报 2025 Q4" in texts


def test_source_field_does_not_break_make_table_signature(tmp_path):
    """'source' 是 cross-cutting 字段,不应作为 make_table 的 kwarg。"""
    # 如果 build.py 没正确 pop "source",会触发 TypeError
    p = _write_plan(tmp_path, {
        "theme": "tech_blue", "output": "./d.pptx",
        "slides": [{"layout": "table", "title": "T",
                    "headers": ["A"], "rows": [["1"]],
                    "source": "Test"}]})
    plan = load_plan(p)
    out = build_deck(plan)
    assert out.exists()


def test_footer_meta_propagates_to_all_content_pages(tmp_path):
    """plan.footer_meta 应在每个内容页 footer 左侧显示。"""
    prs = _build_and_open(tmp_path, [
        {"layout": "cover", "title": "T", "subtitle": "S"},
        {"layout": "cards", "title": "A",
         "cards": [{"title": "x", "body": "y"}]},
        {"layout": "bullet_list", "title": "B", "items": ["1", "2"]},
        {"layout": "closing", "subtitle": ""},
    ])
    # 在 deck_plan 顶层加 footer_meta —— 需要走 _write_plan 写完整 plan
    p = _write_plan(tmp_path, {
        "theme": "tech_blue", "output": "./d2.pptx",
        "footer_meta": {
            "classification": "INTERNAL",
            "project": "Project Atlas",
            "version": "v1.0",
        },
        "slides": [
            {"layout": "cover", "title": "T", "subtitle": "S"},
            {"layout": "cards", "title": "A",
             "cards": [{"title": "x", "body": "y"}]},
            {"layout": "bullet_list", "title": "B", "items": ["1", "2"]},
            {"layout": "closing", "subtitle": ""},
        ],
    })
    plan = load_plan(p)
    out = build_deck(plan)
    prs2 = _Pres(str(out))
    # cards 和 bullet_list 应有 footer_meta;cover 和 closing 没有
    def has_meta(slide):
        for sh in slide.shapes:
            if sh.has_text_frame and "INTERNAL · Project Atlas · v1.0" in sh.text_frame.text:
                return True
        return False
    assert not has_meta(prs2.slides[0]), "cover 不应有 footer_meta"
    assert has_meta(prs2.slides[1]), "cards 应有 footer_meta"
    assert has_meta(prs2.slides[2]), "bullet_list 应有 footer_meta"
    assert not has_meta(prs2.slides[3]), "closing 不应有 footer_meta"
