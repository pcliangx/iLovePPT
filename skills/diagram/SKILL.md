---
name: diagram
description: 生成架构图、流程图、矩阵、决策树、数据可视化。覆盖 draw.io（多层架构/矩阵）、Mermaid（线性流程）、matplotlib（数据驱动）、pptx-native add_shape（slide 内画 ≤5 节点）四套工具。提供选型决策表、跨平台中文字体（默认 Microsoft YaHei）、PNG 嵌入 PPT 链路、8 大致丑坑规避。被 [[pptx-deck]] 调用，也可独立产出图。触发：架构图 / 流程图 / 矩阵 / 决策树 / draw.io / mermaid / sequence / 可视化。
---

# diagram skill — 架构图与可视化

本 skill 是架构图与可视化的统一入口。覆盖 draw.io（mxGraph XML）、Mermaid（文本 DSL）、
matplotlib（数据驱动）、python-pptx add_shape（slide 内原生）四套工具链。提供工具选型决策表、
中文字体配置（默认 Microsoft YaHei）、PNG 嵌入 PPT 链路、8 大致丑坑规避。

## 何时用本 skill

| 信号 | 用 |
|---|:--:|
| deck 含 5+ 张"非简单流程图" | ✅ |
| 用户抱怨"图太少 / 架构看不懂 / 没有可视化" | ✅ |
| 矩阵图（≥ 3 列）/ 角色边界 / 决策树 | ✅ |
| 多张图要"视觉一致性"（同配色 / 字体 / 字号） | ✅ |
| 单张简单线性流程（≤ 6 节点） | ⚠️ Mermaid 即可 |
| 数据驱动可视化（柱 / 雷达 / 仪表盘） | ⚠️ matplotlib |

## 工具选型决策表（8 种图）

| 图类型 | 首选 | 替代 | 切换阈值 |
|---|---|---|---|
| 简单线性流程（≤ 8 节点） | Mermaid | draw.io | 节点 > 10 或要精确配色 → draw.io |
| 多层架构 / 嵌套 subgraph | **draw.io** | — | 没替代 |
| 类比 / 概念图 | draw.io | Excalidraw | 普通 draw.io 统一性更好 |
| 矩阵 / 角色边界 | **draw.io** | — | Mermaid 形状有限 |
| 决策树（菱形判断） | **draw.io** | — | Mermaid 菱形 hover 失稳 |
| 数据可视化（柱 / 雷达） | matplotlib | draw.io 静态 | 数据 > 5 行用 mpl |
| 卡片墙 / icon grid | draw.io | python-pptx 直接画 | 多 slide 复用 → draw.io PNG |
| ≤ 5 节点 slide 内简单关系 | python-pptx | — | 节点 > 5 → 切 draw.io |

经验：deck 总图数 ≤ 10 → 全 Mermaid；> 10 张或要"视觉一致" → 全 draw.io。**不混搭**（造成视觉割裂）。

## 跨工具共识

- **字体**：默认 Microsoft YaHei（与 [[pptx]] 同源）。fallback 链：Microsoft YaHei → PingFang SC → Source Han Sans CN
- **渲染基准**：1600 × 900；标题 28pt / 节点 20-22pt / 注解 16-18pt
- **配色**：使用 [[pptx]] design-system.md 的 10 套色板（默认 Tech Blue: #1E6FE0 / #0B2A4A / #E6F0FC / #00D1C1）
  - **SSOT**：色值的权威定义在 `[[pptx]] helpers.py` 的 `BRAND_*` 常量。本文档及各子文档示例里的 hex 是从那里**抄录的副本**,仅供示意；实际出图前以 `helpers.py` 当前值为准。改主题色 → 改 `helpers.py`,出图前同步更新图的配色。
- **分辨率**：draw.io `--width 3200`；mmdc `-w 2400`；matplotlib `dpi=200`
- **格式**：始终输出 PNG（LibreOffice SVG fallback 不稳定）

⚠️ macOS 渲染前装雅黑（详见 [[pptx]] creating.md）。

## 8 大致丑坑速查

| # | 坑 | 后果 | 解决 |
|---|---|---|---|
| 1 | 用 Heiti SC 作默认 | 老派、宽 hint 模糊 | 用 Microsoft YaHei |
| 2 | sketch hatch 风格 | 不严肃 | 关掉 hand-drawn |
| 3 | 长英文不换行设置 | 节点撑爆 | `whiteSpace=wrap` |
| 4 | 默认 800px 输出 | 嵌 16:9 PPT 模糊 | `--width 3200` |
| 5 | `&#xa;` 换行字符 | 渲染乱码 | 用 XML entity `&#10;` 或 newline |
| 6 | XML 特殊字符不转义 | 解析失败 | `& < > " '` 转义 |
| 7 | edge 拖拽后坐标失稳 | 重新渲染位置偏移 | 用 source/target id 而非坐标 |
| 8 | emoji 在 LibreOffice fallback | 方块字 | 别用 emoji；用 ⚠ ⛔ 🔒 |

## 子文档

| 文档 | 用途 |
|---|---|
| [drawio.md](drawio.md) | mxGraph XML / headless CLI / 8 坑详解 / Cell 类型 |
| [mermaid.md](mermaid.md) | mmdc / flowchart / sequence / themeVariables |
| [matplotlib.md](matplotlib.md) | 柱 / 雷达 / 仪表盘 / 中文字体配置 |
| [pptx-native.md](pptx-native.md) | slide 内 add_shape 直接画（≤ 5 节点） |

### 子文档使用路径

```
用户需要图
  ├─ 图类型？→ SKILL.md 选型表
  ├─ draw.io 相关 → drawio.md §2 CLI + §3 XML 模板 + §7 坑
  ├─ Mermaid → mermaid.md §4 模板 + §3 themeVariables
  ├─ 数据驱动图 → matplotlib.md §4 模板 + §2 字体配置
  └─ slide 内简单图 → pptx-native.md §4 示例
```

## 嵌入 PPT 链路

调 [[pptx]] `helpers.py:embed_picture`:

```python
from pptx.util import Inches

# 单图（全幅，16:9 PPT）
H.embed_picture(slide, "diagram.png", Inches(0.55), Inches(1.9), height=Inches(5.0))

# 双图并列（左右各半）
H.embed_picture(slide, "left.png",  Inches(0.55), Inches(1.9), height=Inches(4.5))
H.embed_picture(slide, "right.png", Inches(7.00), Inches(1.9), height=Inches(4.5))
```

PNG 始终用 `--width 3200`（draw.io）/ `-w 2400`（mmdc）/ `dpi=200`（matplotlib）保证嵌入清晰。

**分辨率原则**：3200px 宽 PNG 缩到 5" 高时等效约 200 DPI，PPT 内清晰无锯齿。

## 批量工作流（多图共享配色 / 字体）

```bash
# 1. sed 全局替换字体（如改主题）
sed -i.bak 's/fontFamily=Heiti SC/fontFamily=Microsoft YaHei/g' *.drawio

# 2. sed 全局替换配色（如切换色板）
sed -i.bak 's/#1E6FE0/#1E2761/g' *.drawio

# 3. for loop 批量渲染
for f in *.drawio; do
    /Applications/draw.io.app/Contents/MacOS/draw.io \
      --export --format png --width 3200 \
      --output "${f%.drawio}.png" "$f"
done
```

详细批量脚本（含目录管理）见 [drawio.md](drawio.md) §8。

## 依赖检查

| 工具 | 检测 | 装法 |
|---|---|---|
| draw.io CLI | `ls /Applications/draw.io.app` | `brew install --cask drawio` |
| mmdc | `which mmdc` | `brew install mermaid-cli` 或 `npm install -g @mermaid-js/mermaid-cli` |
| matplotlib | `python3 -c 'import matplotlib'` | `pip3 install matplotlib` |
| Microsoft YaHei 字体 | `fc-list \| grep -i yahei` | 从 Windows 复制 msyh.ttf 到 ~/Library/Fonts/ |

**一键检测脚本**：

```bash
#!/usr/bin/env bash
echo "=== diagram 依赖检测 ==="
ls /Applications/draw.io.app &>/dev/null && echo "[OK] draw.io" || echo "[MISSING] draw.io — brew install --cask drawio"
which mmdc &>/dev/null && echo "[OK] mmdc $(mmdc --version 2>/dev/null | head -1)" || echo "[MISSING] mmdc — brew install mermaid-cli"
python3 -c 'import matplotlib' 2>/dev/null && echo "[OK] matplotlib" || echo "[MISSING] matplotlib — pip3 install matplotlib"
fc-list 2>/dev/null | grep -qi yahei && echo "[OK] Microsoft YaHei" || echo "[WARN] Microsoft YaHei 未安装，macOS fallback 到 PingFang SC"
```

## 交付前 checklist

- [ ] 渲染分辨率 ≥ 2400px 宽（嵌 16:9 PPT 不糊）
- [ ] 字体统一（Microsoft YaHei；fallback 链 PingFang SC → Source Han Sans CN）
- [ ] 配色与 PPT 主题一致（[[pptx]] design-system.md 同色板）
- [ ] 无 emoji 滥用（用 ⚠ ⛔ ✓ ✗ 替代）
- [ ] XML 转义正确（`&` → `&amp;`，`<` → `&lt;` 等）
- [ ] edge 用 source/target id 而非硬编码坐标
- [ ] 多图共享配色时用 sed 批量替换，不手动一张张改
- [ ] sketch=0（不加 hatch 纹理）
- [ ] 长英文节点加 `whiteSpace=wrap`

## 工具对比速查

| 维度 | draw.io | Mermaid | matplotlib | pptx-native |
|---|---|---|---|---|
| 学习曲线 | 中（mxGraph XML） | 低（DSL） | 中（Python API） | 中（python-pptx） |
| 坐标控制 | 精确手工 | 自动布局 | 精确（pyplot） | 精确（Emu） |
| 中文字体 | ✅ 强 | ⚠️ 中 | ⚠️ 需 rcParams | ✅ 直接设 FONT_CN |
| 数据驱动 | ❌ 弱 | ⚠️ 中 | ✅ 强 | ❌ 弱 |
| 渲染速度 | 慢（Electron） | 快 | 快 | 快（无渲染） |
| PPT 内可编辑 | ❌ 位图 | ❌ 位图 | ❌ 位图 | ✅ 原生形状 |
| 安装 | brew cask 150MB | npm/brew | pip | 无需额外安装 |
| **最佳场景** | **复杂架构 / 多图** | **简单流程** | **数据可视化** | **≤ 5 节点可编辑** |

## Anti-prompt（让模型不走弯路）

```
- 不要把 Heiti SC 作为默认字体 — 用 Microsoft YaHei
- 不要给大背景 box 加 sketch=1 — 会变 hatch 纹理遮挡前景
- 不要用默认 --width 渲染 PNG — 必须 --width 3200
- 不要在 mxCell value 里用裸 \n — 用 XML entity &#xa;
- 不要 ≤ 10 张图选 draw.io — 用 Mermaid 更快
- 不要 > 10 张图选 Mermaid — subgraph 配色控制弱
- 不要边 edge 用纯坐标定起止 — 用 source/target ID 引用节点
- 不要多工具混搭（draw.io + Mermaid 混用）— 视觉割裂
```
