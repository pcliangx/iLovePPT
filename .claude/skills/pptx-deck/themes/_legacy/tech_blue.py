"""themes._legacy.tech_blue — 向后兼容 compat shim。

# 用途
- 旧代码用 `from themes._legacy.tech_blue import BRAND_PRIMARY / FONT_CN` 仍可工作
- 新代码请用 `themes/_base.py:load_theme('tech_blue')` 加载 ThemeConfig
- shim re-export tech_blue.py 全部公开符号 + 暴露 helpers.py 的底层 token(BRAND_*/FONT_CN/...)

# 不变量
- 这个 shim 不能写实现 · 一切以 themes/tech_blue.py 为准 · 改色改字体改 yaml
"""
import sys
from pathlib import Path

# Path setup for direct import outside pytest
_HERE = Path(__file__).parent
_themes_dir = str(_HERE.parent)
_pptx_dir = str(_HERE.parent.parent.parent / "pptx")
for _p in (_themes_dir, _pptx_dir):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Re-export themes.tech_blue 全部公开符号
from themes.tech_blue import *  # noqa: F401, F403
from themes import tech_blue as _tb  # noqa: F401

# 也 re-export helpers.py 底层 token(向后兼容 · 兼容旧代码引用 BRAND_*)
from helpers import (  # noqa: F401
    FONT_CN,
    FONT_CN_DESIGN,
    FONT_EN,
    FONT_NUM,
    BRAND_PRIMARY,
    BRAND_DARK,
    BRAND_TINT,
    ACCENT,
    GRAY_50,
    GRAY_100,
    GRAY_300,
    GRAY_500,
    GRAY_700,
    GRAY_900,
    WHITE,
    BLACK,
    MUTED_BLUE,
    MUTED_SAND,
    MUTED_SAGE,
    MUTED_TERRA,
    MUTED_LAVENDER,
    MUTED_OCHRE,
    SLIDE_W,
    SLIDE_H,
)
