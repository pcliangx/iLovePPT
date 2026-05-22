# iLovePPT Eval Baseline Scorecard

> 记录于 v2 重构后。对比基准——后续改 layout/build 代码后重跑 eval，fail 项变多即回归。

## 01_short （6 页）

- page 2, #13 — TOC 页三条目之间有大片空白（条目顶部堆叠，中段留白过宽），内容未均布
- page 3, #13 — section_divider 数字方块与标题仅占左上区域，下方 2/3 为空白，未居中
- page 4, #13 — bullet 列表三条集中在页面中偏下区域，标题与内容之间大片空白
- page 5, #13 — numbered_list 三个蓝色方块各自内容只有一行文字，方块高度过高（占全页高度约 80%），显得空旷

其余页（cover、closing）全部通过。

## 02_long （28 页，抽检 cover/TOC/divider/content×3/summary/closing）

抽检页：page-01、02、03、04、07、14、26、27、28

- page-03, #13 — section_divider 数字方块与标题仅占左上 1/3 区域，下方大片空白，未居中
- page-04, #13 — bullet 列表（3 条）集中在页面中偏下，上方大片空白
- page-07, #13 — bullet 列表（3 条）集中在页面中偏下，上方大片空白

其余抽检页（cover、TOC、cards 内容页、summary、closing）全部通过。此问题为 section_divider 与 bullet_list 布局的系统性问题，与 01_short 同类。

## 03_cards （5 页）

- page 2, #13 — 双卡片内容（一行文字）顶部对齐，卡片下半部为大片空白；内容稀少但卡片高度固定
- page 3, #13 — 三卡片同上，每张卡仅一行正文，下半部空白明显
- page 4, #13 — 四卡片同上，每张卡仅一行正文，下半部空白明显

其余页（cover、closing）全部通过。此为卡片内容较少时固定高度导致的已知空旷现象。

## 04_compare （4 页）

全部通过。

备注：page-2 两张卡片 accent bar 颜色不同（左蓝、右青），系设计层面对比色意图，非渲染错误。

## 05_pictext （3 页）

全部通过。

page-2 pic_text 布局：左侧图片占位块（纯蓝）+ 右侧三张特性卡，布局匹配意图，无溢出/重叠。

## 06_table （4 页）

全部通过。

page-2、3 表格行 banding 为交替浅蓝/白，属于设计内预期样式，非意外 banding（rubric #10 通过）。

## 07_chinese （6 页）

- page 1, #12 — 封面标题"人工智能驱动的新一代企业数字化转型解决方案全景评估报告"字号较大、文字较长，导致换行并形成 3 行（最后两字"报告"单独成行），大字号文本异常换行

其余页（TOC、bullet 内容×3、closing）全部通过。中文字体正常渲染（无 Arial/花体 fallback）。

## 08_template_extract （3 页）

全部通过。

模板主色提取（4F81BD）正确应用，页面布局与 tech_blue 主题一致。

---

## 汇总

- 总检查页数: 37（01_short 6页 + 02_long 抽检 9页 + 03_cards 5页 + 04_compare 4页 + 05_pictext 3页 + 06_table 4页 + 07_chinese 6页 + 08_template_extract 3页，注：02_long 仅抽检，实际 28 页）
- 总 fail 项: 9
- 已知问题清单:
  1. **#13 空白过多（系统性）**：section_divider 和内容稀少时的 bullet_list 页面上方留有大片异常空白，内容未居中/均布。影响 01_short（3处）、02_long（2处抽检发现）、03_cards（3处）。
  2. **#12 大字号换行（07_chinese page 1）**：封面标题过长，导致装饰大字号在最后异常折行成 3 行，最后一行仅两字。
