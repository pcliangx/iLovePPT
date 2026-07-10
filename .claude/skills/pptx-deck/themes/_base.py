"""iLovePPT pptx-deck · themes/_base.py — theme yaml 加载 + 调度。

# 设计
- yaml 是 design token + layout mapping 的 SSOT(user 想自定义品牌色 / 字体只改 yaml)
- Python `.py` 仍提供 make_<layout> 渲染函数(rendering 逻辑无法 yaml 化)
- 本文件提供三个公开 API:
    - `load_theme(name) -> ThemeConfig`:加载 themes/<name>.yaml + 解析 module_path
    - `apply_theme(module, theme_config)`:把 yaml token 推到 module 常量
        (FONT_HEADER / PRIMARY / PRIMARY_DEEP / ... · 等价 build.py `_extract_theme_from_pptx`)
    - `get_layout_func(theme_config, layout_type) -> callable`:按 layouts mapping 返回 make_<layout> 引用

# 调用者
- Agent A 拆 build.py 后,builder/base.py 用本文件三个 API · 替换原 `from themes.tech_blue import *`
- 主线程跑 build.py 直接调 `load_theme('tech_blue')` 拿 ThemeConfig
- 老代码 `from themes import tech_blue` 继续工作(yaml 不影响 module 加载)

# 不变量
- 默认中文字体 `Microsoft YaHei` · yaml 不写 ea 字段也 fallback 到此值
- 17 enum + 历史 layout 名 cherry-pick · build.py fail-loud 缺失 make_<layout>
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import yaml
from pptx.dml.color import RGBColor

# Path setup for direct import outside pytest
_HERE = Path(__file__).parent
_pptx_dir = str(_HERE.parent.parent / "pptx")
if _pptx_dir not in sys.path:
    sys.path.insert(0, _pptx_dir)

import helpers as H  # noqa: E402


# ============================================================================
# 0. 风格配方(借鉴 mavis pptx design-system 的 Sharp/Soft/Rounded/Pill 参数化)
# ============================================================================
# 单位适配本仓库:radius_* 是 rounded-rect adjustments[0] 比例(0-0.5 · 见 visual-qa
# "卡片圆角"项),gap_in / margin_in 是 inches。yaml `style.recipe` 选档,单值可覆盖。

STYLE_RECIPES: dict[str, dict[str, float]] = {
    # 数据密集 / 财报 · 直角紧凑
    "sharp":   {"radius_small": 0.0,  "radius_medium": 0.02, "radius_large": 0.03,
                "gap_in": 0.15, "margin_in": 0.55},
    # 默认 · 企业通用(radius_medium=0.05 即原 visual-qa 写死的上限)
    "soft":    {"radius_small": 0.03, "radius_medium": 0.05, "radius_large": 0.08,
                "gap_in": 0.25, "margin_in": 0.55},
    # 产品 / 营销 · 大圆角松弛
    "rounded": {"radius_small": 0.08, "radius_medium": 0.12, "radius_large": 0.20,
                "gap_in": 0.35, "margin_in": 0.60},
    # 发布会 / 品牌 · 胶囊大留白
    "pill":    {"radius_small": 0.20, "radius_medium": 0.30, "radius_large": 0.50,
                "gap_in": 0.45, "margin_in": 0.70},
}

_STYLE_KEYS = ("radius_small", "radius_medium", "radius_large", "gap_in", "margin_in")


# ============================================================================
# 1. ThemeConfig dataclass
# ============================================================================

@dataclass
class ThemeConfig:
    """单 theme 的完整配置 · 从 themes/<name>.yaml 加载。

    Attributes:
        name: theme id(= yaml 文件名)
        description: 一句话描述
        colors: dict[str, RGBColor] · 已转好的 RGBColor object(yaml 里是 hex 字符串)
        fonts: dict[str, Any] · ea/latin/num/title_size_pt/body_size_pt
        layouts: dict[str, str | None] · layout_type → make_<func> 函数名
                                          None 表示该 theme 不实现
        implementation: dict · tier1/tier2/tier3_fallback/module_path/source_pptx
        assets: dict[str, str] · 模板独有资产(如 team_illustration 路径)· 可选
        mode: "light"(default) | "dark" · 暗色模板语义声明(dark 时 brand_tint 作深色
              卡片底 · 文字用浅色;消费方:extractor 记录 / visual-qa 对照 / layout 读 THEME_MODE)
        style: dict · 风格配方(recipe + radius_*/gap_in/margin_in · 见 STYLE_RECIPES)
               已按 recipe 默认值补全,直接读数值即可
        _yaml_path: 加载的 yaml 文件路径(debug 用)
    """
    name: str
    description: str = ""
    colors: dict[str, RGBColor] = field(default_factory=dict)
    fonts: dict[str, Any] = field(default_factory=dict)
    layouts: dict[str, str | None] = field(default_factory=dict)
    implementation: dict[str, Any] = field(default_factory=dict)
    assets: dict[str, str] = field(default_factory=dict)
    mode: str = "light"
    style: dict[str, Any] = field(default_factory=lambda: {"recipe": "soft", **STYLE_RECIPES["soft"]})
    _yaml_path: str | None = None

    @property
    def module_path(self) -> str:
        """Python module path(默认 themes/<name>.py · 可 yaml 改 _legacy/<name>.py)"""
        return self.implementation.get("module_path", self.name)

    @property
    def tier1(self) -> bool:
        return bool(self.implementation.get("tier1", False))

    @property
    def tier2(self) -> bool:
        return bool(self.implementation.get("tier2", True))

    @property
    def tier3_fallback(self) -> str:
        return self.implementation.get("tier3_fallback", "tech_blue")

    @property
    def source_pptx(self) -> str | None:
        return self.implementation.get("source_pptx")


# ============================================================================
# 2. yaml loader
# ============================================================================

def _hex2rgb(hex_str: str) -> RGBColor:
    """`#0A52BF` / `0A52BF` → RGBColor"""
    s = hex_str.strip().lstrip("#")
    if len(s) != 6:
        raise ValueError(f"yaml color 非 6 位 hex: {hex_str!r}")
    return RGBColor(int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def load_theme(name: str, themes_dir: str | Path | None = None) -> ThemeConfig:
    """加载 themes/<name>.yaml → ThemeConfig。

    Args:
        name: theme id · 跟 yaml 文件名一致(不带 .yaml 后缀)
        themes_dir: themes 目录路径 · 默认本文件所在目录

    Raises:
        FileNotFoundError: yaml 文件不存在
        ValueError: yaml schema 不合规(缺 name / fonts.ea 等)
    """
    base = Path(themes_dir) if themes_dir else _HERE
    yaml_path = base / f"{name}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(
            f"theme yaml 不存在: {yaml_path}. "
            f"内置 theme: tech_blue / template_golden / template_training. "
            f"自定义 theme:在 themes/<name>.yaml 写一份(参考 themes/_schema.yaml)。"
        )
    with yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # 必填校验
    if not isinstance(data, dict):
        raise ValueError(f"{yaml_path}: yaml 顶层必须是 dict")
    if not data.get("name"):
        raise ValueError(f"{yaml_path}: 缺 name 字段")
    if data["name"] != name:
        raise ValueError(
            f"{yaml_path}: name 字段 {data['name']!r} 跟文件名 {name!r} 不符"
        )

    fonts = data.get("fonts") or {}
    if not fonts.get("ea"):
        raise ValueError(
            f"{yaml_path}: fonts.ea 必填(中文字体不变量 · default 'Microsoft YaHei')"
        )

    # colors: hex str → RGBColor
    colors_raw = data.get("colors") or {}
    colors: dict[str, RGBColor] = {}
    for key, val in colors_raw.items():
        if val is None:
            continue
        try:
            colors[key] = _hex2rgb(val)
        except (ValueError, AttributeError) as e:
            raise ValueError(
                f"{yaml_path}: colors.{key}={val!r} 不是合法 hex 色"
            ) from e

    # required 4 件套
    for req in ("brand_primary", "brand_dark", "brand_tint", "accent"):
        if req not in colors:
            raise ValueError(
                f"{yaml_path}: colors.{req} 必填(brand_primary/brand_dark/"
                f"brand_tint/accent 都得有)"
            )

    # fonts default
    fonts_clean: dict[str, Any] = {
        "ea": fonts["ea"],
        "latin": fonts.get("latin", "Helvetica Neue"),
        "num": fonts.get("num", "Helvetica Neue"),
        "title_size_pt": int(fonts.get("title_size_pt", 28)),
        "body_size_pt": int(fonts.get("body_size_pt", 18)),
    }

    # mode(可选 · 默认 light)
    mode = str(data.get("mode") or "light").lower()
    if mode not in ("light", "dark"):
        raise ValueError(f"{yaml_path}: mode 只能是 light | dark,got {mode!r}")

    # style 配方(可选 · 默认 soft · 单值覆盖)
    style_raw = data.get("style") or {}
    if not isinstance(style_raw, dict):
        raise ValueError(f"{yaml_path}: style 必须是 dict(recipe + 可选单值覆盖)")
    recipe = str(style_raw.get("recipe") or "soft").lower()
    if recipe not in STYLE_RECIPES:
        raise ValueError(
            f"{yaml_path}: style.recipe 只能是 {' | '.join(STYLE_RECIPES)},got {recipe!r}"
        )
    style: dict[str, Any] = {"recipe": recipe, **STYLE_RECIPES[recipe]}
    for key in _STYLE_KEYS:
        if style_raw.get(key) is not None:
            try:
                style[key] = float(style_raw[key])
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"{yaml_path}: style.{key}={style_raw[key]!r} 不是数值"
                ) from e

    return ThemeConfig(
        name=data["name"],
        description=data.get("description", ""),
        colors=colors,
        fonts=fonts_clean,
        layouts=dict(data.get("layouts") or {}),
        implementation=dict(data.get("implementation") or {}),
        assets=dict(data.get("assets") or {}),
        mode=mode,
        style=style,
        _yaml_path=str(yaml_path),
    )


def list_themes(themes_dir: str | Path | None = None) -> list[str]:
    """列 themes/ 下所有 *.yaml(去 _schema · _legacy)"""
    base = Path(themes_dir) if themes_dir else _HERE
    out: list[str] = []
    for p in sorted(base.glob("*.yaml")):
        if p.stem.startswith("_"):
            continue
        out.append(p.stem)
    return out


# ============================================================================
# 3. apply_theme — yaml token → module 常量
# ============================================================================

def _resolve_module(module_path: str) -> ModuleType:
    """按 module_path 加载 Python module。

    支持两种形式:
    - 简单 module 名(`tech_blue`)→ from themes import tech_blue
    - 子包(`_legacy.tech_blue`)→ from themes._legacy import tech_blue

    带 `.` 视为 dotted import path(themes.<dotted>)。
    """
    full = f"themes.{module_path}" if "." not in module_path or not module_path.startswith("themes.") else module_path
    if not full.startswith("themes."):
        full = f"themes.{module_path}"
    return importlib.import_module(full)


def apply_theme(module: ModuleType, theme_config: ThemeConfig) -> None:
    """把 ThemeConfig 的 token 推到 Python module · 覆盖常量。

    映射规则(等价 build.py 老 `_extract_theme_from_pptx`):
    - colors.brand_primary  → module.PRIMARY
    - colors.brand_dark     → module.PRIMARY_DEEP
    - colors.brand_tint     → module.PRIMARY_TINT
    - colors.accent         → module.ACCENT
    - colors.<其他>          → module.<UPPER>(如 muted_blue → MUTED_BLUE)
    - fonts.ea              → module.FONT_HEADER + module.FONT_BODY
    - fonts.latin           → module.FONT_EN(若 module 有 FONT_EN 字段)
    - fonts.num             → module.FONT_NUM
    - fonts.title_size_pt   → module.TITLE_SIZE_PT
    - fonts.body_size_pt    → module.BODY_SIZE_PT
    - mode                  → module.THEME_MODE("light" | "dark")
    - style.*               → module.STYLE_RECIPE / STYLE_RADIUS_* / STYLE_GAP_IN / STYLE_MARGIN_IN

    幂等:多次 apply 同一个 ThemeConfig 不变。
    """
    # 主色 4 件套
    mapping = {
        "brand_primary": "PRIMARY",
        "brand_dark": "PRIMARY_DEEP",
        "brand_tint": "PRIMARY_TINT",
        "accent": "ACCENT",
    }
    for yaml_key, mod_attr in mapping.items():
        if yaml_key in theme_config.colors:
            setattr(module, mod_attr, theme_config.colors[yaml_key])

    # 其他色(muted_* / light_blue / etc)→ module.UPPER
    for yaml_key, rgb in theme_config.colors.items():
        if yaml_key in mapping:
            continue
        setattr(module, yaml_key.upper(), rgb)

    # 字体
    setattr(module, "FONT_HEADER", theme_config.fonts["ea"])
    setattr(module, "FONT_BODY", theme_config.fonts["ea"])
    setattr(module, "FONT_NUM", theme_config.fonts["num"])
    # FONT_EN 是 helpers.py 风格 · 部分 theme 用 · 兼容设置
    if hasattr(module, "FONT_EN"):
        setattr(module, "FONT_EN", theme_config.fonts["latin"])

    # 字号阶梯
    setattr(module, "TITLE_SIZE_PT", theme_config.fonts["title_size_pt"])
    setattr(module, "BODY_SIZE_PT", theme_config.fonts["body_size_pt"])

    # 模式 + 风格配方(layout 渐进读取 · 未读取的 layout 行为不变)
    setattr(module, "THEME_MODE", theme_config.mode)
    setattr(module, "STYLE_RECIPE", theme_config.style["recipe"])
    for key in _STYLE_KEYS:
        setattr(module, f"STYLE_{key.upper()}", theme_config.style[key])


def load_and_apply(name: str,
                    themes_dir: str | Path | None = None
                    ) -> tuple[ThemeConfig, ModuleType]:
    """一步加载 ThemeConfig + module + apply token。

    Returns:
        (theme_config, module) tuple · module 已 apply 过 token。
    """
    cfg = load_theme(name, themes_dir=themes_dir)
    mod = _resolve_module(cfg.module_path)
    apply_theme(mod, cfg)
    return cfg, mod


# ============================================================================
# 4. dispatcher — get_layout_func
# ============================================================================

def get_layout_func(theme_config: ThemeConfig,
                     module: ModuleType,
                     layout_type: str) -> Callable[..., Any]:
    """按 layouts mapping 返回 make_<layout> 函数引用。

    Args:
        theme_config: load_theme() 返回值
        module: 已 apply_theme() 的 module(get_layout_func 不再改 module)
        layout_type: deck_plan slide.layout 字段(如 'cover' / 'compare' / 'pyramid')

    Returns:
        callable · 实际签名是 make_<layout>(prs, ...kwargs)

    Raises:
        ValueError: yaml 没声明这 layout(layouts[<layout>] is None or 缺)
        AttributeError: yaml 声明了但 module 没对应 make_<func>(实现 bug)
    """
    fn_name = theme_config.layouts.get(layout_type)
    if fn_name is None:
        # 列已支持的 layout 帮排错
        available = sorted(k for k, v in theme_config.layouts.items() if v)
        raise ValueError(
            f"theme {theme_config.name!r} 未实现 layout {layout_type!r}。"
            f"已支持:{available}。"
            f"修复:① author 改 layout · ② yaml 加 {layout_type!r} → make_<func> 映射"
            f" · ③ 用 tier3_fallback={theme_config.tier3_fallback!r} 兜底。"
        )
    fn = getattr(module, fn_name, None)
    if fn is None or not callable(fn):
        raise AttributeError(
            f"theme {theme_config.name!r} yaml 声明 layouts.{layout_type}={fn_name!r}"
            f" · 但 module {module.__name__!r} 无 callable {fn_name}。"
            f"修复:在 {module.__file__} 补 def {fn_name}(...)"
        )
    return fn


# ============================================================================
# 5. CLI smoke test(直接跑 python _base.py tech_blue 验证)
# ============================================================================

if __name__ == "__main__":
    # 直接运行时需把 pptx-deck dir 加进 sys.path · 让 `themes` 作为 top-level package
    _deck_dir = str(_HERE.parent)
    if _deck_dir not in sys.path:
        sys.path.insert(0, _deck_dir)
    target = sys.argv[1] if len(sys.argv) > 1 else "tech_blue"
    print(f"加载 theme: {target}")
    cfg, mod = load_and_apply(target)
    print(f"  name:        {cfg.name}")
    print(f"  description: {cfg.description}")
    print(f"  colors:      {sorted(cfg.colors.keys())}")
    print(f"  fonts.ea:    {cfg.fonts['ea']}")
    print(f"  module:      {mod.__name__}")
    print(f"  module.PRIMARY:      {mod.PRIMARY}")
    print(f"  module.FONT_HEADER:  {mod.FONT_HEADER}")
    layouts_impl = sorted(k for k, v in cfg.layouts.items() if v)
    print(f"  layouts (impl):      {layouts_impl}")
    for lt in ("cover", "cards", "summary"):
        try:
            fn = get_layout_func(cfg, mod, lt)
            print(f"  get_layout_func({lt!r}): {fn.__name__}")
        except (ValueError, AttributeError) as e:
            print(f"  get_layout_func({lt!r}) FAILED: {e}")
