# 加新 layout —— Plugin 机制(P3-2 后)

> 本仓库的 layout 系统是 **auto-discover plugin 架构**。加一个新 layout type(如 `swot_grid` / `bcg_growth_share` / `kanban`)= 写**一个文件**,不需要改 `helpers/__init__.py` / `build.py` / `themes/`。

## TL;DR

```bash
# 1. 新建 plugin 文件
cat > .claude/skills/pptx/helpers/swot_grid.py <<'EOF'
"""swot_grid layout plugin — 2×2 SWOT 矩阵(Strengths/Weaknesses/Opportunities/Threats)。"""
from __future__ import annotations
from types import ModuleType
from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide

from . import GRAY_700
from ._base import register_layout
from ._internals import add_title, blank_slide, resolve_brand, text_in_box
from layout import Box, content_region, columns, rows


@register_layout("swot_grid")
def make_swot_grid(
    prs: _Pres,
    title: str,
    strengths: list[str],
    weaknesses: list[str],
    opportunities: list[str],
    threats: list[str],
    *,
    theme: ModuleType | None = None,
) -> Slide:
    T = resolve_brand(theme)
    s = blank_slide(prs)
    add_title(s, title, theme=theme)
    # ... 实现细节 ...
    return s
EOF

# 2. 验证 auto-discover
python -c "
import sys; sys.path.insert(0, '.claude/skills/pptx')
from helpers import LayoutRegistry
assert 'swot_grid' in LayoutRegistry.all_layouts()
print('OK')
"

# 3. 写测试 + 跑 pytest
pytest tests/pptx/ -x
```

完事。

---

## 详细步骤

### 0. 命名 + 准备

- **layout_type 名称**:跟 `library/vocabularies/layout_variants.yaml` 受控词典对齐(snake_case · 短而具体)
- **文件位置**:`.claude/skills/pptx/helpers/<layout_type>.py`(单文件,**不能**用下划线开头 — 否则 auto-discover 跳过)

### 1. 文件骨架

```python
"""<layout_type> layout plugin — <一句话说明>。

<implementation notes / 视觉规则 / N 个数据点的边界条件>
"""
from __future__ import annotations

from types import ModuleType
from typing import Any

from pptx.presentation import Presentation as _Pres
from pptx.slide import Slide
from pptx.util import Inches

# 1. helpers 原语 + token(从 helpers package import)
from . import (
    GRAY_700,          # 设计 token
    fix_textbox_margins,  # 原语函数
    rect,
    set_font,
)

# 2. plugin registration decorator
from ._base import register_layout

# 3. theme-agnostic helper(blank_slide / add_title / text_in_box / resolve_brand)
from ._internals import (
    add_title,
    blank_slide,
    resolve_brand,
    text_in_box,
)

# 4. 几何原语(layout.py 在 sys.path 顶层 · 用绝对 import)
from layout import Box, content_region, columns, rows, stack


@register_layout("<layout_type>")
def make_<layout_type>(
    prs: _Pres,
    title: str,
    # ... 数据字段(列表 / dict / 必传参数) ...
    *,
    theme: ModuleType | None = None,
    # ... 可选关键字参数 ...
) -> Slide:
    """<docstring>"""
    T = resolve_brand(theme)   # 取 PRIMARY / PRIMARY_DEEP / FONT_HEADER 等
    s = blank_slide(prs)
    add_title(s, title, theme=theme)

    # 实现具体渲染逻辑
    region = content_region()
    # ...

    return s
```

### 2. 设计约定

- **函数签名 1**:`prs` 是 first positional;`theme` 是 keyword-only,默认 None(plugin 必须支持 theme 缺省)
- **函数签名 2**:其他业务字段(`title` / `cards` / `tiers` / ...)按 layout 自然语义排,优先 positional · 复杂字典用 keyword-only
- **theme 处理**:用 `T = resolve_brand(theme)` 一次性取常用 token(PRIMARY / PRIMARY_DEEP / PRIMARY_TINT / ACCENT / FONT_HEADER / FONT_BODY / FONT_NUM)
- **不重定义色彩 / 字体**:直接用 `T["PRIMARY"]` / `GRAY_700` / `WHITE` —— 任何新色板放 helpers/__init__.py 或 theme yaml,**不在 plugin 里**
- **handout mode 支持**:用 `is_handout()` 切字号 / 高度;handout = `H.PRESENTATION_MODE == "handout"`(由 build.py set)

### 3. 几何 layout

用 `layout.py` 的纯函数原语,而非手算 `Inches(...)`:

| 需求 | 原语 |
|---|---|
| 整个内容区(header / footer 之间) | `content_region()` |
| 整张 slide(封面 / 封底用) | `full_region()` |
| 横切 N 等宽列 | `columns(box, n, gap=Inches(0.3))` |
| 纵切 N 等高行 | `rows(box, n, gap=Inches(0.2))` |
| 自定义高度堆叠 | `stack(box, [Inches(1.5), Inches(2.0)], align="middle")` |
| 左右分(比例)| `split(box, ratio=0.42)` |
| 四周内缩 | `inset(box, dx=Inches(0.3), dy=Inches(0.25))` |
| 12-col grid(跨页对齐)| `grid_columns(box, [3, 6, 3])`(sum = 12) |

### 4. 注册测试

新加 layout 后:

```python
# tests/pptx/test_layout_<layout_type>.py
from pptx import Presentation
from pptx.util import Inches
import helpers as H


def test_make_<layout_type>_registers():
    assert H.LayoutRegistry.has("<layout_type>")


def test_make_<layout_type>_renders():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    fn = H.LayoutRegistry.get("<layout_type>")
    slide = fn(prs, title="测试", ...)  # 按 plugin 签名传参
    assert len(prs.slides) == 1
    # 校验 shape 数,中文字体 ea field,核心文字内容等
```

### 5. Theme override(可选)

如果某 theme 想 override 标准 plugin 实现(自定义视觉风格):

- **方式 A**:在 `themes/<theme>.py` 写 `def make_<layout_type>(prs, ...)` —— `get_layout_func()` 会优先用 theme module 的,plugin 是 fallback
- **方式 B**:同 layout_type 在 `helpers/<theme>_<layout_type>.py` 再写一次 `@register_layout("<layout_type>")` —— 后注册覆盖。**不推荐**:registry 全局,影响所有 theme

### 6. RAG 词典 / 模板 sync(可选 · 长期生效需做)

如要让 author / iloveppt-builder 主动选这个 layout,还要:

1. **`library/vocabularies/layout_variants.yaml`** 加 enum:`<layout_type>` + variants(如 `swot_grid` 加 `2x2` / `tier-3` / `tier-4`)
2. **`library/pptx-templates/items/<theme>/pages/<NN>/meta.yaml`** 模板里若有现成实例 → 改 layout_type = `<layout_type>` 让 ingest 重 embed
3. **`library/visual-patterns/` kb** 加 pattern doc 让 author Stage D 检索时能命中

## 现有 17 个 plugin 速查

| layout_type | 数据签名 | 用途 |
|---|---|---|
| `cover` | `title, subtitle, *, prepared_by, date, version, project_code, classification` | 封面页 |
| `toc` | `sections: list[str]` | 目录页 |
| `section_divider` | `num, title` | 章节扉页 |
| `single_focus` | `*, big_text, big_number, explanation` | Hero 大字 |
| `cards` | `title, cards: list[{title, body, icon?}]` | N 张并列卡片(2-10)|
| `bullet_list` | `title, items: list[str | dict]` | 要点列表 |
| `data` | `title, *, headers, table_rows | chart_path, highlights?` | 数据展示(表 / 图)|
| `process_flow` | `title, steps: list[{title, desc}]` | N 步流程(N=3-7) |
| `timeline` | `title, milestones: list[{title, desc, date?}]` | 水平时间轴 |
| `pyramid` | `title, tiers, *, side_left?, side_right?` | N-tier 金字塔 |
| `radial` | `title, center, spokes` | 中心 + N 辐射 |
| `venn` | `title, sets: list[{label}], *, intersection_label` | 2-3 圆 Venn |
| `quadrant` | `title, x_axis, y_axis, quadrants` | 2×2 BCG 矩阵 |
| `comparison` | `title, items: list[{title, body, recommended?}]` | N 列对比表 |
| `summary` | `conclusions: list[str], *, title` | N 条结论 |
| `closing` | `*, subtitle, next_steps?` | 封底(谢谢 / Next Steps) |
| `quote` | `quote, *, attribution, role` | 客户证言 |

源码:`.claude/skills/pptx/helpers/<layout_type>.py`。

## 反模式

- ✗ 在 `helpers/<layout>.py` 重定义 `BRAND_PRIMARY` / `FONT_CN` 等 token(SSOT 是 helpers/__init__.py 或 theme yaml)
- ✗ 在 plugin 里硬编码 `Inches(0.55)` 边距(用 `LEFT_MARGIN` / `RIGHT_MARGIN` 或几何原语)
- ✗ 拷贝 `set_font` / `card` 等 helper 代码(用 `from . import set_font, card`)
- ✗ 给 plugin 文件名加下划线前缀(`_my_layout.py`)— auto-discover 会跳过
- ✗ 在 `helpers/__init__.py` 手写 `import .my_layout`(`pkgutil.iter_modules` 已自动)
- ✗ 让 plugin 函数依赖 theme module 必传(`theme` 必须 keyword-only + 默认 None)

## 内部机制

- `helpers/_base.py:LayoutRegistry` 是 class-level singleton,`_layouts: dict[str, Callable]` 在类上
- `helpers/__init__.py` 末尾的 `_auto_discover_layouts()` 用 `pkgutil.iter_modules` walk `helpers/` 目录,`importlib.import_module` 触发各 plugin 文件的 `@register_layout` decorator 执行
- 跳过规则:文件名以 `_`(包内 helper)或 `test_`(测试)开头
- `LayoutRegistry.get(layout_type)` 失败时 fail-loud 列出所有已知 layout · 利于排错
