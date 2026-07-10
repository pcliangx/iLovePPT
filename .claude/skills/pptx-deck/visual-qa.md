# 逐页视觉自检 prompt 与流程

本文档定义逐页视觉自检的 prompt 模板 + fix 循环 + 17 项 deck checklist。是 iloveppt-builder agent Step 3(视觉 QA 循环 ≤ 3 轮)的 checklist,也被 [workflow.md](workflow.md) 在 Stage E 的"Step 3 视觉 QA"步骤引用。

## 严格分工 —— 本 checklist 只查机械视觉,不评认知接收

本文档的 17 项 checklist 是 **iloveppt-builder Step 3 的机械视觉检查表**:字号 / 对齐 / 颜色 / 文字溢出 / 留白 / footer / 表格 banding 等**可量化机械项**。

**认知接收**(论点清晰度 / 节奏感 / 记忆点 / 哪页让读者走神 / 5 秒能否抓到要点)**不在此 checklist 范围内**,由 `iloveppt-audience` agent 评分(见 `${CLAUDE_PROJECT_DIR}/.claude/agents/iloveppt-audience.md`,用自定义 4 维度评分)。

| iloveppt-builder Step 3(本文档) | audience(iloveppt-audience.md) |
|---|---|
| 字号失衡 / 对齐错位 / 颜色违规 | 论点清晰度 / 信息密度感受 |
| 文字溢出 / shape 重叠 / footer 缺失 | 这页 5 秒能不能抓到要点 |
| chart 渲染破损 / 字体 fallback | 章节节奏感 / 走神点 |
| 自动可修(决策 8a 边界内) | 不自动修(回 author 大改) |

若某项既机械又有认知含义(例如"留白比例 ≥ 15%"),归 iloveppt-builder(可量化优先归机械)。

---

视觉 QA 是一个 **Claude 执行的检查步骤**:`build.py` 渲染 PNG → Claude 用 Read 工具读图 → 按 checklist 打分 → 编辑 `deck_plan.json` → 重跑 `build.py`。没有对应的 Python 占位函数。

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

## fix → 重渲染 → 再 check 循环

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

iloveppt-builder Step 3 在逐页 QA 全部通过后(进 Step 4 之前)对全 deck 做一次复核:

### 字体一致性

- **全量机械审计**（替代旧"抽 5 页 grep"抽样流程）：

  ```bash
  python3 ${CLAUDE_PROJECT_DIR}/scripts/audit_pptx.py <deck.pptx> --sections fonts
  ```

- 期望 ea 全是 `Microsoft YaHei`（或 theme yaml `fonts.ea` 声明值）
- ERROR（run 只写 `<a:latin>` 未写 `<a:ea>` 的经典 bug）→ 警告并记录进 `review_needed[category: font_ea]`，不阻止交付；这是 helpers 层代码 bug 信号，改 deck_plan 治不了
- WARNING（继承链 / theme ea 为空）→ 记录数量即可
- builder Step 2.9 在 build 后已跑过一次；本节复核时若 deck_plan 改过重 build，需重跑

### 机械几何审计（读 PNG 之前先跑 · 精度项机械化）

LLM 读 120dpi JPG 测不准 0.1" 级差异——越界 / 文字重叠 / 跨页标题一致性这三类
精度检查交给 XML 机械审计，**读图人审只管机械查不了的**（配色 / 留白观感 / 层级美感）：

```bash
python3 ${CLAUDE_PROJECT_DIR}/scripts/audit_pptx.py <deck.pptx> --sections geometry --format text
```

- `off_canvas`：含文字 shape / 图片越出画布（无文字装饰出血是正常设计，已豁免）
  → 对应页改 deck_plan 字段（通常字数超限撑大 textbox），重 build
- `text_overlap`：同页两个文字 shape bbox 相交 > 35%（装饰大数字 ≥ 100pt 已豁免）
  → 真文字压字，必修；通常是 layout 字段给太长
- `title_alignment`：左锚页标题（24-40pt · x<3"）的 x 锚点偏离中位 > 0.1" 或字号
  偏离众数 → 对照"跨页字号一致"checklist 项判断是否 by-design（如 summary 36pt
  是 make_summary 有意为之则记 evidence 放行，不是则修）
- findings 全 advisory（exit code 不受影响），每条必须在 QA 记录里给 [已修 / by-design 放行 + 理由]，不允许无声跳过

### 页脚 / 页码完整性

- 每页（除 `cover` / `section_divider` / `closing`）应有页脚
- 页码格式：`N / TOTAL`（如 `3 / 12`）
- 用 `slide.placeholders` 枚举，检查 placeholder idx=12（页码位）是否存在

### 章节扉页配对

- 每个 `section_divider` 之后应有 ≥ 1 内容页
- `toc.sections` 的长度 == `section_divider` 出现次数
- `section_divider.num` 连续递增（1, 2, 3 …），无跳号

---

## 视觉 QA checklist（17 项，deck 级）

> 本 checklist 对应 [evals/rubric.md](${CLAUDE_PROJECT_DIR}/evals/rubric.md) 的 **Design（设计）维**（D1–D14）；Content / Coherence 维的全面评估见该文档。

完成所有单页 check 后，对整个 deck 做最终核查：

### 基础

- [ ] **无重叠**：所有元素 z-order 正常，无文字穿形状
- [ ] **无截断**：所有文本框内容完整显示，无省略号或被裁剪
- [ ] **字体统一**：全 deck 使用 Microsoft YaHei / Source Han Sans CN（正文） + Bold（标题）
- [ ] **配色一致**：色值仅来自 `BRAND_*` / `GRAY_*` 套色板，无随机色
- [ ] **字号层级清晰**：封面 48pt + / 页标题 32pt + / 正文 18-20pt / 表格 14pt / 页脚 9pt；**相邻层级字号差 ≥ 20%**（32pt 标题 ÷ 18pt 正文 = 1.8x ✓；20pt 副标题 vs 18pt 正文 ✗ = 层级失败，二选一调开）
- [ ] **留白达标**：左右边距 ≥ 0.55"、底部 ≥ 0.5"，离页边无元素
- [ ] **对齐网格**：同类元素左对齐 / 居中对齐一致；优先使用 12-col grid (`grid_columns`),无随机偏移
- [ ] **表格无意外 banding**：无意外横纹，行高均匀
- [ ] **卡片圆角随 theme 风格**：`adjustments[0] ≤` theme `style.radius_medium`（未声明 style 时默认 soft 配方 = 0.05），不过圆；theme 声明 rounded / pill 配方时按其上限放宽（数值表见 `themes/_base.py STYLE_RECIPES`）
- [ ] **装饰大字号 word_wrap=False**：`single_focus.big_number` 不换行
- [ ] **textbox margin 归零**：所有文本框已调用 `H.fix_textbox_margins()`
- [ ] **引用图分辨率清晰**：`pic_text.image_path` / matplotlib chart 宽度 ≥ 1600px

### 进阶（5 项）

- [ ] **单页留白比例 ≥ 15%**:Read 渲染 PNG 估算"内容覆盖面积",白底面积应 ≥ 15%(空荡比塞满好。塞满 = "无信息层次")
- [ ] **重要信息在左上热区**:F 型阅读路径下,最关键卡片 / 数据应在 slide 左 1/3 或顶部 1/3,不要放在右下(70% 读者忽视)
- [ ] **主色面积比例 ≤ 30%**:60-30-10 规则。单页 BRAND_PRIMARY 实际覆盖面积 ≤ 30%;ACCENT ≤ 10%。剩余 ≥ 60% 应是中性(白 / GRAY_50 / GRAY_300)
- [ ] **数据 slide 有 source 标注**:`table` / `pic_text`(数据图)/ `single_focus`(大数字)必须有 `source` 字段或可见的 "Source:" 引文。咨询稿合规硬要求
- [ ] **action title ≤ 24 字 不换行**:页面标题不能折行(折行会破坏装饰元素定位)。> 24 字必须重写

### Deck-level 一致性(跨页核查)

- [ ] **同 layout 跨页对齐**:连续 N 张 cards 页第一张卡的左缘 x 坐标完全一致(同样适用 compare 第一列、pic_text 图片左缘)。优先用 `grid_columns` 锚定
- [ ] **配色比例各页相近**:不允许"前半 deck 蓝主导,后半灰主导"——每页主色 / 次色 / 中性占比方差应小
- [ ] **字号层级各页一致**:`make_*` 同一函数在不同页应渲染同字号(不允许 page 1 标题 32pt、page 5 标题 28pt)

### 审美负面规则(反 AI 痕迹,deck 级 3 项)

借鉴 mavis pptx skill 的负面清单 —— 以下是"AI 生成 deck"的标志性特征,全 deck 禁止:

- [ ] **标题下无 accent 装饰线**:标题下方细横线 / 短色杠是 AI 痕迹 #1;层级感用留白 / 字号 / 背景色块表达,不用线
- [ ] **正文不居中**:正文段落 / bullet 列表一律左对齐;居中只允许标题、封面元素、大数字 callout
- [ ] **无纯文字页**:每个内容页至少 1 个非文字元素(图表 / 卡片 / 图标 / 数据 callout);连续 ≥ 2 页纯 bullet 墙 → 记 `review_needed`

---

## 与 deck_plan.json / content.md 的关系

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
- 不要用"标题下加装饰线"提升设计感 — 那是 AI 痕迹,层级用留白和字号表达
