# Post-hybrid baseline · 01-exec-decision

| 项 | 值 |
|---|---|
| Date | 2026-05-25 |
| Mode | Hybrid (brainstorm team + 5 subagent) |
| Wall-clock(主要 agent 累计) | ~25 分钟 |
| Total agents invoked | brainstorm × 4 rounds + author × 2 (Stage C / D / D-rework) + critic × 3 (C / D / D-r2) + iloveppt × 1 + audience × 1 |
| Total token (estimated) | ~600k |
| Final critic Stage D verdict | pass_with_notes (r2,r1 needs_revision) |
| Final audience overall_score | 6.4 / 10 (needs_major) |
| audience triage | needs_visual_redo:[8] (page 8 流程图 HTML 裸露) + needs_author_rewrite:[3,5,7,9,11,13,14] (divider 标题 / summary CTA) |
| Runtime.log usable | **NO**(全 agent=main / 5 个新字段全 na;Claude Code 未暴露 env vars 给 Stop hook) |
| Final .pptx | decks/eval-20260525-1351-01-exec-decision/builder/deck_v1.pptx (595KB, 14 pages, gitignore'd) |

## 文件清单

| 路径 | 说明 |
|---|---|
| brainstorm/brief.md | Phase A 收齐 brief(6 必填字段 + SCQA + 素材清单) |
| brainstorm/state.json | round=4, brief_approved=true, 完整 history |
| author/deck_v1_outline.md | Stage C outline(5 章 MECE + 每章 intent/layout/data/diagram) |
| author/deck_v1_content.md | Stage D content + D-rework(15 页全文 + 引文 + 2 张 chart 引用) |
| author/state.json | author 内部 state |
| critic/critic_report_C_r1.md | Stage C verdict=pass_with_notes (2 med + 2 low) |
| critic/critic_report_D_r1.md | Stage D r1 verdict=needs_revision (1 high + B7 fail) |
| critic/critic_report_D_r2.md | Stage D r2 verdict=pass_with_notes (must-fix 已修) |
| builder/deck_plan.json | md→JSON 转换产物 |
| builder/visual_report_r1.md | iloveppt Step 0-4 详细报告 |
| builder/deck_v1_content.postbuild.md | iloveppt 副本(auto_md_edits 留底) |
| audience/audience_review_r1.md | executive 视角 14 页评分 + top_3_must_fix + triage |

## 验证维度

| 维度 | 结果 |
|---|---|
| TeamCreate + Agent spawn | ✓ |
| Phase A brainstorm 多轮 SendMessage | ✓(但 idle 时常缺消息,需主线程 ping,见 postmortem) |
| Phase A → Phase B 切换(shutdown_request) | ✓(approved + teammate_terminated) |
| Task author Stage C / D / D-rework | ✓ |
| Task critic Stage C / D / D-r2 | ✓ |
| Task iloveppt Stage E(Step 0-4)| ✓ |
| Task audience(triage)| ✓ |
| yaml schema 主要字段 parse(agent/status/next_action/artifacts/verdict)| ✓ |
| yaml schema 细节字段 parse(per_page_scores / issues 等)| ⚠ schema 偏差(详见 postmortem) |
| 文本产物完整(brief / outline / content / 报告)| ✓ |
| 二进制产物(.pptx / render JPG)| ✓(在临时目录) |
| runtime.log 新字段(tokens / duration / tool_uses)| ✗ 全 na |

## 不包含

- `.pptx` 二进制(在 `decks/eval-20260525-1351-01-exec-decision/builder/deck_v1.pptx`,gitignore 不入库)
- 14 页 render JPG(同上)
- charts/*.png(同上)
- _assets/ (mock 数据,gitignore)

## 何时重跑

- iloveppt-* prompt 改造 / 6 agent 任一 prompt 大改 → 重跑此 fixture,新 baseline 对比 r1 文本差异
- pipeline-protocol.md 重写 → 重跑
- 新增 layout / theme / SSOT token 改动 → **不**需重跑(只影响 build.py,跑 `bash evals/run_eval.sh` 更适合)
