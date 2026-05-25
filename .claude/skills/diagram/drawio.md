# drawio.md — draw.io mxGraph XML 完全指南

> 适用场景：多层架构图、矩阵图、决策树、卡片墙、角色边界图等复杂图形。
> 配套工具：[[diagram]] SKILL.md（选型）、[[pptx]] helpers.py（嵌入）。

---

## 1. 安装

```bash
brew install --cask drawio   # macOS，约 150 MB
# 安装后产物：
#   /Applications/draw.io.app          （GUI 应用）
#   /opt/homebrew/bin/drawio           （CLI 软链接）
```

验证安装：

```bash
ls /Applications/draw.io.app && echo "installed"
/Applications/draw.io.app/Contents/MacOS/draw.io --version
```

---

## 2. headless CLI 渲染

draw.io 支持无 GUI 的命令行渲染，适合批量生产 PNG。

### 基本命令

```bash
/Applications/draw.io.app/Contents/MacOS/draw.io \
  --export --format png --width 3200 \
  --output out.png in.drawio
```

### 参数详解

| 参数 | 说明 | 默认值 | 推荐值 |
|---|---|---|---|
| `--format png` | 输出格式 | svg | png（PPT 嵌入用） |
| `--width 3200` | 输出宽度（px） | 800 | **3200**（必设，否则糊） |
| `--transparent` | PNG 透明背景 | 白底 | 一般不加（PPT 用白底） |
| `--scale 2` | 矢量缩放倍数 | 1 | 与 --width 二选一 |
| `--output` | 输出路径 | 同名 .png | 显式指定 |
| `--format svg` | SVG 输出 | — | 可选，LibreOffice 渲染不稳定 |
| `--format pdf` | PDF 输出 | — | 适合打印版 |

**为什么必须 `--width 3200`**：默认 800px 嵌 16:9 PPT（13.333" × 200 DPI ≈ 2666px 等效）会糊。3200px 留足余量，缩到 5" 高后分辨率仍充裕。

**渲染速度**：单图约 1-3 秒（Electron 启动慢，但内部有进程复用）。

---

## 3. mxGraph XML 最小模板

以下是一个完整可运行的 drawio 源文件模板，包含两个节点和一条连接边：

```xml
<mxfile host="app.diagrams.net" version="30.0.1">
  <diagram name="my-diagram" id="D1">
    <mxGraphModel dx="1600" dy="900" page="1"
                  pageWidth="1600" pageHeight="900"
                  background="#FFFFFF">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />

        <!-- 节点 A：深色主节点 -->
        <mxCell id="n1" value="节点 A" vertex="1" parent="1"
                style="rounded=1;arcSize=10;
                       fillColor=#1E6FE0;strokeColor=#0B2A4A;
                       fontColor=#FFFFFF;fontSize=20;
                       fontFamily=Microsoft YaHei;fontStyle=1;
                       strokeWidth=2;whiteSpace=wrap;">
          <mxGeometry x="100" y="200" width="240" height="80" as="geometry" />
        </mxCell>

        <!-- 节点 B：浅色次节点 -->
        <mxCell id="n2" value="节点 B" vertex="1" parent="1"
                style="rounded=1;arcSize=10;
                       fillColor=#E6F0FC;strokeColor=#1E6FE0;
                       fontColor=#0B2A4A;fontSize=20;
                       fontFamily=Microsoft YaHei;fontStyle=0;
                       strokeWidth=1.5;whiteSpace=wrap;">
          <mxGeometry x="500" y="200" width="240" height="80" as="geometry" />
        </mxCell>

        <!-- 边：必须用 source/target 引用节点 id -->
        <mxCell id="e1" edge="1" parent="1" source="n1" target="n2"
                style="endArrow=classic;endFill=1;endSize=14;
                       strokeColor=#0B2A4A;strokeWidth=2.5;">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

**关键字段说明**：

| 字段 | 作用 |
|---|---|
| `id="0"` / `id="1"` | 固定根节点，所有内容 parent="1" |
| `vertex="1"` | 声明为节点（非边） |
| `edge="1"` | 声明为边 |
| `parent="1"` | 挂在根层；container 内子节点改为 parent="container_id" |
| `relative="1"` | edge geometry 相对模式（必须） |

---

## 4. 10 类 Cell 清单（按用途）

### 4.1 节点类

| 用途 | style 关键字段 | 何时用 |
|---|---|---|
| **圆角矩形** | `rounded=1;arcSize=10` | 90% 节点，通用首选 |
| **椭圆** | `ellipse` | 角色圈 / 决策象限 / 起止节点 |
| **三角形** | `shape=triangle;direction=north` | 雷达顶点 / 视觉装饰 |
| **菱形（判断）** | `rhombus` | 决策树 / 流程分支节点 |
| **文本（无框）** | `text;html=1;strokeColor=none;fillColor=none` | 标签 / 标题 / 注解 |

#### 圆角矩形完整示例

```xml
<mxCell id="box1" value="系统模块" vertex="1" parent="1"
        style="rounded=1;arcSize=10;
               fillColor=#1E6FE0;strokeColor=#0B2A4A;
               fontColor=#FFFFFF;fontSize=20;
               fontFamily=Microsoft YaHei;fontStyle=1;
               strokeWidth=2;whiteSpace=wrap;">
  <mxGeometry x="200" y="150" width="240" height="80" as="geometry" />
</mxCell>
```

#### 菱形判断节点示例

```xml
<mxCell id="d1" value="条件满足？" vertex="1" parent="1"
        style="rhombus;fillColor=#00D1C1;strokeColor=#0B2A4A;
               fontColor=#0B2A4A;fontSize=18;
               fontFamily=Microsoft YaHei;fontStyle=1;">
  <mxGeometry x="350" y="300" width="160" height="100" as="geometry" />
</mxCell>
```

### 4.2 边类

| 用途 | style 关键字段 | 何时用 |
|---|---|---|
| **直边** | `endArrow=classic;endFill=1` | 简单顺序箭头 |
| **正交折边** | `edgeStyle=orthogonalEdgeStyle;rounded=1` | 90° 折线，架构图首选 |
| **虚线边** | `dashed=1;dashPattern=8 4` | 失败回路 / 可选路径 |
| **曲线** | `curved=1` | 循环箭头 |

#### 正交折边完整示例

```xml
<mxCell id="e2" edge="1" parent="1" source="n1" target="n3"
        style="edgeStyle=orthogonalEdgeStyle;rounded=1;
               endArrow=classic;endFill=1;endSize=12;
               strokeColor=#0B2A4A;strokeWidth=2;">
  <mxGeometry relative="1" as="geometry" />
</mxCell>
```

#### 带拐点的边（绕路）

```xml
<mxCell id="back" edge="1" parent="1" source="n4" target="n1"
        style="endArrow=classic;dashed=1;curved=1;
               strokeColor=#0B2A4A;strokeWidth=1.5;">
  <mxGeometry relative="1" as="geometry">
    <Array as="points">
      <mxPoint x="900" y="550" />
      <mxPoint x="200" y="550" />
    </Array>
  </mxGeometry>
</mxCell>
```

### 4.3 容器 / subgraph

容器本身是一个矩形 cell（无填充或浅填充），子节点通过 `parent="container_id"` 挂载：

```xml
<!-- 容器（subgraph） -->
<mxCell id="grp1" value="子系统层" vertex="1" parent="1"
        style="rounded=1;arcSize=5;
               fillColor=#E6F0FC;strokeColor=#1E6FE0;
               fontColor=#0B2A4A;fontSize=22;fontStyle=1;
               fontFamily=Microsoft YaHei;
               verticalAlign=top;strokeWidth=2;">
  <mxGeometry x="80" y="80" width="600" height="300" as="geometry" />
</mxCell>

<!-- 容器内子节点：parent="grp1" -->
<mxCell id="c1" value="子模块 A" vertex="1" parent="grp1"
        style="rounded=1;arcSize=10;
               fillColor=#1E6FE0;strokeColor=#0B2A4A;
               fontColor=#FFFFFF;fontSize=18;
               fontFamily=Microsoft YaHei;">
  <mxGeometry x="40" y="80" width="200" height="60" as="geometry" />
</mxCell>
```

---

## 5. mxGeometry 坐标系

```
(0,0) ─────────────────────────────────────→ x
  │
  │   ┌─────────────────────┐
  │   │  x=100, y=150       │
  │   │  width=240          │
  │   │  height=80          │
  │   └─────────────────────┘
  ↓ y
```

| 属性 | 说明 |
|---|---|
| `x` / `y` | 节点左上角坐标（画布左上角为原点） |
| `width` / `height` | 节点尺寸（单位 px，基准画布 1600×900） |
| `relative="1"` | 边的 geometry 必须设置此属性 |
| `as="geometry"` | 固定写法，mxGraph 识别标志 |

**坐标规划建议**：

- 水平节点间距：节点宽度 + 80-120px（间距太小显压迫感）
- 垂直层间距：节点高度 + 80-100px
- 页面留白：四边各留 60-80px
- 容器内边距：子节点距容器边缘 ≥ 40px

---

## 6. 设计 Token（与 [[pptx]] 同步）

### 颜色（Tech Blue 默认）

使用 [[pptx]] design-system.md 的 10 套色板，默认 Tech Blue：

```
主色      #1E6FE0   深色 box / 主节点 / 标题栏
深色      #0B2A4A   边框 / 文字 / 箭头颜色
浅底      #E6F0FC   subgraph 背景 / 浅色节点填充
强调      #00D1C1   高亮节点 / 警示 / 正向标记
白色      #FFFFFF   深底节点文字颜色
灰色文    #999999   次要文本 / 注解
浅灰底    #F5F5F5   中性背景
```

切换色板：修改 style 中的 fillColor / strokeColor / fontColor 即可，或用 sed 批量替换（见第 8 节）。

### 字体

```
fontFamily=Microsoft YaHei
```

fallback 链（用于 sed 替换脚本）：

```
Microsoft YaHei → PingFang SC → Source Han Sans CN → Heiti SC
```

⚠️ macOS 无 Microsoft YaHei 时 draw.io 通过 SVG `<foreignObject>` 调 Chromium，会按 fallback 找 PingFang SC。渲染前建议安装雅黑（见 [[pptx]] creating.md）。

### 字号体系（基准画布 1600×900）

| 用途 | 字号 | bold |
|---|---|---|
| **页面标题** | 28pt | ✓ |
| **章节 / subgraph 标题** | 22-24pt | ✓ |
| **节点（深色背景）** | 20-22pt | ✓ |
| **节点（浅色 / 描述）** | 18-20pt | — |
| **强调框 / 输入输出** | 24-26pt | ✓ |
| **注解 / 底部结论** | 16-18pt | 视情况 |
| **小标签 / 角标** | 14-15pt | — |

**字号 → 实际渲染尺寸**：3200px 输出，每 pt 约 4-5px 高 → 28pt ≈ 140px，嵌入 PPT 缩到 13.333" 宽后视感约等于 PPT 32pt。

### 画布尺寸

**统一 1600×900**（16:9，与 PPT slide 比例一致）。嵌入时 `add_picture(height=Inches(N))` 等比缩放不变形。

---

## 7. 8 大致丑坑详解

### 坑 1：用旧字体（黑体 / 苹方）作默认

**现象**：中文字感老派、笔画宽 hint 模糊，视觉"显奇怪"。

**原因**：旧版 macOS 黑体（即 Heiti SC）笔画对比度弱，在投影 / 屏幕小字号下可读性差。

**修法**：统一替换为 Microsoft YaHei（见 §8.3 批量替换脚本）：

```bash
# 一次性替换所有旧字体引用
sed -i.bak -e 's/fontFamily=[^;]*/fontFamily=Microsoft YaHei/g' *.drawio
```

---

### 坑 2：大背景 box 加 `sketch=1`

**现象**：背景变 hatch 斜线纹理，前景文字被纹理遮挡，整体不严肃。

**原因**：`sketch=1` 是手绘风格模式，适合 brainstorm 草图，不适合正式报告。

**修法**：删除或改为 `sketch=0`：

```xml
<!-- 错误 -->
style="sketch=1;fillColor=#E6F0FC;..."

<!-- 正确 -->
style="sketch=0;fillColor=#E6F0FC;..."
<!-- 或直接省略 sketch 字段 -->
```

---

### 坑 3：长英文串在固定宽度 box 内不换行

**现象**：英文产品名（如 `Kubernetes-Operator-v2`）超出节点边界，截断或撑爆布局。

**原因**：draw.io 默认不换行；Microsoft YaHei 字距较宽，固定 240px box 容易溢出。

**修法**：

1. 添加 `whiteSpace=wrap` 允许换行
2. 必要时加宽节点（240 → 270px）
3. 留内边距：`spacingLeft=8;spacingRight=8`

```xml
style="...; whiteSpace=wrap; spacingLeft=8; spacingRight=8;"
<mxGeometry x="100" y="150" width="270" height="80" as="geometry" />
```

---

### 坑 4：渲染不带 `--width 3200`

**现象**：输出 PNG 默认 800px，嵌入 16:9 PPT 后模糊发虚。

**原因**：draw.io CLI 默认宽度 800px，PPT 13.333" @ 200 DPI ≈ 2666px，不足导致上采样。

**修法**：始终显式加 `--width 3200`：

```bash
# 错误（默认 800px）
draw.io --export --format png --output out.png in.drawio

# 正确
draw.io --export --format png --width 3200 --output out.png in.drawio
```

---

### 坑 5：`value` 里裸换行 `\n`

**现象**：XML 解析器报错或节点显示空白。

**原因**：XML 不支持裸 `\n` 在属性值中作换行符。

**修法**：用 XML line-feed entity `&#xa;`：

```xml
<!-- 错误 -->
value="第一行\n第二行"

<!-- 正确 -->
value="第一行&#xa;第二行"
```

---

### 坑 6：`value` 里特殊字符未转义

**现象**：draw.io 文件打开报 XML parser error，或节点文本错乱。

**原因**：XML 属性值中 `& < > " '` 是保留字符。

**修法**：

| 原字符 | 转义 |
|---|---|
| `&` | `&amp;` |
| `<` | `&lt;` |
| `>` | `&gt;` |
| `"` | `&quot;` |
| `'` | `&apos;` |

```xml
<!-- 错误 -->
value="A & B < C"

<!-- 正确 -->
value="A &amp; B &lt; C"
```

---

### 坑 7：edge 用纯坐标定起止（不用 source/target）

**现象**：手动移动节点后，边不跟随，箭头位置偏离节点。

**原因**：纯坐标点是静态值，不绑定节点 id；source/target 引用会动态计算连接点。

**修法**：始终用 `source="node_id" target="node_id"`，拐点坐标写在 `<Array as="points">` 里：

```xml
<!-- 错误（纯坐标）-->
<mxCell id="e1" edge="1" parent="1"
        style="endArrow=classic;">
  <mxGeometry x="340" y="240" width="160" height="0" as="geometry" />
</mxCell>

<!-- 正确（source/target 引用）-->
<mxCell id="e1" edge="1" parent="1" source="n1" target="n2"
        style="endArrow=classic;endFill=1;strokeColor=#0B2A4A;">
  <mxGeometry relative="1" as="geometry" />
</mxCell>
```

---

### 坑 8：节点内用 emoji

**现象**：macOS PNG 渲染正常，但走 LibreOffice 转 PDF 时 emoji 变方块字。

**原因**：LibreOffice Chromium 渲染引擎 emoji fallback 不稳定，缺少彩色 emoji 字体。

**修法**：生产环境不用 emoji。可用 Unicode 符号替代：

| 场景 | 推荐替代 |
|---|---|
| 警告 | ⚠ |
| 禁止 | ⛔ |
| 锁 | 🔒 |
| 成功 | ✓ |
| 失败 | ✗ |

---

## 8. 批量工作流

### 8.1 目录结构

```
project/diagrams/
├── src/    *.drawio   （XML 源，版本控制）
└── png/    *.png      （3200px 渲染产物，gitignore 可选）
```

### 8.2 批量渲染脚本

```bash
#!/usr/bin/env bash
# render-all.sh — 批量渲染所有 .drawio 到 png/

set -euo pipefail

SRC_DIR="./src"
PNG_DIR="./png"
DRAW_IO="/Applications/draw.io.app/Contents/MacOS/draw.io"

mkdir -p "$PNG_DIR"

for f in "$SRC_DIR"/*.drawio; do
    base=$(basename "$f" .drawio)
    echo "Rendering $base ..."
    "$DRAW_IO" --export --format png --width 3200 \
        --output "$PNG_DIR/${base}.png" "$f"
done

echo "Done. $(ls "$PNG_DIR"/*.png | wc -l | tr -d ' ') PNGs in $PNG_DIR/"
```

### 8.3 全局字体替换

```bash
# 全局替换旧字体引用 → Microsoft YaHei（含 .bak 备份）
cd src/
for f in *.drawio; do
    sed -i.bak 's/fontFamily=[^;]*/fontFamily=Microsoft YaHei/g' "$f"
done
# 替换完后重跑批量渲染
```

### 8.4 全局配色替换

```bash
# Tech Blue 替换示例（换成商务深蓝 #1E2761）
for f in *.drawio; do
    sed -i.bak \
        -e 's/#1E6FE0/#1E2761/g' \
        -e 's/#0B2A4A/#0A1234/g' \
        -e 's/#E6F0FC/#CADCFC/g' \
        "$f"
done
```

---

## 9. 嵌入 PPT 链路

draw.io 产出 PNG 后，调 [[pptx]] `helpers.py:embed_picture` 嵌入 slide：

```python
from pptx.util import Inches

# 单图全宽（0.55" 左边距，1.9" 顶边距，5.0" 高等比缩放）
H.embed_picture(slide, "arch.png", Inches(0.55), Inches(1.9), height=Inches(5.0))

# 双图并列（左图）
H.embed_picture(slide, "left.png", Inches(0.55), Inches(1.9), height=Inches(4.5))
# 双图并列（右图）
H.embed_picture(slide, "right.png", Inches(7.00), Inches(1.9), height=Inches(4.5))
```

3200px 宽 PNG → 缩到 5" 高：5" × 200 DPI = 1000px 等效，分辨率充裕不糊。

---

## 10. 何时切换到其他工具

| 情形 | 切换到 | 原因 |
|---|---|---|
| 节点 ≤ 6、单层线性流程 | Mermaid | 文本 DSL 写起来快 5×，无需 XML |
| 数据从 CSV / 程序动态生成 | matplotlib | draw.io 手工坐标不适合动态数据 |
| 单张 slide 内 ≤ 5 节点，需 PPT 可编辑 | pptx-native | add_shape 产物可在 PPT 内直接调整 |
| 需要交互式网页图（非 PPT 输出） | Excalidraw / D3.js | draw.io PNG 是静态输出 |

---

## 附：完整多节点架构图示例

以下是一个 4 节点架构图（含 subgraph 和回路边）的完整示例：

```xml
<mxfile host="app.diagrams.net" version="30.0.1">
  <diagram name="arch-example" id="A1">
    <mxGraphModel dx="1600" dy="900" page="1"
                  pageWidth="1600" pageHeight="900"
                  background="#FFFFFF">
      <root>
        <mxCell id="0" /><mxCell id="1" parent="0" />

        <!-- subgraph 容器 -->
        <mxCell id="g1" value="核心层" vertex="1" parent="1"
                style="rounded=1;arcSize=5;fillColor=#E6F0FC;strokeColor=#1E6FE0;
                       fontColor=#0B2A4A;fontSize=22;fontStyle=1;
                       fontFamily=Microsoft YaHei;verticalAlign=top;strokeWidth=2;">
          <mxGeometry x="80" y="100" width="700" height="250" as="geometry" />
        </mxCell>

        <!-- 节点 1 -->
        <mxCell id="n1" value="输入层" vertex="1" parent="g1"
                style="rounded=1;arcSize=10;fillColor=#1E6FE0;strokeColor=#0B2A4A;
                       fontColor=#FFFFFF;fontSize=20;fontStyle=1;
                       fontFamily=Microsoft YaHei;strokeWidth=2;whiteSpace=wrap;">
          <mxGeometry x="40" y="80" width="200" height="70" as="geometry" />
        </mxCell>

        <!-- 节点 2 -->
        <mxCell id="n2" value="处理层" vertex="1" parent="g1"
                style="rounded=1;arcSize=10;fillColor=#0B2A4A;strokeColor=#0B2A4A;
                       fontColor=#FFFFFF;fontSize=20;fontStyle=1;
                       fontFamily=Microsoft YaHei;strokeWidth=2;whiteSpace=wrap;">
          <mxGeometry x="250" y="80" width="200" height="70" as="geometry" />
        </mxCell>

        <!-- 节点 3（容器外）-->
        <mxCell id="n3" value="输出层" vertex="1" parent="1"
                style="rounded=1;arcSize=10;fillColor=#00D1C1;strokeColor=#0B2A4A;
                       fontColor=#0B2A4A;fontSize=20;fontStyle=1;
                       fontFamily=Microsoft YaHei;strokeWidth=2;whiteSpace=wrap;">
          <mxGeometry x="900" y="280" width="200" height="70" as="geometry" />
        </mxCell>

        <!-- 正向边 n1→n2 -->
        <mxCell id="e1" edge="1" parent="1" source="n1" target="n2"
                style="edgeStyle=orthogonalEdgeStyle;rounded=1;
                       endArrow=classic;endFill=1;endSize=12;
                       strokeColor=#0B2A4A;strokeWidth=2;">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <!-- 正向边 n2→n3 -->
        <mxCell id="e2" edge="1" parent="1" source="n2" target="n3"
                style="endArrow=classic;endFill=1;endSize=12;
                       strokeColor=#0B2A4A;strokeWidth=2;">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```
