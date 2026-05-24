# Deck status · claude-code-training

status: terminated
stopped_at: 2026-05-25
quality_grade: B+(v2 R5)
audience_final_score: 8.58(v2 R5 · 终止后 audience5 完成的最终评分)
audience_v1_final_score: 8.42(v1 R4)
pyramid_known_issues: []
review_needed_architectural:
  - p36 closing next_steps make_closing 函数硬截 [:3](v2 author 写 4 项被截 1 项 · 接受)
  - p36 closing visual 散乱 + p1 cover TEAM 卡通占左半(theme 代码硬编码 · 未动)

last_artifacts:
  - brief.md ✓
  - deck_v1_outline.md ✓ (approved)
  - deck_v1_content.md ✓ (approved · audience R4 8.42)
  - deck_v1.pptx ✓ (audience R4 8.42 ship 版本)
  - deck_v1_baseline.pptx ✓ (baseline 副本)
  - deck_v1_render/ ✓
  - deck_v2_outline.md ✓ (R5++ overhaul · 未经 audience 评)
  - deck_v2_content.md ✓ (R5++ overhaul · 未经 audience 评)
  - deck_v2.pptx ✓ (R5++ + designer4 polish · 未经 audience 评分)
  - deck_v2_plan.json ✓
  - deck_v2_render/ ✓
  - critic_report_C.md ✓ (Stage C pass_with_notes)
  - critic_report_D.md ✓ (Stage D pass_with_notes)
  - audience_review.md ✓ (R1 = 7.55)
  - audience_review_r2.md ✓ (R2 = 8.10)
  - audience_review_r3.md ✓ (R3 = 8.30)
  - audience_review_r4.md ✓ (R4 = 8.42 · v1 最后版本)
  - audience_review_r5.md ✓ (v2 R5 = 8.58 · 用户终止后到达,5/5 cap 用尽)
  - designer_report.md ✓ (含 R1+R2+R3+R4 4 轮 polish)

iteration_log:
  R1 (iter 1/5): 7.55  — 基线
  R2 (iter 2/5): 8.10  — Top 1 (TBD pages b 选项) + 2 (diagram 重画) + 3 (section_divider single_focus)
  R3 (iter 3/5): 8.30  — Top 1 (compare_pk body 扩) + 2 (p7 framing) + 3 (p36 next_steps)
  R4 (iter 4/5): 8.42  — Top 1 (扉页削字 + cover hero + closing)
  v1 ship 版本 = R4 8.42 (quality_grade B)
  
  v2 R5++ 工作完成但未评分:
    - author5: 3 个新 layout (cards_flag_3 × 2 + tri_pyramid_4sub_3 + timeline_band_3)
              + WebSearch evidence anchor (Anthropic + Sacra URL)
              + G 视角翻译 (p20/21/23)
              + 4 扉页削字
    - 主线程: 在 themes/template_training.py 加 3 个 make_ 函数(新 visual patterns)
    - designer4: p32 org-tree-multilevel 重画 + p1 cover hero 数字 anchor + p36 next_steps fix
  
  v2 audience R5 评分:8.58 / 10(终止后到达,5/5 cap 用尽 · quality_grade B+)
    - excellent ≥9: 9 页(R4 是 6,+3)
    - needs_minor: 1 页(**p11 regression** · 9.0→7.5 · VS 圆与 title 几何重叠 + body mid-word 切断)
    - needs_major: 0 页
    - 三视角:E 8.80 / T 8.80 / G 8.50(R4 8.65/8.55/8.10,G 升幅最大 +0.40)

regression_p11:
  symptom: right col title "(Claude Code agentic 时代)" 第 2 行 "时代)" 与 VS 圆重叠;body "读整个 codeba" 切 mid-word
  unknown_root_cause: author5/builder5 都没改 p11,但分数从 9.0→7.5;可能是连锁字段或 theme 边界
  fix_options:
    a: author quick fix · title 缩短到 ≤ 12 字单行(例 "让 AI 直接交付 · Agentic")
    b: theme 根 fix · make_compare_pk 加 VS 圆 wrap-avoidance 几何 或 缩 VS 圆 1.2"→0.9"

repo_code_changes:
  - skills/pptx-deck/themes/template_training.py:
      + make_timeline_band_3
      + make_tri_pyramid_4sub_3
      + make_cards_flag_3
      ✏ make_compare badge stamp 形态(R2 fix)
      ✏ make_toc / make_section_divider 加 caption / sub_caption 参数(R2 fix)
  - skills/pptx-deck/build.py:
      ✏ FOOTERED_LAYOUTS 加 3 个新 layout
  - .claude/pipeline-protocol.md:
      + §0 团队模式通信规则
  - .claude/agents/*.md (7 个文件):
      + tools 字段加 SendMessage
      + ## 团队模式通信(必读)节

pending_data_pages: ["3.3", "3.4", "3.6"]
  reason: 用户选择 placeholder ship,等 1 周 W1/W2 pilot 实测数据回填

how_to_resume: |
  跟主线程说"继续 deck claude-code-training",会:
  1. Read 本 STATUS.md + 各 audience_review_rN.md 看历史
  2. 选恢复点:
     - v1 (R4 8.42) 直接 ship → 用 deck_v1.pptx
     - v2 评分 → 派 audience R5 评 deck_v2.pptx(目前未评)
     - v2 继续 polish → 派 author/designer R6
     - v3 W1 数据回填 → 用户给真实试点数据后,author 改 p20/21/23 body
