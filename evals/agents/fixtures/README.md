# Agent Eval Fixtures

每个子目录是一个**固定测试场景**,跟 `${CLAUDE_PROJECT_DIR}/evals/agents/score_rubric.md` 配套用。

## fixture 结构(固定)

```
<NN>-<slug>/
├── brief.md         # 用户视角的"我要做什么 PPT"——给 brainstorm 当 initial_request
├── expected.md      # 跑完应有的输出特征(章节要点 / audience 目标分 / 必出 layout)
└── README.md        # 这个 fixture 测什么(常规场景 / 边界条件 / 防回归)
```

**brief.md ≠ brainstorm 产出的 brief.md**。这里的 brief.md 是**用户提需求的原话**(包含可能的歧义、未明确字段、模糊措辞),目的是测 brainstorm 能不能挖出 deck_slug / audience / top_recommendation 等关键字段。

## 当前 fixtures(MVP 阶段)

| # | slug | audience | mode | duration | 测什么 |
|---|---|---|---|---|---|
| 01 | exec-decision | executive | speaker | 15 min | brainstorm 能否挖出隐含的 audience + brainstorm 是否替用户填 top_recommendation;**默认路径** |
| 05 | handout-weekly | technical | handout | 阅读型 | handout 模式字数 3-4× 规则;无 duration 的阅读型 deck;**边界条件** |

(README 设计的 02-04 待 P1 补齐:02-tech-architecture / 03-sales-pitch / 04-general-training)

## 怎么用

详细步骤见 `${CLAUDE_PROJECT_DIR}/evals/agents/runners/manual_runner.md`。简版:

1. 把 fixture 的 `brief.md` 内容当作用户的原话,在新会话里说"做个 PPT,需求是 ...(brief.md 内容)"
2. 让主线程按完整流水线跑(brainstorm → author → critic → iloveppt → audience)
3. 跑完收集产物,按 `score_rubric.md` 5 维度打分,写到 `baseline/<YYYY-MM-DD>-<tag>.json`
4. 跟历史 baseline 对比看回归 / 提升

## 为什么 fixture 是"用户原话"而不是结构化 brief

iLovePPT 的 brainstorm agent 价值就在于**把用户的模糊需求挖成结构化 brief**。如果 fixture 直接给结构化 brief,就跳过了 brainstorm 的核心职责测试。所以 fixture 故意保留歧义 / 缺字段 / 行话,看 brainstorm 怎么问。
