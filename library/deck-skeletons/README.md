# `library/deck-skeletons/`

**Deck skeleton SSOT** —— 给常见 deck 类型(季度财报 / 项目复盘 / 产品发布 / ...)预置 brief + outline 骨架,user 不必每次从零开始。

## 是什么

| skeleton | 一句话 |
|---|---|
| `quarterly_finance_report` | 财务总监对董事会的季度业绩报告(数据 / KPI / 趋势 / 风险) |
| `annual_strategy_review` | 高管对全员的年度战略回顾 + 来年方向 |
| `product_launch` | 产品经理对市场 / 销售的新品发布(定位 / 卖点 / GTM) |
| `team_okr_kickoff` | 团队 lead 启动季度 / 年度 OKR(目标 / KR / owner / 节奏) |
| `project_postmortem` | 项目结束后的复盘 / 5-whys / lessons learned |
| `customer_pitch` | 销售 / BD 对客户的提案(场景 / 价值 / 报价 / ROI) |

每个 skeleton 目录含:

```
<skeleton_name>/
├── skeleton.yaml        # brief 字段建议 + outline 章节框架
└── outline.md.tmpl      # author 用的 outline 骨架(留 placeholder 给 user 填)
```

## 怎么用

### 1. 用 `scripts/new_deck.py` 起新 deck

```bash
# 从 quarterly_finance_report 起一份新 deck
scripts/new_deck.py 2026-q2-report --skeleton quarterly_finance_report

# 看会做什么(不真建)
scripts/new_deck.py 2026-q2-report --skeleton quarterly_finance_report --dry-run

# 不带 --skeleton(等同空白 deck)
scripts/new_deck.py my-deck
```

行为:
1. 在 `decks/<name>/` 建标准 workspace(`brainstorm/ author/ critic/ builder/ audience/`)
2. 复制 `library/deck-skeletons/<skeleton>/skeleton.yaml` → `decks/<name>/brainstorm/skeleton_used.yaml`
3. 把 `outline_template` 转成 `decks/<name>/author/deck_v1_outline.md.draft`(留 placeholder)
4. 输出 user 下一步指引(`cd decks/<name>; 跟主线程说"做 PPT"`)

### 2. brainstorm agent 自动识别

`iloveppt-brainstorm.md` Step 0 会检查 `<working_dir>/brainstorm/skeleton_used.yaml`。**存在** → 自动加载 `suggested_audience / suggested_theme / suggested_duration_min / suggested_top_recommendation`,作为对话默认值告知用户("我看到你用了 quarterly_finance_report skeleton · 建议 audience=cfo · 你确认?")。

user 可随时改 / 弃用 / 重选。skeleton 只是 hint,**brief.md 仍是 SSOT**。

## skeleton.yaml schema

```yaml
name: <human-readable label>
description: <一句话用途>
suggested_audience: [<persona>, ...]      # 引用 library/vocabularies/audience_personas.yaml
suggested_theme: <template short name>    # 引用 library/pptx-templates/items/<name>/
suggested_duration_min: <int>
suggested_top_recommendation: <模板句, 用占位符如 N% / <动作> 留 user 填>
suggested_presentation_mode: speaker | handout

outline_template:
  - chapter: <int>
    title: <章节标题>
    intent: <一句话讲什么>
    suggested_layout: <layout enum>       # cover/toc/cards/data/timeline/...
    suggested_pattern: <kb-prefixed pattern id, 可选>
```

`outline.md.tmpl` 是 outline 骨架(章节框架 + intent + pattern hint),保留 `<TBD>` placeholder 让 user 在 brainstorm 阶段填具体内容。

## 贡献新 skeleton

1. `mkdir library/deck-skeletons/<your_skeleton_name>/`
2. 复制现有 skeleton 当蓝本(推荐 `quarterly_finance_report`)
3. 改 `skeleton.yaml`:
   - `name / description / suggested_*` 字段按你的 deck 类型改
   - `outline_template` 列出 6-12 章节框架(不要太细,user 还要填)
4. 改 `outline.md.tmpl`:跟 outline_template 一一对应,留足 `<TBD>` placeholder
5. 在本 README "是什么" 表里加一行
6. 提 PR

**质量要求**:
- audience / theme / duration 必须真用过(不要拍脑袋)
- outline 章节 6-12 个,跟受众认知节奏匹配
- pattern hint 优先 `tpl:` 前缀(具体模板页),其次 `vp:` 前缀(visual-patterns)
- 不要 hard-code 数字(N%, $M, K 用户 等)—— 用占位符

## 不变量

- skeleton 是 **hint**,不是强制。user 在 brainstorm 阶段可全部改 / 删 / 重选
- skeleton.yaml 只有 `suggested_*` 字段,**不含**最终 brief 字段(brief 由 brainstorm + user 协同产出)
- outline.md.tmpl 是 **草稿模板**,author 跑 Stage C 时仍会重写出 deck_v1_outline.md(skeleton 只是给 author 个起点)
