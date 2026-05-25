# Baseline 记录

这个目录存历次 eval 跑分,文件名 `<YYYY-MM-DD>-<git-sha>-<fixture-id>.json`。

## 怎么登记

跑完 1 个 fixture 后,把分数按如下 schema 写一个 JSON:

```json
{
  "fixture_id": "01-exec-decision",
  "iloveppt_version": "<git-tag-or-sha>",
  "git_sha": "855db62",
  "ran_at": "2026-05-24T10:00:00+08:00",
  "scorer": "manual" | "llm-claude-sonnet" | "llm-claude-opus",
  "scorer_notes": "manual mode, 单人评",
  "scores": {
    "1_brief_accuracy": 9,
    "2_outline_structure": 8,
    "3_content_writing": 7,
    "4_critic_depth": 8,
    "5_audience_overall": 9.1
  },
  "total": 41.1,
  "audience_4_dimensions": {
    "comprehension_5s": 9.0,
    "info_density": 8.8,
    "visual_appeal": 9.3,
    "flow_coherence": 9.4
  },
  "pipeline_metrics": {
    "audience_rounds": 1,
    "critic_c_rounds": 1,
    "critic_d_rounds": 1,
    "iloveppt_builder_step3_qa_rounds": 2,
    "iloveppt_builder_step4_visual_rounds": 1,
    "total_time_min": 28
  },
  "model_tiering": {
    "all_6_agents": "opus"
  },
  "notes": "brief.md gate 走得顺;content.md page 5 cards body 20 字超标(speaker mode 上限 18);iloveppt-builder Step 4 加 5 个 lucide icon 全部保留"
}
```

文件名:`2026-05-24-855db62-01-exec-decision.json`

## 历史走势

`grep total *.json` 可以快速看每次跑分。

## 退化判定

新跑分 vs 上一次同 fixture 跑分:
- `total` 变化 ≥ +2 → 提升
- `total` 变化 ≤ -2 → 退化(查 git log 看哪次 prompt 改坏了)
- 单维变化 ≥ ±2 → 该维度有变化(查 specific agent)

## 版本切片

每个版本应该至少跑全部 5 个 fixture:

```
<git-tag>:
  01-exec-decision      total: 41.1
  02-tech-architecture  total: 39.4
  03-sales-pitch        total: 42.8
  04-general-training   total: 38.2
  05-handout-weekly     total: 37.9
  ─────────────────────────
  avg: 39.88
```

下个版本 avg 应该 ≥ 上版 avg + 1.5 才能 commit。
