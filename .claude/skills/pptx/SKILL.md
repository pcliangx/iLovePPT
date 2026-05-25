---
name: pptx
description: .pptx 文件底层读写操作。覆盖 markitdown 提取文本、unpack/pack XML、模板加载与局部修改、跨平台中文字体 EA 字段（默认 Microsoft YaHei）、LibreOffice 渲染验证。被 [[pptx-deck]] 调用,也可独立用于"只读已有 PPT"或"模板小改"。触发：读取 .pptx / 提取文字 / 解包 .pptx / 改模板 / unpack / 演示文稿 / 幻灯片。
---

# pptx skill — .pptx 读写底层

## 场景路由

| 场景 | 子文档 |
|---|---|
| 从零创建 PPT | [creating.md](creating.md) |
| 基于模板编辑 | [editing.md](editing.md) |
| 读取/提取内容 | [reading.md](reading.md) |
| 配色/字体/12 helper | [design-system.md](design-system.md) |

## 依赖检查

```bash
bash scripts/check_deps.sh
```

输出 ✅/❌/⚠️ 检查 python-pptx / lxml / markitdown / Pillow / soffice / pdftoppm / 微软雅黑（macOS）。

## 路径决策（3 选 1）

| 路径 | 何时选 | 代价 |
|---|---|---|
| **`pptx` 局部改** | 已有 .pptx,改 ≤ 5 张文字 | 几行；不适合从零 |
| **基于模板 + 代码混合** | 仓库已有 .pptx 模板,需版本化重生成 | ~500 行；保模板视觉投入 |
| **python-pptx 全定制** | 没模板,跨平台中文,23+ 页 | ~800 行；复用率 90% |

判定经验：
- 用户抱怨"字体丑 / 表格乱 / 中文字体不对"→ 基本需要"全定制"或"模板混合"——纯手动无法根治
- 用户指定了模板路径 → 必走"模板混合"，先用 `scripts/thumbnail.py` 分析模板
- 没模板且跨平台 → 走"全定制"，约 800 行 Python，但复用率高

## 跨场景共识

- **中文字体默认 Microsoft YaHei**，跨平台 EA 字段必写（详见 [helpers.py](helpers.py) `set_font` / `_fix_ph_font`）
- LibreOffice 渲染 PDF → pdftoppm PNG 视觉验证闭环
- 12 个核心 helper 入口见 [design-system.md](design-system.md)

⚠️ **macOS 渲染验证前需装雅黑**：把雅黑字体放到 `~/Library/Fonts/`，否则 LibreOffice fallback 到 PingFang SC，与 Windows PowerPoint 显示不一致。

## 与 [[pptx-deck]] / [[diagram]] 的关系

- [[pptx-deck]] 端到端生成器调本 skill 的 `helpers.py`、`layout.py` 与 `scripts/`
- [[diagram]] 出图 skill 调本 skill 的 `embed_picture` helper 嵌入 PNG

## 模块列表

| 模块 | 用途 |
|---|---|
| `helpers.py` | 低层 pptx 原语（set_font / card / bullets / table_modern / embed_picture 等）+ 设计 token（BRAND_* / FONT_* / 灰阶）|
| `layout.py` | 几何原语（Box、content_region、full_region、columns、rows、stack、split、inset）— 主题无关，供 make_* 函数使用 |

## 交付前 checklist

**通用 13 项**：
- [ ] 跨平台中文字体（用 lxml 写 `<a:ea>` + `<a:cs>`）
- [ ] 没有文字被截断 / 溢出 / 遮挡（LibreOffice 实测）
- [ ] 没有 emoji 滥用（仅 ⚠ ⛔ 🔒 警示性）
- [ ] 单一主色 + 1 强调色（≤ 9 个色变量：4 BRAND + 5 灰阶）
- [ ] 表格关 `firstRow` / `bandRow`（防 banding）
- [ ] 大字号 textbox 设 `word_wrap=False`
- [ ] 所有 textbox 设 `margin_left/right = 0`
- [ ] `line_spacing` 显式设置（标题 1.0 / 正文 1.45）
- [ ] 每页有页脚 + 页码 `N / TOTAL`
- [ ] 章节扉页与内容页 layout 不同
- [ ] 图片用 `height=Inches(N)` 等比缩放（不变形）
- [ ] 不依赖 PrinceXML / 商业 PDF 引擎
- [ ] 可用 `python3 build.py` 一键重生成

**模板路径专项 4 项**：
- [ ] 加载后已用 `clear_template_slides(prs)` 清空样例 slide
- [ ] 所有 placeholder 用 `_fix_ph_font(ph, ...)` 修字体（非 `set_font(run, ...)`）
- [ ] 对照 LibreOffice 输出页数 vs `len(prs.slides)` 一致
- [ ] 已知该模板的可用 layout / 配色 / 字体坑

## 依赖安装（完整）

| 用途 | 工具 | 装法 |
|---|---|---|
| PPT 生成 | `python-pptx ≥ 1.0` | `pip3 install python-pptx lxml` |
| 文字提取 | `markitdown` | `pip3 install "markitdown[pptx]"` |
| 视觉验证 | `soffice`（LibreOffice） | `brew install --cask libreoffice` |
| PDF → PNG | `pdftoppm`（poppler） | `brew install poppler` |
| 缩略图生成 | `Pillow` | `pip3 install Pillow` |

⚠️ 不要装 PrinceXML / pandoc-with-prince。
