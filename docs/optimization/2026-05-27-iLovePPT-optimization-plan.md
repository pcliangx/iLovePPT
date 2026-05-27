# iLovePPT 优化计划

**日期**:2026-05-27
**起始版本**:v0.8.0
**目的**:全维度系统性优化清单 + baseline 度量,后续 sprint 完成后回写对比数据。

---

## 0. 文档使用方式

- 每个 sprint 完成后,**在 § 1 Baseline 度量表新增一列**(`P0-after` / `P1-after` / ...),不要覆盖 baseline
- 任务完成 → § 2-5 任务清单状态 ☐ → ✓,同时在 § 9 变更记录追一行
- 用 `library/_rag/bench.py` 自动跑 7 query bench,把结果填到 § 1 表
- 这份文档是改善前后对比基准,**Baseline 不可改**

---

## 1. Baseline 度量(2026-05-27)

> Baseline 是 v0.8.0 release 后状态。后续 sprint 完成后增加列。

| 维度 | Baseline (2026-05-27) | **P0 后 (2026-05-27)** | P1 后 | P2 后 | 目标 |
|---|---|---|---|---|---|
| **RAG · 准确性** | | | | | |
| #1 命中数 (7 query) | 5/7 (71.4%) | **7/7 (100%)** ✓ | | | 7/7 |
| 平均 #1 分 | 0.7687 | 0.7637(略降 · inverse-cat penalty)| | | ≥ 0.80 |
| 平均 gap (#1 − #2) | 0.0604 | **0.1156** (+0.055) ✓ | | | ≥ 0.10 ✓ 已达 |
| gap < 0.05 的 query 数 | 4/7 | **2/7** (-2) ✓ | | | 0/7 |
| 模板 DB 大小(tpl_pages)| 212 (含 16 工具页)| **196** (-16,清工具页) | | | 196 |
| 模板 DB 大小(emb)| 219 | **203** (-16) | | | 203 |
| **RAG · 工程** | | | | | |
| query log 启用 | ❌ | ✓ (P0-2) | | | ✓ |
| regression bench 启用 | ❌ | ✓ (P0-3) | | | ✓ |
| **7 模板 ingest 时间** | | | | | |
| Wave parallel(5 并行)| ~5 min | (未优化)| < 2 min | | < 2 min (P1-6/7) |
| Extractor agent token(单次)| 80-220k | (不变)| | | 50-150k (P3-7) |
| **Self_check 项数** | 9 | **11** ✓ (P0-1/7) | | | 11+ |
| **placeholder_map 含 shape_id** | ❌(只 tree_path)| ✓ **212/212 backfilled**(P0-7) | | | ✓ |
| **受控词典 SSOT** | 0 个 | (P1 才做) | 5 个 (P1-1~5) | | 5 个 |
| **visual-patterns kb 条数** | 0 | | | 10-15 (P2-6) | 10-15 |
| **Pipeline 步数** | 9 | | | 7 (P2-3) | 7 |
| **Critic verdict 一致率** | 不可重复 | | | 100% (P2-1) | 100% |
| **Audience score 方差**(同 deck 3 次)| 未测 | | | < 0.5 (P2-2) | < 0.5 |
| **Per-deck cost log** | ❌ | | ✓ (P1-8) | | ✓ |

### RAG · 7 query baseline 详细

**Baseline + P0-after 并列对比表**

| Query | Expected | Baseline #1 | Baseline Gap | **P0-后 #1** | **P0-后 Gap** | Δ Gap |
|---|---|---|---|---|---|---|
| 财务汇报 | finance_arrow | ✓ finance_arrow (0.77) | 0.0922 | ✓ finance_arrow (0.77) | **0.1944** | +0.10 |
| 团队培训 OKR kickoff | training_team | ✓ training_team (0.76) | 0.0774 | ✓ training_team (0.76) | **0.1803** | +0.10 |
| 极光渐变 创意 黑底高级感 | creative_aurora | ✓ creative_aurora (0.85) | 0.1412 | ✓ creative_aurora (0.85) | **0.2469** | +0.11 |
| 企业年报 路演 | enterprise_skyline | ✗ finance_arrow #1 (0.79) · 期望 #2 | 0.0203 | ✓ **enterprise_skyline #1 (0.77)** | **0.0527** | +0.03 ✓ 翻 |
| SWOT 工作汇报 | business_geometric | ✗ finance_arrow #1 (0.78) · 期望 #2 | 0.0142 | ✓ **business_geometric #1 (0.76)** | **0.0574** | +0.04 ✓ 翻 |
| 产品介绍 科技 SaaS | product_lineart | ✓ product_lineart (0.75) | 0.0389 | ✓ product_lineart (0.75) | 0.0389 | (gap 不变 · 1/3 hit 同 category) |
| 斜切条纹 几何工业 | modern_stripes | ✓ modern_stripes (0.68) | 0.0383 | ✓ modern_stripes (0.68) | 0.0383 | (gap 不变 · 同) |

**P0 已解决**:2 个 #2 case 翻 #1(企业年报 / SWOT),4 个 query gap 显著拉开(财务汇报 / 团队培训 / 极光 / + 翻盘的 2 个)。
**仍待 P1+**:产品 SaaS / 斜切条纹 2 个 gap 仍 < 0.05(因为 top-3 都在同 category enterprise-modern,inverse-category 没法分;需 layout variant 标准化 P1-1)。

---

## 2. P0 任务清单(立刻修 · 1 工作日)

> 不修就是已知 bug 在线上跑,或后续优化全瞎拍。

| # | 状态 | 问题 | 修法 | 工时 |
|---|---|---|---|---|
| P0-1 | ✓ | `self_check.py` 缺 list element type 校验 → embed_text promote 后炸(本 session 真撞了) | self_check.py 加 #10:`all(isinstance(x, str) for x in arr)` for keywords/content_intent/when_to_use/native_elements/recommended_for/visual_signature | 30min |
| P0-2 | ✓ | RAG 没 query log → 所有后续优化都是拍脑袋 | search.py 加 `log_query(query, hits, scores, chosen, ts)` → 写 `library/_rag/query_log.jsonl` | 30min |
| P0-3 | ✓ | RAG 没 regression bench → embed/search 改了不知道分跌没跌 | `library/_rag/bench.py` + 7 golden query SSOT(`bench_queries.yaml`)+ baseline snapshot | 2h |
| P0-4 | ✓ | "企业年报路演" / "SWOT 工作汇报" 仍 #2(`finance_arrow` 抢)→ v0.8.0 带 bug 发布 | search.py 加 inverse-category soft filter:hit.category 跟 brief.category 不符时 score × 0.85 | 1h |
| P0-5 | ✓ | 4 个 declared==rendered 模板的 `extraction.discrepancy_resolution` 仍是 `pending` → 入库不完整 | 批量改 4 yaml `confirmed_no_loss`;self_check 加规则 declared==rendered → 自动 confirmed | 15min |
| P0-6 | ✓ | iSlide 工具页 keywords 含 "template reference" / "design criteria" → RAG 检索"模板说明"会命中工具页污染结果 | `embed_text/image.py` 加 skip:`if needs_manual_review and layout_type=='other': continue` | 1h |
| P0-7 | ✓ | `placeholder_map.tree_path` 是字符串 · 模板 update shape order 变就静默失效 → tier1 渲染破 | inspect_placeholders.py 同时输出 `shape_id`;placeholder_map 加 shape_id 字段(主),tree_path fallback;self_check #11 对账 | 4h |

**P0 总工时**:~9h

---

## 3. P1 任务清单(本 sprint · 1-2 周)

> 解决 80% 准确性根因 + 立刻能拿的工程性能。**P0 做完再做这层**。

### P1-A · 受控词典层 SSOT(最大杠杆)

| # | 状态 | 任务 | 工时 |
|---|---|---|---|
| P1-1 | ☐ | `library/vocabularies/layout_variants.yaml` SSOT · ~60 enum(cards-3-icon / cards-4-photo / timeline-h-N / process-arrow-N / process-funnel-N / comparison-2col / comparison-tier-3 / quadrant-swot 等)· 7 模板 212 页 backfill `variant` 字段 | 1d |
| P1-2 | ☐ | `library/vocabularies/slot_ids.yaml` SSOT · 通用槽位词汇 · extractor 强制 enum 选 · self_check #12 校验 | 4h |
| P1-3 | ☐ | `library/vocabularies/categories.yaml` SSOT · 4 → 12 enum · 7 模板 retrofit | 2h |
| P1-4 | ☐ | `library/vocabularies/audience_personas.yaml` SSOT · persona 字段(name/role/concerns/decision_criteria) · brief / audience 引用 | 4h |
| P1-5 | ☐ | `library/vocabularies/keywords_bank.yaml` SSOT · 按 category 分桶 · LLM 从桶里选,不允许自由发明 · EXPANSION_HINTS 改成 keywords_bank derived view | 4h |

### P1-B · 工程性能 + 防御加固

| # | 状态 | 任务 | 工时 |
|---|---|---|---|
| P1-6 | ☐ | `embed_text/image` API batch(qwen 支持 batch=16) · ingest 10min → 2min | 1h |
| P1-7 | ☐ | `embed_text` 跟 `embed_image` 两进程并行 | 30min |
| P1-8 | ☐ | per-deck token cost log · `state.json` 加 `tokens_by_agent[]` / `cost_usd` | 1h |
| P1-9 | ☐ | `EXPANSION_HINTS` 挪 yaml(配 P1-5) | 30min |
| P1-10 | ☐ | `red_line_words` 升级 rapidfuzz + 拼音 fallback | 1h |

**P1 总工时**:~3-4 工作日

---

## 4. P2 任务清单(本 quarter · 2-4 周)

### P2-A · 评审量化

| # | 状态 | 任务 | 工时 |
|---|---|---|---|
| P2-1 | ☐ | critic 14 项 checklist 量化 · 每项 `{passed/evidence/severity/suggestion}` schema · verdict = `severity_sum > N` | 1-2d |
| P2-2 | ☐ | audience 9 分硬阈值改定量打分 · 每页 12 项 / 0-3 分 · weighted sum | 1d |

### P2-B · Pipeline 重构

| # | 状态 | 任务 | 工时 |
|---|---|---|---|
| P2-3 | ☐ | pipeline 9 → 7 步 · critic B 并入 brainstorm self-audit · C+D merge · spot-check 并入 audience | 3d |
| P2-4 | ☐ | hot-reload for rework · `state.json` 加 `chapter_hashes[]` · 只重算 changed | 2d |
| P2-5 | ☐ | SSOT 减少 · `content.md` 单源 · `deck_plan.json` 自动 derive | 1d |

### P2-C · RAG 补强 + Library 完整化

| # | 状态 | 任务 | 工时 |
|---|---|---|---|
| P2-6 | ☐ | `visual-patterns` kb ingest 10-15 个 pattern · 验证 RAG fallback 路径 | 1d |
| P2-7 | ☐ | `--query-image` 接到 builder Step 4 / audience Step 3.5 · 视觉一致性检查 | 4h |
| P2-8 | ☐ | brainstorm `--query-image` 路径来源 · chat paste 图先 save 到 inspirations/ | 1h |
| P2-9 | ☐ | hybrid 权重 ablation · (1,0)/(0.8,0.2)/(0.6,0.4)/(0.4,0.6) × 7 query · 确定 default | 4h |
| P2-10 | ☐ | iconify / Unsplash query 沉淀缓存 · 复用历史好 query | 4h |

### P2-D · 可观测性 dashboard

| # | 状态 | 任务 | 工时 |
|---|---|---|---|
| P2-11 | ☐ | `scripts/dashboard.py` 跨 deck 聚合 · token / rework / audience / layout failure rate | 1d |
| P2-12 | ☐ | layout-level audience failure rate · 跨 deck 看哪 layout 最常 fail | 4h |
| P2-13 | ☐ | brief audience 改 multi-select · 不再单选 | 2h |

**P2 总工时**:~12-15 工作日

---

## 5. P3 任务清单(下 quarter / backlog)

### P3-A · 架构升级

| # | 状态 | 任务 | 工时 |
|---|---|---|---|
| P3-1 | ☐ | Theme 完全 yaml 化 · `themes/<name>.yaml` · Python 只剩 dispatcher | 1w |
| P3-2 | ☐ | Layout plugin/hook · `helpers.py/layouts/<name>.py` 自动发现 · `make_*` dynamic register | 3d |
| P3-3 | ☐ | build.py 拆分 · `builder/{base,tier1,tier2,tier3}.py` | 2d |
| P3-4 | ☐ | Hosted embedding endpoint mode · `embed_*.py --remote http://...` | 3d |
| P3-5 | ☐ | RAG quality feedback loop · `feedback.jsonl` · score < 7 pattern 降权 | 2d |
| P3-6 | ☐ | DB 升级 · SQLite WAL 或 pgvector | 2d |
| P3-7 | ☐ | subagent Haiku 路由 · self_check / yaml fix 用 Haiku | 1d |

### P3-B · 新功能 / 扩展

| # | 状态 | 任务 | 工时 |
|---|---|---|---|
| P3-8 | ☐ | `library/deck-skeletons/` SSOT · 季度报/postmortem scaffold | 3d |
| P3-9 | ☐ | 多模板组合 deck · `brief.theme: list` · 跨模板 deep-copy | 1w |
| P3-10 | ☐ | 中英文混排 · `mixed_lang_text(runs)` | 2d |
| P3-11 | ☐ | 多语言支持 · en-US / ja-JP | 2w |
| P3-12 | ☐ | a11y · 对比度 WCAG AA / alt-text / 屏幕阅读器 | 1w |
| P3-13 | ☐ | `scripts/deck_diff.py` 语义 diff | 2d |
| P3-14 | ☐ | `scripts/clip_chapter.py` 跨 deck 章节复制 | 1d |
| P3-15 | ☐ | 模板版本管理 · `source_pptx_version` + sha 跑 self_check | 2d |
| P3-16 | ☐ | layout 分类小 CV 模型 · resnet 走 extractor 快路径 · 80% page token 省 | 1w |
| P3-17 | ☐ | per-deck cost budget · 超额暂停 + 问用户 | 1d |

### P3-C · 治理 + 工程化长尾

| # | 状态 | 任务 | 工时 |
|---|---|---|---|
| P3-18 | ☐ | API key rotation · secrets manager | 1d |
| P3-19 | ☐ | pre-commit hook 扫敏感数据 · `_assets/raw` 强警告 | 4h |
| P3-20 | ☐ | `.gitignore.lint` · 3 份规则一致性自动校 | 4h |
| P3-21 | ☐ | RAG query log 脱敏 · 邮箱 / 手机号 / 钱数 redact | 2h |
| P3-22 | ☐ | 模板入库 detect iSlide 水印 + 版权 LOGO · 强警告 | 4h |

**P3 总工时**:~6-8 周

---

## 6. 依赖图

```
P0-2 query log ───────────────┐
P0-3 regression bench ────────┼──→ 所有 RAG 改动(P0-4, P1-5, P2-9 等)前置
P0-7 stable shape_id ─────────┘
                              │
P1-1 layout_variants.yaml ────┼──→ P1-2 slot_ids · P1-3 categories
                              │     P2-12 layout failure rate
                              │     P3-2 layout plugin/hook
P1-5 keywords_bank.yaml ──────┴──→ P1-9 EXPANSION yaml 化
                                    P3-5 quality feedback loop

P0-1 self_check #10 ──────────────→ P1 vocabulary 工作的强保障

P2-1 critic 量化 ─────────────────→ P2-3 pipeline 9→7
P2-2 audience 量化 ───────────────→ P2-4 hot-reload
```

**核心 dep 链**:`P0-2/3 数据基础 → P1 vocabulary 解准确性 → P2 评审量化 + pipeline 减负 → P3 架构升级`

---

## 7. 推荐执行顺序

| 周 | 任务 | 验收 |
|---|---|---|
| Week 1 | 所有 P0 | bench.py 跑通,query_log 有数据,2 个 #2 case 翻 #1,self_check 11 项 |
| Week 2-3 | P1-A 受控词典层(P1-1 ~ P1-5) | 5 个 vocabulary.yaml 落地;212 页 backfill variant + slot_id;extractor / author 自由字符串 hard_stop |
| Week 4 | P1-B 工程性能(P1-6 ~ P1-10) | ingest 10min → 2min;每 deck 知道 cost;red_line fuzzy |
| Week 5-6 | P2-A 评审量化(P2-1, P2-2) | critic / audience 跑同 deck 3 次方差 < 0.5 |
| Week 7-8 | P2-B Pipeline + SSOT(P2-3 ~ P2-5) | 9→7 步;rework 时间 -60%;content.md 单源 |
| Week 9-10 | P2-C/D RAG 补强 + dashboard | vp kb ≥ 10 patterns;dashboard.py 上线 |
| Week 11+ | P3 按需选做 | 不强求 |

---

## 8. 度量重测计划

每个 sprint 结束:
1. 跑 `library/_rag/bench.py --label <sprint-name>` → 7 query 表
2. 跑 `scripts/dashboard.py` → 跨 deck 聚合(P2-11 上线后)
3. 测 critic / audience 同 deck 跑 3 次方差(P2-1/2 上线后)
4. 测 7 模板 ingest 时间(`time` wall clock)
5. 把数字填到 § 1 baseline 表新增列
6. § 9 加变更记录

---

## 9. 变更记录

| Date | Sprint | 状态 | Notes |
|---|---|---|---|
| 2026-05-27 | Baseline | ✓ recorded | v0.8.0 release · 7 模板 ingest · RAG hybrid + 自然语言 doc + query expansion 完成 |
| 2026-05-27 | **P0 done** | ✓ all 7 | 4 agent 并行 · ~45min wall clock · 命中率 5/7→7/7 · gap 0.060→0.116 · 2 个 #2 case 翻 #1 · self_check 9→11 · placeholder_map 212 张全加 shape_id · DB 清 16 张工具页 |
| TBD | P1 done | ☐ | |
| TBD | P2 done | ☐ | |
| TBD | P3 done | ☐ | |
