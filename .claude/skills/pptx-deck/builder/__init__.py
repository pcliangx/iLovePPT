"""iLovePPT builder 子包 —— build.py 拆分后的实现层。

模块布局:
    base.py   —— 共享:plan load / theme load / Presentation init / build_deck orchestrator
                 / red_line_words 4th-line check / render / ThemeSpec parser
    tier1.py  —— tier1 模板 slide 复用(cross-pptx deep-copy)
                 + drop_rel + shape-removal + placeholder_map 应用
    tier2.py  —— tier2 Python theme 重画(make_<layout> dispatch)
    tier3.py  —— tier3 fallback(layout 不存在 / 错误兜底)

公共 API 由 base.py 导出,直接 `from builder import build_deck, load_plan, ...`。
"""

from .base import (
    # 数据 schema
    FOOTERED_LAYOUTS,
    ThemeSpec,
    parse_theme,
    # 主入口
    load_plan,
    load_theme,
    build_deck,
    render,
    # 内部 helper(测试用)
    _extract_design_tokens,
    _extract_theme_from_pptx,
    _repo_templates_dir,
    _find_template,
    _list_available_templates,
    _parse_red_line_words,
    _check_red_line_words,
)

__all__ = [
    "FOOTERED_LAYOUTS",
    "ThemeSpec",
    "parse_theme",
    "load_plan",
    "load_theme",
    "build_deck",
    "render",
    "_extract_design_tokens",
    "_extract_theme_from_pptx",
    "_repo_templates_dir",
    "_find_template",
    "_list_available_templates",
    "_parse_red_line_words",
    "_check_red_line_words",
]
