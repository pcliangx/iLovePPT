# Fixture 03 · Expected

## brief.md 应有

```yaml
audience: sales
duration_min: 20
top_recommendation: 选我们:同等功能下成本 -50%,落地周期 -3x,30 家头部企业已验证
theme: tech_blue
presentation_mode: speaker
```

## outline.md 应有

- 3-5 章节,典型:痛点 → 我们的方案 → 竞品对比 → 客户案例 → CTA
- action title 含具体卖点 + 数字
- **使用 `compare_pk` 至少 1 张**(对决式视觉冲击)
- **使用 `matrix_2x2` 可选**(差异化定位)

## content.md 应有

- 总页数 20 × 1.5 = **30 页 ± 3**
- **closing 必有 `next_steps` 结构化 CTA**(action + owner + due)
- `compare` 表用得多(竞品对比),有 `recommended: true` 标主推列
- brand assets 用上(iloveppt-builder Step 4 应该把 logo.png 嵌进 cover 或独立 logo wall page)

## builder/visual_report_r1.md 应有(iloveppt-builder Step 4 产出)

- **brand assets 优先级最高** —— iloveppt-builder Step 4 三路降级(brand > iconify > Unsplash)应优先 `_assets/brand/logos.png`
- icon 统一 prefix(若有 cards 加 icon · lucide / phosphor / tabler / heroicons 选一)
- visual_appeal 拉满优先(sales fixture 比 executive 更看重视觉冲击)
- `visual_step4.capability.rag_patterns` 非 `0_available` 且 `rag_fallback_used[]` 出现 ≥ 1 项(library-first:三处强制走 `library/search.sh`,见 [pipeline-protocol.md §3.3](${CLAUDE_PROJECT_DIR}/.claude/pipeline-protocol.md))

## audience 应有

- **按 sales profile**:`visual_appeal` 要求极高(≥ 9)
- CTA 不清晰 → comprehension_5s 扣分
- **overall_score ≥ 8.5**

## 评分锚点

| 维 | 期望 |
|---|---|
| 1 | ≥ 8 |
| 2 | ≥ 8 |
| 3 | ≥ 8 |
| 4 | ≥ 7 |
| 5 | ≥ 8.5 |
| **总分** | ≥ **39.5** |
