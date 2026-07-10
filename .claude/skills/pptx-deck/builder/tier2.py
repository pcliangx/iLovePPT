"""builder/tier2.py —— tier2 Python theme make_<layout> dispatch。

负责:
- 解析 layout → 渲染函数,优先级(SSOT 三层,见 CLAUDE.md):
    1. theme yaml layouts mapping(module._THEME_CONFIG · 含 alias,如
       quadrant → make_matrix_2x2;yaml 值为 null / 缺 key → 继续往下)
    2. module make_<layout>(legacy / .pptx 提取 theme 路径)
    3. helpers LayoutRegistry plugin 标准实现(theme-agnostic,调用时传 theme=module)
- 弹出 cross-cutting 字段(layout / source)后调用
- TypeError 时报"第 N 页 layout=X"友好错误
- 三层都没有时 raise LayoutNotFoundError 让 base.build_deck 走 tier3

不负责:source citation / footer —— base 集中处理。
"""
from __future__ import annotations

from types import ModuleType
from typing import Any, Callable

from pptx import Presentation

import helpers as _H


class LayoutNotFoundError(Exception):
    """Theme 模块缺 make_<layout> 函数。base.build_deck 接住后走 tier3 处理。"""

    def __init__(self, theme: ModuleType, layout: str, page_no: int):
        self.theme = theme
        self.layout = layout
        self.page_no = page_no
        super().__init__(
            f"第 {page_no} 页 layout={layout!r}: theme {theme.__name__!r} 无 make_{layout}"
        )


def resolve_layout_fn(theme: ModuleType,
                       layout: str) -> tuple[Callable[..., Any] | None, bool]:
    """按三层优先级解析 layout 渲染函数。

    Returns:
        (fn, is_plugin) · fn=None 表示三层都没找到(调用方走 tier3);
        is_plugin=True 表示来自 LayoutRegistry,调用时须传 theme=module。

    Raises:
        ValueError: yaml layouts 声明了函数名但 module 没有对应 callable(实现 bug,
                    不静默降级到 plugin —— yaml 声明即承诺)。
    """
    # 1. theme yaml layouts mapping(alias 在这层生效)
    cfg = getattr(theme, "_THEME_CONFIG", None)
    if cfg is not None:
        fn_name = cfg.layouts.get(layout)
        if fn_name:
            fn = getattr(theme, fn_name, None)
            if fn is None or not callable(fn):
                raise ValueError(
                    f"theme {cfg.name!r} yaml 声明 layouts.{layout}={fn_name!r},"
                    f"但 module {theme.__name__!r} 无 callable {fn_name}。"
                    f"修复:在 {theme.__file__} 补 def {fn_name}(...) 或改 yaml mapping。"
                )
            return fn, False
    # 2. module make_<layout>(legacy / extracted theme)
    fn = getattr(theme, f"make_{layout}", None)
    if fn is not None and callable(fn):
        return fn, False
    # 3. LayoutRegistry plugin 标准实现
    if _H.LayoutRegistry.has(layout):
        return _H.LayoutRegistry.get(layout), True
    return None, False


def render_tier2_slide(prs: Presentation, theme: ModuleType,
                        slide_def: dict[str, Any], page_no: int) -> None:
    """按 resolve_layout_fn 三层优先级渲染一页 slide。

    弹出 cross-cutting 字段(layout / source)避免传给 make_*。

    Args:
        prs: 目标 Presentation
        theme: theme module
        slide_def: deck_plan.slides[i] 单页 dict
        page_no: 1-indexed,用于报错时给用户定位

    Raises:
        LayoutNotFoundError: yaml / module / plugin 三层都无该 layout
        ValueError: make_<layout> 接收字段不匹配(TypeError)
    """
    layout = slide_def["layout"]
    fn, is_plugin = resolve_layout_fn(theme, layout)
    if fn is None:
        raise LayoutNotFoundError(theme, layout, page_no)

    # 弹出 cross-cutting 字段,不传给 make_* fn(避免 TypeError)
    fields = {k: v for k, v in slide_def.items() if k != "layout"}
    fields.pop("source", None)
    # 多模板 deck 诊断字段(plan 顶层 theme_spec 路由依据,make_* 不消费)
    fields.pop("chapter_index", None)
    fields.pop("effective_theme", None)

    try:
        if is_plugin:
            fn(prs, theme=theme, **fields)
        else:
            fn(prs, **fields)
    except TypeError as e:
        raise ValueError(f"第 {page_no} 页 layout={layout}: {e}") from e
