"""builder/tier2.py —— tier2 Python theme make_<layout> dispatch。

负责:
- 找 theme 模块的 make_<layout> 函数
- 弹出 cross-cutting 字段(layout / source)后调用
- TypeError 时报"第 N 页 layout=X"友好错误
- 找不到 make_<layout> 时 raise LayoutNotFoundError 让 base.build_deck 走 tier3

不负责:source citation / footer —— base 集中处理。
"""
from __future__ import annotations

from types import ModuleType
from typing import Any

from pptx import Presentation


class LayoutNotFoundError(Exception):
    """Theme 模块缺 make_<layout> 函数。base.build_deck 接住后走 tier3 处理。"""

    def __init__(self, theme: ModuleType, layout: str, page_no: int):
        self.theme = theme
        self.layout = layout
        self.page_no = page_no
        super().__init__(
            f"第 {page_no} 页 layout={layout!r}: theme {theme.__name__!r} 无 make_{layout}"
        )


def render_tier2_slide(prs: Presentation, theme: ModuleType,
                        slide_def: dict[str, Any], page_no: int) -> None:
    """调 theme.make_<layout>(prs, **fields) 生成一页 slide。

    弹出 cross-cutting 字段(layout / source)避免传给 make_*。

    Args:
        prs: 目标 Presentation
        theme: theme module
        slide_def: deck_plan.slides[i] 单页 dict
        page_no: 1-indexed,用于报错时给用户定位

    Raises:
        LayoutNotFoundError: theme 没有对应 make_<layout> 函数
        ValueError: make_<layout> 接收字段不匹配(TypeError)
    """
    layout = slide_def["layout"]
    fn = getattr(theme, f"make_{layout}", None)
    if fn is None or not callable(fn):
        raise LayoutNotFoundError(theme, layout, page_no)

    # 弹出 cross-cutting 字段,不传给 make_* fn(避免 TypeError)
    fields = {k: v for k, v in slide_def.items() if k != "layout"}
    fields.pop("source", None)
    # 多模板 deck 诊断字段(plan 顶层 theme_spec 路由依据,make_* 不消费)
    fields.pop("chapter_index", None)
    fields.pop("effective_theme", None)

    try:
        fn(prs, **fields)
    except TypeError as e:
        raise ValueError(f"第 {page_no} 页 layout={layout}: {e}") from e
