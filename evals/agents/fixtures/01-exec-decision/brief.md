# Fixture 01 · Brief 输入

## user_initial_request

```
做一份给 CTO 看的 AI 4A 评审办法提案,15 分钟,要落地。
我有 Q4 评审数据(_assets/raw/q4_reviews.csv)和现有架构图(_assets/refs/current_arch.png)。
```

## user_responses(按 brainstorm 提问顺序)

按 brainstorm 提问顺序回答,**必须照写**(eval 要可重复):

| brainstorm 提问 | 你的标准回答 |
|---|---|
| audience 是 executive / technical / general / sales 哪个? | executive(CTO 是高管) |
| duration 多少分钟? | 15 |
| presentation_mode speaker / handout / 双用途? | speaker |
| top_recommendation 完整推荐句是什么?(若 brainstorm 给几个候选)| 应当本季度落地 AI 4A 评审办法,5 阶段每阶段 ≤ 3 天,降 60% 人力 |
| theme 用 tech_blue 还是自带模板? | tech_blue |
| output 路径? | 默认即可(`<working_dir>/builder/deck_v1.pptx`)|
| 数据文件确认? | 是的,_assets/raw/q4_reviews.csv |
| 参考图确认? | 是的,_assets/refs/current_arch.png |
| brief.md 看后 OK? | OK |
| outline 审完(若有改动建议) | 批准 outline |
| critic Stage C 报告(若有 notes) | 接受 notes 进 Stage D |
| content 审完 | 批准 content |
| critic Stage D 报告(若有 notes) | 接受 notes 进 builder |
| audience review(若 < 9) | 按 needs_designer_revision / needs_author_rewrite 分类,接受 designer 那条;needs_author_rewrite 我自己看一遍再决定 |
| 最终交付确认 | OK 交付 |

## 准备素材(eval 跑前 mock)

```bash
# 在 fixture 跑前 mock 数据
WORKDIR=/tmp/eval_<timestamp>/decks/01-exec-decision
mkdir -p $WORKDIR/_assets/{raw,refs}
cat > $WORKDIR/_assets/raw/q4_reviews.csv <<EOF
month,reviews_count,review_days_avg,passed_first_round_pct,reviewer_hours
2025-10,12,8.2,0.42,156
2025-11,15,9.5,0.38,194
2025-12,11,11.3,0.31,178
EOF

# 用一张占位图(或仓库自带的任何 PNG)
cp /Users/pc2026/Documents/DevTools/iLovePPT/skills/diagram/examples/minimal.png $WORKDIR/_assets/refs/current_arch.png
```
