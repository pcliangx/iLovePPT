# Fixture 02 · Expected Output

## brief.md 应有

```yaml
audience: technical
duration_min: 30
top_recommendation: 新一代订单系统三层架构把 P99 延迟从 820ms 降到 130ms,Q3 灰度
theme: tech_blue
presentation_mode: speaker
```

## outline.md 应有

- **章节数**:4-5(技术架构典型:背景 → 架构 → 关键决策 → 数据 → 落地)
- **action title 含具体数字**(✗ "性能优化" / ✓ "P99 从 820ms 降到 130ms,QPS 涨 3.2x")
- 配图标注 ≥ 3 张(系统总览 / 数据流 / 部署拓扑)
- footer_meta 默认填

## content.md 应有

- 总页数 30 × 1.5 = **45 页 ± 5**
- 至少 3 张 draw.io 架构图(`_assets/charts/*.png`)
- 至少 1 张 matplotlib 数据图(perf benchmark 对比)
- 每数据 page 有 `> 数据:Source: bench.csv` 引文
- `pic_text` 用得多(架构图 + 解释)

## critic 应有

- **维度 1 论据强度高分**(technical deck 数据多,论据应该 sharp)
- 5 维度判断性 issue ≥ 4 个(可能有"措辞过度商务化"等)

## audience 应有

- **按 technical profile**:`info_density` 应该 9+(技术受众细节为王)
- `visual_appeal` 中等就 OK(技术稿不需要花哨)
- `comprehension_5s` 跟普通受众标准不同(技术受众允许多 2 秒理解)
- **overall_score ≥ 8.0**

## 评分锚点

| 维 | 期望 |
|---|---|
| 1 | ≥ 8 |
| 2 | ≥ 8(MECE + 含数据的 action title) |
| 3 | ≥ 7.5(45 页字数严守 + 架构图齐全有挑战) |
| 4 | ≥ 7 |
| 5 | ≥ 8.0 |
| **总分** | ≥ **38.5** |
