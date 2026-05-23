"""matplotlib SSOT 配置 —— 让数据图与 deck 视觉一致。

用法:
    from matplotlib_rc import apply_iloveppt_style
    apply_iloveppt_style()
    # ... 后续 plt.plot / plt.bar 都会自动用 BRAND_* 调色板 + Microsoft YaHei
    plt.savefig("out.png", dpi=200, bbox_inches="tight")

色板与字体源自 [[pptx]] helpers.py(SSOT);改色 / 改字体 → 改 helpers.py
后回过来 re-export 本模块的常量。
"""
from __future__ import annotations

import sys
from pathlib import Path

# 复用 helpers.py 的色 / 字体常量(SSOT)
_pptx_path = str(Path(__file__).parent.parent / "pptx")
if _pptx_path not in sys.path:
    sys.path.insert(0, _pptx_path)
import helpers as H  # noqa: E402


# ============================================================================
# 调色板(从 helpers.py 抄出 hex,供 matplotlib 使用)
# ============================================================================

def _hex(c) -> str:
    """RGBColor → '#RRGGBB' 字符串"""
    return f"#{c[0]:02X}{c[1]:02X}{c[2]:02X}"


PALETTE = [
    _hex(H.BRAND_PRIMARY),   # #0A52BF
    _hex(H.ACCENT),           # #007A6D
    _hex(H.BRAND_DARK),       # #0B2A4A
    _hex(H.GRAY_700),         # #4A4A4A
    _hex(H.GRAY_500),         # #6F6F6F
    _hex(H.GRAY_300),         # #D9D9D9
]


# ============================================================================
# rcParams 模板
# ============================================================================

RC_PARAMS = {
    # 字体
    "font.family":        "sans-serif",
    "font.sans-serif":    ["Microsoft YaHei", "Source Han Sans CN",
                           "PingFang SC", "Helvetica Neue", "Arial"],
    "axes.unicode_minus": False,  # 中文环境下负号显示

    # 字号(与 deck body=18 / 标题=32 对齐 — chart 整体小 1 档,因为嵌入后会缩放)
    "font.size":         14,
    "axes.titlesize":    18,
    "axes.labelsize":    14,
    "xtick.labelsize":   12,
    "ytick.labelsize":   12,
    "legend.fontsize":   12,
    "figure.titlesize":  20,

    # 配色
    "axes.prop_cycle": __import__("cycler").cycler(color=PALETTE),

    # 网格 / 边框(BCG 风格 — 极简,只留必要边框)
    "axes.grid":      True,
    "grid.color":     _hex(H.GRAY_300),
    "grid.linewidth": 0.5,
    "grid.linestyle": "-",
    "axes.edgecolor":  _hex(H.GRAY_500),
    "axes.linewidth":  0.8,
    "axes.spines.top":   False,    # 去顶边框
    "axes.spines.right": False,    # 去右边框

    # 图例
    "legend.frameon":   False,    # 图例无边框
    "legend.loc":       "best",

    # 输出
    "figure.dpi":     200,       # 嵌入 PPT 时不糊
    "savefig.dpi":    200,
    "savefig.bbox":   "tight",
    "savefig.facecolor": "white",
}


def apply_iloveppt_style() -> None:
    """把 RC_PARAMS 装到当前 matplotlib 全局配置。

    应在创建任何 Figure 之前调用。重复调用幂等。
    """
    import matplotlib
    matplotlib.rcParams.update(RC_PARAMS)


__all__ = ["PALETTE", "RC_PARAMS", "apply_iloveppt_style"]
