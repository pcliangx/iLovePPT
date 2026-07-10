"""themes/_base.py mode(light|dark) + style 风格配方测试。

覆盖:默认值向后兼容 / dark+pill 解析 / 单值覆盖 / 非法值 fail-loud / apply_theme 推常量。
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

_DECK_DIR = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "pptx-deck"
if str(_DECK_DIR) not in sys.path:
    sys.path.insert(0, str(_DECK_DIR))

from themes._base import STYLE_RECIPES, apply_theme, load_theme  # noqa: E402

MINIMAL_YAML = """\
name: {name}
description: "mode/style 测试夹具"
colors:
  brand_primary: "#0A52BF"
  brand_dark: "#0B2A4A"
  brand_tint: "#E6F0FC"
  accent: "#007A6D"
fonts:
  ea: "Microsoft YaHei"
layouts:
  cover: make_cover
{extra}"""


def _write_theme(tmp_path: Path, name: str, extra: str = "") -> Path:
    (tmp_path / f"{name}.yaml").write_text(
        MINIMAL_YAML.format(name=name, extra=extra), encoding="utf-8"
    )
    return tmp_path


def test_defaults_backward_compatible(tmp_path):
    d = _write_theme(tmp_path, "plain")
    cfg = load_theme("plain", themes_dir=d)
    assert cfg.mode == "light"
    assert cfg.style["recipe"] == "soft"
    assert cfg.style["radius_medium"] == STYLE_RECIPES["soft"]["radius_medium"] == 0.05


def test_builtin_themes_still_load():
    for name in ("tech_blue", "template_golden", "template_training"):
        cfg = load_theme(name)
        assert cfg.mode in ("light", "dark")
        assert cfg.style["recipe"] in STYLE_RECIPES


def test_dark_pill_with_override(tmp_path):
    d = _write_theme(tmp_path, "night", extra=(
        "mode: dark\n"
        "style:\n"
        "  recipe: pill\n"
        "  radius_medium: 0.25\n"
    ))
    cfg = load_theme("night", themes_dir=d)
    assert cfg.mode == "dark"
    assert cfg.style["recipe"] == "pill"
    assert cfg.style["radius_medium"] == 0.25          # 单值覆盖生效
    assert cfg.style["radius_large"] == STYLE_RECIPES["pill"]["radius_large"]  # 其余按配方


def test_invalid_mode_and_recipe_failloud(tmp_path):
    d = _write_theme(tmp_path, "badmode", extra="mode: midnight\n")
    with pytest.raises(ValueError, match="light | dark"):
        load_theme("badmode", themes_dir=d)

    d2 = _write_theme(tmp_path, "badrecipe", extra="style:\n  recipe: chamfer\n")
    with pytest.raises(ValueError, match="recipe"):
        load_theme("badrecipe", themes_dir=d2)

    d3 = _write_theme(tmp_path, "badnum", extra="style:\n  gap_in: wide\n")
    with pytest.raises(ValueError, match="不是数值"):
        load_theme("badnum", themes_dir=d3)


def test_apply_theme_pushes_constants(tmp_path):
    d = _write_theme(tmp_path, "night2", extra="mode: dark\nstyle:\n  recipe: rounded\n")
    cfg = load_theme("night2", themes_dir=d)
    mod = types.ModuleType("fake_theme_module")
    apply_theme(mod, cfg)
    assert mod.THEME_MODE == "dark"
    assert mod.STYLE_RECIPE == "rounded"
    assert mod.STYLE_RADIUS_MEDIUM == STYLE_RECIPES["rounded"]["radius_medium"]
    assert mod.STYLE_GAP_IN == STYLE_RECIPES["rounded"]["gap_in"]
    assert mod.STYLE_MARGIN_IN == STYLE_RECIPES["rounded"]["margin_in"]
