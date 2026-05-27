"""Layout plugin registry — auto-discover 机制核心。

每个 helpers/<layout>.py 用 @register_layout("<layout_type>") decorator 把自己
注册到全局 LayoutRegistry。helpers/__init__.py 自动 import 所有同目录模块,
触发 decorator 副作用,完成注册。

build.py 调用约定:
    from helpers import LayoutRegistry
    fn = LayoutRegistry.get("cards")
    fn(prs, theme=tech_blue, title="...", cards=[...])

设计要点:
- LayoutRegistry 是 class-level singleton(_layouts dict 在类上,不是实例上)。
  避免多次实例化丢注册。
- get() 失败 fail-loud:抛 KeyError + 列出所有已知 layout(便于排错)。
- register() 允许重复注册同名(后注册覆盖)— 用例:用户自定义 layout override 内置。
"""
from __future__ import annotations

from typing import Callable


class LayoutRegistry:
    """全局 layout 注册表。

    `_layouts` 是 class attribute(不是 instance),保证整个进程共享一份注册表。
    每个 helpers/<layout>.py 通过 `@register_layout("<name>")` 把 make_<layout>
    函数注册进来。
    """

    _layouts: dict[str, Callable] = {}

    @classmethod
    def register(cls, layout_type: str) -> Callable[[Callable], Callable]:
        """Decorator:注册 layout_type → fn。

        允许重复注册(后注册覆盖)。例:plugin override 内置:
            @register_layout("cover")   # override tech_blue 的 cover
            def make_cover(prs, ...): ...
        """
        def deco(fn: Callable) -> Callable:
            cls._layouts[layout_type] = fn
            return fn
        return deco

    @classmethod
    def get(cls, layout_type: str) -> Callable:
        """取注册的 make_<layout> 函数。未注册 → fail-loud 列出所有已知。"""
        if layout_type not in cls._layouts:
            known = sorted(cls._layouts.keys())
            raise KeyError(
                f"No layout plugin for {layout_type!r}. "
                f"Known {len(known)} layouts: {known}"
            )
        return cls._layouts[layout_type]

    @classmethod
    def has(cls, layout_type: str) -> bool:
        """是否已注册。"""
        return layout_type in cls._layouts

    @classmethod
    def all_layouts(cls) -> list[str]:
        """所有已注册的 layout_type 列表(sorted)。"""
        return sorted(cls._layouts.keys())

    @classmethod
    def clear(cls) -> None:
        """清空注册表(仅 test 用,正常代码不该调)。"""
        cls._layouts.clear()


# 暴露给 helpers/<layout>.py:`from .._base import register_layout`
register_layout = LayoutRegistry.register
