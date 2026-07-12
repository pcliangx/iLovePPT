"""iLovePPT build.py —— deck_plan.json → .pptx + PNG 入口(thin entry)。

实现已拆分到 `builder/` 子包:
- builder/base.py  —— plan/theme load · build_deck orchestrator · render · ThemeSpec
- builder/tier2.py —— Python theme make_<layout> dispatch
- builder/tier3.py —— fallback / 错误兜底(目前 fail-loud,不 silent remap)

本文件保持入口稳定:
- CLI:`python3 build.py deck_plan.json [--no-render]`
- import:`from build import build_deck, load_plan, ...` 等公共 API 仍可用(re-export)

智能部分(brief→deck_plan / 视觉自检)由 Claude 按文档流程做,不在本文件。
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).parent
# 加 pptx-deck 自身 + pptx skill 到 sys.path(base.py 也做,这里冗余但向后兼容
# 直接 `python3 build.py` 跑的情况)
for _p in [str(HERE.parent / "pptx"), str(HERE)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 全部 API 直接 re-export builder.base 的唯一实现。
# (历史上 _find_template / load_theme 在这里有一份为 monkeypatch 服务的重复
# 实现,但 build_deck 走的是 base 版,双份逻辑只会漂移;现无测试依赖该
# contract,删除重复,单实现收口 base。)
from builder.base import (  # noqa: E402
    FOOTERED_LAYOUTS,
    ThemeSpec,
    parse_theme,
    load_plan,
    load_theme,
    build_deck,
    render,
    _extract_design_tokens,
    _extract_theme_from_pptx,
    _parse_red_line_words,
    _check_red_line_words,
    _repo_templates_dir,
    _find_template,
    _list_available_templates,
    THEMES,
    PPTX_BASE_THEMES,
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


def main(argv: list[str]) -> None:
    """CLI entry: python3 build.py deck_plan.json [--no-render]."""
    if not argv:
        sys.exit("用法: python3 build.py deck_plan.json [--no-render]")
    plan_path = argv[0]
    do_render = "--no-render" not in argv
    plan = load_plan(plan_path)
    out = build_deck(plan)
    print(f"已生成 {out}")
    if do_render:
        render_dir = out.parent / (out.stem + "_render")
        pngs = render(out, render_dir)
        print(f"已渲染 {len(pngs)} 页 → {render_dir}")


if __name__ == "__main__":
    main(sys.argv[1:])
