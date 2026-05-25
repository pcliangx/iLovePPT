# matplotlib.md — 数据驱动图表工作流

> 适用场景：数据从 CSV / 程序动态生成的柱状图、雷达图、仪表盘。
> 静态演示图（数据固定）→ 用 draw.io 更省工具切换成本。
> 配套：[[pptx]] design-system.md（色板）、[[pptx]] helpers.py（嵌入）。

---

## 1. 安装

```bash
pip3 install matplotlib
# 验证
python3 -c 'import matplotlib; print(matplotlib.__version__)'
```

---

## 2. 风格 SSOT —— 一行装上所有规范

**所有 iLovePPT 的 matplotlib 图必须在脚本顶部调一次 `apply_iloveppt_style()`**,自动套用:

- 字体优先级 Microsoft YaHei → Source Han Sans CN → PingFang SC → Helvetica → Arial
- 色板 = `helpers.py` 的 `BRAND_PRIMARY / ACCENT / BRAND_DARK / GRAY_*`(全 deck 视觉一致)
- 字号 14pt body / 18pt title / 12pt tick(嵌入 PPT 后等效与 body 18pt 协调)
- 网格 GRAY_300 极细;去顶 + 右边框(BCG 极简风)
- 图例无边框;`dpi=200` + `bbox_inches="tight"`(嵌入清晰)

```python
import sys
from pathlib import Path

# 加载 matplotlib_rc(.claude/skills/diagram/matplotlib_rc.py)
_dpath = str(Path(__file__).parent.parent / "diagram")
if _dpath not in sys.path:
    sys.path.insert(0, _dpath)
from matplotlib_rc import apply_iloveppt_style, PALETTE

apply_iloveppt_style()   # 必须在 plt.figure 之前调

import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.bar(["Q1", "Q2", "Q3", "Q4"], [120, 156, 178, 203])
ax.set_title("营收增长")
plt.savefig("revenue.png")   # 自动 dpi=200 / tight bbox / white facecolor
```

> 不再允许"自己 rcParams 设字体配色"风格,**所有图必须用 SSOT**。如要破例(罕见场景),
> 在 PR 里说明理由 + 视觉一致性自检。

### 中文字体安装(macOS 渲染前)

```bash
# 从 Windows 系统复制字体文件
cp msyh.ttf ~/Library/Fonts/
cp msyhbd.ttf ~/Library/Fonts/

# 刷新 matplotlib 字体缓存
python3 -c "import matplotlib.font_manager; matplotlib.font_manager._load_fontmanager(try_read_cache=False)"

# 验证
fc-list | grep -i yahei
```

---

## 3. 色板与 [[pptx]] 同步

Tech Blue 默认色板（对应 [[pptx]] design-system.md）：

```python
# Tech Blue 色板（默认）
BRAND_PRIMARY = '#0A52BF'  # 主色，柱形 / 雷达填充
BRAND_DARK    = '#0B2A4A'  # 深色，轴线 / 标注文字
BRAND_TINT    = '#E6F0FC'  # 浅色，背景区域
ACCENT        = '#007A6D'  # 强调色，高亮柱 / 阈值线
GRAY_300      = '#D9D9D9'  # 灰色，网格线 / 辅助元素
WHITE         = '#FFFFFF'  # 白色，图表背景
```

切换色板：只需替换上方 6 个常量，与 [[pptx]] design-system.md 中 10 套色板对应。例如切换"商务深蓝"：

```python
BRAND_PRIMARY = '#1E2761'
BRAND_DARK    = '#0A1234'
BRAND_TINT    = '#CADCFC'
ACCENT        = '#FFFFFF'
```

---

## 4. 三类常用图模板

### 4.1 柱状图

适合：分类对比、数据排名、同比环比。

```python
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'Source Han Sans CN', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

# 数据
categories = ['方案 A', '方案 B', '方案 C', '方案 D', '方案 E']
values = [85, 72, 93, 61, 78]
highlight_idx = 2  # 高亮最优方案

BRAND_PRIMARY = '#0A52BF'
ACCENT        = '#007A6D'
BRAND_DARK    = '#0B2A4A'
GRAY_300      = '#D9D9D9'

# 配色：高亮项用 ACCENT，其余用 BRAND_PRIMARY
colors = [ACCENT if i == highlight_idx else BRAND_PRIMARY for i in range(len(values))]

fig, ax = plt.subplots(figsize=(10, 5.625))  # 16:9 比例
bars = ax.bar(categories, values, color=colors, width=0.55, zorder=3)

# 数据标签
for bar, val in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
            f'{val}', ha='center', va='bottom',
            fontsize=13, color=BRAND_DARK, fontweight='bold')

# 样式
ax.set_ylim(0, max(values) * 1.2)
ax.set_ylabel('得分', fontsize=13, color=BRAND_DARK)
ax.set_title('方案评估对比', fontsize=16, fontweight='bold', color=BRAND_DARK, pad=12)
ax.yaxis.grid(True, color=GRAY_300, linewidth=0.8, zorder=0)
ax.set_axisbelow(True)
ax.tick_params(axis='both', labelsize=12, colors=BRAND_DARK)
for spine in ['top', 'right']:
    ax.spines[spine].set_visible(False)
ax.spines['left'].set_color(GRAY_300)
ax.spines['bottom'].set_color(GRAY_300)

fig.tight_layout()
plt.savefig('bar_chart.png', dpi=200, bbox_inches='tight', facecolor=WHITE)
plt.close()
```

### 4.2 雷达图

适合：多维能力评估、多方案综合对比。

```python
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'Source Han Sans CN', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

# 数据
dimensions = ['成本效益', '技术成熟度', '扩展性', '安全性', '易用性', '生态支持']
N = len(dimensions)

data = {
    '方案 A': [80, 90, 75, 85, 70, 80],
    '方案 B': [70, 75, 85, 90, 80, 70],
}

colors = ['#0A52BF', '#007A6D']
BRAND_DARK = '#0B2A4A'
BRAND_TINT = '#E6F0FC'

# 角度
angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
angles += angles[:1]  # 闭合

fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))

for (label, values), color in zip(data.items(), colors):
    v = values + values[:1]
    ax.plot(angles, v, 'o-', linewidth=2, color=color, label=label)
    ax.fill(angles, v, alpha=0.12, color=color)

# 坐标轴
ax.set_xticks(angles[:-1])
ax.set_xticklabels(dimensions, fontsize=12, color=BRAND_DARK)
ax.set_ylim(0, 100)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=9, color='#999999')
ax.grid(color='#D9D9D9', linewidth=0.8)
ax.set_facecolor(BRAND_TINT)

ax.set_title('多维方案对比', fontsize=16, fontweight='bold',
             color=BRAND_DARK, pad=20)
ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1),
          fontsize=12, framealpha=0.8)

plt.savefig('radar_chart.png', dpi=200, bbox_inches='tight', facecolor='white')
plt.close()
```

### 4.3 仪表盘（单值 + 阈值带）

适合：KPI 完成率、健康度评分、单一指标展示。

```python
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'Source Han Sans CN', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

def draw_gauge(value: float, title: str, output: str,
               thresholds=(60, 80), vmax=100):
    """
    value: 当前值（0 ~ vmax）
    thresholds: (警告阈值, 良好阈值)
    """
    BRAND_PRIMARY = '#0A52BF'
    ACCENT        = '#007A6D'
    BRAND_DARK    = '#0B2A4A'

    fig, ax = plt.subplots(figsize=(6, 4), subplot_kw=dict(aspect='equal'))
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-0.2, 1.2)
    ax.axis('off')

    # 阈值带（背景弧）
    def arc_patch(start_pct, end_pct, color, alpha=0.25):
        theta1 = 180 - start_pct / vmax * 180
        theta2 = 180 - end_pct / vmax * 180
        wedge = mpatches.Wedge((0, 0), 1.0, theta2, theta1,
                               width=0.25, color=color, alpha=alpha)
        ax.add_patch(wedge)

    arc_patch(0, thresholds[0], '#F96167')          # 红区
    arc_patch(thresholds[0], thresholds[1], '#FFBF00')  # 黄区
    arc_patch(thresholds[1], vmax, ACCENT)          # 绿区

    # 指针
    angle = np.radians(180 - value / vmax * 180)
    ax.annotate('', xy=(0.75 * np.cos(angle), 0.75 * np.sin(angle)),
                xytext=(0, 0),
                arrowprops=dict(arrowstyle='->', color=BRAND_DARK,
                                lw=2.5, mutation_scale=18))

    # 中心点
    circle = plt.Circle((0, 0), 0.07, color=BRAND_DARK, zorder=5)
    ax.add_patch(circle)

    # 数值
    ax.text(0, -0.12, f'{value:.0f}', ha='center', va='top',
            fontsize=28, fontweight='bold', color=BRAND_PRIMARY)
    ax.text(0, 0.55, title, ha='center', va='center',
            fontsize=14, color=BRAND_DARK)

    plt.savefig(output, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()

# 使用示例
draw_gauge(value=78, title='项目健康度', output='gauge.png')
```

---

## 5. 输出 DPI 设置

始终用 `dpi=200` 保证嵌入 PPT 后清晰：

```python
plt.savefig("out.png", dpi=200, bbox_inches='tight', facecolor='white')
```

| DPI | 适用场景 | 说明 |
|---|---|---|
| 72 | 屏幕预览 | 嵌 PPT 后糊 |
| 150 | 草稿 | 勉强可用 |
| **200** | **PPT 嵌入** | **推荐** |
| 300 | 印刷 | 文件较大 |

---

## 6. 嵌入 PPT

matplotlib 输出 PNG 后，调 [[pptx]] `helpers.py:embed_picture`：

```python
from pptx.util import Inches

# 全图占位（标题 slide 下方）
H.embed_picture(slide, "bar_chart.png", Inches(0.55), Inches(1.9), height=Inches(5.0))

# 半宽（左侧）
H.embed_picture(slide, "radar_chart.png", Inches(0.55), Inches(1.9), height=Inches(4.5))
```

---

## 7. 何时切换到 draw.io

| 情形 | 切换原因 |
|---|---|
| 数据固定不变（静态演示） | draw.io 手工画更快，无需写 Python |
| 需要精确控制节点位置 | matplotlib 坐标系复杂 |
| 图表类型不是数据可视化 | 架构图 / 矩阵 → draw.io |
