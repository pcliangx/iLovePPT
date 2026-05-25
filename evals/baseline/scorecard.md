# iLovePPT Eval Baseline Scorecard（PPTEval 三维）

> 按 evals/rubric.md 三维评测。固定 eval 夹具是 filler 内容，**仅 Design 维为确定性回归信号**；
> Content / Coherence 维对 filler 夹具标 N/A，仅在评真实 deck 时打分。
> 记录于 v2 + PPTEval rubric 采纳后。

## Design 维（D1-D14）—— 固定夹具回归基准

### 01_short （6 页）

- page 2（toc）— **D10** FAIL：目录三条目集中在上方，条目之间及下方大片空白，内容未均布
- page 4（bullet_list）— **D10** FAIL：三条 bullet 集中在页面中偏下区域，标题与内容区之间大片空白
- page 5（summary,3 个 numbered 方块视觉）— **D10** FAIL：三个蓝色数字方块各自仅一行文字在方块顶部，方块下半段大片空白（短内容留白已知限制)
- page 1（cover）— 通过
- page 3（section_divider）— 通过（数字方块与标题垂直居中）
- page 6（closing）— 通过

### 02_long （28 页，抽检 10 页：01, 02, 04, 07, 10, 15, 20, 25, 27, 28）

- page-04（bullet_list 3条）— **D10** FAIL：内容集中在中偏下，标题与内容区之间大片空白
- page-07（bullet_list 3条）— **D10** FAIL：同上
- page-20（cards 3张）— **D10** FAIL：每张卡片内容（一行正文）集中在顶部，卡片下方约 60% 为空白
- page-27（summary,4 个 numbered 方块视觉）— **D10** FAIL：四个蓝色方块各仅一行文字，方块内下方大片空白
- page-01（cover）— 通过
- page-02（toc）— 通过
- page-10（bullet_list）— **D10** FAIL：三条 bullet 内容聚集在页面下半段，大片空白
- page-15（section_divider）— 通过
- page-25（bullet_list 4条）— 通过（内容较多，空白可接受）
- page-28（closing）— 通过

### 03_cards （5 页）

- page 2（双卡片）— **D10** FAIL：每张卡片内容（标题+一行文字）集中在卡片顶部，下半约 60% 为空白
- page 3（三卡片）— **D10** FAIL：同上，三张卡片均有明显内部空白
- page 4（四卡片）— **D10** FAIL：同上，四张卡片均有明显内部空白
- page 1（cover）— 通过
- page 5（closing）— 通过

### 04_compare （4 页）

- page 2（双对比卡片）— **D10** FAIL：两张卡片内容在顶部，下约 50% 为空白
- page 3（三对比卡片）— **D10** FAIL：三张卡片下半均有明显空白。（注：中间卡片 accent 为 teal、左右为蓝,是 `make_compare` 交替 accent 的有意设计,teal = `H.ACCENT` 品牌色,**不计 D8 fail**。）
- page 1（cover）— 通过
- page 4（closing）— 通过

### 05_pictext （3 页）

- page 2（pic_text）— **D10** FAIL：左侧图区为纯蓝占位块（无实际图像），三张右侧文本卡各自内容仅占卡片顶部约 30%，下方大片空白；布局与意图整体相符（D6 通过），无重叠/溢出
- page 1（cover）— 通过
- page 3（closing）— 通过

### 06_table （4 页）

- 全部通过（D1–D14 均无 fail）
- 说明：page-2、3 表格行交替浅蓝/白 banding 为设计内预期样式，非意外 banding（D12 通过）

### 07_chinese （6 页）

- page 1（cover）— **D14** FAIL：封面标题"人工智能驱动的新一代企业数字化转型解决方案全景评估报告"字号大、字数多（21 汉字），在封面框内换行为 2 行，"方"字在行尾折行（"解决方 / 案全景评估报告"）；大字号装饰性标题异常换行
- page 3（bullet_list 6条）— **D10** FAIL：六条 bullet 集中在页面下半段，标题与内容区之间大片空白
- page 4（bullet_list 6条）— **D10** FAIL：同上
- page 5（numbered_list 4项）— **D10** FAIL：四个蓝色数字方块各仅一行文字，方块下方大片空白
- page 2（toc）— 通过
- page 6（closing）— 通过
- 备注：中文字体正常渲染（无 Arial/花体 fallback，D3 通过）；已知限制：07_chinese 封面标题为超长压力测试输入

### 08_template_extract （3 页）

- 全部通过（D1–D14 均无 fail）
- 说明：模板主色提取（4F81BD）正确应用，页面布局与 tech_blue 主题一致

---

## Content / Coherence 维

固定夹具为 filler 内容，本两维不适用（N/A）。评真实生成的 deck 时按 rubric.md 的 C / H 项打分。

---

## 汇总

- Design 维检查页数: 37（01_short 6页 + 02_long 抽检 10页 + 03_cards 5页 + 04_compare 4页 + 05_pictext 3页 + 06_table 4页 + 07_chinese 6页 + 08_template_extract 3页；02_long 实际 28 页，仅抽检）
- Design 维总 fail 项: 19（剔除 1 项 D8 误判,见下）
- 已知限制:
  1. **D10 系统性空白（bullet_list）**：bullet_list 页标题与内容区之间大片空白；影响 01_short、02_long、07_chinese。
  2. **D10 系统性空白（cards / compare 短内容）**：卡片高度固定,短内容（filler 夹具）时卡内下半空白明显；影响 03_cards、04_compare、02_long、07_chinese。卡片高度自适应内容是更大的改动,留待后续。
  3. **D10 toc 间距**：01_short page 2 三条目拉伸间距过大，整体偏空旷。
  4. **D14 大字号换行**：07_chinese page 1 封面超长标题（21 汉字）换行，压力测试预期边缘情况（content-writing.md 规定封面 ≤ 20 字）。
- 已剔除的误判:
  - ~~D8 accent 色不一致（04_compare page 3 中间卡 teal）~~ —— teal 是 `make_compare` 交替 accent 的有意设计,`H.ACCENT` 本就是品牌色,不算 fail。
