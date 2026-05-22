"""layout.py 几何原语单测——纯函数,确定性,断言坐标。"""
from pptx.util import Emu, Inches
import layout as L


def test_box_fields():
    b = L.Box(x=Inches(1), y=Inches(2), w=Inches(3), h=Inches(4))
    assert b.x == Inches(1) and b.w == Inches(3)


def test_content_region_inside_slide():
    r = L.content_region()
    assert r.x > 0 and r.y > 0
    assert r.x + r.w <= Inches(13.333) + 1
    assert r.y + r.h <= Inches(7.5) + 1


def test_columns_count_and_widths_equal():
    box = L.Box(Inches(0), Inches(0), Inches(12), Inches(6))
    cols = L.columns(box, 3, gap=Inches(0))
    assert len(cols) == 3
    assert cols[0].w == cols[1].w == cols[2].w
    assert abs((cols[0].w + cols[1].w + cols[2].w) - Inches(12)) < 100


def test_columns_respects_gap_and_order():
    box = L.Box(Inches(0), Inches(0), Inches(10), Inches(6))
    cols = L.columns(box, 2, gap=Inches(1))
    assert cols[0].x == Inches(0)
    assert abs(cols[1].x - (cols[0].x + cols[0].w + Inches(1))) < 100


def test_rows_count_and_heights_equal():
    box = L.Box(Inches(0), Inches(0), Inches(12), Inches(6))
    rs = L.rows(box, 3, gap=Inches(0))
    assert len(rs) == 3
    assert rs[0].h == rs[1].h == rs[2].h
    assert rs[1].y > rs[0].y


def test_stack_middle_centers_group():
    box = L.Box(Inches(0), Inches(0), Inches(10), Inches(10))
    boxes = L.stack(box, [Inches(2), Inches(2)], gap=Inches(0), align="middle")
    assert abs(boxes[0].y - Inches(3)) < 100


def test_stack_top_starts_at_box_top():
    box = L.Box(Inches(0), Inches(1), Inches(10), Inches(10))
    boxes = L.stack(box, [Inches(2)], gap=Inches(0), align="top")
    assert boxes[0].y == Inches(1)


def test_split_ratio():
    box = L.Box(Inches(0), Inches(0), Inches(10), Inches(6))
    left, right = L.split(box, 0.4, gap=Inches(0))
    assert abs(left.w - Inches(4)) < 100
    assert abs(right.w - Inches(6)) < 100
    assert abs(right.x - (left.x + left.w)) < 100   # gap=0, so right starts right after left


def test_inset_shrinks_box():
    box = L.Box(Inches(1), Inches(1), Inches(10), Inches(8))
    inner = L.inset(box, Inches(0.5), Inches(0.5))
    assert inner.x == Inches(1.5)
    assert inner.w == Inches(9)


def test_columns_single():
    box = L.Box(Inches(0), Inches(0), Inches(12), Inches(6))
    cols = L.columns(box, 1)
    assert len(cols) == 1
    assert cols[0].w == Inches(12)


def test_stack_bottom_align():
    box = L.Box(Inches(0), Inches(0), Inches(10), Inches(10))
    boxes = L.stack(box, [Inches(2)], gap=Inches(0), align="bottom")
    # 2" 块,底对齐 10" 区 → 顶在 8"
    assert abs(boxes[0].y - Inches(8)) < 100


def test_stack_empty_heights_returns_empty():
    box = L.Box(Inches(0), Inches(0), Inches(10), Inches(10))
    assert L.stack(box, []) == []


def test_rows_x_matches_box():
    box = L.Box(Inches(2), Inches(0), Inches(8), Inches(6))
    rs = L.rows(box, 3)
    assert all(r.x == box.x for r in rs)
