# 每页文案拓写规范

本文档定义 11 种 layout 各自的文案约束 + LLM 拓写 prompt 模板。被 [workflow.md](workflow.md) Step 3 引用。

---

## 11 layout 文案规则

| layout | 字数 / 句式约束 | 反例 |
|---|---|---|
| cover | 主标题 ≤ 20 字、副标 ≤ 30 字、不堆头衔 | "关于 XX 公司 2026 年战略发展规划暨数字化转型实施路径研讨" |
| toc | 章节 ≤ 6、每章 ≤ 12 字、动宾对齐 | "公司发展的历史背景与现状分析" |
| section_divider | 章节号 + 标题（≤ 10 字），layout 独立于内容页 | 与内容页同 header |
| single_focus | 1 句话 ≤ 12 字 + 1 数字（72pt+）+ 1 行解释 | 5 个要点平铺 |
| two_col_compare | 左右标题各 ≤ 6 字、句式对称 | 标题长度差 2× |
| three_col_cards | 每卡标题 ≤ 6 字、body ≤ 30 字 | body 一长一短 |
| bullet_list | 每点 ≤ 14 字、句式一致（动宾或名词性结构） | 一点一句话一点一段 |
| table | 列 ≤ 5、行 ≤ 7、单元格 ≤ 8 字 | 把段落塞进单元格 |
| pic_text | 左图右文，4 卡片每卡 ≤ 20 字 | 图占满 + 文字塞角落 |
| summary | 3-5 条结论，每条 ≤ 18 字，有数字佐证 | 重复 outline 章节 |
| closing | 极简："谢谢" + 联系方式或下一步 | 又一页要点总结 |

---

## 拓写指令模板

给 LLM 用的 prompt（在 workflow Step 3 内部调用）：

```
你正在生成 PPT 第 {idx}/{total} 页。
本章节：{section_title}
关键信息（从 brief.key_points）：{key_points}
本页 layout：{layout_type}
本页意图：{intent}

请输出 page_spec JSON，字段对应 {layout_type} 的参数：

cover:            { layout, title, subtitle }
toc:              { layout, sections: [str, ...] }
section_divider:  { layout, num: int, title }
single_focus:     { layout, big_text, big_number, explanation }
two_col_compare:  { layout, left_title, left_body, right_title, right_body }
three_col_cards:  { layout, cards: [{title, body}, ...] }
bullet_list:      { layout, title, items: [str, ...] }
table:            { layout, title, headers: [str, ...], rows: [[str, ...], ...] }
pic_text:         { layout, title, image_path, points: [{title, body}, ...] }
summary:          { layout, conclusions: [str, ...] }
closing:          { layout, contact_info }

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

- 连续 2 页都用 `bullet_list` → 第 2 页换 `three_col_cards` 或 `table`
- 连续 2 页都用 `single_focus` → 其中一页改为 `two_col_compare`
- 连续 2 页都用 `three_col_cards` → 其中一页改为 `pic_text`
- `section_divider` 不计入"连续"判断（它本身不是内容页）

### 强调感（关键论点单独成页）

- 整 deck 最关键的 1-2 个论点用 `single_focus`（大字号 + 大数字）
- 数据密集页用 `table`；对比类用 `two_col_compare`
- 流程类用 `bullet_list`（步骤有序）；分类类用 `three_col_cards`

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
- [ ] 封底 `contact_info` 不超 30 字
- [ ] `bullet_list` 所有 items 同一句式（不混用动宾 / 名词性）
- [ ] `three_col_cards` 每卡 body 长度差 ≤ 30%（视觉平衡）
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
| `reference_pptx` | 若存在，由 [template-ingest.md](template-ingest.md) 提取风格覆盖 theme |

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
| 30 min | 22-28 页 | 可含 2-3 个 `table` + 多个 `two_col_compare` |
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
