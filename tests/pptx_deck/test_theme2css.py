"""theme2css · ThemeConfig → CSS custom properties 派生测试。"""
from themes._base import load_theme
from themes.theme2css import render_css, render_css_from_cfg


def test_render_css_tech_blue_tokens():
    css = render_css("tech_blue")
    assert ':root[data-theme="tech_blue"]' in css
    # colors(brand_primary = #0A52BF)
    assert "--brand-primary: #0A52BF;" in css
    # fonts · ea = Microsoft YaHei(#1 不变量)
    assert "--font-ea: Microsoft YaHei;" in css
    # pt → px(28pt title · 28 * 4/3 = 37.33px)
    assert "--title-size: 37.33px;" in css
    # mode
    assert "--mode: light;" in css


def test_render_css_template_training_orange():
    """training 橙红 #EF5938 来自 yaml · CSS 也要带这个色(不是 tech_blue 的蓝)。"""
    css = render_css("template_training")
    assert "--brand-primary: #EF5938;" in css


def test_render_css_from_cfg_kebab_and_muted():
    """muted_blue → --muted-blue(kebab);style recipe token 出现。"""
    cfg = load_theme("tech_blue")
    css = render_css_from_cfg(cfg)
    if "muted_blue" in cfg.colors:
        assert "--muted-blue:" in css
    # recipe 是 soft → --recipe: soft
    assert "--recipe: soft;" in css


def test_render_css_consistent_across_runs():
    """同 theme 两次调用结果完全一致(deterministic · 可入 git/缓存)。"""
    a = render_css("tech_blue")
    b = render_css("tech_blue")
    assert a == b
