# iLovePPT 使用手册

> 给 PM、设计师、讲者、运营、咨询——任何想把一份 brief 变成完整 PPT 的人。
> 你不需要写代码,也不需要看懂 `build.py`——读完这份手册你就能用 agent 出稿。

---

## 目录

- [1. 30 秒理解 iLovePPT](#1-30-秒理解-iloveppt)
- [2. 五分钟跑通一份 demo](#2-五分钟跑通一份-demo)
- [3. 准备工作:依赖与字体](#3-准备工作依赖与字体)
- [4. 提交需求的三种姿势](#4-提交需求的三种姿势)
- [5. agent 的两阶段流程(你会看到什么)](#5-agent-的两阶段流程你会看到什么)
- [6. 写好 brief 的六条经验](#6-写好-brief-的六条经验)
- [7. 审 outline 的四个角度](#7-审-outline-的四个角度)
- [8. 收稿之后做什么](#8-收稿之后做什么)
- [9. 主题与品牌色](#9-主题与品牌色)
- [10. 11 种 layout 速查](#10-11-种-layout-速查)
- [11. 常见翻车场景与排查](#11-常见翻车场景与排查)
- [12. 直接命令行用法(进阶)](#12-直接命令行用法进阶)
- [13. 术语表](#13-术语表)

---

## 1. 30 秒理解 iLovePPT

**iLovePPT 是一个 Claude Code agent**,你把"主题 / 大纲 / 要点"丢给它,它会:

1. 设计一份完整论证大纲——**先停下来给你看**,改完再继续;
2. 自动判断哪几页该配架构图 / 流程图 / 数据图,然后真的画出来;
3. 逐页拓写文案,跑构建脚本出 `.pptx` + 每页渲染图;
4. 自己读渲染图做视觉自检,有问题就改 `deck_plan.json` 重新构建,最多 3 轮;
5. 把成品 `.pptx` 和"还要人审"的清单一起交给你。

**所以你只做三件事**:

| 你做的 | iLovePPT 做的 |
|---|---|
| 写 brief / 选模板 | 解析 brief、判断图层、设计大纲 |
| 审大纲(可改可拒) | 等你批准,不批不动 |
| 收成品 / 看 review 清单 | 拓写、出图、构建、视觉自检、交付 |

> **核心原则——一图胜千文(一图胜过一千字)。** 凡涉及结构、流程、关系、数据对比,iLovePPT 会主动用 draw.io / matplotlib 画图,而不是堆文字 bullet。

---

## 2. 五分钟跑通一份 demo

仓库自带一份完整 demo,先跑它确认环境没问题。

```bash
# 进仓库根
cd <你的-iLovePPT-仓库>

# 跑构建器(skill 自带 demo plan)
python3 skills/pptx-deck/build.py skills/pptx-deck/examples/demo_plan.json
```

成功的话,在 `skills/pptx-deck/examples/` 下会看到:

- `sample_output.pptx` —— 成品
- `sample_output_render/page-01.jpg` … —— 每页渲染图(用来视觉自检)

用 PowerPoint / Keynote 打开 `.pptx` 检查中文字体是否正确(应该是**微软雅黑**,而不是花体或衬线)。

> 如果中文显示成花体,跳到 [3. 准备工作](#3-准备工作依赖与字体) 装雅黑字体;如果 `soffice` 报错,跳到 [11. 翻车场景](#11-常见翻车场景与排查)。

---

## 3. 准备工作:依赖与字体

### 3.1 一键自检

```bash
bash skills/pptx/scripts/check_deps.sh
```

输出会逐项打勾或报缺,大致这样:

```
== iLovePPT pptx skill 依赖检查 ==
  ✅ python -m pptx
  ✅ python -m lxml
  ✅ python -m PIL
  ✅ soffice
  ✅ pdftoppm
  ✅ 微软雅黑
完成。
```

### 3.2 必装清单

| 用途 | 工具 | macOS 装法 |
|---|---|---|
| .pptx 读写 | `python-pptx`, `lxml` | `pip3 install python-pptx lxml` |
| PNG 渲染验证(soffice → PDF → PNG) | LibreOffice + Poppler | `brew install --cask libreoffice` + `brew install poppler` |
| 中文字体(默认) | Microsoft YaHei | 把 `msyh.ttf` / `msyhbd.ttf` 拷到 `~/Library/Fonts/` |

### 3.3 选装(出图工具)

| 出图工具 | 何时需要 | macOS 装法 |
|---|---|---|
| draw.io CLI(架构 / 流程 / 矩阵 / 关系图) | 几乎一定要 | `brew install --cask drawio` |
| matplotlib(数据图) | brief 含数字趋势 / 对比时 | `pip3 install matplotlib` |
| Mermaid CLI(草图备选) | 极少用 | `npm install -g @mermaid-js/mermaid-cli` |

> **特别提醒(macOS):** Microsoft YaHei 是 iLovePPT 的**默认中文字体**。不装它,LibreOffice 渲染时会 fallback 到 PingFang SC,与 Windows 的 PowerPoint 显示不一致,看起来"图灰一道",但成品 `.pptx` 在 Windows 打开仍然正常。

---

## 4. 提交需求的三种姿势

iLovePPT agent 接受三种输入,用哪种都行——agent 会自己补齐缺的字段。

### 姿势 A:一句话对话

直接在 Claude Code 里跟 agent 说人话:

```
@agent-iloveppt 帮我做一份「AI 4A 架构评审办法 v1.0」的提案,
受众 30 人左右(技术 + 业务),时长 15 分钟,
主线想讲:背景、评审范围、5 阶段流程、组织保障、落地节奏。
主题用内置 tech_blue,产物输出到 ./out/deck.pptx。
```

agent 会自己提取出:`title / outline / audience / duration_min / theme / output`,缺字段会列在 `missing_fields` 里反问你。

### 姿势 B:brief.yaml(结构化,推荐)

适合内容已经成稿、想可重复生成的人。在仓库任意位置写一份 yaml:

```yaml
# brief.yaml
title: "AI 4A 架构评审办法 v1.0"        # 必填,≤ 20 字
subtitle: "技术 + 业务 协同评审机制"     # 可选,≤ 30 字
audience: executive                       # executive / technical / general / sales
duration_min: 15                          # 影响页数估算
outline:                                  # 必填,章节列表
  - "背景与意义"
  - "评审范围"
  - "评审流程(5 阶段)"
  - "组织保障"
  - "落地节奏"
key_points:                               # 可选,跨章节关键信息
  - "强制嵌入研发流程"
  - "5 阶段评审,每阶段 ≤ 3 天"
  - "AI 助手提前预审"
theme: tech_blue                          # 必填,见姿势 C
output: ./out/deck.pptx                   # 必填,产物路径
page_count_target: 20                     # 可选,自动估算时省略
brand_color: "#0B2A4A"                    # 可选,覆盖 theme 主色
reference_pptx: null                      # 可选,见姿势 C
```

然后:

```
@agent-iloveppt 按 ./brief.yaml 出稿
```

> 完整字段样例:`skills/pptx-deck/brief.example.yaml`(直接复制改)。

### 姿势 C:已有 .pptx 当模板

公司已经有品牌模板?直接把 `.pptx` 路径填进 `theme` 或 `reference_pptx`:

```yaml
theme: ./company_template.pptx     # 或写绝对路径
```

agent 会自动从这份模板里抽两样东西:

| 抽什么 | 怎么用 |
|---|---|
| 主题色(`<a:accent1>`) | 替换 `tech_blue` 的 PRIMARY 色 |
| 中文字体(`<a:ea typeface>`) | 替换默认的 Microsoft YaHei |

**抽不到的东西**(这是底线,别期待):

- 背景图、装饰元素、自定义 layout
- 圆角风格、间距、动画
- 你模板里的页面内容(agent 不会复制)

也就是说,模板**只用于换色 + 换字体**,布局仍然是 iLovePPT 内置的 11 种 layout。如果你想要"完全照模板视觉风格出稿",这不是 iLovePPT 的能力范围。

### 字段速查

| 字段 | 必填 | 默认 / 备注 |
|---|:--:|---|
| `title` | ✅ | ≤ 20 字 |
| `outline` | ✅ | 章节列表,每条 ≤ 12 字 |
| `theme` | ✅ | `tech_blue` 或 `.pptx` 路径 |
| `output` | ✅ | 绝对路径或相对当前目录 |
| `subtitle` | — | ≤ 30 字 |
| `audience` | — | `executive` / `technical` / `general` / `sales`,默认 `general` |
| `duration_min` | — | 用于页数估算,公式 `total ≈ duration × 1.5` |
| `key_points` | — | summary 页结论的候选库 |
| `brand_color` | — | 覆盖 theme 主色 |
| `reference_pptx` | — | 同 `theme` 写 .pptx 路径 |

---

## 5. agent 的两阶段流程(你会看到什么)

iLovePPT 把工作砍成**两次派发**,中间有一个**人工 checkpoint**——这是设计上故意的,防止 agent 直接给你一份歪掉的成品。

```
你: @agent-iloveppt 做 PPT
       ↓
[Phase 1: 大纲] ← agent 跑
       ↓
agent 返回 outline.yaml → 停在这里
       ↓
你审 outline(可以全盘改)
       ↓
你: 批准/改 X 处后重发
       ↓
[Phase 2: 构建] ← agent 跑(自动跑完)
       ↓
agent 返回 .pptx + review_needed 清单
```

### 5.1 Phase 1 —— 你会收到什么

agent 跑完 Phase 1 会返回一份 YAML,大概长这样:

```yaml
phase: 1
theme: tech_blue
output: /abs/path/to/deck.pptx
audience: technical
target_page_count: 20

# 金字塔原理 5 件套(核心要求,见第 6 章)
top_recommendation: "应当本季度落地 AI 4A 评审办法,5 阶段每阶段 ≤ 3 天"
scqa:
  situation: "AI 工具铺开,研发提速 30%"
  complication: "架构评审仍靠人审,质量飘移,上线返工率上升"
  question: "怎么让评审跟上节奏又不放低质量?"
  answer: "应当本季度落地 AI 4A 评审办法,5 阶段每阶段 ≤ 3 天"
mece_check_passed: true
pyramid_check_passed: true
bypass_pyramid: false

sections:
  - title: "背景与意义"
    action_title: "AI 工具铺开,但架构评审仍靠人,质量飘移"
    intent: "让管理层认可:这件事必须做"
    layout: bullet_list
    needs_diagram: false
  - title: "评审范围"
    action_title: "覆盖 4A:Application/Architecture/Auth-N/Auth-Z 全闭环"
    intent: "划清边界,避免后续扯皮"
    layout: cards
    needs_diagram: false
  - title: "评审流程"
    action_title: "5 阶段串行,每阶段 ≤ 3 天,卡点不超 1 周"
    intent: "节奏可控,可复制到其他业务线"
    layout: pic_text
    needs_diagram: true
  # ...
diagram_plan:
  - section_idx: 3
    diagram_type: flow
    tool: drawio
    intent: "5 阶段评审流程图,展示阶段 + 卡点 + 角色"
ghost_deck_test_passed: true
missing_fields: []
```

**Phase 1 结束后 agent 不会继续做任何事**——它会等你回话。

> 如果 `pyramid_check_passed: false` 或 `missing_fields` 不空(常见:`top_recommendation 缺失` / `complication 与 situation 重复` / `章节非 MECE`),说明你的 brief 缺金字塔某个要件,agent 会反问你补,而不是硬出大纲。

### 5.2 Phase 1 → Phase 2 之间,你能做的

| 你想做的 | 怎么做 |
|---|---|
| 全盘接受 | 回:"批准,继续" |
| 改某节标题 | 回:"第 3 节 action_title 改成 ……,然后继续" |
| 加 / 删一节 | 回:"删掉第 5 节,在第 2 节后加一节 ……,然后继续" |
| 改图层规划 | 回:"第 2 节也要配架构图,加进去" |
| 推翻重来 | 回:"重新设计 outline,这次按结论先行的结构" |

agent 第二次派发时会带着你**改后的 outline** 进 Phase 2,直接拓写到交付。

### 5.3 Phase 2 —— agent 会做这些

1. **出图** —— 按 `diagram_plan` 调 draw.io / matplotlib,PNG 落到 `<output 同目录>/_assets/`
2. **写 deck_plan.json** —— 逐页拓写文案,严格遵守 11 layout 的字数 / 句式约束
3. **构建** —— 跑 `build.py`,出 `.pptx` + 每页 PNG
4. **视觉自检循环(最多 3 轮)** —— agent 自己读 PNG,按 12 项 checklist 找问题,有问题改 `deck_plan.json` 重跑
5. **交付** —— 返回 `.pptx` 路径 + `review_needed` 清单

### 5.4 Phase 2 你会收到什么

```yaml
phase: 2
pptx_path: /abs/path/to/deck.pptx
qa_rounds: 2                       # 跑了 2 轮自检
review_needed:
  - page: 5
    issues: ["D10 内容下半空白"]
    suggestion: "缩短卡片正文 或 改用 bullet_list"
design_score: "13/14"               # 最弱页的设计分(满分 14)
```

**`review_needed` 不空,说明那几页机器自己修不动了,需要你看看。** 不是失败,只是 agent 已经尽力。

---

## 6. 写好 brief 的六条经验

agent 越笨,你写 brief 就要越细。下面这六条,能把出稿质量直接抬一档。

### 6.1 用麦肯锡金字塔原理设计 outline(核心要求)

**iLovePPT 的内容设计核心要求**:整份 deck 按麦肯锡金字塔原理组织。Phase 1 不通过 Pyramid 自检的 outline,agent 不会交付——你 brief 里把这五件套讲清楚,Phase 1 几乎一次过。

| # | 要件 | 在 brief 里怎么准备 |
|---|---|---|
| ① | **单一顶端论点** | 写一句完整推荐(动宾 + 边界):"应当本季度落地 X,5 阶段每阶段 ≤ 3 天",而不是"我们来讨论 X" |
| ② | **SCQA 开场** | brief 里至少写明 situation(背景) + complication(冲突 / 变化),agent 自己派生 question 和 answer |
| ③ | **答案在前(BLUF)** | 让顶端论点出现在 `subtitle` 或第 1 内容页,而不是只在最后总结 |
| ④ | **横向 MECE** | outline 给 **3-5 节**,两两不重叠,加起来能完整支撑顶端论点 |
| ⑤ | **纵向疑问/回答** | 每节章节名就是"为什么 / 怎么做 / 是什么"的回答(= action title) |

**反例**(话题堆叠,无顶端论点,无 SCQA,非 MECE):

```yaml
title: "AI 4A 架构评审办法"
outline: ["市场背景", "技术方案", "团队介绍", "联系方式"]
# Phase 1 会被 Pyramid 自检卡住——agent 会反问:顶端论点是什么?C 是什么?
```

**对例**(金字塔完整):

```yaml
title: "AI 4A 架构评审办法 v1.0"
subtitle: "本季度落地,5 阶段每阶段 ≤ 3 天"      # ③ BLUF:顶端论点提前

# 让 agent 直接看到 SCQA 骨架(可选,但强烈推荐)
top_recommendation: "应当本季度落地 AI 4A 评审办法,5 阶段每阶段 ≤ 3 天"
situation: "AI 工具铺开,研发提速 30%"
complication: "架构评审仍靠人审,质量飘移,上线返工率上升"

outline:                                          # ④ MECE 章节(回答顶端论点的为什么/怎么做/是什么)
  - "AI 工具铺开,但架构评审仍靠人,质量飘移"    # 为什么要做(= 章节 action title)
  - "覆盖 4A:Application/Architecture/Auth-N/Auth-Z 全闭环"   # 是什么(范围)
  - "5 阶段串行,每阶段 ≤ 3 天,卡点不超 1 周"   # 怎么做(流程)
  - "评审委员会 + AI 助手预审,降 60% 人力"      # 怎么做(组织保障)
  - "Q3 试点 2 业务线,Q4 全公司"                 # 怎么做(落地节奏)

key_points:
  - "5 阶段评审,每阶段 ≤ 3 天"
  - "AI 助手提前预审,降 60% 人力"
  - "Q3 试点 → Q4 全公司"
```

**何时可以豁免?** 仅以下三种 deck 类型可以在 brief 加 `structure_mode: data_report | tutorial | catalog`,agent 会在 Phase 1 设 `bypass_pyramid: true`,跳过自检 1-6 项:

- `data_report`:月报 / 周报 / 数据汇报(章节是数据维度而非论证)
- `tutorial`:培训 / 教学 deck(讲解知识结构,不是说服)
- `catalog`:产品手册 / 能力清单 / 人员介绍

**99% 的提案 / 路演 / 汇报 / 评审场合都走金字塔**——agent 不会自行判断豁免,必须你在 brief 里显式声明。

### 6.2 action title:每页标题就是"答案"

action title 是金字塔原理"答案在前"在**页级**的实现——读者只看标题就知道这页要说什么。

| ✗ 话题标签 | ✓ action title(答案在前) |
|---|---|
| 市场背景 | SaaS 市场三年翻倍,渗透率仍不足 15% |
| 技术方案 | 三层架构把交付周期从 2 周压到 2 天 |
| 效果数据 | 上线 3 月,人均每天省 1.2 小时 |

写 brief 时 outline 直接用 action title 句式,Phase 1 出 outline 时几乎不用改。**这同时也满足金字塔的纵向疑问/回答链**——把所有 action title 抽出来按顺序读,应该能讲出顶端论点的完整论据链(这就是 Pyramid 自检表第 6 项)。

### 6.3 数字 > 形容词

| ✗ | ✓ |
|---|---|
| 显著提升 | 提升 80% |
| 大量节省 | 节省 3.2 小时 / 天 |
| 高效 / 创新 / 领先 | (一律删掉) |

`key_points` 里塞数字,agent 拓写 summary 页时会自动调用。

### 6.4 audience 字段会校准语气

| audience | agent 拓写时的取舍 |
|---|---|
| `executive` | 结论先行、数字突出、每页一个论点 |
| `technical` | 步骤详细、技术术语可用、数字精确 |
| `general` | 类比辅助、避免术语、结论清晰 |
| `sales` | 价值主张突出、对比竞品、行动导向 |

不填默认 `general`。**写对 audience,出稿语气能差一档。**

### 6.5 duration_min 决定页数密度

公式:`total ≈ duration × 1.5`(含封面 / 目录 / 章节扉页 / 总结 / 封底)。

| 时长 | 建议总页数 | 每内容页密度 |
|---|---|---|
| 10 min | 8-12 页 | 每页 3-5 bullet 或 1 组数据 |
| 20 min | 15-20 页 | 每页 4-6 bullet 或 1 张表 |
| 30 min | 22-28 页 | 含 2-3 张 table / compare |
| 45 min | 30-38 页 | 章节更多,每章可 3 内容页 |
| 60 min | 40-50 页 | 通常需配 pic_text 图例 |

**时长短就大胆删 outline 章节**,塞满会让讲者翻不完。

### 6.6 缩写第一次给全称

```yaml
key_points:
  - "4A(Application / Architecture / Auth-N / Auth-Z)是评审范围"
```

agent 看到 `key_points` 里有全称,第一次出现时会沿用,后续才简写。

---

## 7. 审 outline 的四个角度

Phase 1 收到 outline 后,从这四个角度过一遍:

### 7.1 论证骨架(Pyramid 自检 7 项)

agent 已经在 Phase 1 跑过 Pyramid 自检并返回 `pyramid_check_passed: true`,但你审 outline 时再过一遍——agent 有时会"勉强通过":

| 自检项 | 你审什么 |
|---|---|
| **① 单一顶端论点** | `top_recommendation` 是不是一句完整推荐(动宾 + 具体边界)?读着像议题陈述就要改 |
| **② SCQA 完整** | `complication` 真的是冲突 / 变化吗,不是 `situation` 的复述?`answer == top_recommendation`? |
| **③ 答案在前** | `cover.subtitle` 或第 1 内容页是不是明示了顶端论点?藏在最后总结不算 |
| **④ MECE 通过** | 章节数 3-5?两两之间有没有重叠?加起来听众会不会问"那 X 呢"? |
| **⑤ 章节排列方式一致** | 时间序 / 结构序 / 重要性序 / 演绎序——是不是混用了? |
| **⑥ 纵向疑问/回答(ghost deck test)** | 把所有 `action_title` 抽出来按顺序读,能不能讲出顶端论点的完整论据链? |
| **⑦ action title 全是结论句** | 还有名词短语标题没有?("市场背景" / "技术方案"一律要改) |

任一项不过,直接告诉 agent 改:

```
Pyramid 自检第 ④ 项不过:第 3 节"评审流程"和第 4 节"组织保障"内容有重叠
(评审委员会算流程也算保障)。把组织保障合并进流程节,outline 重排成 4 节
```

### 7.2 图层规划

看 `diagram_plan` 那几张图够不够、对不对:

| 信号 | 处理 |
|---|---|
| 全 deck 0 张图 | 一定漏判了,要求 agent 重新扫每章 |
| 一章塞 2 张图 | agent 默认每章最多 1 张,出现 2 张说明误判,合并 |
| 数据章节判成 `arch_diagram` | 改成 `chart`(matplotlib) |
| 流程章节判成 `simple_relation` | 改成 `flow`(draw.io) |
| 5+ 节点的关系判成 `simple_relation` | 改成 `arch_diagram` |

iLovePPT 默认 **结构性图形优先 draw.io**(精确配色、布局可控、跨图视觉一致)。Mermaid 只是草图备选,你一般不需要主动选。

### 7.3 页数

看 `target_page_count` 是否符合 `duration_min`:

- 15 min 但 outline 拓到 30 页 → 删章节或让 agent 减内容页密度
- 30 min 但 outline 才 10 页 → 加章节或让 agent 加内容页

### 7.4 layout 选型

每节的 `layout` 字段决定该节的呈现形式。常见错配:

| outline 内容 | 错的 layout | 该改成 |
|---|---|---|
| "5 个核心模块" | `single_focus` | `cards`(每模块一张卡) |
| "4 项指标 vs 行业均值" | `bullet_list` | `table` 或 `compare` |
| "1 个关键数字(40% 降本)" | `bullet_list` | `single_focus`(72pt 大字) |
| "时间线 / 路线图" | `bullet_list` | `pic_text` + 流程图 |

> layout 字段名一定要用 11 种之一的拼写,见 [10. 11 种 layout 速查](#10-11-种-layout-速查)。

---

## 8. 收稿之后做什么

### 8.1 review_needed 清单

agent 跑完 Phase 2 给你的清单大概这样:

```yaml
review_needed:
  - page: 5
    issues: ["D10 内容下半空白"]
    suggestion: "缩短卡片正文 或 改用 bullet_list"
  - page: 12
    issues: ["大字号 big_number 换了行"]
    suggestion: "把 big_number 从 '127.5%' 改成 '127%'"
```

每条都有**问题描述 + 建议改法**。三个选项:

| 选项 | 适合场景 |
|---|---|
| **跟 agent 说"按 suggestion 改第 5 页,重跑"** | 大部分情况,最省事 |
| **手动改 `deck_plan.json` 重跑 build.py** | 改得很具体、你自己有想法 |
| **直接 PowerPoint 里改** | 一次性微调、不打算复用 |

### 8.2 局部重跑

`deck_plan.json` 落在 `<output 同目录>/deck_plan.json`,直接改对应 slide 字段,然后:

```bash
python3 skills/pptx-deck/build.py /path/to/deck_plan.json
```

每页大概 3-4 秒(LibreOffice 启动 1.5 秒 + 渲染),20 页约 1 分钟。

### 8.3 字体在 macOS 上看起来不对

agent 输出的 `.pptx` 默认用 **Microsoft YaHei**(雅黑)。

- 在 PowerPoint(Mac 版 / Windows) 打开 → 必须显示雅黑;不显示说明字体没装,装一下
- 在 LibreOffice 打开 → 同上
- 在 Keynote 打开 → Keynote 自己渲染逻辑,中文 fallback 可能不是雅黑——这是 Keynote 问题,不是 iLovePPT 问题

**成品交付建议用 PowerPoint 打开校对一遍**,避免 Keynote 渲染误判。

### 8.4 想再迭代一版

直接告诉 agent:

```
@agent-iloveppt 第 7 页 cards 改成 4 个,加一张"客户案例"卡片,
重跑 Phase 2(outline 已批准,不用回 Phase 1)
```

agent 会跳过 Phase 1,从 Phase 2 开始重跑。

---

## 9. 主题与品牌色

### 9.1 内置 tech_blue(默认)

| 角色 | 色值 | 用在哪 |
|---|---|---|
| `BRAND_PRIMARY` | `#1E6FE0` | 标题、强调装饰、key icon |
| `BRAND_DARK` | `#0B2A4A` | 封面背景、深色文字 |
| `BRAND_TINT` | `#E6F0FC` | 卡片底、tag 背景 |
| `ACCENT` | `#00D1C1` | 极个别强调点 |

> **以 `skills/pptx/helpers.py` 的常量为唯一权威源**。手册里的 hex 是抄录,可能因主题更新而过时。

字体:**Microsoft YaHei**(中文)+ 字符回退链。所有字号、间距体系见 `skills/pptx/design-system.md`。

### 9.2 换品牌色

最轻量:在 brief 里加 `brand_color`:

```yaml
brand_color: "#C8102E"     # 比如可口可乐红
```

agent 会用它覆盖 `BRAND_PRIMARY`。

### 9.3 用 .pptx 模板

```yaml
theme: ./company_template.pptx
```

抽 **主题色(accent1)+ 中文字体** 两样,其他全用 tech_blue 的 layout。

**这意味着——**

- ✅ 你的品牌色被沿用
- ✅ 你的指定中文字体被沿用(比如思源黑体)
- ✗ 模板里的特殊背景、装饰元素、自定义 layout **不会被复制**
- ✗ 圆角、间距、动画 **不会被沿用**

提取失败(模板损坏、accent1 是渐变色等)会**静默退回 tech_blue 默认值**,不会中止构建——查 `build.py` 终端输出能看到实际使用的字体与主色。

### 9.4 想要彻底自定义视觉?

需要写 Python——`skills/pptx-deck/themes/tech_blue.py` 是模板,新建 `themes/party_red.py` 复制改即可。这超出本手册范围,见仓库 `CLAUDE.md` 与 `skills/pptx/design-system.md`。

---

## 10. 11 种 layout 速查

| layout | 用途 | 关键字段 | 字数 / 数量约束 |
|---|---|---|---|
| `cover` | 封面 | `title`, `subtitle` | 标题 ≤ 20 字、副标 ≤ 30 字 |
| `toc` | 目录 | `sections: [str]` | ≤ 6 章,每章 ≤ 12 字 |
| `section_divider` | 章节扉页 | `num`, `title` | 标题 ≤ 10 字 |
| `single_focus` | 1 句大话 + 1 大数字 | `big_text`, `big_number`, `explanation` | 大话 ≤ 12 字,1 行解释 |
| `compare` | 左右 / N 列对比 | `title?`, `items: [{title, body}]` | 左右标题 ≤ 6 字,句式对称 |
| `cards` | N 张并列卡片 | `title?`, `cards: [{title, body}]` | 卡标题 ≤ 6 字,body ≤ 30 字 |
| `bullet_list` | 要点列表 | `title`, `items: [str]` | 每点 ≤ 14 字,句式一致 |
| `table` | 表格 | `title`, `headers`, `rows` | 列 ≤ 5,行 ≤ 7,格 ≤ 8 字 |
| `pic_text` | 左图右文(配图页用这个) | `title`, `image_path`, `points: [{title, body}]` | 右侧每卡 ≤ 20 字 |
| `summary` | 总结 | `conclusions: [str]`, `title?` | 3-5 条,每条 ≤ 18 字,有数字 |
| `closing` | 封底 | `subtitle?` | 极简,"谢谢"+ 联系方式 |

### 节奏感规则(agent 自动遵守,你审 outline 时也看看)

- 每个 section 至少 1 张内容页,最多 3 张
- 连续 2 页**不能用同一种 layout**(`bullet_list` 接 `bullet_list` 要换成 `cards`)
- `section_divider` 不计入"连续"判断
- `cover` / `toc` / `closing` 全 deck 各出现 1 次

### 何时强制用某 layout

| 内容信号 | 用 |
|---|---|
| 1 个最关键的数字(40% 降本 / 3× 增速) | `single_focus` |
| 数据密集(指标 vs 目标 vs 行业) | `table` |
| 对比类(v1 vs v2 / 我们 vs 竞品) | `compare` |
| 3-5 个并列模块 / 分类 | `cards` |
| 有顺序的步骤 / 流程 | `bullet_list` 或配 `pic_text` + 流程图 |
| 系统结构 / 架构 / 多层 | `pic_text` + 架构图 |

---

## 11. 常见翻车场景与排查

### 11.1 中文字体显示成花体 / 衬线

**症状**:渲染图(`*_render/page-*.jpg`)里的中文长得像 Times Roman + 楷书。

**原因**:macOS 没装 Microsoft YaHei,LibreOffice 渲染时 fallback 到 PingFang SC 或 Heiti SC。

**修法**:

```bash
# 从 Windows 拷贝 msyh.ttc 和 msyhbd.ttc 到 macOS
cp msyh.ttc ~/Library/Fonts/
cp msyhbd.ttc ~/Library/Fonts/
fc-cache -fv

# 校验
fc-list | grep -i yahei     # 应该看到雅黑
```

装好后让 agent 重跑 Phase 2,或自己跑 `build.py`。

> **成品 `.pptx` 不会因为这个出问题**——这只影响 macOS 端的 PNG 渲染图。在 Windows PowerPoint 里打开总是正确的。

### 11.2 draw.io 没装,agent 出图卡住

**症状**:Phase 2 跑到 "出图" 这一步卡很久或报错 `draw.io: command not found`。

**修法**:

```bash
brew install --cask drawio
ls /Applications/draw.io.app      # 验证装上了
```

装完让 agent 继续。**临时绕过**:在 outline 里把 `diagram_plan` 删掉,让对应章节降级为 `bullet_list` / `cards`——但**违反"一图胜千文"原则**,只在赶 deadline 时用。

### 11.3 大字号被换行

**症状**:`single_focus` 的 `big_number`(72pt+)显示成两行。

**原因**:数字太长。

**修法**(写 brief 时):

- 不要写 `"127.5%"`,改成 `"127%"`
- 不要写 `"1,250,000"`,改成 `"1.25M"` 或 `"125 万"`

review_needed 一定会标这条,按 suggestion 改即可。

### 11.4 全是文字墙,没图

**症状**:成品 20 页全是 bullet,没有架构图 / 流程图。

**原因**:Phase 1 时 `diagram_plan` 是空的——agent 没主动判断,或者你审 outline 时没要求加图。

**修法**:回 Phase 1 让 agent 重做图层规划:

```
@agent-iloveppt 这份 outline 全是文字,按 diagram-planning 的 4 类图决策表
重新扫一遍每节,告诉我哪几节该配图(架构 / 流程 / 数据 / 关系)
```

或者审 outline 时主动说:

```
第 3 节(评审流程)配一张 flow,用 draw.io;
第 5 节(落地节奏)配一张时间线 chart,用 matplotlib
```

### 11.5 agent 把模板内容复制进我的 deck 了

**不应该发生**——`template-extract` 流程明确**只提主色 + 字体**,不复制任何内容。

如果看到这种情况,说明 agent 没按 `template-extract.md` 走。把这条贴回去让它重做:

```
你违反了 template-extract 的约束——模板只用于提取主色与中文字体,
不能挪用模板的页面内容。把所有从模板抄来的页删掉,重新按 brief 拓写。
```

### 11.6 review_needed 三轮还修不好

**症状**:agent 跑了 3 轮自检,某页仍标 `review_needed`。

**原因**:多数是 layout 选错——比如用 `single_focus` 装 5 个 bullet,改字号 / 位置都救不了。

**修法**:换 layout,不是改字段。

```
@agent-iloveppt 第 5 页用 single_focus 装太多内容了,
改成 bullet_list 重跑
```

### 11.7 soffice 渲染卡住 / crash

**症状**:`build.py` 跑到 "渲染 PNG" 这步挂住或报错。

**排查**:

```bash
# 单独跑一次 soffice,看错误
soffice --headless --convert-to pdf <你的>.pptx --outdir /tmp/

# 如果 soffice 也卡,杀掉残留进程再试
pkill -f soffice
```

LibreOffice 有时会因为字体缓存损坏卡住,删 `~/Library/Application Support/LibreOffice/` 重启可解。

### 11.8 想跳过渲染只要 .pptx

```
@agent-iloveppt 这次只要 .pptx,跳过视觉自检
```

或直接命令行:

```bash
python3 skills/pptx-deck/build.py deck_plan.json --no-render
```

不推荐——少了视觉自检,字体 fallback / layout 错配会漏。

---

## 12. 直接命令行用法(进阶)

如果你愿意自己写 `deck_plan.json`(不走 agent),可以直接调 `build.py`。

### 12.1 接口

```bash
python3 skills/pptx-deck/build.py <deck_plan.json> [--no-render]
```

- `--no-render`:跳过 PNG 渲染,只出 `.pptx`(快 3-4 倍)

### 12.2 deck_plan.json 结构

```json
{
  "theme": "tech_blue",
  "output": "./out/deck.pptx",
  "slides": [
    {"layout": "cover", "title": "iLovePPT 演示", "subtitle": "deck_plan 驱动"},
    {"layout": "toc", "sections": ["背景", "方案", "效果"]},
    {"layout": "section_divider", "num": 1, "title": "背景"},
    {"layout": "bullet_list", "title": "三个痛点",
     "items": ["文字墙", "留白多", "改动散"]},
    {"layout": "cards", "title": "三大改进", "cards": [
      {"title": "接缝", "body": "deck_plan.json 隔开机械与智能"},
      {"title": "原语", "body": "layout.py 几何原语,数量灵活"},
      {"title": "回归", "body": "evals 集守护质量"}]},
    {"layout": "compare", "title": "v1 vs v2", "items": [
      {"title": "v1", "body": "骑墙,占位骨架"},
      {"title": "v2", "body": "诚实,机械/智能分离"}]},
    {"layout": "summary",
     "conclusions": ["接口诚实", "布局可组合", "质量可回归"]},
    {"layout": "closing", "subtitle": "github.com/pcliangx/iLovePPT"}
  ]
}
```

完整字段对照见 [10. 11 种 layout 速查](#10-11-种-layout-速查)。

### 12.3 配图

`pic_text` 的 `image_path` 接受相对路径或绝对路径——**图必须自己先生成好**。`build.py` 不画图。

```json
{
  "layout": "pic_text",
  "title": "评审 5 阶段流程",
  "image_path": "./_assets/review_flow.png",
  "points": [
    {"title": "阶段 1", "body": "提案 / 立项"},
    {"title": "阶段 2", "body": "架构评审"},
    {"title": "阶段 3", "body": "安全评审"},
    {"title": "阶段 4", "body": "上线评审"},
    {"title": "阶段 5", "body": "回顾复盘"}
  ]
}
```

出图命令:

```bash
# draw.io
/Applications/draw.io.app/Contents/MacOS/draw.io \
  --export --format png --width 3200 \
  --output ./_assets/review_flow.png review_flow.drawio

# matplotlib(写一段 Python 跑)
python3 plot_trend.py    # 内部 dpi=200, savefig('./_assets/trend.png')
```

详细模板见 `skills/diagram/drawio.md` 与 `skills/diagram/matplotlib.md`。

### 12.4 一键校验输出

```bash
# 渲染 PDF
soffice --headless --convert-to pdf ./out/deck.pptx --outdir /tmp/

# PDF → PNG
pdftoppm -jpeg -r 120 /tmp/deck.pdf /tmp/slide

# 打开第一页看看
open /tmp/slide-01.jpg
```

### 12.5 跑回归 eval(适合改了主题 / layout 后)

```bash
bash evals/run_eval.sh
```

跑完会在 `evals/_run/scorecard.md` 出 scorecard 模板,对照 `evals/baseline/scorecard.md`——fail 项变多说明回归了。

---

## 13. 术语表

| 术语 | 意思 |
|---|---|
| **agent / iLovePPT agent** | Claude Code 里的 subagent,通过 `@agent-iloveppt` 派发,独立上下文跑两阶段 |
| **brief** | 你写给 agent 的需求,可以是一句话 / YAML / 模板 .pptx |
| **outline** | 章节大纲,Phase 1 产出物,等用户批准 |
| **action title** | 行动式标题——每页标题是完整结论句,不是话题标签。是金字塔原理"答案在前"在页级的实现 |
| **金字塔原理(Pyramid Principle)** | 麦肯锡 Barbara Minto 提出的论证结构——iLovePPT 的内容设计核心要求。5 件套:单一顶端论点 / SCQA 开场 / 答案在前 / 横向 MECE / 纵向疑问回答链 |
| **SCQA** | Situation 背景 → Complication 冲突 → Question 问题 → Answer 答案,金字塔原理的开场公式 |
| **MECE** | Mutually Exclusive, Collectively Exhaustive——相互独立、完全穷尽,金字塔横向支撑要求 |
| **BLUF** | Bottom Line Up Front,答案在前,金字塔原理的展开节奏 |
| **Pyramid 自检** | Phase 1 必须通过的 7 项金字塔合规检查,任一不过则不交付 outline |
| **ghost deck test** | Pyramid 自检第 ⑥ 项:把所有 action title 抽出来按顺序读,能不能讲出顶端论点的完整论据链 |
| **bypass_pyramid** | 金字塔自检的逃生口,仅 `data_report` / `tutorial` / `catalog` 三种 deck 可豁免 |
| **deck_plan.json** | agent 写、`build.py` 读的中间产物,描述每页 layout 与字段 |
| **build.py** | 纯机械构建器,`deck_plan.json` → `.pptx` + PNG。**不**拓写、**不**画图、**不**自检 |
| **layout** | 11 种页面版式之一(`cover` / `toc` / `cards` / `pic_text` …) |
| **theme** | 主题,`tech_blue`(内置)或 `.pptx` 模板路径 |
| **tech_blue** | 内置默认主题,蓝色系,字体 Microsoft YaHei |
| **review_needed** | Phase 2 输出的"需要人审"清单,agent 3 轮自检改不动的页 |
| **diagram_plan** | Phase 1 产出的图层规划,标出哪几节配什么类型的图、用什么工具 |
| **template-extract** | 从用户 .pptx 模板提取主色 + 中文字体的流程,**只提这两样** |
| **一图胜千文** | iLovePPT 核心原则:能画图就别堆 bullet |

---

## 附录:文档地图

如果你想深入了解某块细节,这些文档是权威源:

| 想了解 | 看 |
|---|---|
| agent 的完整设计与约束 | `.claude/agents/iloveppt.md` |
| skill 全貌 | `skills/pptx-deck/SKILL.md` |
| 7 步主流程 | `skills/pptx-deck/workflow.md` |
| 11 layout 文案规则 + **金字塔原理 5 件套** + Pyramid 自检表 | `skills/pptx-deck/content-writing.md` |
| 图层规划 4 类决策表 | `skills/pptx-deck/diagram-planning.md` |
| 视觉自检 12 项 checklist | `skills/pptx-deck/visual-qa.md` |
| 模板提取(主色 + 字体) | `skills/pptx-deck/template-extract.md` |
| draw.io / Mermaid / matplotlib 出图 | `skills/diagram/SKILL.md` |
| 底层 .pptx 读写 / 字体处理 | `skills/pptx/SKILL.md` |
| 设计 token(色值 / 字号 / helper) | `skills/pptx/design-system.md` |
| 评分标准(Content / Design / Coherence) | `evals/rubric.md` |
| 仓库架构与代码约定 | `CLAUDE.md`(根目录) |

> 这些 `.md` 不只是"文档"——它们是 agent 在跑的时候**实时读取**的运行手册。改它们等于改 agent 行为。

---

*手册版本:1.0 · 适用 iLovePPT agent v1*
