"""iLovePPT 几何原语 —— 主题无关的区域切分。

Box 是 (x, y, w, h),EMU 单位。原语把一个 Box 切成子 Box,供 theme 的
make_* 函数定位内容。纯函数、无 pptx 渲染依赖,可确定性单测。
"""
from dataclasses import dataclass

from pptx.util import Emu, Inches, Length

import helpers as H


@dataclass(frozen=True)
class Box:
    """一块矩形区域。x/y/w/h 均为 EMU（python-pptx Length）。"""
    x: Length
    y: Length
    w: Length
    h: Length


def content_region() -> Box:
    """header 与 footer 之间的内容区（基于 helpers.py 的边距常量）。"""
    return Box(
        x=H.LEFT_MARGIN,
        y=H.HEADER_BOTTOM,
        w=Emu(H.SLIDE_W - H.LEFT_MARGIN - H.RIGHT_MARGIN),
        h=Emu(H.FOOTER_TOP - H.HEADER_BOTTOM),
    )


def columns(box: Box, n: int, gap: Length = Inches(0.3)) -> list[Box]:
    """把 box 横切成 n 等宽列,列间留 gap。"""
    col_w = Emu(int((box.w - gap * (n - 1)) / n))
    return [
        Box(x=Emu(box.x + i * (col_w + gap)), y=Emu(int(box.y)), w=col_w, h=Emu(int(box.h)))
        for i in range(n)
    ]


def rows(box: Box, n: int, gap: Length = Inches(0.2)) -> list[Box]:
    """把 box 纵切成 n 等高行,行间留 gap。"""
    row_h = Emu(int((box.h - gap * (n - 1)) / n))
    return [
        Box(x=Emu(int(box.x)), y=Emu(box.y + i * (row_h + gap)), w=Emu(int(box.w)), h=row_h)
        for i in range(n)
    ]


def stack(box: Box, heights: list[Length], gap: Length = Inches(0.2),
          align: str = "middle") -> list[Box]:
    """按给定块高纵向排布,整组在 box 内对齐。align: top|middle|bottom。

    若块总高超过 box.h,内容会溢出 box 边界（向上）——由调用方负责确保能放下。
    """
    if not heights:
        return []
    total = sum(heights) + gap * (len(heights) - 1)
    if align == "top":
        cur = box.y
    elif align == "bottom":
        cur = box.y + box.h - total
    else:  # middle
        cur = box.y + (box.h - total) // 2
    out: list[Box] = []
    for hgt in heights:
        out.append(Box(x=Emu(int(box.x)), y=Emu(int(cur)), w=Emu(int(box.w)), h=Emu(int(hgt))))
        cur = cur + hgt + gap
    return out


def split(box: Box, ratio: float, gap: Length = Inches(0.3)) -> tuple[Box, Box]:
    """按 ratio 把 box 横切成左右两块（ratio = 左块占可用宽的比例）。"""
    left_w = Emu(int((box.w - gap) * ratio))
    right_w = Emu(box.w - gap - left_w)
    left = Box(x=box.x, y=Emu(int(box.y)), w=left_w, h=Emu(int(box.h)))
    right = Box(x=Emu(box.x + left_w + gap), y=Emu(int(box.y)), w=right_w, h=Emu(int(box.h)))
    return left, right


def inset(box: Box, dx: Length, dy: Length) -> Box:
    """四周各内缩 dx（左右）/ dy（上下）。"""
    return Box(
        x=Emu(box.x + dx), y=Emu(box.y + dy),
        w=Emu(box.w - 2 * dx), h=Emu(box.h - 2 * dy),
    )
