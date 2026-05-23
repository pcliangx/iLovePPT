# iLovePPT 使用手册(v3)

> 给 PM、设计师、讲者、运营、咨询——任何想把一句话需求变成完整 PPT 的人。
> 你不需要写代码,也不需要看懂 `build.py`——读完这份手册你就能用。
>
> **v3 重大变化(2026-05-23)**:**3 个 agent 接力**(brainstorm → author → builder),主线程做调度。你只面对 markdown,不面对 yaml。
> 用法上你不用记 3 个 agent 名字——你只跟主线程说"做个 PPT",主线程自动派发 brainstorm,后面接力下去。

---

## 目录

- [1. 30 秒理解 iLovePPT v3](#1-30-秒理解-iloveppt-v3)
- [2. 五分钟跑通一份 demo](#2-五分钟跑通一份-demo)
- [3. 准备工作:依赖与字体](#3-准备工作依赖与字体)
- [4. 用 iLovePPT 的标准流程](#4-用-iloveppt-的标准流程)
- [5. 5 阶段你会看到什么](#5-5-阶段你会看到什么)
- [6. 写好需求的六条经验(在 Stage A 对话时用)](#6-写好需求的六条经验在-stage-a-对话时用)
- [7. 审 outline.md 和 content.md 的角度](#7-审-outlinemd-和-contentmd-的角度)
- [8. 收稿之后做什么](#8-收稿之后做什么)
- [9. 主题与品牌色](#9-主题与品牌色)
- [10. 11 种 layout 速查](#10-11-种-layout-速查)
- [11. 常见翻车场景与排查](#11-常见翻车场景与排查)
- [12. 直接命令行用法(进阶)](#12-直接命令行用法进阶)
- [13. 术语表](#13-术语表)

---

## 1. 30 秒理解 iLovePPT v3

**iLovePPT 是 3 个 Claude Code agent 接力**:

1. **iloveppt-brainstorm** —— 多轮跟你问 audience / duration / 核心命题 / 有什么素材
2. **iloveppt-author** —— 出 `deck_v1_outline.md`(给你审)→ 出 `deck_v1_content.md`(再给你审)
3. **iloveppt** —— 接收审过的 content.md → 构建 `.pptx` + 视觉自检

主线程 Claude 是调度员,自动派发 + 转发消息。**你不用记 agent 名字,直接说"帮我做个 X 的 PPT"即可**。

**你只做四件事**:

| 你做的 | 系统做的 |
|---|---|
| 对话:答 audience/duration/核心命题/有什么素材 | brainstorm agent 多轮 prompt 问到收齐 |
| 给素材(数据表 / 图 / 模板路径) | brainstorm Read 文件 / 落 `_assets/` |
| 审 outline.md(可直接编辑文件) | author 等批准 |
| 审 content.md(可直接编辑文件) | author 等批准;批准后派 builder |
| 收 .pptx + 看 auto_md_edits 清单 | builder 自动改格式 + 视觉自检后交付 |

> **核心原则——一图胜千文。** 凡涉及结构、流程、关系、数据对比,author 会主动用 draw.io / matplotlib 画图嵌进 markdown,而不是堆文字 bullet。

> **为什么这么设计?** v2 让 1 个 agent 端到端(用户只审一次 yaml,体验差)。v3 拆 3 个 agent + 主线程 dispatcher,**每个 agent 角色窄、可复用、主线程不被 PPT 任务污染**。详见 [agent-internals.zh.md](agent-internals.zh.md) §10。

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

## 4. 用 iLovePPT 的标准流程

v3 只有**一个**标准入口:**直接对话主线程 Claude**。

### 标准入口:一句话即可

在 Claude Code 里直接说:

```
帮我做一份 AI 4A 架构评审办法 v1.0 的提案
```

主线程 Claude 识别"做提案 / PPT / deck"等关键词后,会**自动启动 brainstorming**,开始 Stage A 对话:

```
主线程: 几个关键问题先确认一下,
       1) 给谁看?老板 / 客户 / 团队 / 投资人?
       2) 讲多久?10/15/20/30 分钟?
       3) 一句话总结:你想让听众接受的核心判断是什么?
       4) 主题用默认 tech_blue,还是有公司模板?
       5) 成品 .pptx 想放哪?

你: 给管理层看,15 分钟,核心是"本季度落地这套办法 5 阶段每阶段 ≤ 3 天",
    用 tech_blue,放 ./decks/

主线程: 好的。你这边有素材吗?
       - Q4 评审数据 / 上线返工率数据?
       - 现有评审流程图?
       - 参考模板 / 之前的提案?

你: 有一份 ./_assets/raw/review_metrics.csv,流程图你帮我画一张
```

主线程接着进入 Stage C(出 outline)+ Stage D(出 content),全程跟你确认。

### 也可以显式派发某个 agent(进阶)

| 想做 | 派发 |
|---|---|
| 从一句话起步 | 直接说"做 PPT" 或 `@agent-iloveppt-brainstorm 做 X 的 PPT` |
| 已有完整 brief / 素材就位,想跳过对话 | `@agent-iloveppt-author working_dir=... stage=C brief={...}` |
| 已有审过的 content.md,想直接 build | `@agent-iloveppt content_md_path=... output_pptx=... theme=...` |

**v3 下直接 `@agent-iloveppt`(不带 content_md_path)会被 reject** —— builder 不做 brief 解析。

普通用户走主线程对话(主线程会自动从 brainstorm 起步)即可。

### brief.yaml(v2 旧路径,仍兼容)

如果你已经有 `brief.yaml`:

```
基于这份 ./brief.yaml 帮我做 PPT
```

主线程会读 yaml → 跳过 Stage A 大部分对话(字段已收齐)→ 直接进 Stage C(出 outline)。后续 outline 审 / content 审仍要做。

> brief.yaml schema 见 `skills/pptx-deck/brief.example.yaml`。

### 工作目录约定

你的 deck 会用一个目录管所有产物:

```
~/decks/2026-05-23-evaluation-proposal/
├── deck_v1_outline.md       # 主线程 Stage C 产出,给你审
├── deck_v1_content.md       # 主线程 Stage D 产出,给你审
├── deck_v1.pptx             # agent Stage E 产出
├── deck_v1_render/          # 渲染图(QA 用,可删)
└── _assets/
    ├── raw/                 # 你提供的素材(csv/png/pdf)
    ├── charts/              # matplotlib / draw.io 生成的图
    └── refs/                # 你直接给的参考图
```

---

## 5. 5 阶段你会看到什么

v3 把流程拆成 **5 阶段**,你在 Stage C 和 Stage D 各审一次:

```
你: "帮我做 X 的 PPT"
   ↓
[Stage A · 主线程多轮问 audience/duration/核心命题/theme/output]
   ↓
你: 答完 5 个字段
   ↓
[Stage B · 主线程问素材] → 你给文件路径或粘贴 → _assets/ 落盘
   ↓
[Stage C · 主线程按 Pyramid 出 outline.md] ← 主线程跑
   ↓
你: 审 outline.md(可改可拒)
   ↓
你: "批准 outline,继续"
   ↓
[Stage D · 主线程拓写 + 出图 + content.md] ← 主线程跑
   ↓
你: 审 content.md(可直接编辑文件)
   ↓
你: "批准 content,继续"
   ↓
[Stage E · agent 派发构建] ← agent 跑(独立上下文)
   ↓
agent 返回 .pptx + auto_md_edits + review_needed
```

### 5.1 Stage C —— 你会收到什么

主线程会写一份 `deck_v1_outline.md` 到你工作目录,大概长这样:

```markdown
---
title: AI 4A 架构评审办法 v1.0
subtitle: 本季度落地,5 阶段每阶段 ≤ 3 天
audience: technical
duration_min: 15
theme: tech_blue
output: ./decks/deck_v1.pptx
top_recommendation: 应当本季度落地 AI 4A 评审办法,5 阶段每阶段 ≤ 3 天
scqa:
  situation: AI 工具铺开,研发提速 30%
  complication: 架构评审仍靠人审,质量飘移
  question: 怎么让评审跟上节奏又不放低质量?
  answer: 应当本季度落地 AI 4A 评审办法,5 阶段每阶段 ≤ 3 天
footer_meta:
  classification: INTERNAL
  project: AI Review
  version: v1.0
---

# Outline

## 1. AI 工具铺开,但架构评审仍靠人,质量飘移
- intent: 让管理层认可:这件事必须做
- layout: bullet_list
- data: 研发提速 30% / 评审排期 ≥ 1 周
- diagram: 无

## 2. 覆盖 4A:Application/Architecture/Auth-N/Auth-Z 全闭环
- intent: 划清边界
- layout: cards
- diagram: 无

## 3. 5 阶段串行,每阶段 ≤ 3 天,卡点不超 1 周
- intent: 节奏可控
- layout: pic_text
- diagram: drawio flow chart

# Pyramid 自检
- [x] ① 单一顶端论点
- [x] ② SCQA 完整
- [x] ③ 答案在前
- [x] ④ MECE 通过
- [x] ⑤ 纵向疑问/回答链
- [x] ⑥ 字段完整
- [x] ⑦ action title ≤ 24 字
```

**主线程会说:"Outline 在 deck_v1_outline.md,审一下,改完告诉我。"**

> 如果 Pyramid 自检某项 unchecked,主线程会主动指出哪一项不过 + 怎么改。

### 5.2 Stage C 后,你能做的

**最方便的 3 种改法**:

| 想做的 | 怎么做 |
|---|---|
| 直接编辑文件 | 在 VS Code / Obsidian 打开 outline.md 改 → 告诉主线程"我改了,继续" |
| 让主线程改 | "第 3 节标题改成 ……" / "加一节 X 在 2 后" / "删第 5 节" |
| 推翻重来 | "重新设计 outline,改用结论先行结构" |

### 5.3 Stage D —— 主线程拓写

批准 outline 后,主线程:

1. **出图** —— 调 matplotlib_rc / draw.io,PNG 落到 `_assets/charts/`
2. **拓写每节** —— 按 layout 字数规则展开;关键数据加 `> 数据:Source: ...` 引文
3. **嵌入图** —— 用 `![alt](_assets/charts/X.png)` 嵌进 markdown

产出 `deck_v1_content.md`(20 页 deck 约 3000-5000 字 + 嵌入图)。

### 5.4 Stage D 你会收到什么

主线程会展示 `deck_v1_content.md` 大纲 + 关键改动,例:

```
deck_v1_content.md 写好了(2400 字 + 2 张图)。预览前 3 页:

## 1. AI 工具铺开,但架构评审仍靠人,质量飘移
<!-- layout: bullet_list -->
- 研发周期被 AI 压缩 30%
- 架构评审仍排期 ≥ 1 周
- 上线返工率从 8% 升至 24%
> 数据:Source: 公司 2025 Q4 月报

## 2. 覆盖 4A 全闭环 ...
[完整内容请打开 deck_v1_content.md]
```

**改法 3 种**:

| 想做的 | 怎么做 |
|---|---|
| 直接改 md | 文件编辑器改 → "我改了 page 5,继续" |
| 让主线程改 | "page 7 那个数据改成 35%" |
| 重写某节 | "第 3 节重写,我要换 layout 成 table" |

### 5.5 Stage E 你会收到什么

content 批准后主线程派 agent 去 build,跑完返回:

```yaml
pptx_path: /abs/path/to/deck_v1.pptx
qa_rounds: 2
auto_md_edits:                          # agent 自动改了哪几句
  - page: 5
    issue: "action title 27 字超 24 限制"
    before: "应当本季度落地 AI 4A 评审办法,5 阶段每阶段不超过 3 天"
    after: "本季度落地 AI 4A,5 阶段 ≤ 3 天"
review_needed:                          # 3 轮仍未解决的(罕见)
  - page: 12
    issue: "matplotlib 字体 fallback"
    suggestion: "macOS 装雅黑"
pyramid_check:
  passed: true
```

**主线程会问**:"agent 自动改了 1 处(page 5 action title 缩短),需要回退吗?" 你回 "接受" 或 "回退" 即可。

---

## 6. 写好需求的六条经验(在 Stage A 对话时用)

主线程在 Stage A 问你需求时,**答得越具体,outline/content 越准**。下面这六条,能把出稿质量直接抬一档。

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

任一项不过,直接告诉主线程改:

```
Pyramid 自检第 ④ 项不过:第 3 节"评审流程"和第 4 节"组织保障"内容有重叠
(评审委员会算流程也算保障)。把组织保障合并进流程节,outline 重排成 4 节
```

### 审 content.md(Stage D 后)

这一步**才是真正决定 .pptx 长什么样**的环节。重点查:

| 维度 | 你审什么 |
|---|---|
| **每节文案** | 数字对不对?术语统一吗?有没有错字? |
| **数据 source** | 关键数据有没有 `> 数据:Source: ...` 引文? |
| **图嵌入** | `![](_assets/charts/X.png)` 路径对吗?图本身好看吗(直接看 PNG)? |
| **字数** | 看到 bullet 特别长 / cards body 特别短的就标出来 |
| **action title** | 还是 outline 那 7 项的延伸:是结论句吗?≤ 24 字吗? |
| **tone 是否一致** | 全 deck 同一语气(executive / technical 等) |

**最高效的改法**:直接打开 `deck_v1_content.md` 在 VS Code / Obsidian 里改,然后告诉主线程"我改了"。markdown 容易编辑,不需要让主线程逐句重写。

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

agent build 完成,主线程会把以下三样给你:

1. **`.pptx` 路径** —— 直接用 PowerPoint / Keynote 打开
2. **`auto_md_edits[]`** —— agent 在视觉 QA 循环里自动改了哪几句 md(列表)
3. **`review_needed[]`** —— 3 轮自检仍解不掉的问题(罕见)

### 处理 auto_md_edits

agent 改了 content.md 的格式类问题(字数超限 / layout 推断错等),都会列在这里:

```yaml
auto_md_edits:
  - page: 5
    issue: "action title 27 字超 24 限制"
    before: "应当本季度落地 AI 4A 评审办法,5 阶段每阶段不超过 3 天"
    after: "本季度落地 AI 4A,5 阶段 ≤ 3 天"
```

你的选项:

| 选项 | 怎么做 |
|---|---|
| 全部接受 | "接受所有 auto_md_edits"(content.md 保持 agent 改后的版本) |
| 回退某条 | "回退 page 5 的改动"(主线程会 revert 那一条) |
| 全部回退 | "回退所有 auto_md_edits"(回到你批准时的 content.md;agent 改的视觉问题会重现,你得自己接受或换思路) |

### 处理 review_needed

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
| **主线程 Claude(v3)** | 与你直接对话的 Claude;v3 中**退化为 thin dispatcher** —— 只 router 消息,不持有 PPT 业务逻辑 |
| **iloveppt-brainstorm**(v3 第 1 agent) | Stage A+B —— 多轮问你需求 + 引导你提素材。多次派发模式,状态在 `.iloveppt_dialog_state.json` |
| **iloveppt-author**(v3 第 2 agent) | Stage C+D —— 出 outline.md → 等你批 → 出 content.md → 等你批。状态在 `.iloveppt_author_state.json` |
| **iloveppt**(v3 第 3 agent,builder) | Stage E —— 接 content.md → Pyramid 自检 → md→JSON → build → 视觉 QA。单次派发完成 |
| **state file** | agent 的"跨派发记忆"——`.iloveppt_*_state.json`。多次派发同一 agent 时,它读 state 恢复进度 |
| **brief** | 你输入的需求,v3 主要是对话(一句话起步);v2 兼容的 brief.yaml 仍可作输入 |
| **outline.md** | Stage C 产出物(`deck_v{N}_outline.md`),章节 + Pyramid 自检 checkbox,等你批准 |
| **content.md** | Stage D 产出物(`deck_v{N}_content.md`),全文 + 数据图嵌入,等你批准 |
| **Stage A-E** | v3 流程的 5 个阶段:需求挖掘 / 素材摄入 / 内容规划 / 全文拓写 / 终稿构建 |
| **auto_md_edits** | agent 在视觉 QA 循环里自动改了 content.md 的清单,返回时给你看,可批准/回退 |
| **_assets/** | 素材文件夹,raw(原始)/ charts(生成图)/ refs(参考图)三个子目录 |
| **outline(v2 遗留概念)** | 章节大纲。v2 是 Phase 1 yaml 输出;v3 改成 outline.md(用户可读) |
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
