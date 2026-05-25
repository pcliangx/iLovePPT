# 每页文案拓写规范

本文档定义 13 种 layout 各自的文案约束 + LLM 拓写 prompt 模板。被 [workflow.md](workflow.md) 引用。

> 拓写文案**之前**先做图层规划：判断哪些章节该配图。规则见 [diagram-planning.md](diagram-planning.md)。需配图的章节,主线程 Claude 先调 [[diagram]] skill 出 PNG 到 `_assets/charts/`,再在 markdown 用 `![title](_assets/charts/X.png)` 嵌入。

---

## 本文档的两类消费者

| 消费者 | 在哪步用本文档 | 用法 |
|---|---|---|
| **author agent**(Stage C-D) | 设计 outline + 拓写 content | 按 13 layout 文案规则写;按 Pyramid 5 件套设计 outline;按 markdown schema 输出 .md |
| **iloveppt agent**(Stage E build) | 拿到 content.md → md→JSON | 反向应用规则:验证 md 合规、推断 layout、转 JSON |

---

## 13 layout 文案规则

| layout | 字数 / 句式约束 | 反例 |
|---|---|---|
| cover | 主标题 ≤ 20 字、副标 ≤ 24 字、不堆头衔 | "关于 XX 公司 2026 年战略发展规划暨数字化转型实施路径研讨" |
| toc | 章节 ≤ 6、每章 ≤ 12 字、动宾对齐 | "公司发展的历史背景与现状分析" |
| section_divider | 章节号 + 标题（≤ 10 字），layout 独立于内容页 | 与内容页同 header |
| single_focus | 1 句话 ≤ 12 字 + 1 数字（72pt+）+ 1 行解释 ≤ 20 字 | 5 个要点平铺 |
| compare | N 列对比表(header bar 风,跟 cards 视觉拉开)。每列 title ≤ 6 字、body ≤ 22 字、句式对称。可加 `recommended: true` 标主推列(蓝 header + 浅蓝 body + 绿 ✓ 徽章) | 标题长度差 2×;3 列里 0 列主推(没主张) |
| **compare_pk** | **对决式两选一**。`left/right={title ≤ 8 字, body ≤ 40 字}`。中间巨型 VS 圆,适合 before/after、新旧 PK、二选一 | 三方对比硬塞(应该用 compare);body 写成 1 个词没说服力 |
| **matrix_2x2** | **BCG 2×2 矩阵**。`x_axis/y_axis = {low, high}`(≤ 8 字),4 quadrants(pos = tl/tr/bl/br),`title ≤ 8 字`、`body ≤ 25 字`,1 个 quadrant 加 `highlight: true` | 4 格写 4 个不相关的点(矩阵的意义是同一维度二分类);轴标签写成完整句 |
| cards | 每卡标题 ≤ 6 字、body ≤ 18 字（N 列，cards 列表） | body 一长一短 |
| bullet_list | 每点 ≤ 12 字、句式一致（动宾或名词性结构） | 一点一句话一点一段 |
| table | 列 ≤ 5、行 ≤ 7、单元格 ≤ 8 字 | 把段落塞进单元格 |
| pic_text | 左图右文，右侧 N 个说明卡片，每卡 ≤ 15 字 | 图占满 + 文字塞角落 |
| summary | 3-5 条结论，每条 ≤ 15 字，有数字佐证 | 重复 outline 章节 |
| closing | 极简："谢谢" + 联系方式或下一步 (≤ 24 字) | 又一页要点总结 |

> **字号基线**:body 18-20pt(投影可读最低)。字数上限按 18pt 单元宽度推算。
> action title 单独约束见下一节,**≤ 24 字**(超限会换行破布局)。

> 上表所有含"标题"的 layout，其 title 应是「行动式标题」（见下节 deck 级论证结构）。

---

## 双模式字数表(brief.presentation_mode 控制)

上表是 **speaker 模式**(默认,BCG 现场演讲风,讲者补充,文字关键词化)的字数限制。**handout 模式**(无讲者,读者自读手册风)字数限制约 **3-4×**:

| 字段 | speaker | handout |
|---|---|---|
| cards body | ≤ 18 字 | ≤ 80 字 |
| bullet items | ≤ 12 字 | ≤ 40 字 |
| summary 条目 | ≤ 15 字 | ≤ 60 字 |
| compare body | ≤ 22 字 | ≤ 80 字 |
| compare_pk left/right body | ≤ 40 字 | ≤ 120 字 |
| matrix_2x2 quadrant body | ≤ 25 字 | ≤ 80 字 |
| table 单元格 | ≤ 8 字 | ≤ 25 字 |
| pic_text point body | ≤ 15 字 | ≤ 50 字 |
| single_focus explanation | ≤ 20 字 | ≤ 60 字 |
| **action_title** | **≤ 24 字(两 mode 一致,硬约束)** | **≤ 24 字** |
| cover.subtitle | ≤ 24 字 | ≤ 24 字 |

### 选哪个模式

brainstorm 在 Stage B 必须问用户(默认 speaker,brainstorm.md 已规定):

- (a) `speaker` —— 现场演讲(讲者补充,文字少 / 关键词)
- (b) `handout` —— 阅读手册(无讲者,文字完整句 / 3-4× 信息密度)
- (c) 双用途 → 推默认 speaker,有需要时出 handout 第二份

### handout 拓写要求(author Stage D 必看)

- **不要写关键词** —— 读者只看文字,没有讲者补充。每个 bullet 都要是**完整可读的句子**
- 句末加句号(speaker 可省,handout 不省)
- 数据 source 引文位置同 speaker,但 source 来源要给全(speaker 可只写"内部数据",handout 要写"内部数据 · 财务部 2026-Q1 报表")
- pic_text body 要解释图,不只是 caption

action title 在两种 mode 字数限制一致(24 字硬约束) —— 那是 textbox 高度的工程约束,跟模式无关。

---

## deck 级论证结构（核心要求:麦肯锡金字塔原理）

> **iLovePPT 的内容设计核心要求**:整份 deck 必须按麦肯锡金字塔原理(Minto Pyramid Principle)组织。
> 这不是"建议遵守",而是 Stage C outline 必须通过的硬约束 —— [iloveppt-author agent](${CLAUDE_PROJECT_DIR}/.claude/agents/iloveppt-author.md) state file 强制包含 `top_recommendation` / `scqa` / `pyramid_known_issues` 字段,任一不过即不能交付。author / critic / iloveppt 三层 Pyramid 防线均不接受"先放着"含糊过关。

金字塔原理由五件套组成,缺一不可:

### ① 单一顶端论点（Top Recommendation / BLUF）

整份 deck **只服务于一个**核心推荐或判断 —— 它就是金字塔的顶点。所有章节、所有页面都是为它做支撑。

- ✗ "我们来讨论 AI 4A 评审办法"(议题陈述,不是论点)
- ✗ "AI 4A 评审办法值得关注"(模糊,无行动指向)
- ✓ "应当本季度落地 AI 4A 评审办法,5 阶段每阶段 ≤ 3 天"(推荐 + 边界 + 节奏)

顶端论点写在 `cover.subtitle` 或第 1 张 `single_focus`(BLUF 提前),也是 `summary.conclusions` 的核心收口。author state file 字段:`top_recommendation`。

### ② SCQA 开场（Situation / Complication / Question / Answer）

整份 deck 的前 1/4 必须按 SCQA 展开,把听众"拉进同一个问题语境":

| 元素 | 作用 | 典型篇幅 |
|---|---|---|
| **S - Situation**(背景) | 听众认同的客观事实 | 1-2 页 |
| **C - Complication**(冲突/变化) | 打破现状的事件、矛盾、风险 | 1-2 页 |
| **Q - Question**(由 C 产生的关键问题) | 听众心里冒出的"那怎么办" | 隐含在 C 之后,或 1 页明示 |
| **A - Answer**(顶端论点) | 直接给出推荐 = ① | 1 页 single_focus / cover.subtitle 提前 |

author state file 字段:`scqa: {situation, complication, question, answer}`。

### ③ 答案在前（BLUF, Bottom Line Up Front）

金字塔原理的核心节奏:**结论先行,论据在后**。在三个层级都贯彻:

| 层级 | 答案在前的体现 |
|---|---|
| **deck 级** | cover.subtitle 已陈述顶端论点;或第 1 张 single_focus 把 Answer 摆出来,后面所有章节都是支撑 |
| **章节级** | 每个 `section_divider` 标题是该节的**结论句**,不是话题名("3 个核心改进" → "三层架构把交付周期从 2 周压到 2 天") |
| **页级** | 每页 `action_title` 是结论,bullet / cards / table 是证据 |

读者从任何一层切入,先看到的都是"答案",再看到"为什么"。

### ④ 横向 MECE 支撑（Mutually Exclusive, Collectively Exhaustive）

顶端论点之下,放 **3-5 个**支撑论点(= deck 的 3-5 个内容章节)。它们必须:

- **相互独立(ME)**:章节之间不重叠,不能"评审范围"和"评审流程"塞同一组要点
- **完全穷尽(CE)**:加起来能完整支撑顶端论点,听众听完不会问"那 X 呢?"

排列方式有讲究,选其一并保持一致:

| 排列方式 | 何时用 |
|---|---|
| **时间序** | 阶段、路线图、迭代节奏 |
| **结构序** | 模块、层、维度(空间 / 组织 / 系统组成) |
| **重要性序** | 影响力从大到小 |
| **演绎序** | 大前提 → 小前提 → 结论 |

author state file 字段:`mece_check_passed: true`(必须经过 MECE 自检并标记通过)。

### Action title 字数硬约束

每页 `title` (= action title) **必须 ≤ 24 字**(中文计 1 字,英文计 0.5)。

| 原因 | 后果 |
|---|---|
| `_add_title` textbox 高度 = `Inches(0.9)`,32pt 单行装满约 26 字符 | > 24 字会换行,装饰元素按"标题占一行"算定位 → 视觉破坏 |
| 行业实践:BCG action title 平均 16-22 字 | 中文 deck 略宽,留 24 字上限是工程兜底 |

**违规处理**(author Stage C + iloveppt Stage E 都要检查):

- 超 24 字:**必须重写**(不允许"差几个字算了")
- 重写策略:删修饰词("非常"/"持续"/"全面"),拆成主谓宾干句,数字代替形容词

**反例 → 对例**:

| ✗ 超 24 字 | ✓ ≤ 24 字 |
|---|---|
| "应当在本季度落地 AI 4A 评审办法,5 阶段每阶段不超过 3 天" (29 字) | "本季度落地 AI 4A,5 阶段 ≤ 3 天" (18 字) |
| "我们建议采用三层架构把交付周期从 2 周压缩到 2 天" (27 字) | "三层架构把交付从 2 周压到 2 天" (16 字) |

---

### ⑤ 纵向疑问/回答链

金字塔自上而下的**每一层**,都在回答上一层引出的"为什么 / 怎么做 / 是什么":

```
顶端: 应当本季度落地 AI 4A 评审办法
   ↓ (为什么?)
章节 1 action_title: AI 工具铺开,但架构评审仍靠人,质量飘移        ← 背景问题
章节 2 action_title: 覆盖 4A:Application/Architecture/Auth-N/Auth-Z 全闭环  ← 范围
章节 3 action_title: 5 阶段串行,每阶段 ≤ 3 天,卡点不超 1 周        ← 怎么做
章节 4 action_title: 评审委员会 + AI 助手预审,降 60% 人力        ← 组织保障
章节 5 action_title: Q3 试点 2 业务线,Q4 全公司                      ← 落地节奏
   ↓ (每一节的页面继续回答该节标题引出的疑问)
```

章节标题串起来 = 顶端论点的完整论据链。把所有章节 + 页面 action_title 抽出来读一遍 —— 应当读出一个**自洽的故事**(这就是 ghost deck test,现为 Pyramid 自检的一项)。

---

### Pyramid 自检表（Stage C 必过,iloveppt Stage E 之前)

| # | 自检项 | 通过标准 |
|---|---|---|
| 1 | **单一顶端论点存在** | `top_recommendation` 字段非空,是完整推荐句(动宾结构 + 具体边界),不是议题陈述 |
| 2 | **SCQA 完整** | `scqa` 四字段全部非空;C 真的是冲突/变化,不是 S 的复述;A == 顶端论点 |
| 3 | **答案在前** | cover.subtitle 或第 1 内容页明示顶端论点;每个 section_divider 标题是结论句 |
| 4 | **MECE 通过** | 章节数 3-5;两两之间无内容重叠;加起来能完整支撑顶端论点(自问"听众会问'那 X 呢'吗") |
| 5 | **章节排列方式一致** | 时间/结构/重要性/演绎,选一种贯穿 |
| 6 | **纵向疑问链通过(ghost deck test)** | 所有 action_title 按顺序读,能讲出顶端论点的完整论据链;若有任一标题与上层论点无关或断裂,重排 |
| 7 | **action title 全是结论句** | 没有任何一页用名词短语标题("市场背景" / "技术方案" 一律禁用) |

任何一项不通过 → 不交付 outline,在 `missing_fields` 列出该项,要求用户补 brief 或自动回去重排。**不要硬出大纲后让 Stage E 蒙混过关**。

### 豁免路径(单项软阻塞)

某项不过时,不允许"先放着" / "不管它"含糊回避,**强制用户二选一**:

1. **豁免某项** —— 必须附理由(例:"豁免第 3 项,理由:数据下周才有,本节先用占位")
   - 理由写进 author state file 的 `pyramid_known_issues: [{item: 3, reason: "...", approved_at: "<ISO>"}]`
   - iloveppt Step 0 再跑 Pyramid 时,fail 项若被 author 豁免,会在 error 里附 `author_known_issues_note` 让用户最终决定
   - critic 也会读 outline 末尾 unchecked 项,失败项若有理由可标注
2. **改某项** —— 收用户指令改 outline,改完重跑 7 项自检

不接受的回答(必须重问):
- "先放着" / "后面再改" / "不管它" / "差不多就行" / 沉默不回

这是软阻塞,不阻断用户节奏,但留 audit 痕迹。

### 纯展示场景的豁免路径

下列场景**不是论证型 deck**,Pyramid 自检会有部分项失败 —— 通过 author state `pyramid_known_issues[]` 显式豁免(附理由):

- **纯数据汇报 / 月报 / 周报**:章节是数据维度而非论证(销售 / 流量 / 成本各 1 节),没有"推荐"也没有"冲突"
- **培训 / 教学 deck**:目标是讲解知识结构,不是说服决策
- **目录式索引 deck**:产品手册、能力清单、人员介绍等

action title ≤ 24 字硬约束(第 7 项)始终保留,排版工程约束不豁免。豁免必须由用户在 brainstorm 阶段明确说明,author 不自行判断 —— 99% 的提案 / 路演 / 汇报场合都应走金字塔。

### 与逐页拓写的衔接

- `section_divider` / `bullet_list` / `cards` / `compare` / `single_focus` / `table` / `pic_text` 的 `title` 字段都应是 action title(结论句)
- `cover.title` 是 deck 主题;`cover.subtitle` 是顶端论点(BLUF)
- `summary.conclusions` 是论证收口,与 `top_recommendation` 呼应,不能新增未出现过的论点
- Pyramid 自检通过后,`outline` 决定 `deck_plan.json` 的 slides 骨架

---

## 拓写指令模板

给 LLM 用的 prompt（在 workflow Step 4 Claude 页面拓写时使用）：

```
你正在生成 PPT 第 {idx}/{total} 页。
本章节：{section_title}
本页 layout：{layout_type}
本页意图：{intent}
顶端论点（贯穿全 deck，本页应支撑）：{top_recommendation}

请输出 deck_plan.json 中该 slide 的 JSON 对象，字段对应 {layout_type} 的参数：

cover:            { layout, title, subtitle }
toc:              { layout, sections: [str, ...] }
section_divider:  { layout, num: int, title }
single_focus:     { layout, big_text, big_number, explanation }
compare:          { layout, title?, items: [{title, body, recommended?: bool}, ...] }
compare_pk:       { layout, title, left: {title, body}, right: {title, body} }
matrix_2x2:       { layout, title, x_axis: {low, high}, y_axis: {low, high},
                    quadrants: [{pos: "tl"|"tr"|"bl"|"br", title, body, highlight?: bool}, ...] }
cards:            { layout, title?, cards: [{title, body}, ...] }
bullet_list:      { layout, title, items: [str, ...] }
table:            { layout, title, headers: [str, ...], rows: [[str, ...], ...] }
pic_text:         { layout, title, image_path, points: [{title, body}, ...] }
summary:          { layout, conclusions: [str, ...], title? }
closing:          { layout, subtitle? }

> `title?` / `subtitle?` 带 `?` 为可选字段。`compare.title` 默认"对比"——
> 建议显式传更具体的页标题（如"现状 vs 目标"）。`closing.subtitle` 默认空(只显大字"谢谢")。
> `compare` / `cards` 的列数由 `items` / `cards` 列表长度决定（N 列）。
> `compare.items[i].recommended=true` 标主推列(蓝 header + 浅蓝 body + 绿 ✓);
> `matrix_2x2.quadrants[i].highlight=true` 标主推象限。同页最多 1 个高亮。

遵循约束（详见上表）：
- 字数限制严格执行，超出则裁剪，不得将约束视为建议
- 句式一致：bullet_list 全动宾 / 全名词性，不混用
- 数字 > 文字：能用数字就别用形容词
- 不使用 emoji，除 ⚠ ⛔ 🔒 警示性场景
- 不堆形容词："高效"/"创新"/"领先" 一律删除
```

### page_spec 验证规则

生成完成后，调用方需校验：

| 字段 | 校验逻辑 |
|---|---|
| `title` / `subtitle` | `len(text) ≤ 上限` |
| `sections` | `len(list) ≤ 6` |
| `items` | 每项 `len ≤ 14` 且句式一致 |
| `cards` | 每卡 `body len ≤ 30` |
| `conclusions` | `3 ≤ len(list) ≤ 5`，每条含数字 |
| `headers` | `len(list) ≤ 5` |
| `rows` | `len(list) ≤ 7`，每格 `≤ 8 字` |

---

## 跨页内容设计

### 节奏感（页序）

```
cover
  → toc
  → section_1_divider → [1-3 内容页]
  → section_2_divider → [1-3 内容页]
  → ...
  → summary
  → closing
```

规则：
- 每个 section 至少 1 内容页，最多 3 内容页
- cover / toc / closing 全 deck 各出现 1 次
- section_divider 数量与 toc.sections 数量严格对应

### 变化感(cards 类视觉去同质化)

cards / compare 实现上都是"横向卡片列",视觉上**同属一类**。即使三页 layout 字段不同(cards/cards/compare),滚动看到的还是连排白卡 → 给读者"排版单一"的体感。

**两条硬规则**:

1. **≥ 2 张 cards-like(`cards` 或 `compare`)layout 连续 → 警告**
   - cards-like 含:`cards` / `compare`
   - 不含:`compare_pk`(对决式)/ `matrix_2x2`(矩阵)/ `bullet_list` / `table` / `pic_text` / `summary` / `single_focus`(都是差异化布局)
   - 触发时:必须改至少 1 页用上方差异化 layout,或用 `recommended` 字段在 compare 上引入"高亮对比"视觉冲击

2. **≥ 3 张任意相同 layout 连续 → 警告**(原规则保留)
   - 仅同 layout 字段名比较;`section_divider` 不计入

合理的连续相同 layout 场景(白名单):

- 3-4 张 `cards` 是产品模块 / 案例**且每张视觉强差异**(如带不同 icon、不同主推标)
- 2 张 `table` 是同一组数据的不同切片(明显数据延续)

警告(不强制阻断,但提醒考虑):

- 连续 cards-like → 提示"是否能改 1 页用 `compare_pk`(对决)/ `matrix_2x2`(矩阵)/ `bullet_list` 打破节奏?"
- `cover` / `toc` / `closing` 全 deck 各 1 次,无连续问题

### 强调感（关键论点单独成页）

- 整 deck 最关键的 1-2 个论点用 `single_focus`（大字号 + 大数字）
- **二选一 / 新旧对决**用 `compare_pk`(中间巨型 VS,视觉冲击最强)
- **二维分类**(如"高/低价值 × 高/低难度")用 `matrix_2x2`(BCG 风,可高亮主推象限)
- 数据密集页用 `table`；多列对比用 `compare`(可带 `recommended` 高亮主推)
- 流程类用 `bullet_list`（步骤有序）；分类类用 `cards`

---

## 内容拓写原则（按重要性）

1. **数字 > 文字**：能用数字就别形容词。"显著提升" → "提升 80%"；"大量节省" → "节省 3.2 小时/天"
2. **动宾结构**：bullet items 用"动词 + 宾语"对齐。"推进数字化" / "建立机制" / "完善体系"
3. **删冗余形容词**："高效的" / "先进的" / "创新的"通常可直接删除，意义不减
4. **首字母大小写一致**：英文标题 Title Case 或 sentence case，deck 内统一，不混用
5. **缩写首次给全称**：第一次出现"4A"写成"4A（Application / Architecture / Authentication / Authorization）"
6. **不用 emoji**（除警示）：⚠ ⛔ 🔒 可用；🚀 ✅ 🎉 不要
7. **标点一致**：中文内容统一用中文标点；英文 inline 内容用英文标点；deck 内不混用
8. **数字单位一致**：全 deck 统一用"%" 或 "个百分点"，不混用

---

## 一致性 checklist（拓写完 outline 后自检）

- [ ] 标题大小写、标点风格一致（"。" / "." / 不用句号，选一贯穿）
- [ ] 数字单位统一（"%" vs "个百分点" vs "pp"）
- [ ] 缩写首次出现给全称，后续可简写
- [ ] 不出现通用形容词（"高效"、"创新"、"优秀"、"先进"）
- [ ] 章节扉页 `num` 与 toc 章节顺序严格一致
- [ ] 总结页结论与 brief 顶端论点 + outline 章节呼应（不新增未出现过的论点）
- [ ] 封底 `subtitle` 不超 30 字
- [ ] `bullet_list` 所有 items 同一句式（不混用动宾 / 名词性）
- [ ] `cards` 每卡 body 长度差 ≤ 30%（视觉平衡）
- [ ] `table` 列标题与行内容语义对齐（列是维度，行是实例）

---

## 与 brief.md 字段的映射

brief.md schema 见 [pipeline-protocol.md §3](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md#3-brainstorm-收齐字段后的总结--确认-gate)。author Stage C/D 在拓写时如下消费这些字段：

| brief.md 字段 | 用于拓写的位置 |
|---|---|
| `top_recommendation` | `cover.subtitle` (BLUF) + `summary.conclusions` 核心收口 |
| `scqa` (situation/complication/question/answer) | cover 后第 1-2 内容页的开场叙述 |
| outline 章节(brainstorm 推断,author Stage C 在 outline.md 里确定) | `toc.sections` + 每节 `section_divider.title` |
| `audience` | 语气校准（technical → 精确数字；executive → 结论先行；general → 类比；sales → 卖点） |
| `duration_min` | 估算页数(1 min ≈ 1.5 页)+ 内容密度(时长短 → 减 bullet) |
| `presentation_mode` | speaker / handout 字数表切换(见上方"双模式字数表") |
| `theme`(若是 .pptx 模板) | 由 [template-extract.md](template-extract.md) 提取主色与字体覆盖 theme |
| `asset_inventory` | author 拓写 pic_text / chart 时优先用用户提供的素材 |

---

## 语气校准（audience 字段）

| audience 值 | 语气风格 | 示例 |
|---|---|---|
| `executive` | 结论先行，数字突出，每页一个论点 | "成本下降 40%，3 个月回本" |
| `technical` | 步骤详细，技术术语可用，数字精确 | "P99 延迟从 820ms 降至 130ms" |
| `general` | 类比辅助，避免术语，结论清晰 | "每天节省 1 小时重复工作" |
| `sales` | 价值主张突出，对比竞品，行动导向 | "选我们：快 3× 、省 50%" |

当 `audience` 未填写时，默认 `general`。

---

## Markdown schema(主线程 ↔ agent 接口契约)

流程用 markdown 文档作为用户与 agent 之间的接口。两份文件:`deck_v{N}_outline.md`(大纲)和 `deck_v{N}_content.md`(全文)。**agent 只认 content.md,outline.md 是给用户审用的中间产物。**

### `deck_v{N}_outline.md` schema

```markdown
---
title: <主标题, ≤ 20 字>
subtitle: <副标, ≤ 24 字>
audience: executive | technical | general | sales
duration_min: <int>
theme: tech_blue                       # 或 .pptx 模板绝对路径
output: ./deck_v1.pptx
top_recommendation: <完整推荐句>        # Pyramid ①
scqa:                                   # Pyramid ②
  situation: <背景>
  complication: <冲突>
  question: <问题>
  answer: <= top_recommendation>
footer_meta:                            # author Stage C 出 outline 时默认填,用户可改
  classification: INTERNAL              # 默认 INTERNAL;可改 CONFIDENTIAL / PUBLIC
  project: <从 working_dir 推断的 deck_slug>  # 默认从工作目录名推断,例:"claude-code-training"
  version: v1.0                         # 默认 v1.0,跟 author state.iteration 同步(每次 +1 → v2.0 / v3.0 ...)
---

# Outline

## 1. <action title - 句, ≤ 24 字>
- intent: <这节要让读者明白什么>
- layout: bullet_list | cards | compare | single_focus | table | pic_text
- data: <关键数据点,逗号分隔>
- diagram: <无 | drawio:flow | matplotlib:bar | ...>
- pattern_hints:                        # 2026-05-25 新增 · author Stage C Step 1A.5 用 search.sh 选
    selected: <pattern-id>              # 从 RAG top-5 选 1-2 个,如 process-5-step-linear
    rationale: <一句话理由,为什么选这个 pattern>
    alternatives: [<id>, <id>, <id>]    # top-5 里没选的 3-4 个,给用户审 outline 时看候选

## 2. <action title>
- intent: ...
- layout: ...
- ...

# Pyramid 自检
- [x] ① 单一顶端论点
- [x] ② SCQA 完整
- [x] ③ 答案在前(cover.subtitle 已含 / 第 1 内容页明示)
- [x] ④ MECE(3-5 节,两两不重叠)
- [x] ⑤ 纵向疑问/回答链(章节标题串读能讲完整故事)
- [x] ⑥ 字段完整
- [x] ⑦ 全部 action title ≤ 24 字
```

### `deck_v{N}_content.md` schema(agent 的输入)

```markdown
---
# 完全继承 outline.md 的 frontmatter
title: ...
subtitle: ...
audience: ...
top_recommendation: ...
scqa: {...}
footer_meta: {...}
output: ./deck_v1.pptx
based_on: deck_v1_outline.md
---

# Content

## [cover]
- title: <同 frontmatter.title>
- subtitle: <同 frontmatter.subtitle>
- prepared_by: 技术部
- date: 2026-05-23
- version: v1.0
- classification: INTERNAL

## [toc]
- <章节 1 title>
- <章节 2 title>
- ...

## [section_divider]
- num: 1
- title: 背景

## 1. <action title 与 outline 保持一致>
<!-- layout: bullet_list -->

- <bullet 1, ≤ 12 字>
- <bullet 2>
- <bullet 3>

> 数据:Source: <数据来源>

## 2. <action title>
<!-- layout: cards -->

- **<卡标题, ≤ 6 字>**: <body, ≤ 18 字>
- **<卡标题>**: <body>
- **<卡标题>**: <body>

## 3. <action title>
<!-- layout: pic_text -->

![<图描述>](_assets/charts/<filename>.png)

- **<点标题, ≤ 6 字>**: <body, ≤ 15 字>
- **<点标题>**: <body>

> 数据:Source: <数据来源>

## [summary]
- <结论 1, ≤ 15 字, 含数字>
- <结论 2>
- <结论 3>

## [closing]
- subtitle: <联系方式 / 行动号召, ≤ 24 字>
- next_steps:                          # 可选 - 结构化 closing
  - action: <动作>
    owner: <负责人>
    due: <YYYY-MM-DD>
  - action: ...
```

### h2 命名约定

| h2 形式 | 含义 |
|---|---|
| `## [cover]` / `## [toc]` / `## [section_divider]` / `## [summary]` / `## [closing]` | 特殊 layout slide,**不**含 action title |
| `## N. <action title>` | 内容页,N 是章节序号(对应 outline),后跟 ≤ 24 字 action title |
| `## <非 N. 开头, 也非 [xxx]>` | **非法**,agent 应报错 |

### layout 推断规则(agent 用)

`<!-- layout: X -->` HTML 注释指定时,**直接用**;无注释时按下表推断:

| md 结构信号 | 推断 layout |
|---|---|
| 单层 `-` list,无加粗,每项短 | `bullet_list` |
| `-` list,每项形如 `**xxx**: yyy` | `cards`(若 ≥ 3 项)或 `compare`(若 = 2 项) |
| 一个 `![alt](path)` + 后续 list | `pic_text` |
| 含 `|` 表格语法 | `table` |
| 仅 1 个加粗大字 + 1 行说明 | `single_focus`(看 frontmatter 是否有 big_number) |

推断无果 → 默认 `bullet_list`;agent 应在 review_needed 标注"layout 默认推断,请人审"。

### 图片引用约定

- `![alt](_assets/charts/X.png)` —— 数据图(matplotlib 生成)
- `![alt](_assets/refs/X.png)` —— 用户提供的图
- 路径必须**相对 markdown 文件所在目录**
- agent 在 md→JSON 转换时,把相对路径解析为绝对路径写入 `image_path`

### 数据来源约定

任何 `## N. xxx` 标题下,若该 slide 含数据(数字 / 图表),**必须**在 list 之后加一条:

```markdown
> 数据:Source: <具体来源>
```

build.py 自动识别为 source citation,渲染在 footer 上方 italic GRAY_500。

### 字数限制(同上方"13 layout 文案规则"表)

agent 在 md→JSON 转换时**必须强制校验**:超限的字段触发 auto_md_edit(自动截短),并记录到 `auto_md_edits[]`。

---

## 素材文件夹布局

每份 deck 在工作目录下应有如下结构:

```
<deck-工作目录>/
├── deck_v1_outline.md           # 用户审 outline 用
├── deck_v1_content.md           # 用户审 content 用,agent 的输入
├── deck_v1.pptx                 # build.py 产出
├── deck_v1_render/              # 渲染图(.gitignore'd)
│   ├── page-01.jpg
│   └── ...
├── _assets/
│   ├── raw/                     # 用户提供的原始素材(对话中收集)
│   │   ├── q4_revenue.csv
│   │   ├── customer_logos.png
│   │   └── industry_report.pdf
│   ├── charts/                  # matplotlib / draw.io 生成的图
│   │   ├── q4_revenue.png
│   │   └── review_flow.png
│   └── refs/                    # 用户直接给的参考图(不重做)
│       └── existing_diagram.png
└── deck_v2_*.md / deck_v2.pptx  # 后续迭代版本(决策 7a)
```

### 素材摄入(主线程 Stage B)

主线程在 Stage A 对话中识别用户有素材时,**主动 prompt**:

| 信号 | prompt 模板 |
|---|---|
| 用户提到"数据 / 报表 / 增长 / 对比" | "你这边有具体数据吗?可以:① 直接粘贴(我现场 parse) ② 给文件路径(.csv / .xlsx) ③ 让我帮你编合理数据(标注 '示意')" |
| 用户提到"我们的架构 / 现有图 / 流程图" | "已有图的话告诉我路径(.png / .jpg);否则我用 draw.io 现画,你审了再用" |
| 用户提到"按某个模板 / 我们公司 PPT" | "把模板 .pptx 路径给我,我提取色板和字体(不复制内容)" |
| 用户提到"参考 / 之前的报告" | "可以给参考文档路径,我提取关键论点供拓写参考" |

提供后,主线程负责把素材**落到正确文件夹**(`mv` 或 `cp` 到 `_assets/raw/`),然后才进 Stage C 内容规划。

### 多版本管理(决策 7a)

- 第一稿:`deck_v1_outline.md` / `deck_v1_content.md` / `deck_v1.pptx`
- 用户大改 → 新版:`deck_v2_*.md`(不覆盖 v1,留对照)
- 小改(改一个字)→ 直接改 `deck_v1_content.md`,重 build → 覆盖 `deck_v1.pptx`(允许)
- `_assets/` 跨版本共享(charts 重生成的话覆盖即可)

---

## 估算页数（duration_min 参考）

| 时长 | 建议总页数 | 内容页密度 |
|---|---|---|
| 10 min | 8-12 页 | 每页 3-5 个 bullet 或 1 组数据 |
| 20 min | 15-20 页 | 每页 4-6 个 bullet 或 1 张表 |
| 30 min | 22-28 页 | 可含 2-3 个 `table` + 多个 `compare` |
| 45 min | 30-38 页 | 章节更多；每章可有 3 内容页 |
| 60 min | 40-50 页 | 通常需要 `pic_text` 补充图例 |

公式参考：`total_slides ≈ duration_min × 1.5`（含 cover / toc / divider / closing 各 1 页）。

---

## 打印 / PDF 导出指南

PPT 主用于屏幕投影,但很多场景需要打印 / 导出 PDF 分享。以下规范避免常见翻车:

| 场景 | 问题 | 应对 |
|---|---|---|
| 屏幕色 → CMYK 打印 | `#0A52BF`(屏幕饱和蓝)打印偏紫 | 重要文件用 grayscale 打印,或印前转 CMYK 校色 |
| 黑白复印 | 9pt GRAY_500 页脚 → 复印后消失;BRAND_TINT 浅蓝底 → 灰得几乎看不到 | 关键文字别用 ≤ 9pt 灰色;别把信息只放在 TINT 底色上 |
| PDF 导出 | LibreOffice / PowerPoint 导出 PDF 时 PNG 可能压缩,失去清晰度 | 用 `soffice --convert-to pdf` 而非"打印到 PDF";嵌入 PNG ≥ 1600px |
| 分级文件分发 | classification 是徽标,容易被遮 | `footer_meta.classification` 会在每页页脚出现;cover 右上角也单独显示一次 |
| 中文字体丢失 | 接收方未装雅黑,PDF 显示宋体 fallback | 导出 PDF 时勾选"嵌入字体"选项(`soffice --convert-to "pdf:writer_pdf_Export:EmbedStandardFonts=true"`) |

**重要原则**:任何要"打印 + 分发"的 deck,导出 PDF 前用 grayscale 预览校验一遍,确认页脚 / 页码 / 数据 source 全部可读。

---

## Anti-prompt

- 不要在 `single_focus` 放 5 个 bullet —— 该 layout 只承载 1 个核心数字 + 1 行解释
- 不要在 `toc` 里写出完整段落 —— 章节标题 ≤ 12 字，是导航，不是摘要
- 不要把 `summary` 写成 `toc` 的重复 —— 总结页要给出结论，不是重列章节名
- 不要在 `closing` 塞要点列表 —— 封底只有"谢谢" + 联系方式，period
- 不要在 `table` 单元格写长句 —— 超 8 字的内容应拆分或换 `bullet_list`
- 不要跳过字数校验步骤 —— 拓写完必须过 checklist，不能"看起来差不多"
- 不要忽略 `duration_min` —— 时间短的 deck 要主动删内容页，不能塞满
- 不要让相邻页 layout 相同 —— 节奏感是 deck 质量的重要维度
