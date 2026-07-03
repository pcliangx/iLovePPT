"""iLovePPT build.py —— deck_plan.json → .pptx + PNG 入口(thin entry)。

实现已拆分到 `builder/` 子包:
- builder/base.py  —— plan/theme load · build_deck orchestrator · render · ThemeSpec
- builder/tier2.py —— Python theme make_<layout> dispatch
- builder/tier3.py —— fallback / 错误兜底(目前 fail-loud,不 silent remap)

本文件保持入口稳定:
- CLI:`python3 build.py deck_plan.json [--no-render]`
- import:`from build import build_deck, load_plan, ...` 等公共 API 仍可用(re-export)
- monkeypatch:`monkeypatch.setattr(build, "_repo_templates_dir", ...)` 仍生效
  (本模块定义 _find_template / _list_available_templates / load_theme 时通过本
   模块自身命名空间查 _repo_templates_dir,让测试拦得到)

智能部分(brief→deck_plan / 视觉自检)由 Claude 按文档流程做,不在本文件。
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).parent
# 加 pptx-deck 自身 + pptx skill 到 sys.path(base.py 也做,这里冗余但向后兼容
# 直接 `python3 build.py` 跑的情况)
for _p in [str(HERE.parent / "pptx"), str(HERE)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 主要 API 直接 re-export(build_deck / load_plan / render 等无 monkeypatch 风险)
from builder.base import (  # noqa: E402
    FOOTERED_LAYOUTS,
    ThemeSpec,
    parse_theme,
    load_plan,
    build_deck,
    render,
    _extract_design_tokens,
    _extract_theme_from_pptx,
    _parse_red_line_words,
    _check_red_line_words,
    THEMES,
    PPTX_BASE_THEMES,
)
from builder import base as _base  # noqa: E402


# ===========================================================================
# 模板查找 API:本模块定义 wrapper,让 monkeypatch.setattr(build, "_repo_templates_dir", ...)
# 真正影响 build.load_theme / build._find_template 的调用链。
# (实现细节都在 _base 里,这里只是把入口拢到 build 命名空间。)
# ===========================================================================

def _repo_templates_dir() -> Path:
    """仓库根的 library/pptx-templates/_source/ 目录。委托给 builder.base。"""
    return _base._repo_templates_dir()


def _find_template(name: str, plan_dir: str | None = None) -> Path | None:
    """按短名查找 .pptx 模板。

    重要:这里**不**直接调 _base._find_template,而是重新实现一遍 lookup 逻辑,
    让 monkeypatch.setattr(build, "_repo_templates_dir", ...) 真正生效
    (历史测试依赖这个 contract)。
    """
    candidates: list[Path] = []
    if plan_dir:
        candidates.append(Path(plan_dir) / "templates" / f"{name}.pptx")
    candidates.append(_repo_templates_dir() / f"{name}.pptx")
    for p in candidates:
        if p.exists():
            return p
    return None


def _list_available_templates() -> list[str]:
    """返回模板 _source 目录下所有 .pptx 短名。委托 wrapper 让 monkeypatch 生效。"""
    tdir = _repo_templates_dir()
    if not tdir.exists():
        return []
    return sorted(p.stem for p in tdir.glob("*.pptx"))


def load_theme(theme_id: str, plan_dir: str | None = None) -> ModuleType:
    """解析 theme_id 到 theme 模块。

    跟 _base.load_theme 同样语义,但通过本模块的 _find_template / _list_available_templates
    走,让 monkeypatch.setattr(build, "_repo_templates_dir", ...) 也作用于
    `build.load_theme("nonexistent_theme")` 这种调用。
    """
    if theme_id in THEMES:
        return THEMES[theme_id]
    if str(theme_id).endswith(".pptx") or "/" in str(theme_id):
        path = Path(theme_id).expanduser()
        if not path.is_absolute() and plan_dir:
            path = (Path(plan_dir) / path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"theme .pptx 不存在: {path}")
        return _extract_theme_from_pptx(str(path))
    found = _find_template(theme_id, plan_dir)
    if found is not None:
        return _extract_theme_from_pptx(str(found))
    available = _list_available_templates()
    available_str = ", ".join(available) if available else "(空,把 .pptx 放进 library/pptx-templates/_source/)"
    raise ValueError(
        f"未知 theme: {theme_id!r}. "
        f"内置: tech_blue. "
        f"library/pptx-templates/_source/ 可用: {available_str}. "
        f"或直接给 .pptx 绝对/相对路径。"
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
