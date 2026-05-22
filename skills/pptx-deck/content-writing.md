# 每页文案拓写规范

本文档定义 11 种 layout 各自的文案约束 + LLM 拓写 prompt 模板。被 [workflow.md](workflow.md) Step 4（Claude 页面拓写）引用。

> 拓写文案**之前**先做图层规划（workflow Step 3）：判断哪些章节该配图。规则见 [diagram-planning.md](diagram-planning.md)。需配图的章节,Claude 先调 [[diagram]] skill 出 PNG,再把该页直接写成 `pic_text` 版式（左图右文）,`image_path` 指向 PNG,右侧 N 个说明卡片文案从该节要点提炼。

---

## 11 layout 文案规则

| layout | 字数 / 句式约束 | 反例 |
|---|---|---|
| cover | 主标题 ≤ 20 字、副标 ≤ 30 字、不堆头衔 | "关于 XX 公司 2026 年战略发展规划暨数字化转型实施路径研讨" |
| toc | 章节 ≤ 6、每章 ≤ 12 字、动宾对齐 | "公司发展的历史背景与现状分析" |
| section_divider | 章节号 + 标题（≤ 10 字），layout 独立于内容页 | 与内容页同 header |
| single_focus | 1 句话 ≤ 12 字 + 1 数字（72pt+）+ 1 行解释 | 5 个要点平铺 |
| compare | 左右标题各 ≤ 6 字、句式对称（N 列，items 列表） | 标题长度差 2× |
| cards | 每卡标题 ≤ 6 字、body ≤ 30 字（N 列，cards 列表） | body 一长一短 |
| bullet_list | 每点 ≤ 14 字、句式一致（动宾或名词性结构） | 一点一句话一点一段 |
| table | 列 ≤ 5、行 ≤ 7、单元格 ≤ 8 字 | 把段落塞进单元格 |
| pic_text | 左图右文，右侧 N 个说明卡片，每卡 ≤ 20 字 | 图占满 + 文字塞角落 |
| summary | 3-5 条结论，每条 ≤ 18 字，有数字佐证 | 重复 outline 章节 |
| closing | 极简："谢谢" + 联系方式或下一步 | 又一页要点总结 |

> 上表所有含"标题"的 layout，其 title 应是「行动式标题」（见下节 deck 级论证结构）。

---

## deck 级论证结构（先于逐页拓写）

拓写每一页之前,先把整份 deck 设计成**一个论证**,而不是一堆话题的拼盘。

### 行动式标题（action title）

每个内容页的标题是**一句完整的结论**,不是话题标签。读者只看标题就知道这页要说什么。

- ✗ 话题标签："市场背景" / "技术方案" / "效果数据"
- ✓ 行动式："SaaS 市场三年翻倍,渗透率仍不足 15%" / "三层架构把交付周期从 2 周压到 2 天" / "上线 3 月,人均每天省 1.2 小时"

### 金字塔结构（Minto）

整份 deck 是一条论证链,常见骨架：

```
背景 situation → 问题 / 冲突 complication → 方案 resolution → 证据 → 结论
```

或"结论先行":核心结论放在 summary 之前就立住,各章是支撑论据。`outline` 不是话题清单,而是这条论证链的展开。

### Ghost deck test（幽灵 deck 测试）

把所有页的 action title 按顺序抽出来单独读一遍 —— 它们应当**独立讲出完整故事**。
若抽出的标题读起来是断的、跳跃的、或全是名词短语,说明论证结构没立住 —— 回去重排 `outline`,而不是硬拓写。

### 与逐页拓写的衔接

- `section_divider` / `bullet_list` / `cards` / `compare` / `single_focus` / `table` / `pic_text` 的 `title` 字段都应是 action title。
- `cover.title` 是 deck 的主命题;`summary` 是论证的收口结论。
- 这一步在 workflow 的图层规划前后做,产出的 `outline` 决定 `deck_plan.json` 的 slides 骨架。

---

## 拓写指令模板

给 LLM 用的 prompt（在 workflow Step 4 Claude 页面拓写时使用）：

```
你正在生成 PPT 第 {idx}/{total} 页。
本章节：{section_title}
关键信息（从 brief.key_points）：{key_points}
本页 layout：{layout_type}
本页意图：{intent}

请输出 deck_plan.json 中该 slide 的 JSON 对象，字段对应 {layout_type} 的参数：

cover:            { layout, title, subtitle }
toc:              { layout, sections: [str, ...] }
section_divider:  { layout, num: int, title }
single_focus:     { layout, big_text, big_number, explanation }
compare:          { layout, title?, items: [{title, body}, ...] }
cards:            { layout, title?, cards: [{title, body}, ...] }
bullet_list:      { layout, title, items: [str, ...] }
table:            { layout, title, headers: [str, ...], rows: [[str, ...], ...] }
pic_text:         { layout, title, image_path, points: [{title, body}, ...] }
summary:          { layout, conclusions: [str, ...], title? }
closing:          { layout, subtitle? }

> `title?` / `subtitle?` 带 `?` 为可选字段。`compare.title` 默认"对比"——
> 建议显式传更具体的页标题（如"现状 vs 目标"）。`closing.subtitle` 默认空(只显大字"谢谢")。
> `compare` / `cards` 的列数由 `items` / `cards` 列表长度决定（N 列）。

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

### 变化感（相邻页 layout 不重复）

- 连续 2 页都用 `bullet_list` → 第 2 页换 `cards` 或 `table`
- 连续 2 页都用 `single_focus` → 其中一页改为 `compare`
- 连续 2 页都用 `cards` → 其中一页改为 `pic_text`
- `section_divider` 不计入"连续"判断（它本身不是内容页）

### 强调感（关键论点单独成页）

- 整 deck 最关键的 1-2 个论点用 `single_focus`（大字号 + 大数字）
- 数据密集页用 `table`；对比类用 `compare`
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
- [ ] 总结页结论与 `brief.key_points` 呼应（不新增未出现过的论点）
- [ ] 封底 `subtitle` 不超 30 字
- [ ] `bullet_list` 所有 items 同一句式（不混用动宾 / 名词性）
- [ ] `cards` 每卡 body 长度差 ≤ 30%（视觉平衡）
- [ ] `table` 列标题与行内容语义对齐（列是维度，行是实例）

---

## 与 brief 的字段映射

| brief 字段 | 用于拓写的位置 |
|---|---|
| `title` | `cover.title` |
| `subtitle` | `cover.subtitle` |
| `outline` | `toc.sections` + `section_divider.title`（按序） |
| `key_points` | `summary.conclusions` + 各 `bullet_list.items` 候选库 |
| `audience` | LLM 拓写时的语气校准（技术受众 → 精确数字；业务受众 → 结论先行） |
| `duration_min` | 估算页数（1 min ≈ 1.5 页）+ 内容密度（时间短 → 减 bullet 数量） |
| `reference_pptx` | 若存在，由 [template-extract.md](template-extract.md) 提取主色与字体覆盖 theme |

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

## Anti-prompt

- 不要在 `single_focus` 放 5 个 bullet —— 该 layout 只承载 1 个核心数字 + 1 行解释
- 不要在 `toc` 里写出完整段落 —— 章节标题 ≤ 12 字，是导航，不是摘要
- 不要把 `summary` 写成 `toc` 的重复 —— 总结页要给出结论，不是重列章节名
- 不要在 `closing` 塞要点列表 —— 封底只有"谢谢" + 联系方式，period
- 不要在 `table` 单元格写长句 —— 超 8 字的内容应拆分或换 `bullet_list`
- 不要跳过字数校验步骤 —— 拓写完必须过 checklist，不能"看起来差不多"
- 不要忽略 `duration_min` —— 时间短的 deck 要主动删内容页，不能塞满
- 不要让相邻页 layout 相同 —— 节奏感是 deck 质量的重要维度
