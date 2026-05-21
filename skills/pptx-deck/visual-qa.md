# 逐页视觉自检 prompt 与流程

本文档定义 `vision_check` 的 prompt 模板 + fix 流程 + 12 项 deck checklist。被 [workflow.md](workflow.md) Step 4 引用。

---

## 单页 vision 自检 prompt 模板

[workflow.py](workflow.py) 渲染每页 PNG 后，Claude 用 Read 工具读图，然后用以下 prompt 思考：

```
你审视的是 PPT 第 {idx}/{total} 页，期望意图：{intent}（layout={spec.layout}）。
渲染图：{image_path}

请找出以下问题（assume 有问题，不要试图确认"没问题"）：

 1. 元素重叠：文字穿过形状 / 卡片相互覆盖 / 线条压住文字
 2. 文字溢出框：截断 / 标题换行成两行但装饰按一行布局
 3. 中文字体 fallback：Arial 字形显示汉字 / cursive 花体 / 大间距宽体
    期望字体：Microsoft YaHei（正文） + Microsoft YaHei Bold（标题）
 4. 标题与内容区距离失衡：> 0.8" 或 < 0.3"
 5. 颜色对比度不足：深底深字 / 浅底浅字（WCAG AA 需 ≥ 4.5:1）
 6. layout 与意图不符：要点 5 个却用了 single_focus
 7. 数字 / 图表位置偏右 / 偏下：textbox margin 未归零
 8. 装饰线 / 配色 / 字体与全 deck 不一致（BRAND_* / GRAY_* 套色板）
 9. 留白边界不达标：< 0.5" 离页边（左右 ≥ 0.55"，底 ≥ 0.5"）
10. 表格意外 banding：横纹穿过单元格，干扰阅读
11. emoji 误用 / 显示为方块（除 ⚠ ⛔ 🔒 警示性 emoji 外均不应出现）
12. 装饰大字号换行：180pt 数字或 single_focus 的 big_number 变两行

输出 JSON（直接供 fix_slide 使用）：

[
  {
    "issue": "描述（一句话）",
    "severity": "low | med | high",
    "suggested_fix": "改 X 函数 / 调 Y 参数 / 换 Z layout"
  }
]

若全无问题，输出 []。
```

---

## 单页渲染脚本

[workflow.py](workflow.py) 中 `render_one_slide(prs, idx, out_png)` 的流程：

1. 将整个 deck 临时导出为 PDF（`soffice --headless --convert-to pdf`）
2. 用 `pdftoppm` 截取第 `idx` 页为 jpg
3. 重命名输出到 `out_png`

速度参考：~3-4s / 页（soffice 启动 ~1.5s + 转换 + pdftoppm 0.3s）。

对于大型 deck（> 20 页），建议批量渲染后再逐页 check，而非每页渲染一次 soffice。

---

## fix → 重渲染 → 再 check 循环

```
generate_slide(spec)
  ↓
render_one_slide(prs, idx) → png
  ↓
vision_check(png, intent, spec) → issues
  ↓
[issues 非空，attempts < 3]
  → fix_slide(slide, issues)
  → render_one_slide → vision_check
  → 循环

[issues 为空]
  → 下一页 ✓

[attempts ≥ 3]
  → 标记 review_needed[idx]
  → 接受当前 slide，继续下一页
```

---

## fix_slide 实现策略

`fix_slide` 根据 `issue.suggested_fix` 字符串关键词决策修法：

| suggested_fix 关键词 | 修法 |
|---|---|
| `"字号过大"` | 减小对应 `set_font(size=N)` 调用的 `N`；参考 [[pptx]] [helpers.py](../pptx/helpers.py) |
| `"margin 未归零"` | 对遗漏的 textbox 补调 `H.fix_textbox_margins()` |
| `"layout 不符"` | 换用其他 `theme.make_*` 函数重新生成本页（不是微调参数） |
| `"颜色对比低"` | 改用 `H.WHITE` / `H.GRAY_900` 等高对比色 |
| `"字体 fallback"` | 检查 `set_font` 是否漏处理某个 run；或提示用户安装 Microsoft YaHei |
| `"装饰数字换行"` | textbox 加宽 / 设 `word_wrap=False` |
| `"重叠"` | 检查 z-order；重叠元素调 `slide.shapes._spTree` 顺序 |
| `"溢出框"` | 缩短文本（回到 content-writing.md 字数约束）或放大容器 |

骨架版（[workflow.py](workflow.py)）暂不实现自动 fix — Claude 在调用时手动修改 `page_spec` 后重跑 `generate_slide`。

---

## 降级策略

单页修 ≥ 3 次仍有 `high` severity issue → 降级处理：

1. 接受当前版本（不再修改）
2. 将该页加入 `review_needed` 列表，记录最后一次 issues
3. 继续处理下一页

**不允许死循环**：≥ 3 次 fix 还没好，大概率是 layout 选错（不是字号 / 位置能修的），降级让用户最后人工审。

`low` severity issue 累积 ≥ 5 个，等同 `high`，也进入降级流程。

---

## 全 deck 复核（deck_review）

[workflow.md](workflow.md) Step 5 在所有 slide 通过后执行：

### 字体一致性

- 抽 5 页随机 run，grep XML 中 `<a:ea>` `typeface` 属性
- 期望全是 `Microsoft YaHei`（或 `Microsoft YaHei Bold`）
- 若出现 fallback 字体（Arial、PingFang、SimSun）→ 警告并记录，不阻止交付

### 页脚 / 页码完整性

- 每页（除 `cover` / `section_divider` / `closing`）应有页脚
- 页码格式：`N / TOTAL`（如 `3 / 12`）
- 用 `slide.placeholders` 枚举，检查 placeholder idx=12（页码位）是否存在

### 章节扉页配对

- 每个 `section_divider` 之后应有 ≥ 1 内容页
- `toc.sections` 的长度 == `section_divider` 出现次数
- `section_divider.num` 连续递增（1, 2, 3 …），无跳号

---

## 视觉 QA checklist（12 项，deck 级）

完成所有单页 check 后，对整个 deck 做最终核查：

- [ ] **无重叠**：所有元素 z-order 正常，无文字穿形状
- [ ] **无截断**：所有文本框内容完整显示，无省略号或被裁剪
- [ ] **字体统一**：全 deck 使用 Microsoft YaHei（正文）+ Microsoft YaHei Bold / Heavy（标题）
- [ ] **配色一致**：色值仅来自 `BRAND_*` / `GRAY_*` 套色板，无随机色
- [ ] **字号层级清晰**：封面 44pt+、页面标题 20pt+、正文 11-14pt
- [ ] **留白达标**：左右边距 ≥ 0.55"，底部 ≥ 0.5"，离页边无元素
- [ ] **对齐网格**：同类元素左对齐 / 居中对齐一致，无随机偏移
- [ ] **表格无意外 banding**：无意外横纹，行高均匀
- [ ] **卡片圆角小**：`adjustments[0] ≤ 0.05`（约 5% 圆角），不过圆
- [ ] **装饰大字号 word_wrap=False**：`single_focus.big_number` 不换行
- [ ] **textbox margin 归零**：所有文本框已调用 `H.fix_textbox_margins()`
- [ ] **引用图分辨率清晰**：`pic_text.image_path` 图片宽度 ≥ 1600px

---

## 与 brief.yaml 的关系

vision QA 通过后，`review_needed` 清单附在最终交付旁，告知用户哪些页需人工审阅。用户选项：

- 自己修改 `brief.key_points` 重新跑 [workflow.py](workflow.py)
- 直接编辑输出的 .pptx
- 接受 `review_needed` 状态交付

---

## Anti-prompt

- 不要 `vision_check` 失败 N 次后还硬重试 — 达到 3 次直接降级，不再循环
- 不要让 `fix_slide` 修改 layout 类型 — 修字号 / 位置 / 颜色可以；要改 layout 应走重新生成
- 不要 `vision_check` 时声称 "看起来 OK" 而不细查 — 默认 assume 有问题，仔细找
- 不要忽略 low severity issue 累积 — 累积 ≥ 5 个 low 等同 1 个 high
- 不要在 deck_review 通过后反复回 single-slide 修 — 标 `review_needed` 后向前推进
- 不要跳过 Microsoft YaHei 字体检查 — 字体 fallback 是最常见的中文 PPT 问题
- 不要把渲染失败（soffice crash）当成视觉问题处理 — 先排查 workflow.py 渲染步骤
