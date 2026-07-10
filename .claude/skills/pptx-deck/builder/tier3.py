"""builder/tier3.py —— tier3 fallback / 错误兜底。

当前策略:**fail-loud**(不 silent remap 到 bullet_list 等掩盖问题)。
让 author / critic / 用户立刻看到错配,而不是等 audience 阶段才暴露。

未来可扩展(本任务不实现):
- "default to bullet_list when content fits" 兜底
- "auto-suggest closest layout" 用 levenshtein 距离推荐

负责:
- handle_missing_layout:tier2 没找到 make_<layout> 时 base 派发到这里
"""
from __future__ import annotations

from types import ModuleType
from typing import Any

from .tier2 import LayoutNotFoundError


def handle_missing_layout(theme: ModuleType, slide_def: dict[str, Any],
                            page_no: int, original_err: LayoutNotFoundError) -> None:
    """Theme 没找到 make_<layout> 函数的 fallback。

    当前实现:fail-loud,raise ValueError 带详细 fix 指引。

    Args:
        theme: theme module
        slide_def: deck_plan.slides[i]
        page_no: 1-indexed
        original_err: tier2.render_tier2_slide raise 的 LayoutNotFoundError
    """
    layout = slide_def["layout"]
    available = sorted(
        name[len("make_"):] for name in dir(theme)
        if name.startswith("make_") and callable(getattr(theme, name))
    )
    theme_stem = theme.__name__.replace("extracted_", "")
    raise ValueError(
        f"第 {page_no} 页 layout={layout!r}: theme {theme.__name__!r} 无 make_{layout}。\n"
        f"2 个 fix 选项:\n"
        f"  ① 让 author 改 layout 到 theme 支持清单:{available}\n"
        f"  ② 主线程实现 themes/{theme_stem}.py 的 make_{layout} 函数"
    ) from original_err
