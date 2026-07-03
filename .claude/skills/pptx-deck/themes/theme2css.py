"""themes/theme2css.py · ThemeConfig → CSS custom properties。

给 **html 轨**(HTML `<link>` global.css)+ **lark-whiteboard 轨**(SVG `<style>` 内嵌)
共享的视觉 token 派生。单一源:

    themes/<name>.yaml → _base.load_theme → ThemeConfig → render_css → :root { --var }

SVG 支持 `<style>` 内嵌 CSS,所以**同一份 CSS vars 喂 HTML + SVG**,三轨(pptx 用
apply_theme token / html+svg 用 CSS vars)视觉身份一致 —— 共享脊柱的 theme SSOT 落地。

CLI:
    python3 themes/theme2css.py tech_blue            # 打印 CSS 到 stdout
    python3 themes/theme2css.py tech_blue -o slides/global.css
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from themes import _base
from themes._base import ThemeConfig

# pt → px @96dpi(1pt = 1/72 inch · 96/72 = 4/3)
_PT2PX = 4.0 / 3.0
# inch → px @96dpi
_IN2PX = 96.0


def _to_hex(color: Any) -> str:
    """RGBColor / hex str → '#RRGGBB'。

    python-pptx RGBColor 的 str() 返回 6 位 hex(无 #);yaml 里是 '#0A52BF' 或 '0A52BF'。
    """
    s = str(color)
    return s if s.startswith("#") else f"#{s}"


def _kebab(key: str) -> str:
    """snake_case → kebab-case:`brand_primary` → `brand-primary`。"""
    return key.replace("_", "-")


# style.recipe 字段 → CSS var 名映射(短化)
_STYLE_MAP = {
    "radius_small": "--radius-sm",
    "radius_medium": "--radius-md",
    "radius_large": "--radius-lg",
    "gap_in": "--gap",
    "margin_in": "--margin",
}


def render_css_from_cfg(cfg: ThemeConfig) -> str:
    """从已加载的 ThemeConfig 生成 `:root[data-theme=...] { --var: ... }` CSS。

    消费方(html `<link>` / SVG `<style>`)按 data-theme 选择器 + var(--token) 取值。
    """
    lines: list[str] = [
        f"/* theme2css · {cfg.name} — {cfg.description}",
        "   由 themes/theme2css.py 从 ThemeConfig 派生;勿手改(改 themes/<name>.yaml 重生成)。 */",
        f':root[data-theme="{cfg.name}"] {{',
    ]

    # colors: 全量 emit(yaml 声明几个就出几个;brand_primary/dark/tint/accent + muted_*/gray_*)
    for key, val in cfg.colors.items():
        lines.append(f"  --{_kebab(key)}: {_to_hex(val)};")

    # fonts
    fonts = cfg.fonts
    lines.append(f'  --font-ea: {fonts.get("ea", "Microsoft YaHei")};')
    lines.append(f'  --font-latin: {fonts.get("latin", "Helvetica Neue")};')
    lines.append(f'  --font-num: {fonts.get("num", "Helvetica Neue")};')
    title_pt = int(fonts.get("title_size_pt", 28))
    body_pt = int(fonts.get("body_size_pt", 18))
    lines.append(f"  --title-size: {title_pt * _PT2PX:.2f}px;")
    lines.append(f"  --body-size: {body_pt * _PT2PX:.2f}px;")

    # style recipe + 数值 token
    style = cfg.style
    if style.get("recipe"):
        lines.append(f'  --recipe: {style["recipe"]};')
    for yaml_key, css_var in _STYLE_MAP.items():
        if yaml_key in style:
            val = float(style[yaml_key])
            if yaml_key.endswith("_in"):
                lines.append(f"  {css_var}: {val * _IN2PX:.1f}px;")  # inch → px
            else:
                lines.append(f"  {css_var}: {val:.3f};")  # ratio(unitless · 消费方乘 base)

    lines.append(f"  --mode: {cfg.mode};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_css(name: str, themes_dir: str | Path | None = None) -> str:
    """加载 theme <name> → 返回 CSS 字符串。"""
    cfg = _base.load_theme(name, themes_dir)
    return render_css_from_cfg(cfg)


def main() -> None:
    ap = argparse.ArgumentParser(description="themes/<name>.yaml → CSS custom properties")
    ap.add_argument("theme", help="theme name (e.g. tech_blue / template_training)")
    ap.add_argument("-o", "--output", help="写到文件(默认 stdout)")
    args = ap.parse_args()
    css = render_css(args.theme)
    if args.output:
        Path(args.output).write_text(css, encoding="utf-8")
        print(f"wrote {len(css)} bytes → {args.output}")
    else:
        print(css)


if __name__ == "__main__":
    main()
