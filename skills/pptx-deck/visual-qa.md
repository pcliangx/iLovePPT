# 逐页视觉自检 prompt 与流程

本文档定义逐页视觉自检的 prompt 模板 + fix 循环 + 12 项 deck checklist。被 [workflow.md](workflow.md) Step 5 引用。

视觉 QA 是一个 **Claude 执行的检查步骤**：`build.py` 渲染 PNG → Claude 用 Read 工具读图 → 按 12 项 checklist 打分 → 编辑 `deck_plan.json` → 重跑 `build.py`。没有对应的 Python 占位函数。

---

## 单页 vision 自检 prompt 模板

`build.py` 渲染每页 PNG 后，Claude 用 Read 工具读图，然后用以下 prompt 思考：

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

输出 JSON（供 Claude 修改 deck_plan.json 时参考）：

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

## 单页渲染（build.py 流程）

`build.py` 在生成 `.pptx` 后自动渲染 PNG（除非传 `--no-render`）：

1. 调用 `soffice --headless --convert-to pdf` 将整个 deck 导出为 PDF
2. 用 `pdftoppm` 将每页转为 PNG，输出到与 `.pptx` 同目录的 `slides/` 子目录

速度参考：~3-4s / 页（soffice 启动 ~1.5s + 转换 + pdftoppm 0.3s）。

对于大型 deck（> 20 页），建议一次性全渲染后再逐页 check，而非每页重跑 build.py。

---

## fix → 重渲染 → 再 check 循环（v2 流程）

```
Claude 产出 deck_plan.json
  ↓
python3 build.py deck_plan.json → .pptx + PNG
  ↓
Claude 逐页 Read PNG → 对照 12 项 checklist 输出 issues JSON
  ↓
[issues 非空，attempts < 3]
  → Claude 编辑 deck_plan.json（修字段 / 换 layout / 调文字长度）
  → 重跑 build.py → 再 Read PNG → 再 check
  → 循环

[issues 为空]
  → 下一页 ✓

[attempts ≥ 3]
  → 标记 review_needed[idx]
  → 接受当前版本，继续下一页
```

---

## fix 策略（Claude 编辑 deck_plan.json）

Claude 根据 `issue.suggested_fix` 决策如何修改 `deck_plan.json`：

| suggested_fix 关键词 | 修法（在 deck_plan.json 中） |
|---|---|
| `"字号过大"` | 裁剪该字段文字至 content-writing.md 字数约束 |
| `"layout 不符"` | 将该 slide 的 `layout` 字段换成更合适的 layout 名称，并调整相应字段 |
| `"颜色对比低"` | 在 deck_plan.json 的 theme 层面换用更高对比配色；或提示用户修改主题文件 |
| `"字体 fallback"` | 提示用户安装 Microsoft YaHei；检查是否传入了正确 theme |
| `"装饰数字换行"` | 缩短 `big_number` / `big_text` 字段内容 |
| `"重叠"` | 裁剪文字 / 换 layout（多数重叠问题是内容过长导致的） |
| `"溢出框"` | 缩短文本至字数约束（参考 content-writing.md 各 layout 上限） |

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

> 本 checklist 对应 [evals/rubric.md](../../evals/rubric.md) 的 **Design（设计）维**（D1–D14）；Content / Coherence 维的全面评估见该文档。

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

- 修改 `deck_plan.json` 重跑 `python3 build.py deck_plan.json`
- 直接编辑输出的 .pptx
- 接受 `review_needed` 状态交付

---

## Anti-prompt

- 不要视觉 check 失败 N 次后还硬重试 — 达到 3 次直接降级，不再循环
- 不要用修字号 / 位置 / 颜色来掩盖 layout 选错的问题 — layout 不符时直接换 layout 名重新渲染
- 不要视觉 check 时声称 "看起来 OK" 而不细查 — 默认 assume 有问题，仔细找
- 不要忽略 low severity issue 累积 — 累积 ≥ 5 个 low 等同 1 个 high
- 不要在 deck_review 通过后反复回 single-slide 修 — 标 `review_needed` 后向前推进
- 不要跳过 Microsoft YaHei 字体检查 — 字体 fallback 是最常见的中文 PPT 问题
- 不要把渲染失败（soffice crash）当成视觉问题处理 — 先排查 build.py 渲染步骤
