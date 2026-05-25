# Fixture 03 · Brief

## user_initial_request

```
做一份给企业客户讲我们 SaaS 产品的销售提案,20 分钟,要打动决策方。
我有竞品对比表(_assets/raw/competitor.csv)和客户 logo(_assets/brand/logos.png)。
```

## user_responses

| brainstorm 提问 | 标准回答 |
|---|---|
| audience | sales |
| duration_min | 20 |
| presentation_mode | speaker |
| top_recommendation | 选我们:同等功能下成本 -50%,落地周期 -3x,30 家头部企业已验证 |
| theme | tech_blue |
| 数据 + 素材 | _assets/raw/competitor.csv + _assets/brand/logos.png |
| brief.md / outline / content / critic / audience | 一律照标准流程 |

## 准备素材

```bash
WORKDIR=/tmp/eval_<timestamp>/decks/03-sales-pitch
mkdir -p $WORKDIR/_assets/{raw,brand}

cat > $WORKDIR/_assets/raw/competitor.csv <<EOF
feature,us,competitor_a,competitor_b
price_per_seat_month_usd,12,28,35
deploy_weeks,2,8,6
api_endpoints,180,95,120
sla_uptime,99.95,99.5,99.9
EOF

cp /Users/pc2026/Documents/DevTools/iLovePPT/.claude/skills/diagram/examples/minimal.png $WORKDIR/_assets/brand/logos.png
```
