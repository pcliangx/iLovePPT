# Manual Runner · 怎么跑一个 fixture

iLovePPT 流水线需要 Claude Code agent infra 才能跑,**没有 fully automated runner**。本文档给手动跑的步骤。

## 准备

1. 确认你在 iLovePPT 仓库根目录(`pwd` 应有 `${CLAUDE_PROJECT_DIR}/skills/pptx-deck/build.py`)
2. 确认 fixture 存在:`ls ${CLAUDE_PROJECT_DIR}/evals/agents/fixtures/<fixture-id>/brief.md`
3. 确认环境干净:
   - `python3 -c "import cairosvg"` ✓(designer 需要)
   - `echo $UNSPLASH_ACCESS_KEY`(可选,designer hero 图)
   - `soffice --version`(builder 渲染)
   - `which pdftoppm`(builder PNG 转换)

## 步骤

### Step 1 · 选 fixture + 准备工作目录

```bash
# 选定 fixture
FIXTURE_ID="01-exec-decision"

# 准备临时工作目录(不污染 decks/ 真实项目)
mkdir -p /tmp/eval_$(date +%Y%m%d-%H%M)/decks/$FIXTURE_ID/_assets/{raw,charts,icons,hero,brand,refs}
cd /tmp/eval_$(date +%Y%m%d-%H%M)/decks/$FIXTURE_ID

# 复制 fixture 的 brief 进来(brainstorm 不读这个文件,但你要照着输 initial_request)
cp /Users/pc2026/Documents/DevTools/iLovePPT/evals/agents/fixtures/$FIXTURE_ID/brief.md ./reference_brief.md
```

### Step 2 · 在 Claude Code 里启动 brainstorm

跟主线程说(按 fixture 的 brief.md 里的 `initial_request` 字段):

```
我要跑 eval。Initial request:
[这里粘贴 fixture brief.md 的 user_initial_request 字段]
```

主线程会:
1. 识别 PPT 意图
2. `TeamCreate` 建 team
3. 派 brainstorm

### Step 3 · 模拟用户回答 brainstorm 的问题

按 fixture brief.md 里的 `user_responses` 字段照着回答 —— **不要 ad-hoc 回答**,evaluations 要可重复。

如:
```
brainstorm 问:audience 是 executive / technical / general / sales 哪个?

你按 fixture 答:executive
```

继续直到 brainstorm 出 brief.md gate。批准 brief.md(或对照 fixture.expected.md 给反馈)。

### Step 4 · author Stage C/D

主线程派 author Stage C → outline.md → 你审(对照 fixture.expected.md 章节)→ 批准 → critic Stage C → 用户 cherry-pick(若需要)→ author Stage D → content.md → 审 → 批准 → critic Stage D → builder → designer → audience。

**关键**:每个 checkpoint 你的回答应该是"标准回答",不要随心改。eval 是测 agent,不是测你的判断。

### Step 5 · 收集产出

跑完后,工作目录里应该有:
```
brief.md
deck_v1_outline.md
deck_v1_content.md
deck_v1_content.postbuild.md
critic_report_C.md
critic_report_D.md
designer_report.md
audience_review.md
deck_v1.pptx
deck_v1_render/page-*.jpg
STATUS.md
```

### Step 6 · 评分 + 记 baseline

按 `${CLAUDE_PROJECT_DIR}/evals/agents/score_rubric.md` 5 维度评分(或喂给独立 Claude 跑 LLM 评分模式)。

把分数记到 `${CLAUDE_PROJECT_DIR}/evals/agents/baseline/<YYYY-MM-DD>-<git-sha>.json`:

```json
{
  "fixture_id": "01-exec-decision",
  "iloveppt_version": "<git-tag-or-sha>",
  "git_sha": "855db62",
  "ran_at": "2026-05-24T10:00:00",
  "scorer": "manual" | "llm-claude-sonnet",
  "scores": {
    "1_brief_accuracy": 9,
    "2_outline_structure": 8,
    "3_content_writing": 7,
    "4_critic_depth": 8,
    "5_audience_overall": 9.1
  },
  "total": 41.1,
  "notes": "brief.md gate 走得很好;content.md 字数 1 处超标(page 5 cards body 20 字)"
}
```

### Step 7 · 对比

跟之前的 baseline 对比:

```bash
ls evals/agents/baseline/*.json | tail -5
# 看历史走势
```

总分变化 ≥ ±2 算显著。

## 常见问题

**Q · 跑 1 个 fixture 多久?**
A · 端到端 ~25-40 分钟(取决于 critic / audience 几轮收敛)。建议一次跑 1 个 fixture,5 个 fixture 跑完 ~3 小时。

**Q · 我可以跳过某些 stage 吗?**
A · 不要。eval 要测全流水线,跳了就不可比。

**Q · 如果 fixture 跑到一半我答错了?**
A · 重来。从 Step 1 开新临时目录。

**Q · 主线程派发出错怎么办?**
A · 记到 notes 里(eval 也测主线程 dispatcher 是否正确)。重启再跑。

**Q · 我可以加新 fixture 吗?**
A · 可以。模仿现有结构,加到 `fixtures/06-xxx/`,加 brief.md + expected.md + README.md。
