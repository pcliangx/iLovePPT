# Agent Eval 框架

这是用来量化 iLovePPT agent 输出质量的 eval 集 —— 跟 `${CLAUDE_PROJECT_DIR}/evals/plans/` 的 build.py 回归测试**性质不同**:

| 集 | 测什么 | 谁评 |
|---|---|---|
| `${CLAUDE_PROJECT_DIR}/evals/plans/` | build.py 机械构建回归(固定 plan → .pptx) | 跟 `baseline/scorecard.md` diff |
| **`${CLAUDE_PROJECT_DIR}/evals/agents/`(本目录)** | agent 输出质量(brainstorm/author/critic/iloveppt/audience 的产出是否好,5 agent + 1 旁路) | 人工 + audience LLM 评分 |

## 为什么需要这个 eval

> 没 eval 一切 prompt 改动都是"看起来更好"

每次改 agent prompt(加 few-shot / 调措辞 / 改人设)后,跑同一份 brief 看输出有没有退化或提升。**没量化反馈 = 盲改**。

## 目录结构

```
evals/agents/
├── README.md                       (本文件)
├── fixtures/                       5 个固定测试 brief
│   ├── 01-exec-decision/           executive 决策 deck
│   │   ├── brief.md                输入(标准化 brief)
│   │   ├── expected.md             预期输出(章节要点 + 必出元素 + audience 目标分)
│   │   └── README.md               这个 fixture 测什么
│   ├── 02-tech-architecture/       technical 架构 deck
│   ├── 03-sales-pitch/             sales 提案
│   ├── 04-general-training/        general 培训
│   └── 05-handout-weekly/          handout 周报模式
├── runners/
│   └── manual_runner.md            人工跑 + 收集输出的步骤
├── score_rubric.md                 5 维评分标准
└── baseline/
    ├── README.md                   怎么登记 baseline
    └── (timestamped JSON 文件)     例:2026-05-24-baseline.json
```

## 5 维评分标准

完整规则见 `score_rubric.md`,概括:

| 维 | 满分 | 评 |
|---|---|---|
| Brief 准确度(brainstorm) | 10 | brief.md 覆盖的字段完整度 + 跟用户原始 intent 一致 |
| Outline 结构(author Stage C) | 10 | Pyramid 5 件套 + MECE + 章节数合理 |
| Content 拓写(author Stage D) | 10 | 字数遵守 + 数字 > 形容词 + Source 引文 |
| Critic 评审深度(critic) | 10 | 三档 verdict 合理 + 判断性 issue 三要素完整 |
| 最终 deck 质量(audience overall) | 10 | audience agent 自己给的 overall_score |

总分 50;baseline 跑下来一般 35-42 之间,改 agent 后 ≥ baseline + 2 算提升,≤ baseline - 2 算退化。

## 怎么跑(manual runner)

详细步骤见 `runners/manual_runner.md`。简版:

```bash
# 1. 选 fixture
cat evals/agents/fixtures/01-exec-decision/brief.md

# 2. 在 Claude Code 里说:
"我要跑 eval fixture 01,brief 内容如下:..."
# 主线程会按完整流水线跑:brainstorm → author → critic(C) → author(D) → critic(D) → iloveppt(build+视觉) → audience

# 3. 跑完后,把各 agent 产出收集到 evals/agents/baseline/<timestamp>-<tag>.json
# 4. 跟之前的 baseline 对比 → 看哪个维度涨了 / 跌了
```

## 何时跑

- ✅ 改 agent prompt 前后(`few-shot 示范` 节有变 / `人设` 改 / `red lines` 加减)
- ✅ 给 agent 加新工具(WebSearch / WebFetch / Skill 之类)
- ✅ 改派发逻辑(主线程的路由变了)
- ⏸️ 改 helpers.py / themes.py(那是 `${CLAUDE_PROJECT_DIR}/evals/plans/` 的事,跟 agent 输出无关)

## 不跑这个 eval 的代价

- 改 prompt → "感觉更好" → commit
- 下次跑发现某 case 退化 → 不知道是哪次改的
- 想 rollback → 不知道 rollback 哪条
- 长期看 agent 质量随机漂移
