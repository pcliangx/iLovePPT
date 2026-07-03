"""themes/_base.py · yaml-based theme loader tests."""
import pytest
from pptx.dml.color import RGBColor

from themes._base import (
    ThemeConfig,
    apply_theme,
    get_layout_func,
    list_themes,
    load_and_apply,
    load_theme,
)


# ----- load_theme -----

def test_load_theme_tech_blue():
    cfg = load_theme("tech_blue")
    assert isinstance(cfg, ThemeConfig)
    assert cfg.name == "tech_blue"
    assert cfg.description.startswith("BCG")
    assert cfg.colors["brand_primary"] == RGBColor(0x0A, 0x52, 0xBF)
    assert cfg.colors["brand_dark"] == RGBColor(0x0B, 0x2A, 0x4A)
    assert cfg.fonts["ea"] == "Microsoft YaHei"
    assert cfg.fonts["title_size_pt"] == 28


def test_load_theme_template_training_color_override():
    cfg = load_theme("template_training")
    # 橙红 #EF5938 是 template_training 独有色板
    assert cfg.colors["brand_primary"] == RGBColor(0xEF, 0x59, 0x38)


def test_load_theme_layouts_mapping_present():
    cfg = load_theme("tech_blue")
    # tech_blue 不实现 pyramid / radial / process_flow
    assert cfg.layouts["pyramid"] is None
    assert cfg.layouts["radial"] is None
    # 实现 cover / cards / quadrant (aliased to make_matrix_2x2)
    assert cfg.layouts["cover"] == "make_cover"
    assert cfg.layouts["quadrant"] == "make_matrix_2x2"


def test_load_theme_unknown_raises():
    with pytest.raises(FileNotFoundError) as e:
        load_theme("nonexistent_xyz_theme")
    assert "nonexistent_xyz_theme" in str(e.value)
    # 提示 schema 文档
    assert "_schema.yaml" in str(e.value) or "tech_blue" in str(e.value)


def test_load_theme_implementation_meta():
    cfg = load_theme("template_golden")
    assert cfg.tier2 is True
    assert cfg.tier3_fallback == "tech_blue"


# ----- apply_theme + module dispatch -----

def test_load_and_apply_pushes_tokens_to_module():
    cfg, mod = load_and_apply("tech_blue")
    # yaml token → module 常量
    assert mod.PRIMARY == cfg.colors["brand_primary"]
    assert mod.PRIMARY_DEEP == cfg.colors["brand_dark"]
    assert mod.PRIMARY_TINT == cfg.colors["brand_tint"]
    assert mod.ACCENT == cfg.colors["accent"]
    assert mod.FONT_HEADER == "Microsoft YaHei"
    assert mod.FONT_BODY == "Microsoft YaHei"


def test_load_and_apply_template_training_overrides_color():
    cfg, mod = load_and_apply("template_training")
    # 橙红 #EF5938 来自 yaml · apply 到 module.PRIMARY
    assert mod.PRIMARY == RGBColor(0xEF, 0x59, 0x38)


# ----- get_layout_func dispatcher -----

def test_get_layout_func_returns_callable():
    cfg, mod = load_and_apply("tech_blue")
    fn = get_layout_func(cfg, mod, "cover")
    assert callable(fn)
    assert fn.__name__ == "make_cover"


def test_get_layout_func_quadrant_aliased():
    """quadrant 是 yaml 别名 · 实际跑 make_matrix_2x2"""
    cfg, mod = load_and_apply("tech_blue")
    fn = get_layout_func(cfg, mod, "quadrant")
    assert fn.__name__ == "make_matrix_2x2"


def test_get_layout_func_unimplemented_layout_raises():
    cfg, mod = load_and_apply("tech_blue")
    # pyramid 在 tech_blue 是 null
    with pytest.raises(ValueError) as e:
        get_layout_func(cfg, mod, "pyramid")
    assert "pyramid" in str(e.value)
    assert "tech_blue" in str(e.value)


def test_get_layout_func_template_golden_pyramid():
    """template_golden 实现 pyramid · 应找到 make_pyramid"""
    cfg, mod = load_and_apply("template_golden")
    fn = get_layout_func(cfg, mod, "pyramid")
    assert fn.__name__ == "make_pyramid"


# ----- list_themes -----

def test_list_themes_excludes_schema_and_legacy():
    names = list_themes()
    assert "tech_blue" in names
    assert "template_golden" in names
    assert "template_training" in names
    # _schema.yaml 以 _ 开头被排除
    assert "_schema" not in names
